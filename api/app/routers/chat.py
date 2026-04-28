from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse
from app.services import llm


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        result = await llm.chat(
            user_message=req.message,
            history=[m.model_dump() for m in req.history],
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatResponse(**result)


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    try:
        history = [m.model_dump() for m in req.history]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def event_source():
        try:
            async for event in llm.stream_chat(req.message, history=history):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except RuntimeError as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
