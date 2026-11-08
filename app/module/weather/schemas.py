from datetime import date
from enum import Enum

from pydantic import BaseModel


class ForecastDay(str, Enum):
    TODAY = "today"
    TOMORROW = "tomorrow"
    DAY_AFTER_TOMORROW = "day_after_tomorrow"


class DailyWeatherResponse(BaseModel):
    location: str
    latitude: float
    longitude: float
    forecast_day: ForecastDay
    forecast_date: date
    timezone: str
    weather_code: int | None
    weather_description: str
    temperature_min_c: float | None
    temperature_max_c: float | None
    feels_like_min_c: float | None
    feels_like_max_c: float | None
    precipitation_probability_max_percent: int | None
    precipitation_sum_mm: float | None
    wind_speed_max_kmh: float | None
    wind_direction_dominant_degrees: int | None
    sunrise: str | None
    sunset: str | None


class WeatherPromptRequest(BaseModel):
    prompt: str


class WeatherPromptResponse(BaseModel):
    answer: str
