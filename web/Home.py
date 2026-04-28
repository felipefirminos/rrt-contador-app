from __future__ import annotations

import streamlit as st

from lib.api import health


st.set_page_config(page_title="RRT Contador", page_icon="📊", layout="wide")

st.title("RRT Contador")
st.caption("Engine v6.1.1 — Brazilian tax/labor calc engine + LLM Q&A • RRT Contabilidade")

h = health()
status = h.get("status")
cols = st.columns(4)
cols[0].metric("API", "ON" if status == "ok" else "OFF")
cols[1].metric("Engine", "OK" if h.get("engine_present") else "MISSING")
cols[2].metric("SKILL.md", "OK" if h.get("skill_md_present") else "MISSING")
cols[3].metric("Anthropic", "OK" if h.get("anthropic_configured") else "—")

if status != "ok":
    st.error(
        f"API não respondeu. Suba o backend antes de continuar.\n\n"
        f"Detalhe: `{h.get('error', 'sem resposta')}`"
    )
else:
    st.success("Tudo pronto. Use o menu lateral para acessar as calculadoras ou o Q&A.")

st.markdown("---")

st.subheader("Calculadoras disponíveis (v0.3)")
st.markdown(
    """
    | Calculadora | Página | Use quando | Base legal |
    |---|---|---|---|
    | **DAS Simples Nacional** | `Simples Nacional` | Apurar DAS mensal, Fator R, sublimite. Inclui sugeridor de Anexo para CNAEs ambíguos de engenharia. | LC 123/2006, Res. CGSN 140/2018 |
    | **Pró-labore** | `Pro labore` | INSS sócio (11%) + CPP + IRRF + custo total empresa. | IN RFB 971/2009, Lei 15.270/2025 |
    | **Comparativo de Regimes** | `Comparativo Regimes` | Simples × Presumido × Lucro Real (ano completo). | Múltiplas (LC 123, RIR, etc.) |
    | **Rescisão** | `Rescisao` | 4 tipos (s/ JC, pedido, JC, acordo 484-A). | CLT 477-484-A, Lei 12.506 |
    | **Folha em Lote** | `Folha Batch` | N empregados → guias GPS/FGTS/DARF 0561. | CLT, Lei 8.212, Lei 8.036 |
    | **Distribuição de Lucros** | `Distribuicao Lucros` | IRRF 10%, regra de transição, alerta Simples. | Lei 15.270/2025 + Lei 9.249 |
    | **IRPF — Posição Anual** | `IRPF` | CLT + deduções + carnê-leão + ganho de capital. | Lei 9.250/95 + Lei 15.270/2025 + RIR/2018 |
    | **CBS / IBS — Reforma** | `CBS IBS` | Operação 2026-2033 + projeção da transição. | EC 132/2023 + LC 214/2025 |
    | **Q&A com LLM** | `Chat` | Pergunte: o assistente cita base legal e chama todas as 9 ferramentas como tools. | SKILL.md cacheado |
    """
)

st.markdown("---")
st.subheader("Próximas calculadoras (roadmap)")
st.caption(
    "O engine já contém 60+ calculadoras Python — 6 expostas via API/UI. "
    "Adicionar uma nova é um padrão de 3 arquivos: schema → engine wrapper → router. "
    "Veja `docs/ADDING_CALCULATORS.md`."
)

st.markdown(
    """
    - 13º salário — `calc_13o.py`
    - Férias — `calc_ferias.py`
    - Hora extra — `calc_hora_extra.py`
    - IRPF integrado — `calc_irpf_integrado.py` (carnê-leão, ganho de capital)
    - DIFAL ICMS — `calc_difal.py`
    - ICMS-ST — `calc_icms_st.py`
    - ISS — `calc_iss.py`
    - Lucro Presumido / Lucro Real / MEI — `calc_presumido.py` / `calc_lucro_real.py` / `calc_mei.py`
    - Ganho de capital (imóvel, veículo, crypto, ETF exterior)
    - CBS/IBS Reforma Tributária — `calc_cbs_ibs.py`
    - Recuperação tributária + PER/DCOMP — `recuperacao_tributaria/`
    - Parser DAS PDF / NF-e XML
    """
)
