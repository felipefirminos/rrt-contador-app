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

st.subheader("Calculadoras disponíveis (v1.0 — 35 ferramentas + parsers + histórico + auto-record + IRPF dossiê + dashboard)")
st.markdown(
    """
    **Tributário PJ — Apuração**

    | Calculadora | Página | Base legal |
    |---|---|---|
    | DAS Simples Nacional + sugeridor de Anexo | `Simples Nacional` | LC 123/2006, Res. CGSN 140/2018 |
    | **Lucro Presumido (apuração trimestral)** | `Lucro Presumido` | Lei 9.249/95 + Lei 9.718/98 |
    | **Lucro Real (LALUR + créditos PIS/COFINS)** | `Lucro Real` | Lei 9.430/96 + RIR/2018 + Lei 8.981/95 |
    | DIFAL ICMS | `DIFAL ICMS` | EC 87/2015 + LC 190/2022 |
    | ICMS-ST (Substituição Tributária) | `ICMS ST` | Convênio ICMS por produto |
    | ISS | `ISS` | LC 116/2003 + base 5K+ municípios |
    | Pró-labore | `Pro labore` | IN RFB 971/2009, Lei 15.270/2025 |
    | Distribuição de Lucros | `Distribuicao Lucros` | Lei 15.270/2025 |
    | Comparativo de Regimes | `Comparativo Regimes` | LC 123 + RIR/2018 |
    | **Custo Total CLT** | `Custo CLT` | Lei 8.212/91 + LC 123/2006 |
    | **Retenções PJ→PJ** | `Retencoes PJ` | IN RFB 1.234/2012 + Art. 30 Lei 10.833 |
    | MEI | `MEI` | LC 123/2006 + LC 188/2021 |
    | CBS / IBS Reforma | `CBS IBS` | EC 132/2023 + LC 214/2025 |
    | Códigos DARF/GPS/DAS | `DARF Codes` | RFB |

    **Tributário PJ — Recuperação**

    | Calculadora | Página | Base legal |
    |---|---|---|
    | Tema 69 STF + prescrição quinquenal | `Recuperacao` | RE 574.706 + LC 118/2005 |
    | Tema 779 STJ + minuta PER/DCOMP | `Tema 779 PERDCOMP` | REsp 1.221.170 + IN RFB 2.055/2021 |

    **Trabalhista (Fluxo 3 SKILL.md)**

    | Calculadora | Página | Base legal |
    |---|---|---|
    | Rescisão (4 tipos) | `Rescisao` | CLT 477-484-A, Lei 12.506 |
    | Folha em Lote | `Folha Batch` | CLT + Lei 8.212 + 8.036 |
    | 13º Salário | `13o` | Lei 4.090/1962 |
    | Férias (abono isento) | `Ferias` | CLT 129-153 + Súmula 386 TST |
    | Hora extra + DSR | `Hora Extra` | CLT 59 + 70 + Lei 605/49 |

    **Pessoa Física**

    | Calculadora | Página | Base legal |
    |---|---|---|
    | IRPF — Posição Anual | `IRPF` | Lei 9.250/95 + RIR/2018 |
    | **IRPF — Dossiê + Validador (NOVO v0.9)** | `IRPF Dossie` | 12 seções + 17 regras de consistência cruzada |
    | **Ganho de Capital (4 tipos) + Carnê-leão** | `Gcap e Carne Leao` | Lei 11.196/2005 + Lei 14.754/2023 + IN RFB 1.585 |

    **Parsers (upload)**

    | Função | Página | Use |
    |---|---|---|
    | DAS PDF (única + lote) + XML fiscal (NF-e/NFC-e/NFS-e) | `Parsers` | Conferência fiscal, fechamento mensal |

    **Histórico + Inteligência (v0.7 — v0.8)**

    | Função | Página | Use |
    |---|---|---|
    | Histórico SQLite por CNPJ + detector de padrões + sugestões proativas | `Historico Cliente` | Memória institucional do escritório, calendário fiscal automatizado |
    | Auto-record (v0.8) | _middleware transparente_ | Header `X-Cliente-CNPJ` em qualquer `/calc/*` grava automaticamente |
    | Auto-record sidebar (v0.9) | sidebar de cada página | Preencha o CNPJ uma vez — todas as calcs gravam no histórico |
    | **Dashboard executivo (v1.0)** | `Dashboard` | KPIs, sazonalidade, top clientes/tags, picos fiscais, clusters |
    | **Backup/restore (v1.0)** | `scripts/export-db.sh` / `import-db.sh` | Snapshot JSON do histórico, merge ou replace |

    **Q&A**

    | Página | Use |
    |---|---|
    | `Chat` | O assistente cita base legal e chama as 33 calculadoras como tools |
    """
)

st.markdown("---")
st.subheader("Próximas calculadoras (roadmap)")
st.caption(
    "O engine ainda tem ~35 calculadoras especializadas não expostas. "
    "Padrão de exposição: schema → engine wrapper → router → tool → page → pytest. "
    "Veja `docs/ADDING_CALCULATORS.md`."
)

st.markdown(
    """
    - Validador de consistência IRPF + dossiê — `validar_consistencia_irpf.py`
    - Histórico de cálculos por cliente/CNPJ — `registro_interacoes.py` (SQLite)
    - Detector de padrões e sazonalidade — `detector_padroes.py`
    - Sugestões proativas (prazos, lembretes) — `sugestoes_proativas.py`
    - Cross-skill router + mapa de clientes — `cross_skill_router.py` / `mapa_clientes.py`
    - Agendador Gestta (orquestração) — `agendador_gestta.py` / `orquestrador_gestta.py`
    - Ponte WhatsApp + classificador — `ponte_whatsapp.py` / `classificar_mensagem.py`
    """
)
