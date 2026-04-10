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

SYSTEM_PROMPT = """You are ZüriBot, a helpful assistant for the city of Zürich, Switzerland.

You help residents and visitors with:
- Weather forecasts and conditions
- Public transport (trams, buses, trains) departures and connections
- Parking availability
- Water temperatures at swimming spots (Badis)
- Air quality measurements
- Points of interest (restaurants, museums, attractions, etc.)
- Voting and referendum results
- Events happening in and aroürich
- Venues (restaurants, bars, hotels, attractions)
- Waste collection schedules (garbage, bio waste, paper, cardboard)
- Recycling collection points (glass, metal, oil, textiles)
- Mobile recycling center schedules
- General web search when other tools don't cover the topic

Rules:
- Always respond in the same language the user writes in (German, Swiss German, English, French, Italian)
- If the user writes in Swiss German, respond in Swiss German
- Use the available tools to get real data before answering
- Be concise and practical
- If a tool returns an error, explain it simply and suggest alternatives
- For locations, always include the address if available
- For schedules, format dates clearly in European format (DD.MM.YYYY)
- When mentioning times, use 24h format
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


def call_tools(state: AgentState) -> AgentState:
    """Execute tool calls from the model."""
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls
    
    tool_messages = []
    for tc in tool_calls:
        name = tc["name"]
        arguments = tc.get("args", {})
        
        logger.info(f"Tool call: {name}({json.dumps(arguments, ensure_ascii=False)})")
        
        result = dispatch_tool(name, arguments)
        
        if result.get("success"):
            content = json.dumps(result.get("data", {}), ensure_ascii=False, default=str)[:3000]
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

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "respond": END,
    },
)

workflow.add_edge("tools", "agent")

graph = workflow.compile()