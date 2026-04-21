"""Weather connector — Open-Meteo forecast for Zürich."""

import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

WMO_CODES = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy",
    3: "Overcast", 45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Light showers", 81: "Showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm",
}


class WeatherConnector(BaseConnector):
    manifest = manifest

    def get_weather(self, location: str = "Zürich") -> dict:
        try:
            resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": 47.3769,
                    "longitude": 8.5417,
                    "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
                    "timezone": "Europe/Zurich",
                    "forecast_days": 3,
                },
                timeout=self.manifest.runtime.timeout_s,
            )
            resp.raise_for_status()
            data = resp.json()

            current = data.get("current", {})
            daily = data.get("daily", {})

            forecast = []
            times = daily.get("time") or []
            codes = daily.get("weather_code") or []
            tmax = daily.get("temperature_2m_max") or []
            tmin = daily.get("temperature_2m_min") or []
            precip = daily.get("precipitation_sum") or []

            for i, date in enumerate(times):
                code = codes[i] if i < len(codes) else None
                forecast.append({
                    "date": date,
                    "weather_code": code,
                    "weather_description": WMO_CODES.get(code, "Unknown"),
                    "temp_max": tmax[i] if i < len(tmax) else None,
                    "temp_min": tmin[i] if i < len(tmin) else None,
                    "precipitation": precip[i] if i < len(precip) else None,
                })

            current_code = current.get("weather_code")
            return self.ok({
                "current": {
                    "time": current.get("time"),
                    "temperature_c": current.get("temperature_2m"),
                    "humidity_pct": current.get("relative_humidity_2m"),
                    "precipitation_mm": current.get("precipitation"),
                    "wind_speed_kmh": current.get("wind_speed_10m"),
                    "weather_code": current_code,
                    "weather_description": WMO_CODES.get(current_code, "Unknown"),
                },
                "forecast": forecast,
            })
        except Exception as e:
            return self.err(e)
