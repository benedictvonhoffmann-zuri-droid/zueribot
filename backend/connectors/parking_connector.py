"""
Zürich Parking Connector
- Raw data from ParkenDD
"""

import requests


def get_parking(name_filter=None):
    """Real-time parking availability in Zürich."""
    try:
        resp = requests.get("https://api.parkendd.de/Zuerich", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        lots = data.get("lots", [])
        
        if name_filter:
            nf = name_filter.lower()
            lots = [l for l in lots if nf in l.get("name", "").lower() or nf in l.get("address", "").lower()]
        
        if not lots:
            return {
                "success": False,
                "data": None,
                "source": {"name": "Stadt Züri Tiefbauamt", "type": "official"},
                "error": f"No parking found{' for ' + name_filter if name_filter else ''}"
            }
        
        parking_lots = []
        for lot in lots:
            free = lot.get("free")
            total = lot.get("total")
            state = lot.get("state", "unknown")
            
            occupancy_pct = None
            if isinstance(free, int) and isinstance(total, int) and total > 0 and state == "open":
                occupancy_pct = round((1 - free / total) * 100)
            
            parking_lots.append({
                "name": lot.get("name", ""),
                "address": lot.get("address", ""),
                "lot_type": lot.get("lot_type", ""),
                "state": state,
                "free": free,
                "total": total,
                "occupancy_pct": occupancy_pct,
                "coords": lot.get("coords"),
            })
        
        return {
            "success": True,
            "data": {
                "lots": parking_lots,
                "last_updated": data.get("last_updated", ""),
            },
            "source": {"name": "Stadt Züri Tiefbauamt", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "Stadt Züri Tiefbauamt", "type": "official"}, "error": str(e)}