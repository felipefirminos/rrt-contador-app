from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_hora_extra  # noqa: E402


st.set_page_config(page_title="Hora Extra + DSR", page_icon="⏱️")
st.title("Horas Extras + DSR")
st.caption(
    "CLT Arts. 59 (50% normal) e 70 (100% domingos/feriados) • "
    "DSR: Lei 605/49 + Súmula 172 TST"
)

with st.form("he"):
    col1, col2 = st.columns(2)
    with col1:
        salario = st.number_input("Salário base (R$)", min_value=0.01, value=5000.0,
                                  step=100.0, format="%.2f")
        jornada = st.number_input(
            "Jornada mensal (h)", min_value=1, value=220, step=20,
            help="220h = 44h/sem; 180h = 36h/sem; 200h = 40h/sem",
        )
        comissoes = st.number_input("Comissões variáveis (R$)", min_value=0.0, value=0.0,
                                    step=100.0, format="%.2f")
    with col2:
        h_normais = st.number_input("HE em dias normais (qtd)", min_value=0.0, value=10.0,
                                    step=1.0)
        adic_normal = st.number_input("Adicional dias normais (%)", min_value=50.0,
                                      value=50.0, step=5.0,
                                      help="Mínimo 50% (CLT 59); CCT pode ser maior")
        h_feriado = st.number_input("HE em domingos/feriados (qtd)", min_value=0.0,
                                    value=0.0, step=1.0)
        adic_feriado = st.number_input("Adicional feriado (%)", min_value=100.0,
                                       value=100.0, step=10.0,
                                       help="Mínimo 100% (CLT 70)")

    st.markdown("**DSR (opcional)**")
    incluir_dsr = st.checkbox("Calcular DSR sobre HE + comissões", value=True)
    col3, col4 = st.columns(2)
    with col3:
        dias_uteis = st.number_input("Dias úteis no mês", min_value=0, max_value=31,
                                     value=22, step=1, disabled=not incluir_dsr)
    with col4:
        dom_fer = st.number_input("Domingos + feriados no mês", min_value=0, max_value=15,
                                  value=8, step=1, disabled=not incluir_dsr)
    submitted = st.form_submit_button("Calcular", type="primary")

if submitted:
    payload = {
        "salario": salario, "horas_normais": h_normais, "horas_feriado": h_feriado,
        "adicional_normal": adic_normal, "adicional_feriado": adic_feriado,
        "jornada_mensal": int(jornada), "comissoes": comissoes,
    }
    if incluir_dsr:
        payload["dias_uteis"] = int(dias_uteis)
        payload["domingos_feriados"] = int(dom_fer)

    try:
        r = calc_hora_extra(**payload)
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(4)
    cols[0].metric("Hora normal", f"R$ {r['hora_normal']:,.2f}")
    cols[1].metric("HE 50%", f"R$ {r['valor_he_normal']:,.2f}")
    cols[2].metric("HE 100%", f"R$ {r['valor_he_feriado']:,.2f}")
    cols[3].metric("Total HE", f"R$ {r['total_he']:,.2f}")

    if "dsr" in r:
        st.markdown("### DSR sobre verbas variáveis")
        cols2 = st.columns(2)
        cols2[0].metric("Variáveis (HE + comissões)", f"R$ {r['total_variaveis']:,.2f}")
        cols2[1].metric(f"DSR ({r['domingos_feriados']} dom/fer)", f"R$ {r['dsr']:,.2f}")
        st.success(
            f"**Total para folha:** HE + comissões + DSR = "
            f"R$ {r['total_variaveis'] + r['dsr']:,.2f}"
        )

    with st.expander("Detalhe completo"):
        st.json(r)

    st.caption(f"📚 {r['base_legal_he']}")
    if "base_legal_dsr" in r:
        st.caption(f"📚 {r['base_legal_dsr']}")
