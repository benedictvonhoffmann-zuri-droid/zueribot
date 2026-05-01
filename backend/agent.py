"""
ZüriBot LangGraph Agent — state machine orchestration.
"""

import json
import logging
from typing import Annotated, Literal
from typing_extensions import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.types import StreamWriter

from backend.config.settings import get_llm
from backend.tools.tools import TOOL_DEFINITIONS, dispatch_tool

logger = logging.getLogger("zuribot.agent")

# RAG tool names that trigger document grading
RAG_TOOL_NAMES = {"search_knowledge_base", "search_law_knowledge_base"}

GRADER_PROMPT = """You are a document relevance grader for a Zürich city assistant.

Given a user question and retrieved knowledge base excerpts, decide if the documents
are relevant enough to answer the question.

Output ONLY valid JSON: {"relevant": true} or {"relevant": false}

Mark relevant=false if:
- The documents are clearly about a different topic than the question
- The documents contain only empty results or "no results found"
- The retrieved content cannot help answer the question at all

Mark relevant=true if the documents contain ANY useful information related to the question,
even if partial."""

SYSTEM_PROMPT = """You are ZüriBot, a helpful assistant for the city of Zürich, Switzerland.

You help residents and visitors with:
- Weather forecasts and conditions
- Public transport (trams, buses, trains) departures and connections
- Parking availability
- Water temperatures at swimming spots (Badis)
- Air quality measurements
- Points of interest (restaurants, museums, attractions, etc.)
- Voting and referendum results
- Events happening in and around Zürich
- Venues (restaurants, bars, hotels, attractions)
- Waste collection schedules (garbage, bio waste, paper, cardboard)
- Recycling collection points (glass, metal, oil, textiles)
- Mobile recycling center schedules
- General web search when other tools don't cover the topic
- Local knowledge: neighborhoods, Swiss customs, tenancy law, government services, restaurant recommendations, expat tips, news

## Source Routing — which tool to use when

Use this guide to decide which source to consult first:

| Type of question | Primary source |
|---|---|
| Simple general knowledge (geography, world facts, language) | Answer from your own knowledge — no tool needed |
| Zürich-specific background, neighborhood character, cultural events, expat tips, local history | `search_knowledge_base` first |
| Real-time or time-sensitive (departures, parking, weather, badi status, air quality, events) | Live connector (get_departures, get_connections, get_parking, get_badi_info, get_weather, get_events, etc.) |
| Swiss statutory text, specific law articles (OR, ZGB, BV, StGB, StPO) | `search_law_knowledge_base` |
| Recent news, current prices, things that may have changed | `web_search` |
| KB returns empty or clearly irrelevant results | You MUST call `web_search` in the same turn. Do not: (a) tell the user to check an external website themselves, (b) list possible websites as "alternatives", (c) ask the user to clarify — those are forbidden escapes. Call web_search first, then decide. |
| Questions needing multiple perspectives | Call `search_knowledge_base` AND the live connector AND `web_search` in one turn (parallel) |

## Rules

- Always respond in the same language the user writes in (German, Swiss German, English, French, Italian)
- If the user writes in Swiss German, respond in Swiss German
- Be concise and practical
- If a tool returns an error, explain it simply and suggest alternatives
- For locations, always include the address if available
- For schedules, format dates clearly in European format (DD.MM.YYYY)
- When mentioning times, use 24h format
- **Realtime-values rule**: never state a specific current number (temperature, occupancy %, free spaces, wait minutes, price) unless a connector call *in this same turn* returned that exact value. If no connector was called or it failed, write "Ich habe für X gerade keine Live-Daten" (or the equivalent in the user's language) and point the user at a source they can check themselves. Never extrapolate from a related value (e.g. other parking garages, yesterday's temperature).
- For questions about specific places (restaurants, shops, venues): call `search_knowledge_base` for editorial context AND `get_pois` or `get_venues` for current addresses/hours — both in the same turn
- **When the user asks about a specific named restaurant, club, bar or venue** (e.g. "Vallocaia", "Kronenhalle", "Hive", "Rote Fabrik"): call ALL THREE in parallel — `search_knowledge_base` with the name, `get_pois` with query=venue_name (name search, not category), AND `get_venues` with name_filter=venue_name. If all three return no results, immediately follow up with `web_search("{name} Zürich")`.
- **Name-match discipline**: if retrieval returns a venue whose name is only *similar* to the one the user asked for (e.g. user says "Hive", result is "Heuried"; user says "Rote Fabrik", result is "Roter Turm"), treat that as a miss, NOT a match. Do not answer about the similar-but-wrong venue. Fall through to `web_search` and tell the user you couldn't find their exact venue.
- **Displaying restaurant/venue details**: Always present in structured form: **Name**, address (street + postcode), opening hours formatted as readable schedule, phone if available, website/booking link as clickable markdown link. Never omit details that are present in tool results.
- For questions about events: check `get_events` for what's on AND `search_knowledge_base` for background on the venue or festival
- When the user asks for the "nearest" location: ask for their exact street address and postcode first. ZüriBot does not access device location for privacy reasons. Once address is provided, call `get_pois` with it as `user_address`
- For Badi questions ("Ist der Letten offen?", "Wann hat die Badi auf?"): use `get_badi_info`. For lake water temperatures: use `get_water_temps`
- Always synthesise results from multiple sources into one coherent, well-structured answer — do not paste raw tool output
- Always cite sources at the end of your answer. Use the [Quelle: ...] tag from tool results. For `search_knowledge_base` results, cite the **actual source names** from `data.sources` (e.g. "Mieterverband", "SRF", "tsri.ch", "HEV Schweiz") — never just "Zürich Knowledge Base". For web results, cite the publication name or URL
- When a connector result includes a URL for a restaurant, venue, or place, always include it as a clickable markdown link: `[Name](url)`
- When connectors report a data publication lag (e.g. electricity, pedestrian counts), always mention the timestamp of the latest available data so the user understands how current the information is
"""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def should_continue(state: AgentState) -> Literal["tools", "respond"]:
    """Check if the model wants to call tools or respond directly."""
    last_message= state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "respond"


def call_model(state: AgentState, writer: StreamWriter) -> AgentState:
    """Call the LLM with current messages, streaming text tokens via writer."""
    messages = state["messages"]

    llm = get_llm().bind_tools(list(TOOL_DEFINITIONS))

    accumulated = None
    for chunk in llm.stream(messages):
        # Emit text tokens only — skip tool_call_chunks (they carry JSON args, not text)
        if chunk.content and not chunk.tool_call_chunks:
            # Claude can return content as a list of blocks
            text = chunk.content
            if isinstance(text, list):
                text = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in text)
            if text:
                writer({"token": text})
        accumulated = chunk if accumulated is None else accumulated + chunk

    if accumulated is None:
        accumulated = AIMessage(content="")

    return {"messages": [accumulated]}


def grade_rag_results(state: AgentState) -> AgentState:
    """
    CRAG: After RAG tool calls, check if retrieved chunks are actually relevant.
    If not relevant, inject an AIMessage signalling the agent to try web_search.
    """
    messages = state["messages"]

    # Find the most recent RAG tool result
    rag_messages = [
        m for m in messages
        if isinstance(m, ToolMessage) and m.name in RAG_TOOL_NAMES
    ]
    if not rag_messages:
        return state  # No RAG result to grade

    rag_content = rag_messages[-1].content

    # Find the last user question
    user_query = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            user_query = m.content if isinstance(m.content, str) else str(m.content)
            break

    if not user_query:
        return state

    # Quick heuristic: if content is clearly empty/no results, skip LLM grading
    lower = rag_content.lower()
    if any(phrase in lower for phrase in ["keine ergebnisse", "no results", '"results": []', '"chunks": []']):
        logger.info("Grader: RAG returned empty results — injecting web_search signal")
        return {"messages": [AIMessage(
            content="[GRADER: Knowledge base returned no relevant results. I will search the web.]"
        )]}

    # LLM grading call (fast, small prompt)
    try:
        grader_llm = get_llm()
        response = grader_llm.invoke([
            SystemMessage(content=GRADER_PROMPT),
            HumanMessage(content=f"Question: {user_query[:400]}\n\nDocuments: {rag_content[:1500]}"),
        ])
        raw = response.content
        if isinstance(raw, list):
            raw = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in raw)
        raw = raw.strip()

        # Extract JSON (model may wrap it in markdown)
        import re
        match = re.search(r'\{[^}]+\}', raw)
        if match:
            grade = json.loads(match.group())
            if not grade.get("relevant", True):
                logger.info("Grader: RAG results not relevant — injecting web_search signal")
                return {"messages": [AIMessage(
                    content="[GRADER: Retrieved documents are not relevant to the question. I will search the web for a better answer.]"
                )]}
    except Exception as e:
        logger.warning("Grader failed (non-blocking): %s", e)

    return state  # Relevant — continue normally


def call_tools(state: AgentState) -> AgentState:
    """Execute tool calls from the model."""
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls
    
    tool_messages = []
    for tc in tool_calls:
        name = tc["name"]
        arguments = tc.get("args", {})
        
        logger.info("Tool call: %s(%s)", name, json.dumps(arguments, ensure_ascii=False))
        
        result = dispatch_tool(name, arguments)
        
        if result.get("success"):
            data_json = json.dumps(result.get("data", {}), ensure_ascii=False, default=str)[:6000]
            source = result.get("source", {})
            source_note = f'\n[Quelle: {source["name"]}]' if source.get("name") else ""
            content = data_json + source_note
        else:
            content = f"Error: {result.get('error', 'Unknown error')}"
        
        tool_messages.append(
            ToolMessage(
                content=content,
                tool_call_id=tc["id"],
                name=name,
            )
        )
    
    return {"messages": tool_messages}


workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", call_tools)
workflow.add_node("grade", grade_rag_results)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "respond": END,
    },
)

# After tools run, grade RAG results before returning to the agent
workflow.add_edge("tools", "grade")
workflow.add_edge("grade", "agent")

graph = workflow.compile()