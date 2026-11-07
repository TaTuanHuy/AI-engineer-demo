from fastapi import APIRouter, HTTPException

from app.module.multi_model_smart.schemas import EasyAssessComplexityRequest, GenerateDatasetRequest, SmartRouteResponse, ClassifyPromptLLMRequest, ClassifyPromptLLMResponse, SmartRoutePromptRequest, SmartRoutePromptResponse
from app.module.multi_model_smart.service import assess_complexity, generate_dataset_scoring_question_complexity, classify_prompt_llm, smart_route_prompt


router = APIRouter(prefix="/multi-model-smart-route", tags=["Multi-Model Smart Route"])

@router.post("easy", response_model=SmartRouteResponse)
def create_dataset(body: EasyAssessComplexityRequest) -> SmartRouteResponse:
    try:
        return SmartRouteResponse(response=assess_complexity(body.prompt))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model routing failed: {exc}") from exc

@router.post("/generate_dataset", response_model=SmartRouteResponse)
async def generate_dataset(body: GenerateDatasetRequest) -> SmartRouteResponse:
    try:
        result = await generate_dataset_scoring_question_complexity(
            body.num_cases,
            temperature=body.temperature,
        )
        return SmartRouteResponse(response=result)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model routing failed: {exc}") from exc

@router.post("/classify_prompt", response_model=ClassifyPromptLLMResponse)
def classify_prompt(body: ClassifyPromptLLMRequest) -> ClassifyPromptLLMResponse:
    try:
        result = classify_prompt_llm(
            user_prompt=body.user_prompt,
        )
        return ClassifyPromptLLMResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model routing failed: {exc}") from exc


@router.post("/route_prompt", response_model=SmartRoutePromptResponse)
def route_prompt(body: SmartRoutePromptRequest) -> SmartRoutePromptResponse:
    """Classify the prompt, select model settings, then generate its answer."""
    try:
        return SmartRoutePromptResponse(**smart_route_prompt(
            prompt=body.prompt,
            max_output_tokens=body.max_output_tokens,
        ))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Smart prompt routing failed: {exc}") from exc



