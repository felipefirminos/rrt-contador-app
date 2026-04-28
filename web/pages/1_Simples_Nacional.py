from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_simples_das  # noqa: E402


st.set_page_config(page_title="Simples Nacional — DAS", page_icon="📊")
st.title("DAS — Simples Nacional")
st.caption("LC 123/2006, Arts. 18-19 • LC 155/2016 • Resolução CGSN 140/2018")

with st.form("simples_form"):
    col1, col2 = st.columns(2)
    with col1:
        anexo = st.selectbox(
            "Anexo",
            ["I", "II", "III", "IV", "V"],
            help="I=comércio, II=indústria, III=serviços c/ Fator R, "
                 "IV=construção/limpeza/vigilância (CPP separada), V=serviços s/ Fator R",
        )
        rbt12 = st.number_input(
            "RBT12 (R$)",
            min_value=1.0, value=780000.0, step=1000.0, format="%.2f",
            help="Receita bruta acumulada nos últimos 12 meses",
        )
    with col2:
        receita_mes = st.number_input(
            "Receita do mês (R$)",
            min_value=0.0, value=85000.0, step=1000.0, format="%.2f",
        )
        folha12 = st.number_input(
            "Folha 12 meses (R$) — incl. pró-labore + encargos",
            min_value=0.0, value=0.0, step=1000.0, format="%.2f",
            help="Obrigatório para Anexo V (Fator R: ≥28% migra para Anexo III)",
        )
    submitted = st.form_submit_button("Calcular DAS", type="primary")

if submitted:
    try:
        r = calc_simples_das(anexo, rbt12, receita_mes, folha12)
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(3)
    cols[0].metric("DAS do mês", f"R$ {r['das']:,.2f}")
    cols[1].metric("Alíquota efetiva", f"{r['aliquota_efetiva_pct']:.2f}%")
    cols[2].metric("Anexo aplicado", r["anexo_aplicado"])

    if r.get("fator_r") is not None:
        st.info(f"**Fator R:** {r['fator_r']}% — {r['nota_fator_r']}")

    if r.get("sublimite_excedido"):
        st.warning(f"⚠️ {r['nota_sublimite']}")

    with st.expander("Detalhes do cálculo", expanded=False):
        st.json(r)

    st.caption(f"📚 {r['base_legal']}")
