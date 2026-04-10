"""
ZuriBot MCP Server - wraps all connectors as MCP tools.
Single server approach for simplicity.
"""

import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

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

logger = logging.getLogger("zuribot.mcp")

mcp = FastMCP("ZuriBot")


@mcp.tool()
def get_weather(location: str = "Zuerich") -> str:
    """Get current weather forecast for Zurich. Returns temperature, conditions, wind, and humidity."""
    result = weather_connector.get_weather(location=location)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_departures(station: str, limit: int = 5) -> str:
    """Get next departures from a Zurich transit station (tram, bus, train)."""
    result = transit_connector.get_departures(station=station, limit=limit)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_connections(from_station: str, to_station: str, limit: int = 3) -> str:
    """Get connections between two transit stations in Zurich."""
    result = transit_connector.get_connections(from_station=from_station, to_station=to_station, limit=limit)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_parking() -> str:
    """Get current parking availability in Zurich. Shows free spaces, total capacity, and status for each parking garage."""
    result = parking_connector.get_parking_situation()
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_water_temps() -> str:
    """Get current water temperatures for swimming spots in and around Zurich (Limmat, Lake Zurich, etc.)."""
    result = water_connector.get_water_temps()
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_air_quality(station: str = "") -> str:
    """Get current air quality measurements in Zurich (PM2.5, PM10, NO2, O3)."""
    result = air_quality_connector.get_air_quality(station=station)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_pois(category: str = "restaurant", query: str = "", limit: int = 10) -> str:
    """Get points of interest in Zurich (attractions, restaurants, hotels, etc.) from OpenStreetMap."""
    result = poi_connector.get_pois(category=category, query=query, limit=limit)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_voting_results(date_filter: str = "", level: str = "", limit: int = 5) -> str:
    """Get Swiss/Zurich voting and referendum results since 1933."""
    result = voting_connector.get_voting_results(date_filter=date_filter, level=level, limit=limit)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_events(query: str = "", category: str = "", limit: int = 10) -> str:
    """Get upcoming events in and around Zurich from Eventfrog."""
    result = events_connector.get_events(query=query, category=category, limit=limit)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_venues(category: str = "gastronomy", limit: int = 10) -> str:
    """Get venues in Zurich: restaurants, bars, cafes, hotels, attractions, museums, activities, shopping, etc. from zuerich.com."""
    result = venues_connector.get_venues(category=category, limit=limit)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_waste_schedule(zip_code: str = "", waste_type: str = "kehricht", upcoming_days: int = 30) -> str:
    """Get waste collection schedule for a Zurich zip code (garbage, bio waste, paper, cardboard)."""
    result = recycling_connector.get_waste_schedule(zip_code=zip_code, waste_type=waste_type, upcoming_days=upcoming_days)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_collection_points(zip_code: str = "", material: str = "") -> str:
    """Get recycling collection points in Zurich (glass, metal, oil, textiles)."""
    result = recycling_connector.get_collection_points(zip_code=zip_code, material=material)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_mobile_recycling(zip_code: str = "", upcoming_days: int = 60) -> str:
    """Get upcoming dates for mobile recycling centers in Zurich."""
    result = recycling_connector.get_mobile_recycling_centers(zip_code=zip_code, upcoming_days=upcoming_days)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def get_all_schedules(zip_code: str = "", upcoming_days: int = 14) -> str:
    """Get all waste collection schedules (garbage, bio, paper, cardboard, mobile recycling) for a Zurich zip code."""
    result = recycling_connector.get_all_schedules(zip_code=zip_code, upcoming_days=upcoming_days)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def web_search(query: str, categories: str = "", language: str = "de", limit: int = 10) -> str:
    """Search the web for information using SearXNG. Use this when other tools don't cover the topic."""
    result = search_connector.search(query=query, categories=categories if categories else None, language=language, limit=limit)
    return json.dumps(result, ensure_ascii=False, default=str)


if __name__ == "__main__":
    mcp.run()