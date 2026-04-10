#!/usr/bin/env python3
"""
ZüriBot — Main Chat Loop
- Qwen 2.5 with native tool calling via Ollama
- Simple, sovereign, no LangChain
"""

import json
import requests
import sys

from backend.tools.tools import TOOL_DEFINITIONS, dispatch_tool

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:7b"

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
- Mobile recycling center ses
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

You have access to tools. When a user asks something that requires real-time data, call the appropriate tool first, then format the response naturally based on the data returned.
"""


def chat(messages, tools=None):
    """Send a chat request to Ollama with tool support."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
    
    resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def handle_tool_calls(response):
    """Process tool calls from the model response."""
    tool_results = []
    
    message = response.get("message", {})
    tool_calls = message.get("tool_calls", [])
    
    if not tool_calls:
        return None
    
    for tc in tool_calls:
        func = tc.get("function", {})
        name = func.get("name", "")
        arguments = func.get("arguments", {})
        
        # Parse arguments if they're a string
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        
        print(f"  🔧 Calling tool: {name}({json.dumps(arguments, ensure_ascii=False)})")
        
        result = dispatch_tool(name, arguments)
        
        tool_results.append({
            "name": name,
            "result": result,
        })
    
    return tool_results


def format_tool_results(tool_results):
    """Format tool results into a message for the model."""
    content_parts = []
    for tr in tool_results:
        name = tr["name"]
        result = tr["result"]
        
        if result.get("success"):
            # Simplify the data for the model
            content_parts.append(f"Tool: {name}\nResult: {json.dumps(result.get('data', {}), ensure_ascii=False, default=str)[:2000]}")
        else:
            content_parts.append(f"Tool: {name}\nError: {result.get('error', 'Unknown error')}")
    
    return "\n\n".join(content_parts)


def run_chat():
    """Main chat loop."""
    print("=" * 60)
    print("  ZüriBot — Your Zürich Assistant")
    print("  Type 'quit' to exit, 'clear' to reset conversation")
    print("=" * 60)
    print()
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("f Wiedersehen! 👋")
            break
        
        if not user_input:
            continue
        
        if user_input.lower() in ("quit", "exit", "q"):
            print("Auf Wiedersehen! 👋")
            break
        
        if user_input.lower() == "clear":
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            print("Conversation cleared.\n")
            continue
        
        # Add user message
        messages.append({"role": "user", "content": user_input})
        
        # First call — model may request tools
        print()
        response = chat(messages, tools=TOOL_DEFINITIONS)
        assistant_message = response.get("message", {})
        
        # Check for tool calls
        tool_calls = assistant_message.get("tool_calls", [])
        
        if tool_calls:
            # Add the assistant's tool call message
            messages.append(assistant_message)
            
            # Process tool calls
            tool_results = handle_tool_calls(response)
            
            if tool_results:
                # Format results and add as tool message
                tool_content = format_tool_results(tool_results)
                messages.append({"role": "tool", "content": tool_content})
                
                # Second call — model generates final response with tool data
                print()
                final_response = chat(messages, tools=TOOL_DEFINITIONS)
                final_message = final_response.get("message", {})
                final_content = final_message.get("content", "")
                
                # Check if the model wants to call more tools
                more_tool_calls = final_message.get("tool_calls", [])
                
                if more_tool_calls:
                    # Handle additional tool calls
                    messages.append(final_message)
                    more_results = handle_tool_calls(final_response)
                    if more_results:
                        more_content = formatool_results(more_results)
                        messages.append({"role": "tool", "content": more_content})
                        
                        # Third call
                        third_response = chat(messages, tools=TOOL_DEFINITIONS)
                        third_message = third_response.get("message", {})
                        print(f"\nZüriBot: {third_message.get('content', '')}\n")
                        messages.append(third_message)
                else:
                    print(f"\nZüriBot: {final_content}\n")
                    messages.append({"role": "assistant", "content": final_content})
        else:
            # No tool calls — just respond
            content = assistant_message.get("content", "")
            print(f"\nZüriBot: {content}\n")
            messages.append({"role": "assistant", "content": content})


if __name__ == "__main__":
    # Check if Ollama is running
    try:
        requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    except requests.exceptionnectionError:
        print("Error: Ollama is not running. Start it with: ollama serve")
        sys.exit(1)
    
    # Check if model is available
    try:
        models = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()
        model_names = [m["name"] for m in models.get("models", [])]
        if not any(MODEL in m for m in model_names):
            print(f"Model '{MODEL}' not found. Available models: {model_names}")
            print(f"Pull it with: ollama pull {MODEL}")
            sys.exit(1)
    except Exception as e:
        print(f"Warning: Could not check models: {e}")
    
    run_chat()
