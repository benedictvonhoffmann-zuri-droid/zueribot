"""Pedestrian frequency connector — Bahnhofstrasse Hystreet sensors."""

import io
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

logger = logging.getLogger("zuribot.connectors.pedestrian")

CSV_URL = (
    "https://data.stadt-zuerich.ch/dataset/hystreet_fussgaengerfrequenzen"
    "/download/hystreet_fussgaengerfrequenzen_seit2021.csv"
)

class PedestrianConnector(BaseConnector):
    manifest = manifest

    def _fetch(self) -> pd.DataFrame | None:
        try:
            resp = requests.get(CSV_URL, timeout=self.manifest.runtime.timeout_s, stream=True)
            resp.raise_for_status()

            lines = []
            header = None
            for chunk in resp.iter_content(chunk_size=65536):
                chunk_lines = chunk.decode("utf-8", errors="replace").splitlines()
                if not header and chunk_lines:
                    header = chunk_lines[0]
                    chunk_lines = chunk_lines[1:]
                lines.extend(chunk_lines)

            recent_lines = lines[-5000:]
            if header:
                recent_lines = [header] + recent_lines

            df = pd.read_csv(io.StringIO("\n".join(recent_lines)))
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
            df = df[df["timestamp"].notna()]

            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            return df[df["timestamp"] >= cutoff]

        except Exception as e:
            logger.error("Failed to load pedestrian data: %s", e)
            return None

    def get_pedestrian_counts(self, hours: int = 6) -> dict:
        df = self._cached("hystreet", self._fetch)
        if df is None or df.empty:
            return self.err("Passantenfrequenzen konnten nicht geladen werden.")

        hours = max(1, min(24, hours))
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        df = df[df["timestamp"] >= cutoff]

        if df.empty:
            return self.err("Keine aktuellen Messwerte verfügbar.")

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
        return self.ok({
            "standorte": results,
            "letzte_messung": latest_ts_local.strftime("%d.%m.%Y %H:%M (Zürich-Zeit)"),
            "zeitraum_stunden": hours,
            "hinweis": "Hystreet-Sensoren publizieren mit ca. 1–2h Verzögerung.",
        })
