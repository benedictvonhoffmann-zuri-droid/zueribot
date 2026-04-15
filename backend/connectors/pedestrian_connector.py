"""
Pedestrian Frequency Connector — Bahnhofstrasse Passantenfrequenzen

Data: https://data.stadt-zuerich.ch/dataset/hystreet_fussgaengerfrequenzen
Sensor locations: Bahnhofstrasse Nord, Mitte, Süd + Lintheschergasse
Updated: hourly
"""

import io
import logging
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import requests
import pandas as pd

logger = logging.getLogger("zuribot.connectors.pedestrian")

CSV_URL = (
    "https://data.stadt-zuerich.ch/dataset/hystreet_fussgaengerfrequenzen"
    "/download/hystreet_fussgaengerfrequenzen_seit2021.csv"
)

SOURCE = {
    "name": "Stadt Zürich – Passantenfrequenzen Bahnhofstrasse (Hystreet)",
    "url": "https://data.stadt-zuerich.ch/dataset/hystreet_fussgaengerfrequenzen",
}

_cache_time: datetime | None = None
_cache_df: pd.DataFrame | None = None
CACHE_TTL_MINUTES = 60


def _load_recent() -> pd.DataFrame | None:
    """Load the CSV and return only the last 24 hours of data."""
    global _cache_time, _cache_df

    now = datetime.now(timezone.utc)
    if _cache_df is not None and _cache_time and (now - _cache_time).seconds < CACHE_TTL_MINUTES * 60:
        return _cache_df

    try:
        # Stream the file and collect only last N lines (efficient for large files)
        resp = requests.get(CSV_URL, timeout=60, stream=True)
        resp.raise_for_status()

        # Read in chunks, keep last 10000 lines
        lines = []
        header = None
        for chunk in resp.iter_content(chunk_size=65536):
            chunk_lines = chunk.decode("utf-8", errors="replace").splitlines()
            if not header and chunk_lines:
                header = chunk_lines[0]
                chunk_lines = chunk_lines[1:]
            lines.extend(chunk_lines)

        # Keep only last 5000 data rows
        recent_lines = lines[-5000:]
        if header:
            recent_lines = [header] + recent_lines

        df = pd.read_csv(io.StringIO("\n".join(recent_lines)))
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df = df[df["timestamp"].notna()]

        # Filter to last 24 hours
        cutoff = now - timedelta(hours=24)
        df = df[df["timestamp"] >= cutoff]

        _cache_df = df
        _cache_time = now
        return df

    except Exception as e:
        logger.error(f"Failed to load pedestrian data: {e}")
        return None


def get_pedestrian_counts(hours: int = 6) -> dict:
    """
    Return recent pedestrian counts on Zürich Bahnhofstrasse.

    Args:
        hours: Look back window in hours (1–24). Default 6.
    """
    df = _load_recent()
    if df is None or df.empty:
        return {"success": False, "error": "Passantenfrequenzen konnten nicht geladen werden."}

    hours = max(1, min(24, hours))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    df = df[df["timestamp"] >= cutoff]

    if df.empty:
        return {"success": False, "error": "Keine aktuellen Messwerte verfügbar.", "source": SOURCE}

    # Latest timestamp in data
    latest_ts = df["timestamp"].max()

    _ZURICH_TZ = ZoneInfo("Europe/Zurich")

    results = []
    for loc in df["location_name"].unique():
        loc_df = df[df["location_name"] == loc].sort_values("timestamp")
        latest = loc_df.iloc[-1]
        count_series = pd.to_numeric(loc_df["pedestrians_count"], errors="coerce")
        latest_count = pd.to_numeric(latest.get("pedestrians_count"), errors="coerce")
        local_ts = latest["timestamp"].astimezone(_ZURICH_TZ)
        results.append({
            "standort": loc,
            "passanten_letzte_stunde": int(latest_count) if pd.notna(latest_count) else None,
            "wetter": latest.get("weather_condition", ""),
            "temperatur_c": round(float(latest["temperature"]), 1) if pd.notna(latest.get("temperature")) else None,
            "zeitpunkt": local_ts.strftime("%d.%m.%Y %H:%M (Zürich-Zeit)"),
            f"durchschnitt_letzte_{hours}h": int(count_series.mean()) if count_series.notna().any() else None,
        })

    latest_ts_local = latest_ts.astimezone(_ZURICH_TZ)
    return {
        "success": True,
        "data": {
            "standorte": results,
            "letzte_messung": latest_ts_local.strftime("%d.%m.%Y %H:%M (Zürich-Zeit)"),
            "zeitraum_stunden": hours,
            "hinweis": "Hystreet-Sensoren publizieren mit ca. 1–2h Verzögerung.",
        },
        "source": SOURCE,
    }
