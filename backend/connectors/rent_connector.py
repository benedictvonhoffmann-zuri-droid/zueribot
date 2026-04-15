"""
Rent Price Connector — Stadt Zürich Mietpreiserhebung (MPE)

Data: https://data.stadt-zuerich.ch/dataset/bau_whg_mpe_mietpreis_raum_zizahl_gn_jahr_od5161
Updated: every 2 years (latest: April 2024)
"""

import io
import logging
from functools import lru_cache
from typing import Optional

import requests
import pandas as pd

logger = logging.getLogger("zuribot.connectors.rent")

CSV_URL = (
    "https://data.stadt-zuerich.ch/dataset/"
    "bau_whg_mpe_mietpreis_raum_zizahl_gn_jahr_od5161/download/BAU516OD5161.csv"
)

SOURCE = {
    "name": "Stadt Zürich Mietpreiserhebung (MPE)",
    "url": "https://data.stadt-zuerich.ch/dataset/bau_whg_mpe_mietpreis_raum_zizahl_gn_jahr_od5161",
}

ROOMS_MAP = {
    "1": "1 Zimmer", "1.5": "1,5 Zimmer",
    "2": "2 Zimmer", "2.5": "2,5 Zimmer",
    "3": "3 Zimmer", "3.5": "3,5 Zimmer",
    "4": "4 Zimmer", "4.5": "4,5 Zimmer",
    "5": "5 Zimmer", "5+": "5 und mehr Zimmer",
}


@lru_cache(maxsize=1)
def _load_data() -> Optional[pd.DataFrame]:
    try:
        resp = requests.get(CSV_URL, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.BytesIO(resp.content), encoding="utf-8-sig")
        # Strip BOM artifacts and quotes from column names
        df.columns = [
            c.encode("latin-1", errors="replace").decode("utf-8", errors="replace")
             .strip().strip("\ufeff").strip('"').strip()
            for c in df.columns
        ]
        return df
    except Exception as e:
        logger.error(f"Failed to load rent data: {e}")
        return None


def get_rent_prices(
    quartier: str = "",
    rooms: str = "",
    gemeinnuetzig: bool = False,
) -> dict:
    """
    Return rent price statistics for Zürich.

    Args:
        quartier: Neighbourhood/Stadtkreis name (e.g. "Ganze Stadt", "Kreis 1",
                  "Langstrasse", "Wipkingen"). Empty = all.
        rooms: Number of rooms as string (e.g. "2", "3", "3.5"). Empty = all.
        gemeinnuetzig: If True, return cooperative housing prices only.
    """
    df = _load_data()
    if df is None:
        return {"success": False, "error": "Mietpreisdaten konnten nicht geladen werden."}

    # Use latest survey year
    latest_year = df["StichtagDatJahr"].max()
    df = df[df["StichtagDatJahr"] == latest_year].copy()

    # Filter: only net rent (not incl. utilities), apartments (not houses)
    df = df[df["PreisartLang"] == "netto"]
    df = df[df["EinheitLang"] == "Wohnung"]

    # Cooperative filter
    if gemeinnuetzig:
        df = df[df["GemeinnuetzigLang"].str.contains("Gemeinn", na=False)]
    else:
        df = df[df["GemeinnuetzigLang"].str.contains("Nicht", na=False)]

    # Quartier filter
    if quartier:
        mask = df["RaumeinheitLang"].str.contains(quartier, case=False, na=False)
        if mask.sum() == 0:
            mask = df["GliederungLang"].str.contains(quartier, case=False, na=False)
        df = df[mask]
        if df.empty:
            return {
                "success": False,
                "error": f"Keine Mietpreisdaten für '{quartier}' gefunden.",
                "source": SOURCE,
            }

    # Rooms filter
    if rooms:
        room_label = ROOMS_MAP.get(rooms.replace(",", "."), rooms)
        df = df[df["ZimmerLang"].str.contains(room_label.split()[0], case=False, na=False)]

    if df.empty:
        return {"success": False, "error": "Keine Daten für diese Filterkomibination.", "source": SOURCE}

    results = []
    for _, row in df.iterrows():
        results.append({
            "quartier": row.get("RaumeinheitLang", ""),
            "zimmer": row.get("ZimmerLang", ""),
            "gemeinnuetzig": "Gemeinnützig" in str(row.get("GemeinnuetzigLang", "")),
            "median_chf": round(float(row["qu50"]), 0) if pd.notna(row.get("qu50")) else None,
            "mittelwert_chf": round(float(row["mean"]), 0) if pd.notna(row.get("mean")) else None,
            "q25_chf": round(float(row["qu25"]), 0) if pd.notna(row.get("qu25")) else None,
            "q75_chf": round(float(row["qu75"]), 0) if pd.notna(row.get("qu75")) else None,
            "jahr": int(row.get("StichtagDatJahr", latest_year)),
        })

    return {
        "success": True,
        "data": {
            "results": results,
            "year": int(latest_year),
            "note": "Nettomieten (ohne Nebenkosten) in CHF/Monat",
        },
        "source": SOURCE,
    }
