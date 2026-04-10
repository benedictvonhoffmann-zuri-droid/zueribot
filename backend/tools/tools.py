"""
Tool definitions and dispatch logic for ZuriBot.
Maps LLM tool calls to connector functions.
"""

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
            "description": "Get points of interest in Zürich (attractions, restaurants, hotels, etc.) from OpenStreetMap.",
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
                        "description": "Optional name search query",
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
            "description": "Get venues in Zürich: restaurants, bars, cafes, hotels, attractions, museums, activities, shopping, etc. from zuerich.com.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category: gastronomy, american, asian, swiss, italian, french, mediterranean, steakhouse, seafood, dinner, lunch, bar, cafe, breakfast, bars, nightlife, accommodation, hotel, attractions, museums, art, churches, nature, parks, viewpoints, activities, tours, shopping, fashion, souvenirs",
                        "default": "gastronomy"
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
]


def dispatch_tool(name, arguments):
    """Dispatch a tool call to the appropriate connector function.
    
    Args:
        name: Tool name (e.g. 'get_weather')
        arguments: Dict of arguments for the tool
    
    Returns:
        Dict with success, data, source, error
    """
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
            # search_poi uses text query matched against OSM_TAG_MAP;
            # combine category + optional query for the best match
            poi_query = arguments.get("query") or arguments.get("category", "restaurant")
            return poi_connector.search_poi(
                query=poi_query,
                limit=arguments.get("limit", 10)
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
                limit=arguments.get("limit", 10)
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
        
        else:
            return {"success": False, "data": None, "source": None, "error": f"Unknown tool: {name}"}
    
    except Exception as e:
        return {"success": False, "data": None, "source": None, "error": f"Tool execution error: {str(e)}"}