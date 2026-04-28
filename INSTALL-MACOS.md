# RRT Contador — Instalação no macOS

Guia em português para instalar a app no Mac de um colega contador.

> **Compatível com:** macOS 12 (Monterey) ou superior, Intel ou Apple Silicon.
> **Tempo total:** 5-10 minutos na primeira instalação.

---

## Antes de começar — o que você vai precisar

1. O arquivo `RRT-Contador-vX.X.X.zip` (vou enviar)
2. Permissão de administrador no Mac (vai pedir senha 1-2 vezes durante o setup)
3. (**Opcional**) Uma chave da API da Anthropic — só se você quiser usar o assistente de IA. As 36 calculadoras funcionam **sem** essa chave.

---

## Passo 1 — Extrair o ZIP

1. Salve o arquivo `RRT-Contador-vX.X.X.zip` numa pasta da sua escolha (recomendo `~/Documents`)
2. Dê **duplo-clique** no ZIP — o macOS extrai automaticamente
3. Vai aparecer uma pasta chamada `RRT-Contador-vX.X.X`

---

## Passo 2 — Rodar o instalador

1. Abra o **Terminal** (Spotlight → digite "Terminal" → ENTER)
2. Digite `cd ` (com espaço no final) e **arraste a pasta extraída para dentro do Terminal** (vai colar o caminho automaticamente)
3. Pressione ENTER
4. Cole o comando abaixo e pressione ENTER:

```bash
bash scripts/install-macos.sh
```

### O que vai acontecer

O script vai (em ~5 minutos, dependendo da sua máquina):

| Etapa | O que faz | Pode pedir senha? |
|---|---|---|
| 1/6 | Verifica se você tem Python 3.10+ | Não |
| 1/6 (caso falte) | Instala o Homebrew + Python | **Sim, 1 vez** |
| 2/6 | Cria um ambiente Python isolado dentro da pasta da app | Não |
| 3/6 | Instala as bibliotecas (FastAPI, Streamlit, etc.) | Não |
| 4/6 | **Valida o engine de cálculo** (1.835+ testes contábeis) | Não |
| 5/6 | **Valida a API** (144 testes adicionais) | Não |
| 6/6 | Pede sua chave Anthropic (opcional) e cria atalho no Desktop | Não |

> ⚠️ **Se qualquer teste falhar nas etapas 4 ou 5**, o instalador para e te avisa. Isso é proposital — uma instalação inconsistente seria perigosa em ambiente contábil real. Mande print do erro pro Richard.

No fim, vai aparecer:

```
✅ Instalação concluída
Para iniciar a app:
   1. Vá ao Desktop
   2. Clique com BOTÃO DIREITO em 'RRT Contador.command'
   3. Selecione 'Abrir' (faça isso UMA VEZ — depois é duplo-clique)
```

---

## Passo 3 — Iniciar a app pela primeira vez

### ⚠️ IMPORTANTE: aviso do macOS na primeira abertura

Como o atalho não é assinado pela Apple, o macOS vai bloquear na **primeira vez** com uma janela tipo:

> _"RRT Contador.command" não pôde ser aberto porque é de um desenvolvedor não identificado._

**Solução (faz só uma vez):**

1. Vá ao Desktop
2. Clique com **botão direito** em `RRT Contador.command`
3. Selecione **"Abrir"** (não duplo-clique)
4. Aparece janela de aviso → clique **"Abrir"** novamente
5. Pronto. Da próxima vez basta duplo-clique normal.

### O que acontece quando você abre

- O **Terminal** aparece (deixe aberto enquanto usar a app)
- O **navegador** abre automaticamente em http://localhost:8501
- Você vê a página inicial da app com 26 calculadoras no menu lateral

### Para parar a app

Feche a janela do Terminal (Cmd+W) ou pressione **Ctrl+C** dentro dela.

---

## Como usar (5 minutos)

### 1. Ative o auto-record (uma vez)

Em qualquer página de calculadora (sidebar esquerda, expander **📚 Auto-record**), preencha o CNPJ do cliente. A partir daí, todos os cálculos da sessão ficam gravados no histórico desse cliente.

### 2. Faça um cálculo de teste

Recomendo `Simples Nacional`:
- Anexo III, RBT12 R$900.000, receita do mês R$80.000, folha 12 meses R$300.000
- Clique em **Calcular DAS** → veja o Fator R migrar para Anexo III, alíquota 12,04%, DAS R$9.632

### 3. Veja o histórico

Página `Historico Cliente` → digite o CNPJ → veja a interação registrada com tags do path.

### 4. Veja o dashboard

Página `Dashboard` → KPIs, top tags, sazonalidade, picos do calendário fiscal.

---

## Atualização da app

Quando o Richard publicar uma nova versão (`RRT-Contador-vX.Y.Z.zip` mais novo):

1. Pare a app (feche o Terminal)
2. Rode `bash scripts/install-macos.sh` na pasta atual — o script é **idempotente**, só atualiza o que precisa
3. Inicie de novo pelo atalho

Para sincronizar mudanças do **engine** (skill upstream):

```bash
bash scripts/sync-engine.sh
```

---

## Backup do histórico

A app guarda todo o histórico em `data/rrt.db` (SQLite, dentro da pasta da app). **Faça backup periodicamente:**

```bash
bash scripts/export-db.sh
```

Gera `backups/rrt-YYYY-MM-DD-HHMMSS.json` que você pode copiar para Drive/Dropbox/etc.

Para restaurar (em outro Mac):

```bash
bash scripts/import-db.sh backups/rrt-2025-04-28.json
```

---

## Problemas comuns

### "macOS não pode verificar este desenvolvedor"

Normal. Veja a seção **Passo 3** acima — clique direito → Abrir, **uma vez só**.

### "Python 3.10+ não encontrado" mesmo após instalar Homebrew

Feche e reabra o Terminal, ou rode `eval "$(/opt/homebrew/bin/brew shellenv)"` (Apple Silicon) ou `eval "$(/usr/local/bin/brew shellenv)"` (Intel).

### A app abre mas dá erro na página `Chat`

Você não configurou a chave Anthropic. As outras 26 páginas funcionam normalmente. Para configurar depois:

```bash
# edite o arquivo .env na pasta da app
nano .env
# substitua a linha ANTHROPIC_API_KEY= por sua chave
```

Reinicie a app pelo atalho do Desktop.

### Quero usar a app em outra máquina

1. No Mac antigo: `bash scripts/export-db.sh`
2. Copie o `.zip` da app + o JSON do backup para o novo Mac
3. No Mac novo: rode o instalador, depois `bash scripts/import-db.sh <arquivo>.json`

### A app está consumindo CPU/memória depois de fechar o Terminal

Force-stop:
```bash
pkill -f "uvicorn app.main"
pkill -f "streamlit run Home.py"
```

---

## ⚠️ Limites e responsabilidade profissional

Esta app calcula com base em:

- **Engine** validado por contador-chefe (skill `rrt-group-contador v6.1.1`)
- **1.835+ testes** internos do engine
- **144 testes** na camada API/UI

Mas:

- **Não substitui revisão profissional.** Use como ferramenta de **draft + sanity check**, nunca como número final que vai direto para o cliente sem revisão.
- **Tabelas (INSS, IRRF, PTAX, salário mínimo) ficam atualizadas via `sync-engine.sh`.** Esquecer de atualizar pode gerar números defasados.
- **Cálculos de risco alto** (Tema 69, IRPF dossiê, PER/DCOMP, distribuição Lei 15.270) **exigem revisão de contador-chefe + advogado tributarista** quando aplicável. A própria app exibe essa cláusula.

Para detalhes sobre níveis de confiança por tipo de cálculo, veja a seção "Tiers de risco" no README.md.

---

**Dúvidas?** Manda print do erro / mensagem para o Richard.
