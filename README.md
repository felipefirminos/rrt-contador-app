# RRT Contador App

App interno da RRT Contabilidade — evolução da skill `rrt-group-contador v6.1.1`
(que continua existindo em paralelo) para uma aplicação web local com:

- **FastAPI** expondo o engine de cálculo brasileiro (62 scripts, ~32K LOC) via REST
- **Streamlit** com formulários para as calculadoras + chat Q&A
- **Camada LLM** (Anthropic Claude Opus 4.7) com `SKILL.md` cacheado como
  system prompt e as calculadoras expostas como **tools** — o assistente
  chama as funções reais ao invés de improvisar números

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
