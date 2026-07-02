"""
Unit tests for the Honeypot Detector.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.honeypot_detector import HoneypotDetector

class TestHoneypotDetector:
    def setup_method(self):
        self.detector = HoneypotDetector()

    def test_impossible_timelines(self):
        # Langchain released 2022. Claiming 72 months (6 years) in 2026 is impossible.
        candidate = {
            "skills": [
                {"name": "LangChain", "duration_months": 72}
            ]
        }
        res = self.detector.detect(candidate)
        assert res["honeypot_probability"] >= 0.4
        assert any("Impossible profile" in r for r in res["reasons"])

    def test_synthetic_inconsistency(self):
        candidate = {
            "profile": {"current_title": "Frontend Developer"},
            "skills": [{"name": "Java"}, {"name": "Spring"}, {"name": "Docker"}]
        }
        res = self.detector.detect(candidate)
        assert res["honeypot_probability"] >= 0.3
        assert any("Synthetic inconsistency: Frontend title" in r for r in res["reasons"])

    def test_keyword_stuffing(self):
        candidate = {
            "profile": {"years_of_experience": 3.0},
            "skills": [{"name": f"Skill_{i}"} for i in range(80)]
        }
        res = self.detector.detect(candidate)
        assert res["honeypot_probability"] >= 0.2
        assert any("Keyword stuffing" in r for r in res["reasons"])

    def test_ai_buzzword_stuffing(self):
        candidate = {
            "skills": [
                {"name": "LangChain"}, {"name": "ChatGPT"}, {"name": "Prompt Engineering"}
            ] # No python or ML foundations
        }
        res = self.detector.detect(candidate)
        assert res["honeypot_probability"] >= 0.5
        assert any("AI buzzword stuffing" in r for r in res["reasons"])

    def test_clean_profile(self):
        candidate = {
            "profile": {
                "current_title": "Backend Engineer",
                "years_of_experience": 5.0
            },
            "career_history": [
                {"duration_months": 60}
            ],
            "skills": [
                {"name": "Java", "duration_months": 60},
                {"name": "Spring", "duration_months": 48},
                {"name": "Docker", "duration_months": 36}
            ]
        }
        res = self.detector.detect(candidate)
        assert res["honeypot_probability"] == 0.0
        assert len(res["reasons"]) == 0

if __name__ == "__main__":
    test_classes = [TestHoneypotDetector]
    passed = failed = 0
    print("\n" + "═" * 60)
    print("  HoneypotDetector — Unit Tests")
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
