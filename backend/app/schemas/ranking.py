from typing import Dict, List, Optional
from pydantic import BaseModel

class CandidateRankResult(BaseModel):
    """
    Output model representing a scored and ranked candidate.
    """
    candidate_id: str
    anonymized_name: str
    headline: str
    location: str
    years_of_experience: float
    
    # Final combined score after penalty
    final_score: float
    
    # Feature scores (normalized 0-1)
    semantic_score: float
    production_score: float
    experience_score: float
    behavior_score: float
    startup_score: float
    stability_score: float
    
    # Applied honeypot penalty (0-1)
    penalty_score: float
    
    explanation: str
    
    top_skills: List[str] = []

class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float
    direction: str  # "positive" | "negative"

class StatusResponse(BaseModel):
    status: str
    message: str
    total_candidates: int = 0
    progress_pct: float = 0.0
