ZURIBOT MEMORY FILE - Updated 2026-04-10

== PROJECT OVERVIEW ==
ZuriBot is a local AI assistant for Zurich, Switzerland.
Architecture: Open WebUI -> FastAPI -> LangGraph Agent -> MCP/Tools -> Connectors -> APIs
Model: Qwen 2.5:7b via Ollama
All data sources are free, no API keys needed.

== CURRENT STATE ==
WORKING:
- FastAPI server on port 8000 (OpenAI-compatible)
- LangGraph agent with state machine orchestration
- MCP server with 15 tools registered
- Open WebUI connected at http://localhost:3000
- Weather connector verified working
- All 15 connectors load without errors
- Git repo committed with all code

NOT YET TESTED:
- Transit (departures, connections) - Bellevue query returned error in old setup
- Restaurants/venues - returned no results in old setup
- Air quality, POI, voting, events, recycling, search - not tested with new architecture
- Multi-step tool calling (agent calling multiple tools in one conversation)
- Streaming responses
- Conversation memory across messages

KEY FILES:
- api_server.py - FastAPI server (entry point)
- backend/agent.py - LangGraph agent
- backend/mcp_server.py - MCP server wrapping connectors
- backend/tools/tools.py - Tool definitions + dispatch
- backend/connectors/ - All 12 connector modules
- backend/models/schemas.py - Pydantic models
- README.md - Full documentation

== HOW TO START ==
1. docker start searxng open-webui
2. cd ~/zuribot && source venv/bin/activate && python3 api_server.py
3. Open http://localhost:3000, select qwen2.5:7b

== OPEN WEBUI CONFIG ==
- Admin Settings -> Settings -> OpenAI API
- Base URL: http://host.docker.internal:8000/v1
- Key: zuribot
- If model dropdown breaks: hard refresh (Cmd+Shift+R), or disable/re-enable Ollama connection

== KNOWN ISSUES ==
1. Connector function signatures must match dispatch arguments (get_weather needed location param added)
2. Open WebUI dropdown can break with duplicate model keys - hard refresh fixes it
3. ZITADEL auth was removed when recreating Open WebUI container - needs re-adding
4. Apertus model still shows in Ollama but is outdated

== NEXT STEPS (PRIORITY ORDER) ==
1. Test all 15 tools with new LangGraph architecture
2. Fix transit connector (Bellevue station query)
3. Fix venues connector (restaurants returning no results)
4. Add conversation memory (LangGraph state persistence)
5. Add streaming responses for better UX
6. Consider upgrading to Qwen 2.5:14b for better reasoning
7. Re-add ZITADEL authentication to Open WebUI
8. Add Telegram bot interface
9. Add Docker Compose for one-command startup
10. Add unit tests for connectors

== ARCHITECTURE DECISIONS ==
- LangGraph over raw Ollama API: better for multi-step tool calls, state management
- MCP single server over multiple servers: simpler, fewer processes, fine for dev
- FastAPI over CLI-only: needed for Open WebUI integration
- Qwen 2.5:7b: good enough for dev, upgrade to 14b+ for production
- Pydantic models: defined but not yet enforced in connectors (future improvement)

== CONNECTOR STATUS ==
- weather_connector.py: WORKING (tested)
- transit_connector.py: NEEDS TESTING (Bellevue had issues)
- parking_connector.py: NEEDS TESTING
- water_connector.py: NEEDS TESTING
- air_quality_connector.py: NEEDS TESTING
- poi_connector.py: NEEDS TESTING
- voting_connector.py: NEEDS TESTING
- events_connector.py: NEEDS TESTING
- venues_connector.py: NEEDS TESTING (restaurants returned no results)
- recycling_connector.py: NEEDS TESTING
- search_connector.py: NEEDS TESTING
- city_services_connector.py: EXISTS but not in current tool definitions
- news_connector.py: EXISTS but pending API approval

== PORTS ==
- 11434: Ollama
- 8000: ZuriBot FastAPI
- 3000: Open WebUI
- 8888: SearXNG
