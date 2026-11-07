from pydantic import BaseModel, Field, HttpUrl


class EasyAssessComplexityRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=4000)


class GenerateDatasetRequest(BaseModel):
    num_cases: int = Field(gt=0, le=100, description="Number of test cases per tier (LOW, MEDIUM, HIGH)")


class SmartRouteResponse(BaseModel):
    response: str


class ClassifyPromptLLMRequest(BaseModel):
    user_prompt: str


class ClassifyPromptLLMResponse(BaseModel):
    response: str




