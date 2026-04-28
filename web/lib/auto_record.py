"""Sidebar reutilizável para o auto-record middleware (Round K).

Cada página de calc importa e chama `render_sidebar()` no topo do
arquivo. O componente sincroniza `st.session_state[ar_cnpj]` e
`st.session_state[ar_texto]`, que `lib/api._post()` lê automaticamente
para anexar os headers X-Cliente-CNPJ e X-Cliente-Texto em qualquer
chamada /calc/*.

Uso:
    from lib.auto_record import render_sidebar
    render_sidebar()  # Logo após st.set_page_config()
"""
from __future__ import annotations

import streamlit as st


def render_sidebar() -> None:
    """Renderiza o painel de auto-record na sidebar da página atual."""
    with st.sidebar:
        st.divider()
        with st.expander("📚 Auto-record (histórico)", expanded=False):
            st.text_input(
                "CNPJ do cliente",
                key="ar_cnpj",
                placeholder="12.345.678/0001-99",
                help="Quando preenchido, cada cálculo é gravado no histórico do cliente.",
            )
            st.text_input(
                "Descrição (ASCII)",
                key="ar_texto",
                placeholder="ex: DAS Anexo III mar/2025",
                help="Opcional. HTTP headers exigem ASCII.",
            )
            cnpj = (st.session_state.get("ar_cnpj") or "").strip()
            if cnpj:
                st.success(f"✅ ON — gravando como `{cnpj}`")
            else:
                st.caption("Preencha o CNPJ para ativar gravação automática.")
