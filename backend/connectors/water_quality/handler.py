"""Drinking water quality connector — Wasserversorgung Zürich."""

import io
import logging
from datetime import datetime

import pandas as pd
import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

logger = logging.getLogger("zuribot.connectors.water_quality")

BASE_URL = "https://data.stadt-zuerich.ch/dataset/dib_wvz_trinkwasserqualitaet/download"

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


class WaterQualityConnector(BaseConnector):
    manifest = manifest

    def _fetch_year(self, year: int) -> pd.DataFrame | None:
        try:
            url = f"{BASE_URL}/{year}_Trinkwasserqualitaet.csv"
            resp = requests.get(url, timeout=self.manifest.runtime.timeout_s)
            resp.raise_for_status()
            df = pd.read_csv(io.BytesIO(resp.content), encoding="utf-8-sig")
            df.columns = [
                c.encode("latin-1", errors="replace").decode("utf-8", errors="replace")
                 .strip().strip("\ufeff").strip()
                for c in df.columns
            ]
            date_col = next((c for c in df.columns if "atum" in c), None)
            if date_col:
                df = df.rename(columns={date_col: "Datum"})
            df["Datum"] = pd.to_datetime(df["Datum"], errors="coerce")
            return df
        except Exception as e:
            logger.warning("Failed to load water quality data for %s: %s", year, e)
            return None

    def _load(self) -> tuple[pd.DataFrame | None, int | None]:
        """Try current year, fall back to previous years (dataset published annually)."""
        current = datetime.now().year
        for year in (current, current - 1, current - 2):
            df = self._cached(f"wq:{year}", lambda y=year: self._fetch_year(y))
            if df is not None:
                return df, year
        return None, None

    def get_water_quality(self, standort: str = "") -> dict:
        df, year = self._load()
        if df is None:
            return self.err("Trinkwasserdaten konnten nicht geladen werden.")

        if standort:
            mask = df.iloc[:, 1].str.contains(standort, case=False, na=False)
            df = df[mask]
            if df.empty:
                return self.err(f"Kein Standort '{standort}' gefunden.")

        try:
            standort_col = [c for c in df.columns if "tandort" in c][0]
            param_col = [c for c in df.columns if "arameter" in c and "gruppe" not in c.lower()][0]
            wert_col = [c for c in df.columns if "esswert" in c or "Wert" in c][0]
            hw_col = [c for c in df.columns if "chst" in c or "max" in c.lower()][0] if any("chst" in c for c in df.columns) else None
        except IndexError:
            standort_col, param_col, wert_col = df.columns[1], df.columns[3], df.columns[7]
            hw_col = None

        latest = df.sort_values("Datum").groupby([standort_col, param_col]).last().reset_index()

        locations = {}
        for _, row in latest.iterrows():
            loc = str(row[standort_col])
            param = str(row[param_col])
            val = row[wert_col]
            max_val = row[hw_col] if hw_col else None
            datum = row["Datum"].strftime("%d.%m.%Y") if pd.notna(row["Datum"]) else ""

            is_key = any(k in param for k in KEY_PARAMS)
            if not is_key:
                continue

            if loc not in locations:
                locations[loc] = {"standort": loc, "datum": datum, "parameter": [], "alle_werte_ok": True}

            ok_flag = True
            if max_val is not None and pd.notna(max_val) and pd.notna(val):
                try:
                    ok_flag = float(val) <= float(max_val)
                except (ValueError, TypeError):
                    ok_flag = True
            if not ok_flag:
                locations[loc]["alle_werte_ok"] = False

            locations[loc]["parameter"].append({
                "name": param,
                "wert": val if pd.notna(val) else "nicht nachweisbar",
                "grenzwert": max_val if (max_val is not None and pd.notna(max_val)) else "–",
                "ok": ok_flag,
            })

        result_list = list(locations.values())
        overall_ok = all(loc["alle_werte_ok"] for loc in result_list)

        return self.ok({
            "fazit": "Das Trinkwasser in Zürich entspricht allen gesetzlichen Anforderungen." if overall_ok
                     else "Achtung: Einzelne Messwerte über dem Grenzwert — Details prüfen.",
            "alle_werte_ok": overall_ok,
            "standorte": result_list,
            "jahr": year,
        })
