"""
Unit tests for the EmbeddingService.
Run standalone: python tests/test_embedding_service.py
Run with pytest: pytest tests/test_embedding_service.py -v
"""
from __future__ import annotations

import json
import shutil
import sys
import traceback
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

# Create a temporary directory for tests
TEST_EMBEDDINGS_DIR = Path(__file__).parent / "test_data" / "embeddings"

# Patch the config directory BEFORE importing EmbeddingService
settings.EMBEDDINGS_DIR = TEST_EMBEDDINGS_DIR

from app.services.embedding_service import EmbeddingService


class TestEmbeddingService:
    def setup_method(self):
        # Ensure test directory is clean
        if TEST_EMBEDDINGS_DIR.exists():
            shutil.rmtree(TEST_EMBEDDINGS_DIR)
        TEST_EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Reset singleton instance between tests
        EmbeddingService._instance = None

        # Create dummy data
        self.df1 = pd.DataFrame({
            "candidate_id": ["C1", "C2", "C3"],
            "unified_text": ["text1", "text2", "text3"]
        })

        self.df2 = pd.DataFrame({
            "candidate_id": ["C2", "C3", "C4", "C5"],
            "unified_text": ["text2", "text3", "text4", "text5"]
        })

    def teardown_method(self):
        if TEST_EMBEDDINGS_DIR.exists():
            shutil.rmtree(TEST_EMBEDDINGS_DIR)

    @patch("app.services.embedding_service.SentenceTransformer")
    def test_singleton_initialization(self, mock_st):
        s1 = EmbeddingService()
        s2 = EmbeddingService()
        assert s1 is s2
        assert mock_st.call_count == 1  # Should only init the model once

    @patch("app.services.embedding_service.SentenceTransformer")
    def test_embed_query(self, mock_st):
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_st.return_value = mock_model

        service = EmbeddingService()
        result = service.embed_query("Data Scientist with Python")
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)
        mock_model.encode.assert_called_once_with(
            "Data Scientist with Python",
            batch_size=1,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

    @patch("app.services.embedding_service.SentenceTransformer")
    def test_embed_candidates_incremental(self, mock_st):
        mock_model = MagicMock()
        # Mock encode to return a matrix of shape (N, 384) where N is len(texts)
        def mock_encode(texts, **kwargs):
            return np.random.rand(len(texts), 384)
        mock_model.encode.side_effect = mock_encode
        mock_st.return_value = mock_model

        service = EmbeddingService()

        # Step 1: Initial load
        service.embed_candidates(self.df1)
        
        # Verify initial save
        assert service.npy_path.exists()
        assert service.meta_path.exists()
        
        ids, embeds = service.load_embeddings()
        assert len(ids) == 3
        assert ids == ["C1", "C2", "C3"]
        assert embeds.shape == (3, 384)
        assert mock_model.encode.call_count == 1

        # Step 2: Incremental load (df2 has C2, C3, C4, C5)
        # Should only embed C4 and C5
        service.embed_candidates(self.df2)
        
        ids, embeds = service.load_embeddings()
        assert len(ids) == 5
        assert ids == ["C1", "C2", "C3", "C4", "C5"]
        assert embeds.shape == (5, 384)
        assert mock_model.encode.call_count == 2
        
        # Verify it was only called with C4 and C5 texts
        call_args = mock_model.encode.call_args[0][0]
        assert len(call_args) == 2
        assert call_args == ["text4", "text5"]

    @patch("app.services.embedding_service.SentenceTransformer")
    def test_embed_candidates_empty(self, mock_st):
        service = EmbeddingService()
        # Empty DataFrame
        service.embed_candidates(pd.DataFrame())
        assert not service.npy_path.exists()

    @patch("app.services.embedding_service.SentenceTransformer")
    def test_missing_metadata_reset(self, mock_st):
        """Test what happens if lengths mismatch (corrupt data)."""
        mock_model = MagicMock()
        def mock_encode(texts, **kwargs):
            return np.ones((len(texts), 384))
        mock_model.encode.side_effect = mock_encode
        mock_st.return_value = mock_model
        
        service = EmbeddingService()
        service.embed_candidates(self.df1)
        
        # Corrupt the metadata
        import pickle
        with open(service.meta_path, "wb") as f:
            pickle.dump(["C1", "C2"], f)  # length 2 instead of 3
            
        # Try to embed df2. It should detect mismatch, reset existing, and re-embed all of df2.
        service.embed_candidates(self.df2)
        
        ids, embeds = service.load_embeddings()
        assert len(ids) == 4
        assert ids == ["C2", "C3", "C4", "C5"]
        assert embeds.shape == (4, 384)


if __name__ == "__main__":
    test_classes = [TestEmbeddingService]

    passed = failed = 0
    print("\n" + "═" * 60)
    print("  EmbeddingService — Unit Tests")
    print("═" * 60)

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        print(f"\n  {cls.__name__} ({len(methods)} tests)")
        for method_name in methods:
            instance.setup_method()
            try:
                getattr(instance, method_name)()
                print(f"    ✅ {method_name}")
                passed += 1
            except Exception as exc:
                print(f"    ❌ {method_name}")
                traceback.print_exc()
                failed += 1
            instance.teardown_method()

    print("\n" + "─" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("─" * 60)
    if failed:
        sys.exit(1)
