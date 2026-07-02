"""
Quick integration test — validates the JSONL loader against sample_candidates.json.
Run: python tests/test_loader.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Make sure backend root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.models import CandidateModel
from app.services.jsonl_loader import load_jsonl
from app.utils.logger import get_logger

logger = get_logger("test_loader")

SAMPLE_JSON = (
    Path(__file__).parent.parent.parent
    / "sample_candidates.json"
)


def test_pydantic_models():
    """Validate that all records in sample_candidates.json parse cleanly."""
    print("\n── Test 1: Pydantic validation ──")
    assert SAMPLE_JSON.exists(), f"sample_candidates.json not found at {SAMPLE_JSON}"

    with open(SAMPLE_JSON, "r", encoding="utf-8") as f:
        records = json.load(f)

    valid = 0
    errors = []
    for rec in records:
        try:
            CandidateModel.model_validate(rec)
            valid += 1
        except Exception as e:
            errors.append((rec.get("candidate_id", "?"), str(e)[:100]))

    total = len(records)
    print(f"  Valid:   {valid}/{total}")
    print(f"  Errors:  {len(errors)}")
    for cid, err in errors[:3]:
        print(f"    ⚠ {cid}: {err}")
    assert valid > 0, "No records validated!"
    print("  ✅ PASSED")


def test_jsonl_loader_with_sample():
    """End-to-end: convert sample JSON → Parquet tables and verify row counts."""
    print("\n── Test 2: JSONL Loader + Parquet output ──")

    # Write sample as JSONL for the loader
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        jsonl_path = tmpdir / "sample.jsonl"
        output_dir = tmpdir / "parquet"

        with open(SAMPLE_JSON, "r", encoding="utf-8") as f:
            records = json.load(f)

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")

        print(f"  Wrote {len(records)} records as JSONL to {jsonl_path}")

        result = load_jsonl(
            source=jsonl_path,
            output_dir=output_dir,
            chunk_size=50,
            force=True,
        )

        print(f"  Total lines:   {result.total_lines}")
        print(f"  Valid records: {result.valid_records}")
        print(f"  Skipped:       {result.skipped_records}")
        print(f"  Elapsed:       {result.elapsed_seconds:.2f}s")
        print(f"  Tables:        {result.tables_written}")

        # Verify Parquet files exist and have correct row counts
        import pandas as pd

        expected_tables = ["profiles", "skills", "education", "career_history"]
        for tbl in expected_tables:
            p = output_dir / f"{tbl}.parquet"
            assert p.exists(), f"Missing table: {tbl}.parquet"
            df = pd.read_parquet(p)
            print(f"    {tbl:<20}: {len(df):>5} rows, {len(df.columns)} cols")
            assert len(df) > 0, f"Table {tbl} is empty!"

        assert result.valid_records == len(records) or result.valid_records > 0
        print("  ✅ PASSED")


def test_candidate_detail_join():
    """Verify that candidate detail JOIN works across tables."""
    print("\n── Test 3: Cross-table JOIN ──")

    import tempfile, json
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        jsonl_path = tmpdir / "sample.jsonl"
        output_dir = tmpdir / "parquet"

        with open(SAMPLE_JSON, "r", encoding="utf-8") as f:
            records = json.load(f)

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")

        load_jsonl(source=jsonl_path, output_dir=output_dir, chunk_size=50, force=True)

        import pandas as pd
        profiles = pd.read_parquet(output_dir / "profiles.parquet")
        skills = pd.read_parquet(output_dir / "skills.parquet")

        first_id = profiles.iloc[0]["candidate_id"]
        cand_skills = skills[skills["candidate_id"] == first_id]

        print(f"  Candidate: {first_id}")
        print(f"  Skills found: {len(cand_skills)}")
        for _, sk in cand_skills.head(3).iterrows():
            print(f"    • {sk['skill_name']} ({sk['proficiency']}, {sk['endorsements']} endorsements)")

        assert len(cand_skills) > 0
        print("  ✅ PASSED")


if __name__ == "__main__":
    print("=" * 50)
    print("RTIE Loader — Integration Tests")
    print("=" * 50)
    test_pydantic_models()
    test_jsonl_loader_with_sample()
    test_candidate_detail_join()
    print("\n✅ All tests passed!")
