from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # App
    APP_TITLE: str = "RTIE — Redrob Talent Intelligence Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    # Paths
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DIR: Path = BASE_DIR / "data" / "raw"
    PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    EMBEDDINGS_DIR: Path = BASE_DIR / "data" / "embeddings"
    OUTPUTS_DIR: Path = BASE_DIR / "data" / "outputs"

    # Model
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_BATCH_SIZE: int = 256
    INTRA_OP_THREADS: int = 8  # CPU intra-op threads (adjust based on deployment)

    # Ranking
    RETRIEVAL_TOP_K: int = 500
    FINAL_TOP_N: int = 100


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure data directories exist
for d in [settings.RAW_DIR, settings.PROCESSED_DIR, settings.EMBEDDINGS_DIR, settings.OUTPUTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
