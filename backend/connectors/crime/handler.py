"""Crime statistics connector — Kanton Zürich PKS."""

import io
import logging

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
    **{str(n): f"Kreis {n}" for n in range(1, 13)},
    **{f"kreis {n}": f"Kreis {n}" for n in range(1, 13)},
}


class CrimeConnector(BaseConnector):
    manifest = manifest

    def _fetch_straftaten(self) -> pd.DataFrame | None:
        try:
            resp = requests.get(STRAFTATEN_URL, timeout=self.manifest.runtime.timeout_s)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text), encoding="utf-8-sig")
            df.columns = [c.strip() for c in df.columns]
            return df
        except Exception as e:
            logger.error(f"Failed to load crime data: {e}")
            return None

    def get_crime_stats(self, stadtkreis: str = "", category: str = "") -> dict:
        df = self._cached("straftaten", self._fetch_straftaten)
        if df is None:
            return self.err("Kriminalstatistik konnte nicht geladen werden.")

        latest_year = df["Ausgangsjahr"].max()
        df_year = df[df["Ausgangsjahr"] == latest_year].copy()

        df_zurich = df_year[df_year["Stadtkreis_Name"].notna() & (df_year["Stadtkreis_Name"] != "")]
        if df_zurich.empty:
            df_zurich = df_year[df_year["Gemeindename"].str.contains("rich", case=False, na=False)]

        if stadtkreis:
            kreis_key = stadtkreis.lower().strip()
            kreis_label = STADTKREIS_MAP.get(kreis_key)
            if kreis_label is None:
                return self.err(
                    f"Unbekannter Stadtkreis '{stadtkreis}'. Gültig: 1–12 oder 'kreis N'."
                )
            df_zurich = df_zurich[df_zurich["Stadtkreis_Name"] == kreis_label]
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
