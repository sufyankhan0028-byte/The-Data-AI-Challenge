"""
ParsedJD — comprehensive, fully-typed output of the JDParser.

Every field is documented with its source logic and downstream usage.
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, computed_field


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class SeniorityLevel(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"           # 0–2 yrs
    MID = "mid"                 # 2–5 yrs
    SENIOR = "senior"           # 5–8 yrs
    LEAD = "lead"               # 7–12 yrs, leads a small team
    PRINCIPAL = "principal"     # 10+ yrs, technical decision-maker
    STAFF = "staff"             # cross-team impact
    DIRECTOR = "director"       # people manager of managers
    VP = "vp"
    EXECUTIVE = "executive"     # C-suite
    UNKNOWN = "unknown"


class WorkMode(str, Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    FLEXIBLE = "flexible"
    UNKNOWN = "unknown"


class SkillContext(str, Enum):
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"
    NEGATIVE = "negative"       # "no experience with X required"


# ─────────────────────────────────────────────────────────────────────────────
# Sub-objects
# ─────────────────────────────────────────────────────────────────────────────

class SkillMention(BaseModel):
    """A skill extracted from the JD with its context."""

    model_config = {"frozen": True}

    name: str
    name_lower: str
    context: SkillContext
    source_section: str          # "requirements" | "preferred" | "full_text"
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]


class ExperienceRange(BaseModel):
    """Parsed experience requirement."""

    model_config = {"frozen": True}

    minimum: Optional[float] = None      # years
    maximum: Optional[float] = None      # years (None = unbounded)
    preferred: Optional[float] = None    # explicit preferred value if stated
    raw_text: str = ""                   # original matched string

    @computed_field  # type: ignore[misc]
    @property
    def midpoint(self) -> Optional[float]:
        if self.minimum is not None and self.maximum is not None:
            return (self.minimum + self.maximum) / 2
        return self.minimum


class LocationHint(BaseModel):
    """A location signal extracted from the JD."""

    model_config = {"frozen": True}

    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    work_mode: WorkMode = WorkMode.UNKNOWN
    relocation_offered: bool = False
    visa_sponsorship: bool = False


class StartupSignals(BaseModel):
    """Signals that indicate a startup / early-stage environment."""

    model_config = {"frozen": True}

    is_startup: bool = False
    funding_stage: Optional[str] = None  # "seed" | "series_a" | "series_b" | "series_c" | "growth"
    fast_paced_mentioned: bool = False
    ownership_culture: bool = False      # "own your work", "high ownership"
    equity_mentioned: bool = False
    flat_hierarchy: bool = False
    scrappy_culture: bool = False
    signals_found: List[str] = Field(default_factory=list)


class LeadershipSignals(BaseModel):
    """Signals that indicate a people-management or technical-leadership role."""

    model_config = {"frozen": True}

    requires_management: bool = False
    min_direct_reports: Optional[int] = None
    max_direct_reports: Optional[int] = None
    hiring_manager_role: bool = False    # explicitly asked to hire
    cross_functional_leadership: bool = False
    technical_lead: bool = False
    strategy_ownership: bool = False
    signals_found: List[str] = Field(default_factory=list)


class NegativeSignal(BaseModel):
    """Something the JD explicitly does NOT want."""

    model_config = {"frozen": True}

    signal: str
    category: str   # "skill_exclusion" | "seniority_cap" | "culture_mismatch" | "availability"
    raw_text: str


# ─────────────────────────────────────────────────────────────────────────────
# Top-level ParsedJD
# ─────────────────────────────────────────────────────────────────────────────

class ParsedJD(BaseModel):
    """
    Complete structured output of JDParser.

    Downstream consumers:
      • FeatureEngineering — uses must_have_skills, experience, seniority
      • RetrievalEngine    — uses must_have_skills, industries, location
      • RankingEngine      — uses all fields for weighted scoring
      • ExplainerService   — uses negative_signals, seniority, leadership_signals
    """

    # ── Raw ───────────────────────────────────────────────────────────────
    raw_text: str
    char_count: int
    section_map: Dict[str, str] = Field(default_factory=dict)  # section_name → text

    # ── Skills ────────────────────────────────────────────────────────────
    must_have_skills: List[SkillMention] = Field(default_factory=list)
    nice_to_have_skills: List[SkillMention] = Field(default_factory=list)

    # ── Experience ────────────────────────────────────────────────────────
    experience: ExperienceRange = Field(default_factory=ExperienceRange)
    minimum_experience: Optional[float] = None   # convenience alias
    maximum_experience: Optional[float] = None   # convenience alias

    # ── Role context ──────────────────────────────────────────────────────
    seniority: SeniorityLevel = SeniorityLevel.UNKNOWN
    seniority_confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    required_industries: List[str] = Field(default_factory=list)
    target_titles: List[str] = Field(default_factory=list)

    # ── Location ──────────────────────────────────────────────────────────
    preferred_location: LocationHint = Field(default_factory=LocationHint)

    # ── Company culture ───────────────────────────────────────────────────
    startup_signals: StartupSignals = Field(default_factory=StartupSignals)
    leadership_signals: LeadershipSignals = Field(default_factory=LeadershipSignals)

    # ── Negative signals ──────────────────────────────────────────────────
    negative_signals: List[NegativeSignal] = Field(default_factory=list)

    # ── Salary ────────────────────────────────────────────────────────────
    salary_min_lpa: Optional[float] = None
    salary_max_lpa: Optional[float] = None
    work_mode: WorkMode = WorkMode.UNKNOWN

    # ── Embedding text ────────────────────────────────────────────────────
    summary_for_embedding: str = ""

    # ── Convenience computed views ────────────────────────────────────────

    @computed_field  # type: ignore[misc]
    @property
    def must_have_skill_names(self) -> List[str]:
        return [s.name for s in self.must_have_skills]

    @computed_field  # type: ignore[misc]
    @property
    def nice_to_have_skill_names(self) -> List[str]:
        return [s.name for s in self.nice_to_have_skills]

    @computed_field  # type: ignore[misc]
    @property
    def all_skill_names(self) -> List[str]:
        seen: set = set()
        out = []
        for s in self.must_have_skills + self.nice_to_have_skills:
            if s.name_lower not in seen:
                seen.add(s.name_lower)
                out.append(s.name)
        return out

    @computed_field  # type: ignore[misc]
    @property
    def is_senior_role(self) -> bool:
        return self.seniority in (
            SeniorityLevel.SENIOR, SeniorityLevel.LEAD, SeniorityLevel.PRINCIPAL,
            SeniorityLevel.STAFF, SeniorityLevel.DIRECTOR, SeniorityLevel.VP,
            SeniorityLevel.EXECUTIVE,
        )

    @computed_field  # type: ignore[misc]
    @property
    def requires_management(self) -> bool:
        return self.leadership_signals.requires_management
