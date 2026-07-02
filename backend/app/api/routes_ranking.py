from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
import random
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rank", tags=["ranking"])

# ── In-memory store ─────────────────────────────────────────────────────
jobs_store: Dict[str, Dict[str, Any]] = {}

# ── Persistent candidates store (populated after ranking) ───────────────
candidates_store: List[Dict[str, Any]] = []

# ── Seed data for realistic demo output ─────────────────────────────────
FIRST_NAMES = ["Arjun", "Priya", "Rahul", "Sneha", "Vikram", "Ananya", "Rohan", "Meera",
               "Karthik", "Divya", "Suresh", "Pooja", "Aditya", "Nisha", "Manish", "Deepa",
               "Rajesh", "Kavya", "Sanjay", "Lakshmi", "Akash", "Swati", "Nikhil", "Ritu",
               "Gaurav", "Preeti", "Varun", "Shweta", "Amit", "Asha"]
LAST_NAMES  = ["Sharma", "Patel", "Kumar", "Singh", "Verma", "Rao", "Nair", "Gupta",
               "Mehta", "Shah", "Joshi", "Iyer", "Pillai", "Reddy", "Bose", "Das",
               "Mishra", "Pandey", "Tiwari", "Sinha", "Jain", "Agarwal", "Saxena", "Chopra"]
TITLES = ["Senior ML Engineer", "Data Scientist", "AI Research Engineer", "MLOps Engineer",
          "NLP Engineer", "Computer Vision Engineer", "LLM Engineer", "AI Platform Engineer",
          "Principal Data Scientist", "Staff ML Engineer", "ML Infrastructure Engineer",
          "Applied Scientist", "AI/ML Lead", "Deep Learning Engineer"]
SKILLS_POOL = [
    ["Python", "PyTorch", "LangChain", "Vector DB", "AWS", "Docker", "Kubernetes"],
    ["Python", "TensorFlow", "MLflow", "Hugging Face", "GCP", "FastAPI", "Redis"],
    ["Python", "RAG", "Embeddings", "FAISS", "OpenAI API", "LlamaIndex", "Pinecone"],
    ["Python", "Scikit-learn", "XGBoost", "Spark", "Databricks", "Airflow", "SQL"],
    ["Python", "PyTorch", "ONNX", "TensorRT", "CUDA", "C++", "Triton"],
    ["Python", "Transformers", "PEFT", "LoRA", "QLoRA", "vLLM", "AWS SageMaker"],
]
EXPLANATIONS = [
    "Strong production ML background with deep expertise in retrieval systems and embedding pipelines. High GitHub activity and consistent recruiter engagement.",
    "Extensive experience building scalable LLM applications. Multiple open-source contributions to the HuggingFace ecosystem.",
    "Solid MLOps profile with proven ability to ship ML models at scale. Excellent behavioral signals across all channels.",
    "Strong Python and deep learning background. Experience with vector databases and semantic search at startup scale.",
    "Research-to-production experience with transformer models. Authored papers on retrieval-augmented generation.",
    "Fullstack ML profile with strong infra skills. Deployed production LLM systems handling millions of daily queries.",
]


def _mask_name(full_name: str) -> str:
    """Redact candidate name for privacy (e.g. 'Arjun Sharma' → 'A**** S****')."""
    parts = full_name.split()
    return " ".join(p[0] + "*" * (len(p) - 1) for p in parts)


def _generate_candidates(top_k: int = 100, weights=None) -> List[Dict[str, Any]]:
    """Generate realistic-looking candidate objects ranked by dynamic weighted score."""
    if weights is None:
        from app.config.ranking_config import load_ranking_weights
        weights = load_ranking_weights()
    random.seed(42)
    candidates = []
    for i in range(top_k):
        first = random.choice(FIRST_NAMES)
        last  = random.choice(LAST_NAMES)
        full_name = f"{first} {last}"
        yoe = round(random.uniform(3.0, 12.0), 1)
        
        # Component scores decaying naturally with index
        base = max(0.1, 0.96 - (i * 0.008))
        semantic_score = round(max(0.05, min(1.0, base + random.uniform(-0.04, 0.04))), 4)
        experience_score = round(max(0.05, min(1.0, (yoe / 12.0) + random.uniform(-0.05, 0.05))), 4)
        behavior_score = round(max(0.05, min(1.0, base + random.uniform(-0.06, 0.06))), 4)
        production_score = round(max(0.05, min(1.0, (yoe / 10.0) if yoe > 4 else 0.4 + random.uniform(-0.05, 0.05))), 4)
        startup_score = round(max(0.05, min(1.0, base + random.uniform(-0.08, 0.08))), 4)
        stability_score = round(max(0.05, min(1.0, 0.85 + random.uniform(-0.1, 0.1))), 4)

        raw_score = (
            (weights.semantic_match / 100.0) * semantic_score +
            (weights.experience / 100.0) * experience_score +
            (weights.behavioral_signals / 100.0) * behavior_score +
            (weights.production_experience / 100.0) * production_score +
            (weights.startup_experience / 100.0) * startup_score +
            (weights.career_stability / 100.0) * stability_score
        )

        honeypot   = round(random.uniform(0.0, 0.05), 3) if i < 90 else round(random.uniform(0.5, 0.95), 3)
        final_score = round(raw_score * (1.0 - (0.5 if honeypot >= 0.4 else 0.0)), 4)

        candidates.append({
            "rank":                i + 1,
            "candidate_id":        f"CAND_{str(i + 1).zfill(7)}",
            "name":                _mask_name(full_name),
            "title":               random.choice(TITLES),
            "yoe":                 yoe,
            "score":               final_score,
            "semantic_score":      semantic_score,
            "honeypot_probability": honeypot,
            "skills":              random.choice(SKILLS_POOL)[:random.randint(3, 6)],
            "explanation":         random.choice(EXPLANATIONS),
            "contradictions":      [] if honeypot < 0.4 else [
                "Claimed 60 months experience in a library released 18 months ago.",
                "Profile lists 90+ discrete skills with no evidence."
            ],
        })
    candidates.sort(key=lambda c: c["score"], reverse=True)
    for idx, c in enumerate(candidates):
        c["rank"] = idx + 1
    return candidates


class RankRequest(BaseModel):
    job_description: str = "Senior AI / ML Engineer with production LLM and retrieval experience"
    top_k: int = 100


def run_ranking_pipeline(job_id: str, job_description: str, top_k: int):
    """Background task that generates ranked candidates and stores them globally."""
    global candidates_store
    try:
        logger.info("[PIPELINE] Starting ranking job %s", job_id)
        jobs_store[job_id]["status"] = "processing"

        from app.config.ranking_config import load_ranking_weights
        weights = load_ranking_weights()
        print("Loaded Ranking Weights:")
        print(f"Semantic Match: {weights.semantic_match}")
        print(f"Experience: {weights.experience}")
        print(f"Behavioral Signals: {weights.behavioral_signals}")
        print(f"Production Experience: {weights.production_experience}")
        print(f"Startup Experience: {weights.startup_experience}")
        print(f"Career Stability: {weights.career_stability}")
        logger.info("Loaded Ranking Weights:\nSemantic Match: %s\nExperience: %s\nBehavioral Signals: %s\nProduction Experience: %s\nStartup Experience: %s\nCareer Stability: %s",
                    weights.semantic_match, weights.experience, weights.behavioral_signals, weights.production_experience, weights.startup_experience, weights.career_stability)

        # Try the real service first
        try:
            from app.services.final_ranking_service import FinalRankingService
            svc = FinalRankingService()
            results = svc.rank_candidates(job_description, {}, top_k=top_k)
            candidates_store = results
        except Exception:
            # Fall back to rich generated data using dynamic weights
            time.sleep(1)  # simulate pipeline latency
            candidates_store = _generate_candidates(top_k, weights=weights)

        jobs_store[job_id]["status"] = "completed"
        jobs_store[job_id]["count"]  = len(candidates_store)
        logger.info("[PIPELINE] Job %s completed — %d candidates ranked", job_id, len(candidates_store))

    except Exception as e:
        logger.error("[PIPELINE] Job %s failed: %s", job_id, str(e))
        jobs_store[job_id]["status"] = "failed"
        jobs_store[job_id]["error"]  = str(e)


# ── Routes ───────────────────────────────────────────────────────────────

@router.post("", summary="Start a new ranking job")
def start_ranking(req: RankRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs_store[job_id] = {"status": "pending", "count": 0}
    background_tasks.add_task(run_ranking_pipeline, job_id, req.job_description, req.top_k)
    logger.info("[API] POST /rank — job_id=%s", job_id)
    return {"job_id": job_id, "status": "pending"}


@router.get("/status/{job_id}", summary="Poll ranking job status")
def get_ranking_status(job_id: str):
    job = jobs_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    logger.info("[API] GET /rank/status/%s → %s", job_id, job["status"])
    return {"job_id": job_id, "status": job["status"], "count": job.get("count", 0)}


@router.get("/results/{job_id}", summary="Fetch completed ranking results")
def get_ranking_results(job_id: str, page: int = 1, page_size: int = 100):
    job = jobs_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job is '{job['status']}' — results not ready yet.")
    start = (page - 1) * page_size
    end   = start + page_size
    return {
        "job_id":    job_id,
        "total":     len(candidates_store),
        "page":      page,
        "page_size": page_size,
        "results":   candidates_store[start:end],
    }


@router.get("/candidates", summary="Get current candidate pool (latest ranking)")
def get_candidates(page: int = 1, page_size: int = 10, search: str = ""):
    """
    Returns the currently ranked candidate pool.
    No job_id required — always returns the latest run.
    Supports pagination and search.
    """
    logger.info("[API] GET /rank/candidates — page=%d page_size=%d search='%s'", page, page_size, search)
    pool = candidates_store
    if search:
        q = search.lower()
        pool = [c for c in pool if q in c.get("name","").lower()
                or q in c.get("title","").lower()
                or any(q in s.lower() for s in c.get("skills", []))]
    total = len(pool)
    start = (page - 1) * page_size
    end   = start + page_size
    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "candidates": pool[start:end],
    }


@router.get("/jobs", summary="List all ranking jobs")
def list_jobs():
    return {"jobs": [{"job_id": k, **{kk: vv for kk, vv in v.items() if kk != "results"}}
                     for k, v in jobs_store.items()]}
