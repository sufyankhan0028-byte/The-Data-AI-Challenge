"""
Unit tests for the Submission Generator.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.submission_generator import SubmissionGenerator

class TestSubmissionGenerator:
    def setup_method(self):
        # We output to a test file in the local dir
        test_dir = Path(__file__).parent / "test_submission.csv"
        self.generator = SubmissionGenerator(output_path=str(test_dir))
        # Ensure we don't accidentally try to run validation on a fake file path in unit test
        self.generator.validator_path = Path("fake_validator.py")

    def teardown_method(self):
        if self.generator.output_path.exists():
            self.generator.output_path.unlink()

    def test_enforce_descending_and_unique(self):
        # Create dummy results with duplicates
        results = [
            {"candidate_id": "C2", "score": 8.0, "reasoning": "R2"},
            {"candidate_id": "C1", "score": 9.0, "reasoning": "R1"},
            {"candidate_id": "C1", "score": 9.0, "reasoning": "Duplicate"},
            {"candidate_id": "C3", "score": 7.0, "reasoning": "R3"},
        ]
        
        self.generator.generate(results)
        
        # Check generated file
        import csv
        with open(self.generator.output_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 3
            # Should be sorted: C1, C2, C3
            assert reader[0]["candidate_id"] == "C1"
            assert reader[0]["rank"] == "1"
            assert reader[1]["candidate_id"] == "C2"
            assert reader[1]["rank"] == "2"
            assert reader[2]["candidate_id"] == "C3"
            assert reader[2]["rank"] == "3"

    def test_exact_100(self):
        # Generate 150 unique candidates
        results = []
        for i in range(150):
            results.append({
                "candidate_id": f"C{i}",
                "score": float(150 - i),
                "reasoning": "Reason"
            })
            
        self.generator.generate(results)
        
        import csv
        with open(self.generator.output_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            # Must strictly truncate to exactly 100 rows
            assert len(reader) == 100


if __name__ == "__main__":
    test_classes = [TestSubmissionGenerator]
    passed = failed = 0
    print("\n" + "═" * 60)
    print("  SubmissionGenerator — Unit Tests")
    print("═" * 60)

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method_name in methods:
            instance.setup_method()
            try:
                getattr(instance, method_name)()
                print(f"    ✅ {method_name}")
                passed += 1
            except Exception as exc:
                print(f"    ❌ {method_name}")
                import traceback
                traceback.print_exc()
                failed += 1
            finally:
                instance.teardown_method()

    print("\n" + "─" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("─" * 60)
    if failed:
        sys.exit(1)
