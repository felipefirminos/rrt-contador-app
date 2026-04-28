from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.api import APIError, calc_distribuicao_lucros  # noqa: E402


st.set_page_config(page_title="Distribuição de Lucros", page_icon="🪙", layout="wide")
st.title("Distribuição de Lucros")
st.caption(
    "Lei 15.270/2025 + Lei 9.249/95 art. 10 + LC 123/2006 art. 14 • "
    "Regras críticas RRT (SKILL.md §3, §4, §6, §7)"
)

with st.expander("⚠️ Pontos críticos — leia antes de calcular", expanded=False):
    st.markdown(
        """
        - **Efeito-salto (Lei 15.270/2025):** distribuição mensal por sócio > R$ 50.000
          dispara IRRF de **10% sobre o VALOR INTEGRAL** (não só excedente).
          Distribuir R$ 50.001 produz líquido **menor** que R$ 50.000.
        - **Regra de transição:** lucros apurados **e aprovados em ata até 31/12/2025**,
          se pagos até **31/12/2028**, mantêm **isenção total** (sem IRRF 10%).
          Documente a ata e o registro contábil.
        - **Escrituração regular obrigatória:** Balanço/DRE assinados por contador
          habilitado. Sem isso, RFB pode reclassificar como pró-labore
          (27,5% IRPF + 11% INSS sócio + retroativos + multa).
        - **Simples Nacional — controvérsia:** há tese sólida (CF art. 146 III 'd')
          de que Lei ordinária não pode afastar isenção da LC 123 art. 14.
          RFB tende a aplicar IRRF 10% mesmo no Simples — postura conservadora
          é reter; avaliar mandado de segurança / PER/DCOMP com OAB+CRC.
        """
    )

with st.form("distribuicao_form"):
    col1, col2 = st.columns(2)
    with col1:
        valor_mensal = st.number_input(
            "Valor distribuído no mês (R$ — total da empresa)",
            min_value=0.0, value=80000.0, step=1000.0, format="%.2f",
        )
        lucro_disponivel = st.number_input(
            "Lucro contábil disponível (R$, opcional)",
            min_value=0.0, value=0.0, step=10000.0, format="%.2f",
            help="Se > 0, o cálculo verifica se a distribuição cabe no lucro apurado",
        )
        regime = st.selectbox(
            "Regime tributário (opcional)",
            ["—", "simples", "presumido", "lucro_real"],
            help="'simples' adiciona alerta da controvérsia LC 123 × Lei 15.270",
        )
    with col2:
        tem_escrit = st.checkbox(
            "Empresa tem escrituração contábil regular?",
            value=True,
            help="Balanço/DRE assinados por contador habilitado",
        )
        lucro_aprovado_2025 = st.checkbox(
            "Lucro foi APURADO e APROVADO em ata até 31/12/2025",
            value=False,
            help="Se sim, mantém isenção total se pago até 31/12/2028 (regra de transição)",
        )
        st.markdown("**Distribuição entre sócios**")
        modo = st.radio(
            "Modo",
            ["Proporcional (igualitária)", "Desigual (lista por sócio)"],
            label_visibility="collapsed",
        )
        socios_input = st.text_input(
            "Valores por sócio (separados por vírgula, em R$)",
            value="30000, 50000",
            disabled=(modo != "Desigual (lista por sócio)"),
            help="Ex: 30000, 50000 — soma deve igualar valor_mensal",
        )

    submitted = st.form_submit_button("Calcular", type="primary")

if submitted:
    payload = {
        "valor_mensal": valor_mensal,
        "tem_escrituracao_regular": tem_escrit,
        "lucro_aprovado_ate_2025": lucro_aprovado_2025,
    }
    if lucro_disponivel > 0:
        payload["lucro_apurado_disponivel"] = lucro_disponivel
    if regime != "—":
        payload["regime_tributario"] = regime
    if modo == "Desigual (lista por sócio)":
        try:
            socios = [float(s.strip()) for s in socios_input.split(",") if s.strip()]
            payload["distribuicao_por_socio"] = socios
        except ValueError:
            st.error("Lista de sócios inválida — use números separados por vírgula.")
            st.stop()

    try:
        r = calc_distribuicao_lucros(**payload)
    except APIError as e:
        st.error(str(e))
        st.stop()

    if r.get("regra_transicao_aplicada"):
        st.success("✅ **Regra de transição aplicada** — IRRF 10% NÃO incide.")

    if r.get("controversia_simples"):
        st.warning(
            "⚖️ **Controvérsia Simples × Lei 15.270/2025** — veja alertas abaixo. "
            "Postura conservadora: reter o IRRF; avaliar ação preventiva c/ advogado."
        )

    cols = st.columns(3)
    irrf_total = r.get("irrf_dividendos_total", r.get("irrf_dividendos", 0))
    liq_total = r.get("valor_liquido_total", r.get("valor_liquido", 0))
    cols[0].metric("Distribuído", f"R$ {valor_mensal:,.2f}")
    cols[1].metric("IRRF 10% (total)", f"R$ {irrf_total:,.2f}")
    cols[2].metric("Líquido total", f"R$ {liq_total:,.2f}")

    if r.get("distribuicao_desigual"):
        st.markdown("### Por sócio")
        rows = []
        for d in r.get("distribuicao_detalhada", []):
            rows.append({
                "Sócio #": d.get("socio_indice"),
                "Bruto": f"R$ {d.get('valor_bruto', 0):,.2f}",
                "Excede R$50K?": "Sim" if d.get("excede_limite") else "Não",
                "IRRF": f"R$ {d.get('irrf_dividendos', 0):,.2f}",
                "Líquido": f"R$ {d.get('valor_liquido', 0):,.2f}",
            })
        st.table(rows)

    if r.get("alertas"):
        st.markdown("### Alertas")
        for a in r["alertas"]:
            if "CRÍTICO" in a or "🚨" in a:
                st.error(a)
            elif "CONTROVÉRSIA" in a or "⚖️" in a:
                st.warning(a)
            else:
                st.info(a)

    with st.expander("Detalhe completo (JSON)"):
        st.json(r)

    st.caption(f"📚 {r['base_legal']}")
