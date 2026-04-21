"""POI connector — OpenStreetMap Overpass search for Zürich."""

import math
import re
import time

import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

OSM_TAG_MAP = {
    "supermarket": ("shop", "supermarket"),
    "migros": ("name", "Migros"),
    "coop": ("name", "Coop"),
    "aldi": ("name", "Aldi"),
    "lidl": ("name", "Lidl"),
    "denner": ("name", "Denner"),
    "pharmacy": ("amenity", "pharmacy"),
    "apotheke": ("amenity", "pharmacy"),
    "bakery": ("shop", "bakery"),
    "butcher": ("shop", "butcher"),
    "restaurant": ("amenity", "restaurant"),
    "cafe": ("amenity", "cafe"),
    "bar": ("amenity", "bar"),
    "hospital": ("amenity", "hospital"),
    "spital": ("amenity", "hospital"),
    "doctor": ("amenity", "doctors"),
    "dentist": ("healthcare", "dentist"),
    "bank": ("amenity", "bank"),
    "atm": ("amenity", "atm"),
    "post office": ("amenity", "post_office"),
    "fuel": ("amenity", "fuel"),
    "parking": ("amenity", "parking"),
    "school": ("amenity", "school"),
    "library": ("amenity", "library"),
    "cinema": ("amenity", "cinema"),
    "theatre": ("amenity", "theatre"),
    "museum": ("tourism", "museum"),
    "hotel": ("tourism", "hotel"),
    "playground": ("leisure", "playground"),
    "park": ("leisure", "park"),
    "fitness": ("leisure", "fitness_centre"),
    "gym": ("leisure", "fitness_centre"),
    "police": ("amenity", "police"),
    "toilets": ("amenity", "toilets"),
    "hairdresser": ("shop", "hairdresser"),
}

OVERPASS_URL = "https://overpass.osm.ch/api/interpreter"
ZURICH_CENTER = (47.3769, 8.5417)


def haversine_m(lat1, lon1, lat2, lon2):
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class POIConnector(BaseConnector):
    manifest = manifest

    _last_call_time: float = 0

    def _overpass_query(self, query_str: str, timeout: int = 25):
        elapsed = time.time() - self._last_call_time
        if elapsed < 2:
            time.sleep(2 - elapsed)
        for attempt in range(3):
            try:
                resp = requests.post(OVERPASS_URL, data={"data": query_str}, timeout=timeout)
                self._last_call_time = time.time()
                if resp.status_code == 200:
                    return resp.json().get("elements", [])
                elif resp.status_code == 429:
                    time.sleep(5 * (attempt + 1))
                else:
                    return []
            except Exception:
                time.sleep(3)
        return []

    def _resolve_location(self, query: str, lat=None, lon=None):
        if lat and lon:
            return query, lat, lon

        kreis_match = re.search(r'kreis\s*(\d{1,2})', query, re.IGNORECASE)
        if kreis_match:
            try:
                time.sleep(0.5)
                resp = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": f"Kreis {kreis_match.group(1)}, Zürich", "format": "json", "limit": 1},
                    headers={"User-Agent": "ZuriBot/1.0"},
                    timeout=5,
                )
                if resp.status_code == 200 and resp.json():
                    lat = float(resp.json()[0]["lat"])
                    lon = float(resp.json()[0]["lon"])
                    poi_query = re.sub(r'(?i)\s*kreis\s*\d{1,2}\s*', ' ', query).strip()
                    return poi_query, lat, lon
            except Exception:
                pass

        loc_match = re.search(r'(?:nähe|naehe|near|bei|beim|in)\s+(.+?)(?:\s+(?:supermarket|pharmacy|restaurant|cafe|bar|bakery|hospital|doctor|dentist|bank|atm|post|fuel|parking|school|library|cinema|theatre|museum|hotel|playground|park|fitness|gym|police|toilets|hairdresser|apotheke|spital))', query, re.IGNORECASE)
        if not loc_match:
            loc_match = re.search(r'(?:nähe|naehe|near|bei|beim|in)\s+(.+)', query, re.IGNORECASE)

        if loc_match:
            try:
                time.sleep(0.5)
                resp = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": f"{loc_match.group(1)}, Zürich", "format": "json", "limit": 1},
                    headers={"User-Agent": "ZuriBot/1.0"},
                    timeout=5,
                )
                if resp.status_code == 200 and resp.json():
                    lat = float(resp.json()[0]["lat"])
                    lon = float(resp.json()[0]["lon"])
                    poi_query = re.sub(r'(?i)\s*(?:nähe|naehe|near|bei|beim|in)\s+.+', '', query).strip()
                    return poi_query, lat, lon
            except Exception:
                pass

        return query, ZURICH_CENTER[0], ZURICH_CENTER[1]

    def get_pois(
        self,
        category: str = "restaurant",
        query: str = "",
        user_address: str = "",
        user_latitude: float | None = None,
        user_longitude: float | None = None,
        radius_m: int = 1500,
        limit: int = 5,
    ) -> dict:
        # Default POI search string: prefer query, fall back to category
        poi_query = query or category or "restaurant"

        lat = user_latitude
        lon = user_longitude

        # Geocode user_address → lat/lon if coordinates not provided directly
        if user_address and not (lat and lon):
            try:
                # geo.admin.ch — official Swiss federal address index, knows every Swiss street
                r = requests.get(
                    "https://api3.geo.admin.ch/rest/services/api/SearchServer",
                    params={"type": "locations", "searchText": user_address, "limit": 1},
                    timeout=5,
                )
                hits = r.json().get("results", []) if r.status_code == 200 else []
                if hits:
                    lat = hits[0]["attrs"]["lat"]
                    lon = hits[0]["attrs"]["lon"]
            except Exception:
                pass

        try:
            poi_q, search_lat, search_lon = self._resolve_location(poi_query, lat, lon)

            osm_tag = None
            q_lower = poi_query.lower()
            for term, tag in OSM_TAG_MAP.items():
                if term in q_lower:
                    osm_tag = tag
                    break

            if osm_tag:
                tk, tv = osm_tag
                if tk == "name":
                    tag_filter = f'["name"~"{tv}",i]'
                else:
                    tag_filter = f'["{tk}"="{tv}"]'
                overpass_q = f'[out:json][timeout:25];(node{tag_filter}(around:{radius_m},{search_lat},{search_lon});way{tag_filter}(around:{radius_m},{search_lat},{search_lon}););out body center {limit};'
            else:
                safe_name = re.sub(r'["\\\n\r]', '', poi_q)
                tag_filter = f'["name"~"{safe_name}",i]'
                overpass_q = f'[out:json][timeout:25];(node{tag_filter}(around:{radius_m},{search_lat},{search_lon});way{tag_filter}(around:{radius_m},{search_lat},{search_lon});relation{tag_filter}(around:{radius_m},{search_lat},{search_lon}););out body center {limit};'

            elements = self._overpass_query(overpass_q)

            results = []
            for elem in elements:
                tags = elem.get("tags", {})
                e_lat = elem.get("lat") or (elem.get("center") or {}).get("lat")
                e_lon = elem.get("lon") or (elem.get("center") or {}).get("lon")

                if not e_lat or not e_lon:
                    continue

                dist = int(haversine_m(search_lat, search_lon, float(e_lat), float(e_lon)))

                results.append({
                    "name": tags.get("name", "Unknown"),
                    "distance_m": dist,
                    "address": f"{tags.get('addr:street', '')} {tags.get('addr:housenumber', '')}".strip(),
                    "plz": tags.get("addr:postcode", ""),
                    "city": tags.get("addr:city", ""),
                    "phone": tags.get("phone", tags.get("contact:phone", "")),
                    "website": tags.get("website", tags.get("contact:website", "")),
                    "opening_hours": tags.get("opening_hours", ""),
                    "cuisine": tags.get("cuisine", ""),
                    "wheelchair": tags.get("wheelchair", ""),
                    "brand": tags.get("brand", ""),
                    "lat": float(e_lat),
                    "lon": float(e_lon),
                })

            results.sort(key=lambda x: x["distance_m"])

            if not results:
                return self.err(f"No results found for '{poi_query}' within {radius_m}m")

            return self.ok({
                "query": poi_query,
                "results": results[:limit],
                "radius_m": radius_m,
                "center": {"lat": search_lat, "lon": search_lon},
            })
        except Exception as e:
            return self.err(e)
