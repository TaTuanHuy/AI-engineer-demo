from typing import Any

from pydantic import BaseModel, Field, HttpUrl


# Gemini response schemas used by the prompt evaluation service.
DATASET_SCHEMA = {
    "type": "object",
    "properties": {
        "test_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "inputs": {"type": "object"},
                    "solution_criteria": {"type": "array", "items": {"type": "string"}},
                    "scenario": {"type": "string"},
                },
                "required": ["inputs", "solution_criteria", "scenario"],
            },
        }
    },
    "required": ["test_cases"],
}

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "strengths": {"type": "array", "items": {"type": "string"}},
        "weaknesses": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
        "score": {"type": "integer", "minimum": 1, "maximum": 10},
    },
    "required": ["strengths", "weaknesses", "reasoning", "score"],
}

FRAMEWORK_DATASET_SCHEMA = {
    "type": "object",
    "properties": {
        "test_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "inputs": {"type": "object"},
                    "scenario": {"type": "string"},
                    "solution_criteria": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["inputs", "scenario", "solution_criteria"],
            },
        }
    },
    "required": ["test_cases"],
}


class SeedCase(BaseModel):
    inputs: dict[str, str | int | float | bool | None]
    notes: str = ""


class DatasetRequest(BaseModel):
    task_description: str = Field(min_length=5, max_length=4000)
    test_cases: list[SeedCase] = Field(min_length=1, max_length=30)
    additional_cases: int = Field(default=5, ge=0, le=30)
    criteria: list[str] = Field(default_factory=list, max_length=20)


class EvaluateRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=20000)
    dataset_url: HttpUrl


class FrameworkDatasetRequest(BaseModel):
    module: str = Field(min_length=1, max_length=100)
    key: str = Field(min_length=1, max_length=150)
    rule: str = Field(min_length=5, max_length=8000)
    example: list[dict[str, Any]] = Field(min_length=1, max_length=50)
    num_cases: int = Field(gt=0, le=100)
    model: str | None = Field(default=None, min_length=1, max_length=150)
    max_token: int = Field(default=4000, ge=1, le=8192)


class FrameworkPromptEvaluationRequest(BaseModel):
    module: str = Field(min_length=1, max_length=100)
    key: str = Field(min_length=1, max_length=150)
    user_prompt: str = Field(min_length=5, max_length=20000)

