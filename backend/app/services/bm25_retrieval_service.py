"""
BM25 Retrieval Service
======================
Handles pure sparse BM25 indexing and retrieval on Candidate text features.
CPU optimized using vectorized sparse matrix operations via scikit-learn & scipy.
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer

from app.utils.logger import get_logger

logger = get_logger(__name__)


class BM25RetrievalService:
    """
    CPU-optimized, vectorized implementation of BM25.
    Handles 100k+ documents instantly without memory bloat.
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        # Minimal analyzer: lowercase, standard word boundaries
        self.vectorizer = CountVectorizer(lowercase=True, token_pattern=r"(?u)\b\w+\b")
        
        self.candidate_ids: List[str] = []
        self.doc_len: Optional[np.ndarray] = None
        self.avgdl: float = 0.0
        self.idf: Optional[np.ndarray] = None
        self.doc_freqs: Optional[sparse.csr_matrix] = None
        self.is_fitted = False
        
        self.index_path = Path("data/bm25_index.pkl")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

    def fit(self, candidate_ids: List[str], corpus: List[str]) -> None:
        """Fit BM25 to the candidate corpus."""
        if len(candidate_ids) != len(corpus):
            raise ValueError("Length of candidate_ids must match corpus.")
            
        logger.info("Fitting BM25 on %d documents...", len(corpus))
        self.candidate_ids = candidate_ids
        
        # doc_freqs: row=doc, col=term, value=count
        self.doc_freqs = self.vectorizer.fit_transform(corpus)
        
        # Document lengths
        self.doc_len = self.doc_freqs.sum(axis=1).A1  # type: ignore
        self.avgdl = float(np.mean(self.doc_len))
        
        # IDF calculation
        N = self.doc_freqs.shape[0]
        # Number of docs containing each term
        df = np.bincount(self.doc_freqs.indices, minlength=self.doc_freqs.shape[1])
        # Standard BM25 IDF formula
        idf = np.log((N - df + 0.5) / (df + 0.5) + 1.0)
        self.idf = sparse.diags(idf, format="csr")
        
        self.is_fitted = True
        logger.info("BM25 fitting complete. Vocab size: %d", len(self.vectorizer.vocabulary_))
        
    def save_index(self) -> None:
        """Save the fitted index to disk."""
        if not self.is_fitted:
            raise RuntimeError("Cannot save empty index. Call fit() first.")
            
        state = {
            "candidate_ids": self.candidate_ids,
            "k1": self.k1,
            "b": self.b,
            "vectorizer": self.vectorizer,
            "doc_len": self.doc_len,
            "avgdl": self.avgdl,
            "idf": self.idf,
            "doc_freqs": self.doc_freqs,
            "is_fitted": self.is_fitted
        }
        with open(self.index_path, "wb") as f:
            pickle.dump(state, f)
        logger.info("Saved BM25 index to %s", self.index_path)
            
    def load_index(self) -> None:
        """Load the index from disk."""
        if not self.index_path.exists():
            raise FileNotFoundError(f"No index found at {self.index_path}")
            
        with open(self.index_path, "rb") as f:
            state = pickle.load(f)
            
        self.candidate_ids = state["candidate_ids"]
        self.k1 = state["k1"]
        self.b = state["b"]
        self.vectorizer = state["vectorizer"]
        self.doc_len = state["doc_len"]
        self.avgdl = state["avgdl"]
        self.idf = state["idf"]
        self.doc_freqs = state["doc_freqs"]
        self.is_fitted = state["is_fitted"]
        logger.info("Loaded BM25 index with %d documents.", len(self.candidate_ids))

    def get_top_k(self, query: str, top_k: int = 100) -> List[Dict[str, float | str]]:
        """
        Calculate BM25 scores for a query across all documents and return top K.
        Uses CPU-optimized np.argpartition for O(N) selection.
        """
        if not self.is_fitted or self.doc_freqs is None or self.idf is None or self.doc_len is None:
            raise ValueError("BM25 is not fitted. Call fit() first.")
            
        # Transform query into term counts
        query_vec = self.vectorizer.transform([query])
        
        # Find which terms are in the query
        q_indices = query_vec.indices
        if len(q_indices) == 0:
            return []
            
        # For the terms in the query, extract their frequencies across all docs
        term_freqs = self.doc_freqs[:, q_indices]
        q_idfs = self.idf.diagonal()[q_indices]
        
        # Calculate BM25 TF component
        len_norm = self.k1 * (1.0 - self.b + self.b * (self.doc_len / self.avgdl))
        
        tf_data = term_freqs.data
        rows, cols = term_freqs.nonzero()
        
        numerator = tf_data * (self.k1 + 1.0)
        denominator = tf_data + len_norm[rows]
        bm25_tf_data = numerator / denominator
        
        bm25_tf = sparse.csr_matrix(
            (bm25_tf_data, (rows, cols)), 
            shape=term_freqs.shape
        )
        
        # Final scores: dot product of TF component with IDFs
        scores = np.asarray(bm25_tf.dot(q_idfs)).flatten()
        
        # CPU-Optimized Top-K Selection
        n_docs = len(scores)
        k = min(top_k, n_docs)
        
        if k == 0:
            return []
            
        if k == n_docs:
            top_indices = np.argsort(-scores)
        else:
            partition_indices = np.argpartition(-scores, k - 1)[:k]
            top_k_scores = scores[partition_indices]
            sort_order = np.argsort(-top_k_scores)
            top_indices = partition_indices[sort_order]
            
        # Format exact requested output
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score > 0:  # Only return candidates that actually matched something
                results.append({
                    "candidate_id": self.candidate_ids[idx],
                    "bm25_score": score
                })
                
        return results
