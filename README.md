# ZüriBot - Your Local Zurich Assistant

A sovereign, local AI assistant for the city of Zurich, Switzerland. Built with open-source models, self-hosted infrastructure, and real-time data from official Zurich APIs.

## Architecture

Open WebUI (frontend, port 3000)
  -> FastAPI (OpenAI-compatible API, port 8000)
  -> LangGraph Agent (orchestration, state machine)
  -> MCP Server (tool protocol, wraps all connectors)
  -> Connectors (weather, transit, parking, etc.)
  -> Official Zurich APIs + Open Data

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM | Qwen 2.5:7b (Ollama) | Reasoning, tool selection, response generation |
| Orchestration | LangGraph | State machine, multi-step tool calling |
| Tool Protocol | MCP (Model Context Protocol) | Standardized tool interface |
| API | FastAPI | OpenAI-compatible REST API |
| Frontend | Open WebUI | Web chat interface |
| Search | SearNG (Docker) | Self-hosted web search |
| Validation | Pydantic | Strict output schemas |

### Data Flow

1. User asks question in Open WebUI
2. Open WebUI sends request to FastAPI /v1/chat/completions
3. FastAPI passes to LangGraph agent
4. Agent (Qwen 2.5) decides which tools to call
5. LangGraph executes tool calls via dispatch
6. Connectors fetch real data from Zurich APIs
7. Agent formats response using tool data
8. FastAPI returns response to Open WebUI

---

## Project Structure

zuribot/
  api_server.py              # FastAPI server (OpenAI-compatible)
  main.py                    # CLI chat loop (legacy, still works)
  requirements.txt            # Python dependencies
  venv/                      # Python virtual environment

  backend/
    agent.py                 # LangGraph agent (state machine)
    mcp_server.py             # MCP server (wraps all connectors as tools)
    tools/
      __init__.py
      tools.py               # Tool definitions + dispatch logic

    connectors/
      __init__.py
      weather_connector.py   # Open-Meteo API
      transit_connector.py   # ZVV API (departures + connections)
      parking_connector.py   # Zurich Parkleitsystem
      water_connector.py     # Stadt Zurich Badis
      air_quality_connector.py  # Ostluft / Umweltzone
      poi_connector.py       # OpenStreetMap Overpass API
      voting_connector.py    # Swissvotes / Bundeskanzlei
      events_connector.py    # Eventfrog API
      venues_connector.py    # zuerich.com API
      recycling_connector.py # Stadt Zurich ERZ (waste + recycling)
      search_connector.py   # SearXNG (self-hosted web search)

    models/
      __init__.py
      schemas.py             # Pydantic models for all outputs

---

## Quick Start

### Prerequisites

- macOS or Linux
- Python 3.11+
- Docker (for SearXNG and Open WebUI)
- Ollama (for LLM inference)

### 1. Clone and Setup

cd ~
git clone <repo-url> zuribot
cd zuribot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

### 2. Start Ollama and Pull Model

ollama serve
ollama pull qwen2.5:7b

### 3. Start SearXNG (Web Search)

docker run -d -p 8888:8080 --name searxng   -e SEARXNG_BASE_URL=http://localhost:8888   -e SEARXNG_SECRET=a420a04193aac5f982607b7d735e0bed6b4ffd634f0ba178cc015cf91fcf17d5   --restart always   searxng/searxng

### 4. Start Open WebUI

docker run -d -p 3000:8080   --add-host=host.docker.internal:host-gateway   -v open-webui:/app/backend/data   --name open-webui   --restart always   ghcr.io/open-webui/open-webui:main

### 5. Start ZuriBot API

cd ~/zuribot
source venv/bin/activate
python3 api_server.py

### 6. Configure Open WebUI

1. Open http://localhost:3000
2. Create admin account
3. Go to Admin Settings -> Settings -> OpenAI API
4. Add Base URL: http://host.docker.internal:8000/v1
5. Add Key: zuribot
6. Save and verify connection
7. Hard refresh browser (Cmd+Shift+R)
8. Select qwen2.5:7b from model dropdown

### 7. Chat!

Ask questions in any language:

- Wie wird das Wetter in Zurich?
- Wann kommt der nachste Tram am Bellevue?
- Wo kann ich Glas entsorgen in 8001?
- Wie ist die Luftqualitat?
- Was gibt es fur Events in Zurich?

---

## Available Tools (15)

| Tool | Description | Source |
|------|-------------|--------|
| get_weather | Current weather + 3-day forecast | Open-Meteo |
| get_departures | Next departures from a station | ZVV API |
| get_connections | Connections between stations | ZVV API |
| get_parking | Parking garage availability | Parkleitsystem |
| get_water_temps | Water temps at swimming spots | Stadt Zurich |
| get_air_quality | Air quality measurements | Ostluft |
| get_pois | Points of interest (OSM) | OpenStreetMap |
| get_voting_results | Swiss/Zurich voting results | Swissvotes |
| get_events | Upcoming events | Eventfrog |
| get_venues | Restaurants, bars, hotels, etc. | zuerich.com |
| get_waste_schedule | Garbage/bio/paper/cardboard schedule | ERZ Stadt Zurich |
| get_collection_points | Glass/metal/oil/textile recycling | ERZ Stadt Zurich |
| get_mobile_recycling | Mobile recycling center dates | ERZ Stadt Zurich |
| get_all_schedules | All waste schedules combined | ERZ Stadt Zurich |
| web_search | General web search | SearXNG |

---

## API Reference

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Health check |
| GET | /health | Health check |
| GET | /v1/models | List available models |
| POST | /v1/chat/completions | OpenAI-compatible chat |

### Example: Chat Completion

curl -X POST http://localhost:8000/v1/chat/completions   -H "Content-Type: application/json"   -d '{"messages":[{"role":"user","content":"Wie wird das Wetter in Zurich?"}]}'

### Example: List Models

curl http://localhost:8000/v1/models

---

## Running Services

| Service | Port | Start Command |
|---------|------|---------------|
| Ollama | 11434 | ollama serve |
| SearXNG | 8888 | docker start searxng |
| Open WebUI | 3000 | docker start open-webui |
| ZuriBot API | 8000 | cd ~/zuribot && source venv/bin/activate && python3 api_server.py |

### Start Everything

Terminal 1: Ollama
  ollama serve

Terminal 2: SearXNG + Open WebUI
  docker start searxng open-webui

Terminal 3: ZuriBot API
  cd ~/zuribot && source venv/bin/activate && python3 api_server.py

---

## Adding a New Connector

### 1. Create connector file (backend/connectors/my_connector.py)

import requests

def get_my_data(query: str = "", limit: int = 10) -> dict:
    try:
        resp = requests.get(
            "https://api.example.com/data",
            params={"q": query, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "success": True,
            "data": data,
            "source": {"name": "My API", "type": "api"},
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "source": {"name": "My API", "type": "api"},
            "error": str(e),
        }

### 2. Add to connectors/__init__.py

from backend.connectors import my_connector

### 3. Add tool definition in backend/tools/tools.py

Add to TOOL_DEFINITIONS list:
  {"name": "get_my_data", "description": "Fetch data from my API.", ...}

### 4. Add dispatch in backend/tools/tools.py

elif name == "get_my_data":
    return my_connector.get_my_data(
        query=arguments.get("query", ""),
        limit=arguments.get("limit", 10)
    )

### 5. Add MCP tool in backend/mcp_server.py

@mcp.tool()
def get_my_data(query: str = "", limit: int = 10) -> str:
    result = my_connector.get_my_data(query=query, limit=limit)
    return json.dumps(result, ensure_ascii=False, default=str)

### 6. Add Pydantic model in backend/models/schemas.py

class MyDataItem(BaseModel):
    name: str
    description: Optional[str]

class MyDataResult(BaseModel):
    items: List[MyDataItem]
    total: int

### 7. Test

cd ~/zuribot && source venv/bin/activate
python3 -c "from backend.tools.tools import dispatch_tool; print(dispatch_tool('get_my_data', {'query': 'test'}))"

---

## Troubleshooting

### Ollama not running
ollama serve

### Model not found
ollama pull qwen2.5:7b

### SearXNG not running
docker start searxng

### Open WebUI not running
docker start open-webui

### Port 8000 already in use
lsof -i :8000
kill <PID>

### Open WebUI model dropdown not working
1. Hard refresh browser (Cmd+Shift+R)
2. Check Admin Settings -> Settings -> OpenAI API connection
3. Verify URL: http://host.docker.internal:8000/v1
4. Verify key: zuribot
5. Restart Open WebUI: docker restart open-webui

### Tool call errors
Check that the connector function signature matches the dispatch arguments.

---

## Connector API Sources

| Connector | API | Notes |
|-----------|-----|-------|
| Weather | Open-Meteo | Free, no key needed |
| Transit | ZVV/OpenTripPlanner | Free, no key needed |
| Parking | Zurich Parkleitsystem | Free, no key needed |
| Water Temp | Stadt Zurich | Free, no key needed |
| Air Quality | Ostluft | Free, no key needed |
| POI | OpenStreetMap Overpass | Free, no key needed |
| Voting | Swissvotes | Free, no key needed |
| Events | Eventfrog | Free, key needed |
| Venues | zuerich.com | Free, no key needed |
| Recycling | ERZ Stadt Zurich | Free, no key needed |
| Web Search | SearXNG (self-hosted) | Free, self-hosted |
| News | SRG API | Pending |

---

## Future Improvements

- [ ] Upgrade to Qwen 2.5:14b or 72b for better reasoning
- [ ] Add conversation memory (LangGraph state persistence)
- [ ] Add streaming responses
- [ ] Add Telegram bot interface
- [ ] Add news connector (pending API approval)
- [ ] Split MCP server into individual connectors for production
- [ ] Add Docker Compose for one-command startup
- [ ] Add authentication to FastAPI
- [ ] Add rate limiting
- [ ] Add logging and monitoring
- [ ] Add unit tests for all connectors
- [ ] Add integration tests for agent
- [ ] Re-add ZITADEL authentication to Open WebUI
- [ ] Consider Apertus model for Swiss German
