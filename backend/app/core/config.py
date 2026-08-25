from functools import lru_cache
import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_data_dir() -> Path:
    if "DATA_DIR" in os.environ and os.environ["DATA_DIR"].strip():
        return Path(os.environ["DATA_DIR"].strip()).resolve()

    backend_root = Path(__file__).resolve().parent.parent.parent
    project_root = backend_root.parent
    if (project_root / "data").exists():
        return (project_root / "data").resolve()
    if (backend_root / "data").exists():
        return (backend_root / "data").resolve()

    return (Path.cwd() / "data").resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Study Assistant"
    api_prefix: str = "/api/v1"
    data_dir: Path = Field(default_factory=_get_default_data_dir)
    uploads_dir: Path | None = None
    vector_store_dir: Path | None = None
    metadata_path: Path | None = None
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_chat_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_CHAT_MODEL")
    gemini_embedding_model: str = Field(default="gemini-embedding-001", alias="GEMINI_EMBEDDING_MODEL")
    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 4
    min_relevance_score: float = 0.35
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "*",
        ]
    )

    def model_post_init(self, __context: object) -> None:
        if self.uploads_dir is None:
            self.uploads_dir = self.data_dir / "uploads"
        if self.vector_store_dir is None:
            self.vector_store_dir = self.data_dir / "vector_store"
        if self.metadata_path is None:
            self.metadata_path = self.data_dir / "documents.json"

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if self.uploads_dir:
            self.uploads_dir.mkdir(parents=True, exist_ok=True)
        if self.vector_store_dir:
            self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        if self.metadata_path:
            self.metadata_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings