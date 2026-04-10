"""
ZuriBot FastAPI Server - OpenAI-compatible API for Open WebUI.
"""

import json
import uuid
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from backend.agent import graph, SYSTEM_PROMPT

logger = logging.getLogger("zuribot.api")

app = FastAPI(title="ZuriBot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "qwen2.5:7b"
    temperature: float = 0.1
    stream: bool = False


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: Usage


@app.get("/")
async def root():
    return {"name": "ZuriBot API", "version": "1.0.0", "status": "running"}


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen2.5:7b",
                "object": "model",
                "created": int(datetime.now().timestamp()),
                "owned_by": "zuribot",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    try:
        langchain_messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
        for msg in request.messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))
        
        result = graph.invoke({"messages": langchain_messages})
        
        final_message = result["messages"][-1]
        response_content = final_message.content if hasattr(final_message, "content") else str(final_message)
        
        return ChatResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(datetime.now().timestamp()),
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=response_content),
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            ),
        )
    
    except Exception as e:
        logger.error(f"Error in chat_completions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)