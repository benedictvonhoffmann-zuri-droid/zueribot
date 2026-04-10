"""
Zürich Water & Badi Connector
- Lake temperatures from tecdottir (WAPO)
- Badi status from Stadt Zürich
"""

import requests
import xml.etree.ElementTree as ET

STATIONS = ["tiefenbrunnen", "mythenquai"]

FREIBAEDER = [
    "Letten", "Oberer Letten", "Unterer Letten",
    "Mythenquai", "Tiefenbrunnen", "Enge",
    "Utoquai", "Wollishofen", "Allenmoos",
    "Heuried", "Letzigraben", "Seebach",
    "Schanzengraben", "Frauenbad", "Männerbad",
    "Au-Höngg",
]


def get_water_temperature():
    """Lake water temperatures from WAPO stations."""
    stations = []
    for station_key in STATIONS:
        try:
            resp = requests.get(
                f"https://tecdottir.metaodi.ch/measurements/{station_key}",
                params={"sort": "timestamp_cet desc", "limit": 1},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("ok") or not data.get("result"):
                stations.append({"name": station_key, "error": "No data"})
                continue
            
            vals = data["result"][0].get("values", {})
            stations.append({
                "name": "Tiefenbrunnen" if station_key == "tiefenbrunnen" else "Mythenquai",
                "timestamp": vals.get("timestamp_cet", {}).get("value"),
                "water_temp_c": vals.get("water_temperature", {}).get("value"),
                "air_temp_c": vals.get("air_temperature", {}).get("value"),
                "wind_speed_ms": vals.get("wind_speed_avg_10min", {}).get("value"),
                "wind_direction_deg": vals.get("wind_direction", {}).get("value"),
                "humidity_pct": vals.get("humidity", {}).get("value"),
                "pressure_hpa": vals.get("barometric_pressure_qfe", {}).get("value"),
                "precipitation_mm": vals.get("precipitation", {}).get("value"),
                "water_level_m": vals.get("water_level", {}).get("value"),
            })
        except Exception as e:
            stations.append({"name": station_key, "error": str(e)})
    
    return {
        "success": True,
        "data": {"stations": stations},
        "source": {"name": "Wasserschutzpolizei Zürich via tecdottir", "type": "official"},
        "error": None,
    }


def get_badi_info(badi_name=None):
    """Badi status from Stadt Zürich. Returns seasonal note for Freibäder when out of season."""
    try:
        resp = requests.get("https://www.stadt-zuerich.ch/stzh/bathdatadownload",
                            timeout=10, headers={"User-Agent": "ZuriBot/1.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        
        all_badis = []
        all_names = []
        for bath in root.findall('.//bath'):
            title = bath.findtext("title", "")
            all_names.append(title)
            all_badis.append({
                "name": title,
                "water_temp": bath.findtext("temperatureWater", ""),
                "status": bath.findtext("openClosedTextPlain", "").strip(),
                "opening_hours": bath.findtext("openingHoursText", ""),
                "modified": bath.findtext("dateModified", "").strip(),
                "url": bath.findtext("urlPage", ""),
            })
        
        if badi_name:
            q = badi_name.lower().strip()
            # Check if it's a known Freibad (seasonal, not in data during winter)
            for freibad in FREIBAEDER:
                if q in freibad.lower() or freibad.lower() in q:
                    # Check if it's in the current data
                    matches = [b for b in all_badis if freibad.lower() in b["name"].lower()]
                    if matches:
                        return {
                            "success": True,
                            "data": matches,
                            "source": {"name": "Sport + Badeanlagen Stadt Zürich", "type": "official"},
                            "error": None,
                        }
                    else:
                        # Freibad not in data = closed for season
                        return {
                            "success": True,
                            "data": [{
                                "name": freibad,
                                "water_temp": "",
                                "status": "Closed (seasonal — Freibäder are open May–September)",
                                "opening_hours": "Seasonal: typically May–September",
                                "modified": "",
                                "url": "",
                            }],
                            "source": {"name": "Sport + Badeanlagen Stadt Zürich", "type": "official"},
                            "error": None,
                        }
            
            # Not a known Freibad, search in current data
            matches = [b for b in all_badis if q in b["name"].lower()]
            if matches:
                return {
                    "success": True,
                    "data": matches,
                    "source": {"name": "Sport + Badeanlagen Stadt Zürich", "type": "official"},
                    "error": None,
                }
            
            return {
                "success": False,
                "data": {
                    "current_badis": all_names,
                    "seasonal_badis": FREIBAEDER,
                    "note": "Freibäder (outdoor pools) are seasonal (May–September). Currently only Hallenbäder (indoor pools) are available.",
                },
                "source": {"name": "Sport + Badeanlagen Stadt Zürich", "type": "official"},
                "error": f"No badi found for '{badi_name}'"
            }
        
        return {
            "success": True,
            "data": all_badis,
            "source": {"name": "Sport + Badeanlagen Stadt Zürich", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "Sport + Badeanlagen Stadt Zürich", "type": "official"}, "error": str(e)}