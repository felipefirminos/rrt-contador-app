from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_lucro_real  # noqa: E402


st.set_page_config(page_title="Lucro Real", page_icon="📈", layout="wide")
st.title("Lucro Real — LALUR + PIS/COFINS Não-cumulativo")
st.caption(
    "Lei 9.430/96 + Decreto 9.580/2018 (RIR) • IRPJ 15% + adicional 10% > R$60K trim "
    "(R$20K mês) • CSLL 9% • PIS 1,65% + COFINS 7,6% com créditos • Compensação prejuízo "
    "limitada a 30% (Lei 8.981/95)"
)

with st.form("lucro_real"):
    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        periodo = st.selectbox("Período", ["trimestral", "mensal"],
                                help="Trimestral: limite adicional R$60K; mensal: R$20K")
    with col_meta2:
        st.caption("Apuração trimestral é o padrão; estimativa mensal exige opção.")

    st.markdown("#### LALUR — Base do IRPJ/CSLL")
    col1, col2, col3 = st.columns(3)
    with col1:
        lucro_contabil = st.number_input(
            "Lucro contábil (R$)", value=300000.0, step=10000.0, format="%.2f",
            help="Pode ser negativo (prejuízo contábil)",
        )
        adicoes = st.number_input(
            "Adições ao LALUR (R$)", min_value=0.0, value=0.0,
            step=1000.0, format="%.2f",
            help="Provisões não dedutíveis, multas indedutíveis, brindes, etc.",
        )
    with col2:
        exclusoes = st.number_input(
            "Exclusões do LALUR (R$)", min_value=0.0, value=0.0,
            step=1000.0, format="%.2f",
            help="Equivalência patrimonial positiva, dividendos recebidos, etc.",
        )
        prej_acum = st.number_input(
            "Prejuízo fiscal acumulado (R$)", min_value=0.0, value=0.0,
            step=10000.0, format="%.2f",
            help="Compensação limitada a 30% do lucro ajustado (Lei 8.981/95)",
        )
    with col3:
        bn_csll = st.number_input(
            "Base negativa CSLL acumulada (R$)", min_value=0.0, value=0.0,
            step=10000.0, format="%.2f",
        )

    st.markdown("#### PIS/COFINS Não-cumulativo")
    col4, col5, col6 = st.columns(3)
    with col4:
        receita_bruta = st.number_input(
            "Receita bruta (R$)", min_value=0.0, value=2000000.0,
            step=50000.0, format="%.2f",
        )
    with col5:
        rec_fin = st.number_input(
            "Receitas financeiras (R$)", min_value=0.0, value=0.0,
            help="Decreto 8.426/2015: PIS 0,65% + COFINS 4%",
        )
        outras_rec = st.number_input(
            "Outras receitas (R$)", min_value=0.0, value=0.0,
        )
    with col6:
        cred_pis = st.number_input(
            "Créditos PIS (R$)", min_value=0.0, value=0.0,
            help="Insumos, aluguéis, energia, depreciação, etc.",
        )
        cred_cofins = st.number_input(
            "Créditos COFINS (R$)", min_value=0.0, value=0.0,
        )

    submitted = st.form_submit_button("Apurar Lucro Real", type="primary")

if submitted:
    try:
        r = calc_lucro_real(
            lucro_contabil=lucro_contabil,
            adicoes=adicoes, exclusoes=exclusoes,
            prejuizo_fiscal_acumulado=prej_acum,
            base_negativa_csll_acumulada=bn_csll,
            receita_bruta=receita_bruta,
            receitas_financeiras=rec_fin, outras_receitas=outras_rec,
            creditos_pis=cred_pis, creditos_cofins=cred_cofins,
            periodo=periodo,
        )
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(4)
    cols[0].metric("IRPJ", f"R$ {r['irpj_total']:,.2f}")
    cols[1].metric("CSLL", f"R$ {r['csll']:,.2f}")
    cols[2].metric("PIS+COFINS a pagar",
                   f"R$ {r['pis_a_pagar'] + r['cofins_a_pagar']:,.2f}")
    cols[3].metric("Total período", f"R$ {r['total_periodo']:,.2f}",
                   f"carga {r['carga_efetiva_pct']}%")

    if r.get("prejuizo_periodo_irpj", 0) > 0:
        st.warning(
            f"⚠️ **Prejuízo fiscal do período:** R$ {r['prejuizo_periodo_irpj']:,.2f}. "
            f"Sem IRPJ devido. Saldo acumulado para próximo período: "
            f"R$ {r['novo_saldo_prejuizo_fiscal']:,.2f}."
        )

    if r.get("compensacao_prejuizo_fiscal", 0) > 0:
        st.success(
            f"✅ **Compensação aplicada:** R$ {r['compensacao_prejuizo_fiscal']:,.2f} "
            f"(limite 30% × R$ {r['lucro_ajustado_irpj']:,.2f}). "
            f"Saldo restante de prejuízo: R$ {r['novo_saldo_prejuizo_fiscal']:,.2f}."
        )

    st.markdown("### LALUR — Apuração do IRPJ")
    rows_lalur = [
        {"Item": "Lucro contábil", "Valor": f"R$ {r['lucro_contabil']:,.2f}"},
        {"Item": "(+) Adições", "Valor": f"R$ {r['adicoes_irpj']:,.2f}"},
        {"Item": "(-) Exclusões", "Valor": f"R$ {r['exclusoes_irpj']:,.2f}"},
        {"Item": "**= Lucro ajustado**", "Valor": f"**R$ {r['lucro_ajustado_irpj']:,.2f}**"},
        {"Item": "(-) Compensação prejuízo (30%)",
         "Valor": f"R$ {r['compensacao_prejuizo_fiscal']:,.2f}"},
        {"Item": "**= Lucro real (base IRPJ)**",
         "Valor": f"**R$ {r['lucro_real_irpj']:,.2f}**"},
        {"Item": "IRPJ 15%", "Valor": f"R$ {r['irpj_15pct']:,.2f}"},
        {"Item": f"Adicional IRPJ 10% (sobre R$ {r['base_adicional_irpj']:,.2f})",
         "Valor": f"R$ {r['adicional_irpj']:,.2f}"},
        {"Item": "**IRPJ total**", "Valor": f"**R$ {r['irpj_total']:,.2f}**"},
    ]
    st.table(rows_lalur)

    st.markdown("### CSLL")
    cols2 = st.columns(2)
    cols2[0].metric("Base de cálculo CSLL", f"R$ {r['base_calculo_csll']:,.2f}")
    cols2[1].metric("CSLL (9%)", f"R$ {r['csll']:,.2f}")

    st.markdown("### PIS / COFINS Não-cumulativo")
    rows_pis = [
        {"Item": "Base (receita bruta + outras)",
         "Valor": f"R$ {r['base_pis_cofins']:,.2f}"},
        {"Item": "PIS bruto (1,65%)", "Valor": f"R$ {r['pis_bruto']:,.2f}"},
        {"Item": "(-) Créditos PIS", "Valor": f"R$ {r['creditos_pis']:,.2f}"},
        {"Item": f"**PIS a pagar** (alíq efetiva {r['aliquota_efetiva_pis']:.2f}%)",
         "Valor": f"**R$ {r['pis_a_pagar']:,.2f}**"},
        {"Item": "COFINS bruto (7,6%)", "Valor": f"R$ {r['cofins_bruto']:,.2f}"},
        {"Item": "(-) Créditos COFINS", "Valor": f"R$ {r['creditos_cofins']:,.2f}"},
        {"Item": f"**COFINS a pagar** (alíq efetiva {r['aliquota_efetiva_cofins']:.2f}%)",
         "Valor": f"**R$ {r['cofins_a_pagar']:,.2f}**"},
    ]
    st.table(rows_pis)

    st.markdown("### Saldos atualizados (próximo período)")
    cols3 = st.columns(3)
    cols3[0].metric("Prejuízo fiscal acumulado",
                    f"R$ {r['novo_saldo_prejuizo_fiscal']:,.2f}")
    cols3[1].metric("Base negativa CSLL",
                    f"R$ {r['novo_saldo_base_negativa_csll']:,.2f}")
    cols3[2].metric("Saldo crédito PIS/COFINS",
                    f"R$ {r.get('saldo_credito_pis', 0) + r.get('saldo_credito_cofins', 0):,.2f}")

    with st.expander("Detalhe completo (JSON)"):
        st.json(r)

    st.caption(f"📚 {r.get('base_legal', 'Lei 9.430/96 + RIR/2018')}")
