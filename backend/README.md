# RTIE Backend — Candidate Loader Service

## Overview

Streams `candidates.jsonl` (100k candidates, ~487 MB) line-by-line into **6 normalized Parquet tables** using Pydantic v2 validation, PyArrow typed schemas, and chunked flushing. Peak memory stays under **~300 MB** regardless of file size.

## Architecture

```
candidates.jsonl
       │
       ▼  (streaming, 1 line at a time)
 Pydantic v2 validator
       │
       ├── invalid? → skip_log
       ▼
 Row extractor
       │
       ├── profiles row
       ├── skills rows      (1 per skill)
       ├── education rows   (1 per degree)
       ├── career_history   (1 per job)
       ├── certifications   (1 per cert)
       └── languages        (1 per lang)
       │
       ▼  (every 2,000 records)
 PyArrow typed flush → .parquet (Snappy compressed)
```

## Output Tables

| Table | Key columns | Notes |
|-------|-------------|-------|
| `profiles.parquet` | `candidate_id`, all profile + signal fields | 1 row per candidate |
| `skills.parquet` | `candidate_id`, `skill_name`, `proficiency`, `endorsements`, `assessment_score` | 1 row per skill |
| `education.parquet` | `candidate_id`, `institution`, `degree`, `tier` | 1 row per degree |
| `career_history.parquet` | `candidate_id`, `company`, `title`, `duration_months`, `job_order` | 1 row per role |
| `certifications.parquet` | `candidate_id`, `cert_name`, `issuer`, `year` | |
| `languages.parquet` | `candidate_id`, `language`, `proficiency` | |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/load/file` | Upload JSONL/JSON file → start background load |
| `POST` | `/api/load/path` | Load from server-side path |
| `GET` | `/api/load/status` | SSE live progress stream |
| `GET` | `/api/load/poll` | Single-request progress JSON |
| `GET` | `/api/load/result` | Final load statistics |
| `GET` | `/api/tables` | List all Parquet tables + metadata |
| `GET` | `/api/tables/{name}` | Paginated table preview |
| `GET` | `/api/candidates` | Search + filter candidates |
| `GET` | `/api/candidates/{id}` | Full candidate with all tables joined |
| `GET` | `/api/stats` | Aggregate dataset statistics |
| `DELETE` | `/api/load/cache` | Clear Parquet cache |
| `GET` | `/health` | Health check |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# --- OR ---

# 3. Load directly from CLI (no server needed)
python scripts/load_candidates.py --input ../candidates.jsonl --stats

# 4. Run tests against sample data
python tests/test_loader.py
```

## CLI Usage

```bash
python scripts/load_candidates.py \
  --input data/raw/candidates.jsonl \
  --output data/processed/ \
  --chunk 5000 \       # Records per Parquet flush
  --force \            # Re-process even if cache exists
  --stats              # Print dataset statistics after load
```

## Memory Profile

| Phase | Peak RAM |
|-------|----------|
| Streaming + validation | ~50 MB |
| Per-chunk buffer (2k records) | ~80 MB |
| PyArrow flush | ~100 MB |
| **Total peak** | **~250 MB** |

## Progress Tracking

**SSE stream** (connect once, get real-time updates):
```js
const es = new EventSource("http://localhost:8000/api/load/status");
es.onmessage = (e) => {
  const { pct, msg, valid, skipped } = JSON.parse(e.data);
  console.log(`${pct.toFixed(1)}% — ${msg}`);
};
```

**Polling** (simpler):
```bash
curl http://localhost:8000/api/load/poll
# {"pct": 45.2, "msg": "Processed 45,200 / 100,000 candidates…", "running": true}
```
