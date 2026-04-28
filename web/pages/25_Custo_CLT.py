from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_custo_empregado  # noqa: E402
from lib.auto_record import render_sidebar  # noqa: E402


st.set_page_config(page_title="Custo Total CLT", page_icon="💼", layout="wide")

render_sidebar()
st.title("Custo Total de Contratação CLT")
st.caption(
    "Lei 8.212/91 + LC 123/2006 • Encargos variam por regime: "
    "Simples I/III/V isento de patronal/RAT/Terceiros (CPP no DAS); "
    "Simples IV recolhe INSS+RAT separados (Terceiros dispensado); "
    "Presumido/Real: encargos plenos"
)

REGIMES = {
    "Lucro Presumido / Lucro Real": "presumido_real",
    "Simples Nacional — Anexos I/III/V (CPP no DAS)": "simples_i_iii_v",
    "Simples Nacional — Anexo IV (CPP separada)": "simples_iv",
}

with st.form("custo_clt"):
    st.markdown("#### Empregado")
    col1, col2 = st.columns(2)
    with col1:
        salario = st.number_input("Salário bruto (R$)", min_value=0.01, value=3000.0,
                                  step=100.0, format="%.2f")
        regime_label = st.selectbox("Regime tributário", list(REGIMES.keys()))
    with col2:
        rat = st.number_input("RAT (%)", min_value=0.0, max_value=3.0, value=2.0, step=0.5,
                              help="1% leve, 2% médio, 3% grave (CNAE)")
        fap = st.number_input("FAP", min_value=0.5, max_value=2.0, value=1.0, step=0.1,
                              help="Fator Acidentário 0,5-2,0")
        terc = st.number_input("Terceiros (%)", min_value=0.0, max_value=10.0, value=5.8, step=0.1,
                               help="Sistema S — não aplicável ao Simples")

    st.markdown("#### Benefícios (mensais, parte empresa)")
    col3, col4, col5, col6 = st.columns(4)
    with col3:
        vt = st.number_input("VT (líquido)", min_value=0.0, value=0.0, format="%.2f",
                             help="Já com desconto 6% do empregado")
    with col4:
        vr = st.number_input("VR/VA", min_value=0.0, value=0.0, format="%.2f")
    with col5:
        ps = st.number_input("Plano saúde", min_value=0.0, value=0.0, format="%.2f")
    with col6:
        outros = st.number_input("Outros (CCT)", min_value=0.0, value=0.0, format="%.2f")

    submitted = st.form_submit_button("Calcular custo total", type="primary")

if submitted:
    try:
        r = calc_custo_empregado(
            salario_bruto=salario, regime=REGIMES[regime_label],
            rat_pct=rat, fap=fap, terceiros_pct=terc,
            vale_transporte=vt, vale_refeicao=vr, plano_saude=ps,
            outros_beneficios=outros,
        )
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(4)
    cols[0].metric("Salário", f"R$ {salario:,.2f}")
    cols[1].metric("Custo mensal", f"R$ {r['custo_mensal']:,.2f}",
                   f"+{r['percentual_sobre_salario']:.1f}%")
    cols[2].metric("Custo anual", f"R$ {r['custo_anual']:,.2f}")
    cols[3].metric("FGTS mensal", f"R$ {r['fgts']:,.2f}")

    st.markdown("### Composição do custo")
    rows = [
        {"Componente": "Salário bruto", "Valor mensal": f"R$ {salario:,.2f}"},
        {"Componente": "INSS patronal (20%)", "Valor mensal": f"R$ {r['inss_patronal']:,.2f}"},
        {"Componente": f"RAT × FAP ({rat}% × {fap})", "Valor mensal": f"R$ {r['rat_fap']:,.2f}"},
        {"Componente": f"Terceiros ({terc}%)", "Valor mensal": f"R$ {r['terceiros']:,.2f}"},
        {"Componente": "**Total encargos patronais**",
         "Valor mensal": f"**R$ {r['total_encargos_patronais']:,.2f}**"},
        {"Componente": "FGTS (8%)", "Valor mensal": f"R$ {r['fgts']:,.2f}"},
        {"Componente": "Provisão 13° (1/12)", "Valor mensal": f"R$ {r['provisao_13o']:,.2f}"},
        {"Componente": "Provisão férias + 1/3 (1/9)",
         "Valor mensal": f"R$ {r['provisao_ferias_terco']:,.2f}"},
        {"Componente": "Encargos sobre provisões",
         "Valor mensal": f"R$ {r['encargos_sobre_provisoes']:,.2f}"},
        {"Componente": "**Total provisões**", "Valor mensal": f"**R$ {r['total_provisoes']:,.2f}**"},
        {"Componente": "Total benefícios", "Valor mensal": f"R$ {r['total_beneficios']:,.2f}"},
        {"Componente": "**= CUSTO MENSAL**", "Valor mensal": f"**R$ {r['custo_mensal']:,.2f}**"},
    ]
    st.table(rows)

    st.caption(f"📚 {r['base_legal']}")

    with st.expander("Detalhe completo"):
        st.json(r)
