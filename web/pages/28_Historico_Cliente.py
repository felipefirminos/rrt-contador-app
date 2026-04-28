from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import (  # noqa: E402
    APIError,
    historico_buscar_tag, historico_estatisticas, historico_feedback,
    historico_listar_cliente, historico_padroes, historico_registrar,
    historico_sugestoes,
)


st.set_page_config(page_title="Histórico por Cliente", page_icon="📚", layout="wide")
st.title("Histórico por Cliente / CNPJ")
st.caption(
    "Persistência local SQLite • Histórico FIFO 500/cliente • "
    "Detector de padrões + Sugestões proativas (calendário fiscal)"
)

tabs = st.tabs([
    "📝 Registrar",
    "👤 Por cliente",
    "🔍 Buscar por tag",
    "📊 Estatísticas",
    "🧠 Padrões + Sugestões",
])

with tabs[0]:
    st.markdown("Registra uma interação cliente↔contador para consulta futura.")
    with st.form("registrar"):
        col1, col2 = st.columns(2)
        with col1:
            cnpj = st.text_input("CNPJ", placeholder="12.345.678/0001-99")
            origem = st.selectbox("Origem", ["direto", "gestta", "whatsapp", "api"])
        with col2:
            tags_raw = st.text_input(
                "Tags (separadas por vírgula)", placeholder="rescisao,484-A",
            )
            fluxo = st.text_input(
                "Fluxo (classificação, opcional)", placeholder="Trabalhista",
            )
        texto = st.text_area("Texto da interação", height=120,
                             placeholder="Cliente perguntou sobre rescisão por acordo mútuo de 5 anos...")
        resultado_raw = st.text_area(
            "Resultado bruto (JSON, opcional)", height=80,
            placeholder='{"total_liquido": 32622.23, "multa_fgts": 12000}',
        )
        if st.form_submit_button("Registrar interação", type="primary"):
            if not cnpj or not texto:
                st.error("CNPJ e texto são obrigatórios.")
            else:
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
                payload = {
                    "cnpj": cnpj, "texto": texto, "tags": tags,
                    "origem": origem,
                    "classificacao": {"fluxo": fluxo} if fluxo else None,
                }
                if resultado_raw.strip():
                    import json as _json
                    try:
                        payload["resultado"] = _json.loads(resultado_raw)
                    except _json.JSONDecodeError:
                        st.warning("JSON do resultado inválido — descartado.")
                try:
                    r = historico_registrar(**payload)
                    st.success(f"✅ Registrado — ID `{r['id']}`")
                    st.json(r)
                except APIError as e:
                    st.error(str(e))

    st.divider()
    st.markdown("#### Avaliar interação existente")
    with st.form("feedback"):
        col1, col2 = st.columns([2, 1])
        with col1:
            interacao_id = st.text_input("ID da interação", placeholder="12345678000199_000003")
        with col2:
            avaliacao = st.selectbox("Avaliação", ["aprovado", "rejeitado", "ajustado"])
        correcao = st.text_area("Correção (obrigatório se 'ajustado')", height=80)
        if st.form_submit_button("Registrar feedback"):
            payload = {"interacao_id": interacao_id, "avaliacao": avaliacao}
            if correcao.strip():
                payload["correcao"] = correcao
            try:
                r = historico_feedback(**payload)
                st.success("Feedback registrado.")
                st.json(r)
            except APIError as e:
                st.error(str(e))

with tabs[1]:
    st.markdown("Lista as últimas N interações de um cliente.")
    col1, col2 = st.columns([3, 1])
    with col1:
        cnpj_q = st.text_input("CNPJ (com ou sem máscara)", key="cnpj_listar",
                                placeholder="12.345.678/0001-99")
    with col2:
        limite = st.number_input("Limite", min_value=10, max_value=500, value=100, step=10)

    if st.button("Listar interações") and cnpj_q:
        try:
            r = historico_listar_cliente(cnpj_q.replace(".", "").replace("/", "").replace("-", ""),
                                          limite=int(limite))
        except APIError as e:
            st.error(str(e))
            st.stop()
        st.caption(f"**{r['total']}** interação(ões) para CNPJ {r['cnpj']}")
        rows = []
        for it in r["interacoes"]:
            avaliacao = it.get("avaliacao") or "—"
            ic = {
                "aprovado": "✅", "rejeitado": "❌", "ajustado": "🟡",
            }.get(avaliacao, "⏳")
            rows.append({
                "ID": it["id"][-8:],
                "Data": it["timestamp"][:10],
                "Avaliação": f"{ic} {avaliacao}",
                "Tags": ", ".join(it.get("tags", []))[:30],
                "Origem": it.get("origem", ""),
                "Texto (início)": (it.get("texto") or "")[:80],
            })
        if rows:
            st.table(rows)
        with st.expander("Detalhe completo (JSON)"):
            st.json(r)

with tabs[2]:
    st.markdown("Filtra interações por tag (ex: `rescisao`, `simples`, `das`).")
    col1, col2 = st.columns(2)
    with col1:
        tag_q = st.text_input("Tag", placeholder="rescisao")
    with col2:
        cnpj_filtro = st.text_input("CNPJ (opcional, restringe)",
                                     placeholder="(deixe em branco = global)")
    if st.button("Buscar", key="buscar_tag") and tag_q:
        try:
            r = historico_buscar_tag(
                tag=tag_q,
                cnpj=cnpj_filtro or None,
                limite=50,
            )
        except APIError as e:
            st.error(str(e))
            st.stop()
        st.caption(f"**{r['total']}** match(es) para tag `{r['query']}`")
        rows = [
            {"ID": it["id"][-8:], "Data": it["timestamp"][:10],
             "Tags": ", ".join(it.get("tags", []))[:40],
             "Texto": (it.get("texto") or "")[:100]}
            for it in r["interacoes"]
        ]
        if rows:
            st.table(rows)

with tabs[3]:
    st.markdown("Estatísticas globais ou por cliente.")
    cnpj_stats = st.text_input("CNPJ (vazio = global)", key="cnpj_stats")
    if st.button("Atualizar estatísticas"):
        try:
            r = historico_estatisticas(cnpj_stats or None)
        except APIError as e:
            st.error(str(e))
            st.stop()
        if r["total"] == 0:
            st.info("Sem interações ainda.")
        else:
            cols = st.columns(4)
            cols[0].metric("Total", r["total"])
            if r.get("clientes_ativos") is not None:
                cols[1].metric("Clientes ativos", r["clientes_ativos"])
            cols[2].metric("Taxa aprovação",
                            f"{r.get('taxa_aprovacao_pct', '—')}%"
                            if r.get("taxa_aprovacao_pct") is not None else "—")
            av = r.get("avaliacoes", {})
            cols[3].metric("Pendentes", av.get("pendente", 0))

            st.markdown("### Avaliações")
            st.json(r["avaliacoes"])

            if r.get("top_tags"):
                st.markdown("### Top 10 tags")
                rows = [{"Tag": t, "Ocorrências": n} for t, n in r["top_tags"]]
                st.table(rows)

            if r.get("top_fluxos"):
                st.markdown("### Top fluxos (classificação)")
                rows = [{"Fluxo": f, "Ocorrências": n} for f, n in r["top_fluxos"]]
                st.table(rows)

with tabs[4]:
    st.markdown(
        "**Padrões** detecta sazonalidade (correlação com calendário fiscal), "
        "padrões de correção e clusters de tags. **Sugestões** proativas inclui "
        "alertas de prazo, lembretes recorrentes e antecipações."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🔬 Padrões")
        cnpj_pad = st.text_input("CNPJ (vazio = global)", key="cnpj_pad")
        if st.button("Detectar padrões"):
            try:
                r = historico_padroes(cnpj_pad or None)
            except APIError as e:
                st.error(str(e))
                st.stop()
            if r.get("total", 0) == 0:
                st.warning(r.get("mensagem", "Sem dados."))
            else:
                saz = r.get("sazonalidade", {})
                if saz.get("picos"):
                    st.markdown("**Picos sazonais detectados:**")
                    for p in saz["picos"]:
                        meses = ["Jan","Fev","Mar","Abr","Mai","Jun",
                                 "Jul","Ago","Set","Out","Nov","Dez"]
                        cf = "; ".join(p.get("calendario_fiscal", []))
                        st.warning(
                            f"📈 **{meses[p['mes']-1]}** — {p['total']} interações "
                            f"({p['ratio']}× média). Calendário: {cf}"
                        )
                with st.expander("Detalhe completo"):
                    st.json(r)

    with col2:
        st.markdown("### 💡 Sugestões proativas")
        cnpj_sug = st.text_input("CNPJ (vazio = global)", key="cnpj_sug")
        regime_sug = st.selectbox("Regime",
                                   ["", "simples", "presumido", "lucro_real", "mei"])
        dias_ant = st.number_input("Dias de antecedência", min_value=1,
                                    max_value=60, value=7)
        if st.button("Gerar sugestões"):
            try:
                r = historico_sugestoes(
                    cnpj=cnpj_sug or None,
                    regime=regime_sug or None,
                    dias_antecedencia=int(dias_ant),
                )
            except APIError as e:
                st.error(str(e))
                st.stop()

            resumo = r.get("resumo", {})
            cols = st.columns(4)
            cols[0].metric("Total", resumo.get("total_sugestoes", 0))
            cols[1].metric("Críticos", resumo.get("criticos", 0))
            cols[2].metric("Alertas", resumo.get("alertas", 0))
            cols[3].metric("Lembretes", resumo.get("lembretes", 0))

            for a in r.get("alertas_prazo", []):
                urg = a.get("urgencia", "media")
                ic = {"critico": "🚨", "alto": "🟠", "media": "🟡"}.get(urg, "ℹ️")
                st.markdown(f"{ic} **{a.get('obrigacao', '?')}** — {a.get('mensagem', '')}")

            if r.get("lembretes_recorrentes"):
                st.markdown("**Lembretes recorrentes:**")
                for lm in r["lembretes_recorrentes"]:
                    st.caption(f"• {lm.get('descricao', '')}")

            with st.expander("Detalhe completo"):
                st.json(r)
