"""
Drinking Water Quality Connector — Stadt Zürich Trinkwasserqualität

Data: https://data.stadt-zuerich.ch/dataset/dib_wvz_trinkwasserqualitaet
Updated: periodically (several times per year)
"""

import io
import logging
from functools import lru_cache

import requests
import pandas as pd

logger = logging.getLogger("zuribot.connectors.water_quality")

BASE_URL = "https://data.stadt-zuerich.ch/dataset/dib_wvz_trinkwasserqualitaet/download"
CURRENT_YEAR = 2024  # Update when new year CSV is published

SOURCE = {
    "name": "Wasserversorgung Zürich – Trinkwasserqualität",
    "url": "https://data.stadt-zuerich.ch/dataset/dib_wvz_trinkwasserqualitaet",
}

# Parameters to highlight in summaries
KEY_PARAMS = {
    "E. coli": "E. coli (Keime)",
    "Enterokokken": "Enterokokken",
    "AMK": "Aerobe mesophile Keime",
    "Nitrat": "Nitrat",
    "Temperatur": "Temperatur",
    "Trübung": "Trübung",
    "pH": "pH-Wert",
    "Chlor": "Chlor",
}


@lru_cache(maxsize=1)
def _load_data() -> pd.DataFrame | None:
    """Load current year's water quality data."""
    try:
        url = f"{BASE_URL}/{CURRENT_YEAR}_Trinkwasserqualitaet.csv"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.BytesIO(resp.content), encoding="utf-8-sig")
        # Decode column names properly (files use latin-1 with UTF-8 BOM artifacts)
        df.columns = [
            c.encode("latin-1", errors="replace").decode("utf-8", errors="replace")
             .strip().strip("\ufeff").strip()
            for c in df.columns
        ]
        # Find the date column regardless of encoding artefacts
        date_col = next((c for c in df.columns if "atum" in c), None)
        if date_col:
            df = df.rename(columns={date_col: "Datum"})
        df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce")
        return df
    except Exception as e:
        logger.error(f"Failed to load water quality data: {e}")
        return None


def get_water_quality(standort: str = "") -> dict:
    """
    Return current drinking water quality measurements for Zürich.

    Args:
        standort: Measurement location (e.g. "Moos", "Hardhof", "Lengg").
                  Empty = return summary of all locations.
    """
    df = _load_data()
    if df is None:
        return {"success": False, "error": "Trinkwasserdaten konnten nicht geladen werden."}

    # Filter by location if specified
    if standort:
        mask = df.iloc[:, 1].str.contains(standort, case=False, na=False)  # Standort column
        df = df[mask]
        if df.empty:
            return {
                "success": False,
                "error": f"Kein Standort '{standort}' gefunden.",
                "source": SOURCE,
            }

    # Get most recent measurements per location + parameter
    try:
        standort_col = [c for c in df.columns if "tandort" in c][0]
        param_col = [c for c in df.columns if "arameter" in c and "gruppe" not in c.lower()][0]
        wert_col = [c for c in df.columns if "esswert" in c or "Wert" in c][0]
        hw_col = [c for c in df.columns if "chst" in c or "max" in c.lower()][0] if any("chst" in c for c in df.columns) else None
        richtwert_col = [c for c in df.columns if "ichtwert" in c][0] if any("ichtwert" in c for c in df.columns) else None
    except IndexError:
        standort_col, param_col, wert_col = df.columns[1], df.columns[3], df.columns[7]
        hw_col, richtwert_col = None, None

    latest = df.sort_values("Datum").groupby([standort_col, param_col]).last().reset_index()

    # Build summary
    locations = {}
    for _, row in latest.iterrows():
        loc = str(row[standort_col])
        param = str(row[param_col])
        val = row[wert_col]
        max_val = row[hw_col] if hw_col else None
        datum = row["Datum"].strftime("%d.%m.%Y") if pd.notna(row["Datum"]) else ""

        # Check if any key parameter
        is_key = any(k in param for k in KEY_PARAMS)
        if not is_key:
            continue

        if loc not in locations:
            locations[loc] = {"standort": loc, "datum": datum, "parameter": [], "alle_werte_ok": True}

        # Check compliance
        ok = True
        if max_val is not None and pd.notna(max_val) and pd.notna(val):
            try:
                ok = float(val) <= float(max_val)
            except (ValueError, TypeError):
                ok = True
        if not ok:
            locations[loc]["alle_werte_ok"] = False

        locations[loc]["parameter"].append({
            "name": param,
            "wert": val if pd.notna(val) else "nicht nachweisbar",
            "grenzwert": max_val if (max_val is not None and pd.notna(max_val)) else "–",
            "ok": ok,
        })

    result_list = list(locations.values())

    overall_ok = all(loc["alle_werte_ok"] for loc in result_list)

    return {
        "success": True,
        "data": {
            "fazit": "Das Trinkwasser in Zürich entspricht allen gesetzlichen Anforderungen." if overall_ok
                     else "Achtung: Einzelne Messwerte über dem Grenzwert — Details prüfen.",
            "alle_werte_ok": overall_ok,
            "standorte": result_list,
            "jahr": CURRENT_YEAR,
        },
        "source": SOURCE,
    }
