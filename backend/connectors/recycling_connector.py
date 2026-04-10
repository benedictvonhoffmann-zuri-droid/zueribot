"""
Zürich Recycling & Waste Connector
- Garbage collection schedule (Kehricht)
- Bio waste schedule (Bioabfall)
- Paper waste schedule (Papier)
- Cardboard schedule (Karton)
- Collection points (Sammelstellen) - glass, metal, oil, textiles
- Mobile recycling centers (Mobiler Recyclinghof)
- Recycling centers (Recyclinghof) - permanent locations
"""

import requests
import csv
import io
from datetime import datetime, timedelta

BASE_URL = "https://data.stadt-zuerich.ch/dataset"

CSV_URLS = {
    "kehricht": f"{BASE_URL}/entsorgungskalender_kehricht/download/entsorgungskalender_kehricht_2026.csv",
    "bioabfall": f"{BASE_URL}/entsorgungskalender_bioabfall/download/entsorgungskalender_bioabfall_2026.csv",
    "papier": f"{BASE_URL}/entsorgungskalender_papier/download/papier_2026.csv",
    "karton": f"{BASE_URL}/entsorgungskalender_karton/download/karton_2026.csv",
    "sammelstellen": f"{BASE_URL}/entsorgungskalender_sammelstellen/download/entsorgungskalender_sammelstellen_2026.csv",
    "mobiler_recyclinghof": f"{BASE_URL}/entsorgungskalender_mobiler_recyclinghof/download/mobiler_recyclinghof_2026.csv",
}


def _fetch_csv(url):
    """Fetch and parse a CSV from the given URL."""
    resp = requests.get(url, timeout=15, headers={"User-Agent": "ZuriBot/1.0"})
    resp.raise_for_status()
    text = resp.content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _format_date(date_str):
    """Format ISO date to readable German format."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%d.%m.%Y")
    except:
        return date_str


def get_waste_schedule(zip_code=None, waste_type="kehricht", upcoming_days=30):
    """Get waste collection schedule.
    
    Args:
        zip_code: Filter by PLZ (e.g., 8001, 8002)
        waste_type: Type of waste (kehricht, bioabfall, papier, karton)
        upcoming_days: Number of days to look ahead
    """
    try:
        if waste_type not in CSV_URLS:
            return {"success": False, "data": None, "source": {"name": "Statistik Stadt Zürich", "type": "official"}, "error": f"Unknown waste type: {waste_type}"}
        
        rows = _fetch_csv(CSV_URLS[waste_type])
        
        if not rows:
            return {"success": False, "data": None, "source": {"name": "Statistik Stadt Zürich", "type": "official"}, "error": "No data available"}
        
        # Filter by zip code
        if zip_code:
            zip_str = str(zip_code)
            rows = [r for r in rows if str(r.get("PLZ", "")).startswith(zip_str)]
        
        # Filter upcoming dates
        today = datetime.now().date()
        end_date = today + timedelta(days=upcoming_days)
        
        schedule = []
        for row in rows:
            date_str = row.get("Abholdatum", "")
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                continue
            
            if date < today:
                continue
            if date > end_date:
                continue
            
            entry = {
                "date": date_str,
                "date_formatted": _format_date(date_str),
                "zip_code": row.get("PLZ", ""),
            }
            
            # Add station if available
            if "Station" in row:
                entry["station"] = row.get("Station", "")
            
            schedule.append(entry)
        
        # Sort by date
        schedule.sort(key=lambda x: x["date"])
        
        # Remove duplicates
        seen = set()
        unique = []
        for s in schedule:
            key = (s["date"], s.get("zip_code", ""))
            if key not in seen:
                seen.add(key)
                unique.append(s)
        
        waste_names = {
            "kehricht": "Garbage (Kehricht)",
            "bioabfall": "Bio Waste (Bioabfall)",
            "papier": "Paper (Papier)",
            "karton": "Cardboard (Karton)",
        }
        
        return {
            "success": True,
            "data": {
                "waste_type": waste_type,
                "waste_name": waste_names.get(waste_type, waste_type),
                "schedule": unique[:30],
                "total_upcoming": len(unique),
            },
            "source": {"name": "ERZ Entsorgung + Recycling Zürich", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "ERZ Entsorgung + Recycling Zürich", "type": "official"}, "error": str(e)}


def get_collection_points(zip_code=None, material=None):
    """Get collection points for recyclables (glass, metal, oil, textiles).
    
    Args:
        zip_code: Filter by PLZ
        material: Filter by material (glas, metall, oel, textilien)
    """
    try:
        rows = _fetch_csv(CSV_URLS["sammelstellen"])
        
        if not rows:
            return {"success": False, "data": None, "source": {"name": "ERZ Entsorgung + Recycling Zürich", "type": "official"}, "error": "No data available"}
        
        points = []
        for row in rows:
            # Filter by zip code
            if zip_code:
                zip_str = str(zip_code)
                if not str(row.get("PLZ", "")).startswith(zip_str):
                    continue
            
            # Filter by material
            if material:
                mat_key = material.lower()
                if mat_key in ["glass", "glas"]:
                    if row.get("Glas", "").lower() != "x":
                        continue
                elif mat_key in ["metal", "metall"]:
                    if row.get("Metall", "").lower() != "x":
                        continue
                elif mat_key in ["oil", "oel", "öl"]:
                    if row.get("Oel", "").lower() != "x":
                        continue
                elif mat_key in ["textiles", "textilien", "clothes"]:
                    if row.get("Textilien", "").lower() != "x":
                        continue
            
            point = {
                "zip_code": row.get("PLZ", ""),
                "station": row.get("Station", ""),
                "materials": [],
            }
            
            if row.get("Glas", "").lower() == "x":
                point["materials"].append("Glas")
            if row.get("Metall", "").lower() == "x":
                point["materials"].append("Metall")
            if row.get("Oel", "").lower() == "x":
                point["materials"].append("Öl")
            if row.get("Textilien", "").lower() == "x":
                point["materials"].append("Textilien")
            
            points.append(point)
        
        return {
            "success": True,
            "data": {
                "collection_points": points,
                "total": len(points),
            },
            "source": {"name": "ERZ Entsorgung + Recycling Zürich", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "ERZ Entsorgung + Recycling Zürich", "type": "official"}, "error": str(e)}


def get_mobile_recycling_centers(zip_code=None, upcoming_days=60):
    """Get mobile recycling center schedule.
    
    Args:
        zip_code: Filter by PLZ
        upcoming_days: Number of days to look ahead
    """
    try:
        rows = _fetch_csv(CSV_URLS["mobiler_recyclinghof"])
        
        if not rows:
            return {"success": False, "data": None, "source": {"name": "ERZ Entsorgung + Recycling Zürich", "type": "official"}, "error": "No data available"}
        
        # Filter by zip code
        if zip_code:
            zip_str = str(zip_code)
            rows = [r for r in rows if str(r.get("PLZ", "")).startswith(zip_str)]
        
        # Filter upcoming dates
        today = datetime.now().date()
        end_date = today + timedelta(days=upcoming_days)
        
        centers = []
        for row in rows:
            date_str = row.get("Abholdatum", "")
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                continue
            
            if date < today:
                continue
            if date > end_date:
                continue
            
            centers.append({
                "date": date_str,
                "date_formatted": _format_date(date_str),
                "zip_code": row.get("PLZ", ""),
                "station": row.get("Station", ""),
            })
        
        centers.sort(key=lambda x: x["date"])
        
        return {
            "success": True,
            "data": {
                "mobile_recycling_centers": centers,
                "total_upcoming": len(centers),
            },
            "source": {"name": "ERZ Entsorgung + Recycling Zürich", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "ERZ Entsorgung + Recycling Zürich", "type": "official"}, "error": str(e)}


def get_all_schedules(zip_code=None, upcoming_days=14):
    """Get all waste collection schedules for a zip code.
    
    Args:
        zip_code: Filter by PLZ
        upcoming_days: Number of days to look ahead
    """
    try:
        results = {}
        waste_types = ["kehricht", "bioabfall", "papier", "karton"]
        
        waste_names = {
            "kehricht": "Garbage (Kehricht)",
            "bioabfall": "Bio Waste (Bioabfall)",
            "papier": "Paper (Papier)",
            "karton": "Cardboard (Karton)",
        }
        
        for wt in waste_types:
            result = get_waste_schedule(zip_code=zip_code, waste_type=wt, upcoming_days=upcoming_days)
            if result["success"]:
                results[wt] = {
                    "name": waste_names[wt],
                    "dates": [s["date_formatted"] for s in result["data"]["schedule"][:5]],
                }
            else:
                results[wt] = {"name": waste_names[wt], "dates": [], "error": result.get("error")}
        
        # Also get mobile recycling centers
        mobile = get_mobile_recycling_centers(zip_code=zip_code, upcoming_days=upcoming_days)
        if mobile["success"]:
            results["mobiler_recyclinghof"] = {
                "name": "Mobile Recycling Center",
                "dates": [f"{m['date_formatted']} - {m['station']}" for m in mobile["data"]["mobile_recycling_centers"][:3]],
            }
        
        return {
            "success": True,
            "data": results,
            "source": {"name": "ERZ Entsorgung + Recycling Zürich", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "ERZ Entsorgung + Recycling Zürich", "type": "official"}, "error": str(e)}