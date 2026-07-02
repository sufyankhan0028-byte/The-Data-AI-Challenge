"""
Unit tests for the Pseudo Label Generator.
"""
import sys
import os
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.pseudo_label_generator import PseudoLabelGenerator

class TestPseudoLabelGenerator:
    def setup_method(self):
        # Redirect output to test temp file
        temp_path = Path(__file__).parent / "test_pseudo_labels.csv"
        self.generator = PseudoLabelGenerator(output_path=str(temp_path))
        self.mock_jd = {
            "must_have_skills": ["Python", "Machine Learning"]
        }
        
    def teardown_method(self):
        if self.generator.output_path.exists():
            self.generator.output_path.unlink()

    def test_fraud_label_zero(self):
        # Even if hybrid score is perfect, fraud should force label 0
        candidates = [
            {
                "candidate": {
                    "candidate_id": "FRAUD_1",
                    "skills": [{"name": "LangChain", "duration_months": 80}] # Impossible timeline -> honeypot score high
                },
                "hybrid_score": 1.0 
            }
        ]
        
        self.generator.generate_labels(candidates, self.mock_jd)
        
        assert self.generator.output_path.exists()
        with open(self.generator.output_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 1
            assert reader[0]["label"] == "0"
            assert reader[0]["candidate_id"] == "FRAUD_1"
            assert float(reader[0]["honeypot_score"]) >= 0.4

    def test_excellent_label(self):
        # Great semantic match + great production ML experience
        candidates = [
            {
                "candidate": {
                    "candidate_id": "EXC_1",
                    "skills": [{"name": "Docker"}, {"name": "Kubernetes"}, {"name": "Python"}]
                },
                "hybrid_score": 0.95
            }
        ]
        
        self.generator.generate_labels(candidates, self.mock_jd)
        
        with open(self.generator.output_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert reader[0]["label"] == "3"
            assert reader[0]["candidate_id"] == "EXC_1"

    def test_average_label(self):
        # Average semantic match (0.5), no production experience
        candidates = [
            {
                "candidate": {
                    "candidate_id": "AVG_1",
                    "skills": [{"name": "HTML"}, {"name": "CSS"}]
                },
                "hybrid_score": 0.5
            }
        ]
        
        self.generator.generate_labels(candidates, self.mock_jd)
        
        with open(self.generator.output_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert reader[0]["label"] == "1"
            assert reader[0]["candidate_id"] == "AVG_1"

if __name__ == "__main__":
    test_classes = [TestPseudoLabelGenerator]
    passed = failed = 0
    print("\n" + "═" * 60)
    print("  PseudoLabelGenerator — Unit Tests")
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
