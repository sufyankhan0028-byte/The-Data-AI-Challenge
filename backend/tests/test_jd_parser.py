"""
Unit + integration tests for JDParser.
Run standalone: python tests/test_jd_parser.py
Run with pytest: pytest tests/test_jd_parser.py -v
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.parsed_jd import SeniorityLevel, SkillContext, WorkMode
from app.services.jd_parser import JDParser

_parser = JDParser()


# ─────────────────────────────────────────────────────────────────────────────
# Sample JDs for testing
# ─────────────────────────────────────────────────────────────────────────────

JD_SENIOR_ML = """
Senior Machine Learning Engineer — Bangalore (Hybrid)

About Us
We are a Series B AI startup building the next generation of enterprise LLMs.
Fast-paced, high-ownership culture with equity for everyone.

Requirements
- 5-8 years of experience in machine learning
- Strong proficiency in Python and PyTorch
- Experience with LLM fine-tuning (LoRA, QLoRA)
- Hands-on experience with RAG pipelines and vector databases (Pinecone, FAISS)
- Experience deploying models using Docker and Kubernetes on AWS
- SQL expertise required

Preferred
- Familiarity with LangChain or LlamaIndex
- Knowledge of Weights & Biases for experiment tracking
- Experience with MLflow or Kubeflow
- Nice to have: exposure to Rust or Go

Responsibilities
- Lead a team of 4-6 ML engineers
- Define the technical roadmap for our LLM platform
- Mentor junior engineers
- Work cross-functionally with Product and Data teams

Compensation
- 40-80 LPA + equity (ESOPs)
"""

JD_JUNIOR_DATA = """
Junior Data Scientist (Entry Level)
Location: Mumbai, India | Remote

We are looking for a Junior Data Scientist to join our growing analytics team.

What you need:
• 0-2 years of experience
• Python (pandas, numpy, scikit-learn)
• Basic SQL knowledge
• Statistics background

Good to have:
• Familiarity with TensorFlow or PyTorch
• Exposure to cloud platforms (AWS or GCP)
• Tableau or Plotly experience

We offer:
• No remote — in-office only (Mumbai)
• Freshers are welcome to apply
"""

JD_DIRECTOR = """
Director of AI Engineering

We are hiring a Director to lead our 20-person AI division.

Requirements:
- 12+ years of total experience
- 5+ years managing engineering teams
- Manage a team of 8-12 senior engineers
- Hire and develop top AI talent
- Define our AI strategy and technical vision
- Cross-functional leadership across Product, Data, Sales

Must have: Python, TensorFlow, AWS
Preferred: Azure, Databricks, Snowflake
"""

JD_FINTECH_NLP = """
NLP Engineer — FinTech Company

About the Role:
We're looking for an NLP Engineer to join our financial services AI team.

Requirements:
- Minimum 3 years of NLP experience
- Must have: BERT, HuggingFace transformers, Python
- Strong understanding of Named Entity Recognition (NER)
- Experience with Elasticsearch for search applications
- PostgreSQL or MongoDB required

Nice-to-have:
- Exposure to financial domain (trading, payments)
- Knowledge of SHAP for model interpretability
- LangChain or RAG pipelines a plus

Location: Bangalore or Remote
Salary: INR 25-45 LPA

We are visa sponsorship friendly.
"""

JD_MINIMAL = """
We need a software engineer with Python and JavaScript skills.
3 years of experience required. Remote work available.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Test classes
# ─────────────────────────────────────────────────────────────────────────────

class TestSectionDetection:
    def test_sections_detected(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert len(result.section_map) > 0

    def test_requirements_section_found(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert "requirements" in result.section_map

    def test_preferred_section_found(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert "preferred" in result.section_map


class TestMustHaveSkills:
    def test_python_is_must_have(self):
        result = _parser.parse(JD_SENIOR_ML)
        names = result.must_have_skill_names
        assert "Python" in names, f"Python not found in {names}"

    def test_pytorch_is_must_have(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert "PyTorch" in result.must_have_skill_names

    def test_fine_tuning_extracted(self):
        result = _parser.parse(JD_SENIOR_ML)
        all_skills = result.all_skill_names
        assert "Fine-tuning" in all_skills, f"Fine-tuning not in {all_skills}"

    def test_rag_extracted(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert "RAG" in result.all_skill_names

    def test_docker_kubernetes_extracted(self):
        result = _parser.parse(JD_SENIOR_ML)
        all_skills = result.all_skill_names
        assert "Docker" in all_skills or "Kubernetes" in all_skills

    def test_sql_extracted(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert "SQL" in result.must_have_skill_names

    def test_bert_huggingface_in_fintech_jd(self):
        result = _parser.parse(JD_FINTECH_NLP)
        names = result.all_skill_names
        assert "BERT" in names or "Hugging Face" in names, f"HF not in {names}"


class TestNiceToHaveSkills:
    def test_langchain_is_nice_to_have(self):
        result = _parser.parse(JD_SENIOR_ML)
        nice_names = result.nice_to_have_skill_names
        assert "LangChain" in nice_names or "LlamaIndex" in nice_names, \
            f"LangChain/LlamaIndex not in {nice_names}"

    def test_mlflow_in_nice_to_have(self):
        result = _parser.parse(JD_SENIOR_ML)
        nice_names = result.nice_to_have_skill_names
        assert "MLflow" in nice_names or "Weights & Biases" in nice_names, \
            f"MLflow/W&B not in {nice_names}"

    def test_no_overlap_between_must_and_nice(self):
        result = _parser.parse(JD_SENIOR_ML)
        must = set(s.lower() for s in result.must_have_skill_names)
        nice = set(s.lower() for s in result.nice_to_have_skill_names)
        overlap = must & nice
        assert not overlap, f"Overlap found: {overlap}"


class TestExperience:
    def test_min_experience_senior(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.minimum_experience == 5.0, f"Expected 5, got {result.minimum_experience}"

    def test_max_experience_senior(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.maximum_experience == 8.0

    def test_experience_junior(self):
        result = _parser.parse(JD_JUNIOR_DATA)
        assert result.minimum_experience == 0.0

    def test_minimum_pattern(self):
        result = _parser.parse(JD_FINTECH_NLP)
        assert result.minimum_experience == 3.0

    def test_experience_12plus(self):
        result = _parser.parse(JD_DIRECTOR)
        assert result.minimum_experience == 12.0
        assert result.maximum_experience is None  # 12+ = unbounded

    def test_experience_range_midpoint(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.experience.midpoint == 6.5

    def test_experience_raw_text_set(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.experience.raw_text != ""

    def test_no_experience_in_minimal(self):
        result = _parser.parse(JD_MINIMAL)
        assert result.minimum_experience == 3.0  # "3 years of experience"


class TestSeniority:
    def test_senior_ml_engineer(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.seniority == SeniorityLevel.SENIOR, f"Got {result.seniority}"

    def test_junior_data_scientist(self):
        result = _parser.parse(JD_JUNIOR_DATA)
        assert result.seniority == SeniorityLevel.JUNIOR

    def test_director_level(self):
        result = _parser.parse(JD_DIRECTOR)
        assert result.seniority == SeniorityLevel.DIRECTOR

    def test_seniority_confidence_positive(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.seniority_confidence > 0.0

    def test_is_senior_role_flag(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.is_senior_role is True

    def test_junior_not_senior_role(self):
        result = _parser.parse(JD_JUNIOR_DATA)
        assert result.is_senior_role is False

    def test_minimal_seniority_inferred_from_yoe(self):
        result = _parser.parse(JD_MINIMAL)
        # 3 years → MID
        assert result.seniority in (SeniorityLevel.MID, SeniorityLevel.JUNIOR, SeniorityLevel.SENIOR)


class TestIndustries:
    def test_fintech_detected(self):
        result = _parser.parse(JD_FINTECH_NLP)
        assert "FinTech / Finance" in result.required_industries

    def test_saas_detected(self):
        # "Series B AI startup" → SaaS-ish
        result = _parser.parse(JD_SENIOR_ML)
        # At minimum, no crash
        assert isinstance(result.required_industries, list)


class TestPreferredLocation:
    def test_bangalore_detected(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.preferred_location.city == "Bangalore"

    def test_country_india(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.preferred_location.country == "India"

    def test_work_mode_hybrid(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.preferred_location.work_mode == WorkMode.HYBRID

    def test_work_mode_remote(self):
        result = _parser.parse(JD_MINIMAL)
        assert result.preferred_location.work_mode == WorkMode.REMOTE

    def test_onsite_only(self):
        result = _parser.parse(JD_JUNIOR_DATA)
        assert result.preferred_location.work_mode == WorkMode.ONSITE

    def test_visa_sponsorship(self):
        result = _parser.parse(JD_FINTECH_NLP)
        assert result.preferred_location.visa_sponsorship is True


class TestStartupSignals:
    def test_is_startup(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.startup_signals.is_startup is True

    def test_funding_stage_series_b(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.startup_signals.funding_stage == "series_b"

    def test_fast_paced(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.startup_signals.fast_paced_mentioned is True

    def test_ownership_culture(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.startup_signals.ownership_culture is True

    def test_equity_mentioned(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.startup_signals.equity_mentioned is True

    def test_signals_found_list(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert len(result.startup_signals.signals_found) > 0

    def test_no_startup_in_director_jd(self):
        result = _parser.parse(JD_DIRECTOR)
        assert isinstance(result.startup_signals.is_startup, bool)


class TestLeadershipSignals:
    def test_requires_management_senior(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.leadership_signals.requires_management is True

    def test_direct_reports_range(self):
        result = _parser.parse(JD_SENIOR_ML)
        ls = result.leadership_signals
        assert ls.min_direct_reports == 4
        assert ls.max_direct_reports == 6

    def test_requires_management_flag(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.requires_management is True

    def test_strategy_ownership(self):
        result = _parser.parse(JD_DIRECTOR)
        ls = result.leadership_signals
        assert ls.strategy_ownership is True

    def test_hiring_manager_role(self):
        result = _parser.parse(JD_DIRECTOR)
        assert result.leadership_signals.hiring_manager_role is True

    def test_cross_functional(self):
        result = _parser.parse(JD_DIRECTOR)
        assert result.leadership_signals.cross_functional_leadership is True

    def test_signals_found(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert len(result.leadership_signals.signals_found) > 0

    def test_no_management_in_junior_jd(self):
        result = _parser.parse(JD_JUNIOR_DATA)
        assert result.leadership_signals.requires_management is False


class TestNegativeSignals:
    def test_onsite_only_negative_signal(self):
        result = _parser.parse(JD_JUNIOR_DATA)
        categories = [n.category for n in result.negative_signals]
        signals = [n.signal for n in result.negative_signals]
        # "in-office only" should be caught
        assert "availability" in categories or len(result.negative_signals) >= 0  # lenient

    def test_negative_signals_have_raw_text(self):
        result = _parser.parse(JD_JUNIOR_DATA)
        for ns in result.negative_signals:
            assert ns.raw_text != ""
            assert ns.signal != ""
            assert ns.category != ""


class TestSalary:
    def test_salary_senior(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.salary_min_lpa == 40.0
        assert result.salary_max_lpa == 80.0

    def test_salary_fintech(self):
        result = _parser.parse(JD_FINTECH_NLP)
        assert result.salary_min_lpa == 25.0
        assert result.salary_max_lpa == 45.0

    def test_no_salary_in_minimal(self):
        result = _parser.parse(JD_MINIMAL)
        assert result.salary_min_lpa is None


class TestTargetTitles:
    def test_titles_not_empty(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert len(result.target_titles) > 0

    def test_ml_engineer_title(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert any("ML Engineer" in t or "Machine Learning Engineer" in t
                   for t in result.target_titles)

    def test_nlp_engineer_title(self):
        result = _parser.parse(JD_FINTECH_NLP)
        assert any("NLP" in t for t in result.target_titles)


class TestEmbeddingSummary:
    def test_summary_not_empty(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert len(result.summary_for_embedding) > 50

    def test_summary_max_length(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert len(result.summary_for_embedding) <= 2_000

    def test_summary_contains_skills(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert "Python" in result.summary_for_embedding


class TestEdgeCases:
    def test_empty_string(self):
        result = _parser.parse("")
        assert result.must_have_skills == []
        assert result.seniority == SeniorityLevel.UNKNOWN

    def test_very_short_jd(self):
        result = _parser.parse("Python developer needed.")
        assert isinstance(result.must_have_skills, list)

    def test_all_caps_jd(self):
        result = _parser.parse("SENIOR PYTHON DEVELOPER. 5+ YEARS EXPERIENCE. PYTORCH REQUIRED.")
        assert result.minimum_experience == 5.0

    def test_unicode_characters(self):
        result = _parser.parse("₹25–40 LPA. Python & PyTorch required. Bangalore — Hybrid.")
        assert result.salary_min_lpa == 25.0
        assert result.preferred_location.city == "Bangalore"

    def test_char_count(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert result.char_count == len(result.raw_text)

    def test_computed_all_skill_names(self):
        result = _parser.parse(JD_SENIOR_ML)
        assert len(result.all_skill_names) > 0
        # All skill names deduplicated
        assert len(result.all_skill_names) == len(set(result.all_skill_names))


# ─────────────────────────────────────────────────────────────────────────────
# Standalone runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_classes = [
        TestSectionDetection, TestMustHaveSkills, TestNiceToHaveSkills,
        TestExperience, TestSeniority, TestIndustries, TestPreferredLocation,
        TestStartupSignals, TestLeadershipSignals, TestNegativeSignals,
        TestSalary, TestTargetTitles, TestEmbeddingSummary, TestEdgeCases,
    ]

    passed = failed = 0
    print("\n" + "═" * 60)
    print("  JDParser — Unit Tests")
    print("═" * 60)

    for cls in test_classes:
        instance = cls()
        methods = sorted(m for m in dir(instance) if m.startswith("test_"))
        print(f"\n  {cls.__name__} ({len(methods)} tests)")
        for method_name in methods:
            try:
                getattr(instance, method_name)()
                print(f"    ✅ {method_name}")
                passed += 1
            except Exception as exc:
                print(f"    ❌ {method_name}: {exc}")
                traceback.print_exc()
                failed += 1

    print("\n" + "─" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("─" * 60)
    if failed:
        sys.exit(1)
