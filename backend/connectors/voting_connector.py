"""
Zürich Voting Connector
- Raw data from Stadt Zürich Open Data Portal
"""

import requests
import csv
import io
from datetime import datetime

VOTING_CSV_URL = "https://ckan-prod.zurich.datopian.com/dataset/politik_abstimmungen_seit1933/resource/65e011cf-6479-4fea-aa12-5928924ac4d2/download/abstimmungen_seit1933.csv"


def get_voting_results(date_filter=None, level=None, kreis=None, limit=5):
    """Get voting results from Stadt Zürich Open Data Portal.
    
    Args:
        date_filter: Filter by date (format: YYYY-MM-DD or partial like YYYY-MM)
        level: Filter by political level ("Eidgenossenschaft", "Kanton Zürich", "Stadt Zürich")
        kreis: Filter by district number (1-12)
        limit: Max number of results to return
    """
    try:
        resp = requests.get(VOTING_CSV_URL, timeout=30, headers={"User-Agent": "ZuriBot/1.0"})
        resp.raise_for_status()
        text = resp.content.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
        
        if not rows:
            return {"success": False, "data": None, "source": {"name": "Statistik Stadt Zürich", "type": "official"}, "error": "No voting data available"}
        
        # Apply filters
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
        
        # If no filters, get the latest date
        if not date_filter and not level and not kreis:
            dates = sorted(set(r.get("Abstimmungs_Datum", "") for r in filtered), reverse=True)
            if dates:
                latest_date = dates[0]
                filtered = [r for r in filtered if r.get("Abstimmungs_Datum", "") == latest_date]
        
        # Group results by vote
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
            
            result = {
                "gebiet": row.get("Name_Resultat_Gebiet", ""),
                "nr_wahlkreis": row.get("Nr_Wahlkreis_StZH", "").strip(),
                "wahlkreis": row.get("Name_Wahlkreis_StZH", ""),
                "stimmberechtigt": stimmberechtigt,
                "ja_absolut": ja_abs,
                "nein_absolut": nein_abs,
                "beteiligung_pct": beteiligung,
                "ja_prozent": ja_prozent,
                "nein_prozent": nein_prozent,
            }
            votes[vote_key]["results"].append(result)
        
        # Convert to list and limit
        vote_list = sorted(votes.values(), key=lambda v: v["date"], reverse=True)[:limit]
        
        return {
            "success": True,
            "data": {
                "votes": vote_list,
                "total_votes_available": len(votes),
            },
            "source": {"name": "Statistik Stadt Zürich", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "Statistik Stadt Zürich", "type": "official"}, "error": str(e)}