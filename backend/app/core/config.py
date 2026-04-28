from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Study Assistant"
    api_prefix: str = "/api/v1"
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3])
    data_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "data")
    uploads_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "data" / "uploads")
    vector_store_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "data" / "vector_store")
    metadata_path: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "data" / "documents.json")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_chat_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_CHAT_MODEL")
    gemini_embedding_model: str = Field(default="gemini-embedding-001", alias="GEMINI_EMBEDDING_MODEL")
    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 4
    min_relevance_score: float = 0.35
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ]
    )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings

