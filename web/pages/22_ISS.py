from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, buscar_municipio, calc_iss  # noqa: E402
from lib.auto_record import render_sidebar  # noqa: E402


st.set_page_config(page_title="ISS", page_icon="🏙️")

render_sidebar()
st.title("ISS — Imposto sobre Serviços")
st.caption("LC 116/2003 (alíquota máxima 5%) • Base de municípios brasileiros")

ITENS_LC116 = {
    "—": None,
    "1 — Tecnologia da Informação": 1,
    "7 — Engenharia / Arquitetura": 7,
    "8 — Educação": 8,
    "14 — Saúde": 14,
    "17 — Consultoria / Assessoria": 17,
}

st.markdown("#### Buscar município")
col1, col2 = st.columns([3, 1])
with col1:
    busca_municipio = st.text_input(
        "Digite parte do nome", placeholder="ex: Campinas, Rio, Bauru",
        key="mun_busca",
    )
with col2:
    if st.button("Buscar", key="btn_busca"):
        if len(busca_municipio.strip()) < 2:
            st.warning("Mínimo 2 caracteres.")
        else:
            try:
                r = buscar_municipio(busca_municipio.strip())
                results = r.get("resultados", [])
                if results:
                    st.session_state.municipio_options = [m["municipio"] for m in results]
                    st.success(f"{len(results)} encontrado(s).")
                else:
                    st.warning("Nenhum município encontrado.")
            except APIError as e:
                st.error(str(e))

mun_options = st.session_state.get("municipio_options", ["São Paulo-SP", "Campinas-SP",
                                                          "Rio de Janeiro-RJ"])

st.markdown("---")

with st.form("iss"):
    col1, col2 = st.columns(2)
    with col1:
        valor_servico = st.number_input(
            "Valor do serviço (R$)", min_value=0.0, value=10000.0,
            step=500.0, format="%.2f",
        )
        municipio = st.selectbox(
            "Município",
            mun_options,
            help="Use a busca acima se não estiver na lista",
        )
    with col2:
        item_label = st.selectbox(
            "Item LC 116/2003 (opcional)",
            list(ITENS_LC116.keys()),
            help="Alguns itens têm alíquota reduzida em municípios específicos",
        )
        simples = st.checkbox(
            "Empresa optante pelo Simples Nacional",
            help="Se sim, ISS pode estar incluído no DAS — alerta será exibido",
        )
    submitted = st.form_submit_button("Calcular ISS", type="primary")

if submitted:
    payload = {
        "valor_servico": valor_servico,
        "municipio": municipio,
        "simples_nacional": simples,
    }
    if ITENS_LC116[item_label] is not None:
        payload["item_lc116"] = ITENS_LC116[item_label]

    try:
        r = calc_iss(**payload)
    except APIError as e:
        st.error(str(e))
        st.stop()

    if r.get("verificar_legislacao_municipal"):
        st.error(f"⚠️ {r.get('erro')} — usando alíquota MÁXIMA legal (5%) como conservadora.")
        if r.get("sugestoes"):
            st.info("Sugestões: " + " • ".join(r["sugestoes"]))

    cols = st.columns(3)
    cols[0].metric("ISS", f"R$ {r.get('iss_valor', 0):,.2f}")
    cols[1].metric("Alíquota", f"{r.get('aliquota', 0):.2f}%")
    cols[2].metric("Retido na fonte?",
                   "✅ Sim" if r.get("retido_na_fonte") else "❌ Não")

    if r.get("aviso"):
        st.warning(r["aviso"])
        if r.get("iss_valor_base"):
            st.info(
                f"ℹ️ ISS de referência (se NÃO estiver no DAS): "
                f"R$ {r['iss_valor_base']:,.2f}"
            )

    with st.expander("Detalhe completo"):
        st.json(r)

    st.caption(f"📚 {r.get('base_legal', 'LC 116/2003')}")
