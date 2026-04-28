from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_icms_st  # noqa: E402
from lib.auto_record import render_sidebar  # noqa: E402


st.set_page_config(page_title="ICMS-ST", page_icon="📦")

render_sidebar()
st.title("ICMS-ST — Substituição Tributária")
st.caption(
    "Antecipação do imposto sobre toda a cadeia (ICMS Convênios + protocolos por UF) • "
    "BC-ST = (valor + despesas) × (1 + MVA/100); ICMS-ST = BC × alíq_interna - ICMS_próprio"
)

with st.form("icms_st"):
    col1, col2 = st.columns(2)
    with col1:
        valor_op = st.number_input(
            "Valor da operação (R$)", min_value=0.01, value=500.0,
            step=100.0, format="%.2f",
        )
        mva = st.number_input(
            "MVA — Margem de Valor Agregado (%)", min_value=0.0, max_value=300.0,
            value=40.0, step=5.0,
            help="Definida em Convênio ICMS específico do produto/segmento",
        )
        aliq_origem = st.number_input(
            "Alíquota interna ORIGEM (%)", min_value=0.0, max_value=30.0,
            value=12.0, step=0.5,
            help="Alíquota interestadual aplicada na NF de origem",
        )
        aliq_interna = st.number_input(
            "Alíquota interna DESTINO (%)", min_value=0.0, max_value=30.0,
            value=18.0, step=0.5,
        )
    with col2:
        frete = st.number_input("Frete (R$)", min_value=0.0, value=0.0, format="%.2f")
        seguro = st.number_input("Seguro (R$)", min_value=0.0, value=0.0, format="%.2f")
        outras = st.number_input("Outras despesas (R$)", min_value=0.0, value=0.0, format="%.2f")

    submitted = st.form_submit_button("Calcular ICMS-ST", type="primary")

if submitted:
    try:
        r = calc_icms_st(
            valor_operacao=valor_op, mva=mva,
            aliquota_interna=aliq_interna, aliquota_origem=aliq_origem,
            frete=frete, seguro=seguro, outras_despesas=outras,
        )
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(3)
    cols[0].metric("BC-ST", f"R$ {r['base_st']:,.2f}", f"MVA {r['mva_pct']}%")
    cols[1].metric(
        "ICMS próprio (crédito)",
        f"R$ {r['icms_proprio']:,.2f}",
        f"{r['aliquota_origem_pct']}%",
    )
    cols[2].metric(
        "ICMS-ST a recolher",
        f"R$ {r['icms_st']:,.2f}",
        delta=None if r["icms_st"] == r["icms_st_bruto"] else f"bruto: R$ {r['icms_st_bruto']:,.2f}",
    )

    if r["tem_restituicao"]:
        st.warning(
            f"⚠️ **ICMS-ST bruto NEGATIVO** (R$ {r['icms_st_bruto']:,.2f}). "
            f"Não há ST a recolher; possível direito a ressarcir/restituir "
            f"R$ {r['valor_restituicao']:,.2f} — verifique legislação estadual de origem."
        )

    st.markdown("### Composição")
    rows = [
        {"Componente": "Valor da operação", "Valor": f"R$ {r['valor_operacao']:,.2f}"},
        {"Componente": "Despesas acessórias (frete + seguro + outras)",
         "Valor": f"R$ {r['despesas_acessorias']:,.2f}"},
        {"Componente": f"× (1 + MVA {r['mva_pct']}%)", "Valor": "—"},
        {"Componente": "**= BC-ST**", "Valor": f"**R$ {r['base_st']:,.2f}**"},
        {"Componente": f"× alíq. interna destino {r['aliquota_interna_pct']}%",
         "Valor": f"R$ {round(r['base_st'] * r['aliquota_interna_pct'] / 100, 2):,.2f}"},
        {"Componente": f"− ICMS próprio (alíq origem {r['aliquota_origem_pct']}%)",
         "Valor": f"R$ {r['icms_proprio']:,.2f}"},
        {"Componente": "**= ICMS-ST**", "Valor": f"**R$ {r['icms_st']:,.2f}**"},
    ]
    st.table(rows)

    with st.expander("Detalhe completo"):
        st.json(r)
