from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, resumo_mei  # noqa: E402
from lib.auto_record import render_sidebar  # noqa: E402


st.set_page_config(page_title="MEI", page_icon="🧑‍💼")

render_sidebar()
st.title("MEI — Resumo Completo")
st.caption(
    "LC 123/2006 + LC 188/2021 + Resolução CGSN 140/2018 • "
    "DAS + faturamento + obrigações + situação de enquadramento"
)

st.warning(
    "ℹ️ **PLP 108/21** (limite R$130K + 2 empregados) tem urgência aprovada (mar/2026), "
    "mas **NÃO está em vigor**. Limite atual: R$ 81.000/ano (R$ 251.600 caminhoneiro)."
)

ATIVIDADES = {
    "Comércio e/ou Indústria": "comercio",
    "Serviços": "servicos",
    "Comércio + Serviços": "comercio_servicos",
    "Caminhoneiro (LC 188/2021)": "caminhoneiro",
}

with st.form("mei"):
    col1, col2, col3 = st.columns(3)
    with col1:
        atividade_label = st.selectbox("Atividade", list(ATIVIDADES.keys()))
    with col2:
        receita = st.number_input(
            "Receita bruta anual (R$)", min_value=0.0, value=60000.0,
            step=5000.0, format="%.2f",
        )
    with col3:
        meses = st.number_input(
            "Meses de atividade", min_value=1, max_value=12, value=12, step=1,
            help="Limite proporcionaliza se < 12",
        )
    submitted = st.form_submit_button("Calcular MEI", type="primary")

if submitted:
    try:
        r = resumo_mei(
            atividade=ATIVIDADES[atividade_label],
            receita_bruta_anual=receita,
            meses_atividade=int(meses),
        )
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(4)
    cols[0].metric("DAS mensal", f"R$ {r['das_mensal']:,.2f}")
    cols[1].metric("DAS anual (12×)", f"R$ {r['das_anual']:,.2f}")
    cols[2].metric("Limite proporcional", f"R$ {r['limite_proporcional']:,.2f}")
    cols[3].metric("Margem restante", f"R$ {r['margem_restante']:,.2f}")

    if r["enquadrado"]:
        st.success(f"✅ Enquadrado — situação: {r['situacao']}")
    else:
        st.error(f"⚠️ FORA do MEI — {r['situacao']}")
        if r.get("orientacao"):
            st.warning(f"**Orientação:** {r['orientacao']}")

    st.markdown("### Composição do DAS")
    rows = [
        {"Componente": "INSS", "Valor": f"R$ {r['inss_mensal']:,.2f}"},
        {"Componente": "ICMS", "Valor": f"R$ {r['icms_mensal']:,.2f}"},
        {"Componente": "ISS", "Valor": f"R$ {r['iss_mensal']:,.2f}"},
        {"Componente": "**TOTAL**", "Valor": f"**R$ {r['das_mensal']:,.2f}**"},
    ]
    st.table(rows)

    st.markdown("### Obrigações")
    obrig_rows = []
    for o in r.get("obrigacoes", []):
        obrig_rows.append({
            "Obrigação": o["obrigacao"], "Periodicidade": o["periodicidade"],
            "Prazo": o["prazo"], "Descrição": o["descricao"],
        })
    st.table(obrig_rows)

    if r.get("alertas"):
        st.markdown("### Alertas")
        for a in r["alertas"]:
            st.info(a)

    with st.expander("Detalhe completo"):
        st.json(r)

    st.caption(f"📚 {r['base_legal']}")
