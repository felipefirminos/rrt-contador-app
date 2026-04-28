# RRT Contador App

App interno da RRT Contabilidade — evolução da skill `rrt-group-contador v6.1.1`
(que continua existindo em paralelo) para uma aplicação web local com:

- **FastAPI** expondo o engine de cálculo brasileiro (62 scripts, ~32K LOC) via REST
- **Streamlit** com formulários para as calculadoras + chat Q&A
- **Camada LLM** (Anthropic Claude Opus 4.7) com `SKILL.md` cacheado como
  system prompt e as calculadoras expostas como **tools** — o assistente
  chama as funções reais ao invés de improvisar números

## Calculadoras expostas (v0.3 — 9 ferramentas, ~40 ainda no engine)

| Endpoint | Calc | Empiricamente validado |
|---|---|---|
| `POST /calc/simples-das` | DAS + Fator R + sublimite | RBT12 R$900K, Anexo V folha R$300K → migra Anexo III |
| `POST /calc/sugerir-anexo-engenharia` | CNAE 71.12, 71.11, 43.29 (SKILL.md §5) | Executa obras → IV; consultoria pura → III/V |
| `POST /calc/prolabore` | INSS 11% + CPP + IRRF (Lei 15.270) | R$5K/Presumido → líquido R$4.450, custo R$6K |
| `POST /calc/comparativo-regimes` | Simples × Presumido × Lucro Real | R$2.4M, margem 25%, 1 sócio R$8K + R$30K → recomenda Presumido |
| `POST /calc/rescisao` | 4 tipos (s/ JC, pedido, JC, acordo 484-A) | 5 anos R$5.8K → bruto R$32.622, multa R$12K |
| `POST /calc/folha-batch` | N empregados, GPS+FGTS+DARF 0561 | 3 empregados → bruto R$13.6K, GPS R$5.147,41 |
| `POST /calc/distribuicao-lucros` | Lei 15.270/2025 + transição | R$50.001 → líquido R$45.000,90 (efeito-salto) |
| `POST /calc/irpf` | Posição anual PF (CLT + deduções + carnê-leão + gcap) | R$8K/mês CLT + 1 dep + R$5K saúde → ZERADO |
| `POST /calc/cbs-ibs` | EC 132/2023 + LC 214/2025 | 2026: CBS 0,9% + IBS 0,1%; 2033: ~26,5% combinada |
| `POST /calc/cbs-ibs/projecao` | Projeção 2026-2033 ano-a-ano | Mostra carga em cada ano da transição |
| `POST /chat` | Q&A LLM com tools | 9 ferramentas expostas (8 calc + 1 sugeridor) |

## Qualidade

- **57 scripts upstream passam seus testes próprios** (~1835 asserções) na cópia em `engine/`
- **37 testes pytest** na API (`api/tests/`) cobrindo:
  - Auditoria contra os 7 erros recorrentes do SKILL.md (§1 CPP, §2 INSS 11%, §3 controvérsia Simples, §4 efeito-salto, §5 engenharia, §6 escrituração, §7 transição 2025-2028)
  - Incidências de rescisão (CLT 144 — férias indenizadas isentas)
  - Guias da folha (vencimentos GPS dia 20, FGTS dia 7, DARF 0561)
  - IRPF integrado (cenários CLT, vazio, gcap puro)
  - CBS/IBS (alíquotas 2026/2033, setores específicos, projeção)
  - Edge cases: validação Pydantic, propagação de erros do engine

```bash
cd api && python3 -m pytest tests/ -v   # 37 passed in 0.10s
```

## Arquitetura

```
rrt-contador-app/
├── engine/                        # Calc engine (sincronizado da skill)
│   ├── scripts/                   # 62 calc_*.py + 8 tabelas/*.json
│   ├── references/                # MD references (carregados no system prompt)
│   ├── recuperacao_tributaria/    # Teses, PER/DCOMP, etc.
│   └── SKILL.md                   # Governança RRT (carregada no system prompt)
├── api/                           # FastAPI
│   ├── app/
│   │   ├── main.py                # Entry + CORS
│   │   ├── config.py              # pydantic-settings, lê .env
│   │   ├── routers/
│   │   │   ├── calculators.py     # POST /calc/{simples-das, prolabore, comparativo-regimes}
│   │   │   ├── chat.py            # POST /chat e POST /chat/stream (SSE)
│   │   │   └── health.py          # GET /health
│   │   ├── services/
│   │   │   ├── engine.py          # Importa calc_*.py + define CALCULATOR_TOOLS
│   │   │   └── llm.py             # Anthropic SDK c/ tool-use loop e prompt caching
│   │   └── schemas/               # Pydantic v2
│   └── requirements.txt
├── web/                           # Streamlit
│   ├── Home.py                    # Dashboard / health
│   ├── pages/
│   │   ├── 1_Simples_Nacional.py
│   │   ├── 2_Pro_labore.py
│   │   ├── 3_Comparativo_Regimes.py
│   │   └── 4_Chat.py              # Q&A streaming + tool-call trace
│   ├── lib/api.py                 # cliente HTTP do front
│   └── requirements.txt
├── scripts/
│   ├── dev.sh                     # Sobe API + Web em paralelo
│   └── sync-engine.sh             # Repuxa engine da skill em ~/.claude/skills/
├── docs/
│   └── ADDING_CALCULATORS.md      # Padrão p/ expor mais calculadoras
├── .env.example
└── README.md
```

## Setup (primeira vez)

```bash
# 1. Instalar dependências (em um virtualenv idealmente)
python3 -m pip install --user -r api/requirements.txt
python3 -m pip install --user -r web/requirements.txt

# 2. Configurar credenciais
cp .env.example .env
# edite .env e preencha ANTHROPIC_API_KEY=sk-ant-...

# 3. Subir tudo
./scripts/dev.sh
# API:  http://127.0.0.1:8765/docs
# Web:  http://localhost:8501
```

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Status da API + engine + chave Anthropic |
| GET | `/docs` | Swagger UI (FastAPI auto) |
| POST | `/calc/simples-das` | DAS Simples Nacional (com Fator R, sublimite) |
| POST | `/calc/prolabore` | INSS sócio + CPP + IRRF + custo empresa |
| POST | `/calc/comparativo-regimes` | Simples × Presumido × Lucro Real (anual) |
| POST | `/calc/rescisao` | Rescisão CLT (4 tipos: s/ JC, pedido, JC, acordo 484-A) |
| POST | `/calc/folha-batch` | Folha de N empregados + guias consolidadas |
| POST | `/calc/distribuicao-lucros` | Distribuição de lucros + Lei 15.270/2025 |
| POST | `/calc/sugerir-anexo-engenharia` | Enquadramento Anexo IV vs III/V para CNAEs ambíguos |
| POST | `/calc/irpf` | Posição anual IRPF (CLT + deduções + carnê-leão + gcap) |
| POST | `/calc/cbs-ibs` | CBS+IBS de uma operação num ano (2026-2033) |
| POST | `/calc/cbs-ibs/projecao` | Projeção 2026-2033 da mesma operação |
| POST | `/chat` | Q&A síncrono (resposta + trace de tool calls) |
| POST | `/chat/stream` | Q&A com SSE (streaming) |

## LLM Q&A

O endpoint `/chat` serializa um system prompt com:

1. `engine/SKILL.md` (governança v6.1.1, regras de criticidade, erros recorrentes)
2. Todos os `engine/references/*.md` (tributário, trabalhista, societário, etc.)
3. Instruções operacionais (sempre chamar tools para cálculos)

O bloco inteiro é enviado com `cache_control: {"type": "ephemeral"}`, então só
paga input tokens cheios na primeira chamada — chamadas subsequentes (até 5min)
leem do cache (~10× mais barato).

As calculadoras expostas via tool-use ficam em `engine.CALCULATOR_TOOLS`. O
loop em `llm.chat()` resolve as chamadas server-side e devolve o resultado ao
modelo até ele parar de pedir tools.

## Sincronizar a skill upstream

```bash
./scripts/sync-engine.sh
# (depois reinicie a API para invalidar o cache do system prompt)
```

A skill original em `~/.claude/skills/rrt-group-contador/` continua sendo a
fonte de verdade. **Não edite scripts dentro de `engine/` neste repo** — faça
upstream e sincronize.

## Adicionar uma calculadora nova

Veja [`docs/ADDING_CALCULATORS.md`](docs/ADDING_CALCULATORS.md). Padrão de 3
arquivos: schema Pydantic → wrapper no `engine.py` → endpoint no router →
página Streamlit.

## Testes do engine

Os 1835 testes da skill continuam vivendo upstream — não duplicamos aqui.
Para rodar:

```bash
~/.claude/skills/rrt-group-contador/scripts/run_all_tests.sh
```

## Limitações conhecidas (v0.1)

- Sem persistência: não há histórico de cálculos por cliente/CNPJ ainda
- Sem auth: assumimos uso local single-tenant (rodando em 127.0.0.1)
- 3 calculadoras expostas (de ~60 disponíveis no engine)
- Parsers de PDF (DAS) e XML (NF-e) ainda não têm endpoint de upload
- Sem testes automatizados do API/UI (apenas smoke test manual)
