"""
Unit tests for the Feature Engineering Service.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.feature_engineering import FeatureEngineeringService

class TestFeatureEngineeringService:
    def setup_method(self):
        self.candidate = {
            "profile": {
                "years_of_experience": 5.0,
                "current_title": "Senior Machine Learning Engineer",
                "summary": "Worked at a startup doing AI.",
                "country": "India"
            },
            "skills": [
                {"name": "Python"},
                {"name": "PyTorch"},
                {"name": "Docker"},
                {"name": "Pinecone"},
                {"name": "BM25"}
            ],
            "career_history": [
                {"duration_months": 24},
                {"duration_months": 36}
            ],
            "redrob_signals": {
                "github_activity_score": 0.9,
                "open_to_work": True,
                "notice_period_days": 15
            }
        }
        
        self.jd = {
            "must_have_skills": ["Python", "PyTorch", "Kubernetes"],
            "required_experience_min": 3.0,
            "required_experience_max": 7.0,
            "seniority_level": "senior"
        }

    def test_feature_generation(self):
        features = FeatureEngineeringService.generate_features(
            candidate=self.candidate,
            jd_requirements=self.jd,
            bm25_score=0.8,
            embedding_score=0.9
        )
        
        # Semantic
        assert features.bm25_score == 0.8
        assert features.embedding_similarity == 0.9
        assert features.skill_overlap_score == 2.0 / 3.0  # Python, PyTorch matched, Kubernetes missing
        
        # Experience
        assert features.years_experience_score == 1.0  # 5 is between 3 and 7
        assert features.production_ml_score == 1.0  # Docker is present
        assert features.startup_score == 1.0
        
        # Skills
        assert features.vector_db_score == 1.0  # Pinecone
        assert features.retrieval_score == 1.0  # BM25
        assert features.python_score == 1.0
        assert features.open_source_score == 1.0  # Github > 0.5
        
        # Location
        assert features.india_score == 1.0
        
        # Behavioral
        assert features.open_to_work_score == 1.0
        assert features.notice_period_score == 1.0  # 15 days <= 30

    def test_empty_candidate(self):
        features = FeatureEngineeringService.generate_features({}, {})
        assert features.years_experience_score == 1.0
        assert features.skill_overlap_score == 1.0 # 0 / 0 defaults to 1.0

if __name__ == "__main__":
    test_classes = [TestFeatureEngineeringService]
    passed = failed = 0
    print("\n" + "═" * 60)
    print("  FeatureEngineeringService — Unit Tests")
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
