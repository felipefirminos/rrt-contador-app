from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_retencoes_pj  # noqa: E402


st.set_page_config(page_title="Retenções PJ → PJ", page_icon="🔁")
st.title("Retenções PJ → PJ")
st.caption(
    "IN RFB 1.234/2012 + Art. 30 Lei 10.833/2003 + Art. 31 Lei 8.212/91 • "
    "Calcula IRRF, CSRF (PIS+COFINS+CSLL), INSS (cessão) e ISS sobre nota PJ→PJ"
)

with st.expander("⚖️ Regras críticas (SKILL.md Fluxo 9)"):
    st.markdown(
        """
        - **Simples Nacional NÃO retém IRRF nem CSRF** — **EXCEÇÃO: publicidade**
          retém IRRF 1,5% mesmo em Simples
        - **CSRF dispensada** se valor da nota ≤ R$215,05 (mínimo DARF R$10)
        - **INSS 11% retido** apenas em **cessão de mão de obra** (Art. 31 Lei 8.212/91)
        - **TRAVA DE COMPETÊNCIA**: retenção segue o **fato gerador** (data do
          pagamento/crédito, Art. 30 Lei 10.833/2003), não a data de emissão da NF
        - Alíquotas IRRF: 1,5% serviços profissionais/comissão/publicidade;
          1,0% limpeza/vigilância/conservação/cessão MO
        - CSRF: PIS 0,65% + COFINS 3% + CSLL 1% = **4,65%**
        """
    )

TIPOS = {
    "Profissional (consultoria, advocacia, eng., contab.)": "profissional",
    "Limpeza / conservação": "limpeza",
    "Vigilância / segurança": "vigilancia",
    "Conservação / manutenção predial": "conservacao",
    "Cessão de mão de obra (+ INSS 11%)": "cessao_mao_obra",
    "Publicidade (RETÉM IRRF mesmo Simples)": "publicidade",
    "Comissão / corretagem": "comissao",
}

with st.form("retencoes_pj"):
    col1, col2 = st.columns(2)
    with col1:
        valor = st.number_input("Valor da nota (R$)", min_value=0.01, value=10000.0,
                                step=100.0, format="%.2f")
        tipo_label = st.selectbox("Tipo de serviço", list(TIPOS.keys()))
    with col2:
        prest_simples = st.checkbox("Prestador é Simples Nacional?")
        reter_inss = st.checkbox(
            "Reter INSS 11% (apenas cessão MO)",
            help="Marca apenas se o tipo é cessão de mão de obra",
        )

    st.markdown("**ISS (opcional, varia por município)**")
    col3, col4 = st.columns(2)
    with col3:
        reter_iss = st.checkbox("Reter ISS na fonte")
    with col4:
        aliq_iss = st.number_input(
            "Alíquota ISS (%)", min_value=0.0, max_value=10.0, value=0.0, step=0.5,
            disabled=not reter_iss,
        )

    submitted = st.form_submit_button("Calcular retenções", type="primary")

if submitted:
    try:
        r = calc_retencoes_pj(
            valor_nota=valor, tipo_servico=TIPOS[tipo_label],
            prestador_simples=prest_simples,
            reter_inss=reter_inss, reter_iss=reter_iss,
            aliquota_iss=aliq_iss if reter_iss else 0,
        )
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(4)
    cols[0].metric("Valor bruto", f"R$ {r['valor_nota']:,.2f}")
    cols[1].metric("Total retenções", f"R$ {r['total_retencoes']:,.2f}")
    cols[2].metric("Valor líquido (a pagar)", f"R$ {r['valor_liquido']:,.2f}")
    pct = (r["total_retencoes"] / r["valor_nota"] * 100) if r["valor_nota"] > 0 else 0
    cols[3].metric("Carga retenção", f"{pct:.2f}%")

    st.markdown("### Discriminação")
    rows = [
        {"Retenção": f"IRRF ({r['irrf_aliquota']*100:.2f}%)",
         "Valor": f"R$ {r['irrf_valor']:,.2f}",
         "Status": "✅" if r["irrf_valor"] > 0 else "— (não retém)"},
        {"Retenção": "CSRF — PIS (0,65%)",
         "Valor": f"R$ {r['csrf_pis']:,.2f}", "Status": ""},
        {"Retenção": "CSRF — COFINS (3%)",
         "Valor": f"R$ {r['csrf_cofins']:,.2f}", "Status": ""},
        {"Retenção": "CSRF — CSLL (1%)",
         "Valor": f"R$ {r['csrf_csll']:,.2f}", "Status": ""},
        {"Retenção": "**CSRF total (4,65%)**",
         "Valor": f"**R$ {r['csrf_total']:,.2f}**",
         "Status": "❌ Dispensada" if r["csrf_dispensada"] else "✅ Devida"},
        {"Retenção": "INSS retido (11% — cessão MO)",
         "Valor": f"R$ {r['inss_retido']:,.2f}", "Status": ""},
        {"Retenção": "ISS retido",
         "Valor": f"R$ {r['iss_retido']:,.2f}", "Status": ""},
    ]
    st.table(rows)

    if r["csrf_dispensada"] and r["valor_nota"] <= 215.05:
        st.info("ℹ️ CSRF dispensada — valor ≤ R$215,05 (mínimo DARF R$10).")
    if r["csrf_dispensada"] and prest_simples:
        st.info("ℹ️ CSRF dispensada — prestador é Simples Nacional.")
    if prest_simples and TIPOS[tipo_label] == "publicidade":
        st.warning(
            "⚠️ **Publicidade no Simples** retém IRRF mesmo assim "
            "(exceção da regra geral)."
        )

    with st.expander("Detalhe completo"):
        st.json(r)
