from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_MARKERS = ("your_", "placeholder", "changeme", "example")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_api_key: str
    llm_model_name: str
    pinecone_api_key: str
    pinecone_index_name: str
    pinecone_environment: str
    embedding_model_name: str
    embedding_api_key: str

    @field_validator("*")
    @classmethod
    def _reject_empty_or_placeholder(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        lowered = stripped.lower()
        for marker in _PLACEHOLDER_MARKERS:
            if marker in lowered:
                raise ValueError(
                    f"value {value!r} looks like a placeholder from .env.example "
                    "and is not a real credential; set a real value in the "
                    "environment or in .env"
                )
        return stripped


settings = Settings()