from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    data_dir: Path = Path("data")
    weaviate_url: str = "http://localhost:8096"
    ollama_url: str = "http://localhost:11436"
    ollama_model: str = "qwen2.5:1.5b"
    include_schema_in_prompt: bool = True
    extractor: str = "ollama"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_mode: str = "fastembed"
    embedding_cache_dir: Path = Path.home() / ".cache" / "fastembed"
    ocr_provider: str = "tesseract"
    ocr_language: str = "eng"
    allow_paid_ocr: bool = False
    aws_region: str = "us-east-1"
    access_token: str = ""
    max_upload_bytes: int = 30 * 1024 * 1024
    max_pages: int = 400
    max_documents: int = 1000
    lease_seconds: int = 900
    max_attempts: int = 3
    review_threshold: float = 0.85

    @property
    def database(self) -> Path:
        return self.data_dir / "pipeline.sqlite3"
