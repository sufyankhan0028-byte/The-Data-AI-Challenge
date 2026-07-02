"""
Embedding Service
=================
Handles generation of dense vector embeddings for both Candidates and Job Descriptions
using sentence-transformers. Designed for CPU optimization and incremental processing.
"""
from __future__ import annotations

import os
import pickle
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    Singleton service for generating and managing embeddings.
    Runs strictly on CPU, using intra_op_threads for performance.
    Handles incremental processing of candidate batches.
    """

    _instance: Optional["EmbeddingService"] = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._initialized = False  # type: ignore
        return cls._instance

    def __init__(self):
        if self._initialized:  # type: ignore
            return

        logger.info(
            "Initializing EmbeddingService on CPU with model: %s",
            settings.EMBEDDING_MODEL,
        )

        # CPU optimization: limit threads to avoid context-switching overhead
        torch.set_num_threads(settings.INTRA_OP_THREADS)

        self.model = SentenceTransformer(
            model_name_or_path=settings.EMBEDDING_MODEL,
            device="cpu",
        )
        
        # Use configured embeddings directory
        embed_dir = settings.EMBEDDINGS_DIR
        embed_dir.mkdir(parents=True, exist_ok=True)
        
        self.npy_path: Path = embed_dir / "candidate_embeddings.npy"
        self.meta_path: Path = embed_dir / "candidate_mapping.pkl"

        self._initialized = True

    @lru_cache(maxsize=128)
    def embed_query(self, text: str) -> np.ndarray:
        """
        Embed a single text string (e.g., a Job Description).
        Returns a 1D numpy array.
        Results are cached in memory to speed up repeated identical queries.
        """
        embedding = self.model.encode(
            text,
            batch_size=1,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,  # bge-small often benefits from normalization
        )
        return embedding  # type: ignore

    def embed_candidates(
        self, candidates_df: pd.DataFrame, text_column: str = "unified_text"
    ) -> None:
        """
        Incrementally embed candidates.
        Only generates embeddings for candidate_ids not already present in the metadata.
        Appends results to the numpy array and updates metadata.
        """
        if candidates_df.empty:
            logger.info("Empty dataframe provided to embed_candidates.")
            return

        if "candidate_id" not in candidates_df.columns or text_column not in candidates_df.columns:
            raise ValueError(f"DataFrame must contain 'candidate_id' and '{text_column}' columns.")

        # Load existing state
        existing_ids: List[str] = []
        existing_embeds: Optional[np.ndarray] = None

        if self.meta_path.exists() and self.npy_path.exists():
            with open(self.meta_path, "rb") as f:
                existing_ids = pickle.load(f)
            existing_embeds = np.load(self.npy_path)
            
            if len(existing_ids) != existing_embeds.shape[0]:
                logger.warning(
                    "Mismatch between metadata length (%d) and npy rows (%d). Resetting embeddings.",
                    len(existing_ids), existing_embeds.shape[0]
                )
                existing_ids = []
                existing_embeds = None

        existing_set = frozenset(existing_ids)

        # Identify new candidates
        # We preserve the order of candidates_df for the new ones
        new_df = candidates_df[~candidates_df["candidate_id"].isin(existing_set)]

        if new_df.empty:
            logger.info("No new candidates to embed. All %d already exist.", len(candidates_df))
            return

        new_ids = new_df["candidate_id"].tolist()
        new_texts = new_df[text_column].tolist()

        logger.info(
            "Generating embeddings for %d new candidates in batches of %d...",
            len(new_texts), settings.EMBEDDING_BATCH_SIZE
        )

        # Generate embeddings
        new_embeds = self.model.encode(
            new_texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        # Append to existing
        if existing_embeds is not None:
            combined_embeds = np.vstack([existing_embeds, new_embeds])
            combined_ids = existing_ids + new_ids
        else:
            combined_embeds = new_embeds
            combined_ids = new_ids

        # Save to disk
        # Save temp then rename for atomic-ish write
        tmp_npy = self.npy_path.with_suffix(".tmp.npy")
        tmp_meta = self.meta_path.with_suffix(".tmp.pkl")

        np.save(tmp_npy, combined_embeds)
        with open(tmp_meta, "wb") as f:
            pickle.dump(combined_ids, f)

        # Replace originals
        tmp_npy.replace(self.npy_path)
        tmp_meta.replace(self.meta_path)

        logger.info("Successfully updated embeddings. Total embedded: %d", len(combined_ids))

    def load_embeddings(self) -> Tuple[List[str], np.ndarray]:
        """
        Load the current candidate IDs and their corresponding embeddings from disk.
        Returns:
            Tuple containing (list of candidate IDs, 2D numpy array of embeddings).
        Raises:
            FileNotFoundError if embeddings haven't been generated yet.
        """
        if not self.meta_path.exists() or not self.npy_path.exists():
            raise FileNotFoundError("Embeddings not found on disk. Run embed_candidates first.")

        with open(self.meta_path, "rb") as f:
            candidate_ids = pickle.load(f)
            
        embeddings = np.load(self.npy_path)
        return candidate_ids, embeddings
