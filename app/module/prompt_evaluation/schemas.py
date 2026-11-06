from pydantic import BaseModel, Field, HttpUrl


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

