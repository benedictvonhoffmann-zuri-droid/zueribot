"""Venues connector — zuerich.com Open Data API."""

import re
from html import unescape

import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

ZUERICH_API = "https://www.zuerich.com/api/v2/data"

CATEGORIES = {
    # Gastronomy umbrella + sub-cuisines (zuerich.com IDs 166 + 193–205)
    "gastronomy": "166",
    "american": "193", "asian": "194", "swiss": "195", "italian": "196",
    "french": "197", "mediterranean": "198", "steakhouse": "199", "seafood": "200",
    "dinner": "201", "lunch": "202", "cafe": "204", "breakfast": "205",
    # "bar" is the gastronomy sub-category; "bars" is the top-level nightlife list (different IDs)
    "bar": "203",
    "bars": "103",
    "nightlife": "162",
    # Accommodation
    "accommodation": "71", "hotel": "72", "hostel": "73", "b&b": "74",
    # Attractions + culture
    "attractions": "99", "museums": "96", "art": "136", "churches": "137",
    # Nature (zuerich.com has no separate water category — 159 covers both)
    "nature": "159", "water": "159",
    "parks": "160", "viewpoints": "161",
    # Activities
    "activities": "95", "tours": "97", "events": "98",
    # Shopping
    "shopping": "100", "fashion": "101", "souvenirs": "102",
}

TYPE_MAP = {
    "Restaurant": "restaurant",
    "BarOrPub": "bar",
    "CafeOrCoffeeShop": "cafe",
    "Hotel": "hotel",
    "Hostel": "hostel",
    "BedAndBreakfast": "b&b",
    "Museum": "museum",
    "CivicStructure": "attraction",
    "LocalBusiness": "venue",
    "Place": "place",
    "TouristAttraction": "attraction",
    "LandmarksOrHistoricalBuildings": "landmark",
}


def _clean_html(text):
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _parse_opening_hours(hours_list):
    if not hours_list:
        return ""
    day_map = {"Mo": "Mon", "Tu": "Tue", "We": "Wed", "Th": "Thu", "Fr": "Fri", "Sa": "Sat", "Su": "Sun"}
    formatted = []
    for h in hours_list:
        match = re.match(r'([A-Za-z,]+)\s+(\d{2}:\d{2}):\d{2}-(\d{2}:\d{2}):\d{2}', h)
        if match:
            days = match.group(1)
            open_time = match.group(2)
            close_time = match.group(3)
            for de, en in day_map.items():
                days = days.replace(de, en)
            formatted.append(f"{days} {open_time}-{close_time}")
    return "; ".join(formatted)


def _parse_venue(item):
    name = item.get("name", {}).get("de") or item.get("name", {}).get("en", "")
    if not name:
        return None

    description = _clean_html(item.get("disambiguatingDescription", {}).get("de", ""))
    full_description = _clean_html(item.get("description", {}).get("de", ""))
    opening_hours = _parse_opening_hours(item.get("openingHours", []))

    photos = item.get("photo", [])
    image_url = ""
    if photos and isinstance(photos, list):
        image_url = photos[0].get("url", "") if isinstance(photos[0], dict) else ""

    categories = []
    cat_obj = item.get("category", {})
    if isinstance(cat_obj, dict):
        for key, val in cat_obj.items():
            if val and isinstance(val, dict):
                categories.append(key)

    schema_type = item.get("@type", "")
    custom_type = item.get("@customType", "")
    venue_type = TYPE_MAP.get(schema_type, "venue")
    if custom_type:
        venue_type = custom_type.lower()

    address = item.get("address", {})
    address_str = ""
    if isinstance(address, dict):
        street = address.get("streetAddress", "")
        postal = address.get("postalCode", "")
        city = address.get("addressLocality", "")
        address_str = f"{street}, {postal} {city}".strip(", ")

    geo = item.get("geo", {})
    lat = geo.get("latitude", 0) if isinstance(geo, dict) else 0
    lon = geo.get("longitude", 0) if isinstance(geo, dict) else 0

    price_range = item.get("priceRange", "")
    price = item.get("price", {}).get("de", "") if isinstance(item.get("price"), dict) else ""

    return {
        "id": item.get("identifier", ""),
        "name": name,
        "type": venue_type,
        "schema_type": schema_type,
        "description": description,
        "full_description": full_description[:500] if full_description else "",
        "opening_hours": opening_hours,
        "image_url": image_url,
        "categories": categories,
        "url": item.get("url", ""),
        "address": address_str,
        "lat": float(lat) if lat else None,
        "lon": float(lon) if lon else None,
        "price_range": price_range,
        "price": price,
        "zurich_card": item.get("zurichCard", False),
    }


class VenuesConnector(BaseConnector):
    manifest = manifest

    def get_venues(self, category: str = "gastronomy", name_filter: str = "", limit: int = 10) -> dict:
        try:
            cat_id = CATEGORIES.get(category.lower(), category)
            params = {"id": cat_id}
            resp = requests.get(
                ZUERICH_API,
                params=params,
                timeout=self.manifest.runtime.timeout_s,
                headers={"User-Agent": "ZuriBot/1.0", "Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

            if not isinstance(data, list):
                data = [data]

            scan_all = bool(name_filter)
            name_lower = name_filter.lower()

            venues = []
            for item in data if scan_all else data[:limit]:
                venue = _parse_venue(item)
                if not venue:
                    continue
                if name_filter and name_lower not in venue["name"].lower():
                    continue
                venues.append(venue)
                if not scan_all and len(venues) >= limit:
                    break

            return self.ok({
                "venues": venues[:limit],
                "category": category,
                "total_available": len(data) if isinstance(data, list) else 1,
            })
        except Exception as e:
            return self.err(e)
