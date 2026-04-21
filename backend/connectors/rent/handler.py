"""Rent price connector — Stadt Zürich Mietpreiserhebung (MPE)."""

import io
import logging
from typing import Optional

import pandas as pd
import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

logger = logging.getLogger("zuribot.connectors.rent")

CSV_URL = (
    "https://data.stadt-zuerich.ch/dataset/"
    "bau_whg_mpe_mietpreis_raum_zizahl_gn_jahr_od5161/download/BAU516OD5161.csv"
)

# Dataset only breaks rents down by these bins (MPE publishes coarse categories).
ROOMS_MAP = {
    "2": "2 Zimmer",
    "3": "3 Zimmer",
    "4": "4 Zimmer",
    "all": "2 , 3  und 4 Zimmer",
}


class RentConnector(BaseConnector):
    manifest = manifest

    def _fetch(self) -> Optional[pd.DataFrame]:
        try:
            resp = requests.get(CSV_URL, timeout=self.manifest.runtime.timeout_s)
            resp.raise_for_status()
            df = pd.read_csv(io.BytesIO(resp.content), encoding="utf-8-sig")
            df.columns = [
                c.encode("latin-1", errors="replace").decode("utf-8", errors="replace")
                 .strip().strip("\ufeff").strip('"').strip()
                for c in df.columns
            ]
            return df
        except Exception as e:
            logger.error(f"Failed to load rent data: {e}")
            return None

    def get_rent_prices(self, quartier: str = "", rooms: str = "", gemeinnuetzig: bool = False) -> dict:
        df = self._cached("mpe", self._fetch)
        if df is None:
            return self.err("Mietpreisdaten konnten nicht geladen werden.")

        latest_year = df["StichtagDatJahr"].max()
        df = df[df["StichtagDatJahr"] == latest_year].copy()

        df = df[df["PreisartLang"] == "netto"]
        df = df[df["EinheitLang"] == "Wohnung"]

        if gemeinnuetzig:
            df = df[df["GemeinnuetzigLang"].str.contains("Gemeinn", na=False)]
        else:
            df = df[df["GemeinnuetzigLang"].str.contains("Nicht", na=False)]

        if quartier:
            mask = df["RaumeinheitLang"].str.contains(quartier, case=False, na=False)
            if mask.sum() == 0:
                mask = df["GliederungLang"].str.contains(quartier, case=False, na=False)
            df = df[mask]
            if df.empty:
                return self.err(f"Keine Mietpreisdaten für '{quartier}' gefunden.")

        if rooms:
            room_key = rooms.replace(",", ".").strip()
            room_label = ROOMS_MAP.get(room_key)
            if room_label is None:
                return self.err(
                    f"Unbekannte Zimmerzahl '{rooms}'. Gültig: {', '.join(ROOMS_MAP.keys())}."
                )
            df = df[df["ZimmerLang"] == room_label]

        if df.empty:
            return self.err("Keine Daten für diese Filterkomibination.")

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

        return self.ok({
            "results": results,
            "year": int(latest_year),
            "note": "Nettomieten (ohne Nebenkosten) in CHF/Monat",
        })
