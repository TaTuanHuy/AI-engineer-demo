import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Demo AI API")
    app_environment: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    app_reload: bool = get_bool_env("APP_RELOAD", default=True)
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash")
    gemini_dataset_model: str = os.getenv("GEMINI_DATASET_MODEL", "")
    gemini_output_model: str = os.getenv("GEMINI_OUTPUT_MODEL", "")
    gemini_grading_model: str = os.getenv("GEMINI_GRADING_MODEL", "")
    gemini_temperature: float = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
    gemini_dataset_temperature: float = float(os.getenv("GEMINI_DATASET_TEMPERATURE", "0.4"))
    gemini_output_temperature: float = float(os.getenv("GEMINI_OUTPUT_TEMPERATURE", "0.2"))
    gemini_grading_temperature: float = float(os.getenv("GEMINI_GRADING_TEMPERATURE", "0.0"))
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or os.getenv(
        "GOOGLE_API_KEY"
    )


settings = Settings()
