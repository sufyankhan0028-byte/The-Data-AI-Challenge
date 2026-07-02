"""
Features schema representing the multi-dimensional vector for a single candidate.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional

class FeatureVector(BaseModel):
    """
    28-dimensional dense feature vector representing a candidate's fit for a specific JD.
    All scores are generally normalized between 0.0 and 1.0.
    """
    model_config = ConfigDict(frozen=True)

    # Semantic Features
    embedding_similarity: float = 0.0
    bm25_score: float = 0.0
    skill_overlap_score: float = 0.0

    # Experience Features
    years_experience_score: float = 0.0
    seniority_score: float = 0.0
    production_ml_score: float = 0.0
    startup_score: float = 0.0
    leadership_score: float = 0.0

    # Career Features
    average_tenure: float = 0.0
    job_hops: int = 0
    career_growth_score: float = 0.0
    title_progression_score: float = 0.0

    # Skill Features
    vector_db_score: float = 0.0
    retrieval_score: float = 0.0
    ranking_score: float = 0.0
    python_score: float = 0.0
    llm_score: float = 0.0
    fine_tuning_score: float = 0.0
    open_source_score: float = 0.0

    # Behavioral Features
    recruiter_response_rate: float = 0.0
    github_activity_score: float = 0.0
    interview_completion_rate: float = 0.0
    profile_views_score: float = 0.0
    saved_by_recruiters_score: float = 0.0
    profile_completeness_score: float = 0.0
    open_to_work_score: float = 0.0
    recent_activity_score: float = 0.0
    notice_period_score: float = 0.0

    # Location Features
    india_score: float = 0.0
    relocation_score: float = 0.0
    hybrid_score: float = 0.0
