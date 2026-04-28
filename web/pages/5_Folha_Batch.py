from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_folha_batch  # noqa: E402


st.set_page_config(page_title="Folha em Lote", page_icon="👥", layout="wide")
st.title("Folha de Pagamento — Lote")
st.caption(
    "CLT + Lei 8.212 (INSS) + Lei 8.036 (FGTS) • "
    "Gera GPS (vence dia 20), FGTS Digital (dia 7), DARF 0561 (dia 20)"
)

REGIMES = {
    "Lucro Presumido / Lucro Real (CPP separada)": "presumido_real",
    "Simples Anexos I/III/V (CPP no DAS)": "simples_i_iii_v",
    "Simples Anexo IV (CPP separada)": "simples_iv",
}

with st.sidebar:
    st.subheader("Empresa")
    competencia = st.text_input("Competência", value="04/2026", help="MM/AAAA — informativo")
    regime_label = st.selectbox("Regime tributário", list(REGIMES.keys()))
    rat_pct = st.number_input("RAT (%)", min_value=0.0, value=2.0, step=0.5)
    fap = st.number_input("FAP", min_value=0.0, value=1.0, step=0.1)

st.markdown("#### Empregados")
st.caption(
    "Edite a tabela abaixo (linhas podem ser adicionadas/removidas). "
    "Clique fora da célula para confirmar e depois em **Processar folha**."
)

DEFAULT_ROWS = [
    {"nome": "João Silva", "salario_base": 4000.0, "he_normais": 0.0, "he_feriado": 0.0,
     "horas_noturnas": 0.0, "adicional_noturno_pct": 0.0, "insalubridade_pct": 0,
     "periculosidade_pct": 0.0, "adicional_funcao": 0.0, "comissoes": 0.0,
     "faltas_dias": 0, "num_dependentes": 1, "pensao_alimenticia": 0.0,
     "vt_base": 0.0, "outros_descontos": 0.0, "jornada_mensal": 220},
    {"nome": "Maria Souza", "salario_base": 6500.0, "he_normais": 10.0, "he_feriado": 0.0,
     "horas_noturnas": 0.0, "adicional_noturno_pct": 0.0, "insalubridade_pct": 0,
     "periculosidade_pct": 0.0, "adicional_funcao": 0.0, "comissoes": 0.0,
     "faltas_dias": 0, "num_dependentes": 2, "pensao_alimenticia": 0.0,
     "vt_base": 250.0, "outros_descontos": 0.0, "jornada_mensal": 220},
]

if "folha_rows" not in st.session_state:
    st.session_state.folha_rows = DEFAULT_ROWS

edited = st.data_editor(
    st.session_state.folha_rows,
    num_rows="dynamic",
    use_container_width=True,
    key="folha_editor",
    column_config={
        "salario_base": st.column_config.NumberColumn("Salário (R$)", min_value=0, format="%.2f"),
        "he_normais": st.column_config.NumberColumn("HE 50%", min_value=0),
        "he_feriado": st.column_config.NumberColumn("HE 100%", min_value=0),
        "horas_noturnas": st.column_config.NumberColumn("Hs noturnas", min_value=0),
        "adicional_noturno_pct": st.column_config.NumberColumn("Ad noturno %", min_value=0),
        "insalubridade_pct": st.column_config.SelectboxColumn("Insalub %", options=[0, 10, 20, 40]),
        "periculosidade_pct": st.column_config.NumberColumn("Pericul %", min_value=0, max_value=30),
        "vt_base": st.column_config.NumberColumn("VT (R$)", min_value=0, format="%.2f"),
        "pensao_alimenticia": st.column_config.NumberColumn("Pensão (R$)", min_value=0, format="%.2f"),
        "jornada_mensal": st.column_config.NumberColumn("Jornada h/mês", min_value=1),
    },
)

if st.button("Processar folha", type="primary"):
    rows = [r for r in edited if r.get("nome") and r.get("salario_base", 0) > 0]
    if not rows:
        st.error("Nenhum empregado válido na tabela.")
        st.stop()

    try:
        r = calc_folha_batch(rows, REGIMES[regime_label], competencia, rat_pct, fap)
    except APIError as e:
        st.error(str(e))
        st.stop()

    totais = r.get("totais", {})
    cols = st.columns(4)
    cols[0].metric("Bruto total", f"R$ {totais.get('total_bruto', 0):,.2f}")
    cols[1].metric("Líquido total", f"R$ {totais.get('total_liquido', 0):,.2f}")
    cols[2].metric("Custo empresa", f"R$ {totais.get('total_custo_empresa', 0):,.2f}")
    cols[3].metric("Empregados", str(len(r.get("empregados", []))))

    st.markdown("### Guias do mês")
    guias = r.get("guias", {})
    cols2 = st.columns(3)
    if "gps" in guias:
        with cols2[0]:
            st.markdown("**GPS — INSS**")
            st.metric("Total", f"R$ {guias['gps']['total']:,.2f}")
            st.caption(f"⏰ {guias['gps']['vencimento']}")
            with st.expander("Composição"):
                st.write(f"INSS empregados: R$ {guias['gps']['inss_empregados']:,.2f}")
                st.write(f"INSS patronal: R$ {guias['gps']['inss_patronal']:,.2f}")
                st.write(f"RAT × FAP: R$ {guias['gps']['rat_fap']:,.2f}")
                st.write(f"Terceiros: R$ {guias['gps']['terceiros']:,.2f}")
    if "fgts" in guias:
        with cols2[1]:
            st.markdown("**FGTS Digital**")
            st.metric("Total", f"R$ {guias['fgts']['total']:,.2f}")
            st.caption(f"⏰ {guias['fgts']['vencimento']}")
    if "irrf" in guias:
        with cols2[2]:
            st.markdown("**DARF 0561 — IRRF**")
            st.metric("Total", f"R$ {guias['irrf']['total']:,.2f}")
            st.caption(f"⏰ {guias['irrf']['vencimento']}")

    st.markdown("### Resultados individuais")
    individual_rows = []
    for e in r.get("empregados", []):
        individual_rows.append({
            "Nome": e.get("nome", ""),
            "Bruto": f"R$ {e.get('total_proventos', 0):,.2f}",
            "INSS": f"R$ {e.get('inss_empregado', 0):,.2f}",
            "IRRF": f"R$ {e.get('irrf', 0):,.2f}",
            "Descontos": f"R$ {e.get('total_descontos', 0):,.2f}",
            "Líquido": f"R$ {e.get('salario_liquido', 0):,.2f}",
            "Custo empresa": f"R$ {e.get('custo_empresa', 0):,.2f}",
            "FGTS": f"R$ {e.get('fgts', 0):,.2f}",
        })
    st.table(individual_rows)

    if r.get("erros"):
        st.error(f"⚠️ {len(r['erros'])} empregado(s) com erro:")
        st.json(r["erros"])

    with st.expander("Detalhe completo (JSON)"):
        st.json(r)
