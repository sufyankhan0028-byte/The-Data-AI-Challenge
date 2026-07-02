"""
Hybrid Retrieval Service
========================
Combines BM25 sparse scores and dense embedding scores (Cosine Similarity)
to retrieve the top K candidate matches for a job description.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.services.bm25_retrieval_service import BM25RetrievalService
from app.services.embedding_service import EmbeddingService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HybridRetrievalService:
    """
    Performs normalized hybrid search across the candidate pool.
    Configurable weights for BM25 vs Semantic search.
    """
    def __init__(
        self, 
        bm25_service: BM25RetrievalService, 
        embedding_service: EmbeddingService,
        bm25_weight: float = 0.4,
        semantic_weight: float = 0.6
    ):
        self.bm25_service = bm25_service
        self.embedding_service = embedding_service
        self.bm25_weight = bm25_weight
        self.semantic_weight = semantic_weight
        
        # We will hold the dense embeddings in memory for fast matrix multiplication
        self.candidate_ids: List[str] = []
        self.embeddings: Optional[np.ndarray] = None
        
    def load_indexes(self) -> None:
        """
        Loads the BM25 index and the dense embeddings from disk into memory.
        """
        logger.info("Loading indexes into HybridRetrievalService...")
        t0 = time.time()
        
        # Load BM25
        self.bm25_service.load_index()
        
        # Load Dense Embeddings
        self.candidate_ids, self.embeddings = self.embedding_service.load_embeddings()
        
        if len(self.candidate_ids) != len(self.bm25_service.candidate_ids):
            logger.warning(
                "Mismatch between Dense IDs (%d) and BM25 IDs (%d)!",
                len(self.candidate_ids), len(self.bm25_service.candidate_ids)
            )
            
        logger.info("Indexes loaded successfully in %.3fs", time.time() - t0)

    def retrieve(
        self, 
        query_text: str, 
        top_k: int = 500
    ) -> List[Dict[str, float | str]]:
        """
        Perform hybrid retrieval.
        Score = bm25_weight * norm(BM25) + semantic_weight * norm(Cosine)
        Returns the top K candidates.
        """
        if not self.bm25_service.is_fitted or self.embeddings is None:
            raise RuntimeError("Engine not indexed. Call load_indexes() first.")
            
        t_start = time.time()
        
        # 1. Sparse (BM25) Scoring
        t_bm25 = time.time()
        # Transform query into term counts
        query_vec = self.bm25_service.vectorizer.transform([query_text])
        q_indices = query_vec.indices
        
        if len(q_indices) == 0:
            bm25_scores = np.zeros(self.bm25_service.doc_freqs.shape[0])
        else:
            term_freqs = self.bm25_service.doc_freqs[:, q_indices]
            q_idfs = self.bm25_service.idf.diagonal()[q_indices]
            
            len_norm = self.bm25_service.k1 * (
                1.0 - self.bm25_service.b + self.bm25_service.b * (self.bm25_service.doc_len / self.bm25_service.avgdl)
            )
            tf_data = term_freqs.data
            rows, cols = term_freqs.nonzero()
            
            numerator = tf_data * (self.bm25_service.k1 + 1.0)
            denominator = tf_data + len_norm[rows]
            bm25_tf_data = numerator / denominator
            
            from scipy import sparse
            bm25_tf = sparse.csr_matrix((bm25_tf_data, (rows, cols)), shape=term_freqs.shape)
            bm25_scores = np.asarray(bm25_tf.dot(q_idfs)).flatten()
            
        # MinMax scale BM25 to [0, 1] for fair weighting
        bm25_max = bm25_scores.max()
        bm25_min = bm25_scores.min()
        if bm25_max > bm25_min:
            bm25_norm = (bm25_scores - bm25_min) / (bm25_max - bm25_min)
        else:
            bm25_norm = np.zeros_like(bm25_scores)
            
        # 2. Dense (Embedding) Scoring
        t_dense = time.time()
        # Use lru_cache wrapped query embedding
        query_embedding = self.embedding_service.embed_query(query_text)
        
        # Dot product is equivalent to cosine similarity (since embeddings are L2 normalized)
        cosine_scores = np.dot(self.embeddings, query_embedding)
        
        # 3. Hybrid Score Combination
        final_scores = (self.bm25_weight * bm25_norm) + (self.semantic_weight * cosine_scores)
        
        # 4. CPU-Optimized Top-K Selection
        t_sort = time.time()
        n_candidates = len(final_scores)
        k = min(top_k, n_candidates)
        
        if k == 0:
            return []
            
        if k == n_candidates:
            top_indices = np.argsort(-final_scores)
        else:
            partition_indices = np.argpartition(-final_scores, k - 1)[:k]
            top_k_scores = final_scores[partition_indices]
            sort_order = np.argsort(-top_k_scores)
            top_indices = partition_indices[sort_order]
            
        # 5. Output Formatting
        results = []
        for idx in top_indices:
            results.append({
                "candidate_id": self.candidate_ids[idx],
                "hybrid_score": float(final_scores[idx]),
                "bm25_norm": float(bm25_norm[idx]),
                "semantic_score": float(cosine_scores[idx])
            })
            
        t_end = time.time()
        
        # Timing Logs
        logger.info(
            "Retrieved top %d candidates in %.3fs "
            "(BM25: %.3fs, Dense: %.3fs, Sort: %.3fs). "
            "Max BM25 Norm: %.2f | Max Cosine: %.2f", 
            len(results), t_end - t_start, 
            t_dense - t_bm25, t_sort - t_dense, t_end - t_sort,
            bm25_norm.max(), cosine_scores.max()
        )
        
        return results
