"""
ZuriBot FastAPI Server - OpenAI-compatible API for Open WebUI.
"""

import json
import uuid
import logging
import time
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
                "created": int(time.time()),
                "owned_by": "zuribot",
            }
        ],
    }


async def _stream_generator(langchain_messages: list, model: str, chat_id: str):
    """Async generator that yields OpenAI-compatible SSE lines."""
    created = int(time.time())

    # Role announcement chunk
    yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"

    try:
        async for item in graph.astream({"messages": langchain_messages}, stream_mode="custom"):
            token = item.get("token", "")
            if not token:
                continue
            yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'content': token}, 'finish_reason': None}]})}\n\n"
    except Exception as e:
        logger.error(f"Error during streaming: {e}", exc_info=True)

    # Stop chunk
    yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
    yield "data: [DONE]\n\n"


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

        chat_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"

        if request.stream:
            return StreamingResponse(
                _stream_generator(langchain_messages, request.model, chat_id),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        result = await graph.ainvoke({"messages": langchain_messages})

        final_message = result["messages"][-1]
        raw_content = final_message.content if hasattr(final_message, "content") else str(final_message)
        # Claude returns content as a list of blocks when tools are bound — extract text
        if isinstance(raw_content, list):
            response_content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in raw_content
            )
        else:
            response_content = raw_content

        return ChatResponse(
            id=chat_id,
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=response_content),
                    finish_reason="stop",
                )
            ],
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )

    except Exception as e:
        logger.error(f"Error in chat_completions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)