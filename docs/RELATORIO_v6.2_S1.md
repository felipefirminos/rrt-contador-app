# Relatório — v6.2 / Semana 1 (Eixo Evidência)

**Período:** 2026-05-11
**Status:** ✅ Entregue
**Princípio operacional:** Cautela — cada peça validada antes de avançar.

---

## O que foi entregue

| # | Peça | Localização | Status |
|---|---|---|---|
| 1 | `normas_registry.json` (12 normas) | `v6_2/scripts/tabelas/` | ✅ |
| 2 | `snapshot_normas.py` (auditor de hash) | `v6_2/scripts/` | ✅ |
| 3 | `pre_merge_check.sh` (hook dual-control) | `v6_2/git-hooks/` | ✅ |
| 4 | `INSTALAR_v6.2_S1.sh` (com rollback) | `v6_2/` | ✅ |

**Testes acumulados** (S1 + correção Art. 145):

| Suite | Total | Passou |
|---|---|---|
| `calc_rendimentos_isentos_simples.py --teste` | 49 | 49 ✅ |
| `validador_base_legal.py --teste` | 18 | 18 ✅ |
| `snapshot_normas.py --teste` | 26 | 26 ✅ |
| **TOTAL S1** | **93** | **93 ✅** |

**Linha de base do skill após S1**: 0 críticos, 0 altos (validador).

---

## Decisões de cautela tomadas

1. **Stage isolado** — arquivos vivem em `v6_2/` separados da v6.1.fix-art145 para inspeção antes do merge.
2. **Instalador com rollback automático** — `INSTALAR_v6.2_S1.sh` faz backup, testa pré e pós, e restaura se algo quebra.
3. **Hard-gate na captura de hash** — `snapshot_normas.py --force` exige `RRT_HASH_OVERRIDE=1` como segunda chave (evita sobrescrita acidental por automação).
4. **Hook git é instalação opcional** — descrito mas não copiado automaticamente para `.git/hooks/`, porque depende do repositório hospedeiro.
5. **Hashes ficam null no registry** — só serão preenchidos após a primeira captura online consciente, executada manualmente pelo contador-chefe (`snapshot_normas.py --update-hashes`).
6. **Validador continua aprovando o skill** — nenhum dos 3 arquivos novos introduziu achado crítico/alto.

---

## Detalhamento técnico

### 1. `normas_registry.json` — 12 normas catalogadas

```
• Lei 9.249/1995, Art. 10              (permanente)  — isenção dividendos
• Lei 9.249/1995, Art. 15              (permanente)  — presunções
• LC 123/2006, Arts. 13, 14 e 18       (permanente)  — Simples
• Res. CGSN 140/2018, Art. 145         (permanente)  — Art. 145 (incidente Felipe)
• IN RFB 971/2009                      (permanente)  — INSS sócio
• IN RFB 2.055/2021                    (permanente)  — PER/DCOMP
• IN RFB 2.312/2026                    (vence 2026-12-31)  — DIRPF 2026
• Lei 15.270/2025                      (permanente)  — IRRF 10% dividendos
• Lei 14.754/2023                      (permanente)  — exterior
• Lei 12.431/2011, Art. 3°             (permanente)  — CRI/CRA isentos
• Lei 9.250/1995                       (permanente)  — tabela IRPF
• RIR/2018 (Decreto 9.580/2018)        (permanente)  — regulamento
```

Cada entrada tem: `id`, `norma_curta`, `norma_completa`, `ementa`, `tema`, `url_oficial`, `url_cache_econet`, `vigencia_inicio`, `vigencia_ate`, `data_captura`, `hash_sha256_html`, `hash_sha256_pdf`, `revisado_por`, `ultima_verificacao_externa`, `scripts_que_dependem`, `tabelas_que_dependem`, `observacoes`.

20 scripts únicos referenciados pelas 12 normas — quando alguma muda, sabemos exatamente o que reauditar.

### 2. `snapshot_normas.py` — auditor de hash com vigência

**Modos:**
- `--check` (default) — só verifica. Exit 1 se há divergência/vencida; 2 se vencendo.
- `--update-hashes` — captura hashes faltantes pela primeira vez.
- `--force` — sobrescreve hashes existentes. Exige `RRT_HASH_OVERRIDE=1` (dual-control externo).
- `--offline` — não baixa, só valida vigências (para CI sem internet).
- `--json` — saída machine-readable.
- `--teste` — autotestes.

**Robustez:**
- Normalização do HTML antes de hash (remove scripts, CSRF tokens, timestamps, whitespace) → hash estável entre fetches sucessivos.
- Timeout de 15s por URL.
- User-Agent identificado (contato@rrtgroup.com.br).
- Falhas de rede viram `ERRO_FETCH`, nunca crash.

**Alertas de vigência:**
- ≤ 30 dias → status `VENCENDO` (alerta)
- < hoje → status `VENCIDA` (crítico)
- "permanente" / null → `PERMANENTE`

### 3. `pre_merge_check.sh` — hook dual-control

**O que verifica em modo HIGH** (quando o PR toca `scripts/tabelas/*.json`):

1. ≥ 2 commits no PR (dual-control mínimo).
2. ≥ 1 commit GPG/SSH-assinado.
3. Toda mensagem de commit sensível contém linha `Source: <url>`.

**O que verifica em qualquer modo:**

4. `validador_base_legal.py --skill-dir . --json` — zero achados CRÍTICA/ALTA.
5. `snapshot_normas.py --check --offline` — passou.
6. `snapshot_normas.py --teste` — passou.

**Resultado dos testes do hook:**
- ✅ Cenário saudável (sem tabelas tocadas) → exit 0 (libera merge).
- ✅ Cenário tóxico (1 commit, sem 'Source:', sem assinatura) → exit 1 (bloqueia merge), 3 críticos relatados.

---

## Como aplicar

```bash
# 1. Garantir que a correção Art. 145 (v6.1.fix) já está aplicada
bash /Users/ffirmino/Documents/Claude/Projects/RRT\ CONTADOR\ -\ UPDATE/correcao_art145/INSTALAR.sh

# 2. Aplicar Semana 1 da v6.2
bash /Users/ffirmino/Documents/Claude/Projects/RRT\ CONTADOR\ -\ UPDATE/correcao_art145/v6_2/INSTALAR_v6.2_S1.sh

# 3. (Opcional, online) Capturar hashes iniciais das 12 normas
cd <skill_dir>/scripts
python3 snapshot_normas.py --update-hashes

# 4. (Opcional) Instalar hook git no repo que hospeda o skill
cp /Users/ffirmino/Documents/Claude/Projects/RRT\ CONTADOR\ -\ UPDATE/correcao_art145/v6_2/git-hooks/pre_merge_check.sh \
   <repo>/.git/hooks/pre-merge-commit
chmod +x <repo>/.git/hooks/pre-merge-commit
```

O `INSTALAR_v6.2_S1.sh` faz backup, testa pré-instalação, instala, testa pós-instalação, e **restaura o backup se algo falhar**.

---

## Critérios de aceitação atendidos (S1)

- [x] `normas_registry.json` com 12 normas-base catalogadas.
- [x] Snapshot trimestral utilitário implementado (manual + CI offline).
- [x] Hook git com dual-control + 'Source:' obrigatório nas tabelas.
- [x] Autotestes de cada peça (26 do snapshot + integração).
- [x] Validador continua passando (0 críticos).
- [x] Instalador defensivo com rollback automático.

---

## Próximas semanas (lembrete)

- **S2 — Computacional:** property-based tests (Hypothesis), cross-check engine, validador v1.1, audit trail decorator.
- **S3 — Interface:** output 3 camadas, nível de confiança numérico, honeypots históricos.
- **S4 — Observabilidade:** dashboard de qualidade, Cláusula de Julgamento Profissional 2.0.

> Felipe, esta entrega da Semana 1 está pronta para revisão.
> Antes de seguir para a Semana 2, sugiro:
> 1. Rodar `INSTALAR_v6.2_S1.sh` no skill.
> 2. Executar `snapshot_normas.py --update-hashes` para capturar os hashes iniciais das 12 normas-base.
> 3. Validar 1-2 das URLs oficiais conferem com o conteúdo esperado.
> 4. Aprovar para começar a Semana 2.
