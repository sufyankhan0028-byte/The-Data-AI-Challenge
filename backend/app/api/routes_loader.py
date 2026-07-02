"""
FastAPI service — Candidate Data Loader

Endpoints:
  POST /api/load/file         — trigger load from an uploaded file
  POST /api/load/path         — trigger load from a server-side file path
  GET  /api/load/status       — SSE stream of live progress
  GET  /api/load/result       — final LoadResult JSON
  GET  /api/tables            — list available Parquet tables + row counts
  GET  /api/tables/{name}     — paginated preview of any table
  GET  /api/candidates        — search/filter profiles table
  GET  /api/candidates/{id}   — full candidate with all joined tables
  GET  /api/stats             — aggregate statistics over the dataset
  DELETE /api/load/cache      — wipe Parquet cache (force reload on next run)
"""
from __future__ import annotations

import asyncio
import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import pyarrow.parquet as pq
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.services.jsonl_loader import LoadResult, load_jsonl
from app.utils.logger import get_logger
from app.utils.state import app_state

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["loader"])

# ── Shared progress state (simple in-process; good enough for single-worker) ──
_load_result: Optional[LoadResult] = None
_progress_pct: float = 0.0
_progress_msg: str = "Idle"
_is_running: bool = False

OUTPUT_DIR = settings.PROCESSED_DIR


# ─────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────

class LoadPathRequest(BaseModel):
    path: str
    force: bool = False
    chunk_size: int = 2_000


class LoadResultResponse(BaseModel):
    total_lines: int
    valid_records: int
    skipped_records: int
    success_rate: float
    elapsed_seconds: float
    tables_written: List[str]
    skip_log: List[dict]


class TableInfo(BaseModel):
    name: str
    row_count: int
    size_bytes: int
    columns: List[str]


class CandidateSummary(BaseModel):
    candidate_id: str
    anonymized_name: str
    headline: str
    current_title: str
    current_company: str
    years_of_experience: float
    location: str
    country: str
    open_to_work_flag: bool
    profile_completeness_score: float
    preferred_work_mode: str
    skill_count: int


# ─────────────────────────────────────────────────────
# Load from uploaded file
# ─────────────────────────────────────────────────────

@router.post("/load/file", summary="Upload and load a JSONL/JSON candidate file")
async def load_from_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="candidates.jsonl or candidates.json"),
    force: bool = Query(False, description="Force re-process even if cache exists"),
    chunk_size: int = Query(2_000, ge=100, le=10_000, description="Records per Parquet flush"),
):
    global _is_running
    if _is_running:
        raise HTTPException(409, "A load operation is already running. Check /api/load/status.")

    suffix = Path(file.filename or "candidates.jsonl").suffix.lower()
    if suffix not in (".jsonl", ".json"):
        raise HTTPException(400, f"Unsupported file type '{suffix}'. Use .jsonl or .json.")

    dest = settings.RAW_DIR / f"candidates{suffix}"
    logger.info("Saving upload to %s ...", dest)
    with open(dest, "wb") as out:
        shutil.copyfileobj(file.file, out)

    size_mb = dest.stat().st_size / (1024 * 1024)
    logger.info("Saved %.1f MB. Queuing background load.", size_mb)

    background_tasks.add_task(_run_load, dest, chunk_size, force)

    return {
        "status": "accepted",
        "filename": file.filename,
        "size_mb": round(size_mb, 2),
        "message": "Load started. Poll GET /api/load/status for progress.",
    }


# ─────────────────────────────────────────────────────
# Load from server-side path
# ─────────────────────────────────────────────────────

@router.post("/load/path", summary="Load candidates from a server-side file path")
async def load_from_path(
    req: LoadPathRequest,
    background_tasks: BackgroundTasks,
):
    global _is_running
    if _is_running:
        raise HTTPException(409, "A load operation is already running.")

    source = Path(req.path)
    if not source.exists():
        raise HTTPException(404, f"File not found: {req.path}")
    if source.suffix.lower() not in (".jsonl", ".json"):
        raise HTTPException(400, "Only .jsonl or .json files are supported.")

    background_tasks.add_task(_run_load, source, req.chunk_size, req.force)
    return {
        "status": "accepted",
        "path": req.path,
        "message": "Load started. Poll GET /api/load/status for progress.",
    }


# ─────────────────────────────────────────────────────
# SSE progress stream
# ─────────────────────────────────────────────────────

@router.get("/load/status", summary="Live progress stream (Server-Sent Events)")
async def load_status_sse():
    """
    Returns an SSE stream that emits progress events every 500ms.
    Connect with EventSource in the browser or poll via fetch.
    """
    async def event_generator():
        global _progress_pct, _progress_msg, _is_running
        while True:
            data = json.dumps({
                "pct": round(_progress_pct, 1),
                "msg": _progress_msg,
                "running": _is_running,
                "valid": _load_result.valid_records if _load_result else 0,
                "skipped": _load_result.skipped_records if _load_result else 0,
            })
            yield f"data: {data}\n\n"
            if not _is_running and _progress_pct >= 100.0:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ─────────────────────────────────────────────────────
# Polling-friendly status endpoint
# ─────────────────────────────────────────────────────

@router.get("/load/poll", summary="Single-request progress check (JSON)")
def load_poll():
    return {
        "pct": round(_progress_pct, 1),
        "msg": _progress_msg,
        "running": _is_running,
        "valid": _load_result.valid_records if _load_result else 0,
        "skipped": _load_result.skipped_records if _load_result else 0,
    }


# ─────────────────────────────────────────────────────
# Final load result
# ─────────────────────────────────────────────────────

@router.get("/load/result", response_model=LoadResultResponse, summary="Final load statistics")
def get_load_result():
    if _load_result is None:
        raise HTTPException(404, "No load operation has been completed yet.")
    return LoadResultResponse(
        total_lines=_load_result.total_lines,
        valid_records=_load_result.valid_records,
        skipped_records=_load_result.skipped_records,
        success_rate=round(_load_result.success_rate, 4),
        elapsed_seconds=round(_load_result.elapsed_seconds, 2),
        tables_written=_load_result.tables_written,
        skip_log=_load_result.skip_log[:50],  # only first 50 for response
    )


# ─────────────────────────────────────────────────────
# Table explorer
# ─────────────────────────────────────────────────────

@router.get("/tables", response_model=List[TableInfo], summary="List available Parquet tables")
def list_tables():
    tables = []
    for pq_file in sorted(OUTPUT_DIR.glob("*.parquet")):
        try:
            meta = pq.read_metadata(str(pq_file))
            schema = pq.read_schema(str(pq_file))
            tables.append(TableInfo(
                name=pq_file.stem,
                row_count=meta.num_rows,
                size_bytes=pq_file.stat().st_size,
                columns=[f.name for f in schema],
            ))
        except Exception as exc:
            logger.warning("Could not read %s: %s", pq_file.name, exc)
    return tables


@router.get("/tables/{name}", summary="Preview rows from a Parquet table")
def preview_table(
    name: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    columns: Optional[str] = Query(None, description="Comma-separated column names"),
):
    path = OUTPUT_DIR / f"{name}.parquet"
    if not path.exists():
        raise HTTPException(404, f"Table '{name}' not found. Available: {_available_tables()}")

    col_list = [c.strip() for c in columns.split(",")] if columns else None
    try:
        df = pd.read_parquet(path, columns=col_list)
        total = len(df)
        page = df.iloc[offset: offset + limit]
        return {
            "table": name,
            "total_rows": total,
            "offset": offset,
            "limit": limit,
            "columns": list(page.columns),
            "rows": page.fillna("").to_dict(orient="records"),
        }
    except Exception as exc:
        raise HTTPException(500, f"Error reading table: {exc}")


# ─────────────────────────────────────────────────────
# Candidate search
# ─────────────────────────────────────────────────────

@router.get("/candidates", summary="Search and filter candidates")
def search_candidates(
    q: Optional[str] = Query(None, description="Full-text search on title/headline"),
    skill: Optional[str] = Query(None, description="Filter by skill name (substring)"),
    open_to_work: Optional[bool] = Query(None),
    min_yoe: Optional[float] = Query(None),
    max_yoe: Optional[float] = Query(None),
    work_mode: Optional[str] = Query(None, description="remote | hybrid | onsite | flexible"),
    country: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    profiles_path = OUTPUT_DIR / "profiles.parquet"
    if not profiles_path.exists():
        raise HTTPException(503, "Candidate data not loaded yet. POST /api/load/file first.")

    df = pd.read_parquet(profiles_path)

    # Apply filters
    if q:
        q_lower = q.lower()
        mask = (
            df["current_title"].str.lower().str.contains(q_lower, na=False)
            | df["headline"].str.lower().str.contains(q_lower, na=False)
            | df["summary"].str.lower().str.contains(q_lower, na=False)
        )
        df = df[mask]

    if open_to_work is not None:
        df = df[df["open_to_work_flag"] == open_to_work]

    if min_yoe is not None:
        df = df[df["years_of_experience"] >= min_yoe]

    if max_yoe is not None:
        df = df[df["years_of_experience"] <= max_yoe]

    if work_mode:
        df = df[df["preferred_work_mode"] == work_mode]

    if country:
        df = df[df["country"].str.lower() == country.lower()]

    # Skill filter: join with skills table
    if skill:
        skills_path = OUTPUT_DIR / "skills.parquet"
        if skills_path.exists():
            skills_df = pd.read_parquet(skills_path, columns=["candidate_id", "skill_name"])
            matched_ids = skills_df[
                skills_df["skill_name"].str.lower().str.contains(skill.lower(), na=False)
            ]["candidate_id"].unique()
            df = df[df["candidate_id"].isin(matched_ids)]

    total = len(df)
    page = df.iloc[offset: offset + limit]

    summary_cols = [
        "candidate_id", "anonymized_name", "headline", "current_title",
        "current_company", "years_of_experience", "location", "country",
        "open_to_work_flag", "profile_completeness_score",
        "preferred_work_mode", "skill_count",
    ]
    available = [c for c in summary_cols if c in page.columns]
    rows = page[available].fillna("").to_dict(orient="records")

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": rows,
    }


# ─────────────────────────────────────────────────────
# Candidate detail
# ─────────────────────────────────────────────────────

@router.get("/candidates/{candidate_id}", summary="Full candidate profile with all tables")
def get_candidate(candidate_id: str):
    profiles_path = OUTPUT_DIR / "profiles.parquet"
    if not profiles_path.exists():
        raise HTTPException(503, "Data not loaded.")

    profile_df = pd.read_parquet(profiles_path)
    row = profile_df[profile_df["candidate_id"] == candidate_id]
    if row.empty:
        raise HTTPException(404, f"Candidate '{candidate_id}' not found.")

    def _join_table(table_name: str) -> List[dict]:
        p = OUTPUT_DIR / f"{table_name}.parquet"
        if not p.exists():
            return []
        df = pd.read_parquet(p)
        sub = df[df["candidate_id"] == candidate_id]
        return sub.drop(columns=["candidate_id"], errors="ignore").fillna("").to_dict(orient="records")

    return {
        "profile": row.drop(columns=["embedding_text"], errors="ignore").fillna("").to_dict(orient="records")[0],
        "skills": _join_table("skills"),
        "education": _join_table("education"),
        "career_history": _join_table("career_history"),
        "certifications": _join_table("certifications"),
        "languages": _join_table("languages"),
    }


# ─────────────────────────────────────────────────────
# Dataset statistics
# ─────────────────────────────────────────────────────

@router.get("/stats", summary="Aggregate statistics over the loaded dataset")
def dataset_stats():
    profiles_path = OUTPUT_DIR / "profiles.parquet"
    if not profiles_path.exists():
        raise HTTPException(503, "Data not loaded.")

    df = pd.read_parquet(profiles_path)
    skills_path = OUTPUT_DIR / "skills.parquet"

    stats: Dict[str, Any] = {
        "total_candidates": len(df),
        "open_to_work": int(df["open_to_work_flag"].sum()),
        "avg_years_experience": round(float(df["years_of_experience"].mean()), 2),
        "avg_profile_completeness": round(float(df["profile_completeness_score"].mean()), 2),
        "countries": df["country"].value_counts().head(10).to_dict(),
        "work_mode_distribution": df["preferred_work_mode"].value_counts().to_dict(),
        "willing_to_relocate": int(df["willing_to_relocate"].sum()),
        "verified_email": int(df["verified_email"].sum()),
        "verified_phone": int(df["verified_phone"].sum()),
        "linkedin_connected": int(df["linkedin_connected"].sum()),
        "avg_notice_period_days": round(float(df["notice_period_days"].mean()), 1),
        "avg_recruiter_response_rate": round(float(df["recruiter_response_rate"].mean()), 3),
        "avg_interview_completion_rate": round(float(df["interview_completion_rate"].mean()), 3),
        "yoe_distribution": {
            "0-2": int((df["years_of_experience"] < 2).sum()),
            "2-5": int(((df["years_of_experience"] >= 2) & (df["years_of_experience"] < 5)).sum()),
            "5-10": int(((df["years_of_experience"] >= 5) & (df["years_of_experience"] < 10)).sum()),
            "10-15": int(((df["years_of_experience"] >= 10) & (df["years_of_experience"] < 15)).sum()),
            "15+": int((df["years_of_experience"] >= 15).sum()),
        },
    }

    if skills_path.exists():
        skills_df = pd.read_parquet(skills_path, columns=["skill_name", "proficiency", "endorsements"])
        stats["total_skill_entries"] = len(skills_df)
        stats["top_skills"] = skills_df["skill_name"].value_counts().head(20).to_dict()
        stats["proficiency_distribution"] = skills_df["proficiency"].value_counts().to_dict()

    return stats


# ─────────────────────────────────────────────────────
# Cache management
# ─────────────────────────────────────────────────────

@router.delete("/load/cache", summary="Delete Parquet cache (triggers fresh reload on next run)")
def delete_cache():
    global _load_result, _progress_pct, _progress_msg
    deleted = []
    for pq_file in OUTPUT_DIR.glob("*.parquet"):
        pq_file.unlink()
        deleted.append(pq_file.name)
    _load_result = None
    _progress_pct = 0.0
    _progress_msg = "Cache cleared."
    return {"deleted": deleted, "message": "Cache cleared. POST /api/load/file to reload."}


# ─────────────────────────────────────────────────────
# Background worker
# ─────────────────────────────────────────────────────

def _update_progress(pct: float, msg: str):
    global _progress_pct, _progress_msg
    _progress_pct = pct
    _progress_msg = msg


def _run_load(source: Path, chunk_size: int, force: bool):
    global _load_result, _is_running, _progress_pct, _progress_msg
    _is_running = True
    _progress_pct = 0.0
    _progress_msg = f"Starting load of {source.name}…"
    try:
        result = load_jsonl(
            source=source,
            output_dir=OUTPUT_DIR,
            chunk_size=chunk_size,
            force=force,
            progress_callback=_update_progress,
        )
        _load_result = result
        # Update app_state so ranking pipeline can use the data
        app_state.processing_status = "idle"
        app_state.processing_message = (
            f"Loaded {result.valid_records:,} candidates in {result.elapsed_seconds:.1f}s"
        )
        app_state.total_candidates = result.valid_records
        _progress_pct = 100.0
        _progress_msg = app_state.processing_message
    except Exception as exc:
        logger.error("Load failed: %s", exc, exc_info=True)
        _progress_msg = f"Error: {exc}"
        app_state.processing_status = "error"
        app_state.processing_message = str(exc)
    finally:
        _is_running = False


# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────

def _available_tables() -> List[str]:
    return [p.stem for p in OUTPUT_DIR.glob("*.parquet")]
