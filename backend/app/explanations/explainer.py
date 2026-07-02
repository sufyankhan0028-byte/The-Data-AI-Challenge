"""
Explanation Generator
Produces per-candidate SHAP-style feature importance using manual partial scores.
Also generates the global feature importance for the dashboard.
"""
from __future__ import annotations

from typing import Dict, List

from app.config import settings
from app.schemas.ranking import FeatureImportanceItem, RankResult


def get_candidate_feature_importance(result: RankResult) -> List[FeatureImportanceItem]:
    """Return ordered feature importance for a single candidate's ranking."""
    from app.config.ranking_config import load_ranking_weights
    weights = load_ranking_weights()
    bd = result.score_breakdown
    components = [
        ("Semantic Match", bd.semantic_score * (weights.semantic_match / 100.0), "positive"),
        ("Experience", bd.experience_score * (weights.experience / 100.0), "positive"),
        ("Behavioral Signals", bd.signal_score * (weights.behavioral_signals / 100.0), "positive"),
        ("Production Experience", bd.skill_score * (weights.production_experience / 100.0), "positive"),
        ("Startup Experience", bd.education_score * (weights.startup_experience / 100.0), "positive"),
        ("Career Stability", bd.engagement_score * (weights.career_stability / 100.0), "positive"),
        ("Penalty", -bd.penalty, "negative"),
    ]
    items = [
        FeatureImportanceItem(
            feature=name,
            importance=round(abs(imp), 4),
            direction=direction if imp >= 0 else "negative",
        )
        for name, imp, direction in components
    ]
    return sorted(items, key=lambda x: x.importance, reverse=True)


def get_global_feature_importance(results: List[RankResult]) -> List[FeatureImportanceItem]:
    """
    Average component contributions across top-N results to produce global importance.
    """
    if not results:
        return []

    from app.config.ranking_config import load_ranking_weights
    weights = load_ranking_weights()
    totals: Dict[str, float] = {}
    for r in results:
        bd = r.score_breakdown
        totals["Semantic Match"] = totals.get("Semantic Match", 0) + bd.semantic_score * (weights.semantic_match / 100.0)
        totals["Experience"] = totals.get("Experience", 0) + bd.experience_score * (weights.experience / 100.0)
        totals["Behavioral Signals"] = totals.get("Behavioral Signals", 0) + bd.signal_score * (weights.behavioral_signals / 100.0)
        totals["Production Experience"] = totals.get("Production Experience", 0) + bd.skill_score * (weights.production_experience / 100.0)
        totals["Startup Experience"] = totals.get("Startup Experience", 0) + bd.education_score * (weights.startup_experience / 100.0)
        totals["Career Stability"] = totals.get("Career Stability", 0) + bd.engagement_score * (weights.career_stability / 100.0)

    n = len(results)
    items = [
        FeatureImportanceItem(
            feature=name,
            importance=round(total / n, 4),
            direction="positive",
        )
        for name, total in totals.items()
    ]
    return sorted(items, key=lambda x: x.importance, reverse=True)
