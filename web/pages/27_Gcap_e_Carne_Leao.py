from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import (  # noqa: E402
    APIError, calc_carne_leao, calc_gcap_imovel, calc_gcap_veiculo,
    gcap_crypto_checklist, gcap_etf_checklist,
)
from lib.auto_record import render_sidebar  # noqa: E402


st.set_page_config(page_title="Ganho de Capital + Carnê-leão", page_icon="🪙", layout="wide")

render_sidebar()
st.title("Ganho de Capital + Carnê-leão (Pessoa Física)")
st.caption(
    "4 variantes de gcap + carnê-leão isolado • "
    "Lei 11.196/2005 + Lei 7.713/88 + IN RFB 599/2005 + Lei 14.754/2023 + IN RFB 1.585"
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Imóvel", "🚗 Veículo", "💰 Crypto (guidance)",
    "🌍 ETF exterior (guidance)", "✈️ Carnê-leão",
])

with tab1:
    st.markdown("Lei 11.196/2005: isenção único imóvel ≤ R$440K, fator redutor por tempo.")
    with st.form("imovel"):
        col1, col2 = st.columns(2)
        with col1:
            v_venda = st.number_input("Valor venda (R$)", min_value=0.01, value=800000.0,
                                      step=10000.0, format="%.2f")
            v_custo = st.number_input("Custo aquisição (R$)", min_value=0.0, value=600000.0,
                                      step=10000.0, format="%.2f")
            d_aq = st.date_input("Data aquisição", value=date(2018, 1, 15))
        with col2:
            benf = st.number_input("Benfeitorias (R$)", min_value=0.0, value=0.0, format="%.2f",
                                   help="Ampliação, reforma — somam ao custo")
            corr = st.number_input("Corretagem na venda (R$)", min_value=0.0, value=0.0, format="%.2f")
            unico = st.checkbox("Único imóvel residencial",
                                help="Isenção: único imóvel + venda ≤ R$440K (Lei 11.196 Art. 40 §2°)")
        if st.form_submit_button("Calcular gcap imóvel", type="primary"):
            try:
                r = calc_gcap_imovel(
                    valor_venda=v_venda, custo_aquisicao=v_custo,
                    data_aquisicao=d_aq.isoformat(),
                    benfeitorias=benf, corretagem=corr,
                    unico_imovel=unico,
                )
            except APIError as e:
                st.error(str(e)); st.stop()

            cols = st.columns(4)
            cols[0].metric("Ganho bruto", f"R$ {r['ganho_bruto']:,.2f}")
            cols[1].metric("Ganho tributável", f"R$ {r['ganho_tributavel']:,.2f}")
            cols[2].metric("Imposto devido", f"R$ {r['imposto_devido']:,.2f}",
                           f"alíq efetiva {r['aliquota_efetiva']:.2f}%")
            cols[3].metric("Líquido pós-imposto",
                           f"R$ {v_venda - r['imposto_devido']:,.2f}")

            if r.get("isencoes_aplicadas"):
                for isen in r["isencoes_aplicadas"]:
                    st.success(f"✅ {isen}")

            st.caption(f"📚 {r['base_legal']}")
            with st.expander("Detalhe completo"): st.json(r)

with tab2:
    st.markdown("Veículo PARTICULAR é ISENTO (apenas reportar IRPF). COMERCIAL tributa "
                "com alíquotas progressivas. DEPENDENTE exige parecer.")
    with st.form("veiculo"):
        col1, col2, col3 = st.columns(3)
        with col1:
            v_venda_v = st.number_input("Valor venda (R$)", min_value=0.01, value=70000.0,
                                        step=1000.0, format="%.2f", key="v_v_venda")
        with col2:
            v_custo_v = st.number_input("Custo aquisição (R$)", min_value=0.0, value=60000.0,
                                        step=1000.0, format="%.2f", key="v_v_custo")
        with col3:
            tipo_v = st.selectbox("Tipo", ["particular", "comercial", "dependente"])
        if st.form_submit_button("Calcular gcap veículo", type="primary"):
            try:
                r = calc_gcap_veiculo(valor_venda=v_venda_v, custo_aquisicao=v_custo_v,
                                       tipo_veiculo=tipo_v)
            except APIError as e:
                st.error(str(e)); st.stop()
            cols = st.columns(3)
            cols[0].metric("Ganho bruto", f"R$ {r['ganho_bruto']:,.2f}")
            cols[1].metric("Imposto", f"R$ {r['imposto_devido']:,.2f}")
            cols[2].metric("Alíquota", f"{r['aliquota_efetiva']:.2f}%")
            for o in r.get("observacoes", []): st.info(o)
            if r.get("alerta"): st.warning(r["alerta"])
            with st.expander("Detalhe completo"): st.json(r)

with tab3:
    st.warning(
        "⚠️ **Modo GUIDANCE** — esta calculadora NÃO faz o cálculo automático. "
        "Cripto exige FIFO + isenção mensal R$35K + saldo R$5K em 31/12, complexidade "
        "que requer **revisão manual do contador**. A página retorna checklist + alertas."
    )
    if st.button("Gerar checklist crypto", type="primary"):
        try:
            r = gcap_crypto_checklist()
        except APIError as e:
            st.error(str(e)); st.stop()
        st.markdown("### Checklist obrigatório")
        for i, item in enumerate(r.get("checklist", []), 1):
            st.markdown(f"- {item}")
        if r.get("alertas"):
            st.markdown("### Alertas")
            for a in r["alertas"]: st.warning(a)
        if r.get("regras_resumo"):
            st.markdown("### Regras-chave")
            for k, v in r["regras_resumo"].items():
                st.caption(f"**{k}**: {v}")

with tab4:
    st.warning(
        "⚠️ **Modo GUIDANCE** — verifica tratado de bitributação Brasil-país de origem "
        "(Lei 14.754/2023). Não calcula come-cotas anual ou opção offshore."
    )
    PAISES = ["EUA", "IRLANDA", "LUXEMBURGO", "ILHAS_CAYMAN", "JAPAO", "ALEMANHA", "REINO_UNIDO"]
    pais = st.selectbox("País de origem do ETF", PAISES)
    if st.button("Gerar checklist ETF", type="primary", key="etf_btn"):
        try:
            r = gcap_etf_checklist(pais_origem=pais)
        except APIError as e:
            st.error(str(e)); st.stop()
        trat = r.get("tratado_bitributacao", {})
        if trat.get("existe"):
            st.success(f"✅ Brasil tem tratado com {pais}")
        else:
            st.error(f"❌ Brasil NÃO tem tratado com {pais} — risco de bitributação")
        st.markdown("### Checklist")
        for item in r.get("checklist", []): st.markdown(f"- {item}")
        if r.get("alertas"):
            for a in r["alertas"]: st.warning(a)

with tab5:
    st.markdown("Renda no exterior em moeda estrangeira → BRL via PTAX → IRRF mensal.")
    with st.form("carne_leao"):
        col1, col2 = st.columns(2)
        with col1:
            valor_moeda = st.number_input(
                "Valor recebido (moeda)", min_value=0.01, value=10000.0,
                step=500.0, format="%.2f",
            )
            moeda = st.selectbox("Moeda", ["USD", "EUR", "GBP", "JPY", "CHF"])
        with col2:
            mes_ref = st.text_input("Mês referência (YYYY-MM)", value="2025-01")
            deps = st.number_input("Dependentes", min_value=0, value=0, step=1)
        deducoes = st.number_input("Deduções do mês (pensão, prev.) R$",
                                   min_value=0.0, value=0.0, format="%.2f")

        if st.form_submit_button("Calcular carnê-leão", type="primary"):
            try:
                r = calc_carne_leao(
                    renda_exterior_moeda=valor_moeda, moeda_origem=moeda,
                    mes_referencia=mes_ref, dependentes_irrf=int(deps),
                    deducoes_mes=deducoes,
                )
            except APIError as e:
                st.error(str(e)); st.stop()

            cols = st.columns(4)
            cols[0].metric(f"{moeda}", f"{valor_moeda:,.2f}")
            cols[1].metric("PTAX", f"{r['ptax_utilizada']:.4f}")
            cols[2].metric("Renda BRL", f"R$ {r['renda_brl']:,.2f}")
            cols[3].metric(
                "IRRF devido",
                f"R$ {r['irrf_devido']:,.2f}",
                f"{r['aliquota_efetiva']:.2f}% efetiva",
            )

            st.caption(f"Faixa: {r.get('faixa_aplicada', '—')} • Base: R$ {r['base_calculo']:,.2f}")
            if r.get("desvio_ptax_sinalizado"):
                st.warning("⚠️ Desvio significativo de PTAX detectado — confirme manualmente")
            st.caption(f"📚 {r['base_legal']}")
            with st.expander("Detalhe completo"): st.json(r)
