from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_rescisao  # noqa: E402


st.set_page_config(page_title="Rescisão Trabalhista", page_icon="✂️", layout="wide")
st.title("Rescisão Trabalhista")
st.caption(
    "CLT Arts. 477-484-A • Lei 12.506/2011 (aviso proporcional) • "
    "Reforma Trabalhista (Lei 13.467/2017)"
)

TIPOS = {
    "Dispensa sem justa causa": "sem_justa_causa",
    "Pedido de demissão": "pedido_demissao",
    "Justa causa (Art. 482 CLT)": "justa_causa",
    "Acordo mútuo (Art. 484-A CLT)": "acordo_mutuo",
}
AVISOS = {
    "Indenizado (paga)": "indenizado",
    "Trabalhado (cumpriu)": "trabalhado",
    "Dispensado (empregador abre mão sem desconto)": "dispensado",
}

with st.form("rescisao_form"):
    st.markdown("#### Vínculo")
    col1, col2, col3 = st.columns(3)
    with col1:
        tipo_label = st.selectbox("Tipo de desligamento", list(TIPOS.keys()))
        salario = st.number_input("Salário mensal (R$)", min_value=0.01, value=5800.0,
                                  step=100.0, format="%.2f")
    with col2:
        anos_servico = st.number_input(
            "Anos de serviço (completos)", min_value=0, value=5, step=1,
            help="Lei 12.506: aviso = 30 dias + 3/ano (máx 90 dias)",
        )
        media_adicionais = st.number_input(
            "Média de adicionais (HE/noturno) R$", min_value=0.0, value=0.0, format="%.2f",
        )
    with col3:
        aviso_label = st.selectbox("Aviso prévio", list(AVISOS.keys()))
        dias_trab_mes = st.number_input(
            "Dias trabalhados no mês", min_value=0, max_value=31, value=15, step=1,
        )

    st.markdown("#### Verbas proporcionais")
    col4, col5, col6 = st.columns(3)
    with col4:
        meses_13 = st.number_input("Avos de 13° (meses no exercício)",
                                   min_value=0, max_value=12, value=8, step=1)
    with col5:
        meses_ferias = st.number_input("Avos de férias proporcionais",
                                       min_value=0, max_value=12, value=8, step=1)
    with col6:
        num_dependentes = st.number_input("Dependentes (IRRF)", min_value=0, value=0, step=1)

    st.markdown("#### Férias vencidas e FGTS")
    col7, col8, col9 = st.columns(3)
    with col7:
        tem_vencidas = st.checkbox("Tem férias vencidas (concessivo expirado)")
    with col8:
        periodos_vencidas = st.number_input(
            "Períodos vencidos", min_value=0, max_value=2, value=1 if tem_vencidas else 0,
            disabled=not tem_vencidas, help="2 = férias dobradas (CLT Art. 137)",
        )
    with col9:
        saldo_fgts = st.number_input("Saldo FGTS (R$)", min_value=0.0, value=30000.0,
                                     step=1000.0, format="%.2f")

    submitted = st.form_submit_button("Calcular rescisão", type="primary")

if submitted:
    try:
        r = calc_rescisao(
            tipo=TIPOS[tipo_label],
            salario=salario,
            anos_servico=int(anos_servico),
            aviso_previo=AVISOS[aviso_label],
            dias_trabalhados_mes=int(dias_trab_mes),
            meses_13_proporcional=int(meses_13),
            meses_ferias_proporcional=int(meses_ferias),
            tem_ferias_vencidas=tem_vencidas,
            periodos_ferias_vencidas=int(periodos_vencidas) if tem_vencidas else 0,
            saldo_fgts=saldo_fgts,
            num_dependentes=int(num_dependentes),
            media_adicionais=media_adicionais,
        )
    except APIError as e:
        st.error(str(e))
        st.stop()

    cols = st.columns(3)
    cols[0].metric("Total bruto", f"R$ {r['total_bruto']:,.2f}")
    cols[1].metric("Total líquido", f"R$ {r['total_liquido']:,.2f}")
    cols[2].metric("Descontos (INSS+IRRF)", f"R$ {r['total_descontos']:,.2f}")

    st.markdown("### Verbas")
    verbas = [
        ("Saldo de salário", r.get("saldo_salario", 0), "Tributável (INSS+IRRF)"),
        (f"Aviso prévio {r.get('aviso_previo_dias', 0)}d ({r.get('aviso_previo_tipo', '-')})",
         r.get("aviso_previo_valor", 0), "Indenizatório (isento INSS/IRRF se indenizado)"),
        (f"13° proporcional ({r.get('meses_13', 0)}/12)",
         r.get("decimo_terceiro_prop", 0), "Cálculo separado de INSS/IRRF"),
        (f"Férias proporcionais ({r.get('meses_ferias', 0)}/12)",
         r.get("ferias_proporcionais", 0), "Indenizatório"),
        ("1/3 férias proporcionais", r.get("terco_ferias_prop", 0), "Indenizatório"),
        (f"Férias vencidas ({r.get('periodos_ferias_vencidas', 0)} período(s))",
         r.get("ferias_vencidas", 0), "Indenizatório"),
        ("1/3 férias vencidas", r.get("terco_ferias_vencidas", 0), "Indenizatório"),
        (f"Multa FGTS ({int(r.get('multa_fgts_pct', 0)*100)}% × R$ {r.get('saldo_fgts_informado', 0):,.2f})",
         r.get("multa_fgts", 0), "Indenizatório"),
    ]
    rows = [{"Verba": v, "Valor": f"R$ {val:,.2f}", "Natureza": nat}
            for (v, val, nat) in verbas if val != 0]
    st.table(rows)

    st.markdown("### Direitos pós-rescisão")
    cols2 = st.columns(2)
    cols2[0].markdown(
        f"**Saque FGTS:** {'✅ ' if r.get('direito_saque_fgts') else '❌ '}"
        f"{int(r.get('saque_fgts_percentual', 0)*100)}% do saldo"
    )
    cols2[1].markdown(
        f"**Seguro-desemprego:** "
        f"{'✅ Sim' if r.get('direito_seguro_desemprego') else '❌ Não'}"
    )

    if r.get("disclaimer_tipo"):
        st.warning(r["disclaimer_tipo"])

    with st.expander("Detalhe completo do cálculo (incl. INSS/IRRF)"):
        st.json(r)

    st.caption(f"📚 {r['base_legal']}")
