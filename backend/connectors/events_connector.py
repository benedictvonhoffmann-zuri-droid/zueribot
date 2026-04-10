"""
Zürich Events Connector
- Raw data from Eventfrog API
"""

import requests
import os
from datetime import datetime

EVENTFROG_API = "https://api.eventfrog.net/public/v1/events"
EVENTFROG_LOCATIONS = "https://api.eventfrog.net/public/v1/locations"
EVENTFROG_KEY = os.environ.get("EVENTFROG_KEY", "51880FF2-6CCF-4B4B-B377-27380B26C290")

ZURICH_ZIPS = [f"800{i}" for i in range(10)] + ["8010", "8020", "8021", "8022", "8023", "8024", "8025", "8026", "8027", "8028", "8032", "8037", "8038", "8041", "8044", "8045", "8046", "8047", "8048", "8049", "8050", "8051", "8052", "8053", "8055", "8057", "8058", "8064"]

RUBRIC_MAP = {
    1: "Single-Party", 2: "Sonstige Veranstaltungen", 3: "Speed-Dating",
    4: "Ausfahrt", 5: "Ausflug", 6: "Brauchtum", 7: "Familie",
    8: "Fest", 9: "Führungen", 10: "Gottesdienst",
    11: "Kurs / Seminar", 12: "Lesung", 13: "Messe / Ausstellung",
    14: "Musik - Klassik", 15: "Musik - Rock/Pop", 16: "Musik - Jazz/Blues/Folk",
    17: "Musik - Schlager/Volksmusik", 18: "Musik - Weltmusik", 19: "Musik - Sonstiges",
    20: "Sport - Anlass", 21: "Sport - Aktiv", 22: "Theater / Tanz",
    23: "Vortrag / Diskussion", 24: "Film", 25: "Party",
    26: "Konzert", 27: "Festival", 28: "Comedy",
    29: "Musical / Show", 30: "Oper", 31: "Kabarett",
    32: "Ausstellung", 33: "Museum", 34: "Workshop",
    35: "Networking", 36: "Kinder", 37: "Senioren",
}


def _get_headers():
    return {"Authorization": f"Bearer {EVENTFROG_KEY}", "Accept": "application/json"}


def _get_zurich_location_ids():
    """Fetch location IDs in Zürich area."""
    try:
        location_ids = set()
        for zip_code in ZURICH_ZIPS[:10]:  # Limit API calls
            resp = requests.get(
                EVENTFROG_LOCATIONS,
                params={"postalCode": zip_code, "limit": 50},
                headers=_get_headers(),
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            for loc in data.get("locations", []):
                if loc.get("city", "").startswith("Zürich") or loc.get("city", "").startswith("Zurich"):
                    location_ids.add(loc.get("id"))
        return location_ids
    except Exception:
        return set()


def get_events(query=None, category=None, limit=10):
    """Get events in Zürich from Eventfrog."""
    try:
        params = {
            "country": "CH",
            "limit": min(limit * 3, 50),  # Fetch more to filter locally
        }
        
        if query:
            params["q"] = query
        
        resp = requests.get(EVENTFROG_API, params=params, headers=_get_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        events = []
        for event in data.get("events", []):
            # Filter for Zürich area
            location_alias = event.get("locationAlias", {}).get("de") or ""
            title = event.get("title", {}).get("de") or ""
            
            # Get location details if available
            loc_ids = event.get("locationIds", [])
            
            begin = event.get("begin", "")
            end = event.get("end", "")
            
            # Format dates
            try:
                begin_fmt = datetime.strptime(begin[:19], "%Y-%m-%dT%H:%M:%S").strftime("%d.%m.%Y %H:%M") if begin else ""
            except:
                begin_fmt = begin
            
            try:
                end_fmt = datetime.strptime(end[:19], "%Y-%m-%dT%H:%M:%S").strftime("%d.%m.%Y %H:%M") if end else ""
            except:
                end_fmt = end
            
            rubric_id = event.get("rubricId")
            category_name = RUBRIC_MAP.get(rubric_id, "Sonstige")
            
            events.append({
                "id": event.get("id", ""),
                "title": title,
                "begin": begin,
                "begin_formatted": begin_fmt,
                "end": end,
                "end_formatted": end_fmt,
                "category": category_name,
                "rubric_id": rubric_id,
                "url": event.get("url", ""),
                "organizer": event.get("organizerName", ""),
                "location_ids": loc_ids,
                "location_alias": location_alias,
                "short_description": event.get("shortDescription", {}).get("de", ""),
                "cancelled": event.get("cancelled", False),
                "sold_out": event.get("soldOut"),
                "image_url": (event.get("emblemToShow") or {}).get("url", ""),
            })
        
        # Filter by category if specified
        if category:
            cat_lower = category.lower()
            events = [e for e in events if cat_lower in e["category"].lower()]
        
        # Filter for upcoming events
        now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        events = [e for e in events if e.get("begin", "") >= now]
        
        events = events[:limit]
        
        return {
            "success": True,
            "data": {
                "events": events,
                "total_available": data.get("totalNumberOfResources", 0),
            },
            "source": {"name": "Eventfrog", "type": "community"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "Eventfrog", "type": "community"}, "error": str(e)}


def get_zurich_events(limit=10):
    """Get events specifically in Zürich by fetching location IDs first."""
    try:
        # First get Zürich location IDs
        zurich_loc_ids = _get_zurich_location_ids()
        
        if not zurich_loc_ids:
            # Fallback to general search
            return get_events(query="Zürich", limit=limit)
        
        # Get events for those locations
        all_events = []
        for loc_id in list(zurich_loc_ids)[:5]:  # Limit API calls
            params = {
                "country": "CH",
                "limit": limit,
                "locationId": loc_id,
            }
            resp = requests.get(EVENTFROG_API, params=params, headers=_get_headers(), timeout=10)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for event in data.get("events", []):
                title = event.get("title", {}).get("de", "")
                begin = event.get("begin", "")
                end = event.get("end", "")
                
                try:
                    begin_fmt = datetime.strptime(begin[:19], "%Y-%m-%dT%H:%M:%S").strftime("%d.%m.%Y %H:%M") if begin else ""
                except:
                    begin_fmt = begin
                
                try:
                    end_fmt = datetime.strptime(end[:19], "%Y-%m-%dT%H:%M:%S").strftime("%d.%m.%Y %H:%M") if end else ""
                except:
                    end_fmt = end
                
                rubric_id = event.get("rubricId")
                
                all_events.append({
                    "id": event.get("id", ""),
                    "title": title,
                    "begin": begin,
                    "begin_formatted": begin_fmt,
                    "end": end,
                    "end_formatted": end_fmt,
                    "category": RUBRIC_MAP.get(rubric_id, "Sonstige"),
                    "rubric_id": rubric_id,
                    "url": event.get("url", ""),
                    "organizer": event.get("organizerName", ""),
                    "location_alias": event.get("locationAlias", {}).get("de", ""),
                    "short_description": event.get("shortDescription", {}).get("de", ""),
                    "cancelled": event.get("cancelled", False),
                    "sold_out": event.get("soldOut"),
                    "image_url": (event.get("emblemToShow") or {}).get("url", ""),
                })
        
        # Sort by date and remove duplicates
        seen = set()
        unique_events = []
        for e in sorted(all_events, key=lambda x: x.get("begin", "")):
            if e["id"] not in seen:
                seen.add(e["id"])
                unique_events.append(e)
        
        return {
            "success": True,
            "data": {
                "events": unique_events[:limit],
                "total_available": len(unique_events),
            },
            "source": {"name": "Eventfrog", "type": "community"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "Eventfrog", "type": "community"}, "error": str(e)}