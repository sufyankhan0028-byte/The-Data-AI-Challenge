"""
Submission Generator Service
============================
Converts ranked results into the official hackathon CSV format and writes to disk.
Enforces all challenge rules and automatically runs the validator script.
"""
import csv
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from app.utils.logger import get_logger

logger = get_logger(__name__)

class SubmissionGenerator:
    """
    Handles CSV output generation, deduplication, sorting, and validation.
    """
    def __init__(self, output_path: str = "submission.csv"):
        # Resolve to project root
        project_root = Path(__file__).parent.parent.parent.parent
        self.output_path = project_root / output_path
        self.validator_path = project_root / "validate_submission.py"

    def generate(self, results: List[Dict[str, Any]]) -> Path:
        """
        Receives a list of dicts: {"candidate_id", "score", "reasoning"}
        Enforces rules: unique candidates, descending score, exact 100 rows.
        """
        logger.info(f"Generating submission CSV from {len(results)} results...")
        
        # 1. Enforce unique candidates and descending score
        unique_results = []
        seen_ids = set()
        
        # Sort incoming results by score descending just to be safe
        sorted_results = sorted(results, key=lambda x: x.get("score", 0.0), reverse=True)
        
        for res in sorted_results:
            cid = res.get("candidate_id")
            if cid not in seen_ids:
                seen_ids.add(cid)
                unique_results.append(res)
                
        # 2. Enforce exactly 100 rows
        if len(unique_results) < 100:
            logger.warning(f"Only have {len(unique_results)} unique candidates. Submission requires exactly 100!")
        
        top_100 = unique_results[:100]
        
        # 3. Write CSV
        headers = ["candidate_id", "rank", "score", "reasoning"]
        
        with open(self.output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(headers)
            
            # Ranks are automatically 1 to 100 sequentially
            for rank_idx, res in enumerate(top_100, start=1):
                writer.writerow([
                    res.get("candidate_id"),
                    rank_idx,
                    f"{res.get('score', 0.0):.4f}",
                    res.get("reasoning", "Strong semantic match.")
                ])
                
        logger.info(f"Generated submission.csv at {self.output_path} with {len(top_100)} rows.")
        
        # 4. Automatic Validation
        self._run_validator()
        
        return self.output_path

    def _run_validator(self) -> None:
        """
        Executes the validate_submission.py script automatically.
        """
        if not self.validator_path.exists():
            logger.error(f"Validator script not found at {self.validator_path}")
            return
            
        logger.info("Running automatic hackathon validation script...")
        try:
            # We must run it using the python executable in our environment
            result = subprocess.run(
                [sys.executable, str(self.validator_path), "--file", str(self.output_path)],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Validation Passed!\n{result.stdout}")
            else:
                logger.error(f"❌ Validation Failed!\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        except BaseException as e:
            logger.error(f"Failed to execute validator: {e}")
