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

st.subheader("Calculadoras disponíveis (v0.4 — 14 ferramentas)")
st.markdown(
    """
    **Tributário (Pessoa Jurídica)**

    | Calculadora | Página | Base legal |
    |---|---|---|
    | DAS Simples Nacional | `Simples Nacional` | LC 123/2006, Res. CGSN 140/2018 |
    | Pró-labore | `Pro labore` | IN RFB 971/2009, Lei 15.270/2025 |
    | Comparativo de Regimes | `Comparativo Regimes` | LC 123, RIR/2018 |
    | Distribuição de Lucros | `Distribuicao Lucros` | Lei 15.270/2025 + Lei 9.249 |
    | MEI (LC 188/2021) | `MEI` | LC 123/2006 + LC 188/2021 |
    | CBS / IBS Reforma | `CBS IBS` | EC 132/2023 + LC 214/2025 |
    | Recuperação tributária (Tema 69 + prescrição) | `Recuperacao` | RE 574.706 + LC 118/2005 |
    | Códigos DARF/GPS/DAS | `DARF Codes` | RFB + 27+ códigos |

    **Trabalhista (Fluxo 3 SKILL.md)**

    | Calculadora | Página | Base legal |
    |---|---|---|
    | Rescisão (4 tipos) | `Rescisao` | CLT 477-484-A, Lei 12.506 |
    | Folha em Lote | `Folha Batch` | CLT + Lei 8.212 + 8.036 |
    | 13º Salário | `13o` | Lei 4.090/1962 + CF 7° VIII |
    | Férias + 1/3 (abono isento) | `Ferias` | CLT 129-153 + Súmula 386 TST |
    | Hora extra + DSR | `Hora Extra` | CLT 59 + 70 + Lei 605/49 |

    **Pessoa Física**

    | Calculadora | Página | Base legal |
    |---|---|---|
    | IRPF — Posição Anual | `IRPF` | Lei 9.250/95 + Lei 15.270/2025 + RIR/2018 |

    **Q&A**

    | Página | Use |
    |---|---|
    | `Chat` | Pergunte qualquer coisa — o assistente cita base legal e chama as 14 calculadoras como tools |
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
    - DIFAL ICMS — `calc_difal.py`
    - ICMS-ST — `calc_icms_st.py`
    - ISS — `calc_iss.py`
    - Lucro Presumido / Lucro Real (apuração detalhada) — `calc_presumido.py` / `calc_lucro_real.py`
    - Ganho de capital (imóvel, veículo, crypto, ETF exterior)
    - Tema 779 STJ (insumo gerador de crédito) — `calcular_tema_779.py`
    - PER/DCOMP (template) — `templates/template_perdcomp.md`
    - Parser DAS PDF / NF-e XML
    - Carnê-leão isolado — `calc_carne_leao.py`
    - Histórico de cálculos por cliente/CNPJ
    """
)
