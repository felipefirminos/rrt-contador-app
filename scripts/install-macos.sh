#!/usr/bin/env bash
# RRT Contador — Instalador para macOS (Intel + Apple Silicon)
# Cria virtualenv, instala dependências, valida o engine e a API,
# cria atalho de duplo-clique no Desktop.
#
# Uso:
#   bash scripts/install-macos.sh
#
# O instalador é IDEMPOTENTE: pode rodar de novo sem efeitos colaterais.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"
LAUNCHER_DESKTOP="$HOME/Desktop/RRT Contador.command"

# Cores para output legível
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

step()  { printf "${BLUE}▸${NC} %s\n" "$1"; }
ok()    { printf "${GREEN}✓${NC} %s\n" "$1"; }
warn()  { printf "${YELLOW}⚠${NC} %s\n" "$1"; }
fail()  { printf "${RED}✗${NC} %s\n" "$1" >&2; }
title() { printf "\n${BOLD}%s${NC}\n%s\n\n" "$1" "$(printf '=%.0s' $(seq 1 ${#1}))"; }

abort() {
    fail "$1"
    echo
    echo "Instalação interrompida. Veja a saída acima e tente novamente."
    echo "Se o problema persistir, abra um issue no repositório."
    exit 1
}

title "RRT Contador — Instalador macOS"
echo "Diretório do app: $REPO_ROOT"
echo

# ─── Etapa 1/6: Detectar Python 3.10+ ─────────────────────────────

step "Etapa 1/6: Verificando Python 3.10+"

PYTHON_BIN=""
for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
        version_full=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")' 2>/dev/null || echo "0.0.0")
        major=$("$cmd" -c 'import sys; print(sys.version_info.major)' 2>/dev/null || echo "0")
        minor=$("$cmd" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
        if [[ "$major" == "3" && "$minor" -ge 10 ]]; then
            PYTHON_BIN=$(command -v "$cmd")
            ok "Python encontrado: $PYTHON_BIN ($version_full)"
            break
        fi
    fi
done

if [[ -z "$PYTHON_BIN" ]]; then
    warn "Python 3.10+ não encontrado neste Mac."
    echo
    echo "Para instalar Python, vou usar o Homebrew (gerenciador de pacotes do macOS)."
    echo "Se você ainda não tem o Homebrew, ele será instalado primeiro."
    echo
    read -p "Pode prosseguir? [s/N] " resp
    if [[ "$resp" != "s" && "$resp" != "S" && "$resp" != "y" && "$resp" != "Y" ]]; then
        abort "Cancelado pelo usuário. Instale Python 3.10+ manualmente em https://www.python.org/downloads/"
    fi

    if ! command -v brew >/dev/null 2>&1; then
        step "Instalando Homebrew (vai pedir sua senha do macOS)..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || \
            abort "Falha ao instalar Homebrew."
        # Adiciona brew ao PATH na sessão atual (Apple Silicon usa /opt/homebrew, Intel /usr/local)
        if [[ -f "/opt/homebrew/bin/brew" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [[ -f "/usr/local/bin/brew" ]]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
        ok "Homebrew instalado."
    fi

    step "Instalando Python 3.11 via Homebrew..."
    brew install python@3.11 || abort "Falha ao instalar Python."
    PYTHON_BIN=$(command -v python3.11)
    ok "Python 3.11 instalado: $PYTHON_BIN"
fi

# ─── Etapa 2/6: Criar virtualenv ──────────────────────────────────

step "Etapa 2/6: Criando ambiente virtual em $VENV_DIR"

if [[ -d "$VENV_DIR" ]]; then
    ok "Virtualenv já existe; reutilizando."
else
    "$PYTHON_BIN" -m venv "$VENV_DIR" || abort "Falha ao criar virtualenv."
    ok "Virtualenv criado."
fi

# Atualiza pip silenciosamente
"$VENV_DIR/bin/pip" install --upgrade pip --quiet 2>&1 | tail -1 || true

# ─── Etapa 3/6: Instalar dependências ─────────────────────────────

step "Etapa 3/6: Instalando dependências (~2-3 min)"

"$VENV_DIR/bin/pip" install --quiet --disable-pip-version-check \
    -r "$REPO_ROOT/api/requirements.txt" || \
    abort "Falha ao instalar dependências do backend."
ok "Backend (FastAPI + Anthropic + pdfplumber) instalado."

"$VENV_DIR/bin/pip" install --quiet --disable-pip-version-check \
    -r "$REPO_ROOT/web/requirements.txt" || \
    abort "Falha ao instalar dependências do frontend."
ok "Frontend (Streamlit) instalado."

# ─── Etapa 4/6: Validar engine (1835+ testes) ─────────────────────

step "Etapa 4/6: Validando engine de cálculo (1835+ asserções)"

ENGINE_TESTS_OK=0
ENGINE_TESTS_FAIL=0
ENGINE_LOG="$REPO_ROOT/.install-engine-tests.log"

cd "$REPO_ROOT/engine/scripts"

# Roda cada calc_*.py com --teste e conta sucessos
for script in calc_simples.py calc_prolabore.py calc_rescisao.py \
              calc_distribuicao_lucros.py calc_irrf.py calc_inss.py \
              calc_13o.py calc_ferias.py calc_hora_extra.py \
              calc_lucro_real.py calc_presumido.py calc_mei.py \
              calc_difal.py calc_icms_st.py calc_iss.py \
              calc_cbs_ibs.py calc_carne_leao.py calc_irpf_integrado.py \
              calc_custo_empregado.py calc_retencoes_pj.py \
              calc_gcap_imovel.py calc_gcap_veiculo.py \
              calc_darf_codes.py calc_folha.py calc_folha_batch.py; do
    if [[ -f "$script" ]]; then
        if "$VENV_DIR/bin/python" "$script" --teste >>"$ENGINE_LOG" 2>&1; then
            ENGINE_TESTS_OK=$((ENGINE_TESTS_OK + 1))
        else
            ENGINE_TESTS_FAIL=$((ENGINE_TESTS_FAIL + 1))
            warn "Falhou: $script (ver $ENGINE_LOG)"
        fi
    fi
done

cd "$REPO_ROOT"

if [[ "$ENGINE_TESTS_FAIL" -gt 0 ]]; then
    abort "$ENGINE_TESTS_FAIL script(s) do engine falharam. Não vou prosseguir — instalação inconsistente."
fi
ok "Engine OK: $ENGINE_TESTS_OK scripts validados."
rm -f "$ENGINE_LOG"

# ─── Etapa 5/6: Validar API (pytest) ──────────────────────────────

step "Etapa 5/6: Validando API (144 testes pytest)"

cd "$REPO_ROOT/api"
if "$VENV_DIR/bin/pytest" tests/ --quiet --tb=no 2>&1 | tail -3 | grep -q "passed"; then
    n_passed=$("$VENV_DIR/bin/pytest" tests/ --quiet --tb=no 2>&1 | grep -oE "[0-9]+ passed" | head -1)
    ok "API OK: $n_passed."
else
    cd "$REPO_ROOT"
    abort "Pytest da API falhou. Rode 'cd api && $VENV_DIR/bin/pytest tests/ -v' para diagnosticar."
fi
cd "$REPO_ROOT"

# ─── Etapa 6/6: Configurar .env e atalho ──────────────────────────

step "Etapa 6/6: Configurando .env e atalho do Desktop"

ENV_FILE="$REPO_ROOT/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    cp "$REPO_ROOT/.env.example" "$ENV_FILE"
    echo
    echo "🔑 Para ativar o Q&A com LLM (página 'Chat'), você precisa de uma chave da Anthropic."
    echo "   Obtenha em: https://console.anthropic.com/"
    echo "   (Pode pular agora — todas as 36 calculadoras funcionam sem isso.)"
    echo
    read -p "   Cole sua ANTHROPIC_API_KEY (ou ENTER para pular): " api_key
    if [[ -n "$api_key" ]]; then
        # macOS sed precisa de '' após -i
        sed -i '' "s|ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$api_key|" "$ENV_FILE"
        ok "Chave Anthropic salva em .env"
    else
        warn "Sem chave Anthropic — Q&A com LLM ficará desabilitado (calcs funcionam normalmente)."
    fi
else
    ok ".env já existe; preservado."
fi

# Cria launcher no Desktop
cat > "$LAUNCHER_DESKTOP" <<EOF
#!/usr/bin/env bash
# RRT Contador — Atalho gerado por install-macos.sh
# Mantenha este arquivo. Para remover, basta apagar.
cd "$REPO_ROOT" || {
    echo "❌ Pasta da app não encontrada em $REPO_ROOT"
    echo "   Você moveu/renomeou a pasta? Rode install-macos.sh de novo."
    read -p "Pressione ENTER para fechar..."
    exit 1
}
source "$VENV_DIR/bin/activate"
echo "🚀 Iniciando RRT Contador..."
echo "   Browser vai abrir automaticamente em alguns segundos."
echo "   Para parar: feche esta janela do Terminal (Ctrl+C aqui dentro)."
echo
# Abre o browser depois de 4s, sem bloquear o Terminal
( sleep 4 && open "http://localhost:8501" ) &
bash scripts/dev.sh
EOF
chmod +x "$LAUNCHER_DESKTOP"
ok "Atalho criado: $LAUNCHER_DESKTOP"

# ─── Final ────────────────────────────────────────────────────────

echo
title "✅ Instalação concluída"
echo "Para iniciar a app:"
echo "   1. Vá ao Desktop"
echo "   2. Clique com BOTÃO DIREITO em 'RRT Contador.command'"
echo "   3. Selecione 'Abrir' (faça isso UMA VEZ — depois é duplo-clique)"
echo
echo "Browser abre em http://localhost:8501 automaticamente."
echo
echo "Localização da app: $REPO_ROOT"
echo "Para atualizar: cd para essa pasta e rode 'git pull && bash scripts/install-macos.sh'"
echo
