from pydantic import BaseModel, Field, HttpUrl


class EasyAssessComplexityRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=4000)


class SmartRouteResponse(BaseModel):
    response: str


