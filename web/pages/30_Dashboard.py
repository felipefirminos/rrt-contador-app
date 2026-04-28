"""Dashboard executivo do escritório RRT.

Lê do `/historico/estatisticas` e `/historico/padroes` para gerar
visualizações consolidadas: KPIs, sazonalidade, top clientes, top tags,
distribuição por origem, inconsistências detectadas.

Renderiza somente se houver dados (sem histórico → guia para o usuário
começar a registrar via auto-record sidebar).
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, historico_estatisticas, historico_padroes  # noqa: E402

API_BASE = os.environ.get("RRT_API_BASE", "http://127.0.0.1:8765")


st.set_page_config(page_title="Dashboard Executivo", page_icon="📈", layout="wide")
st.title("Dashboard Executivo — Escritório RRT")
st.caption(
    "Visão consolidada do histórico: KPIs, sazonalidade fiscal, "
    "top clientes/tags, inconsistências detectadas"
)


def _fetch_todas_interacoes() -> list[dict]:
    """Pega todas as interações via endpoint específico do dashboard.

    Não temos endpoint dump — usamos /historico/estatisticas para os agregados
    e /historico/padroes para clusters. Para listas detalhadas (top clientes,
    series temporais), faz queries por CNPJ via session_state cache.

    Para v1 do dashboard, usamos apenas estatísticas globais + padrões globais.
    """
    return []


# ─── Carrega dados ─────────────────────────────────────────────────

try:
    stats = historico_estatisticas(None)
except APIError as e:
    st.error(f"Sem conexão com a API: {e}")
    st.stop()

if stats.get("total", 0) == 0:
    st.warning(
        "📊 **Dashboard vazio.** Nenhuma interação registrada ainda. "
        "Para começar a popular o histórico, qualquer uma das opções abaixo:"
    )
    cols = st.columns(3)
    cols[0].markdown(
        "**Sidebar das pages**: preencha o CNPJ do cliente "
        "no expander 'Auto-record' de qualquer página de calc."
    )
    cols[1].markdown(
        "**Header HTTP**: passe `X-Cliente-CNPJ` em qualquer chamada "
        "`POST /calc/*` (curl, Postman, integrações)."
    )
    cols[2].markdown(
        "**Manual**: vá para a página `Historico Cliente` e use "
        "o form de registro direto."
    )
    st.stop()


# ─── KPIs ─────────────────────────────────────────────────────────

st.markdown("### KPIs")
cols = st.columns(4)
cols[0].metric("Interações totais", f"{stats['total']:,}")
cols[1].metric("Clientes ativos", stats.get("clientes_ativos", 0))
taxa = stats.get("taxa_aprovacao_pct")
cols[2].metric(
    "Taxa de aprovação",
    f"{taxa}%" if taxa is not None else "—",
    help="(aprovados / avaliados). Ignora pendentes.",
)
top_fluxo = stats.get("top_fluxos", [])
cols[3].metric(
    "Fluxo dominante",
    top_fluxo[0][0] if top_fluxo else "—",
    f"{top_fluxo[0][1]}× usado" if top_fluxo else None,
)

# ─── Avaliações ────────────────────────────────────────────────────

avaliacoes = stats.get("avaliacoes", {})
st.markdown("### Avaliações (feedback loop)")
if any(avaliacoes.values()):
    df_aval = pd.DataFrame({
        "estado": list(avaliacoes.keys()),
        "qtd": list(avaliacoes.values()),
    })
    st.bar_chart(df_aval.set_index("estado"))
else:
    st.caption("Sem avaliações registradas ainda.")

# ─── Top tags + Top fluxos lado a lado ────────────────────────────

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### Top 10 tags")
    top_tags = stats.get("top_tags", [])
    if top_tags:
        df_tags = pd.DataFrame(top_tags, columns=["tag", "ocorrencias"])
        st.bar_chart(df_tags.set_index("tag"))
    else:
        st.caption("Sem tags ainda.")

with col_b:
    st.markdown("### Top 10 fluxos (classificação)")
    if top_fluxo:
        df_fluxos = pd.DataFrame(top_fluxo, columns=["fluxo", "ocorrencias"])
        st.bar_chart(df_fluxos.set_index("fluxo"))
    else:
        st.caption("Sem classificação registrada (preencha 'Fluxo' no form).")

# ─── Distribuição por origem ──────────────────────────────────────

st.markdown("### Distribuição por origem")
origens = stats.get("origens", {})
if origens:
    df_orig = pd.DataFrame({
        "origem": list(origens.keys()),
        "interacoes": list(origens.values()),
    })
    st.bar_chart(df_orig.set_index("origem"))

# ─── Padrões e sazonalidade (insights) ────────────────────────────

st.markdown("### Sazonalidade — distribuição mensal")
try:
    padroes = historico_padroes(None)
except APIError as e:
    st.warning(f"Não foi possível carregar padrões: {e}")
    padroes = {}

saz = padroes.get("sazonalidade", {})
dist = saz.get("distribuicao_mensal")
if dist:
    meses_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    df_saz = pd.DataFrame({
        "mes": meses_pt,
        "interacoes": [dist.get(str(i), dist.get(i, 0)) for i in range(1, 13)],
    })
    st.line_chart(df_saz.set_index("mes"))

    media = saz.get("media_mensal", 0)
    cols2 = st.columns(3)
    cols2[0].metric("Média mensal", f"{media:.1f}")
    cols2[1].metric("Picos detectados", len(saz.get("picos", [])))
    cols2[2].metric("Vales detectados", len(saz.get("vales", [])))

    if saz.get("picos"):
        st.markdown("#### 📈 Picos sazonais (>1,5× média)")
        for p in saz["picos"]:
            cf = "; ".join(p.get("calendario_fiscal", []))
            top_t = ", ".join(t for t, _ in p.get("top_tags", [])[:3])
            st.warning(
                f"**{meses_pt[p['mes']-1]}** — {p['total']} interações "
                f"({p['ratio']}× média). Tags: {top_t}. Calendário: {cf}"
            )
else:
    st.caption("Dados insuficientes para análise de sazonalidade.")

# ─── Clusters de tags coocorrentes ────────────────────────────────

clusters = padroes.get("clusters", [])
if clusters:
    st.markdown("### 🔗 Clusters de tags coocorrentes")
    st.caption("Pares de tags que aparecem juntas com frequência (≥3 vezes).")
    rows = [
        {"Tags": " + ".join(c.get("tags", [])),
         "Coocorrências": c.get("coocorrencias", 0)}
        for c in clusters[:10]
    ]
    st.table(rows)

# ─── Padrões de correção (feedback loop) ──────────────────────────

correcao = padroes.get("correcao", {})
if correcao.get("temas_corrigidos"):
    st.markdown("### 🟡 Padrões de correção (próximos pontos de atenção)")
    st.caption(
        "Tags que aparecem em interações 'ajustadas' — vão virar "
        "validações reforçadas no próximo ciclo via /historico/sugestoes."
    )
    rows = [
        {"Tag corrigida": t.get("tag", ""), "Frequência": t.get("freq", 0)}
        for t in correcao["temas_corrigidos"][:10]
    ]
    st.table(rows)

# ─── Footer com link para histórico ───────────────────────────────

st.divider()
st.caption(
    f"Dashboard gerado em tempo real consultando `{API_BASE}`. "
    f"Para granularidade por cliente, use a página `Historico Cliente`."
)
