from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_decimo_terceiro  # noqa: E402


st.set_page_config(page_title="13º Salário", page_icon="🎁")
st.title("13º Salário")
st.caption("Lei 4.090/1962 + CF Art. 7° VIII • 1ª parcela até 30/nov • 2ª até 20/dez")

with st.form("13o"):
    col1, col2 = st.columns(2)
    with col1:
        salario = st.number_input("Salário bruto (R$)", min_value=0.01, value=5000.0,
                                  step=100.0, format="%.2f")
        meses = st.number_input("Meses trabalhados (avos)", min_value=1, max_value=12,
                                value=12, step=1, help="Proporcional se contratado durante o ano")
    with col2:
        deps = st.number_input("Dependentes (IRRF)", min_value=0, value=0, step=1)
        pensao = st.number_input("Pensão alimentícia (R$)", min_value=0.0, value=0.0,
                                 step=100.0, format="%.2f")
    submitted = st.form_submit_button("Calcular 13º", type="primary")

if submitted:
    try:
        r = calc_decimo_terceiro(
            salario_bruto=salario, meses_trabalhados=int(meses),
            num_dependentes=int(deps), pensao_alimenticia=pensao,
        )
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(3)
    cols[0].metric("13° bruto", f"R$ {r['decimo_terceiro_bruto']:,.2f}")
    cols[1].metric("Total líquido", f"R$ {r['total_liquido']:,.2f}")
    cols[2].metric("FGTS (8%)", f"R$ {r['total_fgts_13o']:,.2f}")

    st.markdown("### Parcelas")
    rows = [
        {"Parcela": "1ª (até 30/nov, sem deduções)", "Valor": f"R$ {r['primeira_parcela']:,.2f}",
         "FGTS": f"R$ {r['fgts_primeira_parcela']:,.2f}"},
        {"Parcela": "2ª (até 20/dez, após INSS+IRRF)", "Valor": f"R$ {r['segunda_parcela']:,.2f}",
         "FGTS": f"R$ {r['fgts_segunda_parcela']:,.2f}"},
    ]
    st.table(rows)

    st.markdown("### Descontos (calculados sobre o 13° bruto completo)")
    cols2 = st.columns(2)
    cols2[0].metric("INSS", f"R$ {r['inss_sobre_13o']:,.2f}")
    cols2[1].metric("IRRF", f"R$ {r['irrf_sobre_13o']:,.2f}")

    with st.expander("Detalhe completo"):
        st.json(r)
