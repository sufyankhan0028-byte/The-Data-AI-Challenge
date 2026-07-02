"""
Unit tests for the Candidate Contradiction Detector.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.contradiction_detector import CandidateContradictionDetector

class TestCandidateContradictionDetector:
    def setup_method(self):
        self.detector = CandidateContradictionDetector()

    def test_marketing_manager_advanced_ai(self):
        candidate = {
            "profile": {"current_title": "Marketing Manager"},
            "skills": [
                {"name": "PyTorch", "proficiency": "advanced"}
            ]
        }
        res = self.detector.detect(candidate)
        assert res["contradiction_score"] >= 0.3
        assert "Anomalous skillset: Marketing title with advanced AI framework skills." in res["reasons"]

    def test_unrealistic_experience(self):
        candidate = {
            "profile": {"years_of_experience": 15.0},
            "career_history": [
                {"duration_months": 24} # Only 2 years of jobs
            ]
        }
        res = self.detector.detect(candidate)
        assert res["contradiction_score"] >= 0.3
        assert any("Unrealistic experience claim" in r for r in res["reasons"])

    def test_unrealistic_skill_duration(self):
        candidate = {
            "skills": [
                {"name": "LangChain", "duration_months": 60} # 5 years in LangChain is impossible
            ]
        }
        res = self.detector.detect(candidate)
        assert res["contradiction_score"] >= 0.5
        assert any("LangChain" in r for r in res["reasons"])

    def test_education_timeline_anomaly(self):
        candidate = {
            "education": [
                {"start_year": 2020, "end_year": 2018}
            ]
        }
        res = self.detector.detect(candidate)
        assert res["contradiction_score"] >= 0.3
        assert any("Education anomaly" in r for r in res["reasons"])

    def test_senior_title_beginner_skills(self):
        candidate = {
            "profile": {"current_title": "Senior AI Engineer"},
            "skills": [
                {"name": "Python", "proficiency": "beginner", "duration_months": 6},
                {"name": "PyTorch", "proficiency": "beginner", "duration_months": 12}
            ]
        }
        res = self.detector.detect(candidate)
        assert res["contradiction_score"] >= 0.4
        assert any("Contradictory seniority" in r for r in res["reasons"])
        
    def test_clean_profile(self):
        candidate = {
            "profile": {
                "current_title": "Senior Data Scientist",
                "years_of_experience": 5.0
            },
            "career_history": [
                {"title": "Data Scientist", "duration_months": 36},
                {"title": "Senior Data Scientist", "duration_months": 24}
            ],
            "skills": [
                {"name": "Python", "proficiency": "advanced", "duration_months": 60},
                {"name": "PyTorch", "proficiency": "advanced", "duration_months": 48}
            ],
            "education": [
                {"start_year": 2016, "end_year": 2020}
            ]
        }
        res = self.detector.detect(candidate)
        assert res["contradiction_score"] == 0.0
        assert len(res["reasons"]) == 0


if __name__ == "__main__":
    test_classes = [TestCandidateContradictionDetector]
    passed = failed = 0
    print("\n" + "═" * 60)
    print("  CandidateContradictionDetector — Unit Tests")
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

    print("\n" + "─" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("─" * 60)
    if failed:
        sys.exit(1)
