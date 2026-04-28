from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_lucro_presumido  # noqa: E402


st.set_page_config(page_title="Lucro Presumido", page_icon="📊")
st.title("Lucro Presumido — Apuração Trimestral")
st.caption(
    "Lei 9.249/95 (presunção + alíquotas) + Lei 9.718/98 (PIS/COFINS cumulativo) • "
    "IRPJ 15% + adicional 10% > R$60K/trim • CSLL 9% • PIS 0,65% • COFINS 3%"
)

ATIVIDADES = {
    "Comércio": "comercio",
    "Indústria": "industria",
    "Serviços (consultoria, advocacia, eng. consultiva)": "servicos",
    "Transporte de cargas": "transporte_cargas",
    "Transporte de passageiros": "transporte_passageiros",
    "Combustíveis (revenda)": "combustiveis",
    "Serviços hospitalares (clínicas, hospitais)": "servicos_hospitalares",
    "Construção civil": "construcao_civil",
}

with st.form("presumido"):
    col1, col2 = st.columns(2)
    with col1:
        atv_label = st.selectbox("Atividade", list(ATIVIDADES.keys()))
        receita_trim = st.number_input(
            "Receita bruta do trimestre (R$)", min_value=0.01, value=500000.0,
            step=50000.0, format="%.2f",
        )
    with col2:
        rec_fin = st.number_input(
            "Receitas financeiras (R$)", min_value=0.0, value=0.0, format="%.2f",
            help="Rendimentos de aplicações, juros — entram 100% na base",
        )
        outras_rec = st.number_input(
            "Outras receitas (R$)", min_value=0.0, value=0.0, format="%.2f",
            help="Ganhos de capital, aluguéis (fora da atividade-fim)",
        )
    submitted = st.form_submit_button("Apurar trimestre", type="primary")

if submitted:
    try:
        r = calc_lucro_presumido(
            atividade=ATIVIDADES[atv_label],
            receita_trimestre=receita_trim,
            receitas_financeiras=rec_fin,
            outras_receitas=outras_rec,
        )
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(4)
    cols[0].metric("IRPJ", f"R$ {r['irpj_total']:,.2f}",
                   f"{r['presuncao_irpj_pct']}% presunção")
    cols[1].metric("CSLL", f"R$ {r['csll']:,.2f}",
                   f"{r['presuncao_csll_pct']}% presunção")
    cols[2].metric("PIS + COFINS", f"R$ {r['pis'] + r['cofins']:,.2f}", "0,65% + 3%")
    cols[3].metric("Total trimestral", f"R$ {r['total_trimestral']:,.2f}",
                   f"carga {r['carga_efetiva_pct']}%")

    if r["adicional_irpj"] > 0:
        st.warning(
            f"⚠️ **Adicional IRPJ ativo:** R$ {r['adicional_irpj']:,.2f} "
            f"(10% sobre R$ {r['adicional_irpj_base']:,.2f} acima de R$ 60.000)"
        )

    st.markdown("### Discriminação")
    rows = [
        {"Tributo": "IRPJ — base de presunção", "Base": f"R$ {r['base_presuncao_irpj']:,.2f}",
         "Alíquota": "—", "Valor": "—"},
        {"Tributo": "  + receitas financeiras + outras", "Base": f"R$ {r['base_irpj']:,.2f}",
         "Alíquota": "—", "Valor": "—"},
        {"Tributo": "IRPJ 15%", "Base": "—", "Alíquota": "15%",
         "Valor": f"R$ {r['irpj_15pct']:,.2f}"},
        {"Tributo": "Adicional IRPJ 10%", "Base": f"R$ {r['adicional_irpj_base']:,.2f}",
         "Alíquota": "10%", "Valor": f"R$ {r['adicional_irpj']:,.2f}"},
        {"Tributo": "**IRPJ TOTAL**", "Base": "—", "Alíquota": "—",
         "Valor": f"**R$ {r['irpj_total']:,.2f}**"},
        {"Tributo": "CSLL", "Base": f"R$ {r['base_csll']:,.2f}",
         "Alíquota": "9%", "Valor": f"R$ {r['csll']:,.2f}"},
        {"Tributo": "PIS cumulativo", "Base": f"R$ {r['base_pis_cofins']:,.2f}",
         "Alíquota": "0,65%", "Valor": f"R$ {r['pis']:,.2f}"},
        {"Tributo": "COFINS cumulativo", "Base": f"R$ {r['base_pis_cofins']:,.2f}",
         "Alíquota": "3%", "Valor": f"R$ {r['cofins']:,.2f}"},
    ]
    st.table(rows)

    if r.get("pode_parcelar_3x"):
        st.info(
            f"💡 **IRPJ + CSLL = R$ {r['irpj_csll_trimestral']:,.2f}** parcelável em 3x: "
            f"R$ {r['quota_mensal_irpj_csll']:,.2f}/mês. "
            f"PIS+COFINS mensal: R$ {r['pis_cofins_mensal']:,.2f}."
        )

    with st.expander("Detalhe completo"):
        st.json(r)

    st.caption(f"📚 IRPJ: {r['base_legal_irpj']}")
    st.caption(f"📚 CSLL: {r['base_legal_csll']}")
    st.caption(f"📚 PIS/COFINS: {r['base_legal_pis_cofins']}")
