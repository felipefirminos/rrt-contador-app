from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_tema_69, verificar_prescricao  # noqa: E402


st.set_page_config(page_title="Recuperação Tributária", page_icon="⚖️", layout="wide")
st.title("Recuperação Tributária")
st.caption(
    "STF Tema 69 (RE 574.706) • LC 118/2005 (prescrição quinquenal) • "
    "Lei 9.430/96 (PER/DCOMP)"
)

with st.expander("ℹ️ Regras críticas (SKILL.md §6.0)"):
    st.markdown(
        """
        - **Tema 69 — modulação STF 13/05/2021**: créditos a partir de 15/03/2017 são
          automáticos. Pré-15/03/2017 só com **ação ajuizada** antes daquela data.
        - **Prescrição quinquenal (LC 118/2005, art. 3º)**: 5 anos contados do pagamento
          indevido. Verifique SEMPRE antes de iniciar estudo de recuperação — pagamento
          prescrito não recupera administrativamente.
        - **Apenas Lucro Real / Lucro Presumido**: Simples Nacional e MEI ficam fora.
        - **Cláusula CRC + OAB obrigatória**: a execução do pleito (ação judicial,
          PER/DCOMP em larga escala) exige advogado tributarista. O contador
          identifica/quantifica; o advogado executa.
        - **Atualização SELIC** (art. 39 §4 Lei 9.250/95): aplicar do pagamento até a
          compensação. Esta calculadora retorna apenas o **principal**.
        """
    )

tab1, tab2 = st.tabs(["📐 Tema 69 — exclusão ICMS de PIS/COFINS", "⏱️ Prescrição quinquenal"])

with tab1:
    st.markdown(
        "Calcula PIS/COFINS pagos indevidamente sobre o ICMS destacado, mês a mês. "
        "Adicione/remova competências na tabela abaixo."
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        regime = st.selectbox(
            "Regime",
            ["LUCRO_PRESUMIDO", "LUCRO_REAL"],
            help=(
                "PRESUMIDO (cumulativo): PIS 0,65% + COFINS 3% = 3,65%. "
                "REAL (não-cumulativo): PIS 1,65% + COFINS 7,6% = 9,25%"
            ),
        )
    with col2:
        tem_acao = st.checkbox(
            "Empresa tinha ação ajuizada ANTES de 15/03/2017?",
            help=(
                "Se sim, libera créditos pré-modulação (RE 574.706, modulação STF 13/05/2021). "
                "Sem ação prévia: só competências ≥ 15/03/2017."
            ),
        )

    DEFAULT_OPS = [
        {"competencia": "2024-01", "receita_bruta": 500000.0, "icms_destacado": 60000.0},
        {"competencia": "2024-02", "receita_bruta": 480000.0, "icms_destacado": 57600.0},
        {"competencia": "2024-03", "receita_bruta": 520000.0, "icms_destacado": 62400.0},
    ]
    if "tema69_ops" not in st.session_state:
        st.session_state.tema69_ops = DEFAULT_OPS

    edited = st.data_editor(
        st.session_state.tema69_ops,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "competencia": st.column_config.TextColumn(
                "Competência (YYYY-MM)",
                help="Mês de referência (ex: 2024-01)",
            ),
            "receita_bruta": st.column_config.NumberColumn(
                "Receita bruta (R$)", min_value=0, format="%.2f",
            ),
            "icms_destacado": st.column_config.NumberColumn(
                "ICMS destacado (R$)", min_value=0, format="%.2f",
            ),
        },
    )

    if st.button("Calcular Tema 69", type="primary"):
        ops = []
        for op in edited:
            if not op.get("competencia") or not op.get("receita_bruta"):
                continue
            ops.append({
                "competencia": str(op["competencia"]),
                "receita_bruta": float(op["receita_bruta"]),
                "icms_destacado": float(op.get("icms_destacado") or 0),
                "regime": regime,
            })
        if not ops:
            st.error("Adicione ao menos uma competência válida.")
            st.stop()

        try:
            r = calc_tema_69(ops, tem_acao_pre_15_03_2017=tem_acao)
        except APIError as e:
            st.error(str(e))
            st.stop()

        cols = st.columns(4)
        cols[0].metric("PIS recuperável", f"R$ {r['total_pis_recuperavel']:,.2f}")
        cols[1].metric("COFINS recuperável", f"R$ {r['total_cofins_recuperavel']:,.2f}")
        cols[2].metric("Total principal", f"R$ {r['total_geral']:,.2f}")
        cols[3].metric("Competências OK",
                       f"{r['competencias_elegiveis']} / "
                       f"{r['competencias_elegiveis'] + r['competencias_bloqueadas']}")

        st.markdown("### Detalhe por competência")
        rows = []
        for d in r["resultados_mensais"]:
            rows.append({
                "Competência": d["competencia"][:7],
                "Modulação OK?": "✅" if d["dentro_modulacao"] else "❌",
                "ICMS destacado": f"R$ {d['icms_destacado']:,.2f}",
                "PIS indevido": f"R$ {d['pis_pago_indevido']:,.2f}",
                "COFINS indevido": f"R$ {d['cofins_pago_indevido']:,.2f}",
                "Total": f"R$ {d['total_recuperavel']:,.2f}",
                "Obs": d["observacao"][:80],
            })
        st.table(rows)

        st.warning(r["aviso_selic"])
        st.caption(f"📚 {r['base_legal']}")

        with st.expander("Detalhe JSON"):
            st.json(r)

with tab2:
    st.markdown(
        "Verifica se ainda há prazo de 5 anos para pleitear restituição/compensação "
        "(LC 118/2005, art. 3º + CTN art. 168 I)."
    )

    col1, col2 = st.columns(2)
    with col1:
        data_pag = st.date_input("Data do pagamento indevido",
                                 value=date(2020, 6, 15),
                                 max_value=date.today())
    with col2:
        usar_hoje = st.checkbox("Usar data de hoje como referência", value=True)
        if not usar_hoje:
            data_ref = st.date_input("Data de referência (protocolo)", value=date.today())

    if st.button("Verificar prescrição", type="primary", key="presc_btn"):
        try:
            r = verificar_prescricao(
                data_pagamento=data_pag.isoformat(),
                data_referencia=None if usar_hoje else data_ref.isoformat(),
            )
        except APIError as e:
            st.error(str(e))
            st.stop()

        if r["prescrito"]:
            st.error(f"### ❌ PRESCRITO\n{r['observacao']}")
        elif r["dias_restantes"] < 90:
            st.error(f"### 🟠 URGENTE\n{r['observacao']}")
        elif r["dias_restantes"] < 365:
            st.warning(f"### 🟡 ATENÇÃO\n{r['observacao']}")
        else:
            st.success(f"### ✅ OK\n{r['observacao']}")

        cols = st.columns(3)
        cols[0].metric("Dias restantes", str(r["dias_restantes"]))
        cols[1].metric("Limite do pleito", r["data_limite_pleito"])
        cols[2].metric(
            "Janela recuperável (5 anos)",
            f"{r['periodo_recuperavel_inicio']} → {r['periodo_recuperavel_fim']}",
        )

        st.caption(f"📚 {r['base_legal']}")
