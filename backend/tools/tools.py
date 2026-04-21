"""
Tool definitions and dispatch logic for ZuriBot.
Maps LLM tool calls to connector functions.
"""

from backend.connectors import registry as connector_registry
from backend.connectors import (
    weather_connector,
    transit_connector,
    parking_connector,
    water_connector,
    air_quality_connector,
    poi_connector,
    voting_connector,
    events_connector,
    venues_connector,
    recycling_connector,
    search_connector,
    knowledge_connector,
    rent_connector,
    pedestrian_connector,
    water_quality_connector,
    crime_connector,
    city_stats_connector,
)

# Tool definitions in OpenAI/Ollama function calling format
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather forecast for Zürich. Returns temperature, conditions, wind, and humidity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location name (default: Zürich)",
                        "default": "Zürich"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_connections",
            "description": "Get public transport connections between two stations in Zürich (tram, bus, train).",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_station": {
                        "type": "string",
                        "description": "Origin station name (e.g. 'Zürich HB', 'Bellevue')"
                    },
                    "to_station": {
                        "type": "string",
                        "description": "Destination station name (e.g. 'Zürich HB', 'Oerlikon')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of connections to return (default: 3)",
                        "default": 3
                    }
                },
                "required": ["from_station", "to_station"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_departures",
            "description": "Get next departures from a Zürich transit station (tram, bus, train).",
            "parameters": {
                "type": "object",
                "properties": {
                    "station": {
                        "type": "string",
                        "description": "Station name (e.g. 'Zürich HB', 'Bahnhofstrasse', 'Bellevue')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of departures to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["station"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_parking",
            "description": "Get current parking availability in Zürich. Shows free spaces, total capacity, and status for each parking garage.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_water_temps",
            "description": "Get current water temperatures for swimming spots in and around Zürich (Limmat, Lake Zürich, etc.).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_air_quality",
            "description": "Get current air quality measurements in Zürich (PM2.5, PM10, NO2, O3).",
            "parameters": {
                "type": "object",
                "properties": {
                    "station": {
                        "type": "string",
                        "description": "Station name (e.g. 'Zürich Kaserne', 'Zürich Heubeck'). Leave empty for all stations.",
                        "default": ""
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pois",
            "description": (
                "Get points of interest in Zürich (shops, restaurants, pharmacies, supermarkets, etc.) from OpenStreetMap, "
                "sorted by distance from the given location. "
                "When the user asks for the 'nearest' or 'closest' place, ask for their address or current location first, "
                "then pass it as user_address. Results include opening_hours — always mention them in your answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category: restaurant, cafe, bar, hotel, museum, attraction, church, park, viewpoint, pharmacy, hospital, supermarket, bank, atm, post_office, library, cinema, theatre, swimming_pool, fitness_centre, bicycle_parking, bus_station, tram_stop, railway_station",
                        "default": "restaurant"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query — use the place type or brand name (e.g. 'Migros', 'pharmacy', 'restaurant')",
                        "default": ""
                    },
                    "user_address": {
                        "type": "string",
                        "description": "User's current address or location in Zürich (e.g. 'Bahnhofstrasse 10, Zürich'). Used to find nearest results. Leave empty to search city-wide."
                    },
                    "user_latitude": {
                        "type": "number",
                        "description": "User's latitude (optional, use instead of user_address if coordinates are known)"
                    },
                    "user_longitude": {
                        "type": "number",
                        "description": "User's longitude (optional, use instead of user_address if coordinates are known)"
                    },
                    "radius_m": {
                        "type": "integer",
                        "description": "Search radius in metres around the user's location (default: 1500)",
                        "default": 1500
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default: 5)",
                        "default": 5
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_voting_results",
            "description": "Get Swiss/Zürich voting and referendum results since 1933.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_filter": {
                        "type": "string",
                        "description": "Date filter: YYYY for year, YYYY-MM for month, YYYY-MM-DD for exact date",
                        "default": ""
                    },
                    "level": {
                        "type": "string",
                        "description": "Political level: Eidgenossenschaft (federal), Kanton Zürich (cantonal), Stadt Zürich (city)",
                        "default": ""
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default: 5)",
                        "default": 5
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_events",
            "description": "Get upcoming events in and around Zürich from Eventfrog.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for events (e.g. 'concert', 'exhibition', 'festival')",
                        "default": ""
                    },
                    "category": {
                        "type": "string",
                        "description": "Event category filter",
                        "default": ""
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default: 10)",
                        "default": 10
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_venues",
            "description": "Get venues in Zürich: restaurants, bars, cafes, hotels, attractions, museums, activities, shopping, etc. from zuerich.com. Supports filtering by name — use name_filter when looking for a specific restaurant or venue by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category: gastronomy, american, asian, swiss, italian, french, mediterranean, steakhouse, seafood, dinner, lunch, bar, cafe, breakfast, bars, nightlife, accommodation, hotel, attractions, museums, art, churches, nature, parks, viewpoints, activities, tours, shopping, fashion, souvenirs",
                        "default": "gastronomy"
                    },
                    "name_filter": {
                        "type": "string",
                        "description": "Optional: filter results to venues whose name contains this string (case-insensitive). Use when looking for a specific restaurant by name, e.g. 'Vallocaia', 'Kronenhalle'.",
                        "default": ""
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default: 10)",
                        "default": 10
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_waste_schedule",
            "description": "Get waste collection schedule for a Zürich zip code (garbage, bio waste, paper, cardboard).",
            "parameters": {
                "type": "object",
                "properties": {
                    "zip_code": {
                        "type": "string",
                        "description": "Zürich zip code (e.g. 8001, 8002, 8032)",
                        "default": ""
                    },
                    "waste_type": {
                        "type": "string",
                        "description": "Type of waste: kehricht (garbage), bioabfall (bio waste), papier (paper), karton (cardboard)",
                        "enum": ["kehricht", "bioabfall", "papier", "karton"],
                        "default": "kehricht"
                    },
                    "upcoming_days": {
                        "type": "integer",
                        "description": "Number of days to look ahead (default: 30)",
                        "default": 30
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_collection_points",
            "description": "Get recycling collection points in Zürich (glass, metal, oil, textiles).",
            "parameters": {
                "type": "object",
                "properties": {
                    "zip_code": {
                        "type": "string",
                        "description": "Zürich zip code (e.g. 8001, 8002)",
                        "default": ""
                    },
                    "material": {
                        "type": "string",
                        "description": "Material to recycle: glas, metall, oel, textilien",
                        "enum": ["glas", "metall", "oel", "textilien"],
                        "default": ""
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_mobile_recycling",
            "description": "Get upcoming dates for mobile recycling centers in Zürich.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zip_code": {
                        "type": "string",
                        "description": "Zürich zip code (e.g. 8001, 8002)",
                        "default": ""
                    },
                    "upcoming_days": {
                        "type": "integer",
                        "description": "Number of days to look ahead (default: 60)",
                        "default": 60
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_badi_info",
            "description": "Get current status, opening hours and water temperature for Zürich Badis (swimming pools and outdoor areas). Use when the user asks if a specific Badi is open, e.g. 'Ist der Letten offen?', 'Wann hat die Badi Mythenquai auf?'. Includes Letten, Oberer Letten, Unterer Letten, Mythenquai, Tiefenbrunnen, Enge, Utoquai, Wollishofen, Allenmoos, Heuried, Letzigraben, Frauenbad, Männerbad and more. Outdoor Freibäder are seasonal (May–September) — this tool will say so when they are closed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "badi_name": {
                        "type": "string",
                        "description": "Name of the badi (e.g. 'Letten', 'Mythenquai', 'Tiefenbrunnen'). Leave empty to get all badis.",
                        "default": ""
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_schedules",
            "description": "Get all waste collection schedules (garbage, bio, paper, cardboard, mobile recycling) for a Zürich zip code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zip_code": {
                        "type": "string",
                        "description": "Zürich zip code (e.g. 8001, 8002)",
                        "default": ""
                    },
                    "upcoming_days": {
                        "type": "integer",
                        "description": "Number of days to look ahead (default: 14)",
                        "default": 14
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information using SearXNG. Use this when other tools don't cover the topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - pass the user's question directly"
                    },
                    "categories": {
                        "type": "string",
                        "description": "Optional category: general, news, images, videos, it, science, files, social media",
                        "default": ""
                    },
                    "language": {
                        "type": "string",
                        "description": "Language code: de, en, fr, it",
                        "default": "de"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Search the Zürich knowledge base for local, cultural, and legal knowledge. "
                "Use for: neighborhood character and recommendations (Kreis 1-12), Swiss customs "
                "and etiquette, tenancy and housing law, government services, local news, "
                "restaurant and food recommendations, recycling rules, history, hidden gems. "
                "Works in German, English, French, Italian, and Swiss German. "
                "For questions about specific places, combine this with get_pois or get_venues "
                "to also get real-time addresses and opening hours."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language question or topic to search for"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of knowledge chunks to retrieve (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_rent_prices",
            "description": "Get rent price statistics for Zürich from the official Mietpreiserhebung (MPE). Shows median, mean and quartile rents by neighbourhood (Quartier/Stadtkreis) and number of rooms. Use when asked about rent costs, housing prices, or how expensive it is to live in a specific area.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quartier": {
                        "type": "string",
                        "description": "Neighbourhood or Stadtkreis (e.g. 'Ganze Stadt', 'Kreis 4', 'Langstrasse', 'Wipkingen'). Leave empty for city-wide overview.",
                        "default": ""
                    },
                    "rooms": {
                        "type": "string",
                        "description": "Number of rooms (e.g. '2', '3', '3.5', '4'). Leave empty for all room sizes.",
                        "default": ""
                    },
                    "gemeinnuetzig": {
                        "type": "boolean",
                        "description": "If true, return cooperative/social housing prices only.",
                        "default": False
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pedestrian_counts",
            "description": "Get current pedestrian frequency counts on the Zürich Bahnhofstrasse (Nord, Mitte, Süd) and Lintheschergasse. Updated hourly. Use when asked how busy/crowded Bahnhofstrasse is right now.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Look-back window in hours (1–24). Default 6.",
                        "default": 6
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_water_quality",
            "description": "Get drinking water quality measurements for Zürich from Wasserversorgung Zürich. Shows key parameters (E. coli, pH, nitrate, turbidity) and whether all values comply with legal limits. Use when asked if tap water in Zürich is safe to drink.",
            "parameters": {
                "type": "object",
                "properties": {
                    "standort": {
                        "type": "string",
                        "description": "Measurement location (e.g. 'Moos', 'Hardhof', 'Lengg'). Leave empty for all locations.",
                        "default": ""
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_crime_stats",
            "description": "Get crime statistics (Kriminalstatistik) for Zürich Stadtkreise from the Kantonspolizei. Shows number of offences by category and crime rate per 1,000 residents. Use when asked about safety, crime rates, or how safe a neighbourhood is.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stadtkreis": {
                        "type": "string",
                        "description": "Kreis number or name (e.g. '4', 'Kreis 4'). Leave empty for all city districts.",
                        "default": ""
                    },
                    "category": {
                        "type": "string",
                        "description": "Crime category filter (e.g. 'Einbruch', 'Körperverletzung', 'Diebstahl'). Leave empty for all categories.",
                        "default": ""
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recycling_stats",
            "description": "Get latest recycling and waste statistics for Zürich from ERZ (Entsorgung + Recycling Zürich). Shows Zürisack sales, recycling quota percentage, and monthly waste tonnage. Use when asked about Zürich's recycling rate or waste volumes.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_electricity_load",
            "description": "Get current electricity consumption (Bruttolastgang) for the city of Zürich from EWZ. Shows real-time power demand in megawatts with 15-minute resolution. Use when asked about Zürich's energy consumption or current power demand.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_law_knowledge_base",
            "description": (
                "Search the Swiss federal law collection (Bundesverfassung, OR, ZGB, StGB, StPO, ZPO, VRV). "
                "Use ONLY when the user explicitly asks for statutory text, specific article numbers, "
                "or legal citations (e.g. 'Was steht in OR Art. 271?', 'Zeig mir den Gesetzestext zur Kündigung'). "
                "Do NOT use for general advice or questions — use search_knowledge_base for those."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Legal question or article reference, e.g. 'OR Art. 271 Kündigung', 'ZGB Eigentumsrecht Artikel'"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of law chunks to retrieve (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
]


def dispatch_tool(name, arguments):
    """Dispatch a tool call to the appropriate connector function.
    
    Args:
        name: Tool name (e.g. 'get_weather')
        arguments: Dict of arguments for the tool
    
    Returns:
        Dict with success, data, source, error
    """
    # New per-folder registry takes precedence. Tools that have been migrated
    # resolve here; anything not yet migrated falls through to the legacy
    # if/elif block below.
    if name in connector_registry._registry:
        return connector_registry.dispatch(name, arguments)

    try:
        if name == "get_weather":
            return weather_connector.get_weather(
                location=arguments.get("location", "Zürich")
            )
        
        elif name == "get_connections":
            return transit_connector.get_connections(
                origin=arguments.get("from_station", ""),
                destination=arguments.get("to_station", ""),
                limit=arguments.get("limit", 3)
            )

        elif name == "get_departures":
            return transit_connector.get_departures(
                stop_name=arguments.get("station", "Zürich HB"),
                limit=arguments.get("limit", 5)
            )

        elif name == "get_parking":
            return parking_connector.get_parking()

        elif name == "get_water_temps":
            return water_connector.get_water_temperature()

        elif name == "get_air_quality":
            return air_quality_connector.get_air_quality()

        elif name == "get_pois":
            poi_query = arguments.get("query") or arguments.get("category", "restaurant")
            lat = arguments.get("user_latitude")
            lon = arguments.get("user_longitude")
            # Geocode user_address → lat/lon if coordinates not provided directly
            user_address = arguments.get("user_address", "")
            if user_address and not (lat and lon):
                import requests as _requests
                try:
                    # geo.admin.ch — official Swiss federal address index, knows every Swiss street
                    r = _requests.get(
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
            return poi_connector.search_poi(
                query=poi_query,
                lat=lat,
                lon=lon,
                radius=arguments.get("radius_m", 1500),
                limit=arguments.get("limit", 5)
            )
        
        elif name == "get_voting_results":
            return voting_connector.get_voting_results(
                date_filter=arguments.get("date_filter", ""),
                level=arguments.get("level", ""),
                limit=arguments.get("limit", 5)
            )
        
        elif name == "get_events":
            return events_connector.get_events(
                query=arguments.get("query", ""),
                category=arguments.get("category", ""),
                limit=arguments.get("limit", 10)
            )
        
        elif name == "get_venues":
            return venues_connector.get_venues(
                category=arguments.get("category", "gastronomy"),
                limit=arguments.get("limit", 10),
                name_filter=arguments.get("name_filter", ""),
            )
        
        elif name == "get_waste_schedule":
            return recycling_connector.get_waste_schedule(
                zip_code=arguments.get("zip_code"),
                waste_type=arguments.get("waste_type", "kehricht"),
                upcoming_days=arguments.get("upcoming_days", 30)
            )
        
        elif name == "get_collection_points":
            return recycling_connector.get_collection_points(
                zip_code=arguments.get("zip_code"),
                material=arguments.get("material")
            )
        
        elif name == "get_mobile_recycling":
            return recycling_connector.get_mobile_recycling_centers(
                zip_code=arguments.get("zip_code"),
                upcoming_days=arguments.get("upcoming_days", 60)
            )
        
        elif name == "get_all_schedules":
            return recycling_connector.get_all_schedules(
                zip_code=arguments.get("zip_code"),
                upcoming_days=arguments.get("upcoming_days", 14)
            )
        
        elif name == "web_search":
            return search_connector.search(
                query=arguments.get("query", ""),
                categories=arguments.get("categories"),
                language=arguments.get("language", "de"),
                limit=arguments.get("limit", 10)
            )

        elif name == "get_badi_info":
            return water_connector.get_badi_info(
                badi_name=arguments.get("badi_name", "")
            )

        elif name == "search_knowledge_base":
            return knowledge_connector.search_knowledge_base(
                query=arguments.get("query", ""),
                limit=arguments.get("limit", 5)
            )

        elif name == "search_law_knowledge_base":
            return knowledge_connector.search_law_knowledge_base(
                query=arguments.get("query", ""),
                limit=arguments.get("limit", 5)
            )

        elif name == "get_rent_prices":
            return rent_connector.get_rent_prices(
                quartier=arguments.get("quartier", ""),
                rooms=arguments.get("rooms", ""),
                gemeinnuetzig=arguments.get("gemeinnuetzig", False),
            )

        elif name == "get_pedestrian_counts":
            return pedestrian_connector.get_pedestrian_counts(
                hours=arguments.get("hours", 6),
            )

        elif name == "get_water_quality":
            return water_quality_connector.get_water_quality(
                standort=arguments.get("standort", ""),
            )

        elif name == "get_crime_stats":
            return crime_connector.get_crime_stats(
                stadtkreis=arguments.get("stadtkreis", ""),
                category=arguments.get("category", ""),
            )

        elif name == "get_recycling_stats":
            return city_stats_connector.get_recycling_stats()

        elif name == "get_electricity_load":
            return city_stats_connector.get_electricity_load()

        else:
            return {"success": False, "data": None, "source": None, "error": f"Unknown tool: {name}"}
    
    except Exception as e:
        return {"success": False, "data": None, "source": None, "error": f"Tool execution error: {str(e)}"}