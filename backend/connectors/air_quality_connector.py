"""
Zürich Air Quality Connector
- Raw data from UGZ Stadt Zürich
"""

import requests
import csv
import io
from datetime import datetime

AIR_QUALITY_LIMITS = {
    "NO2": 80, "PM10": 50, "PM2.5": 25, "O3": 120, "O3_max_h1": 120,
    "SO2": 100, "CO": 8,
}

STATION_NAMES = {
    "Zch_Stampfenbachstrasse": "Stampfenbachstrasse (Kreis 6)",
    "Zch_Schimmelstrasse": "Schimmelstrasse (Kreis 2)",
    "Zch_Rosengartenstrasse": "Rosengartenstrasse (Kreis 10)",
    "Zch_Heubeeribüel": "Heubeeribüel (Kreis 11)",
}

KEY_POLLUTANTS = ["PM10", "PM2.5", "NO2", "O3", "O3_max_h1", "CO", "SO2"]

CSV_URL = "https://ckan-prod.zurich.datopian.com/dataset/ugz_luftschadstoffmessung_tageswerte/resource/75fbb34e-2dd1-4a4b-b992-53127c6820dd/download/ugz_ogd_air_d1_{}.csv"


def get_air_quality():
    """Daily air quality from UGZ Stadt Zürich."""
    try:
        year = datetime.now().year
        url = CSV_URL.format(year)
        resp = requests.get(url, timeout=30, headers={"User-Agent": "ZuriBot/1.0"})
        resp.raise_for_status()
        text = resp.content.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
        
        if not rows:
            return {"success": False, "data": None, "source": {"name": "UGZ Stadt Zürich", "type": "official"}, "error": "No air quality data available"}
        
        # Find latest date
        dates = set(r.get("Datum", "")[:10] for r in rows)
        latest_date = sorted(dates)[-1]
        latest_rows = [r for r in rows if r.get("Datum", "").startswith(latest_date)]
        
        # Organize by station
        stations = {}
        for row in latest_rows:
            sid = row.get("Standort", "unknown")
            param = row.get("Parameter", "")
            if sid not in stations:
                stations[sid] = []
            try:
                val = float(row.get("Wert", ""))
            except (ValueError, TypeError):
                val = None
            stations[sid].append({
                "parameter": param,
                "value": val,
                "unit": row.get("Einheit", ""),
                "status": row.get("Status", ""),
            })
        
        # Build output
        station_data = []
        for sid, measurements in sorted(stations.items()):
            pollutants = {}
            for m in measurements:
                if m["parameter"] in KEY_POLLUTANTS and m["value"] is not None:
                    pollutants[m["parameter"]] = {
                        "value": m["value"],
                        "unit": m["unit"],
                        "limit": AIR_QUALITY_LIMITS.get(m["parameter"]),
                    }
            
            station_data.append({
                "name": STATION_NAMES.get(sid, sid),
                "id": sid,
                "measurements": measurements,
                "key_pollutants": pollutants,
            })
        
        try:
            date_display = datetime.strptime(latest_date, "%Y-%m-%d").strftime("%d.%m.%Y")
        except:
            date_display = latest_date
        
        return {
            "success": True,
            "data": {
                "date": date_display,
                "stations": station_data,
            },
            "source": {"name": "UGZ Stadt Zürich", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "UGZ Stadt Zürich", "type": "official"}, "error": str(e)}