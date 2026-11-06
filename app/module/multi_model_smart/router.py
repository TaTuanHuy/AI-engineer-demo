from fastapi import APIRouter, HTTPException

from app.module.multi_model_smart.schemas import EasyAssessComplexityRequest, SmartRouteResponse
from app.module.multi_model_smart.service import assess_complexity


router = APIRouter(prefix="/multi-model-smart-route", tags=["Multi-Model Smart Route"])

@router.post("", response_model=SmartRouteResponse)
def create_dataset(body: EasyAssessComplexityRequest) -> SmartRouteResponse:
    try:
        return SmartRouteResponse(response=assess_complexity(body.prompt))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model routing failed: {exc}") from exc


