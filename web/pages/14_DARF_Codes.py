from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, darf_buscar, darf_consultar, darf_listar_regime  # noqa: E402
from lib.auto_record import render_sidebar  # noqa: E402


st.set_page_config(page_title="Códigos DARF/GPS/DAS", page_icon="🧾", layout="wide")

render_sidebar()
st.title("Códigos DARF / GPS / DAS")
st.caption(
    "Base com 27+ códigos: IRPJ, CSLL, PIS, COFINS, IRRF, CSRF, INSS/GPS, FGTS, "
    "DAS, DAS-MEI, ICMS, ISS, CBS, IBS, DIFAL"
)

tab1, tab2, tab3 = st.tabs(["🔎 Buscar livre", "📋 Por tributo", "📚 Por regime"])

with tab1:
    st.markdown("Busca por número, descrição parcial ou tributo (mínimo 2 caracteres).")
    texto = st.text_input("Texto de busca", value="0561", placeholder="ex: 0561, IRRF, PIS, retenção")
    if st.button("Buscar", key="buscar"):
        if len(texto.strip()) < 2:
            st.warning("Use pelo menos 2 caracteres.")
        else:
            try:
                r = darf_buscar(texto.strip())
            except APIError as e:
                st.error(str(e))
                st.stop()
            results = r.get("resultados", [])
            st.caption(f"{len(results)} resultado(s) encontrados.")
            for it in results:
                with st.container():
                    st.markdown(f"**Código {it.get('codigo')}** — {it.get('descricao')}")
                    cols = st.columns(3)
                    cols[0].caption(f"Tributo: {it.get('tributo')}")
                    cols[1].caption(f"Regime: {', '.join(it.get('regime', []))}")
                    cols[2].caption(f"Periodicidade: {it.get('periodicidade')}")
                    st.caption(f"📅 Vencimento: {it.get('vencimento', '—')}")
                    if it.get("obs"):
                        st.caption(f"📝 {it['obs']}")
                    st.divider()

with tab2:
    st.markdown("Consulta por tributo específico.")
    tributo = st.selectbox(
        "Tributo",
        ["IRPJ", "CSLL", "PIS", "COFINS", "IRRF", "CSRF", "INSS", "FGTS",
         "DAS", "DAS-MEI", "ICMS", "ISS", "CBS", "IBS", "DIFAL"],
    )
    if st.button("Consultar", key="cons"):
        try:
            r = darf_consultar(tributo)
        except APIError as e:
            st.error(str(e))
            st.stop()
        results = r.get("resultados", [])
        st.caption(f"{r.get('total_encontrado', len(results))} código(s) para {tributo}.")
        rows = []
        for it in results:
            rows.append({
                "Código": it.get("codigo"),
                "Descrição": it.get("descricao"),
                "Periodicidade": it.get("periodicidade"),
                "Vencimento": it.get("vencimento"),
                "Regime(s)": ", ".join(it.get("regime", [])),
            })
        st.table(rows)

with tab3:
    st.markdown("Lista todos os códigos aplicáveis a um regime — útil para checklist mensal.")
    regime = st.selectbox(
        "Regime", ["simples", "presumido", "lucro_real", "mei", "dp"],
        format_func=lambda x: {
            "simples": "Simples Nacional", "presumido": "Lucro Presumido",
            "lucro_real": "Lucro Real", "mei": "MEI", "dp": "Departamento Pessoal",
        }.get(x, x),
    )
    if st.button("Listar", key="reg"):
        try:
            r = darf_listar_regime(regime)
        except APIError as e:
            st.error(str(e))
            st.stop()
        codigos = r.get("codigos", [])
        st.caption(f"{len(codigos)} código(s) aplicáveis ao regime {regime}.")
        rows = []
        for it in codigos:
            rows.append({
                "Código": it.get("codigo"),
                "Tributo": it.get("tributo"),
                "Descrição": it.get("descricao"),
                "Periodicidade": it.get("periodicidade"),
                "Vencimento": it.get("vencimento"),
            })
        st.table(rows)
