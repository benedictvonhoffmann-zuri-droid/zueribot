"""
City Stats Connector — ERZ Recycling & EWZ Electricity Load

Combines two datasets:
- ERZ operational data (Züri-Säcke sold, recycling quota): monthly
- EWZ electricity load (Bruttolastgang): 15-minute real-time

Data:
  https://data.stadt-zuerich.ch/dataset/erz_elog_kennzahlen
  https://data.stadt-zuerich.ch/dataset/ewz_bruttolastgang_stadt_zuerich
"""

import io
import logging
from datetime import datetime, timezone
from functools import lru_cache

import requests
import pandas as pd

logger = logging.getLogger("zuribot.connectors.city_stats")

ERZ_URL = "https://data.stadt-zuerich.ch/dataset/erz_elog_kennzahlen/download/erz_elog_kennzahlen.csv"
EWZ_URL_TEMPLATE = "https://data.stadt-zuerich.ch/dataset/ewz_bruttolastgang_stadt_zuerich/download/{year}_ewz_bruttolastgang.csv"

SOURCE_RECYCLING = {
    "name": "ERZ Entsorgung + Recycling Zürich – Betriebskennzahlen",
    "url": "https://data.stadt-zuerich.ch/dataset/erz_elog_kennzahlen",
}
SOURCE_ELECTRICITY = {
    "name": "EWZ – Bruttolastgang elektrische Energie Stadt Zürich",
    "url": "https://data.stadt-zuerich.ch/dataset/ewz_bruttolastgang_stadt_zuerich",
}

_erz_cache: pd.DataFrame | None = None
_ewz_cache: tuple[pd.DataFrame | None, datetime | None] = (None, None)
EWZ_CACHE_MINUTES = 30


@lru_cache(maxsize=1)
def _load_erz() -> pd.DataFrame | None:
    try:
        resp = requests.get(ERZ_URL, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), encoding="utf-8-sig")
        df.columns = [c.strip() for c in df.columns]
        df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce")
        return df
    except Exception as e:
        logger.error(f"Failed to load ERZ data: {e}")
        return None


def _load_ewz() -> pd.DataFrame | None:
    global _ewz_cache
    df, ts = _ewz_cache
    now = datetime.now(timezone.utc)
    if df is not None and ts and (now - ts).seconds < EWZ_CACHE_MINUTES * 60:
        return df
    try:
        year = now.year
        url = EWZ_URL_TEMPLATE.format(year=year)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), encoding="utf-8-sig")
        df.columns = [c.strip().lstrip("\ufeff").strip('"') for c in df.columns]
        # Rename first column to zeitpunkt
        df.columns = ["zeitpunkt" if i == 0 else c for i, c in enumerate(df.columns)]
        df["zeitpunkt"] = pd.to_datetime(df["zeitpunkt"], errors="coerce", utc=True)
        _ewz_cache = (df, now)
        return df
    except Exception as e:
        logger.error(f"Failed to load EWZ data: {e}")
        return None


def get_recycling_stats() -> dict:
    """
    Return latest recycling and waste statistics for Zürich.
    Shows Zürisack sales, recycling quota, and monthly tonnage.
    """
    df = _load_erz()
    if df is None:
        return {"success": False, "error": "ERZ-Daten konnten nicht geladen werden."}

    latest_date = df["Datum"].max()
    df_latest = df[df["Datum"] == latest_date]

    stats = {}
    for _, row in df_latest.iterrows():
        desc = str(row.get("Beschreibung", "")).strip()
        val = row.get("Wert")
        einheit = str(row.get("Masseinheit", "")).strip()
        if pd.notna(val):
            stats[desc] = {"wert": val, "einheit": einheit}

    # Also get recycling quota trend (last 6 months)
    quota_df = df[df["Beschreibung"].str.contains("Recyclingquote", na=False)].sort_values("Datum").tail(6)
    quota_trend = []
    for _, row in quota_df.iterrows():
        quota_trend.append({
            "datum": row["Datum"].strftime("%m/%Y"),
            "recyclingquote_prozent": row["Wert"],
        })

    return {
        "success": True,
        "data": {
            "monat": latest_date.strftime("%B %Y") if pd.notna(latest_date) else "",
            "kennzahlen": [
                {"beschreibung": k, "wert": v["wert"], "einheit": v["einheit"]}
                for k, v in stats.items()
            ],
            "recyclingquote_verlauf": quota_trend,
        },
        "source": SOURCE_RECYCLING,
    }


def get_electricity_load() -> dict:
    """
    Return current electricity load (Bruttolastgang) for the city of Zürich.
    Shows the latest 15-minute measurement and recent hourly trend.
    """
    df = _load_ewz()
    if df is None:
        return {"success": False, "error": "Stromlastdaten konnten nicht geladen werden."}

    df_valid = df[df["zeitpunkt"].notna()].sort_values("zeitpunkt")
    if df_valid.empty:
        return {"success": False, "error": "Keine Messwerte verfügbar.", "source": SOURCE_ELECTRICITY}

    latest = df_valid.iloc[-1]
    last_ts = latest["zeitpunkt"]

    # Last 4 hours of data (16 × 15min intervals)
    cutoff = last_ts - pd.Timedelta(hours=4)
    recent = df_valid[df_valid["zeitpunkt"] >= cutoff]

    trend = []
    for _, row in recent.iterrows():
        if pd.notna(row.get("bruttolastgang")):
            trend.append({
                "zeitpunkt": row["zeitpunkt"].strftime("%H:%M"),
                "kw": round(float(row["bruttolastgang"]) / 1000, 1),  # convert to MW
            })

    current_mw = round(float(latest["bruttolastgang"]) / 1000, 1) if pd.notna(latest.get("bruttolastgang")) else None

    return {
        "success": True,
        "data": {
            "aktueller_verbrauch_mw": current_mw,
            "zeitpunkt": last_ts.strftime("%d.%m.%Y %H:%M UTC"),
            "verlauf_4h": trend,
            "hinweis": "Bruttolastgang = Gesamtstromverbrauch der Stadt Zürich (EWZ-Netz), in Megawatt.",
        },
        "source": SOURCE_ELECTRICITY,
    }
