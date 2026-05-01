"""Voting connector — Stadt Zürich Open Data Portal."""

import csv
import io

import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

VOTING_CSV_URL = "https://ckan-prod.zurich.datopian.com/dataset/politik_abstimmungen_seit1933/resource/65e011cf-6479-4fea-aa12-5928924ac4d2/download/abstimmungen_seit1933.csv"


class VotingConnector(BaseConnector):
    manifest = manifest

    def get_voting_results(
        self,
        date_filter: str = "",
        level: str = "",
        limit: int = 5,
        kreis: str | int | None = None,
    ) -> dict:
        try:
            resp = requests.get(
                VOTING_CSV_URL,
                timeout=self.manifest.runtime.timeout_s,
                headers={"User-Agent": "ZuriBot/1.0"},
            )
            resp.raise_for_status()
            text = resp.content.decode("utf-8-sig")
            rows = list(csv.DictReader(io.StringIO(text)))

            if not rows:
                return self.err("No voting data available")

            filtered = rows

            if date_filter:
                df = date_filter.strip()
                filtered = [r for r in filtered if r.get("Abstimmungs_Datum", "").startswith(df)]

            if level:
                lf = level.strip()
                filtered = [r for r in filtered if lf.lower() in r.get("Name_Politische_Ebene", "").lower()]

            if kreis is not None:
                kreis_str = str(kreis)
                filtered = [r for r in filtered if r.get("Nr_Wahlkreis_StZH", "").strip() == kreis_str]

            if not date_filter and not level and not kreis:
                dates = sorted({r.get("Abstimmungs_Datum", "") for r in filtered}, reverse=True)
                if dates:
                    latest_date = dates[0]
                    filtered = [r for r in filtered if r.get("Abstimmungs_Datum", "") == latest_date]

            votes = {}
            for row in filtered:
                vote_key = (row.get("Abstimmungs_Datum", ""), row.get("Abstimmungs_Text", ""), row.get("Name_Politische_Ebene", ""))
                if vote_key not in votes:
                    votes[vote_key] = {
                        "date": row.get("Abstimmungs_Datum", ""),
                        "title": row.get("Abstimmungs_Text", ""),
                        "level": row.get("Name_Politische_Ebene", ""),
                        "results": [],
                    }

                try:
                    ja_abs = int(row.get("Ja_Absolut", "0") or "0")
                    nein_abs = int(row.get("Nein_Absolut", "0") or "0")
                except ValueError:
                    ja_abs = 0
                    nein_abs = 0

                try:
                    stimmberechtigt = int(row.get("Stimmberechtigt", "0") or "0")
                except ValueError:
                    stimmberechtigt = 0

                try:
                    beteiligung = float(row.get("Stimmbeteiligung_Prozent", "0") or "0")
                    ja_prozent = float(row.get("Ja_Prozent", "0") or "0")
                    nein_prozent = float(row.get("Nein_Prozent", "0") or "0")
                except ValueError:
                    beteiligung = 0
                    ja_prozent = 0
                    nein_prozent = 0

                votes[vote_key]["results"].append({
                    "gebiet": row.get("Name_Resultat_Gebiet", ""),
                    "nr_wahlkreis": row.get("Nr_Wahlkreis_StZH", "").strip(),
                    "wahlkreis": row.get("Name_Wahlkreis_StZH", ""),
                    "stimmberechtigt": stimmberechtigt,
                    "ja_absolut": ja_abs,
                    "nein_absolut": nein_abs,
                    "beteiligung_pct": beteiligung,
                    "ja_prozent": ja_prozent,
                    "nein_prozent": nein_prozent,
                })

            vote_list = sorted(votes.values(), key=lambda v: v["date"], reverse=True)[:limit]

            return self.ok({
                "votes": vote_list,
                "total_votes_available": len(votes),
            })
        except Exception as e:
            return self.err(e)
