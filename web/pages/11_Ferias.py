from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_ferias  # noqa: E402


st.set_page_config(page_title="Férias", page_icon="🏖️")
st.title("Férias + 1/3 Constitucional")
st.caption(
    "CLT Arts. 129-153 + CF Art. 7° XVII • "
    "**REGRA CRÍTICA (CLT 144 + Súmula 386 TST):** abono pecuniário + 1/3 sobre abono "
    "são ISENTOS de INSS/IRRF"
)

with st.form("ferias"):
    col1, col2 = st.columns(2)
    with col1:
        salario = st.number_input("Salário (R$)", min_value=0.01, value=5000.0,
                                  step=100.0, format="%.2f")
        media_adic = st.number_input(
            "Média de adicionais (HE/noturno) R$", min_value=0.0, value=0.0,
            step=100.0, format="%.2f",
            help="Súmula 264 TST: incorpora ao cálculo de férias",
        )
    with col2:
        dias_ferias = st.number_input(
            "Dias de férias gozadas", min_value=0, max_value=30, value=20, step=1,
            help="Mínimo 20 quando há abono (CLT 143)",
        )
        dias_abono = st.number_input(
            "Dias de abono (vendidos)", min_value=0, max_value=10, value=10, step=1,
            help="Máximo 10 dias — abono pecuniário ISENTO de INSS/IRRF",
        )
    deps = st.number_input("Dependentes (IRRF)", min_value=0, value=0, step=1)
    submitted = st.form_submit_button("Calcular férias", type="primary")

if submitted:
    try:
        r = calc_ferias(
            salario=salario, dias_ferias=int(dias_ferias), dias_abono=int(dias_abono),
            num_dependentes=int(deps), media_adicionais=media_adic,
        )
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(3)
    cols[0].metric("Total bruto", f"R$ {r['total_bruto']:,.2f}")
    cols[1].metric("Total líquido", f"R$ {r['total_liquido']:,.2f}")
    cols[2].metric("Descontos (INSS+IRRF)", f"R$ {r['total_descontos']:,.2f}")

    st.markdown("### Verbas")
    rows = [
        {"Verba": f"Férias gozadas ({r['dias_ferias']} dias)", "Valor": f"R$ {r['ferias_gozadas']:,.2f}",
         "Natureza": "Tributável (INSS+IRRF)"},
        {"Verba": "1/3 constitucional", "Valor": f"R$ {r['terco_constitucional']:,.2f}",
         "Natureza": "Tributável"},
    ]
    if r["dias_abono"] > 0:
        rows.append({
            "Verba": f"Abono pecuniário ({r['dias_abono']} dias)",
            "Valor": f"R$ {r['abono_pecuniario']:,.2f}",
            "Natureza": "✅ ISENTO (CLT 144)",
        })
        rows.append({
            "Verba": "1/3 sobre abono",
            "Valor": f"R$ {r['terco_abono']:,.2f}",
            "Natureza": "✅ ISENTO",
        })
    st.table(rows)

    st.info(
        f"**Base do INSS/IRRF:** R$ {r['base_inss']:,.2f} "
        f"(apenas férias gozadas + 1/3, NÃO inclui abono)"
    )

    with st.expander("Detalhe completo"):
        st.json(r)

    st.caption(f"📚 {r['base_legal_ferias']}")
    st.caption(f"📚 Abono isento: {r['base_legal_abono_isento']}")
