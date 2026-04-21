"""Crime statistics connector — Kanton Zürich PKS."""

import io
import logging
from functools import lru_cache

import pandas as pd
import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

logger = logging.getLogger("zuribot.connectors.crime")

STRAFTATEN_URL = (
    "https://data.stadt-zuerich.ch/dataset/"
    "ktzh_pks_straftaten_tatbestandgruppe_gemeinden_stadtkreise/download/KTZH_00001202_00003600.csv"
)

STADTKREIS_MAP = {
    "1": "Kreis 01", "2": "Kreis 02", "3": "Kreis 03", "4": "Kreis 04",
    "5": "Kreis 05", "6": "Kreis 06", "7": "Kreis 07", "8": "Kreis 08",
    "9": "Kreis 09", "10": "Kreis 10", "11": "Kreis 11", "12": "Kreis 12",
    "kreis 1": "Kreis 01", "kreis 2": "Kreis 02", "kreis 3": "Kreis 03",
    "kreis 4": "Kreis 04", "kreis 5": "Kreis 05", "kreis 6": "Kreis 06",
    "kreis 7": "Kreis 07", "kreis 8": "Kreis 08", "kreis 9": "Kreis 09",
    "kreis 10": "Kreis 10", "kreis 11": "Kreis 11", "kreis 12": "Kreis 12",
}


@lru_cache(maxsize=1)
def _load_straftaten() -> pd.DataFrame | None:
    try:
        resp = requests.get(STRAFTATEN_URL, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), encoding="utf-8-sig")
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        logger.error(f"Failed to load crime data: {e}")
        return None


class CrimeConnector(BaseConnector):
    manifest = manifest

    def get_crime_stats(self, stadtkreis: str = "", category: str = "") -> dict:
        df = _load_straftaten()
        if df is None:
            return self.err("Kriminalstatistik konnte nicht geladen werden.")

        latest_year = df["Ausgangsjahr"].max()
        df_year = df[df["Ausgangsjahr"] == latest_year].copy()

        df_zurich = df_year[df_year["Stadtkreis_Name"].notna() & (df_year["Stadtkreis_Name"] != "")]
        if df_zurich.empty:
            df_zurich = df_year[df_year["Gemeindename"].str.contains("rich", case=False, na=False)]

        if stadtkreis:
            kreis_key = stadtkreis.lower().strip()
            kreis_label = STADTKREIS_MAP.get(kreis_key, stadtkreis)
            mask = df_zurich["Stadtkreis_Name"].str.contains(
                kreis_label.split()[-1].lstrip("0"), case=False, na=False
            )
            df_zurich = df_zurich[mask]
            if df_zurich.empty:
                return self.err(f"Keine Daten für Stadtkreis '{stadtkreis}' gefunden.")

        if category:
            df_zurich = df_zurich[df_zurich["Haupttitel"].str.contains(category, case=False, na=False)]

        summary = (
            df_zurich.groupby(["Stadtkreis_Name", "Haupttitel"])
            .agg(straftaten=("Straftaten_total", "sum"), haeufigkeit=("Häufigkeitszahl", "mean"))
            .reset_index()
            .sort_values("straftaten", ascending=False)
        )

        kreise = {}
        for _, row in summary.iterrows():
            kreis = row["Stadtkreis_Name"] or "Gesamt"
            if kreis not in kreise:
                kreise[kreis] = {"kreis": kreis, "delikte": []}
            kreise[kreis]["delikte"].append({
                "kategorie": row["Haupttitel"],
                "straftaten": int(row["straftaten"]),
                "haeufigkeitszahl_pro_1000": round(float(row["haeufigkeit"]), 1) if pd.notna(row["haeufigkeit"]) else None,
            })

        return self.ok({
            "jahr": int(latest_year),
            "stadtkreise": list(kreise.values()),
            "hinweis": "Häufigkeitszahl = Straftaten pro 1'000 Einwohner. Quelle: PKS Kantonspolizei Zürich.",
        })
