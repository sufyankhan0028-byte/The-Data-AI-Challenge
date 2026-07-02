"""
Unit tests for the Final Ranking Service.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.final_ranking_service import FinalRankingService

class TestFinalRankingService:
    def setup_method(self):
        # Mock HybridRetrievalService
        self.mock_retrieval = MagicMock()
        self.mock_retrieval.retrieve.return_value = [
            {"candidate_id": "C1", "bm25_score": 0.8, "embedding_score": 0.9, "hybrid_score": 0.86},
            {"candidate_id": "FRAUD", "bm25_score": 0.5, "embedding_score": 0.5, "hybrid_score": 0.5},
        ]
        
        # We pass a fake ranker model path so it falls back gracefully in tests
        self.service = FinalRankingService(
            hybrid_retrieval_service=self.mock_retrieval,
            ranker_model_path="fake_path.pkl"
        )
        
        self.jd = {"must_have_skills": ["Python"]}
        self.db = {
            "C1": {
                "profile": {"years_of_experience": 5.0, "current_title": "Engineer"},
                "skills": [{"name": "Python"}],
                "career_history": [{"duration_months": 60}]
            },
            "FRAUD": {
                "profile": {"years_of_experience": 3.0, "current_title": "Marketing Manager"},
                "skills": [{"name": "PyTorch", "proficiency": "advanced"}], # Matches Fraud Rule 1
                "career_history": [{"duration_months": 36}]
            }
        }

    def test_ranking_orchestration(self):
        results = self.service.rank_candidates(self.jd, self.db, top_k=100)
        
        assert len(results) == 1
        assert results[0]["candidate_id"] == "C1"
        assert "feature_breakdown" in results[0]
        assert results[0]["feature_breakdown"]["python_score"] == 1.0
        
        # FRAUD should be dropped by the firewall (contradiction > 0.4)
        ids = [r["candidate_id"] for r in results]
        assert "FRAUD" not in ids


if __name__ == "__main__":
    test_classes = [TestFinalRankingService]
    passed = failed = 0
    print("\n" + "═" * 60)
    print("  FinalRankingService — Unit Tests")
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
