from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_difal  # noqa: E402


st.set_page_config(page_title="DIFAL ICMS", page_icon="🚛")
st.title("DIFAL — Diferencial de Alíquota ICMS")
st.caption(
    "EC 87/2015 + LC 190/2022 • Operação interestadual destinada a "
    "consumidor final não-contribuinte • 100% para o estado de DESTINO desde 2022"
)

with st.expander("ℹ️ Alíquotas interestaduais — referência rápida"):
    st.markdown(
        """
        | Origem → Destino | Alíquota interestadual |
        |---|---|
        | Sul/SE (exc. ES) → Norte/Nordeste/CO/ES | **7%** |
        | Demais combinações | **12%** |
        | Importados (CST início 1, 2, 3, 8) | **4%** |
        """
    )

with st.form("difal"):
    col1, col2 = st.columns(2)
    with col1:
        valor_op = st.number_input(
            "Valor da operação (R$)", min_value=0.01, value=1000.0,
            step=100.0, format="%.2f",
        )
        aliq_dest = st.number_input(
            "Alíquota interna do DESTINO (%)", min_value=0.0, max_value=30.0,
            value=18.0, step=0.5,
        )
        aliq_inter = st.selectbox(
            "Alíquota interestadual",
            [4.0, 7.0, 12.0],
            index=1,
            format_func=lambda x: f"{x}% — {'Importados' if x==4 else 'N/NE/CO/ES' if x==7 else 'Demais'}",
        )
    with col2:
        frete = st.number_input("Frete (R$)", min_value=0.0, value=0.0, format="%.2f")
        seguro = st.number_input("Seguro (R$)", min_value=0.0, value=0.0, format="%.2f")
        outras = st.number_input("Outras despesas (R$)", min_value=0.0, value=0.0, format="%.2f")

    submitted = st.form_submit_button("Calcular DIFAL", type="primary")

if submitted:
    try:
        r = calc_difal(
            valor_operacao=valor_op,
            aliquota_destino=aliq_dest,
            aliquota_interestadual=aliq_inter,
            frete=frete, seguro=seguro, outras_despesas=outras,
        )
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(3)
    cols[0].metric("Base de cálculo", f"R$ {r['base_calculo']:,.2f}")
    cols[1].metric(
        "Diferencial",
        f"{r['diferencial_aliquota_pct']:.2f}%",
        f"({r['aliquota_destino_pct']}% - {r['aliquota_interestadual_pct']}%)",
    )
    cols[2].metric("DIFAL", f"R$ {r['difal']:,.2f}")

    st.success(
        "**100% do DIFAL para o estado de DESTINO** (EC 87/2015 art. 99, §3, "
        "regra desde 2022 — antes havia partilha gradativa entre origem e destino)."
    )

    with st.expander("Detalhe completo"):
        st.json(r)
