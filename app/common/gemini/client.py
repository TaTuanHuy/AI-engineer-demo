from typing import Any

from google import genai
from google.genai import types

from app.config import settings


DEFAULT_MODEL = "gemini-3.1-flash"


class GeminiClient:
    """Shared Gemini configuration and chat/generation helpers."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or settings.gemini_api_key
        if not key:
            raise RuntimeError("Set GEMINI_API_KEY in the environment before using Gemini.")
        self.model = model or settings.gemini_model or DEFAULT_MODEL
        self.default_temperature = settings.gemini_temperature
        self.client = genai.Client(api_key=key)
    

    def generate(
        self,
        prompt: str,
        *,
        temperature: float | None = None,
        model: str | None = None,
    ) -> str:
        response = self.client.models.generate_content(
            model=model or self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.default_temperature if temperature is None else temperature,
                max_output_tokens=500,
            ),
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        
        return response.text.strip()

    def generate_json(
        self,
        prompt: str,
        *,
        schema: dict[str, Any],
        temperature: float | None = None,
        model: str | None = None,
    ) -> Any:
        response = self.client.models.generate_content(
            model=model or self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.default_temperature if temperature is None else temperature,
                response_mime_type="application/json",
                response_json_schema=schema,
                max_output_tokens=500,
            ),
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty JSON response.")
        import json

        return json.loads(response.text)

