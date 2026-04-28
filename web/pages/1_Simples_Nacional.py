from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_simples_das, sugerir_anexo_engenharia  # noqa: E402
from lib.auto_record import render_sidebar  # noqa: E402


st.set_page_config(page_title="Simples Nacional — DAS", page_icon="📊")

render_sidebar()
st.title("DAS — Simples Nacional")
st.caption("LC 123/2006, Arts. 18-19 • LC 155/2016 • Resolução CGSN 140/2018")

with st.expander("🔎 Não sabe o Anexo? — Engenharia/arquitetura/construção (SKILL.md §5)"):
    st.caption(
        "CNAEs ambíguos (71.12, 71.11, 43.29) podem ser **Anexo III/V c/ Fator R** "
        "(consultoria, projetos, laudos) **OU Anexo IV** (execução de obras / cessão "
        "de mão de obra). Use o sugeridor antes de enquadrar."
    )
    s_col1, s_col2, s_col3 = st.columns(3)
    with s_col1:
        cnae_in = st.text_input("CNAE", value="71.12-0-00", key="sug_cnae")
    with s_col2:
        exec_obras = st.checkbox("Executa obras / serviços de campo", key="sug_obras")
    with s_col3:
        cessao = st.checkbox("Cessão de mão de obra ao tomador", key="sug_cessao")
    if st.button("Sugerir anexo", key="sug_btn"):
        try:
            sug = sugerir_anexo_engenharia(cnae_in, exec_obras, cessao)
            anexo_sug = sug.get("anexo_sugerido")
            if anexo_sug == "IV":
                st.error(f"**Anexo {anexo_sug}** — {sug['motivo']}")
            elif anexo_sug:
                st.success(f"**Anexo {anexo_sug}** — {sug['motivo']}")
            else:
                st.warning(sug["motivo"])
        except APIError as e:
            st.error(str(e))

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
