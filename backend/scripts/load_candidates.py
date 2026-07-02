#!/usr/bin/env python3
"""
Standalone CLI script to pre-process candidates.jsonl → Parquet tables.

Usage:
    python scripts/load_candidates.py --input data/raw/candidates.jsonl
    python scripts/load_candidates.py --input data/raw/candidates.jsonl --force --chunk 5000
    python scripts/load_candidates.py --input data/raw/candidates.jsonl --stats
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure backend/app is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.jsonl_loader import load_jsonl
from app.utils.logger import get_logger

logger = get_logger("load_candidates")


def main():
    parser = argparse.ArgumentParser(
        description="Stream-load candidates JSONL → normalized Parquet tables"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=settings.RAW_DIR / "candidates.jsonl",
        help="Path to candidates.jsonl (default: data/raw/candidates.jsonl)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=settings.PROCESSED_DIR,
        help="Output directory for Parquet tables (default: data/processed/)",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-process even if Parquet cache exists",
    )
    parser.add_argument(
        "--chunk", "-c",
        type=int,
        default=2_000,
        help="Records per Parquet flush (default: 2000)",
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Print dataset statistics after loading",
    )
    args = parser.parse_args()

    if not args.input.exists():
        logger.error("Input file not found: %s", args.input)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("RTIE Candidate Loader")
    logger.info("  Input:  %s (%.1f MB)", args.input, args.input.stat().st_size / 1e6)
    logger.info("  Output: %s", args.output)
    logger.info("  Force:  %s | Chunk: %d", args.force, args.chunk)
    logger.info("=" * 60)

    def progress(pct: float, msg: str):
        bar_len = 40
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r  [{bar}] {pct:5.1f}%  {msg[:60]:<60}", end="", flush=True)
        if pct >= 100:
            print()

    t0 = time.perf_counter()
    result = load_jsonl(
        source=args.input,
        output_dir=args.output,
        chunk_size=args.chunk,
        force=args.force,
        progress_callback=progress,
    )
    elapsed = time.perf_counter() - t0

    print()
    print("─" * 60)
    print(f"  ✅ Valid records  : {result.valid_records:>10,}")
    print(f"  ⏭  Skipped        : {result.skipped_records:>10,}")
    print(f"  📄 Total lines    : {result.total_lines:>10,}")
    print(f"  ⚡ Success rate   : {result.success_rate*100:>9.2f}%")
    print(f"  ⏱  Elapsed        : {elapsed:>9.1f}s")
    print(f"  🚀 Throughput     : {result.valid_records/max(elapsed,0.001):>9.0f} rec/s")
    print("─" * 60)
    print("  Tables written:")
    for tbl in sorted(result.tables_written):
        p = args.output / tbl
        size_mb = p.stat().st_size / 1e6 if p.exists() else 0
        print(f"    • {tbl:<30} {size_mb:6.1f} MB")
    print("─" * 60)

    if result.skip_log:
        print(f"\n  ⚠ First {min(5, len(result.skip_log))} skipped lines:")
        for entry in result.skip_log[:5]:
            print(f"    Line {entry['line']:>6}: {entry['reason'][:80]}")

    if args.stats:
        _print_stats(args.output)


def _print_stats(output_dir: Path):
    import pandas as pd
    print("\n" + "=" * 60)
    print("  Dataset Statistics")
    print("=" * 60)
    try:
        df = pd.read_parquet(output_dir / "profiles.parquet")
        print(f"  Total candidates      : {len(df):,}")
        print(f"  Open to work          : {df['open_to_work_flag'].sum():,}")
        print(f"  Avg YoE               : {df['years_of_experience'].mean():.2f}")
        print(f"  Avg completeness      : {df['profile_completeness_score'].mean():.1f}%")
        print(f"  Work modes:")
        for mode, cnt in df["preferred_work_mode"].value_counts().items():
            print(f"    {mode:<12}: {cnt:,}")
        print(f"  Top countries:")
        for country, cnt in df["country"].value_counts().head(5).items():
            print(f"    {country:<20}: {cnt:,}")
    except Exception as e:
        print(f"  Could not compute stats: {e}")

    try:
        skills_df = pd.read_parquet(output_dir / "skills.parquet")
        print(f"\n  Total skill entries   : {len(skills_df):,}")
        print(f"  Top 10 skills:")
        for skill, cnt in skills_df["skill_name"].value_counts().head(10).items():
            print(f"    {skill:<30}: {cnt:,}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
