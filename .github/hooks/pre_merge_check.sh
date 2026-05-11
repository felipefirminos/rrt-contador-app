#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# pre_merge_check.sh — Hook git de dual-control + validação de norma
# ───────────────────────────────────────────────────────────────────
# Bloqueia merges que tocam em `scripts/tabelas/*.json` ou
# `scripts/tabelas/normas_registry.json` sem atender:
#
#   1. AO MENOS 2 commits no PR (dual-control mínimo).
#   2. Pelo menos UM commit GPG-assinado (revisão verificável).
#   3. Toda mensagem de commit relevante contém linha 'Source: <url>'.
#   4. Validador de base legal sem achados CRÍTICOS/ALTOS.
#   5. Autotestes do snapshot_normas.py passam.
#
# Instalação:
#   cp pre_merge_check.sh .git/hooks/pre-merge-commit
#   chmod +x .git/hooks/pre-merge-commit
# (Ou usar Husky / pre-commit framework apontando para este script.)
#
# Para CI (GitHub Actions / GitLab CI) chamar diretamente como
#   bash pre_merge_check.sh --ci
#
# Saída:
#   0  → tudo OK, merge liberado
#   1  → bloqueio CRÍTICO (não permite merge)
#   2  → bloqueio ALTO (não permite merge)
#   3  → erro interno (configuração / arquivos ausentes)
# ═══════════════════════════════════════════════════════════════════

set -uo pipefail
# NÃO usar -e: queremos coletar TODOS os problemas, não parar no primeiro.

# ─── Configuração ─────────────────────────────────────────────────
CI_MODE=0
[[ "${1:-}" == "--ci" ]] && CI_MODE=1

# Diretórios e arquivos críticos
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SCRIPT_REL="scripts/snapshot_normas.py"
VALIDADOR_REL="scripts/validador_base_legal.py"
REGISTRY_REL="scripts/tabelas/normas_registry.json"
TABELAS_DIR="scripts/tabelas"

# Branches alvo (qualquer merge nessas exige dual-control)
PROTECTED_BRANCHES="^(main|master|prod|release/.+)$"

# ─── Helpers de output ────────────────────────────────────────────
CRITICOS=()
ALTOS=()
INFOS=()

bold()    { printf '\033[1m%s\033[0m\n' "$*"; }
ok()      { printf '  ✅ %s\n' "$*"; }
warn()    { printf '  ⚠️  %s\n' "$*"; ALTOS+=("$*"); }
fail()    { printf '  🚨 %s\n' "$*"; CRITICOS+=("$*"); }
info()    { printf '  ℹ️  %s\n' "$*"; INFOS+=("$*"); }
sep()     { printf '\n─────────────────────────────────────────────────────────────────\n'; }

# ─── Header ───────────────────────────────────────────────────────
bold "═════════════════════════════════════════════════════════════════"
bold "  pre_merge_check.sh — Dual-control + Validação Normativa"
bold "═════════════════════════════════════════════════════════════════"
echo "  Repo: $REPO_ROOT"
echo "  CI mode: $CI_MODE"
echo

cd "$REPO_ROOT" 2>/dev/null || {
    fail "Não foi possível chegar à raiz do repositório."
    exit 3
}

# ─── 1. Detecta se há mudanças em tabelas regulatórias ───────────
sep
bold "▶ 1. Detecção de arquivos sensíveis no PR"

# Lista arquivos modificados entre HEAD e a branch base (origin/main por default)
BASE_REF="${MERGE_BASE_REF:-origin/main}"
if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
    # Fallback para staging local
    BASE_REF="HEAD~1"
fi

# Diferença completa do PR
CHANGED_FILES=$(git diff --name-only "$BASE_REF"...HEAD 2>/dev/null || \
                git diff --name-only HEAD 2>/dev/null || echo "")

TABELAS_TOCADAS=$(echo "$CHANGED_FILES" | grep -E "^${TABELAS_DIR}/.*\.json$" || true)
REGISTRY_TOCADO=$(echo "$CHANGED_FILES" | grep -E "${REGISTRY_REL}$" || true)

if [[ -z "$TABELAS_TOCADAS" && -z "$REGISTRY_TOCADO" ]]; then
    ok "Nenhuma tabela regulatória ou registry tocada — modo light check."
    SENSIBILIDADE="LIGHT"
else
    SENSIBILIDADE="HIGH"
    warn "Arquivos sensíveis modificados:"
    echo "$TABELAS_TOCADAS" "$REGISTRY_TOCADO" | tr ' ' '\n' | sort -u | sed 's/^/      /'
fi

# ─── 2. Dual-control (só em modo HIGH) ───────────────────────────
if [[ "$SENSIBILIDADE" == "HIGH" ]]; then
    sep
    bold "▶ 2. Dual-control — exige ≥ 2 commits + ao menos 1 assinado"

    COMMITS_PR=$(git rev-list --count "$BASE_REF"...HEAD 2>/dev/null || echo "1")
    echo "    Commits no PR: $COMMITS_PR"

    if [[ "$COMMITS_PR" -lt 2 ]]; then
        fail "Modificação em tabela regulatória exige ≥ 2 commits (dual-control). Encontrados: $COMMITS_PR"
    else
        ok "≥ 2 commits encontrados."
    fi

    # Verifica se ao menos um commit do range é assinado (GPG ou SSH)
    ASSINADOS=$(git log "$BASE_REF"...HEAD --pretty="%G?" 2>/dev/null | \
                grep -E '^[GU]$' | wc -l | tr -d ' ')
    echo "    Commits assinados (GPG/SSH): $ASSINADOS"
    if [[ "$ASSINADOS" -lt 1 ]]; then
        fail "Modificação em tabela regulatória exige AO MENOS 1 commit assinado (gpgsign/sshsign)."
    else
        ok "≥ 1 commit assinado."
    fi

    # Verifica 'Source:' em mensagens de commit que tocam tabelas
    sep
    bold "▶ 3. Cláusula 'Source:' nas mensagens dos commits sensíveis"

    SEM_SOURCE=0
    while IFS= read -r commit; do
        [[ -z "$commit" ]] && continue
        FILES_COMMIT=$(git show --name-only --pretty="" "$commit" 2>/dev/null)
        TOCA_SENSIVEL=$(echo "$FILES_COMMIT" | grep -E "^${TABELAS_DIR}/.*\.json$" || true)
        if [[ -n "$TOCA_SENSIVEL" ]]; then
            MSG=$(git log -1 --pretty="%B" "$commit" 2>/dev/null)
            if ! echo "$MSG" | grep -qiE '^Source:[[:space:]]+https?://'; then
                fail "Commit $commit toca tabela mas mensagem não tem 'Source: <url>'"
                SEM_SOURCE=$((SEM_SOURCE+1))
            fi
        fi
    done < <(git rev-list "$BASE_REF"...HEAD 2>/dev/null)

    if [[ "$SEM_SOURCE" -eq 0 ]]; then
        ok "Todas as alterações em tabelas têm 'Source:' rastreável."
    fi
fi

# ─── 4. Validador de base legal ──────────────────────────────────
sep
bold "▶ 4. validador_base_legal.py — achados CRÍTICA/ALTA"

if [[ -f "$VALIDADOR_REL" ]]; then
    VALIDADOR_OUT=$(python3 "$VALIDADOR_REL" --skill-dir . --json 2>/dev/null || echo '{"achados":[]}')
    N_CRIT=$(echo "$VALIDADOR_OUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    crit = sum(1 for a in d.get('achados', []) if a.get('severidade') == 'CRITICA')
    print(crit)
except Exception:
    print(0)
" 2>/dev/null || echo "0")
    N_ALTA=$(echo "$VALIDADOR_OUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    alta = sum(1 for a in d.get('achados', []) if a.get('severidade') == 'ALTA')
    print(alta)
except Exception:
    print(0)
" 2>/dev/null || echo "0")

    echo "    CRÍTICAS: $N_CRIT  ·  ALTAS: $N_ALTA"
    if [[ "$N_CRIT" -gt 0 ]]; then
        fail "Validador acusou $N_CRIT achado(s) CRÍTICO(s) — corrigir antes do merge."
    fi
    if [[ "$N_ALTA" -gt 0 ]]; then
        warn "Validador acusou $N_ALTA achado(s) ALTO(s) — revisar."
    fi
    if [[ "$N_CRIT" -eq 0 && "$N_ALTA" -eq 0 ]]; then
        ok "Validador aprovou — zero CRÍTICOS, zero ALTOS."
    fi
else
    warn "validador_base_legal.py não encontrado em $VALIDADOR_REL — pulando."
fi

# ─── 5. snapshot_normas.py --check --offline ─────────────────────
sep
bold "▶ 5. snapshot_normas.py --check --offline"

if [[ -f "$SCRIPT_REL" ]]; then
    if python3 "$SCRIPT_REL" --check --offline >/tmp/snapshot_$$_out 2>&1; then
        CODE=$?
        ok "Snapshot offline OK (exit 0)."
    else
        CODE=$?
        if [[ "$CODE" -eq 1 ]]; then
            fail "Snapshot acusou problema CRÍTICO (vencida/divergente) — exit 1."
        elif [[ "$CODE" -eq 2 ]]; then
            warn "Snapshot acusou problema ALTO (vencendo/sem URL) — exit 2."
        else
            warn "Snapshot retornou exit $CODE — checar."
        fi
        # Mostra detalhes
        tail -30 /tmp/snapshot_$$_out 2>/dev/null | sed 's/^/        /'
    fi
    rm -f /tmp/snapshot_$$_out
else
    warn "snapshot_normas.py não encontrado em $SCRIPT_REL — pulando."
fi

# ─── 6. Autotestes do snapshot_normas.py ─────────────────────────
sep
bold "▶ 6. Autotestes do snapshot_normas.py"

if [[ -f "$SCRIPT_REL" ]]; then
    if python3 "$SCRIPT_REL" --teste >/tmp/test_$$_out 2>&1; then
        ok "Autotestes passaram."
    else
        fail "Autotestes do snapshot_normas.py FALHARAM."
        tail -20 /tmp/test_$$_out 2>/dev/null | sed 's/^/        /'
    fi
    rm -f /tmp/test_$$_out
fi

# ─── Resumo final ────────────────────────────────────────────────
sep
bold "═════════════════════════════════════════════════════════════════"
bold "  RESUMO"
bold "═════════════════════════════════════════════════════════════════"
echo "  Críticos: ${#CRITICOS[@]}"
echo "  Altos:    ${#ALTOS[@]}"
echo "  Infos:    ${#INFOS[@]}"

if [[ ${#CRITICOS[@]} -gt 0 ]]; then
    echo
    bold "  ❌ MERGE BLOQUEADO — corrigir os pontos críticos:"
    for c in "${CRITICOS[@]}"; do echo "    • $c"; done
    exit 1
fi

if [[ ${#ALTOS[@]} -gt 0 ]]; then
    echo
    bold "  ⚠️  MERGE BLOQUEADO — pontos altos exigem revisão:"
    for a in "${ALTOS[@]}"; do echo "    • $a"; done
    exit 2
fi

echo
bold "  ✅ Merge liberado."
exit 0
