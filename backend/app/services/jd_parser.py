"""
JDParser Service
================
Converts raw job description text → structured ParsedJD using:
  • Regex (compiled, with named groups)
  • In-house lightweight NLP (tokenisation, n-grams, sentence segmentation,
    context windows, section detection)
  • Curated taxonomies (skills, industries, locations, signal phrases)

No external APIs, no spaCy download, no network calls — fully offline.

Design:
  • Stateless class — instantiate once, parse many JDs.
  • Section-aware — splits JD into labelled sections before extracting.
  • Context-aware skill extraction — determines must-have vs. nice-to-have
    from the surrounding sentence, not just the section header.
  • Multi-pattern YoE extraction — handles "3-5 years", "3+ years",
    "minimum 5 years", "atleast 3 yrs", "5 to 8 years" etc.

Usage:
    parser = JDParser()
    result: ParsedJD = parser.parse(jd_text)
    print(result.must_have_skill_names)
    print(result.seniority)
    print(result.startup_signals.is_startup)
"""
from __future__ import annotations

import re
import string
from collections import Counter, defaultdict
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from app.schemas.parsed_jd import (
    ExperienceRange,
    LeadershipSignals,
    LocationHint,
    NegativeSignal,
    ParsedJD,
    SeniorityLevel,
    SkillContext,
    SkillMention,
    StartupSignals,
    WorkMode,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Section taxonomy
# ═════════════════════════════════════════════════════════════════════════════

_SECTION_HEADERS: Dict[str, List[str]] = {
    "requirements": [
        "requirements", "required", "must have", "must-have", "what you need",
        "what we need", "you must", "what you'll need", "minimum qualifications",
        "basic qualifications", "mandatory", "essential",
    ],
    "preferred": [
        "preferred", "nice to have", "nice-to-have", "bonus", "good to have",
        "good-to-have", "plus", "additional", "preferred qualifications",
        "desired", "ideally", "would be great",
    ],
    "responsibilities": [
        "responsibilities", "what you'll do", "what you will do",
        "role & responsibilities", "key responsibilities", "your role",
        "the job", "about the role", "duties",
    ],
    "about_company": [
        "about us", "about the company", "who we are", "our story",
        "company overview", "at [company]",
    ],
    "perks": [
        "perks", "benefits", "what we offer", "compensation", "why join",
        "what's in it for you",
    ],
}

# Context phrases that mark must-have skills in a sentence
_MUST_HAVE_SENTINELS: FrozenSet[str] = frozenset({
    "required", "must have", "must-have", "mandatory", "essential",
    "you must", "need to have", "need to know", "is required",
    "are required", "experience with", "proficiency in",
    "strong experience", "proven experience", "hands-on experience",
    "solid understanding", "deep understanding", "expertise in",
    "background in", "demonstrated experience", "minimum",
})

# Context phrases that mark nice-to-have skills
_NICE_TO_HAVE_SENTINELS: FrozenSet[str] = frozenset({
    "preferred", "nice to have", "nice-to-have", "bonus", "plus",
    "good to have", "ideal", "ideally", "familiarity with",
    "exposure to", "knowledge of", "experience with would be",
    "would be great", "advantageous", "desirable", "a plus",
    "not required", "optional",
})

# Phrases that signal the NEGATIVE form ("you don't need X")
_NEGATION_SENTINELS: FrozenSet[str] = frozenset({
    "no experience required", "not required", "no prior", "without",
    "regardless of", "even if you don't", "don't need",
})


# ═════════════════════════════════════════════════════════════════════════════
# Skill taxonomy (comprehensive, multi-domain)
# ═════════════════════════════════════════════════════════════════════════════

# Format: canonical_name → (set of aliases in lower-case)
_SKILL_TAXONOMY: Dict[str, Set[str]] = {
    # ── Programming languages ─────────────────────────────────────────────
    "Python": {"python"},
    "JavaScript": {"javascript", "js"},
    "TypeScript": {"typescript", "ts"},
    "Java": {"java"},
    "Go": {"golang", "go lang"},
    "Rust": {"rust"},
    "C++": {"c++", "c plus plus", "cpp"},
    "C#": {"c#", "c sharp", "csharp"},
    "Scala": {"scala"},
    "R": {r"\br\b", "r language", "r programming"},
    "SQL": {"sql", "structured query language"},
    "Bash": {"bash", "shell scripting", "bash scripting"},

    # ── ML / DL frameworks ────────────────────────────────────────────────
    "PyTorch": {"pytorch", "torch"},
    "TensorFlow": {"tensorflow", "tf"},
    "Keras": {"keras"},
    "scikit-learn": {"scikit-learn", "sklearn", "scikit learn"},
    "XGBoost": {"xgboost", "xgb"},
    "LightGBM": {"lightgbm", "lgbm"},
    "CatBoost": {"catboost"},
    "JAX": {"jax"},
    "Hugging Face": {"hugging face", "huggingface", "hf transformers"},
    "ONNX": {"onnx"},

    # ── LLM / Generative AI ───────────────────────────────────────────────
    "LLM": {"llm", "large language model", "large language models"},
    "GPT": {"gpt", "gpt-4", "gpt4", "gpt-3.5", "chatgpt"},
    "BERT": {"bert", "roberta", "distilbert", "albert"},
    "Fine-tuning": {"fine-tuning", "fine tuning", "finetuning", "lora", "qlora", "peft"},
    "RAG": {"rag", "retrieval augmented generation", "retrieval-augmented"},
    "LangChain": {"langchain", "lang chain"},
    "LlamaIndex": {"llamaindex", "llama index", "llama-index"},
    "Prompt Engineering": {"prompt engineering", "prompting", "prompt design"},
    "Embeddings": {"embeddings", "word embeddings", "sentence embeddings", "text embeddings"},
    "Generative AI": {"generative ai", "gen ai", "genai"},
    "Stable Diffusion": {"stable diffusion"},
    "OpenAI API": {"openai", "openai api"},
    "Anthropic": {"anthropic", "claude api"},

    # ── NLP ───────────────────────────────────────────────────────────────
    "NLP": {"nlp", "natural language processing", "natural-language processing"},
    "Text Mining": {"text mining", "text analysis", "information extraction"},
    "Named Entity Recognition": {"ner", "named entity recognition"},
    "Sentiment Analysis": {"sentiment analysis", "opinion mining"},
    "Speech Recognition": {"speech recognition", "asr", "automatic speech recognition"},
    "TTS": {"tts", "text to speech", "text-to-speech"},

    # ── Computer Vision ───────────────────────────────────────────────────
    "Computer Vision": {"computer vision", "cv"},
    "OpenCV": {"opencv"},
    "Image Classification": {"image classification"},
    "Object Detection": {"object detection", "yolo", "yolov5", "yolov8"},
    "Image Segmentation": {"image segmentation", "semantic segmentation"},
    "CNNs": {"cnn", "convolutional neural network", "convolutional"},

    # ── MLOps / DevOps ────────────────────────────────────────────────────
    "MLflow": {"mlflow"},
    "MLOps": {"mlops", "ml ops"},
    "Kubeflow": {"kubeflow"},
    "Airflow": {"airflow", "apache airflow"},
    "DVC": {"dvc", "data version control"},
    "Weights & Biases": {"weights & biases", "wandb", "w&b"},
    "Docker": {"docker", "containerization", "containers"},
    "Kubernetes": {"kubernetes", "k8s"},
    "CI/CD": {"ci/cd", "cicd", "continuous integration", "continuous deployment", "jenkins", "github actions"},

    # ── Cloud ─────────────────────────────────────────────────────────────
    "AWS": {"aws", "amazon web services", "sagemaker", "aws sagemaker", "ec2", "s3", "lambda"},
    "GCP": {"gcp", "google cloud", "vertex ai", "bigquery", "gcp vertex"},
    "Azure": {"azure", "microsoft azure", "azure ml", "azure openai"},

    # ── Data engineering ──────────────────────────────────────────────────
    "Spark": {"spark", "apache spark", "pyspark"},
    "Kafka": {"kafka", "apache kafka"},
    "Flink": {"flink", "apache flink"},
    "Airflow": {"airflow"},
    "dbt": {"dbt", "data build tool"},
    "Snowflake": {"snowflake"},
    "Databricks": {"databricks"},
    "DuckDB": {"duckdb"},
    "Redshift": {"redshift", "amazon redshift"},
    "BigQuery": {"bigquery", "bq"},
    "PostgreSQL": {"postgresql", "postgres"},
    "MySQL": {"mysql"},
    "Redis": {"redis"},
    "MongoDB": {"mongodb", "mongo"},
    "Elasticsearch": {"elasticsearch", "elastic search"},
    "Pinecone": {"pinecone"},
    "Weaviate": {"weaviate"},
    "Chroma": {"chromadb", "chroma db"},
    "Milvus": {"milvus"},
    "FAISS": {"faiss"},

    # ── Web frameworks ────────────────────────────────────────────────────
    "FastAPI": {"fastapi", "fast api"},
    "Flask": {"flask"},
    "Django": {"django"},
    "React": {"react", "reactjs", "react.js"},
    "Node.js": {"node.js", "nodejs", "node js"},
    "Next.js": {"next.js", "nextjs"},

    # ── Statistics / Math ─────────────────────────────────────────────────
    "Statistical Modeling": {"statistical modeling", "statistical modelling", "statistics"},
    "A/B Testing": {"a/b testing", "ab testing", "experimentation"},
    "Feature Engineering": {"feature engineering"},
    "SHAP": {"shap", "shapley"},
    "Bayesian Methods": {"bayesian", "bayesian statistics", "bayesian inference"},
    "Time Series": {"time series", "forecasting", "arima", "prophet"},

    # ── Reinforcement Learning ────────────────────────────────────────────
    "Reinforcement Learning": {"reinforcement learning", "rl", "deep rl", "deep reinforcement"},

    # ── General tools ─────────────────────────────────────────────────────
    "Git": {"git", "github", "gitlab", "bitbucket", "version control"},
    "REST API": {"rest", "rest api", "restful", "api design"},
    "GraphQL": {"graphql"},
    "Linux": {"linux", "unix"},
    "Terraform": {"terraform", "infrastructure as code", "iac"},
    "NumPy": {"numpy"},
    "Pandas": {"pandas"},
    "Matplotlib": {"matplotlib", "seaborn", "plotly", "visualization"},
    "Jupyter": {"jupyter", "jupyter notebook", "jupyterlab"},
}

# Build reverse lookup: alias_lower → canonical
_ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canonical, aliases in _SKILL_TAXONOMY.items():
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias] = canonical
# Also map canonical lower → canonical
for canonical in _SKILL_TAXONOMY:
    _ALIAS_TO_CANONICAL[canonical.lower()] = canonical


# ═════════════════════════════════════════════════════════════════════════════
# Industry taxonomy
# ═════════════════════════════════════════════════════════════════════════════

_INDUSTRY_PATTERNS: List[Tuple[str, List[str]]] = [
    ("FinTech / Finance", ["fintech", "financial services", "banking", "payments", "trading",
                            "hedge fund", "investment bank", "insurance"]),
    ("HealthTech / Healthcare", ["healthtech", "health tech", "healthcare", "medical",
                                  "pharma", "biotech", "clinical"]),
    ("EdTech / Education", ["edtech", "ed tech", "education", "e-learning", "lms"]),
    ("E-Commerce / Retail", ["e-commerce", "ecommerce", "retail", "marketplace", "shopify"]),
    ("SaaS / Software", ["saas", "software as a service", "software company", "b2b software"]),
    ("Cybersecurity", ["cybersecurity", "cyber security", "infosec", "security"]),
    ("Logistics / Supply Chain", ["logistics", "supply chain", "transportation", "fleet"]),
    ("Gaming", ["gaming", "game development", "game studio"]),
    ("Media / Entertainment", ["media", "entertainment", "streaming", "content"]),
    ("Automotive", ["automotive", "ev", "electric vehicle", "autonomous vehicles"]),
    ("Manufacturing / Industry", ["manufacturing", "industrial", "iot", "robotics"]),
    ("Consulting", ["consulting", "management consulting", "advisory"]),
    ("IT Services", ["it services", "outsourcing", "bpo", "managed services"]),
    ("Agriculture / AgriTech", ["agriculture", "agritech", "agri-tech", "farming"]),
    ("Real Estate / PropTech", ["real estate", "proptech", "prop-tech"]),
]


# ═════════════════════════════════════════════════════════════════════════════
# Location taxonomy
# ═════════════════════════════════════════════════════════════════════════════

_CITY_MAP: Dict[str, Tuple[str, str]] = {   # lower → (city, country)
    "bangalore": ("Bangalore", "India"),
    "bengaluru": ("Bangalore", "India"),
    "mumbai": ("Mumbai", "India"),
    "delhi": ("Delhi", "India"),
    "new delhi": ("New Delhi", "India"),
    "hyderabad": ("Hyderabad", "India"),
    "chennai": ("Chennai", "India"),
    "pune": ("Pune", "India"),
    "gurgaon": ("Gurgaon", "India"),
    "gurugram": ("Gurgaon", "India"),
    "noida": ("Noida", "India"),
    "kolkata": ("Kolkata", "India"),
    "ahmedabad": ("Ahmedabad", "India"),
    "san francisco": ("San Francisco", "USA"),
    "new york": ("New York", "USA"),
    "seattle": ("Seattle", "USA"),
    "austin": ("Austin", "USA"),
    "boston": ("Boston", "USA"),
    "london": ("London", "UK"),
    "berlin": ("Berlin", "Germany"),
    "singapore": ("Singapore", "Singapore"),
    "toronto": ("Toronto", "Canada"),
    "sydney": ("Sydney", "Australia"),
    "dubai": ("Dubai", "UAE"),
}

_COUNTRY_MAP: Dict[str, str] = {
    "india": "India",
    "usa": "USA",
    "united states": "USA",
    "us": "USA",
    "uk": "UK",
    "united kingdom": "UK",
    "canada": "Canada",
    "australia": "Australia",
    "germany": "Germany",
    "singapore": "Singapore",
}


# ═════════════════════════════════════════════════════════════════════════════
# Seniority taxonomy
# ═════════════════════════════════════════════════════════════════════════════

_SENIORITY_PATTERNS: List[Tuple[SeniorityLevel, float, List[str]]] = [
    # (level, confidence, trigger_phrases)
    (SeniorityLevel.INTERN, 0.95, [
        "intern", "internship", "apprentice", "trainee",
    ]),
    (SeniorityLevel.JUNIOR, 0.85, [
        "junior", "entry level", "entry-level", "associate",
        "0-2 years", "0 to 2 years", "fresher",
    ]),
    (SeniorityLevel.MID, 0.80, [
        "mid level", "mid-level", "2-5 years", "2 to 5 years",
        "mid-senior", "3-5 years",
    ]),
    (SeniorityLevel.SENIOR, 0.90, [
        "senior", "sr.", "sr ", "5+ years", "5-8 years",
        "5 to 8 years", "7+ years", "experienced",
    ]),
    (SeniorityLevel.LEAD, 0.90, [
        "lead", "tech lead", "team lead", "technical lead",
        "engineering lead", "squad lead",
    ]),
    (SeniorityLevel.PRINCIPAL, 0.90, [
        "principal", "staff engineer", "distinguished",
        "10+ years", "10 to 15 years",
    ]),
    (SeniorityLevel.STAFF, 0.85, [
        "staff engineer", "staff ml", "staff data scientist",
    ]),
    (SeniorityLevel.DIRECTOR, 0.92, [
        "director", "head of engineering", "head of ai", "head of data",
        "head of product", "vp of engineering", "vp engineering",
    ]),
    (SeniorityLevel.VP, 0.95, [
        "vice president", "svp", "evp",
    ]),
    (SeniorityLevel.EXECUTIVE, 0.95, [
        "cto", "chief technology officer", "ceo", "coo",
        "chief data officer", "c-suite",
    ]),
]


# ═════════════════════════════════════════════════════════════════════════════
# Startup signals taxonomy
# ═════════════════════════════════════════════════════════════════════════════

_STARTUP_TRIGGERS: Dict[str, str] = {
    # phrase → attribute name in StartupSignals
    "seed": "funding_stage:seed",
    "series a": "funding_stage:series_a",
    "series b": "funding_stage:series_b",
    "series c": "funding_stage:series_c",
    "series d": "funding_stage:series_d",
    "growth stage": "funding_stage:growth",
    "pre-ipo": "funding_stage:pre_ipo",
    "vc-backed": "is_startup",
    "venture-backed": "is_startup",
    "funded startup": "is_startup",
    "fast-paced": "fast_paced_mentioned",
    "fast paced": "fast_paced_mentioned",
    "move fast": "fast_paced_mentioned",
    "rapidly growing": "fast_paced_mentioned",
    "high-growth": "fast_paced_mentioned",
    "high growth": "fast_paced_mentioned",
    "high ownership": "ownership_culture",
    "high-ownership": "ownership_culture",
    "own your work": "ownership_culture",
    "take ownership": "ownership_culture",
    "bias for action": "ownership_culture",
    "strong sense of ownership": "ownership_culture",
    "scrappy": "scrappy_culture",
    "wear many hats": "scrappy_culture",
    "generalist": "scrappy_culture",
    "flat structure": "flat_hierarchy",
    "flat hierarchy": "flat_hierarchy",
    "no bureaucracy": "flat_hierarchy",
    "equity": "equity_mentioned",
    "esop": "equity_mentioned",
    "stock options": "equity_mentioned",
    "vesting": "equity_mentioned",
    "startup": "is_startup",
    "early stage": "is_startup",
    "early-stage": "is_startup",
    "seed-funded": "is_startup",
}


# ═════════════════════════════════════════════════════════════════════════════
# Leadership signals taxonomy
# ═════════════════════════════════════════════════════════════════════════════

_LEADERSHIP_TRIGGERS: List[Tuple[str, str]] = [
    # (regex or phrase, attribute)
    (r"manage\s+a\s+team", "requires_management"),
    (r"manage\s+\d+\s*(?:engineers?|data scientists?|people|reports?)", "requires_management"),
    (r"people\s+manager", "requires_management"),
    (r"people\s+management", "requires_management"),
    (r"(\d+)\s*(?:to|-)\s*(\d+)\s*(?:direct)?\s*reports?", "direct_reports_range"),
    (r"team\s+of\s+(\d+)\s*(?:to|-)\s*(\d+)", "direct_reports_range"),
    (r"team\s+of\s+(\d+)\+?", "min_direct_reports"),
    (r"(\d+)\+?\s*(?:direct)?\s*reports?", "min_direct_reports"),
    (r"lead\s+(?:and\s+)?(?:grow|build|scale|develop|mentor)\s+(?:a\s+)?(?:team|engineers?|scientists?)", "requires_management"),
    (r"build\s+(?:out\s+)?(?:and\s+)?(?:lead|grow|scale)\s+(?:a\s+)?team", "requires_management"),
    (r"grow\s+the\s+team", "hiring_manager_role"),
    (r"hire\s+(?:and\s+develop)?|hiring\s+(?:and\s+developing)?|build\s+the\s+team", "hiring_manager_role"),
    (r"cross[\s-]functional", "cross_functional_leadership"),
    (r"work\s+(?:closely\s+)?with\s+(?:product|design|sales|marketing|business)\s+teams?", "cross_functional_leadership"),
    (r"define\s+(?:the\s+)?(?:technical\s+)?(?:vision|roadmap|strategy|direction)", "strategy_ownership"),
    (r"technical\s+(?:vision|roadmap|strategy|direction)", "strategy_ownership"),
    (r"drive\s+(?:the\s+)?(?:technical|engineering)\s+(?:vision|roadmap|strategy)", "strategy_ownership"),
    (r"tech(?:nical)?\s+lead(?:ership)?(?:\s+of\s+(?:the\s+)?team)?", "technical_lead"),
    (r"lead\s+(?:the\s+)?(?:technical|engineering|architecture)\s+(?:decisions?|work|direction)", "technical_lead"),
    (r"mentor(?:ing)?\s+(?:junior|mid[\s-]level|other)?\s*(?:engineers?|developers?|scientists?)", "technical_lead"),
]


# ═════════════════════════════════════════════════════════════════════════════
# Negative signal taxonomy
# ═════════════════════════════════════════════════════════════════════════════

_NEGATIVE_SIGNAL_PATTERNS: List[Tuple[str, str, str]] = [
    # (regex, category, display_label)
    (r"freshers?\s+(?:only|preferred)|only\s+freshers?", "seniority_cap", "Freshers only"),
    (r"no\s+(?:prior\s+)?(?:llm|ai|ml|machine\s+learning)\s+experience\s+(?:required|necessary|needed)", "skill_exclusion", "No ML experience required"),
    (r"non[\s-]technical\s+background", "culture_mismatch", "Non-technical background preferred"),
    (r"no\s+remote|in[\s-]office\s+only|onsite\s+only|no\s+work\s+from\s+home", "availability", "No remote work"),
    (r"immediate\s+(?:joiner|joining)|join\s+immediately|joining\s+immediately", "availability", "Immediate joiner required"),
    (r"must\s+be\s+(?:based\s+)?(?:in|at)\s+(?:[A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", "availability", "Must be in specific location"),
    (r"(?:no|without)\s+(?:gaps?|career\s+gaps?)\s+(?:in\s+)?(?:employment|resume|cv)", "culture_mismatch", "No employment gaps"),
    (r"not\s+looking\s+for\s+(?:freshers?|entry[\s-]level|juniors?)", "seniority_cap", "Not for entry-level"),
    (r"(?:no|not)\s+(?:open|available|accepting)\s+(?:to\s+)?(?:remote|wfh|work\s+from\s+home)", "availability", "No remote candidates"),
    (r"notice\s+period\s+(?:of\s+)?(?:0|zero|immediate|15\s+days?)\s+(?:only|or\s+less)", "availability", "Short notice period required"),
]


# ═════════════════════════════════════════════════════════════════════════════
# Compiled regex cache (compiled at module load, not per-call)
# ═════════════════════════════════════════════════════════════════════════════

_COMPILED_NEGATIVE = [
    (re.compile(pat, re.IGNORECASE), cat, label)
    for pat, cat, label in _NEGATIVE_SIGNAL_PATTERNS
]

_COMPILED_LEADERSHIP = [
    (re.compile(pat, re.IGNORECASE), attr)
    for pat, attr in _LEADERSHIP_TRIGGERS
]

_YOE_PATTERNS: List[re.Pattern] = [
    # "3-5 years", "3 to 5 years", "3–5 yrs"
    re.compile(r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", re.IGNORECASE),
    # "minimum 5 years", "at least 5 yrs", "atleast 5 years"
    re.compile(r"(?:minimum|min(?:imum)?|at\s?least|minimum\s+of)\s+(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\b", re.IGNORECASE),
    # "5+ years"
    re.compile(r"(\d+(?:\.\d+)?)\+\s*(?:years?|yrs?)\b", re.IGNORECASE),
    # "5 years of experience"
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s*(?:of\s+)?(?:relevant\s+)?(?:experience|exp)\b", re.IGNORECASE),
    # "experience of 5+ years"
    re.compile(r"experience\s+of\s+(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\b", re.IGNORECASE),
]

_SALARY_PATTERNS: List[re.Pattern] = [
    re.compile(r"(?:₹|INR|Rs\.?)\s*(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(?:LPA|lpa|lakhs?)\b"),
    re.compile(r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(?:LPA|lpa|lakhs?)\b"),
    re.compile(r"(?:₹|INR|Rs\.?)\s*(\d+(?:\.\d+)?)\s*(?:LPA|lpa|lakhs?)\b"),
]


# ═════════════════════════════════════════════════════════════════════════════
# JDParser
# ═════════════════════════════════════════════════════════════════════════════

class JDParser:
    """
    Stateless, offline job description parser.

    Instantiate once — parsing is thread-safe and produces no side effects.

    Algorithm:
      1. Normalise whitespace + encoding.
      2. Detect and label sections (requirements / preferred / …).
      3. Tokenise into sentences.
      4. Extract each field using section-aware, context-aware patterns.
      5. Deduplicate and rank extracted items.
      6. Build summary_for_embedding string.
    """

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def parse(self, text: str) -> ParsedJD:
        """
        Parse a raw job description string into a structured ParsedJD.

        Args:
            text: Raw job description text (any length, any format).

        Returns:
            ParsedJD — fully populated, typed, immutable.
        """
        logger.info("JDParser: processing %d chars", len(text))

        # ── 1. Normalise ──────────────────────────────────────────────────
        text = self._normalise(text)
        text_lower = text.lower()
        sentences = self._split_sentences(text)

        # ── 2. Detect sections ────────────────────────────────────────────
        section_map = self._detect_sections(text)
        req_text = section_map.get("requirements", "")
        pref_text = section_map.get("preferred", "")
        resp_text = section_map.get("responsibilities", "")
        full_text_fallback = text

        # ── 3. Skills ─────────────────────────────────────────────────────
        must_have = self._extract_skills(
            req_text or full_text_fallback,
            sentences,
            SkillContext.MUST_HAVE,
            section_label="requirements",
        )
        # If we have a preferred section, extract from it; otherwise scan full text
        # for skills that appear in nice-to-have sentinel context
        nice_to_have = self._extract_skills(
            pref_text or full_text_fallback,
            sentences,
            SkillContext.NICE_TO_HAVE,
            section_label="preferred",
        )
        # Ensure no overlap: if a skill is in must_have, remove from nice_to_have
        must_have_lower = {s.name_lower for s in must_have}
        nice_to_have = [s for s in nice_to_have if s.name_lower not in must_have_lower]


        # ── 4. Experience ─────────────────────────────────────────────────
        experience = self._extract_experience(text)

        # ── 5. Seniority ──────────────────────────────────────────────────
        seniority, seniority_conf = self._extract_seniority(text_lower)
        # Cross-validate seniority with experience
        seniority, seniority_conf = self._reconcile_seniority_with_yoe(
            seniority, seniority_conf, experience
        )

        # ── 6. Industries ─────────────────────────────────────────────────
        industries = self._extract_industries(text_lower)

        # ── 7. Location ───────────────────────────────────────────────────
        location = self._extract_location(text, text_lower)

        # ── 8. Startup signals ────────────────────────────────────────────
        startup_signals = self._extract_startup_signals(text_lower)

        # ── 9. Leadership signals ─────────────────────────────────────────
        leadership_signals = self._extract_leadership_signals(text, text_lower)

        # ── 10. Negative signals ──────────────────────────────────────────
        negative_signals = self._extract_negative_signals(text)

        # ── 11. Target titles ─────────────────────────────────────────────
        target_titles = self._extract_target_titles(text, text_lower)

        # ── 12. Salary ────────────────────────────────────────────────────
        salary_min, salary_max = self._extract_salary(text)

        # ── 13. Work mode ─────────────────────────────────────────────────
        work_mode = location.work_mode

        # ── 14. Embedding summary ─────────────────────────────────────────
        summary = self._build_embedding_summary(
            text, must_have, nice_to_have, target_titles, seniority, industries
        )

        result = ParsedJD(
            raw_text=text,
            char_count=len(text),
            section_map={k: v[:500] for k, v in section_map.items()},
            must_have_skills=must_have,
            nice_to_have_skills=nice_to_have,
            experience=experience,
            minimum_experience=experience.minimum,
            maximum_experience=experience.maximum,
            seniority=seniority,
            seniority_confidence=seniority_conf,
            required_industries=industries,
            target_titles=target_titles,
            preferred_location=location,
            startup_signals=startup_signals,
            leadership_signals=leadership_signals,
            negative_signals=negative_signals,
            salary_min_lpa=salary_min,
            salary_max_lpa=salary_max,
            work_mode=work_mode,
            summary_for_embedding=summary,
        )

        logger.info(
            "JDParser done: must=%d nice=%d seniority=%s yoe=[%s–%s] industries=%d",
            len(must_have), len(nice_to_have), seniority.value,
            experience.minimum, experience.maximum, len(industries),
        )
        return result

    # ──────────────────────────────────────────────────────────────────────
    # 1. Normalise
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalise(text: str) -> str:
        """Normalise Unicode, em-dashes, bullets, and excessive whitespace."""
        # Unicode normalisation
        text = text.replace("\u2013", "-").replace("\u2014", "-")   # en/em dash → hyphen
        text = text.replace("\u2019", "'").replace("\u2018", "'")   # smart quotes
        text = text.replace("\u2022", "\n• ")                        # bullet
        text = text.replace("\u00a0", " ")                           # non-breaking space
        # Normalise line endings
        text = re.sub(r"\r\n|\r", "\n", text)
        # Collapse 3+ blank lines to 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip trailing whitespace on each line
        text = "\n".join(line.rstrip() for line in text.splitlines())
        return text.strip()

    # ──────────────────────────────────────────────────────────────────────
    # 2. Sentence splitter (lightweight, no external deps)
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """
        Split text into sentences.
        Handles: bullet points, numbered lists, period-terminated sentences.
        Returns list of non-empty stripped sentences.
        """
        # Split on: sentence terminators + bullet points + newlines
        raw = re.split(
            r'(?<=[.!?])\s+(?=[A-Z])'   # sentence boundary
            r'|(?:\n\s*[-•*]\s*)'         # bullet point
            r'|(?:\n\s*\d+[.)]\s+)',       # numbered list
            text,
        )
        return [s.strip() for s in raw if s.strip() and len(s.strip()) > 3]

    # ──────────────────────────────────────────────────────────────────────
    # 3. Section detection
    # ──────────────────────────────────────────────────────────────────────

    def _detect_sections(self, text: str) -> Dict[str, str]:
        """
        Split JD into labelled sections using header heuristics.
        Returns dict: section_name → section_text.
        """
        section_map: Dict[str, str] = {}
        lines = text.splitlines()
        current_section: Optional[str] = None
        current_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            label = self._classify_line_as_header(stripped)

            if label:
                # Save previous section
                if current_section and current_lines:
                    text_to_save = "\n".join(current_lines).strip()
                    if current_section in section_map:
                        section_map[current_section] += "\n" + text_to_save
                    else:
                        section_map[current_section] = text_to_save
                current_section = label
                current_lines = []
            else:
                current_lines.append(line)

        # Save last section
        if current_section and current_lines:
            text_to_save = "\n".join(current_lines).strip()
            if current_section in section_map:
                section_map[current_section] += "\n" + text_to_save
            else:
                section_map[current_section] = text_to_save

        # If no sections detected, put everything under "full_text"
        if not section_map:
            section_map["full_text"] = text

        return section_map

    @staticmethod
    def _classify_line_as_header(line: str) -> Optional[str]:
        """Return section label if this line looks like a section header, else None."""
        # Headers are typically short (< 60 chars), possibly title-cased, often end with ':'
        if not line or len(line) > 80:
            return None
        # A header usually doesn't start with a bullet point or number
        if re.match(r"^[\-•*]\s", line) or re.match(r"^\d+\.", line):
            return None
            
        line_lower = line.lower().rstrip(":").strip()
        for label, triggers in _SECTION_HEADERS.items():
            for trigger in triggers:
                if trigger in line_lower and len(line_lower) < 60:
                    return label
        return None

    # ──────────────────────────────────────────────────────────────────────
    # 4. Skill extraction
    # ──────────────────────────────────────────────────────────────────────

    def _extract_skills(
        self,
        section_text: str,
        all_sentences: List[str],
        default_context: SkillContext,
        section_label: str,
    ) -> List[SkillMention]:
        """
        Extract skill mentions from section_text with context classification.
        Falls back to sentence-level context analysis for must-have vs nice-to-have.
        """
        found: Dict[str, SkillMention] = {}  # canonical_name_lower → best mention

        # Tokenise the section into sentences for context analysis
        section_sentences = self._split_sentences(section_text) if section_text else []

        # Build (alias, canonical) pairs sorted by alias length DESC (greedy matching)
        sorted_aliases = sorted(
            _ALIAS_TO_CANONICAL.items(), key=lambda x: len(x[0]), reverse=True
        )

        text_lower = section_text.lower()

        for alias, canonical in sorted_aliases:
            # Skip R (too short, causes false positives unless in isolation)
            if alias == r"\br\b":
                if not re.search(r"\bR\b", section_text):
                    continue
            elif alias not in text_lower:
                continue

            # Find all occurrences and pick best context
            context, confidence = self._classify_skill_context(
                alias, canonical, section_sentences, all_sentences, default_context
            )

            key = canonical.lower()
            if key not in found or confidence > found[key].confidence:
                found[key] = SkillMention(
                    name=canonical,
                    name_lower=key,
                    context=context,
                    source_section=section_label,
                    confidence=confidence,
                )

        # Filter to only those matching the desired context (or both if label = "requirements")
        if default_context == SkillContext.MUST_HAVE:
            # Keep must-have; also accept nice-to-have found in req section (lower confidence)
            result = [
                m for m in found.values()
                if m.context in (SkillContext.MUST_HAVE, SkillContext.NICE_TO_HAVE)
            ]
        else:
            result = list(found.values())

        # Sort: MUST_HAVE first, then by confidence
        result.sort(key=lambda m: (m.context != SkillContext.MUST_HAVE, -m.confidence))
        return result[:30]  # cap at 30 per section

    def _classify_skill_context(
        self,
        alias: str,
        canonical: str,
        section_sentences: List[str],
        all_sentences: List[str],
        default_context: SkillContext,
    ) -> Tuple[SkillContext, float]:
        """
        Determine whether a skill is must-have or nice-to-have by analysing the
        sentence(s) that contain the alias.

        Strategy:
          1. Find all sentences containing the alias.
          2. Check for sentinel phrases within ±1 sentence (context window).
          3. Return highest-confidence classification.
        """
        # Search in section sentences first, then all sentences as fallback
        search_pool = section_sentences if section_sentences else all_sentences
        matching = [s for s in search_pool if alias in s.lower()]

        if not matching:
            return default_context, 0.60

        best_context = default_context
        best_conf = 0.60

        for sentence in matching:
            sent_lower = sentence.lower()

            # Check for negation (overrides everything)
            if any(neg in sent_lower for neg in _NEGATION_SENTINELS):
                return SkillContext.NICE_TO_HAVE, 0.55  # relax — not strictly required

            # Check must-have sentinels
            must_score = sum(1 for s in _MUST_HAVE_SENTINELS if s in sent_lower)
            nice_score = sum(1 for s in _NICE_TO_HAVE_SENTINELS if s in sent_lower)

            if must_score > nice_score:
                conf = min(0.70 + must_score * 0.05, 0.95)
                if conf > best_conf:
                    best_context = SkillContext.MUST_HAVE
                    best_conf = conf
            elif nice_score > must_score:
                conf = min(0.70 + nice_score * 0.05, 0.90)
                if conf > best_conf:
                    best_context = SkillContext.NICE_TO_HAVE
                    best_conf = conf
            else:
                # No explicit sentinel — trust the section label
                conf = 0.65
                if conf > best_conf:
                    best_context = default_context
                    best_conf = conf

        return best_context, best_conf

    # ──────────────────────────────────────────────────────────────────────
    # 5. Experience
    # ──────────────────────────────────────────────────────────────────────

    def _extract_experience(self, text: str) -> ExperienceRange:
        """Extract YoE range using multiple compiled patterns."""
        for pat in _YOE_PATTERNS:
            m = pat.search(text)
            if not m:
                continue
            groups = m.groups()
            raw = m.group(0)
            if len(groups) >= 2 and groups[1]:
                mn, mx = float(groups[0]), float(groups[1])
                return ExperienceRange(minimum=min(mn, mx), maximum=max(mn, mx), raw_text=raw)
            elif groups[0]:
                mn = float(groups[0])
                # "5+ years" → minimum=5, maximum=None (unbounded)
                if "+" in raw:
                    return ExperienceRange(minimum=mn, maximum=None, raw_text=raw)
                return ExperienceRange(minimum=mn, maximum=mn + 4.0, raw_text=raw)
        return ExperienceRange()

    # ──────────────────────────────────────────────────────────────────────
    # 6. Seniority
    # ──────────────────────────────────────────────────────────────────────

    def _extract_seniority(self, text_lower: str) -> Tuple[SeniorityLevel, float]:
        """
        Detect seniority from trigger phrases using word boundaries to prevent
        false positives (e.g. 'cto' inside 'vector').
        Returns (level, confidence) of the highest-confidence match.
        """
        best_level = SeniorityLevel.UNKNOWN
        best_conf = 0.0

        for level, confidence, triggers in _SENIORITY_PATTERNS:
            for trigger in triggers:
                # Use word boundaries for exact match
                if re.search(r"\b" + re.escape(trigger) + r"\b", text_lower):
                    if confidence > best_conf:
                        best_level = level
                        best_conf = confidence
                    break

        return best_level, round(best_conf, 2)

    @staticmethod
    def _reconcile_seniority_with_yoe(
        seniority: SeniorityLevel,
        confidence: float,
        experience: ExperienceRange,
    ) -> Tuple[SeniorityLevel, float]:
        """
        If seniority is UNKNOWN but experience range is available, infer from YoE.
        Also cross-validate: flag if stated seniority contradicts YoE.
        """
        if experience.minimum is None:
            return seniority, confidence

        yoe = experience.midpoint or experience.minimum

        # Infer if unknown
        if seniority == SeniorityLevel.UNKNOWN:
            if yoe == 0:
                return SeniorityLevel.INTERN, 0.55
            if yoe <= 2:
                return SeniorityLevel.JUNIOR, 0.60
            if yoe <= 5:
                return SeniorityLevel.MID, 0.60
            if yoe <= 8:
                return SeniorityLevel.SENIOR, 0.60
            if yoe <= 12:
                return SeniorityLevel.LEAD, 0.55
            return SeniorityLevel.PRINCIPAL, 0.55

        # Cross-validate and adjust confidence
        expected_yoe_range = {
            SeniorityLevel.INTERN: (0, 1),
            SeniorityLevel.JUNIOR: (0, 3),
            SeniorityLevel.MID: (2, 6),
            SeniorityLevel.SENIOR: (4, 10),
            SeniorityLevel.LEAD: (6, 14),
            SeniorityLevel.PRINCIPAL: (8, 25),
            SeniorityLevel.STAFF: (8, 25),
            SeniorityLevel.DIRECTOR: (10, 30),
            SeniorityLevel.VP: (12, 30),
            SeniorityLevel.EXECUTIVE: (15, 40),
        }
        if seniority in expected_yoe_range:
            lo, hi = expected_yoe_range[seniority]
            if not (lo <= yoe <= hi):
                confidence = max(confidence - 0.10, 0.40)  # penalty for mismatch

        return seniority, round(confidence, 2)

    # ──────────────────────────────────────────────────────────────────────
    # 7. Industries
    # ──────────────────────────────────────────────────────────────────────

    def _extract_industries(self, text_lower: str) -> List[str]:
        """Match industry patterns against text. Return list of canonical names."""
        found: List[str] = []
        for canonical, patterns in _INDUSTRY_PATTERNS:
            if any(p in text_lower for p in patterns):
                found.append(canonical)
        return found

    # ──────────────────────────────────────────────────────────────────────
    # 8. Location
    # ──────────────────────────────────────────────────────────────────────

    def _extract_location(self, text: str, text_lower: str) -> LocationHint:
        """Extract city, country, work mode, relocation offer, visa sponsorship."""
        city = region = country = None

        # City detection
        for city_lower, (city_name, country_name) in _CITY_MAP.items():
            if city_lower in text_lower:
                city = city_name
                country = country_name
                break

        # Country fallback
        if not country:
            for c_lower, c_name in _COUNTRY_MAP.items():
                if re.search(r"\b" + re.escape(c_lower) + r"\b", text_lower):
                    country = c_name
                    break

        # Work mode
        work_mode = WorkMode.UNKNOWN
        mode_patterns = [
            (WorkMode.HYBRID, ["hybrid"]),
            (WorkMode.ONSITE, [
                "on-site", "onsite", "in-office", "in office",
                "full-time in office", "office only", "in office only",
                "no remote", "no work from home",
            ]),
            (WorkMode.REMOTE, ["remote", "work from home", "wfh", "fully remote", "100% remote"]),
            (WorkMode.FLEXIBLE, ["flexible", "flexible work"]),
        ]
        for mode, triggers in mode_patterns:
            if any(t in text_lower for t in triggers):
                work_mode = mode
                break

        # Relocation & visa
        relocation_offered = any(p in text_lower for p in [
            "relocation assistance", "relocation support", "relocation package", "we cover relocation",
        ])
        visa_sponsorship = any(p in text_lower for p in [
            "visa sponsorship", "we sponsor", "work authorization", "h1b", "h-1b",
        ])

        return LocationHint(
            city=city,
            country=country,
            work_mode=work_mode,
            relocation_offered=relocation_offered,
            visa_sponsorship=visa_sponsorship,
        )

    # ──────────────────────────────────────────────────────────────────────
    # 9. Startup signals
    # ──────────────────────────────────────────────────────────────────────

    def _extract_startup_signals(self, text_lower: str) -> StartupSignals:
        """Detect startup culture signals from text."""
        is_startup = False
        funding_stage: Optional[str] = None
        fast_paced = False
        ownership = False
        equity = False
        flat = False
        scrappy = False
        signals_found: List[str] = []

        for phrase, attr in _STARTUP_TRIGGERS.items():
            if phrase in text_lower:
                signals_found.append(phrase)
                if attr.startswith("funding_stage:"):
                    funding_stage = attr.split(":")[1]
                    is_startup = True
                elif attr == "is_startup":
                    is_startup = True
                elif attr == "fast_paced_mentioned":
                    fast_paced = True
                elif attr == "ownership_culture":
                    ownership = True
                elif attr == "equity_mentioned":
                    equity = True
                elif attr == "flat_hierarchy":
                    flat = True
                elif attr == "scrappy_culture":
                    scrappy = True

        return StartupSignals(
            is_startup=is_startup,
            funding_stage=funding_stage,
            fast_paced_mentioned=fast_paced,
            ownership_culture=ownership,
            equity_mentioned=equity,
            flat_hierarchy=flat,
            scrappy_culture=scrappy,
            signals_found=signals_found,
        )

    # ──────────────────────────────────────────────────────────────────────
    # 10. Leadership signals
    # ──────────────────────────────────────────────────────────────────────

    def _extract_leadership_signals(self, text: str, text_lower: str) -> LeadershipSignals:
        """Detect people management and technical leadership signals."""
        requires_management = False
        min_reports: Optional[int] = None
        max_reports: Optional[int] = None
        hiring_mgr = False
        cross_func = False
        tech_lead = False
        strategy = False
        signals_found: List[str] = []

        for compiled_pat, attr in _COMPILED_LEADERSHIP:
            m = compiled_pat.search(text)
            if not m:
                continue
            signals_found.append(m.group(0)[:60])

            if attr == "requires_management":
                requires_management = True
            elif attr == "direct_reports_range":
                grps = m.groups()
                if len(grps) >= 2:
                    try:
                        lo, hi = int(grps[0]), int(grps[1])
                        min_reports = min(lo, hi)
                        max_reports = max(lo, hi)
                        requires_management = True
                    except (ValueError, TypeError):
                        pass
            elif attr == "min_direct_reports":
                try:
                    min_reports = int(m.group(1))
                    requires_management = True
                except (ValueError, TypeError, IndexError):
                    pass
            elif attr == "hiring_manager_role":
                hiring_mgr = True
            elif attr == "cross_functional_leadership":
                cross_func = True
            elif attr == "technical_lead":
                tech_lead = True
                requires_management = True
            elif attr == "strategy_ownership":
                strategy = True

        return LeadershipSignals(
            requires_management=requires_management,
            min_direct_reports=min_reports,
            max_direct_reports=max_reports,
            hiring_manager_role=hiring_mgr,
            cross_functional_leadership=cross_func,
            technical_lead=tech_lead,
            strategy_ownership=strategy,
            signals_found=signals_found[:10],
        )

    # ──────────────────────────────────────────────────────────────────────
    # 11. Negative signals
    # ──────────────────────────────────────────────────────────────────────

    def _extract_negative_signals(self, text: str) -> List[NegativeSignal]:
        """Detect explicit negative requirements from text."""
        found: List[NegativeSignal] = []
        for compiled_pat, category, label in _COMPILED_NEGATIVE:
            m = compiled_pat.search(text)
            if m:
                found.append(NegativeSignal(
                    signal=label,
                    category=category,
                    raw_text=m.group(0)[:100],
                ))
        return found

    # ──────────────────────────────────────────────────────────────────────
    # 12. Target titles
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_target_titles(text: str, text_lower: str) -> List[str]:
        """Extract job titles from JD title lines, role intro patterns, and known ML titles."""
        titles: List[str] = []

        # Pattern 1: first non-empty line (usually the job title)
        first_lines = [l.strip() for l in text.splitlines() if l.strip()][:3]
        for line in first_lines:
            if 5 < len(line) < 80 and not any(c in line for c in [".", ",", "?", "@"]):
                if re.search(r"(?:engineer|scientist|analyst|manager|developer|lead|architect|researcher|specialist)", line, re.I):
                    titles.append(line)

        # Pattern 2: "We are hiring a/an <Title>"
        for m in re.finditer(
            r"(?:hiring|looking for|seeking|recruiting)\s+(?:a|an)\s+([A-Z][a-zA-Z\s/,]+?)(?:[.,!?]|\s{2}|$)",
            text, re.IGNORECASE
        ):
            t = m.group(1).strip().rstrip(",.")
            if 5 < len(t) < 70:
                titles.append(t)

        # Pattern 3: "Role: <Title>" or "Position: <Title>"
        for m in re.finditer(
            r"(?:role|position|title|job title)\s*:\s*([A-Z][a-zA-Z\s/,\-]+?)(?:\n|$)",
            text, re.IGNORECASE
        ):
            t = m.group(1).strip()
            if 5 < len(t) < 70:
                titles.append(t)

        # Known canonical titles (full-text fallback)
        _KNOWN_TITLES = [
            "Machine Learning Engineer", "ML Engineer", "Senior ML Engineer",
            "Data Scientist", "Senior Data Scientist", "Staff Data Scientist",
            "AI Engineer", "Applied Scientist", "Research Scientist",
            "NLP Engineer", "Computer Vision Engineer",
            "MLOps Engineer", "Data Engineer", "Analytics Engineer",
            "AI Researcher", "Deep Learning Engineer",
            "Software Engineer", "Backend Engineer", "Full Stack Engineer",
            "Head of AI", "Director of Engineering", "VP of Engineering",
            "Principal Engineer", "Staff Engineer",
        ]
        for t in _KNOWN_TITLES:
            if t.lower() in text_lower and t not in titles:
                titles.append(t)

        # Deduplicate preserving order
        seen: Set[str] = set()
        deduped: List[str] = []
        for t in titles:
            tl = t.lower()
            if tl not in seen:
                seen.add(tl)
                deduped.append(t)

        return deduped[:8]

    # ──────────────────────────────────────────────────────────────────────
    # 13. Salary
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_salary(text: str) -> Tuple[Optional[float], Optional[float]]:
        for pat in _SALARY_PATTERNS:
            m = pat.search(text)
            if m:
                grps = m.groups()
                if len(grps) >= 2 and grps[1]:
                    return float(grps[0]), float(grps[1])
                if grps[0]:
                    v = float(grps[0])
                    return v, v * 1.5
        return None, None

    # ──────────────────────────────────────────────────────────────────────
    # 14. Embedding summary
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_embedding_summary(
        text: str,
        must_have: List[SkillMention],
        nice_to_have: List[SkillMention],
        titles: List[str],
        seniority: SeniorityLevel,
        industries: List[str],
    ) -> str:
        parts = [
            text[:600],  # raw JD intro
            f"Required skills: {', '.join(s.name for s in must_have[:15])}",
            f"Nice-to-have: {', '.join(s.name for s in nice_to_have[:10])}",
            f"Titles: {', '.join(titles[:4])}",
            f"Seniority: {seniority.value}",
            f"Industries: {', '.join(industries[:5])}",
        ]
        return " ".join(p for p in parts if p)[:2_000]
