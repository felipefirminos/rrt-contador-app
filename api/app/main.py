from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import calculators, chat, health, parsers


app = FastAPI(
    title="RRT Contador API",
    version="0.1.0",
    description=(
        "Camada HTTP sobre o engine de cálculos RRT v6.1.1 (Brazilian tax/labor) "
        "+ Q&A LLM com SKILL.md como prompt cacheado."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin, "http://127.0.0.1:8501", "http://localhost:8501"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(calculators.router)
app.include_router(parsers.router)
app.include_router(chat.router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "rrt-contador-api",
        "docs": "/docs",
        "health": "/health",
    }
