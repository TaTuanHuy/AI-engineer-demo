from pydantic import BaseModel, Field, HttpUrl

from app.config import settings


class EasyAssessComplexityRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=4000)


class GenerateDatasetRequest(BaseModel):
    num_cases: int = Field(gt=0, le=100, description="Number of test cases per tier (LOW, MEDIUM, HIGH)")
    temperature: float = Field(
        default=settings.gemini_dataset_temperature,
        ge=0.0,
        le=2.0,
        description="Gemini generation temperature (0.0-2.0)",
    )


class SmartRouteResponse(BaseModel):
    response: str


class ClassifyPromptLLMRequest(BaseModel):
    user_prompt: str = Field(min_length=1, max_length=8000)


class ClassifyPromptLLMResponse(BaseModel):
    expected_tier: str
    temperature: float

class SmartRoutePromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    max_output_tokens: int = Field(default=2000, ge=1, le=8192)


class SmartRoutePromptResponse(BaseModel):
    tier: str
    model: str
    temperature: float
    response: str




