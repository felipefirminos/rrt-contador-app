"""Anthropic SDK wrapper for the RRT Q&A layer.

The skill's governance (SKILL.md + reference markdown) is loaded once and sent
as a cached system prompt. The calculators are exposed as tools, so the model
can run an actual `calc_simples_das` call instead of guessing numbers.

This is a server-only module — the API key never leaves the backend.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic

from app.config import REFERENCES_DIR, SKILL_MD, settings
from app.services.engine import CALCULATOR_TOOLS, TOOL_DISPATCH


@lru_cache(maxsize=1)
def _system_prompt() -> str:
    parts: list[str] = []
    if SKILL_MD.exists():
        parts.append("# SKILL.md (governança RRT v6.1.1)\n\n" + SKILL_MD.read_text(encoding="utf-8"))
    if REFERENCES_DIR.exists():
        for md in sorted(REFERENCES_DIR.glob("*.md")):
            parts.append(f"\n\n# references/{md.name}\n\n" + md.read_text(encoding="utf-8"))
    parts.append(
        "\n\n# Instruções operacionais\n\n"
        "- Você está sendo executado como serviço interno da RRT Contabilidade.\n"
        "- Para QUALQUER cálculo (DAS, pró-labore, comparativo), use os tools disponíveis. "
        "NUNCA improvise números — sempre chame a calculadora.\n"
        "- Cite base legal e classifique a criticidade (BAIXA/MÉDIA/ALTA/CRÍTICA) conforme SKILL.md.\n"
        "- Respostas em português brasileiro, diretas, formato markdown."
    )
    return "".join(parts)


def _client() -> AsyncAnthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY não configurada. Defina em .env ou variável de ambiente."
        )
    return AsyncAnthropic(api_key=settings.anthropic_api_key)


def _build_messages(history: list[dict[str, Any]], user_message: str) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = []
    for h in history:
        role = h.get("role")
        content = h.get("content")
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": user_message})
    return msgs


def _system_blocks() -> list[dict[str, Any]]:
    return [
        {
            "type": "text",
            "text": _system_prompt(),
            "cache_control": {"type": "ephemeral"},
        }
    ]


async def chat(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    max_tool_iterations: int = 5,
) -> dict[str, Any]:
    """Single-turn chat with tool-use loop. Returns final assistant text + trace."""
    client = _client()
    messages = _build_messages(history or [], user_message)
    tool_calls_trace: list[dict[str, Any]] = []

    for _ in range(max_tool_iterations):
        resp = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=_system_blocks(),
            tools=CALCULATOR_TOOLS,
            messages=messages,
        )

        if resp.stop_reason != "tool_use":
            text_blocks = [b.text for b in resp.content if b.type == "text"]
            return {
                "reply": "\n".join(text_blocks).strip(),
                "tool_calls": tool_calls_trace,
                "usage": {
                    "input_tokens": resp.usage.input_tokens,
                    "output_tokens": resp.usage.output_tokens,
                    "cache_read_input_tokens": getattr(resp.usage, "cache_read_input_tokens", 0),
                    "cache_creation_input_tokens": getattr(resp.usage, "cache_creation_input_tokens", 0),
                },
            }

        messages.append({"role": "assistant", "content": resp.content})
        tool_results: list[dict[str, Any]] = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            fn = TOOL_DISPATCH.get(block.name)
            try:
                result = fn(**block.input) if fn else {"erro": f"Tool desconhecido: {block.name}"}
                is_error = "erro" in result
            except Exception as exc:  # noqa: BLE001 — surface any calc failure to the model
                result = {"erro": str(exc)}
                is_error = True
            tool_calls_trace.append({"name": block.name, "input": block.input, "result": result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result),
                "is_error": is_error,
            })
        messages.append({"role": "user", "content": tool_results})

    return {
        "reply": "(Limite de iterações de tools atingido — peça para o usuário restringir o pedido.)",
        "tool_calls": tool_calls_trace,
        "usage": {},
    }


async def stream_chat(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """SSE-friendly streaming variant. Yields dicts: {type, ...}.

    Note: when a tool_use is requested, we resolve it server-side then continue
    the stream in a fresh request. Each tool call is reported as a status event.
    """
    client = _client()
    messages = _build_messages(history or [], user_message)

    for _ in range(5):
        async with client.messages.stream(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=_system_blocks(),
            tools=CALCULATOR_TOOLS,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield {"type": "delta", "text": text}
            final = await stream.get_final_message()

        if final.stop_reason != "tool_use":
            yield {
                "type": "done",
                "usage": {
                    "input_tokens": final.usage.input_tokens,
                    "output_tokens": final.usage.output_tokens,
                    "cache_read_input_tokens": getattr(final.usage, "cache_read_input_tokens", 0),
                    "cache_creation_input_tokens": getattr(final.usage, "cache_creation_input_tokens", 0),
                },
            }
            return

        messages.append({"role": "assistant", "content": final.content})
        tool_results: list[dict[str, Any]] = []
        for block in final.content:
            if block.type != "tool_use":
                continue
            fn = TOOL_DISPATCH.get(block.name)
            try:
                result = fn(**block.input) if fn else {"erro": f"Tool desconhecido: {block.name}"}
                is_error = "erro" in result
            except Exception as exc:  # noqa: BLE001
                result = {"erro": str(exc)}
                is_error = True
            yield {"type": "tool_call", "name": block.name, "input": block.input, "result": result}
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result),
                "is_error": is_error,
            })
        messages.append({"role": "user", "content": tool_results})

    yield {"type": "done", "usage": {}}
