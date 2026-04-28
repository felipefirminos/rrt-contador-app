from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_cbs_ibs, projecao_cbs_ibs  # noqa: E402
from lib.auto_record import render_sidebar  # noqa: E402


st.set_page_config(page_title="CBS / IBS — Reforma Tributária", page_icon="🏛️", layout="wide")

render_sidebar()
st.title("CBS / IBS — Reforma Tributária")
st.caption(
    "EC 132/2023 + LC 214/2025 • Transição 2026-2033 • "
    "2026: ano-teste (CBS 0,9% + IBS 0,1%) → 2033: regime definitivo"
)

with st.expander("📅 Cronograma da transição"):
    st.markdown(
        """
        | Ano | Fase | CBS | IBS | PIS/COFINS | ICMS/ISS |
        |---|---|---|---|---|---|
        | **2026** | Ano-teste | 0,9% | 0,1% | Vigentes (CBS compensável) | 100% vigentes |
        | **2027** | CBS pleno | ~8,8% | 0,1% | EXTINTOS | 100% vigentes |
        | **2028** | Início IBS | ~8,8% | 1,0% | — | 90% vigentes |
        | **2029** | — | ~8,8% | ~3,5% | — | 80% vigentes |
        | **2030** | — | ~8,8% | ~7,1% | — | 60% vigentes |
        | **2031** | — | ~8,8% | ~10,6% | — | 40% vigentes |
        | **2032** | — | ~8,8% | ~14,2% | — | 20% vigentes |
        | **2033** | Definitivo | ~8,8% | ~17,7% | — | EXTINTOS |
        """
    )
    st.warning(
        "⚠️ Alíquotas pós-2026 são **estimativas** — valores definitivos serão fixados "
        "por lei ordinária (CBS) e Resolução do Comitê Gestor (IBS)."
    )

st.markdown("---")

tab1, tab2 = st.tabs(["📐 Cálculo único", "📊 Projeção 2026-2033"])

with tab1:
    with st.form("cbs_ibs_single"):
        col1, col2, col3 = st.columns(3)
        with col1:
            valor_op = st.number_input(
                "Valor da operação (R$)", min_value=0.01, value=10000.0,
                step=1000.0, format="%.2f",
            )
            ano = st.number_input("Ano", min_value=2026, max_value=2099, value=2026, step=1)
        with col2:
            regime = st.selectbox("Regime", ["lucro_presumido", "lucro_real", "simples"])
            tipo_op = st.selectbox("Tipo de operação", ["mercadoria", "servico", "misto"])
        with col3:
            aliq_icms = st.number_input("Alíquota ICMS atual (%)", min_value=0.0, max_value=30.0,
                                        value=18.0, step=0.5)
            aliq_iss = st.number_input("Alíquota ISS atual (%)", min_value=0.0, max_value=10.0,
                                       value=0.0, step=0.5)
        setor = st.selectbox(
            "Setor específico (regime diferenciado, opcional)",
            ["—", "combustiveis", "financeiro", "imobiliario", "saude", "educacao"],
        )
        submitted = st.form_submit_button("Calcular CBS/IBS", type="primary")

    if submitted:
        payload = {
            "valor_operacao": valor_op, "ano": int(ano), "regime": regime,
            "aliquota_icms": aliq_icms, "aliquota_iss": aliq_iss,
            "tipo_operacao": tipo_op,
        }
        if setor != "—":
            payload["setor_especifico"] = setor

        try:
            r = calc_cbs_ibs(**payload)
        except APIError as e:
            st.error(str(e))
            st.stop()

        st.info(f"**Fase {ano}:** {r.get('fase', '')}")
        if r.get("nota"):
            st.caption(r["nota"])

        cols = st.columns(4)
        cols[0].metric("CBS", f"R$ {r['cbs_valor']:,.2f}", f"{r['cbs_aliquota']}%")
        cols[1].metric("IBS", f"R$ {r['ibs_valor']:,.2f}", f"{r['ibs_aliquota']}%")
        cols[2].metric("Total CBS+IBS", f"R$ {r['total_cbs_ibs']:,.2f}",
                       f"{r['aliquota_combinada']}%")
        cols[3].metric(
            "Δ vs antiga",
            f"R$ {r['diferenca_absoluta']:,.2f}",
            f"{r['diferenca_percentual']:+.1f}%",
            delta_color="inverse",
        )

        if r.get("aviso_setor_especifico"):
            st.warning(r["aviso_setor_especifico"])

        st.markdown("### Comparativo carga tributária")
        rows = [
            {"Tributo": "PIS", "Valor": f"R$ {r['pis_antigo']:,.2f}"},
            {"Tributo": "COFINS", "Valor": f"R$ {r['cofins_antigo']:,.2f}"},
            {"Tributo": "ICMS (atual)", "Valor": f"R$ {r['icms_antigo']:,.2f}"},
            {"Tributo": "ISS (atual)", "Valor": f"R$ {r['iss_antigo']:,.2f}"},
            {"Tributo": "**TOTAL ANTIGO**", "Valor": f"**R$ {r['carga_total_antiga']:,.2f}**"},
            {"Tributo": "CBS", "Valor": f"R$ {r['cbs_valor']:,.2f}"},
            {"Tributo": "IBS", "Valor": f"R$ {r['ibs_valor']:,.2f}"},
            {"Tributo": f"PIS/COFINS líquido após compensação CBS",
             "Valor": f"R$ {max(r['total_pis_cofins_antigo'] - r['compensacao_cbs_com_pis_cofins'], 0):,.2f}"},
            {"Tributo": "**TOTAL NOVO**", "Valor": f"**R$ {r['carga_total_nova']:,.2f}**"},
        ]
        st.table(rows)
        st.caption(f"📚 {r['base_legal']}")
        st.caption(f"⚠️ {r['aviso']}")

        with st.expander("Detalhe completo (JSON)"):
            st.json(r)

with tab2:
    st.markdown("Projeta a carga tributária da MESMA operação ao longo de 2026-2033.")
    with st.form("cbs_ibs_projection"):
        col1, col2, col3 = st.columns(3)
        with col1:
            p_valor = st.number_input(
                "Valor (R$)", min_value=0.01, value=10000.0,
                step=1000.0, format="%.2f", key="p_valor",
            )
        with col2:
            p_regime = st.selectbox("Regime", ["lucro_presumido", "lucro_real", "simples"], key="p_regime")
        with col3:
            p_icms = st.number_input("ICMS atual (%)", min_value=0.0, max_value=30.0,
                                     value=18.0, step=0.5, key="p_icms")
        p_iss = st.number_input("ISS atual (%)", min_value=0.0, max_value=10.0,
                                value=0.0, step=0.5, key="p_iss")
        sub_proj = st.form_submit_button("Projetar 2026-2033", type="primary")

    if sub_proj:
        try:
            r = projecao_cbs_ibs(
                valor_operacao=p_valor, regime=p_regime,
                aliquota_icms=p_icms, aliquota_iss=p_iss,
            )
        except APIError as e:
            st.error(str(e))
            st.stop()

        rows = []
        for ano_resultado in r.get("projecao", []):
            rows.append({
                "Ano": ano_resultado["ano"],
                "Fase": ano_resultado.get("fase", "—"),
                "CBS": f"R$ {ano_resultado.get('cbs_valor', 0):,.2f}",
                "IBS": f"R$ {ano_resultado.get('ibs_valor', 0):,.2f}",
                "Total CBS+IBS": f"R$ {ano_resultado.get('total_cbs_ibs', 0):,.2f}",
                "Carga total": f"R$ {ano_resultado.get('carga_total_nova', 0):,.2f}",
                "Δ vs hoje (%)": f"{ano_resultado.get('diferenca_percentual', 0):+.1f}%",
            })
        st.markdown("### Carga ano a ano")
        st.table(rows)

        with st.expander("Detalhe completo (JSON)"):
            st.json(r)
