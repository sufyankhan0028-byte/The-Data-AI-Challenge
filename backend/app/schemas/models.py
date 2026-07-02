"""
Pydantic v2 models for validating every field of the candidate schema.
Used by the JSONL loader for type-safe parsing with clear error reporting.
"""
from __future__ import annotations

from typing import Annotated, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────
# Nested sub-models
# ─────────────────────────────────────────

CompanySize = Literal[
    "1-10", "11-50", "51-200", "201-500",
    "501-1000", "1001-5000", "5001-10000", "10001+"
]

WorkMode = Literal["remote", "hybrid", "onsite", "flexible"]

EducationTier = Literal["tier_1", "tier_2", "tier_3", "tier_4", "unknown"]

Proficiency = Literal["beginner", "intermediate", "advanced", "expert"]

LangProficiency = Literal["basic", "conversational", "professional", "native"]


class ProfileModel(BaseModel):
    anonymized_name: str
    headline: str
    summary: str
    location: str
    country: str
    years_of_experience: Annotated[float, Field(ge=0, le=50)]
    current_title: str
    current_company: str
    current_company_size: CompanySize
    current_industry: str


class CareerEntryModel(BaseModel):
    company: str
    title: str
    start_date: str
    end_date: Optional[str] = None
    duration_months: Annotated[int, Field(ge=0)]
    is_current: bool
    industry: str
    company_size: CompanySize
    description: str


class EducationModel(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_year: Annotated[int, Field(ge=1970, le=2030)]
    end_year: Annotated[int, Field(ge=1970, le=2035)]
    grade: Optional[str] = None
    tier: EducationTier = "unknown"


class SkillModel(BaseModel):
    name: str
    proficiency: Proficiency
    endorsements: Annotated[int, Field(ge=0)]
    duration_months: Annotated[int, Field(ge=0)] = 0


class CertificationModel(BaseModel):
    name: str
    issuer: str
    year: int


class LanguageModel(BaseModel):
    language: str
    proficiency: LangProficiency


class SalaryRangeModel(BaseModel):
    min: Annotated[float, Field(ge=0)]
    max: Annotated[float, Field(ge=0)]


class RedrobSignalsModel(BaseModel):
    profile_completeness_score: Annotated[float, Field(ge=0, le=100)]
    signup_date: str
    last_active_date: str
    open_to_work_flag: bool
    profile_views_received_30d: Annotated[int, Field(ge=0)]
    applications_submitted_30d: Annotated[int, Field(ge=0)]
    recruiter_response_rate: Annotated[float, Field(ge=0, le=1)]
    avg_response_time_hours: Annotated[float, Field(ge=0)]
    skill_assessment_scores: Dict[str, Annotated[float, Field(ge=0, le=100)]] = Field(
        default_factory=dict
    )
    connection_count: Annotated[int, Field(ge=0)]
    endorsements_received: Annotated[int, Field(ge=0)]
    notice_period_days: Annotated[int, Field(ge=0, le=180)]
    expected_salary_range_inr_lpa: SalaryRangeModel
    preferred_work_mode: WorkMode
    willing_to_relocate: bool
    github_activity_score: Annotated[float, Field(ge=-1, le=100)]
    search_appearance_30d: Annotated[int, Field(ge=0)]
    saved_by_recruiters_30d: Annotated[int, Field(ge=0)]
    interview_completion_rate: Annotated[float, Field(ge=0, le=1)]
    offer_acceptance_rate: Annotated[float, Field(ge=-1, le=1)]
    verified_email: bool
    verified_phone: bool
    linkedin_connected: bool


# ─────────────────────────────────────────
# Top-level candidate
# ─────────────────────────────────────────

class CandidateModel(BaseModel):
    candidate_id: str = Field(pattern=r"^CAND_\d{7}$")
    profile: ProfileModel
    career_history: List[CareerEntryModel] = Field(min_length=1, max_length=10)
    education: List[EducationModel] = Field(max_length=5)
    skills: List[SkillModel]
    certifications: List[CertificationModel] = Field(default_factory=list)
    languages: List[LanguageModel] = Field(default_factory=list)
    redrob_signals: RedrobSignalsModel

    @field_validator("candidate_id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v.startswith("CAND_"):
            raise ValueError("candidate_id must start with CAND_")
        return v
