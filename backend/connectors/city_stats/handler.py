"""City stats connector — ERZ recycling + EWZ electricity load."""

import io
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

logger = logging.getLogger("zuribot.connectors.city_stats")

ERZ_URL = "https://data.stadt-zuerich.ch/dataset/erz_elog_kennzahlen/download/erz_elog_kennzahlen.csv"
EWZ_URL_TEMPLATE = "https://data.stadt-zuerich.ch/dataset/ewz_bruttolastgang_stadt_zuerich/download/{year}_ewz_bruttolastgang.csv"


class CityStatsConnector(BaseConnector):
    manifest = manifest

    def _fetch_erz(self) -> pd.DataFrame | None:
        try:
            resp = requests.get(ERZ_URL, timeout=self.manifest.runtime.timeout_s)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text), encoding="utf-8-sig")
            df.columns = [c.strip() for c in df.columns]
            df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce")
            return df
        except Exception as e:
            logger.error("Failed to load ERZ data: %s", e)
            return None

    def _fetch_ewz(self) -> pd.DataFrame | None:
        try:
            year = datetime.now(timezone.utc).year
            url = EWZ_URL_TEMPLATE.format(year=year)
            resp = requests.get(url, timeout=self.manifest.runtime.timeout_s)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text), encoding="utf-8-sig")
            df.columns = [c.strip().lstrip("\ufeff").strip('"') for c in df.columns]
            df.columns = ["zeitpunkt" if i == 0 else c for i, c in enumerate(df.columns)]
            df["zeitpunkt"] = pd.to_datetime(df["zeitpunkt"], errors="coerce", utc=True)
            return df
        except Exception as e:
            logger.error("Failed to load EWZ data: %s", e)
            return None

    def get_recycling_stats(self) -> dict:
        df = self._cached("erz", self._fetch_erz)
        if df is None:
            return self.err("ERZ-Daten konnten nicht geladen werden.")

        latest_date = df["Datum"].max()
        df_latest = df[df["Datum"] == latest_date]

        stats = {}
        for _, row in df_latest.iterrows():
            desc = str(row.get("Beschreibung", "")).strip()
            val = row.get("Wert")
            einheit = str(row.get("Masseinheit", "")).strip()
            if pd.notna(val):
                stats[desc] = {"wert": val, "einheit": einheit}

        quota_df = df[df["Beschreibung"].str.contains("Recyclingquote", na=False)].sort_values("Datum").tail(6)
        quota_trend = []
        for _, row in quota_df.iterrows():
            quota_trend.append({
                "datum": row["Datum"].strftime("%m/%Y"),
                "recyclingquote_prozent": row["Wert"],
            })

        return self.ok({
            "monat": latest_date.strftime("%B %Y") if pd.notna(latest_date) else "",
            "kennzahlen": [
                {"beschreibung": k, "wert": v["wert"], "einheit": v["einheit"]}
                for k, v in stats.items()
            ],
            "recyclingquote_verlauf": quota_trend,
        })

    def get_electricity_load(self) -> dict:
        df = self._cached("ewz", self._fetch_ewz)
        if df is None:
            return self.err("Stromlastdaten konnten nicht geladen werden.")

        df_valid = df[df["zeitpunkt"].notna()].sort_values("zeitpunkt")
        if df_valid.empty:
            return self.err("Keine Messwerte verfügbar.")

        latest = df_valid.iloc[-1]
        last_ts = latest["zeitpunkt"]

        cutoff = last_ts - pd.Timedelta(hours=4)
        recent = df_valid[df_valid["zeitpunkt"] >= cutoff]

        _ZURICH_TZ = ZoneInfo("Europe/Zurich")
        last_ts_local = last_ts.astimezone(_ZURICH_TZ)

        trend = []
        for _, row in recent.iterrows():
            if pd.notna(row.get("bruttolastgang")):
                local_row_ts = row["zeitpunkt"].astimezone(_ZURICH_TZ)
                trend.append({
                    "zeitpunkt": local_row_ts.strftime("%H:%M"),
                    "mw": round(float(row["bruttolastgang"]) / 1000, 1),
                })

        current_mw = round(float(latest["bruttolastgang"]) / 1000, 1) if pd.notna(latest.get("bruttolastgang")) else None

        now_utc = datetime.now(timezone.utc)
        lag_hours = round((now_utc - last_ts.replace(tzinfo=timezone.utc) if last_ts.tzinfo is None else now_utc - last_ts).total_seconds() / 3600, 1)
        lag_note = f"Letzte verfügbare Messung: {last_ts_local.strftime('%d.%m.%Y %H:%M')} (Zürich-Zeit). EWZ veröffentlicht Daten mit ca. {lag_hours:.0f}h Verzögerung."

        return self.ok({
            "aktueller_verbrauch_mw": current_mw,
            "zeitpunkt": last_ts_local.strftime("%d.%m.%Y %H:%M (Zürich-Zeit)"),
            "verlauf_4h": trend,
            "hinweis": f"Bruttolastgang = Gesamtstromverbrauch der Stadt Zürich (EWZ-Netz), in Megawatt. {lag_note}",
        })
