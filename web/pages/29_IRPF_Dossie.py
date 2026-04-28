from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, irpf_dossie, irpf_validar  # noqa: E402
from lib.auto_record import render_sidebar  # noqa: E402


st.set_page_config(page_title="IRPF — Dossiê + Validador", page_icon="📋", layout="wide")

render_sidebar()
st.title("IRPF — Dossiê Completo + Validador (17 regras)")
st.caption(
    "Gera dossiê com 12 seções (enquadramento, rendimentos tributáveis/exclusivos/"
    "isentos, deduções, bens, gcap, exterior, comparativo) e valida cruzamento "
    "via 17 regras de consistência (R01-R17)"
)

with st.expander("📚 As 17 regras de validação"):
    st.markdown(
        """
        - **R01** IRRF total cruzado entre seções
        - **R02** Rendimentos tributáveis vs fontes pagadoras
        - **R03** Limite de educação por dependente
        - **R04** PGBL limitado a 12% renda tributável
        - **R05** PGBL exige tipo identificado (PGBL/VGBL)
        - **R06** PGBL com regime declaração obrigatório (completa)
        - **R07** Crypto exige custódia identificada
        - **R08** Códigos de rendimentos isentos válidos
        - **R09** Rendimentos exterior exigem PTAX
        - **R10** Tratado Brasil-EUA não existe (alerta)
        - **R11** Comparativo completa × simplificada obrigatório
        - **R12** Saldo de imposto coerente entre seções
        - **R13** Dependentes com CPF
        - **R14** Bens no exterior convertidos para BRL
        - **R15** Aluguel código 70 não-dedutível
        - **R16** Exercício vs ano-calendário coerente
        - **R17** Dividendos acima de isenção (Lei 15.270/2025)
        """
    )

st.markdown("#### 1. Dados do contribuinte")
col1, col2 = st.columns(2)
with col1:
    cpf = st.text_input("CPF", placeholder="111.222.333-44")
    nome = st.text_input("Nome completo", placeholder="João da Silva")
with col2:
    pensao = st.number_input("Pensão alimentícia mensal (R$)",
                              min_value=0.0, value=0.0, format="%.2f")
    regime_dec = st.selectbox("Regime de declaração",
                              ["", "completa", "simplificada"],
                              help="Vazio = decisão depende do comparativo")

st.markdown("#### 2. Dependentes (opcional)")
if "irpf_dep" not in st.session_state:
    st.session_state.irpf_dep = []
edited_dep = st.data_editor(
    st.session_state.irpf_dep,
    num_rows="dynamic", use_container_width=True,
    column_config={
        "nome": st.column_config.TextColumn("Nome"),
        "cpf": st.column_config.TextColumn("CPF"),
        "tipo": st.column_config.SelectboxColumn(
            "Tipo", options=["filho", "conjuge", "pais", "ascendente", "outro"],
        ),
    },
)

st.markdown("#### 3. Fontes tributáveis (PJ pagadoras)")
DEFAULT_FONTES = [
    {"cnpj_fonte": "12.345.678/0001-99", "nome_fonte": "Empresa X",
     "rendimento_anual": 96000.0, "irrf_anual": 11828.64, "inss_anual": 11058.12},
]
if "irpf_fontes" not in st.session_state:
    st.session_state.irpf_fontes = DEFAULT_FONTES
edited_fontes = st.data_editor(
    st.session_state.irpf_fontes, num_rows="dynamic", use_container_width=True,
    column_config={
        "rendimento_anual": st.column_config.NumberColumn("Rend. anual", min_value=0, format="%.2f"),
        "irrf_anual": st.column_config.NumberColumn("IRRF anual", min_value=0, format="%.2f"),
        "inss_anual": st.column_config.NumberColumn("INSS anual", min_value=0, format="%.2f"),
    },
)

st.markdown("#### 4. Deduções anuais (opcional)")
TIPOS_DED = ["saude", "educacao", "previdencia_privada", "pensao_alimenticia",
              "dependentes", "livro_caixa"]
if "irpf_deducoes" not in st.session_state:
    st.session_state.irpf_deducoes = [{"tipo": "saude", "valor": 0.0, "documentos": "recibo"}]
edited_deds = st.data_editor(
    st.session_state.irpf_deducoes, num_rows="dynamic", use_container_width=True,
    column_config={
        "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS_DED),
        "valor": st.column_config.NumberColumn("Valor (R$)", min_value=0, format="%.2f"),
        "documentos": st.column_config.TextColumn("Documentos (csv)"),
    },
)

st.markdown("#### 5. Bens e direitos em 31/12 (opcional)")
TIPOS_BEM = ["imovel", "veiculo", "conta_corrente", "poupanca", "acoes",
             "fundo_investimento", "crypto", "etf_exterior", "outros"]
if "irpf_bens" not in st.session_state:
    st.session_state.irpf_bens = []
edited_bens = st.data_editor(
    st.session_state.irpf_bens, num_rows="dynamic", use_container_width=True,
    column_config={
        "tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS_BEM),
        "valor_31_12": st.column_config.NumberColumn("Valor 31/12 (R$)",
                                                       min_value=0, format="%.2f"),
        "pais": st.column_config.SelectboxColumn(
            "País", options=["BRA", "USA", "IRL", "LUX", "GBR", "JPN", "DEU", "OUTRO"],
        ),
    },
)

with st.expander("⚙️ Opções avançadas"):
    validar = st.checkbox("Executar validação (17 regras)", value=True)
    regras_excluir_raw = st.text_input(
        "Regras a pular (códigos separados por vírgula, ex: R10, R16)",
        value="",
    )

if st.button("Gerar dossiê + validar", type="primary"):
    if not cpf or not nome:
        st.error("CPF e Nome são obrigatórios.")
        st.stop()

    deducoes_clean = []
    for d in edited_deds:
        if not d.get("tipo") or not d.get("valor"):
            continue
        deducoes_clean.append({
            "tipo": d["tipo"], "valor": float(d["valor"]),
            "documentos": [s.strip() for s in (d.get("documentos") or "").split(",") if s.strip()],
        })

    payload = {
        "dados_contribuinte": {
            "cpf": cpf, "nome": nome,
            "dependentes": [d for d in edited_dep if d.get("nome") and d.get("cpf")],
            "pensao_alimenticia_mensal": pensao,
        },
        "fontes_tributaveis": [
            f for f in edited_fontes
            if f.get("nome_fonte") and f.get("rendimento_anual")
        ],
        "deducoes_anuais": deducoes_clean,
        "bens_direitos": [
            b for b in edited_bens
            if b.get("tipo") and b.get("valor_31_12")
        ],
        "validar": validar,
        "regras_excluidas": [r.strip().upper() for r in regras_excluir_raw.split(",")
                              if r.strip()],
    }
    if regime_dec:
        payload["dados_contribuinte"]["regime_declaracao"] = regime_dec

    try:
        r = irpf_dossie(**payload)
    except APIError as e:
        st.error(str(e))
        st.stop()

    dossie = r["dossie"]
    val = r.get("validacao")

    if val:
        status = val["status"]
        cores = {"APROVADO": "success", "ALERTAS": "warning", "REPROVADO": "error"}
        getattr(st, cores.get(status, "info"))(
            f"### Status validação: **{status}** "
            f"— {val['total_inconsistencias']} inconsistência(s) "
            f"de {val['total_regras']} regras"
        )

        cols = st.columns(4)
        cols[0].metric("Críticos", val["resumo"]["critico"])
        cols[1].metric("Alto", val["resumo"]["alto"])
        cols[2].metric("Médio", val["resumo"]["medio"])
        cols[3].metric("Baixo", val["resumo"]["baixo"])

        if val["inconsistencias"]:
            st.markdown("### Inconsistências detectadas")
            for inc in val["inconsistencias"]:
                sev = inc.get("severidade", "baixo")
                ic = {"critico": "🚨", "alto": "🟠", "medio": "🟡", "baixo": "ℹ️"}.get(sev, "•")
                with st.expander(
                    f"{ic} **{inc['regra']}** ({sev}) — {inc['secao']}/{inc['campo']}"
                ):
                    st.markdown(f"**Esperado:** {inc.get('esperado', '—')}")
                    st.markdown(f"**Encontrado:** {inc.get('encontrado', '—')}")
                    if inc.get("sugestao"):
                        st.markdown(f"**Sugestão:** {inc['sugestao']}")

    st.markdown("### Dossiê")
    secoes_disponiveis = sorted([k for k in dossie if k.startswith("secao_")],
                                 key=lambda x: int(x.split("_")[1]))
    for secao_key in secoes_disponiveis:
        secao = dossie[secao_key]
        titulo = secao.get("titulo", secao_key)
        with st.expander(f"**{secao_key.upper()}** — {titulo}"):
            st.json(secao)

    # Download
    md_lines = [
        f"# Dossiê IRPF — {dossie.get('contribuinte', {}).get('nome', '?')}",
        f"\n**CPF:** {dossie.get('cpf', '?')}",
        f"**Exercício:** {dossie.get('metadados', {}).get('exercicio', '?')}",
        f"**Data:** {dossie.get('metadados', {}).get('data_geracao', '?')}",
        "",
    ]
    for secao_key in secoes_disponiveis:
        secao = dossie[secao_key]
        md_lines.append(f"\n## {secao.get('titulo', secao_key)}\n")
        for k, v in secao.items():
            if k == "titulo":
                continue
            md_lines.append(f"- **{k}:** {v}")
    md_doc = "\n".join(md_lines)

    cols2 = st.columns(2)
    cols2[0].download_button(
        "⬇️ Baixar dossiê (.md)",
        data=md_doc,
        file_name=f"irpf_dossie_{cpf.replace('.', '').replace('-', '')}.md",
        mime="text/markdown",
    )
    cols2[1].download_button(
        "⬇️ Baixar dossiê (.json)",
        data=json.dumps(r, indent=2, ensure_ascii=False),
        file_name=f"irpf_dossie_{cpf.replace('.', '').replace('-', '')}.json",
        mime="application/json",
    )

    st.caption(f"📚 {dossie.get('disclaimer', '')}")
