"""
Zürich Venues Connector
- Raw data from zuerich.com Open Data API
- Covers: restaurants, bars, cafes, hotels, attractions, museums, parks, viewpoints, activities, tours, shopping
"""

import requests
import re
from html import unescape

ZUERICH_API = "https://www.zuerich.com/api/v2/data"

# Category IDs from zuerich.com
CATEGORIES = {
    # Gastronomy
    "gastronomy": "166",
    "american": "193",
    "asian": "194",
    "swiss": "195",
    "italian": "196",
    "french": "197",
    "mediterranean": "198",
    "steakhouse": "199",
    "seafood": "200",
    "dinner": "201",
    "lunch": "202",
    "bar": "203",
    "cafe": "204",
    "breakfast": "205",
    # Bars & Nightlife
    "bars": "103",
    "nightlife": "162",
    # Accommodation
    "accommodation": "71",
    "hotel": "72",
    "hostel": "73",
    "b&b": "74",
    # Attractions & Culture
    "attractions": "99",
    "museums": "96",
    "art": "136",
    "churches": "137",
    # Nature & Outdoors
    "nature": "159",
    "parks": "160",
    "viewpoints": "161",
    "water": "159",
    # Activities & Tours
    "activities": "95",
    "tours": "97",
    "events": "98",
    # Shopping
    "shopping": "100",
    "fashion": "101",
    "souvenirs": "102",
}

# Map schema.org types to user-friendly names
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
    """Remove HTML tags and decode entities."""
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _parse_opening_hours(hours_list):
    """Parse opening hours into readable format."""
    if not hours_list:
        return ""
    
    day_map = {
        "Mo": "Mon", "Tu": "Tue", "We": "Wed", "Th": "Thu",
        "Fr": "Fri", "Sa": "Sat", "Su": "Sun"
    }
    
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
    """Parse a single venue item from the API."""
    name = item.get("name", {}).get("de") or item.get("name", {}).get("en", "")
    if not name:
        return None
    
    description = item.get("disambiguatingDescription", {}).get("de", "")
    description = _clean_html(description)
    
    full_description = item.get("description", {}).get("de", "")
    full_description = _clean_html(full_description)
    
    opening_hours = _parse_opening_hours(item.get("openingHours", []))
    
    # Get image
    photos = item.get("photo", [])
    image_url = ""
    if photos and isinstance(photos, list):
        image_url = photos[0].get("url", "") if isinstance(photos[0], dict) else ""
    
    # Get categories
    categories = []
    cat_obj = item.get("category", {})
    if isinstance(cat_obj, dict):
        for key, val in cat_obj.items():
            if val and isinstance(val, dict):
                categories.append(key)
    
    # Get venue type
    schema_type = item.get("@type", "")
    custom_type = item.get("@customType", "")
    venue_type = TYPE_MAP.get(schema_type, "venue")
    if custom_type:
        venue_type = custom_type.lower()
    
    # Get address
    address = item.get("address", {})
    address_str = ""
    if isinstance(address, dict):
        street = address.get("streetAddress", "")
        postal = address.get("postalCode", "")
        city = address.get("addressLocality", "")
        address_str = f"{street}, {postal} {city}".strip(", ")
    
    # Get location
    geo = item.get("geo", {})
    lat = geo.get("latitude", 0) if isinstance(geo, dict) else 0
    lon = geo.get("longitude", 0) if isinstance(geo, dict) else 0
    
    # Get price info
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


def get_venues(category="gastronomy", limit=10, name_filter=""):
    """Get venues from zuerich.com Open Data API.

    Args:
        category: Category name or ID (see CATEGORIES dict)
        limit: Max number of results
        name_filter: Optional name substring to filter results (case-insensitive)

    Returns venues of type: restaurants, bars, cafes, hotels, attractions,
    museums, parks, viewpoints, activities, tours, shopping, etc.
    """
    try:
        # Look up category ID
        cat_id = CATEGORIES.get(category.lower(), category)

        params = {"id": cat_id}
        resp = requests.get(ZUERICH_API, params=params, timeout=15,
                           headers={"User-Agent": "ZuriBot/1.0", "Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, list):
            data = [data]

        # When searching by name, scan all results before applying limit
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

        return {
            "success": True,
            "data": {
                "venues": venues[:limit],
                "category": category,
                "total_available": len(data) if isinstance(data, list) else 1,
            },
            "source": {"name": "Zürich Tourismus", "type": "official"},
            "error": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "Zürich Tourismus", "type": "official"}, "error": str(e)}


def get_restaurants(cuisine=None, limit=10):
    """Get restaurants, optionally filtered by cuisine.
    
    Args:
        cuisine: Cuisine type (american, asian, swiss, italian, french, mediterranean, steakhouse, seafood)
        limit: Max number of results
    """
    if cuisine and cuisine.lower() in CATEGORIES:
        return get_venues(category=cuisine.lower(), limit=limit)
    return get_venues(category="gastronomy", limit=limit)


def get_bars(limit=10):
    """Get bars and nightlife venues."""
    return get_venues(category="bars", limit=limit)


def get_hotels(limit=10):
    """Get hotels and accommodation."""
    return get_venues(category="accommodation", limit=limit)


def get_attractions(limit=10):
    """Get attractions and viewpoints."""
    return get_venues(category="attractions", limit=limit)


def get_museums(limit=10):
    """Get museums and art venues."""
    return get_venues(category="museums", limit=limit)


def get_activities(limit=10):
    """Get activities and tours."""
    return get_venues(category="activities", limit=limit)