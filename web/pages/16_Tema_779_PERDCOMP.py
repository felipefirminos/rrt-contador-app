from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_tema_779, gerar_minuta_perdcomp  # noqa: E402


st.set_page_config(page_title="Tema 779 + PER/DCOMP", page_icon="🧪", layout="wide")
st.title("Tema 779 STJ + Minuta PER/DCOMP")
st.caption(
    "STJ Tema 779 (REsp 1.221.170/PR) — conceito amplo de insumo • "
    "Geração de minuta PER/DCOMP (IN RFB 2.055/2021)"
)

tab1, tab2 = st.tabs(["🧪 Tema 779 — análise de insumos", "📄 Minuta PER/DCOMP"])

with tab1:
    with st.expander("ℹ️ Categorias e força da tese"):
        st.markdown(
            """
            **FORTE** (jurisprudência consolidada):
            - `MATERIA_PRIMA_DIRETA`, `EMBALAGEM_PRIMARIA`,
              `ENERGIA_ELETRICA_PRODUTIVA`, `COMBUSTIVEL_MAQUINA_PRODUTIVA`

            **MEDIA** (favorável mas exige laudo técnico):
            - `EPI_OBRIGATORIO_NR`, `SERVICOS_MANUTENCAO_MAQUINARIO`,
              `FRETE_INTERNO_ENTRE_ESTABELECIMENTOS`,
              `PRODUTOS_LIMPEZA_AREA_PRODUTIVA`, `ANALISES_LABORATORIAIS_QUALIDADE`

            **FRACA** (alto risco de glosa, multa 75-150%):
            - `MATERIAL_ESCRITORIO`, `DESPESAS_ADMINISTRATIVAS`,
              `MARKETING_PUBLICIDADE`, `ALIMENTACAO_FUNCIONARIOS`

            **NÃO APLICÁVEL** (vedação legal expressa):
            - `MAO_DE_OBRA_PF`, `TRIBUTOS_RECUPERAVEIS`
            """
        )

    DEFAULT = [
        {"descricao": "Aço para usinagem", "categoria": "MATERIA_PRIMA_DIRETA",
         "valor_total_competencia": 100000.0, "competencia": "03/2025",
         "justificativa_tecnica": "Insumo principal da linha de produção",
         "tem_laudo_tecnico": False},
        {"descricao": "EPIs NR-12", "categoria": "EPI_OBRIGATORIO_NR",
         "valor_total_competencia": 15000.0, "competencia": "03/2025",
         "justificativa_tecnica": "Obrigatório por NR-12 nas prensas",
         "tem_laudo_tecnico": True},
    ]
    if "tema779_insumos" not in st.session_state:
        st.session_state.tema779_insumos = DEFAULT

    edited = st.data_editor(
        st.session_state.tema779_insumos,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "descricao": st.column_config.TextColumn("Descrição"),
            "categoria": st.column_config.SelectboxColumn(
                "Categoria",
                options=[
                    "MATERIA_PRIMA_DIRETA", "EMBALAGEM_PRIMARIA",
                    "ENERGIA_ELETRICA_PRODUTIVA", "COMBUSTIVEL_MAQUINA_PRODUTIVA",
                    "EPI_OBRIGATORIO_NR", "SERVICOS_MANUTENCAO_MAQUINARIO",
                    "FRETE_INTERNO_ENTRE_ESTABELECIMENTOS",
                    "PRODUTOS_LIMPEZA_AREA_PRODUTIVA",
                    "ANALISES_LABORATORIAIS_QUALIDADE",
                    "MATERIAL_ESCRITORIO", "DESPESAS_ADMINISTRATIVAS",
                    "MARKETING_PUBLICIDADE", "ALIMENTACAO_FUNCIONARIOS",
                    "MAO_DE_OBRA_PF", "TRIBUTOS_RECUPERAVEIS",
                ],
            ),
            "valor_total_competencia": st.column_config.NumberColumn(
                "Valor (R$)", min_value=0, format="%.2f",
            ),
            "competencia": st.column_config.TextColumn("Competência (MM/AAAA)"),
            "justificativa_tecnica": st.column_config.TextColumn("Justificativa"),
            "tem_laudo_tecnico": st.column_config.CheckboxColumn("Laudo?"),
        },
    )

    if st.button("Analisar Tema 779", type="primary", key="t779"):
        insumos = [it for it in edited
                   if it.get("descricao") and it.get("valor_total_competencia")]
        if not insumos:
            st.error("Adicione ao menos um insumo válido.")
            st.stop()

        try:
            r = calc_tema_779(insumos)
        except APIError as e:
            st.error(str(e))
            st.stop()

        cols = st.columns(4)
        cols[0].metric("Total bruto", f"R$ {r['credito_total_bruto']:,.2f}")
        cols[1].metric("Alta confiança", f"R$ {r['credito_alta_confianca']:,.2f}")
        cols[2].metric("Média confiança", f"R$ {r['credito_media_confianca']:,.2f}")
        cols[3].metric("Baixa confiança", f"R$ {r['credito_baixa_confianca']:,.2f}")

        st.markdown("### Análise por insumo")
        rows = []
        for a in r["analises"]:
            icone = {
                "FORTE": "✅", "MEDIA": "🟡", "FRACA": "🟠", "NAO_APLICAVEL": "❌",
            }.get(a["forca_tese"], "—")
            rows.append({
                "Insumo": a["descricao"],
                "Categoria": a["categoria"],
                "Força": f"{icone} {a['forca_tese']}",
                "Valor": f"R$ {a['valor_competencia']:,.2f}",
                "Crédito (9,25%)": f"R$ {a['credito_total']:,.2f}",
                "Riscos": len(a["riscos"]),
            })
        st.table(rows)

        for a in r["analises"]:
            if a["riscos"]:
                with st.expander(f"⚠️ {a['descricao']} — {len(a['riscos'])} risco(s)"):
                    for ri in a["riscos"]:
                        st.warning(ri)
                    st.info(a["recomendacao"])

        st.warning(r["aviso_selic"])
        st.caption(f"📚 {r['base_legal']}")

        with st.expander("Detalhe JSON"):
            st.json(r)

with tab2:
    st.markdown("Gera minuta da memória de cálculo PER/DCOMP — preencha as identificações.")

    with st.form("perdcomp"):
        st.markdown("#### Cliente e regime")
        col1, col2 = st.columns(2)
        with col1:
            razao = st.text_input("Razão social", value="EXEMPLO LTDA")
            cnpj = st.text_input("CNPJ", value="00.000.000/0001-00")
            regime = st.selectbox("Regime tributário", ["LUCRO_REAL", "LUCRO_PRESUMIDO"])
        with col2:
            tese = st.text_input("Tese", value="Tema 69 STF — Exclusão do ICMS da base de PIS/COFINS")
            leading = st.text_input("Leading case", value="RE 574.706/PR")

        st.markdown("#### Período e valores")
        col3, col4, col5 = st.columns(3)
        with col3:
            comp_ini = st.text_input("Competência inicial (MM/AAAA)", value="01/2021")
        with col4:
            comp_fim = st.text_input("Competência final (MM/AAAA)", value="12/2024")
        with col5:
            num_comp = st.number_input("Nº competências", min_value=1, value=48, step=1)

        col6, col7 = st.columns(2)
        with col6:
            principal = st.number_input(
                "Total principal (R$)", min_value=0.0, value=120000.0,
                step=10000.0, format="%.2f",
            )
        with col7:
            atualizado = st.number_input(
                "Total atualizado SELIC (R$, opcional)", min_value=0.0, value=0.0,
                step=10000.0, format="%.2f",
            )

        st.markdown("#### Responsáveis")
        col8, col9 = st.columns(2)
        with col8:
            cont_nome = st.text_input("Contador (nome)", value="Richard Firmino")
            cont_crc = st.text_input("CRC", value="SP-XXXXXX/O")
        with col9:
            adv_nome = st.text_input("Advogado (nome, opcional)")
            adv_oab = st.text_input("OAB (opcional)")

        col10, col11 = st.columns(2)
        with col10:
            forma = st.selectbox("Forma de recuperação", ["DCOMP", "PER", "RESSARCIMENTO"])
        with col11:
            ult_dia = st.text_input("Último dia para pleito (DD/MM/AAAA, opcional)")

        sem_presc = st.checkbox(
            "✅ Confirmo que verifiquei a prescrição quinquenal",
            value=True,
            help="Se desmarcado, a minuta inclui alerta destacado",
        )

        sub_minuta = st.form_submit_button("Gerar minuta", type="primary")

    if sub_minuta:
        payload = {
            "cliente_razao_social": razao, "cliente_cnpj": cnpj,
            "regime_tributario": regime, "tese": tese, "leading_case": leading,
            "competencia_inicial": comp_ini, "competencia_final": comp_fim,
            "num_competencias": int(num_comp), "total_principal": principal,
            "contador_nome": cont_nome, "contador_crc": cont_crc,
            "forma_recuperacao": forma, "sem_prescricao": sem_presc,
        }
        if atualizado > 0:
            payload["total_atualizado"] = atualizado
        if adv_nome:
            payload["advogado_nome"] = adv_nome
        if adv_oab:
            payload["advogado_oab"] = adv_oab
        if ult_dia:
            payload["ultimo_dia_pleito"] = ult_dia

        try:
            r = gerar_minuta_perdcomp(**payload)
        except APIError as e:
            st.error(str(e))
            st.stop()

        st.success(
            f"✅ Minuta gerada — {r['tamanho_chars']:,} caracteres, "
            f"data {r['data_geracao']}"
        )
        st.warning(r["aviso"])

        st.download_button(
            "⬇️ Baixar minuta (.md)",
            data=r["minuta_markdown"],
            file_name=f"perdcomp_{cnpj.replace('.', '').replace('/', '').replace('-', '')}.md",
            mime="text/markdown",
        )

        with st.expander("Visualizar minuta", expanded=True):
            st.markdown(r["minuta_markdown"])
