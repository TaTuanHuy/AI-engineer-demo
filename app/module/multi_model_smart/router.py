import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse

from app.config import settings
from app.module.multi_model_smart.schemas import EasyAssessComplexityRequest, GenerateDatasetRequest, SmartRouteResponse, ClassifyPromptLLMRequest, ClassifyPromptLLMResponse, SmartRoutePromptRequest, SmartRoutePromptResponse
from app.module.multi_model_smart.service import assess_complexity, generate_dataset_scoring_question_complexity, classify_prompt_llm, smart_route_prompt, score_classify_prompt


router = APIRouter(prefix="/multi-model-smart-route", tags=["Multi-Model Smart Route"])


@router.post("/classify-prompt/evaluate")
async def evaluate_classifier(request: Request) -> dict:
    """Evaluate the current classifier using the saved dataset."""
    if not settings.mongo_enabled:
        raise HTTPException(status_code=503, detail="MongoDB is not enabled")
    try:
        result = await score_classify_prompt()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Classifier evaluation failed") from exc
    filename = Path(result["html_report_path"]).name
    result["html_report_url"] = str(request.url_for("get_classifier_report", filename=filename))
    return result

@router.post("/easy", response_model=SmartRouteResponse)
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


@router.post("/route_prompt")
def route_prompt(body: SmartRoutePromptRequest) -> PlainTextResponse:
    """Classify the prompt, select model settings, then return the answer as markdown text."""
    try:
        result = smart_route_prompt(
            prompt=body.prompt,
            max_output_tokens=body.max_output_tokens,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Smart prompt routing failed: {exc}") from exc
    return PlainTextResponse(
        result["response"],
        media_type="text/markdown; charset=utf-8",
        headers={
            "X-Tier": str(result["tier"]),
            "X-Model": str(result["model"]),
            "X-Temperature": str(result["temperature"]),
        },
    )



