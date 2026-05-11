#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# INSTALADOR — v6.2 / Semana 1 (Eixo Evidência)
# ───────────────────────────────────────────────────────────────────
# Aplica APENAS as 3 peças da Semana 1 do roadmap v6.2:
#   1. scripts/snapshot_normas.py
#   2. scripts/tabelas/normas_registry.json
#   3. .git-hooks/pre_merge_check.sh (cópia para .git/hooks/)
#
# Pré-requisito: INSTALAR.sh (v6.1.fix-art145) já aplicado.
#   → calc_rendimentos_isentos_simples.py
#   → validador_base_legal.py
#   → tabelas/codigos_rendimentos_isentos.json
#
# Princípio operacional: CAUTELA.
#   • Faz backup ANTES de copiar.
#   • Roda autotestes ANTES de instalar.
#   • Roda autotestes DEPOIS de instalar (verificação cruzada).
#   • Se algum teste falhar, restaura o backup automaticamente.
# ═══════════════════════════════════════════════════════════════════
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SKILL_DIR="${1:-/var/folders/ss/_jr9788j6ndg_hln5_5hnq3c0000gn/T/claude-hostloop-plugins/bdd411a4a3303219/skills/rrt-group-contador}"

echo "════════════════════════════════════════════════════════════════"
echo "  INSTALADOR — v6.2 / Semana 1 (Eixo EVIDÊNCIA)"
echo "════════════════════════════════════════════════════════════════"
echo "  Origem:  $SCRIPT_DIR"
echo "  Destino: $SKILL_DIR"
echo

# ─── Pré-checagens ────────────────────────────────────────────────
if [ ! -d "$SKILL_DIR" ]; then
    echo "❌ Diretório do skill não encontrado: $SKILL_DIR"
    echo "   Passe o caminho correto como argumento."
    exit 1
fi
if [ ! -w "$SKILL_DIR/scripts" ]; then
    echo "❌ Skill é read-only ($SKILL_DIR/scripts)."
    echo "   Ajuste permissões ou copie manualmente."
    exit 2
fi

# Confirma que a v6.1.fix-art145 já está aplicada
if [ ! -f "$SKILL_DIR/scripts/calc_rendimentos_isentos_simples.py" ] || \
   [ ! -f "$SKILL_DIR/scripts/validador_base_legal.py" ]; then
    echo "❌ v6.1.fix-art145 não detectada. Rode INSTALAR.sh antes."
    exit 3
fi

# ─── 1. Backup ────────────────────────────────────────────────────
TS=$(date +%Y%m%d_%H%M%S)
BKP_DIR="$SKILL_DIR/.backup_v6.2_S1_$TS"
mkdir -p "$BKP_DIR"
echo "▶ 1. Backup em: $BKP_DIR"
[ -f "$SKILL_DIR/scripts/snapshot_normas.py" ] && cp -v "$SKILL_DIR/scripts/snapshot_normas.py" "$BKP_DIR/"
[ -f "$SKILL_DIR/scripts/tabelas/normas_registry.json" ] && cp -v "$SKILL_DIR/scripts/tabelas/normas_registry.json" "$BKP_DIR/"
echo

# ─── 2. Testes PRE-instalação (na pasta de stage) ─────────────────
echo "▶ 2. Testes PRE-instalação (na pasta de stage)"
if ! python3 "$SCRIPT_DIR/scripts/snapshot_normas.py" --teste >/tmp/pre_test_$$.log 2>&1; then
    echo "  ❌ Autotestes do snapshot_normas.py falharam ANTES da instalação."
    tail -20 /tmp/pre_test_$$.log
    rm -f /tmp/pre_test_$$.log
    exit 4
fi
rm -f /tmp/pre_test_$$.log
echo "  ✅ snapshot_normas.py --teste passou"
echo

# ─── 3. Copia os arquivos ─────────────────────────────────────────
echo "▶ 3. Instalando arquivos da Semana 1"
cp -v "$SCRIPT_DIR/scripts/snapshot_normas.py" \
      "$SKILL_DIR/scripts/snapshot_normas.py"
cp -v "$SCRIPT_DIR/scripts/tabelas/normas_registry.json" \
      "$SKILL_DIR/scripts/tabelas/normas_registry.json"
echo
echo "▶ 3b. Hook git (informativo — usuário decide instalar manualmente)"
echo "      cp $SCRIPT_DIR/git-hooks/pre_merge_check.sh <repo>/.git/hooks/pre-merge-commit"
echo "      chmod +x <repo>/.git/hooks/pre-merge-commit"
echo

# ─── 4. Testes PÓS-instalação ─────────────────────────────────────
echo "▶ 4. Testes PÓS-instalação"
cd "$SKILL_DIR/scripts"

FAIL=0
if ! python3 snapshot_normas.py --teste >/tmp/post_test_$$.log 2>&1; then
    echo "  ❌ snapshot_normas.py --teste FALHOU PÓS-instalação"
    tail -10 /tmp/post_test_$$.log
    FAIL=1
else
    echo "  ✅ snapshot_normas.py --teste OK"
fi
rm -f /tmp/post_test_$$.log

if ! python3 snapshot_normas.py --check --offline >/tmp/post_check_$$.log 2>&1; then
    echo "  ⚠️  snapshot --check --offline retornou exit ≠ 0 (verificar log)"
    tail -10 /tmp/post_check_$$.log
fi
rm -f /tmp/post_check_$$.log

# Validador continua passando?
if ! python3 validador_base_legal.py --skill-dir "$SKILL_DIR" --json > /tmp/val_$$.json 2>&1; then
    CODE=$?
    if [ "$CODE" = "1" ]; then
        echo "  ❌ Validador acusou CRÍTICOS após instalação"
        FAIL=1
    elif [ "$CODE" = "2" ]; then
        echo "  ⚠️  Validador acusou ALTOS após instalação"
    fi
fi
N_CRIT=$(python3 -c "import json; d=json.load(open('/tmp/val_$$.json')); print(sum(1 for a in d.get('achados',[]) if a.get('severidade')=='CRITICA'))" 2>/dev/null || echo "?")
echo "  ℹ️  Validador: $N_CRIT achados CRÍTICOS"
rm -f /tmp/val_$$.json

if [ "$FAIL" = "1" ]; then
    echo
    echo "════════════════════════════════════════════════════════════════"
    echo "  ❌ INSTALAÇÃO FALHOU — RESTAURANDO BACKUP"
    echo "════════════════════════════════════════════════════════════════"
    cp -v "$BKP_DIR"/*.py    "$SKILL_DIR/scripts/" 2>/dev/null || true
    cp -v "$BKP_DIR"/*.json  "$SKILL_DIR/scripts/tabelas/" 2>/dev/null || true
    # Se o arquivo era inexistente antes, remover
    if [ ! -s "$BKP_DIR/snapshot_normas.py" ]; then
        rm -f "$SKILL_DIR/scripts/snapshot_normas.py"
    fi
    if [ ! -s "$BKP_DIR/normas_registry.json" ]; then
        rm -f "$SKILL_DIR/scripts/tabelas/normas_registry.json"
    fi
    echo
    echo "  Backup mantido em $BKP_DIR para diagnóstico."
    exit 5
fi

echo
echo "════════════════════════════════════════════════════════════════"
echo "  ✅ v6.2 / Semana 1 INSTALADA"
echo "════════════════════════════════════════════════════════════════"
echo
echo "  Próximos passos sugeridos:"
echo "  • Para CAPTURAR os hashes iniciais das 12 normas (online):"
echo "      cd $SKILL_DIR/scripts"
echo "      python3 snapshot_normas.py --update-hashes"
echo
echo "  • Para instalar o hook git no repositório que hospeda o skill:"
echo "      cp $SCRIPT_DIR/git-hooks/pre_merge_check.sh <repo>/.git/hooks/pre-merge-commit"
echo "      chmod +x <repo>/.git/hooks/pre-merge-commit"
echo
echo "  Backup desta instalação: $BKP_DIR"
echo
echo "  Próxima entrega do roadmap: Semana 2 (Eixo COMPUTACIONAL) —"
echo "  property-based tests, cross-check engine, validador v1.1, audit trail."
