"""
JSONL Candidate Loader — memory-efficient, streaming, normalized Parquet tables.

Produces 6 separate Parquet tables:
  profiles.parquet          — one row per candidate (core profile + signals)
  skills.parquet            — one row per (candidate × skill)
  education.parquet         — one row per (candidate × degree)
  career_history.parquet    — one row per (candidate × job)
  certifications.parquet    — one row per (candidate × cert)
  languages.parquet         — one row per (candidate × language)

Design decisions:
  • Streams JSONL line-by-line → never loads full file into RAM.
  • Validates each record with Pydantic; invalid lines are logged and skipped.
  • Flushes every CHUNK_SIZE records to Parquet to keep peak memory ~200 MB for 100k candidates.
  • Incremental append via pyarrow.parquet.write_to_dataset (partition-friendly).
  • Returns LoadResult with counts, skipped lines, and timing.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator, Iterator, List, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError
from tqdm import tqdm

from app.schemas.models import CandidateModel
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ─────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────

CHUNK_SIZE = 2_000          # records per flush
TQDM_MINITERS = 500         # tqdm update frequency


# ─────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────

@dataclass
class LoadResult:
    total_lines: int = 0
    valid_records: int = 0
    skipped_records: int = 0
    skip_log: List[dict] = field(default_factory=list)   # {line, reason}
    elapsed_seconds: float = 0.0
    output_dir: str = ""
    tables_written: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_lines == 0:
            return 0.0
        return self.valid_records / self.total_lines


# ─────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────

def load_jsonl(
    source: Path,
    output_dir: Path,
    chunk_size: int = CHUNK_SIZE,
    force: bool = False,
    progress_callback=None,   # optional callable(pct: float, msg: str)
) -> LoadResult:
    """
    Stream-parse source JSONL → 6 normalized Parquet tables in output_dir.

    Args:
        source:            Path to candidates.jsonl (or .json array).
        output_dir:        Directory where Parquet files are written.
        chunk_size:        Records per flush (tune for memory vs speed).
        force:             Re-process even if Parquet files already exist.
        progress_callback: Optional callable(pct, msg) for UI status updates.

    Returns:
        LoadResult with full statistics.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Skip if already processed
    profiles_parquet = output_dir / "profiles.parquet"
    if profiles_parquet.exists() and not force:
        logger.info("Parquet tables already exist. Use force=True to re-process.")
        existing = _count_existing(profiles_parquet)
        result = LoadResult(
            valid_records=existing,
            total_lines=existing,
            output_dir=str(output_dir),
            tables_written=_list_tables(output_dir),
        )
        if progress_callback:
            progress_callback(100.0, f"Loaded {existing:,} candidates from cache.")
        return result

    # Estimate line count for progress bar
    total_lines = _estimate_line_count(source)
    logger.info("Starting JSONL load: %s | estimated %d lines", source.name, total_lines)
    if progress_callback:
        progress_callback(0.0, f"Starting load of {source.name} (~{total_lines:,} records)…")

    result = LoadResult(output_dir=str(output_dir))
    t0 = time.perf_counter()

    # Delete old partial files
    for name in _TABLE_NAMES:
        p = output_dir / f"{name}.parquet"
        if p.exists():
            p.unlink()

    # Chunk buffers
    buffers: dict[str, list[dict]] = {name: [] for name in _TABLE_NAMES}

    writers: dict[str, Optional[pq.ParquetWriter]] = {name: None for name in _TABLE_NAMES}

    pbar = tqdm(
        _stream_lines(source),
        total=total_lines if total_lines > 0 else None,
        desc="Loading candidates",
        unit="rec",
        miniters=TQDM_MINITERS,
        dynamic_ncols=True,
    )

    for line_no, line in enumerate(pbar, start=1):
        result.total_lines += 1
        raw = line.strip()
        if not raw:
            continue

        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            _skip(result, line_no, f"JSON parse error: {exc}")
            continue

        try:
            candidate = CandidateModel.model_validate(obj)
        except ValidationError as exc:
            _skip(result, line_no, f"Validation error: {exc.error_count()} errors")
            continue

        cid = candidate.candidate_id
        _extract_rows(candidate, cid, buffers)
        result.valid_records += 1

        # Flush chunk
        if result.valid_records % chunk_size == 0:
            _flush(buffers, writers, output_dir)
            pct = min(result.valid_records / max(total_lines, 1) * 100, 99.0)
            msg = f"Processed {result.valid_records:,} / {total_lines:,} candidates…"
            pbar.set_postfix_str(f"valid={result.valid_records:,} skipped={result.skipped_records}")
            if progress_callback:
                progress_callback(pct, msg)

    # Final flush
    _flush(buffers, writers, output_dir)

    # Close all writers
    for w in writers.values():
        if w:
            w.close()

    result.elapsed_seconds = time.perf_counter() - t0
    result.tables_written = _list_tables(output_dir)

    logger.info(
        "Load complete: %d valid / %d total in %.1fs (%.0f rec/s) | skipped=%d",
        result.valid_records,
        result.total_lines,
        result.elapsed_seconds,
        result.valid_records / max(result.elapsed_seconds, 0.001),
        result.skipped_records,
    )
    if progress_callback:
        progress_callback(
            100.0,
            f"Done! {result.valid_records:,} candidates loaded in {result.elapsed_seconds:.1f}s.",
        )

    return result


# ─────────────────────────────────────────
# Table schemas
# ─────────────────────────────────────────

_TABLE_NAMES = [
    "profiles",
    "skills",
    "education",
    "career_history",
    "certifications",
    "languages",
]

_SCHEMAS: dict[str, pa.Schema] = {
    "profiles": pa.schema([
        pa.field("candidate_id", pa.string()),
        pa.field("anonymized_name", pa.string()),
        pa.field("headline", pa.string()),
        pa.field("summary", pa.string()),
        pa.field("location", pa.string()),
        pa.field("country", pa.string()),
        pa.field("years_of_experience", pa.float32()),
        pa.field("current_title", pa.string()),
        pa.field("current_company", pa.string()),
        pa.field("current_company_size", pa.string()),
        pa.field("current_industry", pa.string()),
        pa.field("cert_count", pa.int16()),
        pa.field("skill_count", pa.int16()),
        # redrob_signals (flattened)
        pa.field("profile_completeness_score", pa.float32()),
        pa.field("signup_date", pa.string()),
        pa.field("last_active_date", pa.string()),
        pa.field("open_to_work_flag", pa.bool_()),
        pa.field("profile_views_received_30d", pa.int32()),
        pa.field("applications_submitted_30d", pa.int32()),
        pa.field("recruiter_response_rate", pa.float32()),
        pa.field("avg_response_time_hours", pa.float32()),
        pa.field("connection_count", pa.int32()),
        pa.field("endorsements_received", pa.int32()),
        pa.field("notice_period_days", pa.int16()),
        pa.field("salary_min_lpa", pa.float32()),
        pa.field("salary_max_lpa", pa.float32()),
        pa.field("preferred_work_mode", pa.string()),
        pa.field("willing_to_relocate", pa.bool_()),
        pa.field("github_activity_score", pa.float32()),
        pa.field("search_appearance_30d", pa.int32()),
        pa.field("saved_by_recruiters_30d", pa.int32()),
        pa.field("interview_completion_rate", pa.float32()),
        pa.field("offer_acceptance_rate", pa.float32()),
        pa.field("verified_email", pa.bool_()),
        pa.field("verified_phone", pa.bool_()),
        pa.field("linkedin_connected", pa.bool_()),
        pa.field("avg_assessment_score", pa.float32()),
        pa.field("embedding_text", pa.string()),
    ]),
    "skills": pa.schema([
        pa.field("candidate_id", pa.string()),
        pa.field("skill_name", pa.string()),
        pa.field("proficiency", pa.string()),
        pa.field("endorsements", pa.int32()),
        pa.field("duration_months", pa.int32()),
        pa.field("assessment_score", pa.float32()),   # -1 if no assessment
    ]),
    "education": pa.schema([
        pa.field("candidate_id", pa.string()),
        pa.field("institution", pa.string()),
        pa.field("degree", pa.string()),
        pa.field("field_of_study", pa.string()),
        pa.field("start_year", pa.int16()),
        pa.field("end_year", pa.int16()),
        pa.field("grade", pa.string()),
        pa.field("tier", pa.string()),
    ]),
    "career_history": pa.schema([
        pa.field("candidate_id", pa.string()),
        pa.field("company", pa.string()),
        pa.field("title", pa.string()),
        pa.field("start_date", pa.string()),
        pa.field("end_date", pa.string()),
        pa.field("duration_months", pa.int32()),
        pa.field("is_current", pa.bool_()),
        pa.field("industry", pa.string()),
        pa.field("company_size", pa.string()),
        pa.field("description", pa.string()),
        pa.field("job_order", pa.int8()),
    ]),
    "certifications": pa.schema([
        pa.field("candidate_id", pa.string()),
        pa.field("cert_name", pa.string()),
        pa.field("issuer", pa.string()),
        pa.field("year", pa.int16()),
    ]),
    "languages": pa.schema([
        pa.field("candidate_id", pa.string()),
        pa.field("language", pa.string()),
        pa.field("proficiency", pa.string()),
    ]),
}


# ─────────────────────────────────────────
# Row extraction helpers
# ─────────────────────────────────────────

def _extract_rows(c: CandidateModel, cid: str, buffers: dict) -> None:
    """Decompose one validated CandidateModel into rows for each table buffer."""
    sig = c.redrob_signals
    assessments = sig.skill_assessment_scores

    # ── profiles ──
    avg_assess = (
        sum(assessments.values()) / len(assessments) if assessments else -1.0
    )
    embedding_text = _build_embedding_text(c)
    buffers["profiles"].append({
        "candidate_id": cid,
        "anonymized_name": c.profile.anonymized_name,
        "headline": c.profile.headline,
        "summary": c.profile.summary,
        "location": c.profile.location,
        "country": c.profile.country,
        "years_of_experience": c.profile.years_of_experience,
        "current_title": c.profile.current_title,
        "current_company": c.profile.current_company,
        "current_company_size": c.profile.current_company_size,
        "current_industry": c.profile.current_industry,
        "cert_count": len(c.certifications),
        "skill_count": len(c.skills),
        # signals
        "profile_completeness_score": sig.profile_completeness_score,
        "signup_date": sig.signup_date,
        "last_active_date": sig.last_active_date,
        "open_to_work_flag": sig.open_to_work_flag,
        "profile_views_received_30d": sig.profile_views_received_30d,
        "applications_submitted_30d": sig.applications_submitted_30d,
        "recruiter_response_rate": sig.recruiter_response_rate,
        "avg_response_time_hours": sig.avg_response_time_hours,
        "connection_count": sig.connection_count,
        "endorsements_received": sig.endorsements_received,
        "notice_period_days": sig.notice_period_days,
        "salary_min_lpa": sig.expected_salary_range_inr_lpa.min,
        "salary_max_lpa": sig.expected_salary_range_inr_lpa.max,
        "preferred_work_mode": sig.preferred_work_mode,
        "willing_to_relocate": sig.willing_to_relocate,
        "github_activity_score": sig.github_activity_score,
        "search_appearance_30d": sig.search_appearance_30d,
        "saved_by_recruiters_30d": sig.saved_by_recruiters_30d,
        "interview_completion_rate": sig.interview_completion_rate,
        "offer_acceptance_rate": sig.offer_acceptance_rate,
        "verified_email": sig.verified_email,
        "verified_phone": sig.verified_phone,
        "linkedin_connected": sig.linkedin_connected,
        "avg_assessment_score": avg_assess,
        "embedding_text": embedding_text,
    })

    # ── skills ──
    for skill in c.skills:
        assess_score = float(assessments.get(skill.name, -1.0))
        buffers["skills"].append({
            "candidate_id": cid,
            "skill_name": skill.name,
            "proficiency": skill.proficiency,
            "endorsements": skill.endorsements,
            "duration_months": skill.duration_months,
            "assessment_score": assess_score,
        })

    # ── education ──
    for edu in c.education:
        buffers["education"].append({
            "candidate_id": cid,
            "institution": edu.institution,
            "degree": edu.degree,
            "field_of_study": edu.field_of_study,
            "start_year": edu.start_year,
            "end_year": edu.end_year,
            "grade": edu.grade or "",
            "tier": edu.tier,
        })

    # ── career_history ──
    for i, job in enumerate(c.career_history):
        buffers["career_history"].append({
            "candidate_id": cid,
            "company": job.company,
            "title": job.title,
            "start_date": job.start_date,
            "end_date": job.end_date or "",
            "duration_months": job.duration_months,
            "is_current": job.is_current,
            "industry": job.industry,
            "company_size": job.company_size,
            "description": job.description,
            "job_order": i,
        })

    # ── certifications ──
    for cert in c.certifications:
        buffers["certifications"].append({
            "candidate_id": cid,
            "cert_name": cert.name,
            "issuer": cert.issuer,
            "year": cert.year,
        })

    # ── languages ──
    for lang in c.languages:
        buffers["languages"].append({
            "candidate_id": cid,
            "language": lang.language,
            "proficiency": lang.proficiency,
        })


def _build_embedding_text(c: CandidateModel) -> str:
    """Concatenate key text fields for sentence-transformer embedding."""
    skill_names = [s.name for s in c.skills[:20]]
    career_descs = [j.description for j in c.career_history[:2]]
    parts = [
        c.profile.headline,
        c.profile.summary[:500],
        c.profile.current_title,
        c.profile.current_industry,
        " ".join(skill_names),
        " ".join(career_descs),
    ]
    return " ".join(p for p in parts if p)[:2000]


# ─────────────────────────────────────────
# Flush logic
# ─────────────────────────────────────────

def _flush(
    buffers: dict[str, list[dict]],
    writers: dict[str, Optional[pq.ParquetWriter]],
    output_dir: Path,
) -> None:
    """Convert all non-empty buffers to PyArrow tables and append to Parquet writers."""
    for name, rows in buffers.items():
        if not rows:
            continue
        schema = _SCHEMAS[name]
        table = pa.Table.from_pydict(
            {col.name: [r[col.name] for r in rows] for col in schema},
            schema=schema,
        )
        path = output_dir / f"{name}.parquet"
        if writers[name] is None:
            writers[name] = pq.ParquetWriter(
                str(path),
                schema,
                compression="snappy",
                use_dictionary=True,
                write_statistics=True,
            )
        writers[name].write_table(table)
        rows.clear()


# ─────────────────────────────────────────
# Streaming / utility helpers
# ─────────────────────────────────────────

def _stream_lines(source: Path) -> Generator[str, None, None]:
    """
    Yield lines one at a time from a JSONL file.
    For .json array files, wraps each element on its own line.
    """
    suffix = source.suffix.lower()
    if suffix == ".jsonl":
        with open(source, "r", encoding="utf-8", buffering=1 << 20) as f:
            yield from f
    else:  # .json — assume array, stream array elements
        import ijson  # lazy import — only needed for JSON arrays
        with open(source, "rb") as f:
            for item in ijson.items(f, "item"):
                yield json.dumps(item)


def _estimate_line_count(source: Path) -> int:
    """Fast line count via 8KB block reads (avoids loading full file)."""
    try:
        count = 0
        with open(source, "rb") as f:
            while True:
                block = f.read(1 << 23)  # 8 MB
                if not block:
                    break
                count += block.count(b"\n")
        return count
    except Exception:
        return 0


def _skip(result: LoadResult, line_no: int, reason: str) -> None:
    result.skipped_records += 1
    if len(result.skip_log) < 200:  # keep first 200 errors only
        result.skip_log.append({"line": line_no, "reason": reason})
    if result.skipped_records % 500 == 0:
        logger.warning("Skipped %d records so far. Latest: line %d — %s", result.skipped_records, line_no, reason)


def _count_existing(parquet_path: Path) -> int:
    try:
        return pq.read_metadata(str(parquet_path)).num_rows
    except Exception:
        return 0


def _list_tables(output_dir: Path) -> list[str]:
    return [p.name for p in output_dir.glob("*.parquet")]
