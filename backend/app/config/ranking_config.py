"""
Ranking Configuration Model and Persistence
===========================================
Defines the Pydantic schema for scoring weights, validation rules,
and helper functions to load/save weights from JSON storage.
"""
from __future__ import annotations

import json
from pathlib import Path
from pydantic import BaseModel, Field, model_validator
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RankingWeights(BaseModel):
    semantic_match: float = Field(default=30.0, ge=0.0, le=100.0, description="Semantic match weight (%)")
    experience: float = Field(default=20.0, ge=0.0, le=100.0, description="Experience weight (%)")
    behavioral_signals: float = Field(default=15.0, ge=0.0, le=100.0, description="Behavioral signals weight (%)")
    production_experience: float = Field(default=20.0, ge=0.0, le=100.0, description="Production experience weight (%)")
    startup_experience: float = Field(default=10.0, ge=0.0, le=100.0, description="Startup experience weight (%)")
    career_stability: float = Field(default=5.0, ge=0.0, le=100.0, description="Career stability weight (%)")

    @model_validator(mode="after")
    def validate_sum_equals_100(self) -> "RankingWeights":
        total = (
            self.semantic_match
            + self.experience
            + self.behavioral_signals
            + self.production_experience
            + self.startup_experience
            + self.career_stability
        )
        if abs(total - 100.0) > 1e-3:
            raise ValueError(f"Weights must sum to exactly 100%. Current sum is {round(total, 2)}%.")
        return self


# ─────────────────────────────────────────────────────────
# Persistence functions (Step 2)
# ─────────────────────────────────────────────────────────
# File path: backend/data/config/ranking_weights.json
CONFIG_DIR = settings.DATA_DIR / "config"
WEIGHTS_FILE = CONFIG_DIR / "ranking_weights.json"

DEFAULT_WEIGHTS = RankingWeights(
    semantic_match=30.0,
    experience=20.0,
    behavioral_signals=15.0,
    production_experience=20.0,
    startup_experience=10.0,
    career_stability=5.0,
)


def load_ranking_weights() -> RankingWeights:
    """
    Load ranking weights from backend/data/config/ranking_weights.json.
    If the file does not exist or is invalid, create it with default values.
    """
    if not WEIGHTS_FILE.exists():
        logger.info("Ranking weights file not found. Creating default config at %s", WEIGHTS_FILE)
        save_ranking_weights(DEFAULT_WEIGHTS)
        return DEFAULT_WEIGHTS.model_copy()

    try:
        with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        weights = RankingWeights.model_validate(data)
        return weights
    except Exception as exc:
        logger.warning("Failed to load or validate ranking weights from %s (%s). Reverting to defaults.", WEIGHTS_FILE, exc)
        save_ranking_weights(DEFAULT_WEIGHTS)
        return DEFAULT_WEIGHTS.model_copy()


def save_ranking_weights(weights: RankingWeights) -> RankingWeights:
    """
    Save validated ranking weights to backend/data/config/ranking_weights.json.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(WEIGHTS_FILE, "w", encoding="utf-8") as f:
        json.dump(weights.model_dump(), f, indent=2)
    logger.info("Saved ranking weights to %s: %s", WEIGHTS_FILE, weights.model_dump())
    return weights
