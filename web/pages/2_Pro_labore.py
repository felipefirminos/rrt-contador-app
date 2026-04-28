from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_prolabore  # noqa: E402
from lib.auto_record import render_sidebar  # noqa: E402


st.set_page_config(page_title="Pró-labore", page_icon="💰")

render_sidebar()
st.title("Pró-labore")
st.caption("INSS sócio 11% (IN RFB 971/2009 art. 65) + CPP 20% conforme regime + IRRF (Lei 15.270/2025)")

REGIMES = {
    "Lucro Presumido": "presumido",
    "Lucro Real": "lucro_real",
    "Simples — Anexo IV (CPP separada)": "simples_iv",
    "Simples — Anexos I/III/V (CPP no DAS)": "simples_i_iii_v",
    "Simples — Anexo I": "simples_i",
    "Simples — Anexo II": "simples_ii",
    "Simples — Anexo III": "simples_iii",
    "Simples — Anexo V": "simples_v",
}

with st.form("prolabore_form"):
    col1, col2 = st.columns(2)
    with col1:
        valor_bruto = st.number_input(
            "Valor bruto do pró-labore (R$/mês)",
            min_value=0.0, value=5000.0, step=100.0, format="%.2f",
        )
        regime_label = st.selectbox("Regime tributário", list(REGIMES.keys()))
    with col2:
        num_dependentes = st.number_input("Nº dependentes (IRRF)", min_value=0, value=0, step=1)
        pensao = st.number_input(
            "Pensão alimentícia (R$/mês)", min_value=0.0, value=0.0, step=100.0, format="%.2f",
        )
    submitted = st.form_submit_button("Calcular", type="primary")

if submitted:
    try:
        r = calc_prolabore(valor_bruto, REGIMES[regime_label], int(num_dependentes), pensao)
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(4)
    cols[0].metric("Valor líquido", f"R$ {r['valor_liquido']:,.2f}")
    cols[1].metric("INSS sócio (11%)", f"R$ {r['inss_socio']:,.2f}")
    cols[2].metric("IRRF", f"R$ {r['irrf']:,.2f}")
    cols[3].metric("Encargo total", f"{r['encargo_total_pct']:.1f}%")

    st.markdown("### Custo para a empresa")
    cols2 = st.columns(3)
    cols2[0].metric("CPP patronal (20%)", f"R$ {r['inss_patronal']:,.2f}",
                    help="0 se CPP já incluída no DAS")
    cols2[1].metric("Custo mensal", f"R$ {r['custo_empresa_mensal']:,.2f}")
    cols2[2].metric("Custo anual", f"R$ {r['custo_empresa_anual']:,.2f}")

    if r.get("alertas"):
        for a in r["alertas"]:
            st.warning(a)

    if r.get("cpp_inclusa_no_das"):
        st.info("ℹ️ CPP patronal já incluída no DAS — não recolha 20% separadamente.")

    with st.expander("Detalhes do cálculo", expanded=False):
        st.json(r)

    st.caption(f"📚 {r['base_legal']}")
