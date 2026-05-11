# Roadmap rrt-group-contador v6.2 — Costura Anti-Erro

**Tema**: "v6.2 não adiciona cálculos novos. Adiciona costura."
Costura entre **código e norma** · entre **código e código** · entre **código e humano**.

**Origem**: Mesa redonda Dev × Juíza × Designer (2026-05-11) após incidente
Art. 145 Res. CGSN 140/2018 relatado por Felipe Firmino.

**Premissa**: v6.1.1 já é robusta — 33k linhas Python, 31 calculadoras, 48
scripts com `--teste`, validadores existentes. O gap não é cobertura, é
**rastreabilidade probatória**, **redundância computacional** e **fidelidade
da mensagem ao usuário final**.

---

## Eixo 1 — EVIDÊNCIA (lidera: Juíza)

> *"A pergunta certa não é 'esse cálculo está certo?'. É: 'que prova temos
> de que está certo HOJE, com a vigência atual da norma?'"*

### 1.1 `normas_registry.json` — registro central de fontes

Arquivo único em `scripts/tabelas/normas_registry.json` listando TODAS as
normas-base do skill, no formato:

```json
{
  "Res_CGSN_140_2018_Art145": {
    "norma": "Resolução CGSN nº 140/2018",
    "artigo": "Art. 145, §§ 1° e 2°",
    "tema": "Isenção IRPF lucros sócio Simples",
    "url_oficial": "https://www.gov.br/receitafederal/.../resolucao-cgsn-140-2018",
    "url_cache_econet": "https://www.econeteditora.com.br//bdi/res/rs18/res_cgsn_140_2018.php#art145",
    "data_captura": "2026-05-11",
    "hash_sha256_pdf": "<a calcular>",
    "vigencia_inicio": "2018-05-22",
    "vigencia_ate": "permanente",
    "revisado_por": "felipe.firmino@rrtgroup.com.br",
    "scripts_que_dependem": [
      "calc_rendimentos_isentos_simples.py",
      "scripts/tabelas/codigos_rendimentos_isentos.json"
    ],
    "ultima_verificacao_externa": "2026-05-11"
  }
}
```

**Mínimo viável**: 12 normas (Lei 9.249/95, LC 123/06, IN RFB 971/09, IN RFB
2.055/21, IN RFB 2.312/26, Res. CGSN 140/18, Lei 15.270/25, Lei 14.754/23,
Lei 12.431/11, Lei 9.250/95, RIR/2018, CLT consolidada).

### 1.2 Snapshot trimestral de normas (`scripts/snapshot_normas.py`)

CLI que:
- baixa cada norma do `url_oficial`,
- calcula `sha256` do conteúdo,
- compara com `normas_registry.json`,
- se hash diverge → abre task no TodoList interno + e-mail para o
  contador-chefe + flag amarela no validador.

**Cadência**: cron trimestral + execução manual antes de cada release.

### 1.3 Dual-control para mudanças em tabelas regulatórias

Qualquer PR que toque em `scripts/tabelas/*.json` (alíquotas, presunções,
tetos INSS/IRRF, salário mínimo, dependentes) exige:

- 2 commits assinados (contador-chefe + 1 par revisor),
- mensagem de commit contendo `Source:` com URL oficial e data,
- bloqueio automático via hook git pré-merge (`scripts/pre_merge_check.sh`).

### 1.4 Cláusula de Julgamento Profissional 2.0 (dinâmica)

Substitui o disclaimer fixo. Cada output gera, com base no contexto:

```
⚖️ JULGAMENTO PROFISSIONAL OBRIGATÓRIO antes de assinar:
  □ Confirmar atividade econômica enquadrada (presunção 32% pressupõe serviços
    em geral — verificar CNAE primário).
  □ Validar IRPJ devido contra o PGDAS-D do período (R$ 5.400 informado).
  □ Confirmar ausência de pró-labore retirado no período (não aplicável a
    isenção §1°).
  □ Tabelas usadas: simples_nacional.json v2026.05 (vigência permanente);
    lucro_presumido.json v2026.05 (vigência permanente).
```

A lista é **gerada por inferência sobre o que o cálculo precisou presumir**.
Não é texto estático.

---

## Eixo 2 — ROBUSTEZ COMPUTACIONAL (lidera: Dev)

> *"Código que não existe não pode ser testado.
> Toda regra que aparece em conversa precisa ter um endpoint executável."*

### 2.1 Property-based testing (Hypothesis)

Adicionar `requirements.txt`: `hypothesis>=6.100`.

**Targets** (com invariantes legais, não valores absolutos):

| Script | Invariante |
|---|---|
| `calc_inss.py` | INSS sócio (CI) = 11% × min(base, teto). Para empregado CLT, INSS é monotonicamente crescente com base. |
| `calc_irrf.py` | IRRF ≥ 0; base 0 → IRRF 0; base no limite isenção → IRRF 0; aumentar base nunca diminui IRRF. |
| `calc_folha.py` | liquido = bruto − INSS − IRRF − descontos; liquido ≤ bruto sempre. |
| `calc_distribuicao_lucros.py` | Distribuir R$ 50K = isento; R$ 50.001 → líquido < R$ 50K (efeito-salto comprovado). |
| `calc_rendimentos_isentos_simples.py` | Forma 1 (com escrituração) sempre ≥ Forma 2 quando lucro líquido ≥ base presumida. |
| `calc_simples.py` | DAS ≥ 0; receita zero → DAS zero; faixa monotônica. |
| `calc_presumido.py` | IRPJ + CSLL + PIS + COFINS ≤ receita × 100%. |

Localização: `tests/properties/test_*.py`. Rodar 1.000 casos por property no CI.

### 2.2 Cross-validation engine (`scripts/cross_check.py`)

Para os 5 cálculos críticos abaixo, segunda implementação independente:

| Cálculo primário | Implementação alternativa |
|---|---|
| `calc_simples.calcular_das` | `cross_check.das_v2` — só NumPy, lê a mesma tabela mas com algoritmo recoded |
| `calc_inss.calcular_inss_clt` | `cross_check.inss_v2` — recursivo por faixa |
| `calc_irrf.calcular_irrf` | `cross_check.irrf_v2` — tabela inversa |
| `calc_rendimentos_isentos_simples.calcular_isencao_presuncao` | `cross_check.isencao_v2` — método simbólico |
| `calc_distribuicao_lucros.calcular_distribuicao` | `cross_check.distribuicao_v2` |

**Tolerância**: R$ 0,01. Se diverge:
- bloqueia retorno do cálculo primário,
- escreve `~/.rrt-cache/divergencias/<timestamp>_<calc>.json` com inputs,
  ambos os outputs e diff,
- abre task no TodoList interno,
- retorno do cálculo é `{"erro": "DIVERGENCIA_CROSS_CHECK", "divergencia_id": "..."}`.

### 2.3 Validador de base legal — expansão (v1.0 → v1.1)

Já existe (`validador_base_legal.py` v1.0 com 7 regras). Adicionar 5 regras
novas para a v1.1:

| Regra | Severidade | Detecta |
|---|---|---|
| `CONSTANTE_MAGICA_SEM_FONTE` | MEDIA | Float literal em código sem comentário `# Lei X / Art. Y` na mesma linha ou linha anterior |
| `TABELA_HARDCODED_NO_CODIGO` | ALTA | Lista/dict de faixas/alíquotas dentro de `.py` em vez de `.json` com `vigencia_ate` |
| `FUNCAO_PUBLICA_SEM_BASE_LEGAL` | MEDIA | `def calc_*` em retorno dict sem chave `"base_legal"` |
| `DOCSTRING_SEM_BASE_LEGAL` | BAIXA | Função pública sem citação de lei no docstring |
| `TABELA_VENCENDO_EM_30D` | ALTA | `vigencia_ate` < hoje+30d e ainda não foi renovada |

### 2.4 Audit trail estruturado (`~/.rrt-cache/audit/`)

Decorator `@audit_trail` aplicado a toda função pública de cálculo:

```python
@audit_trail(prazo_retencao_anos=5)  # prescrição fiscal
def calcular_rendimentos_isentos(...):
    ...
```

Grava em `~/.rrt-cache/audit/YYYY-MM-DD.jsonl` (1 linha por chamada):

```json
{"ts":"2026-05-11T14:32:01-03:00","calc":"calcular_rendimentos_isentos",
 "versao_script":"1.0.0","versao_tabelas":{"simples_nacional":"v2026.05",
 "lucro_presumido":"v2026.05"},"input":{...},"output":{...},
 "hash_inputs":"sha256:...","hash_output":"sha256:...","confianca":0.92}
```

Permite responder em fiscalização: *"Em 11/05/2026, com tabela v2026.05 e
input X, o sistema retornou Y."*

---

## Eixo 3 — CONFIABILIDADE NA INTERFACE (lidera: Designer)

> *"Os disclaimers existem mas se desencaixam do número no caminho.
> Precisamos costurar a confiança ao próprio resultado, não anexar."*

### 3.1 Saída em três camadas

Padronizar em `output_formatter.py` (já existe, expandir). Cada cálculo
público retorna:

```python
{
  "tldr": "Limite isento R$ 186.600 (sem escrituração; pode crescer com Balanço/DRE).",
  "executivo": [
    "Forma 2 (presunção) aplicável — empresa sem escrituração contábil regular.",
    "Receita R$ 600.000 × 32% (serviços) − R$ 5.400 (IRPJ no DAS) = R$ 186.600.",
    "Base legal: Res. CGSN 140/2018, Art. 145, §1°.",
    "⚠️ Com Balanço/DRE assinados, distribui-se o lucro líquido (Forma 1, §2°) — costuma ser maior."
  ],
  "tecnico": { /* dict atual completo */ },
  "confianca": 0.92,
  "julgamento_profissional": [ ... ],
}
```

### 3.2 Nível de confiança numérico

`confianca` ∈ [0.0, 1.0] calculada por:

```
confianca = 1.0
× (0.9 se houve estimativa/fallback, senão 1.0)
× (0.8 se tabela usada vence em ≤90d, 0.7 em ≤30d, senão 1.0)
× (0.85 se há controvérsia jurídica ativa no domínio, senão 1.0)
× (0.95 se algum input opcional ficou em default, senão 1.0)
× (1.0 - 0.05 × num_alertas_criticos)
clipped a [0.0, 1.0]
```

Regras de comportamento:
- `confianca ≥ 0.9` → output normal.
- `0.7 ≤ confianca < 0.9` → `tldr` prefixado com `⚠️ ATENÇÃO — `.
- `0.5 ≤ confianca < 0.7` → `tldr` prefixado com `🔴 ESTIMATIVA — VALIDAR ANTES DE USAR`.
- `confianca < 0.5` → retorno é erro: `{"erro": "CONFIANCA_INSUFICIENTE", "motivos": [...]}`.

### 3.3 Disclaimer inseparável nos renderizadores

Renderers atuais: `gerar_dossie_irpf`, `relatorio_integracao`, `rascunho_resposta`.

Mudança: a função `formatar_para_*` em cada renderer obrigatoriamente
concatena `tldr` + alerta CRÍTICO de maior severidade. Quem rendeniza
manualmente sem `formatar_para_*` recebe `DeprecationWarning`.

Linter de saída (`validador_base_legal.py` regra nova):
`OUTPUT_SEM_TLDR` — função `def gerar_relatorio*` que não usa
`output_formatter.formatar_saida_padronizada`.

### 3.4 Honeypots de erros históricos

Pasta `tests/honeypots/` com um arquivo por incidente já documentado:

```
tests/honeypots/
  2026_04_23_anexo_v_cpp_indevido.py     # v6.1 corrigiu — não pode voltar
  2026_04_23_inss_socio_progressivo.py   # v6.1 corrigiu — não pode voltar
  2026_05_11_art145_irpf_vs_irpj.py      # v6.2 corrigiu — não pode voltar
  2026_04_22_tema_478_vs_738.py          # v6.0 corrigiu — não pode voltar
  2026_04_22_tema_985_oportunidade.py    # v6.0 corrigiu — não pode voltar
```

Cada honeypot:
1. Recria o input que historicamente levou ao erro.
2. Roda o cálculo.
3. Verifica que o output NÃO é o valor errado.
4. Verifica que o output CONTÉM o alerta pedagógico esperado.

Rodam no `run_all_tests.sh` em fase obrigatória — **falha um, falha tudo**.

---

## Eixo 4 — OBSERVABILIDADE (transversal, dev)

`metrics.jsonl` agregado mensalmente por `dashboard_qualidade.py`:

| Métrica | Verde | Amarelo | Vermelho |
|---|---|---|---|
| % cálculos com `confianca ≥ 0.9` | ≥ 95% | 85-95% | < 85% |
| Divergências cross-check / 1000 chamadas | 0 | 1 | ≥ 2 |
| Tabelas com `vigencia_ate` ≤ 30d | 0 | 1 | ≥ 2 |
| Honeypots passando | 100% | n/a | < 100% |
| Achados ALTA do `validador_base_legal` | 0 | 1-3 | ≥ 4 |
| Alertas CRÍTICOS gerados / mês | < 5 | 5-20 | > 20 |

Dashboard renderiza em HTML estático que pode ser anexado a relatório
trimestral interno.

---

## Cronograma sugerido (4 semanas)

| Semana | Eixo | Entregas |
|---|---|---|
| **S1** | Evidência | `normas_registry.json` populado; `snapshot_normas.py`; pre-merge hook |
| **S2** | Computacional | Property-based tests (5 calculadoras); audit trail decorator; validador v1.1 |
| **S2** | Computacional | Cross-check engine para 5 cálculos críticos |
| **S3** | Interface | Output 3 camadas; nível de confiança; renderers atualizados |
| **S3** | Interface | Honeypots (5 incidentes mapeados) |
| **S4** | Observabilidade | `metrics.jsonl` + `dashboard_qualidade.py`; Cláusula Profissional 2.0 |
| **S4** | Release | Atualizar SKILL.md → v6.2; rodar suite completa; tag git |

---

## Critérios de aceitação v6.2

A v6.2 só sai com:

- [ ] 100% das calculadoras públicas retornam `tldr`, `executivo`, `tecnico`, `confianca`, `julgamento_profissional`.
- [ ] Property-based tests passando para 7 calculadoras-alvo (10.000 casos cada).
- [ ] Cross-check engine ativo em 5 cálculos críticos, 0 divergências em smoke test.
- [ ] `validador_base_legal.py` v1.1 rodando com 0 achados CRÍTICOS e 0 ALTOS.
- [ ] 5 honeypots passando.
- [ ] `normas_registry.json` com 12 normas-base catalogadas e hash conferido.
- [ ] Audit trail decorator em ≥ 80% das funções públicas.
- [ ] Dashboard de qualidade renderizando.
- [ ] Cláusula de Julgamento Profissional 2.0 ativa em todos os renderers.
- [ ] SKILL.md changelog v6.2 explicitando esses pontos.

---

## O que NÃO entra na v6.2

Para manter foco:

- ❌ Novas calculadoras (postpor para v6.3).
- ❌ Integração com ERPs além das pontes existentes.
- ❌ Reescrita arquitetural de scripts existentes.
- ❌ Migração de Python puro para framework (Flask/FastAPI etc.).

**v6.2 = consolidação defensiva. v6.3 = expansão.**

---

## Sinais de sucesso a observar nos 90 dias após release

1. Incidentes do tipo "fórmula errada repetida em conversa" → **zero**.
2. Tempo até detectar mudança normativa → de **dias** para **horas** (via snapshot).
3. Cálculos com `confianca < 0.7` no log → **< 5%** do volume.
4. Relatórios entregues com `tldr` no topo → **100%**.
5. Auditoria interna trimestral → **zero achados CRÍTICOS**.

---

*"v6.2 não adiciona cálculos novos. Adiciona costura."*
— Mesa redonda Dev × Juíza × Designer, 2026-05-11
