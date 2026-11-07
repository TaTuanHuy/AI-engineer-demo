from fastapi import APIRouter, HTTPException

from app.module.multi_model_smart.schemas import EasyAssessComplexityRequest, GenerateDatasetRequest, SmartRouteResponse, ClassifyPromptLLMRequest, ClassifyPromptLLMResponse
from app.module.multi_model_smart.service import assess_complexity, generate_dataset_scoring_question_complexity, classify_prompt_llm


router = APIRouter(prefix="/multi-model-smart-route", tags=["Multi-Model Smart Route"])

@router.post("easy", response_model=SmartRouteResponse)
def create_dataset(body: EasyAssessComplexityRequest) -> SmartRouteResponse:
    try:
        return SmartRouteResponse(response=assess_complexity(body.prompt))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model routing failed: {exc}") from exc

@router.post("/generate_dataset", response_model=SmartRouteResponse)
def generate_dataset(body: GenerateDatasetRequest) -> SmartRouteResponse:
    try:
        return SmartRouteResponse(response=generate_dataset_scoring_question_complexity(body.num_cases))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model routing failed: {exc}") from exc

@router.post("/classify_prompt", response_model=ClassifyPromptLLMResponse)
def classify_prompt(body: ClassifyPromptLLMRequest) -> ClassifyPromptLLMResponse:
    try:
        return ClassifyPromptLLMResponse(response=classify_prompt_llm(body.user_prompt))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model routing failed: {exc}") from exc



