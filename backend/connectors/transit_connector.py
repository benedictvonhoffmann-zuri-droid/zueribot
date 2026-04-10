"""
Zürich Transit Connector
- Raw data from transport.opendata.ch (SBB)
"""

import requests
import re


def get_departures(stop_name="Zürich HB", limit=8):
    """Next departures from a transport stop."""
    try:
        resp = requests.get("https://transport.opendata.ch/v1/stationboard",
                            params={"station": stop_name, "limit": limit}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        station = data.get("station", {})
        stationboard = data.get("stationboard", [])
        
        if not stationboard:
            return {
                "success": False,
                "data": None,
                "source": {"name": "SBB / ÖV Schwiiz", "type": "official"},
                "error": f"No departures found for '{stop_name}'"
            }
        
        departures = []
        for entry in stationboard:
            stop = entry.get("stop", {})
            departures.append({
                "line": f"{entry.get('category', '')}{entry.get('number', '')}",
                "to": entry.get("to", ""),
                "departure": stop.get("departure", ""),
                "departure_platform": stop.get("platform", ""),
                "delay_min": stop.get("delay", 0) or 0,
            })
        
        return {
            "success": True,
            "data": {
                "station": station.get("name", stop_name),
                "departures": departures,
            },
            "source": {"name": "SBB / ÖV Schwiiz", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "SBB / ÖV Schwiiz", "type": "official"}, "error": str(e)}


def get_connections(origin, destination, limit=4, via=None):
    """Public transport connections from A to B."""
    try:
        params = {"from": origin, "to": destination, "limit": min(limit, 6)}
        if via:
            params["via[]"] = via
        resp = requests.get("https://transport.opendata.ch/v1/connections", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        connections = data.get("connections", [])
        if not connections:
            return {
                "success": False,
                "data": None,
                "source": {"name": "SBB / ÖV Schwiiz", "type": "official"},
                "error": f"No connections found from '{origin}' to '{destination}'"
            }
        
        result = []
        for conn in connections:
            dep = conn.get("from", {})
            arr = conn.get("to", {})
            
            # Parse duration "00d00:23:00" -> "23min"
            duration_raw = conn.get("duration", "")
            dur_match = re.match(r'(\d+)d(\d+):(\d+):(\d+)', duration_raw) if duration_raw else None
            if dur_match:
                d, h, m = int(dur_match.group(1)), int(dur_match.group(2)), int(dur_match.group(3))
                if d > 0:
                    duration = f"{d}d {h}h {m}min"
                elif h > 0:
                    duration = f"{h}h {m}min"
                else:
                    duration = f"{m}min"
            else:
                duration = duration_raw
            
            # Extract sections
            sections = []
            for sec in conn.get("sections", []):
                journey = sec.get("journey")
                walk = sec.get("walk")
                sec_dep = sec.get("departure", {})
                sec_arr = sec.get("arrival", {})
                
                if journey:
                    sections.append({
                        "type": "transit",
                        "line": f"{journey.get('category', '')}{journey.get('number', '')}",
                        "to": journey.get("to", ""),
                        "departure_station": sec_dep.get("station", {}).get("name", ""),
                        "departure_time": sec_dep.get("departure", ""),
                        "arrival_station": sec_arr.get("station", {}).get("name", ""),
                        "arrival_time": sec_arr.get("arrival", ""),
                    })
                elif walk:
                    sections.append({
                        "type": "walk",
                        "from": sec_dep.get("station", {}).get("name", ""),
                        "to": sec_arr.get("station", {}).get("name", ""),
                        "duration_min": walk.get("duration", 0) // 60 if isinstance(walk.get("duration", 0), int) else walk.get("duration", 0),
                    })
            
            result.append({
                "departure_time": dep.get("departure", ""),
                "departure_platform": dep.get("platform", ""),
                "departure_delay_min": dep.get("delay", 0) or 0,
                "arrival_time": arr.get("arrival", ""),
                "arrival_platform": arr.get("platform", ""),
                "duration": duration,
                "transfers": conn.get("transfers", 0),
                "sections": sections,
            })
        
        return {
            "success": True,
            "data": {
                "from": data.get("from", {}).get("name", origin),
                "to": data.get("to", {}).get("name", destination),
                "connections": result,
            },
            "source": {"name": "SBB / ÖV Schwiiz", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "SBB / ÖV Schwiiz", "type": "official"}, "error": str(e)}