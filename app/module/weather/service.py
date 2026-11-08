import json
from ipaddress import ip_address
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import geocoder

from app.module.weather.schemas import ForecastDay


WEATHER_DESCRIPTIONS = {
    0: "Trời quang",
    1: "Trời gần như quang",
    2: "Có mây rải rác",
    3: "Nhiều mây",
    45: "Sương mù",
    48: "Sương mù đóng băng",
    51: "Mưa phùn nhẹ",
    53: "Mưa phùn vừa",
    55: "Mưa phùn dày",
    56: "Mưa phùn đóng băng nhẹ",
    57: "Mưa phùn đóng băng dày",
    61: "Mưa nhẹ",
    63: "Mưa vừa",
    65: "Mưa lớn",
    66: "Mưa đóng băng nhẹ",
    67: "Mưa đóng băng lớn",
    71: "Tuyết rơi nhẹ",
    73: "Tuyết rơi vừa",
    75: "Tuyết rơi dày",
    77: "Mưa tuyết",
    80: "Mưa rào nhẹ",
    81: "Mưa rào vừa",
    82: "Mưa rào mạnh",
    85: "Mưa tuyết rào nhẹ",
    86: "Mưa tuyết rào mạnh",
    95: "Dông",
    96: "Dông kèm mưa đá nhẹ",
    99: "Dông kèm mưa đá mạnh",
}


class LocationNotFoundError(ValueError):
    """Raised when the geocoder cannot resolve a place name."""


class WeatherServiceError(RuntimeError):
    """Raised when a location or weather provider cannot return data."""


def _get_json(url: str, params: dict[str, str | float | int]) -> dict:
    request_url = f"{url}?{urlencode(params)}"
    try:
        with urlopen(request_url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise WeatherServiceError("Không thể kết nối dịch vụ thời tiết") from exc


def _resolve_location(city: str | None, client_ip: str | None):
    """Resolve an explicit place name or infer an approximate location by IP."""
    if city:
        provider_errors = []
        for provider in (geocoder.osm, geocoder.arcgis):
            try:
                location = provider(city, timeout=10)
            except Exception as exc:
                provider_errors.append(str(exc))
                continue

            if location.ok and location.latlng:
                return location, city
            if location.error:
                provider_errors.append(str(location.error))

        if len(provider_errors) == 2:
            raise WeatherServiceError("Không thể kết nối các dịch vụ định vị")
        raise LocationNotFoundError(f"Không tìm thấy địa điểm: {city}")

    lookup_ip = client_ip or "me"
    try:
        parsed_ip = ip_address(lookup_ip)
        if parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_reserved:
            lookup_ip = "me"
    except ValueError:
        lookup_ip = "me"

    try:
        location = geocoder.ip(lookup_ip, timeout=10)
    except Exception as exc:
        raise WeatherServiceError("Không thể kết nối dịch vụ định vị") from exc

    if not location.ok or not location.latlng:
        raise LocationNotFoundError("Không thể xác định vị trí hiện tại từ địa chỉ IP")
    return location, "Vị trí hiện tại"


def _daily_value(daily: dict, key: str,  index: int):
    values = daily.get(key)
    if not isinstance(values, list) or index >= len(values):
        return None
    return values[index]


def extract_daily_weather_data(data: dict, forecast_day: ForecastDay) -> dict:
    """Extract and normalize one requested day from an Open-Meteo response."""
    daily = data.get("daily")
    if not isinstance(daily, dict):
        raise WeatherServiceError("Dịch vụ thời tiết không trả về dữ liệu dự báo")

    day_index = {
        ForecastDay.TODAY: 0,
        ForecastDay.TOMORROW: 1,
        ForecastDay.DAY_AFTER_TOMORROW: 2,
    }[forecast_day]
    forecast_date = _daily_value(daily, "time", day_index)
    if not forecast_date:
        raise WeatherServiceError("Không tìm thấy ngày dự báo được yêu cầu")

    code = _daily_value(daily, "weather_code", day_index)
    return {
        "forecast_day": forecast_day,
        "forecast_date": forecast_date,
        "timezone": data.get("timezone", ""),
        "weather_code": code,
        "weather_description": WEATHER_DESCRIPTIONS.get(code, "Không rõ"),
        "temperature_min_c": _daily_value(daily, "temperature_2m_min", day_index),
        "temperature_max_c": _daily_value(daily, "temperature_2m_max", day_index),
        "feels_like_min_c": _daily_value(daily, "apparent_temperature_min", day_index),
        "feels_like_max_c": _daily_value(daily, "apparent_temperature_max", day_index),
        "precipitation_probability_max_percent": _daily_value(
            daily, "precipitation_probability_max", day_index
        ),
        "precipitation_sum_mm": _daily_value(daily, "precipitation_sum", day_index),
        "wind_speed_max_kmh": _daily_value(daily, "wind_speed_10m_max", day_index),
        "wind_direction_dominant_degrees": _daily_value(
            daily, "wind_direction_10m_dominant", day_index
        ),
        "sunrise": _daily_value(daily, "sunrise", day_index),
        "sunset": _daily_value(daily, "sunset", day_index),
    }


def get_daily_weather(
    forecast_day: ForecastDay,
    city: str | None = None,
    client_ip: str | None = None,
) -> dict:
    """Return a daily forecast for today, tomorrow, or the following day."""
    normalized_city = city.strip() if city else None
    location, fallback_name = _resolve_location(normalized_city, client_ip)
    latitude, longitude = location.latlng

    data = _get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": latitude,
            "longitude": longitude,
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "apparent_temperature_max,apparent_temperature_min,"
                "precipitation_probability_max,precipitation_sum,"
                "wind_speed_10m_max,wind_direction_10m_dominant,sunrise,sunset"
            ),
            "forecast_days": 3,
            "timezone": "auto",
        },
    )
    
    weather_data = extract_daily_weather_data(data, forecast_day)

    return {
        "location": location.address or fallback_name,
        "latitude": latitude,
        "longitude": longitude,
        **weather_data,
    }
