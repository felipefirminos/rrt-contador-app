from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_irpf  # noqa: E402


st.set_page_config(page_title="IRPF — Posição Anual", page_icon="📑", layout="wide")
st.title("IRPF — Posição Anual (Pessoa Física)")
st.caption(
    "Exercício 2026 (ano-calendário 2025) • Lei 9.250/95 + Lei 15.270/2025 + RIR/2018 + IN RFB 1.500/2014 • "
    "Integra: renda CLT, deduções legais, carnê-leão (exterior), ganhos de capital"
)

with st.sidebar:
    st.subheader("Renda CLT")
    salario_uniforme = st.number_input(
        "Salário mensal uniforme (R$)",
        min_value=0.0, value=8000.0, step=500.0, format="%.2f",
        help="Aplica o mesmo valor aos 12 meses. Use a tabela abaixo se houver variação.",
    )
    usar_tabela_meses = st.checkbox("Variação mês a mês", value=False)
    num_dependentes = st.number_input("Nº dependentes", min_value=0, max_value=20, value=1, step=1)
    pensao_mensal = st.number_input(
        "Pensão alimentícia mensal (R$)", min_value=0.0, value=0.0, format="%.2f",
    )
    irrf_outras_fontes = st.number_input(
        "IRRF retido por outras fontes (R$/ano)",
        min_value=0.0, value=0.0, format="%.2f",
        help="Ex: aluguel, autônomo PJ→PF, retenção fonte pagadora externa",
    )

if usar_tabela_meses:
    st.markdown("#### Salário mês a mês")
    default_rows = [{"mês": i, "salario": salario_uniforme} for i in range(1, 13)]
    if "irpf_meses" not in st.session_state:
        st.session_state.irpf_meses = default_rows
    edited_meses = st.data_editor(
        st.session_state.irpf_meses,
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "mês": st.column_config.NumberColumn("Mês", disabled=True),
            "salario": st.column_config.NumberColumn("Salário (R$)", min_value=0, format="%.2f"),
        },
        hide_index=True,
    )
    salarios_mensais = [float(r["salario"] or 0) for r in edited_meses]
else:
    salarios_mensais = [salario_uniforme] * 12

st.markdown("#### Deduções legais (anuais)")
st.caption(
    "Tipos: `saude` (sem limite), `educacao` (R$ 3.561,50/dependente), "
    "`previdencia_privada` (12% renda tributável), `dependentes` (R$ 2.275,08/dep), "
    "`pensao_alimenticia` (judicial)"
)
default_deds = [
    {"tipo": "saude", "valor": 0.0, "documentos": "recibo,nota_fiscal,cpf_beneficiario"},
]
if "irpf_deducoes" not in st.session_state:
    st.session_state.irpf_deducoes = default_deds
edited_deds = st.data_editor(
    st.session_state.irpf_deducoes,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "tipo": st.column_config.SelectboxColumn(
            "Tipo", options=["saude", "educacao", "previdencia_privada",
                              "pensao_alimenticia", "dependentes", "livro_caixa"],
        ),
        "valor": st.column_config.NumberColumn("Valor (R$)", min_value=0, format="%.2f"),
        "documentos": st.column_config.TextColumn("Documentos (csv)",
            help="Ex: recibo,nota_fiscal,cpf_beneficiario"),
    },
)

with st.expander("✈️ Carnê-leão — rendimentos no exterior (opcional)"):
    if "irpf_exterior" not in st.session_state:
        st.session_state.irpf_exterior = []
    edited_ext = st.data_editor(
        st.session_state.irpf_exterior,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "valor": st.column_config.NumberColumn("Valor (moeda)", min_value=0, format="%.2f"),
            "moeda": st.column_config.SelectboxColumn("Moeda", options=["USD", "EUR", "GBP"]),
            "mes": st.column_config.NumberColumn("Mês", min_value=1, max_value=12, step=1),
        },
    )

with st.expander("🏠 Ganhos de capital (imóvel/veículo, opcional)"):
    if "irpf_gcap" not in st.session_state:
        st.session_state.irpf_gcap = []
    edited_gcap = st.data_editor(
        st.session_state.irpf_gcap,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "tipo": st.column_config.SelectboxColumn("Tipo", options=["imovel", "veiculo"]),
            "valor_venda": st.column_config.NumberColumn("Valor venda (R$)", min_value=0, format="%.2f"),
            "custo_aquisicao": st.column_config.NumberColumn("Custo aquisição (R$)", min_value=0, format="%.2f"),
            "data_aquisicao": st.column_config.TextColumn("Data aquisição (YYYY-MM-DD)"),
            "data_venda": st.column_config.TextColumn("Data venda (YYYY-MM-DD)"),
        },
    )

if st.button("Calcular posição anual", type="primary"):
    deducoes = []
    for d in edited_deds:
        if not d.get("tipo") or not d.get("valor"):
            continue
        deducoes.append({
            "tipo": d["tipo"],
            "valor": float(d["valor"]),
            "documentos": [s.strip() for s in (d.get("documentos") or "").split(",") if s.strip()],
        })

    rendimentos = []
    for r in edited_ext:
        if not r.get("valor") or not r.get("moeda") or not r.get("mes"):
            continue
        rendimentos.append({
            "valor": float(r["valor"]),
            "moeda": r["moeda"],
            "mes": int(r["mes"]),
        })

    gcaps = []
    for g in edited_gcap:
        if not g.get("tipo") or not g.get("valor_venda"):
            continue
        gcaps.append({
            "tipo": g["tipo"],
            "valor_venda": float(g["valor_venda"]),
            "custo_aquisicao": float(g.get("custo_aquisicao") or 0),
            "data_aquisicao": g.get("data_aquisicao"),
            "data_venda": g.get("data_venda"),
        })

    payload = {
        "salarios_mensais": salarios_mensais,
        "num_dependentes": int(num_dependentes),
        "pensao_alimenticia_mensal": pensao_mensal,
        "deducoes_anuais": deducoes,
        "rendimentos_exterior": rendimentos,
        "ganhos_capital": gcaps,
        "irrf_ja_retido_anual": irrf_outras_fontes,
    }

    try:
        r = calc_irpf(**payload)
    except APIError as e:
        st.error(str(e))
        st.stop()

    pf = r.get("posicao_fiscal", {})
    sit = pf.get("situacao_fiscal", "—")
    saldo = pf.get("saldo_imposto", 0)

    if sit == "RESTITUIR":
        st.success(f"### ✅ RESTITUIÇÃO  •  R$ {abs(saldo):,.2f}")
    elif sit == "PAGAR":
        st.error(f"### ⚠️ A PAGAR  •  R$ {saldo:,.2f}")
    else:
        st.info(f"### {sit}")

    cols = st.columns(4)
    cols[0].metric("Renda tributável", f"R$ {pf.get('renda_tributavel_anual', 0):,.2f}")
    cols[1].metric("Imposto devido", f"R$ {pf.get('imposto_anual_devido', 0):,.2f}")
    cols[2].metric("IRRF retido (total)", f"R$ {pf.get('irrf_total_retido', 0):,.2f}")
    cols[3].metric("Desconto simpl. (20%)", f"R$ {pf.get('desconto_simplificado_anual', 0):,.2f}")

    rt = r.get("renda_trabalho", {})
    if rt:
        st.markdown("### Renda de trabalho")
        cols2 = st.columns(3)
        cols2[0].metric("Bruto anual", f"R$ {rt.get('total_bruto_anual', 0):,.2f}")
        cols2[1].metric("INSS descontado", f"R$ {rt.get('total_inss_descontado', 0):,.2f}")
        cols2[2].metric("IRRF retido CLT", f"R$ {rt.get('total_irrf_retido', 0):,.2f}")

    dl = r.get("deducoes_legais", {})
    if dl.get("total_aceito"):
        st.markdown("### Deduções legais aceitas")
        st.metric("Total aceito", f"R$ {dl['total_aceito']:,.2f}")
        if dl.get("flagged_items"):
            st.warning(f"⚠️ {len(dl['flagged_items'])} item(s) FLAGGED — documentação parcial:")
            for fi in dl["flagged_items"]:
                st.caption(
                    f"• **{fi['categoria']}** R$ {fi['valor_aceito']:,.2f} "
                    f"(confiança {fi['confianca_pct']}%) — {'; '.join(fi.get('motivos', []))[:200]}"
                )

    cl = r.get("carne_leao")
    if cl and cl.get("total_brl"):
        st.markdown("### Carnê-leão (rendimentos no exterior)")
        st.metric("Total convertido (R$)", f"R$ {cl['total_brl']:,.2f}")

    gc = r.get("ganhos_capital")
    if gc and gc.get("imposto_total"):
        st.markdown("### Ganhos de capital")
        st.metric("Imposto sobre ganho", f"R$ {gc['imposto_total']:,.2f}")

    with st.expander("Detalhe completo (JSON)"):
        st.json(r)
