"""
Unit tests for the BM25 Retrieval Service.
"""
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.bm25_retrieval_service import BM25RetrievalService

class TestBM25RetrievalService:
    def setup_method(self):
        self.service = BM25RetrievalService()
        self.service.index_path = Path("test_bm25_index.pkl")
        
        self.candidate_ids = ["CAND_1", "CAND_2", "CAND_3"]
        # Index includes: headline, summary, skills, career descriptions, certifications.
        self.corpus = [
            "Senior Software Engineer Python Django AWS Docker",
            "Data Scientist Machine Learning Python PyTorch SQL",
            "Frontend Developer React Next.js Tailwind CSS HTML"
        ]

    def teardown_method(self):
        if self.service.index_path.exists():
            self.service.index_path.unlink()

    def test_fit_and_retrieve(self):
        self.service.fit(self.candidate_ids, self.corpus)
        
        # Test exact term match
        results = self.service.get_top_k("Python AWS", top_k=2)
        
        assert len(results) == 2
        
        # Check dictionary schema
        assert "candidate_id" in results[0]
        assert "bm25_score" in results[0]
        
        # Candidate 1 should have highest score for "Python AWS"
        assert results[0]["candidate_id"] == "CAND_1"
        assert results[1]["candidate_id"] == "CAND_2"
        
    def test_save_and_load(self):
        self.service.fit(self.candidate_ids, self.corpus)
        self.service.save_index()
        
        assert self.service.index_path.exists()
        
        # Create fresh service and load
        new_service = BM25RetrievalService()
        new_service.index_path = self.service.index_path
        new_service.load_index()
        
        results = new_service.get_top_k("PyTorch")
        assert len(results) == 1
        assert results[0]["candidate_id"] == "CAND_2"


if __name__ == "__main__":
    test_classes = [TestBM25RetrievalService]
    passed = failed = 0
    print("\n" + "═" * 60)
    print("  BM25RetrievalService — Unit Tests")
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
