from typing import Any

from google.genai import types

from app.common.gemini.client import GeminiClient
from app.module.weather.schemas import DailyWeatherResponse, ForecastDay
from app.module.weather.service import (
    LocationNotFoundError,
    WeatherServiceError,
    get_daily_weather,
)


def get_daily_weather_tool(city: str, day: str = "today") -> dict[str, Any]:
    """Get a daily weather forecast for a city.

    Args:
        city: City or place name, for example "Hà Nội" or "Boston".
        day: Forecast day. Use "today", "tomorrow", or
            "day_after_tomorrow".

    Returns:
        Weather information formatted as a JSON-compatible dictionary.
    """
    try:
        forecast_day = ForecastDay(day)
    except ValueError:
        return {
            "error": (
                "day must be one of: today, tomorrow, "
                "day_after_tomorrow"
            )
        }

    try:
        result = get_daily_weather(
            forecast_day=forecast_day,
            city=city,
        )
    except (LocationNotFoundError, WeatherServiceError) as exc:
        return {"error": str(exc)}

    return DailyWeatherResponse.model_validate(result).model_dump(mode="json")


def generate_weather_answer(
    prompt: str,
) -> str:
    """Let Gemini call the weather tool and return its final text answer."""
    gemini = GeminiClient()
    response = gemini.client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[get_daily_weather_tool],
        ),
    )
    if not response.text:
        raise RuntimeError("Gemini returned an empty response after calling the tool.")
    return response.text.strip()
