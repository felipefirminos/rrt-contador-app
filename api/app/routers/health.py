from __future__ import annotations

from fastapi import APIRouter

from app.config import SCRIPTS_DIR, SKILL_MD, settings


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "engine_scripts_dir": str(SCRIPTS_DIR),
        "engine_present": SCRIPTS_DIR.exists(),
        "skill_md_present": SKILL_MD.exists(),
        "anthropic_configured": bool(settings.anthropic_api_key),
        "model": settings.anthropic_model,
    }
