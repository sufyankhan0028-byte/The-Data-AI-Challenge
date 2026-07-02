"""
Ranking Engine
Combines features into a final weighted score, applies negative signal penalties,
selects top-N candidates.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from app.config import settings
from app.schemas.ranking import ParsedJD, RankResult, ScoreBreakdown
from app.services.feature_engineering import build_features
from app.services.negative_signals import detect_negative_signals
from app.utils.logger import get_logger

logger = get_logger(__name__)


def rank_candidates(
    df: pd.DataFrame,
    jd: ParsedJD,
    semantic_scores: np.ndarray,
    top_n: int = 100,
) -> List[RankResult]:
    """
    Score all candidates in df, apply penalties, return top_n RankResults sorted by score.
    """
    logger.info("Ranking %d candidates ...", len(df))
    from app.config.ranking_config import load_ranking_weights
    weights = load_ranking_weights()
    print("Loaded Ranking Weights:")
    print(f"Semantic Match: {weights.semantic_match}")
    print(f"Experience: {weights.experience}")
    print(f"Behavioral Signals: {weights.behavioral_signals}")
    print(f"Production Experience: {weights.production_experience}")
    print(f"Startup Experience: {weights.startup_experience}")
    print(f"Career Stability: {weights.career_stability}")
    logger.info("Loaded Ranking Weights:\nSemantic Match: %s\nExperience: %s\nBehavioral Signals: %s\nProduction Experience: %s\nStartup Experience: %s\nCareer Stability: %s",
                weights.semantic_match, weights.experience, weights.behavioral_signals, weights.production_experience, weights.startup_experience, weights.career_stability)
    scored = []

    for i, (_, row) in enumerate(df.iterrows()):
        sem_score = float(semantic_scores[i]) if i < len(semantic_scores) else 0.0

        # Build features
        features = build_features(row, jd, sem_score)

        # Negative signals
        penalty, neg_flags = detect_negative_signals(row)

        # Weighted score
        breakdown = _compute_breakdown(features)

        # Apply penalty
        raw_score = (
            (weights.production_experience / 100.0) * breakdown.skill_score
            + (weights.semantic_match / 100.0) * breakdown.semantic_score
            + (weights.experience / 100.0) * breakdown.experience_score
            + (weights.behavioral_signals / 100.0) * breakdown.signal_score
            + (weights.startup_experience / 100.0) * breakdown.education_score
            + (weights.career_stability / 100.0) * breakdown.engagement_score
        )
        final_score = raw_score * (1.0 - penalty)
        breakdown.penalty = penalty
        breakdown.total_score = round(final_score, 6)

        # Top positive factors
        pos_factors = _top_positive_factors(features, breakdown)

        scored.append(
            (final_score, row, breakdown, pos_factors, neg_flags, features)
        )

    # Sort descending
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_n]

    # Build RankResult objects
    results: List[RankResult] = []
    for rank_idx, (score, row, breakdown, pos_factors, neg_flags, features) in enumerate(top, start=1):
        # Get skill list from row
        import json
        skills_json = row.get("skills_json", "[]")
        skills_data = json.loads(skills_json) if isinstance(skills_json, str) else []
        top_skills = [s["name"] for s in sorted(
            skills_data,
            key=lambda s: (
                {"expert": 4, "advanced": 3, "intermediate": 2, "beginner": 1}.get(s.get("proficiency", "beginner"), 0),
                s.get("endorsements", 0),
            ),
            reverse=True,
        )[:5]]

        reasoning = _build_reasoning(row, features, jd, neg_flags)

        rr = RankResult(
            candidate_id=str(row["candidate_id"]),
            rank=rank_idx,
            score=round(score, 4),
            reasoning=reasoning,
            score_breakdown=breakdown,
            top_positive_factors=pos_factors,
            negative_flags=neg_flags,
            current_title=str(row.get("current_title", "")),
            years_of_experience=float(row.get("years_of_experience", 0)),
            location=str(row.get("location", "")),
            country=str(row.get("country", "")),
            headline=str(row.get("headline", "")),
            top_skills=top_skills,
            open_to_work=bool(row.get("open_to_work_flag", False)),
            notice_period_days=int(row.get("notice_period_days", 60)),
        )
        results.append(rr)

    logger.info("Ranking complete. Top score=%.4f", results[0].score if results else 0)
    return results


def _compute_breakdown(features: Dict[str, float]) -> ScoreBreakdown:
    return ScoreBreakdown(
        skill_score=round(features.get("skill_score", 0.0), 4),
        semantic_score=round(features.get("semantic_score", 0.0), 4),
        experience_score=round(features.get("experience_score", 0.0), 4),
        signal_score=round(features.get("signal_score", 0.0), 4),
        education_score=round(features.get("education_score", 0.0), 4),
        engagement_score=round(features.get("engagement_score", 0.0), 4),
    )


def _top_positive_factors(
    features: Dict[str, float],
    breakdown: ScoreBreakdown,
) -> List[str]:
    """Return top 3 contributing factors as human-readable strings."""
    from app.config.ranking_config import load_ranking_weights
    weights = load_ranking_weights()
    component_scores = {
        "Production Experience": breakdown.skill_score * (weights.production_experience / 100.0),
        "Semantic Match": breakdown.semantic_score * (weights.semantic_match / 100.0),
        "Experience": breakdown.experience_score * (weights.experience / 100.0),
        "Behavioral Signals": breakdown.signal_score * (weights.behavioral_signals / 100.0),
        "Startup Experience": breakdown.education_score * (weights.startup_experience / 100.0),
        "Career Stability": breakdown.engagement_score * (weights.career_stability / 100.0),
    }
    top3 = sorted(component_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    return [f"{name} ({score:.2f})" for name, score in top3]


def _build_reasoning(row: pd.Series, features: Dict[str, float], jd: ParsedJD, neg_flags: List[str]) -> str:
    """Build the submission reasoning string."""
    title = str(row.get("current_title", "Professional"))
    yoe = float(row.get("years_of_experience", 0))
    req_matched = int(features.get("req_skills_matched", 0) * max(len(jd.required_skills), 1))
    rr = float(row.get("recruiter_response_rate", 0))
    open_flag = bool(row.get("open_to_work_flag", False))

    parts = [
        f"{title} with {yoe:.1f} yrs",
        f"{req_matched} core skills matched",
        f"response rate {rr:.2f}",
    ]
    if open_flag:
        parts.append("open to work")
    if neg_flags:
        parts.append(f"flags: {neg_flags[0][:40]}")

    return "; ".join(parts) + "."
