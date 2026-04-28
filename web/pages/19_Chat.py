from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, chat_stream, health  # noqa: E402


st.set_page_config(page_title="Q&A com LLM", page_icon="💬", layout="wide")
st.title("Q&A com LLM")
st.caption(
    "Assistente RRT v6.1.1 (Claude Opus 4.7) — SKILL.md + referências cacheadas, "
    "calculadoras expostas como tools."
)

h = health()
if not h.get("anthropic_configured"):
    st.error(
        "ANTHROPIC_API_KEY não configurada no backend. "
        "Crie um `.env` na raiz do projeto com `ANTHROPIC_API_KEY=sk-...` e reinicie a API."
    )
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("Sessão")
    if st.button("🗑️ Limpar conversa", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption("Exemplos:")
    examples = [
        "Empresa de engenharia consultiva, RBT12 R$ 1,2M, receita do mês R$ 100K, folha 12 meses R$ 350K. Qual o DAS?",
        "Compare os regimes para uma empresa de serviços com R$ 2,4M/ano, margem 25%, 4 empregados a R$ 4K, 1 sócio com pró-labore de R$ 8K e distribuição de R$ 30K/mês.",
        "Como calcular o INSS de um sócio que recebe R$ 12.000 de pró-labore? Cite a base legal.",
        "No Anexo V do Simples, devo recolher CPP separada sobre o pró-labore?",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{hash(ex)}", use_container_width=True):
            st.session_state.pending = ex
            st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("tool_calls"):
            with st.expander(f"🔧 {len(msg['tool_calls'])} tool call(s)", expanded=False):
                for tc in msg["tool_calls"]:
                    st.markdown(f"**{tc['name']}**")
                    st.json({"input": tc["input"], "result": tc["result"]})

prompt = st.chat_input("Pergunte sobre tributário, trabalhista, societário…")
if "pending" in st.session_state:
    prompt = st.session_state.pop("pending")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        tool_log: list[dict] = []
        buf = ""
        try:
            history_for_api = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
            ]
            for ev in chat_stream(prompt, history_for_api):
                t = ev.get("type")
                if t == "delta":
                    buf += ev.get("text", "")
                    placeholder.markdown(buf + "▌")
                elif t == "tool_call":
                    tool_log.append({
                        "name": ev["name"], "input": ev["input"], "result": ev["result"],
                    })
                    placeholder.markdown(buf + f"\n\n_🔧 chamou {ev['name']}…_")
                elif t == "error":
                    placeholder.error(ev.get("message", "erro desconhecido"))
                    break
            placeholder.markdown(buf if buf else "_(sem resposta)_")
        except APIError as e:
            placeholder.error(str(e))
            st.stop()

        if tool_log:
            with st.expander(f"🔧 {len(tool_log)} tool call(s)", expanded=False):
                for tc in tool_log:
                    st.markdown(f"**{tc['name']}**")
                    st.json({"input": tc["input"], "result": tc["result"]})

    st.session_state.messages.append({
        "role": "assistant",
        "content": buf,
        "tool_calls": tool_log,
    })
