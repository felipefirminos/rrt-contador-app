# RRT Contador App

App interno da RRT Contabilidade — evolução da skill `rrt-group-contador v6.1.1`
(que continua existindo em paralelo) para uma aplicação web local com:

- **FastAPI** expondo o engine de cálculo brasileiro (62 scripts, ~32K LOC) via REST
- **Streamlit** com formulários para as calculadoras + chat Q&A
- **Camada LLM** (Anthropic Claude Opus 4.7) com `SKILL.md` cacheado como
  system prompt e as calculadoras expostas como **tools** — o assistente
  chama as funções reais ao invés de improvisar números

## Calculadoras expostas (v0.9 — 35 ferramentas + parsers + histórico + auto-record + IRPF dossiê)

### Tributário PJ
| Endpoint | Validação empírica |
|---|---|
| `POST /calc/simples-das` | Anexo V folha 33% → migra Anexo III |
| `POST /calc/sugerir-anexo-engenharia` | CNAE 71.12 executa obras → Anexo IV |
| `POST /calc/prolabore` | R$5K/Presumido → líquido R$4.450, custo R$6K |
| `POST /calc/comparativo-regimes` | R$2.4M serv 25% → Presumido vence |
| `POST /calc/distribuicao-lucros` | R$50.001 → líquido R$45.000,90 (efeito-salto) |
| `POST /calc/mei/resumo` | Comércio R$60K → DAS R$82,05; caminhoneiro R$150K → R$195,52 |
| `POST /calc/cbs-ibs` | 2026 CBS 0,9% + IBS 0,1%; 2033 ~26,5% combinada |
| `POST /calc/cbs-ibs/projecao` | Projeção 2026-2033 ano-a-ano |
| `POST /calc/recuperacao/tema-69` | LP R$60K ICMS → recupera R$2.190 (PIS R$390 + COFINS R$1.800) |
| `POST /calc/recuperacao/prescricao` | Pago 2018 → prescrito; 2024 → 993 dias restantes |
| `POST /calc/darf/{consultar,buscar,regime}` | 27+ códigos: IRPJ, CSLL, IRRF 0561, INSS, FGTS, DAS, etc. |

### Trabalhista (CLT)
| Endpoint | Validação empírica |
|---|---|
| `POST /calc/rescisao` | 5 anos R$5.8K → bruto R$32.622, multa R$12K (484-A: 50/20/80) |
| `POST /calc/folha-batch` | 3 empregados → GPS R$5.147 + FGTS R$1.088 + DARF 0561 R$646 |
| `POST /calc/decimo-terceiro` | R$5K × 12 → 1ª R$2.500 + 2ª R$1.998 + FGTS R$400 |
| `POST /calc/ferias` | 20+10 abono → base_INSS = férias gozadas+1/3 (CLT 144) |
| `POST /calc/hora-extra` | R$5K/220h → hora R$22,73; HE 50% × 10h = R$340,91 |

### Pessoa Física
| `POST /calc/irpf` | R$8K CLT + 1 dep + R$5K saúde → ZERADO |

### Trabalhista — calcs adicionais
| Endpoint | Validação empírica |
|---|---|
| `POST /calc/decimo-terceiro` | R$5K × 12 → 1ª R$2.500 + 2ª R$1.998 + FGTS R$400 |
| `POST /calc/ferias` | 20+10 abono → base_INSS = férias gozadas+1/3 (CLT 144) |
| `POST /calc/hora-extra` | R$5K/220h → hora R$22,73; HE 50% × 10h = R$340,91 |

### ICMS / ISS
| Endpoint | Validação empírica |
|---|---|
| `POST /calc/icms/difal` | R$1K destino 17% inter 12% → R$50; com frete R$200 → R$60 |
| `POST /calc/icms/st` | R$500 MVA 40% → BC R$700, próprio R$60, ST R$66 |
| `POST /calc/iss` | SP R$10K → R$500 (5%); Simples → 0 + base; não-mapeado → 5% |
| `POST /calc/iss/buscar-municipio` | Fuzzy search em 5K+ municípios |

### Recuperação tributária — adicionais
| Endpoint | Validação empírica |
|---|---|
| `POST /calc/recuperacao/tema-779` | MATERIA_PRIMA_DIRETA → FORTE 9,25%; MAO_DE_OBRA_PF → 0 (vedação) |
| `POST /calc/recuperacao/perdcomp-minuta` | Substitui placeholders → markdown 5K+ chars pronto p/ revisão |

### Parsers (multipart upload)
| Endpoint | Use |
|---|---|
| `POST /parser/das-pdf` | Guia DAS única — extrai tipo, CNPJ, competência, valores, atraso |
| `POST /parser/das-pdf-batch` | Até 50 guias (carteira inteira no fechamento mensal) |
| `POST /parser/xml-fiscal` | NF-e / NFC-e / NFS-e — detecta tipo, extrai estrutura completa |

### Apuração detalhada (Round G)
| Endpoint | Validação empírica |
|---|---|
| `POST /calc/lucro-presumido` | Serviços R$500K/trim → IRPJ R$34K, CSLL R$14,4K, total R$66,65K |
| `POST /calc/lucro-real` | Lucro R$300K → IRPJ R$69K + CSLL R$27K; compensação prejuízo limitada a 30% |

### Operacional dia-a-dia (Round H)
| Endpoint | Validação empírica |
|---|---|
| `POST /calc/custo-empregado` | R$3K Presumido → custo mensal R$4.866 (62,21% sobre salário); Simples I/III/V → R$3.870 |
| `POST /calc/retencoes-pj` | R$10K profissional → IRRF R$150 + CSRF R$465; Simples zero (exceto publicidade) |

### Pessoa Física — gcap + carnê-leão (Round I)
| Endpoint | Validação empírica |
|---|---|
| `POST /calc/gcap/imovel` | Ganho R$200K → imposto R$30K (15%); único <440K → isento |
| `POST /calc/gcap/veiculo` | Particular → isento; comercial R$10K ganho → R$1.500 (15%) |
| `POST /calc/gcap/crypto` | Modo GUIDANCE — checklist 12 itens + alertas |
| `POST /calc/gcap/etf-exterior` | Modo GUIDANCE — tratado de bitributação |
| `POST /calc/carne-leao` | USD 10K × PTAX → R$52.800 → IRRF R$13.611 (27,5%) |

### IRPF — Dossiê completo + Validador (Round L — v0.9)
| Endpoint | Use |
|---|---|
| `POST /calc/irpf/dossie` | Gera dossiê PF com 12 seções + opcionalmente valida (17 regras) |
| `POST /calc/irpf/validar` | Aplica as 17 regras em um dossiê pré-existente |

17 regras de consistência cruzada (R01-R17): IRRF cruzado, limites de
educação/PGBL, crypto custódia, exterior PTAX, comparativo
completa×simplificada, dependentes com CPF, bens exterior em BRL,
dividendos acima da isenção (Lei 15.270/2025), etc.

### Histórico + Inteligência (Round J — v0.7)

Primeira camada **stateful** da app: persistência SQLite (`data/rrt.db`) +
detector de padrões + sugestões proativas (calendário fiscal).

| Endpoint | Use |
|---|---|
| `POST /historico/registrar` | Grava interação (CNPJ + texto + tags + classificação + resultado) |
| `POST /historico/feedback` | Avalia (aprovado / rejeitado / ajustado) — feedback loop |
| `GET /historico/cliente/{cnpj}` | Lista últimas N interações por CNPJ |
| `POST /historico/buscar-tag` | Busca por tag (global ou restrita a cliente) |
| `GET /historico/estatisticas` | Stats: total, taxa aprovação, top tags/fluxos |
| `POST /historico/padroes` | Detecta sazonalidade (correlação calendário fiscal) + clusters + padrões correção |
| `POST /historico/sugestoes` | Alertas de prazo + lembretes recorrentes + antecipações |

Schema SQLite com índices em `cnpj`, `timestamp`, `avaliacao`. Tiebreaker
por `id DESC` (timestamp tem resolução de segundos). Schema migra
automaticamente na 1ª execução.

### Auto-record middleware (Round K — v0.8)

Qualquer chamada bem-sucedida em `/calc/*` é gravada automaticamente
no histórico se o request incluir o header `X-Cliente-CNPJ`. Opcional:
`X-Cliente-Texto` (ASCII) sobrescreve a descrição default.

```bash
curl -X POST http://127.0.0.1:8765/calc/simples-das \
  -H 'Content-Type: application/json' \
  -H 'X-Cliente-CNPJ: 12.345.678/0001-99' \
  -H 'X-Cliente-Texto: DAS Anexo III mar/2025' \
  -d '{"anexo":"III","rbt12":900000,"receita_mes":80000,"folha12":300000}'
```

Comportamento:
- **Opt-in**: sem header, middleware não interfere (nenhuma escrita)
- **Apenas /calc/***: parsers, chat, histórico e health ficam de fora
- **Apenas 2xx**: erros de validação (422) e exceções não poluem o histórico
- **Best-effort**: falha de gravação NUNCA quebra a resposta da calc
- **Tags inferidas do path**: `/calc/recuperacao/tema-69` → `['recuperacao', 'tema-69']`
- **Resultado preservado**: até 64KB do JSON da calc vai para `resultado_json`

#### Round M — Streamlit auto-record sidebar (v0.9)

Cada página de calc (Streamlit) agora inclui um painel "📚 Auto-record"
na sidebar via `lib.auto_record.render_sidebar()`. Preenchendo o CNPJ
uma vez, todas as chamadas seguintes da sessão são gravadas no histórico
sem precisar passar header manualmente.

`lib/api._post()` lê `st.session_state['ar_cnpj']` e injeta automaticamente
em headers `X-Cliente-CNPJ` / `X-Cliente-Texto`. Detecção via
`try: import streamlit` — fora do contexto Streamlit (testes), retorna
dict vazio (não interfere).

### LLM
| `POST /chat` + `POST /chat/stream` | 33 ferramentas como Anthropic tools |

## Qualidade

- **57 scripts upstream passam seus testes próprios** (~1835 asserções) na cópia em `engine/`
- **137 testes pytest** na API (`api/tests/`) cobrindo:
  - Auditoria contra os 7 erros recorrentes do SKILL.md (§1 CPP, §2 INSS 11%, §3 controvérsia Simples, §4 efeito-salto, §5 engenharia, §6 escrituração, §7 transição 2025-2028)
  - Incidências de rescisão (CLT 144 — férias indenizadas isentas)
  - Guias da folha (vencimentos GPS dia 20, FGTS dia 7, DARF 0561)
  - IRPF integrado (cenários CLT, vazio, gcap puro)
  - CBS/IBS (alíquotas 2026/2033, setores específicos, projeção)
  - 13º (1ª/2ª parcelas, FGTS), Férias (abono isento — CLT 144), HE (50/100%, DSR)
  - MEI (R$81K, excesso 20%, caminhoneiro), DARF (códigos por tributo/regime/busca)
  - Recuperação tributária: Tema 69 (modulação STF, alíquotas LR/LP), prescrição
    quinquenal, Tema 779 (4 forças por categoria), PER/DCOMP (placeholders)
  - DIFAL (com frete), ICMS-ST (cálculo + restituição), ISS (SP/Simples/não-mapeado)
  - Lucro Presumido (8 atividades, adicional, parcelamento 3x)
  - Lucro Real (LALUR, compensação 30%, PIS/COFINS não-cumulativo)
  - Custo CLT por regime (Simples isento, Anexo IV intermediário, Presumido pleno)
  - Retenções PJ→PJ (IRRF, CSRF, INSS cessão MO, exceção publicidade Simples)
  - Gcap imóvel (isenção 440K), veículo (particular vs comercial), crypto/ETF (GUIDANCE)
  - Carnê-leão (PTAX, dependentes, faixas IRRF)
  - Parsers: validação multipart, encoding, extensão, payload vazio
  - **Histórico SQLite** (Round J): registro/feedback/listagem/busca por tag,
    estatísticas com taxa de aprovação, padrões com sazonalidade, sugestões
    proativas com calendário fiscal — 15 testes
  - **Auto-record middleware** (Round K): opt-in via header, só /calc/*, só 2xx,
    tags inferidas do path, body preservado, best-effort em CNPJ inválido — 11 testes
  - **IRPF Dossiê + Validador** (Round L): 12 seções, 17 regras de consistência,
    regras_excluidas funciona, payload mínimo aceito — 6 testes
  - Edge cases: validação Pydantic, propagação de erros do engine

```bash
cd api && python3 -m pytest tests/ -v   # 137 passed in 0.42s
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
