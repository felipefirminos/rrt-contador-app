from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import streamlit as st


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError  # noqa: E402

API_BASE = os.environ.get("RRT_API_BASE", "http://127.0.0.1:8765")


st.set_page_config(page_title="Parsers — DAS PDF + NF-e XML", page_icon="📥", layout="wide")
st.title("Parsers — DAS PDF e XMLs Fiscais")
st.caption(
    "Extração estruturada de guias DAS (Simples/MEI) e XMLs de NF-e/NFC-e/NFS-e • "
    "Útil para conferência fiscal mensal"
)

tab1, tab2, tab3 = st.tabs([
    "📄 DAS — guia única",
    "📑 DAS — lote (carteira)",
    "🧾 XML fiscal (NF-e/NFC-e/NFS-e)",
])

with tab1:
    st.markdown("Carregue uma guia DAS em PDF — extrai CNPJ, competência, vencimento, "
                "valores discriminados (principal, juros, multa) e detecta atraso.")
    uploaded = st.file_uploader("Guia DAS (PDF)", type=["pdf"], key="das_single")
    if uploaded and st.button("Extrair dados", key="btn_das_single", type="primary"):
        try:
            r = httpx.post(
                f"{API_BASE}/parser/das-pdf",
                files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                timeout=60.0,
            )
        except httpx.ConnectError:
            st.error(f"API offline em {API_BASE}.")
            st.stop()

        if r.status_code != 200:
            try:
                st.error(r.json().get("detail", r.text))
            except Exception:
                st.error(r.text)
            st.stop()

        d = r.json()
        if not d.get("sucesso"):
            st.warning(f"Extração com baixa confiança: {d.get('erro', '')}")

        dados = d.get("dados", {})
        if dados:
            cols = st.columns(4)
            cols[0].metric("Tipo", dados.get("tipo_das", "—"))
            cols[1].metric("Total", f"R$ {dados.get('valor_total', 0):,.2f}")
            cols[2].metric("Competência", dados.get("competencia_original", "—"))
            cols[3].metric("Vencimento", dados.get("vencimento_original", "—"))

            if dados.get("em_atraso"):
                st.error(f"⚠️ DAS VENCIDO há {dados.get('dias_atraso')} dias")

            st.markdown("### Discriminação")
            rows = []
            for k, label in [
                ("razao_social", "Razão Social"),
                ("cnpj", "CNPJ"),
                ("valor_principal", "Principal"),
                ("juros", "Juros"),
                ("multa", "Multa"),
            ]:
                v = dados.get(k)
                if v not in (None, "", 0):
                    if isinstance(v, (int, float)):
                        rows.append({"Campo": label, "Valor": f"R$ {v:,.2f}"})
                    else:
                        rows.append({"Campo": label, "Valor": str(v)})
            st.table(rows)

        if d.get("alertas"):
            for a in d["alertas"]:
                st.warning(a)

        with st.expander("Detalhe completo"):
            st.json(d)

with tab2:
    st.markdown("Carregue múltiplas guias DAS de uma vez — útil para apuração de "
                "carteira inteira de clientes no mesmo dia.")
    uploaded_batch = st.file_uploader(
        "Guias DAS (até 50 PDFs)", type=["pdf"], accept_multiple_files=True, key="das_batch",
    )
    if uploaded_batch and st.button("Processar lote", key="btn_das_batch", type="primary"):
        files_payload = [
            ("files", (f.name, f.getvalue(), "application/pdf"))
            for f in uploaded_batch
        ]
        try:
            r = httpx.post(
                f"{API_BASE}/parser/das-pdf-batch",
                files=files_payload, timeout=120.0,
            )
        except httpx.ConnectError:
            st.error(f"API offline em {API_BASE}.")
            st.stop()

        if r.status_code != 200:
            st.error(r.json().get("detail", r.text))
            st.stop()

        d = r.json()
        st.success(f"✅ {d.get('total_processados', 0)} guias processadas — "
                   f"R$ {d.get('valor_total_lote', 0):,.2f} total")

        rows = []
        for it in d.get("resultados", []):
            dados = it.get("dados", {})
            rows.append({
                "Arquivo": it.get("arquivo", "—"),
                "Tipo": dados.get("tipo_das", "—"),
                "CNPJ": dados.get("cnpj", "—"),
                "Razão social": (dados.get("razao_social") or "")[:30],
                "Competência": dados.get("competencia_original", "—"),
                "Total (R$)": f"{dados.get('valor_total', 0):,.2f}",
                "Status": "🚨 vencido" if dados.get("em_atraso") else "✅ OK",
            })
        st.table(rows)

        with st.expander("Detalhe completo (JSON)"):
            st.json(d)

with tab3:
    st.markdown("Carregue um XML de NF-e, NFC-e ou NFS-e — detecta o tipo automaticamente "
                "e extrai estrutura completa (emitente/destinatário, totais, impostos, itens).")
    uploaded_xml = st.file_uploader(
        "XML fiscal", type=["xml", "nfe", "nfse"], key="xml_single",
    )
    if uploaded_xml and st.button("Parsear XML", key="btn_xml", type="primary"):
        try:
            r = httpx.post(
                f"{API_BASE}/parser/xml-fiscal",
                files={"file": (uploaded_xml.name, uploaded_xml.getvalue(), "application/xml")},
                timeout=60.0,
            )
        except httpx.ConnectError:
            st.error(f"API offline em {API_BASE}.")
            st.stop()

        if r.status_code != 200:
            st.error(r.json().get("detail", r.text))
            st.stop()

        d = r.json()
        tipo = d.get("tipo", "—")
        st.info(f"**Tipo detectado:** {tipo.upper()}")

        if not d.get("sucesso"):
            st.warning(d.get("erro", "Falha no parse"))

        dados = d.get("dados", {})
        if dados:
            # Identificação
            cols = st.columns(3)
            ident = dados.get("identificacao", {})
            cols[0].metric("Número", ident.get("numero", "—"))
            cols[1].metric("Série", ident.get("serie", "—"))
            cols[2].metric("Emissão", ident.get("data_emissao", "—"))

            # Totais
            tot = dados.get("totais", {})
            if tot:
                st.markdown("### Totais")
                cols2 = st.columns(4)
                cols2[0].metric("Valor NF", f"R$ {tot.get('valor_nf', 0):,.2f}")
                cols2[1].metric("ICMS", f"R$ {tot.get('icms', 0):,.2f}")
                cols2[2].metric("PIS", f"R$ {tot.get('pis', 0):,.2f}")
                cols2[3].metric("COFINS", f"R$ {tot.get('cofins', 0):,.2f}")

            # Emitente / destinatário
            colA, colB = st.columns(2)
            with colA:
                emi = dados.get("emitente", {})
                if emi:
                    st.markdown("**Emitente**")
                    st.caption(f"{emi.get('razao_social', '—')} ({emi.get('cnpj', '—')})")
                    st.caption(f"{emi.get('uf', '—')} — {emi.get('municipio', '—')}")
            with colB:
                dest = dados.get("destinatario", {})
                if dest:
                    st.markdown("**Destinatário**")
                    st.caption(f"{dest.get('razao_social', '—')} ({dest.get('cnpj', dest.get('cpf', '—'))})")
                    st.caption(f"{dest.get('uf', '—')} — {dest.get('municipio', '—')}")

            # Itens
            itens = dados.get("itens", [])
            if itens:
                st.markdown(f"### Itens ({len(itens)})")
                rows_it = []
                for it in itens[:20]:
                    rows_it.append({
                        "Item": it.get("numero", "—"),
                        "Descrição": (it.get("descricao") or "")[:50],
                        "CFOP": it.get("cfop", "—"),
                        "NCM": it.get("ncm", "—"),
                        "Qtd": it.get("quantidade", "—"),
                        "Total": f"R$ {it.get('valor_total', 0):,.2f}",
                    })
                st.table(rows_it)
                if len(itens) > 20:
                    st.caption(f"… +{len(itens)-20} itens (ver JSON completo)")

        if d.get("alertas"):
            for a in d["alertas"]:
                st.warning(a)

        with st.expander("Detalhe completo (JSON)"):
            st.json(d)
