from __future__ import annotations

import json
import os
from typing import Any, Iterator

import httpx


API_BASE = os.environ.get("RRT_API_BASE", "http://127.0.0.1:8765")


class APIError(Exception):
    pass


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        r = httpx.post(f"{API_BASE}{path}", json=payload, timeout=60.0)
    except httpx.ConnectError as exc:
        raise APIError(
            f"Sem conexão com a API em {API_BASE}. "
            "Suba o backend com `./scripts/dev.sh` ou `cd api && uvicorn app.main:app --reload --port 8765`."
        ) from exc
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise APIError(f"{r.status_code}: {detail}")
    return r.json()


def health() -> dict[str, Any]:
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=3.0)
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"status": "down", "error": str(exc)}


def calc_simples_das(anexo: str, rbt12: float, receita_mes: float, folha12: float = 0.0) -> dict:
    return _post("/calc/simples-das", {
        "anexo": anexo, "rbt12": rbt12, "receita_mes": receita_mes, "folha12": folha12,
    })


def sugerir_anexo_engenharia(cnae: str | None = None, executa_obras: bool = False,
                             cessao_mao_obra: bool = False) -> dict:
    return _post("/calc/sugerir-anexo-engenharia", {
        "cnae": cnae, "executa_obras": executa_obras, "cessao_mao_obra": cessao_mao_obra,
    })


def calc_prolabore(valor_bruto: float, regime: str, num_dependentes: int = 0,
                   pensao_alimenticia: float = 0.0) -> dict:
    return _post("/calc/prolabore", {
        "valor_bruto": valor_bruto, "regime": regime,
        "num_dependentes": num_dependentes, "pensao_alimenticia": pensao_alimenticia,
    })


def calc_comparativo(**kwargs) -> dict:
    return _post("/calc/comparativo-regimes", kwargs)


def calc_rescisao(**kwargs) -> dict:
    return _post("/calc/rescisao", kwargs)


def calc_folha_batch(empregados: list[dict[str, Any]], regime: str = "presumido_real",
                     competencia: str | None = None, rat_pct: float = 2.0,
                     fap: float = 1.0) -> dict:
    return _post("/calc/folha-batch", {
        "empregados": empregados, "regime": regime, "competencia": competencia,
        "rat_pct": rat_pct, "fap": fap,
    })


def calc_distribuicao_lucros(**kwargs) -> dict:
    return _post("/calc/distribuicao-lucros", kwargs)


def chat(message: str, history: list[dict[str, str]]) -> dict:
    return _post("/chat", {"message": message, "history": history})


def chat_stream(message: str, history: list[dict[str, str]]) -> Iterator[dict[str, Any]]:
    """Stream Server-Sent Events from /chat/stream."""
    try:
        with httpx.stream(
            "POST",
            f"{API_BASE}/chat/stream",
            json={"message": message, "history": history},
            timeout=120.0,
        ) as r:
            if r.status_code >= 400:
                raise APIError(f"{r.status_code}: {r.read().decode()}")
            for line in r.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                try:
                    yield json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
    except httpx.ConnectError as exc:
        raise APIError(f"Sem conexão com a API em {API_BASE}.") from exc
