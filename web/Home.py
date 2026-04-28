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

st.subheader("Calculadoras disponíveis (v0.1)")
st.markdown(
    """
    | Calculadora | Página | Use quando |
    |---|---|---|
    | **DAS Simples Nacional** | `Simples_Nacional` | Apurar DAS mensal, validar Fator R, sublimite. |
    | **Pró-labore** | `Pro_labore` | Calcular INSS sócio + CPP + IRRF + custo total empresa. |
    | **Comparativo de Regimes** | `Comparativo_Regimes` | Comparar Simples × Presumido × Lucro Real (ano completo). |
    | **Q&A com LLM** | `Chat` | Pergunte qualquer coisa: o assistente cita base legal e chama as calculadoras automaticamente. |
    """
)

st.markdown("---")
st.subheader("Próximas calculadoras (roadmap)")
st.caption(
    "O engine já contém 60+ calculadoras Python — apenas 3 estão expostas via API/UI. "
    "Adicionar uma nova é um padrão de 3 arquivos: schema → engine wrapper → router. "
    "Veja `docs/ADDING_CALCULATORS.md`."
)

st.markdown(
    """
    - Rescisão (CLT) — `calc_rescisao.py`
    - Folha em lote — `calc_folha_batch.py`
    - 13º salário — `calc_13o.py`
    - Férias — `calc_ferias.py`
    - Hora extra — `calc_hora_extra.py`
    - IRPF integrado — `calc_irpf_integrado.py`
    - DIFAL ICMS — `calc_difal.py`
    - ICMS-ST — `calc_icms_st.py`
    - ISS — `calc_iss.py`
    - Lucro Presumido / Lucro Real / MEI — `calc_presumido.py` / `calc_lucro_real.py` / `calc_mei.py`
    - Distribuição de lucros (Lei 15.270/2025) — `calc_distribuicao_lucros.py`
    - Ganho de capital (imóvel, veículo, crypto, ETF exterior)
    - CBS/IBS Reforma Tributária — `calc_cbs_ibs.py`
    - Recuperação tributária + PER/DCOMP — `recuperacao_tributaria/`
    - Parser DAS PDF / NF-e XML
    """
)
