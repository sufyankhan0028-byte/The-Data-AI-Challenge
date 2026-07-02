"""
Hybrid Retrieval Engine
Combines semantic similarity + keyword SQL filtering to retrieve Top-K candidates.
"""
from __future__ import annotations

import json
from typing import List, Optional

import numpy as np
import pandas as pd

from app.config import settings
from app.schemas.ranking import ParsedJD
from app.utils.logger import get_logger

logger = get_logger(__name__)


def retrieve_top_k(
    df: pd.DataFrame,
    embeddings: np.ndarray,
    candidate_ids: List[str],
    jd: ParsedJD,
    jd_embedding: np.ndarray,
    top_k: int = 500,
) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Hybrid retrieval: semantic cosine + keyword SQL.
    Returns (filtered_df, semantic_scores_for_filtered_df).
    """
    n_total = len(df)
    logger.info("Retrieval: %d total candidates, targeting top %d", n_total, top_k)

    # ---------- 1. Semantic retrieval ----------
    # Cosine similarity (embeddings are L2-normalized → dot product = cosine)
    id_to_idx = {cid: i for i, cid in enumerate(candidate_ids)}

    # Only compute cosine for candidates present in df
    df_ids = df["candidate_id"].tolist()
    df_indices = np.array([id_to_idx[cid] for cid in df_ids if cid in id_to_idx])
    if len(df_indices) == 0:
        logger.warning("No candidate IDs found in embedding map.")
        df_indices = np.arange(len(embeddings))

    sub_embeddings = embeddings[df_indices]  # [N, D]
    semantic_scores = sub_embeddings @ jd_embedding  # [N]

    # Clamp to [0, 1] range (MiniLM can produce slightly negative cosines)
    semantic_scores = np.clip(semantic_scores, 0.0, 1.0)

    # Top semantic candidates
    sem_top_k = min(top_k, n_total)
    sem_top_indices = np.argpartition(semantic_scores, -sem_top_k)[-sem_top_k:]
    sem_top_ids = set(df_ids[i] for i in sem_top_indices)

    # ---------- 2. Keyword / signal filtering ----------
    keyword_ids = _keyword_filter(df, jd)

    # ---------- 3. Merge & deduplicate ----------
    combined_ids = sem_top_ids | keyword_ids
    logger.info(
        "Retrieval: semantic=%d, keyword=%d, combined=%d",
        len(sem_top_ids), len(keyword_ids), len(combined_ids),
    )

    # Filter df
    mask = df["candidate_id"].isin(combined_ids)
    filtered_df = df[mask].copy().reset_index(drop=True)

    # Build semantic score array for filtered df
    id_to_sem = {df_ids[i]: float(semantic_scores[i]) for i in range(len(df_ids))}
    filtered_sem_scores = np.array([
        id_to_sem.get(cid, 0.0) for cid in filtered_df["candidate_id"]
    ])

    logger.info("Retrieval complete: %d candidates selected.", len(filtered_df))
    return filtered_df, filtered_sem_scores


def _keyword_filter(df: pd.DataFrame, jd: ParsedJD) -> set:
    """
    SQL-style keyword filter using pandas string ops.
    Returns set of candidate_ids that match key criteria.
    """
    matched = set()

    # Candidates open to work
    if "open_to_work_flag" in df.columns:
        otw = df[df["open_to_work_flag"] == True]["candidate_id"].tolist()
        matched.update(otw[:200])  # cap to avoid too many low-quality

    # Candidates with matching required skills
    if jd.required_skills:
        for skill in jd.required_skills[:8]:  # top 8 required
            skill_lower = skill.lower()
            has_skill = df["skills_list"].str.contains(skill_lower, case=False, na=False)
            matched.update(df[has_skill]["candidate_id"].tolist()[:100])

    # Candidates matching target titles in career history
    if jd.target_titles:
        for title in jd.target_titles[:4]:
            title_lower = title.lower()
            has_title = (
                df["current_title"].str.lower().str.contains(title_lower, na=False)
                | df["career_titles"].str.lower().str.contains(title_lower, na=False)
            )
            matched.update(df[has_title]["candidate_id"].tolist()[:80])

    return matched
