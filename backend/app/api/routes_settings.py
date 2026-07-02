"""
Settings API Router
===================
Endpoints for retrieving and updating ranking configuration weights.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.config.ranking_config import RankingWeights, load_ranking_weights, save_ranking_weights
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["settings"])


@router.get("/settings/ranking-weights", response_model=RankingWeights, summary="Get current ranking weights")
@router.get("/api/settings/ranking-weights", response_model=RankingWeights, summary="Get current ranking weights (api prefix)")
def get_ranking_weights():
    try:
        weights = load_ranking_weights()
        logger.info("[API] GET /settings/ranking-weights -> %s", weights.model_dump())
        return weights
    except Exception as exc:
        logger.error("Failed to get ranking weights: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/settings/ranking-weights", response_model=RankingWeights, summary="Update ranking weights")
@router.put("/api/settings/ranking-weights", response_model=RankingWeights, summary="Update ranking weights (api prefix)")
def update_ranking_weights(weights: RankingWeights):
    try:
        saved = save_ranking_weights(weights)
        logger.info("[API] PUT /settings/ranking-weights -> %s", saved.model_dump())
        return saved
    except ValueError as val_err:
        logger.warning("Validation error updating weights: %s", val_err)
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        logger.error("Failed to save ranking weights: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
