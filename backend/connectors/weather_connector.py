"""
Zürich Weather Connector
- Raw data from Open-Meteo API
"""

import requests

WMO_CODES = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy",
    3: "Overcast", 45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Light showers", 81: "Showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm",
}


def get_weather(location="Zürich"):
    """Current weather and 3-day forecast for Zürich."""
    try:
        resp = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": 47.3769,
            "longitude": 8.5417,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "timezone": "Europe/Zurich",
            "forecast_days": 3,
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current", {})
        daily = data.get("daily", {})

        # Build forecast list
        forecast = []
        if daily.get("time"):
            for i, date in enumerate(daily["time"]):
                forecast.append({
                    "date": date,
                    "weather_code": daily.get("weather_code", [])[i] if i < len(daily.get("weather_code", [])) else None,
                    "weather_description": WMO_CODES.get(daily.get("weather_code", [])[i], "Unknown") if i < len(daily.get("weather_code", [])) else "Unknown",
                    "temp_max": daily.get("temperature_2m_max", [])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
                    "temp_min": daily.get("temperature_2m_min", [])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
                    "precipitation": daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else None,
                })

        return {
            "success": True,
            "data": {
                "current": {
                    "time": current.get("time"),
                    "temperature_c": current.get("temperature_2m"),
                    "humidity_pct": current.get("relative_humidity_2m"),
                    "precipitation_mm": current.get("precipitation"),
                    "wind_speed_kmh": current.get("wind_speed_10m"),
                    "weather_code": current.get("weather_code"),
                    "weather_description": WMO_CODES.get(current.get("weather_code"), "Unknown"),
                },
                "forecast": forecast,
            },
            "source": {"name": "Open-Meteo", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "Open-Meteo", "type": "official"}, "error": str(e)}