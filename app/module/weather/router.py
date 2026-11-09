import asyncio

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.module.weather.schemas import (
    DailyWeatherResponse,
    ForecastDay,
    WeatherPromptRequest,
    WeatherPromptResponse,
)
from app.module.weather.service import (
    LocationNotFoundError,
    WeatherServiceError,
    get_daily_weather,
)
from app.module.weather.tools import generate_weather_answer


router = APIRouter(prefix="/weather", tags=["Weather"])


def _get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = (
        forwarded_for.split(",", maxsplit=1)[0].strip()
        if forwarded_for
        else request.headers.get("x-real-ip")
    )
    if not client_ip and request.client:
        client_ip = request.client.host
    return client_ip


# @router.get("/current", response_model=DailyWeatherResponse)
# async def weather(
#     request: Request,
#     day: ForecastDay = Query(description="Ngày dự báo: hôm nay, ngày mai hoặc ngày kia"),
#     city: str | None = Query(
#         default=None,
#         min_length=2,
#         max_length=120,
#         description="Tên thành phố hoặc địa điểm; để trống để xác định gần đúng theo IP",
#     ),
# ) -> DailyWeatherResponse:
#     try:
#         result = await asyncio.to_thread(
#             get_daily_weather,
#             day,
#             city,
#             _get_client_ip(request),
#         )
#     except LocationNotFoundError as exc:
#         raise HTTPException(status_code=404, detail=str(exc)) from exc
#     except WeatherServiceError as exc:
#         raise HTTPException(status_code=502, detail=str(exc)) from exc
#     return DailyWeatherResponse(**result)


@router.post("/ask")
async def ask_weather(body: WeatherPromptRequest) -> PlainTextResponse:
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt must not be empty")

    try:
        answer = await asyncio.to_thread(generate_weather_answer, prompt)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Weather assistant failed: {exc}",
        ) from exc
    return PlainTextResponse(answer)
