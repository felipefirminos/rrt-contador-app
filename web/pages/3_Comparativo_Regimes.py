from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_comparativo  # noqa: E402
from lib.auto_record import render_sidebar  # noqa: E402


st.set_page_config(page_title="Comparativo de Regimes", page_icon="⚖️", layout="wide")

render_sidebar()
st.title("Comparativo de Regimes Tributários")
st.caption("Simples Nacional × Lucro Presumido × Lucro Real (cenário anual completo)")

with st.form("comparativo_form"):
    st.markdown("#### Empresa")
    col1, col2, col3 = st.columns(3)
    with col1:
        receita_anual = st.number_input(
            "Receita anual (R$)", min_value=1.0, value=2400000.0, step=10000.0, format="%.2f",
        )
        atividade = st.selectbox(
            "Atividade (Lucro Presumido)",
            ["servicos", "comercio", "industria", "transporte_carga", "transporte_passageiros"],
        )
    with col2:
        anexo = st.selectbox("Anexo Simples", ["I", "II", "III", "IV", "V"], index=2)
        margem = st.number_input(
            "Margem de lucro real (%)", min_value=0.0, max_value=100.0, value=20.0, step=1.0,
        )
    with col3:
        folha_anual = st.number_input(
            "Folha anual (R$)", min_value=0.0, value=240000.0, step=10000.0, format="%.2f",
            help="Para Fator R do Anexo V e custo CLT comparativo",
        )
        creditos = st.number_input(
            "Créditos PIS/COFINS estimados (% receita)",
            min_value=0.0, max_value=100.0, value=0.0, step=0.5,
            help="Apenas Lucro Real",
        )

    st.markdown("#### Empregados (custo CLT comparativo, opcional)")
    col4, col5, col6 = st.columns(3)
    with col4:
        num_empregados = st.number_input("Nº empregados", min_value=0, value=0, step=1)
    with col5:
        salario_medio = st.number_input(
            "Salário médio (R$)", min_value=0.0, value=0.0, step=100.0, format="%.2f",
        )
    with col6:
        rat_pct = st.number_input("RAT (%)", min_value=0.0, value=2.0, step=0.5)

    st.markdown("#### Sócios (opcional)")
    col7, col8, col9 = st.columns(3)
    with col7:
        prolabore_mensal = st.number_input(
            "Pró-labore mensal POR sócio (R$)",
            min_value=0.0, value=0.0, step=100.0, format="%.2f",
        )
    with col8:
        num_socios = st.number_input("Nº de sócios", min_value=1, value=1, step=1)
    with col9:
        lucro_dist = st.number_input(
            "Distribuição mensal POR sócio (R$)",
            min_value=0.0, value=0.0, step=500.0, format="%.2f",
            help="IRRF 10% sobre VALOR INTEGRAL se exceder R$ 50K/mês",
        )

    submitted = st.form_submit_button("Comparar", type="primary")

if submitted:
    try:
        r = calc_comparativo(
            receita_anual=receita_anual,
            atividade_presumido=atividade,
            anexo_simples=anexo,
            margem_lucro_pct=margem,
            folha_anual=folha_anual,
            creditos_pis_cofins_pct=creditos,
            num_empregados=int(num_empregados),
            salario_medio=salario_medio,
            rat_pct=rat_pct,
            prolabore_mensal=prolabore_mensal,
            num_socios=int(num_socios),
            lucro_mensal_distribuicao=lucro_dist,
        )
    except APIError as e:
        st.error(str(e))
        st.stop()

    if r.get("recomendacao"):
        st.success(
            f"### Recomendação: **{r['recomendacao'].upper()}**  •  "
            f"economia de R$ {r.get('economia', 0):,.2f}/ano vs pior regime"
        )

    st.markdown("### Ranking")
    ranking = r.get("ranking", [])
    if ranking:
        rows = []
        for item in ranking:
            rows.append({
                "Regime": item.get("regime", ""),
                "Total anual (R$)": f"R$ {item.get('total_anual', 0):,.2f}",
                "Carga efetiva (%)": f"{item.get('carga_efetiva_pct', 0):.2f}%",
            })
        st.table(rows)

    cols = st.columns(3)
    for col, key, label in [
        (cols[0], "simples", "Simples Nacional"),
        (cols[1], "presumido", "Lucro Presumido"),
        (cols[2], "lucro_real", "Lucro Real"),
    ]:
        data = r.get(key, {})
        with col:
            st.markdown(f"#### {label}")
            if data.get("elegivel") is False:
                st.warning(data.get("motivo", "Não elegível"))
            else:
                total = data.get("total_anual")
                carga = data.get("carga_efetiva_pct")
                if total is not None:
                    st.metric("Total anual", f"R$ {total:,.2f}")
                if carga is not None:
                    st.metric("Carga efetiva", f"{carga:.2f}%")

    with st.expander("Detalhes completos", expanded=False):
        st.json(r)
