# Relatório de Correção — Art. 145 Res. CGSN 140/2018

**Skill afetado:** `rrt-group-contador`
**Data:** 2026-05-11
**Autor:** Felipe Firmino (relato) + assistente Claude (implementação)
**Severidade do incidente:** ALTA — risco de cálculo errado de rendimentos
isentos do sócio do Simples Nacional na declaração de IRPF.

---

## 1. Resumo executivo

Foi relatado que uma das formas de calcular rendimentos isentos para IRPF
estava retornando resultado errado por usar fórmula em desacordo com a
**Resolução CGSN nº 140/2018, Art. 145**.

A fórmula informal que circulava era:

> **Forma 2: Faturamento Bruto × 32% − IRPF = Rendimentos Isentos**

Essa fórmula tem **três erros simultâneos**:

1. ❌ **"IRPF"** — o que se subtrai é o **IRPJ devido pelo Simples no
   período** (parte do DAS), NÃO o IRPF do sócio.
2. ❌ **"32%"** — não é fixo; varia por atividade conforme **Art. 15 da
   Lei 9.249/1995** (1,6% combustíveis · 8% comércio/indústria/cargas/
   hospitalares · 16% transp. passageiros/inst. financeiras · 32% serviços
   em geral/profissionais).
3. ❌ **Forma 2 aplicada universalmente** — pelo §2° do Art. 145, quando
   há escrituração contábil regular, **prevalece a Forma 1** (lucro
   líquido do DRE), sem o limite presumido.

### Causa-raiz na codebase

O skill `rrt-group-contador` **não tinha** um módulo dedicado ao cálculo
do Art. 145 — apenas referências esparsas:

- `tabelas/codigos_rendimentos_isentos.json` → código 13 com descrição
  vaga ("Isento até o limite de presunção"), sem fórmula nem distinção
  Forma 1/Forma 2.
- `calc_distribuicao_lucros.py` → trata da Lei 15.270/2025 (IRRF 10% sobre
  dividendos), **regra diferente** e aplicável a PJ em geral, não da
  isenção presumida do Simples.
- Nenhum script implementava a Forma 2 (§1°) ou a Forma 1 (§2°).

### Risco operacional

Sem implementação central correta, qualquer cálculo manual feito pela
equipe (planilha, conversa com cliente) poderia repetir a fórmula errada:

- **Por excesso de isenção:** declarar como isento um valor maior que o
  permitido → glosado em malha fina + multa + juros.
- **Por falta de isenção:** declarar como tributável um valor que poderia
  ser isento → pagamento indevido de IRPF.

---

## 2. O que foi feito

### 2.1 — Módulo novo `calc_rendimentos_isentos_simples.py`

Implementa as DUAS formas previstas no Art. 145, com:

- **Forma 1 (§2°)** — `calcular_isencao_escrituracao(lucro_liquido_dre)`
  - Limite = LUCRO LÍQUIDO − já distribuído. Sem teto presumido.
  - Alertas: lucro negativo, distribuição > lucro, exigência de DRE.
- **Forma 2 (§1°)** — `calcular_isencao_presuncao(receita, atividade, irpj)`
  - Limite = (Receita × % presunção Art. 15) − IRPJ no Simples.
  - Tabela completa de presunções por atividade (13 entradas).
  - Aliases para 14 sinônimos comuns (advocacia, consultoria, saúde, etc.).
  - Fallback de estimativa de IRPJ por anexo, com alerta de imprecisão.
- **Interface unificada** — `calcular_rendimentos_isentos(...)`
  - Calcula ambas, indica qual prevalece, separa isento × excedente
    tributável quando há distribuição efetiva.
- **49 testes internos** cobrindo: cenários oficiais; proteções
  anti-erro (verifica que NUNCA usa "32% sem subtrair IRPJ" e que
  NUNCA confunde IRPF/IRPJ); validações de input; aliases; serialização
  JSON para integração com `gerar_dossie_irpf.py`.

**Cenários oficiais validados:**

| Cenário | Receita | Atividade | IRPJ | Limite isento |
|---|---|---|---|---|
| 1 | R$ 600.000 | serviços | R$ 5.400 | **R$ 186.600** |
| 2 | R$ 1.200.000 | comércio | R$ 8.000 | **R$ 88.000** |
| 3 | R$ 500.000 | indústria | R$ 3.000 | **R$ 37.000** |
| 4 | R$ 100.000 | comércio | R$ 15.000 | **R$ 0,00** (IRPJ > base) |
| 18 mensal | R$ 50.000 | serviços | R$ 450 | **R$ 15.550** |

### 2.2 — Validador preventivo `validador_base_legal.py`

Sistema que escaneia TODO o skill em busca de 7 categorias de erros:

| Regra | Severidade | O que detecta |
|---|---|---|
| `ART145_IRPF_VS_IRPJ` | **CRÍTICA** | Fórmula "Faturamento × 32% − IRPF" |
| `PRESUNCAO_HARDCODED_32PCT` | MÉDIA | Uso de 32% sem contexto de atividade |
| `LEI_SEM_ANO` | BAIXA | "Lei 9.249" sem "/1995" associado |
| `PRESUNCAO_DIVERGENTE_DA_LEI` | ALTA | Tabela com % diferente da Lei 9.249/95 |
| `ISENTOS_SIMPLES_SEM_ART145` | MÉDIA | Doc/script sobre isentos sem citar Art. 145 |
| `IRRF10_SIMPLES_SEM_DISTINCAO` | MÉDIA | Lei 15.270/2025 misturada ao Simples sem distinção |
| `CALC_SEM_TESTE` | MÉDIA | Função `calcular_*` sem rotina de testes |

- **18 autotestes** confirmam que o validador detecta corretamente
  (e tolera contextos pedagógicos).
- Saída em texto colorido (default) ou JSON (`--json`) para CI.
- Exit code 1 em CRÍTICA, 2 em ALTA, 0 caso contrário.

### 2.3 — Atualização do `codigos_rendimentos_isentos.json`

Código 13 (lucros do Simples) reescrito com:

- Descrição precisa citando Art. 145.
- Detalhamento das DUAS formas e da diferença entre Forma 1 e Forma 2.
- Tabela de percentuais por atividade.
- ⚠️ Aviso explícito: "subtrai-se IRPJ devido pela EMPRESA, NÃO o IRPF do
  sócio".
- Apontador para `calc_rendimentos_isentos_simples.py`.

Também esclarecido o código 05 (dividendos de PJ NÃO-Simples — Lei 15.270/2025).

### 2.4 — Patches para `SKILL.md`, `references/tributario.md` e `references/checklist_irpf.md`

Documentação completa do Art. 145 com:

- Seção **3.A** nova no `tributario.md` com tabela de presunções, exemplo
  numérico, distinção frente à Lei 15.270/2025, controvérsia LC 123.
- Erro recorrente **nº 8** no `SKILL.md` (já existem 7 documentados).
- Reescrita da seção de Rendimentos Isentos no `checklist_irpf.md` com
  tabela "código CORRETO × código ERRADO frequente".
- Inclusão dos novos scripts na tabela de scripts do `SKILL.md`.
- Adição de comandos de teste ao `run_all_tests.sh`.

---

## 3. Como aplicar a correção

A pasta do skill é read-only no sandbox. Os arquivos abaixo estão prontos
para serem copiados para o repositório do skill (em
`/var/folders/.../skills/rrt-group-contador/`):

### Cópia direta (substituir/adicionar):

```bash
SKILL_DIR=/var/folders/ss/_jr9788j6ndg_hln5_5hnq3c0000gn/T/claude-hostloop-plugins/bdd411a4a3303219/skills/rrt-group-contador
PATCH_DIR="/Users/ffirmino/Documents/Claude/Projects/RRT CONTADOR - UPDATE/correcao_art145"

# 1. Scripts novos
cp "$PATCH_DIR/scripts/calc_rendimentos_isentos_simples.py" "$SKILL_DIR/scripts/"
cp "$PATCH_DIR/scripts/validador_base_legal.py" "$SKILL_DIR/scripts/"

# 2. Tabela atualizada (código 13 corrigido)
cp "$PATCH_DIR/scripts/tabelas/codigos_rendimentos_isentos.json" "$SKILL_DIR/scripts/tabelas/"

# 3. Validar
cd "$SKILL_DIR/scripts"
python3 calc_rendimentos_isentos_simples.py --teste
python3 validador_base_legal.py --teste
python3 validador_base_legal.py --skill-dir "$SKILL_DIR"
```

### Patches manuais (mesclar no arquivo existente):

- `references/SKILL_PATCH_secao_art145.md` → mesclar em `SKILL.md`
- `references/tributario_PATCH_art145.md` → inserir em `references/tributario.md`
- `references/checklist_irpf_PATCH.md` → substituir trecho em `references/checklist_irpf.md`

---

## 4. Resultado da auditoria do skill atual (linha de base)

Rodando `validador_base_legal.py` no skill original (antes das correções):

```
Total de achados: 27
  ⚠️ MEDIA: 5   (IRRF10_SIMPLES_SEM_DISTINCAO — alertas pedagógicos)
  ℹ️ BAIXA: 22  (LEI_SEM_ANO — cosméticos, citações sem /YYYY)

✅ ZERO achados CRÍTICOS
✅ ZERO achados ALTOS
```

**Bom achado**: o skill atual **não** continha o erro CRÍTICO da fórmula
"Fat × 32% − IRPF" em nenhum script. O risco estava na ausência de uma
implementação centralizada — qualquer cálculo manual ou improvisado pela
equipe poderia reproduzir o erro.

Os 5 alertas MEDIA são em arquivos que mencionam IRRF 10% (Lei 15.270/2025)
junto a "Simples" sem explicar a distinção entre Lei 15.270 (retenção
na fonte) e Art. 145 CGSN 140/2018 (limite de isenção). Recomendação:
após aplicar os patches do `SKILL.md` e `tributario.md`, esses alertas
podem ser silenciados via comentário em código ou link cruzado para a
seção 3.A do `tributario.md`.

Os 22 alertas BAIXA são citações de leis sem o ano explícito ("Lei 14.754"
em vez de "Lei 14.754/2023") — boa prática, não bug.

---

## 5. Validação final

```
calc_rendimentos_isentos_simples.py  →  49/49 testes ✅
validador_base_legal.py (autotestes) →  18/18 testes ✅
validador_base_legal.py (skill)      →  0 CRÍTICOS, 0 ALTOS ✅
```

---

## 6. Sistema preventivo — recomendações de processo

Para evitar recorrência:

1. **CI/CD**: incluir `python3 validador_base_legal.py --skill-dir .` no
   pipeline. Exit code 1 = falha de build.
2. **Pré-release**: rodar suite completa via `run_all_tests.sh` (já com
   os 2 novos scripts incluídos pelo patch).
3. **Code review**: qualquer PR que toque em "presunção", "isento",
   "IRPF de sócio do Simples" deve incluir referência ao Art. 145.
4. **Documentação cruzada**: o validador detecta arquivos que falem de
   isentos do Simples sem citar Art. 145 — manter isso passando.
5. **Conhecimento institucional**: a seção 3.A do `tributario.md` (com
   exemplo numérico) serve como referência pedagógica para a equipe.

---

## 7. Base legal consolidada

- **Resolução CGSN nº 140/2018, Art. 145, §§ 1° e 2°**
  ([econet](https://www.econeteditora.com.br//bdi/res/rs18/res_cgsn_140_2018.php#art145))
- **Lei 9.249/1995, Art. 15** (percentuais de presunção)
- **Lei 9.249/1995, Art. 10** (isenção genérica de dividendos)
- **LC 123/2006, Art. 14** (Simples Nacional e isenção)
- **Lei 15.270/2025** (IRRF 10% — regra paralela, NÃO substitui Art. 145)
