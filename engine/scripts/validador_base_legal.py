#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validador_base_legal.py — Sistema Preventivo Anti-Erro Legal
═════════════════════════════════════════════════════════════════════════════
Auditor automatizado que percorre TODO o skill `rrt-group-contador`
em busca de padrões que historicamente levaram a cálculos errados,
especialmente:

  1. Fórmulas que confundem IRPF com IRPJ (caso do Art. 145 §1°)
  2. Percentuais de presunção hard-coded em 32% sem checagem de atividade
  3. Citações de leis sem versionamento/vigência
  4. Inconsistências entre tabelas e fórmulas
  5. Documentação que não cita a base legal correta
  6. Cálculos que ignoram a hierarquia normativa
  7. Testes ausentes para regras críticas

Origem: 2026-05-11. Criado após incidente relatado por Felipe
        (RRT) — método de Forma 2 da presunção do Simples retornava
        resultado errado por confundir IRPF com IRPJ.

Exit codes:
    0 — sem alertas críticos
    1 — falhas críticas encontradas (CI falha)
    2 — apenas avisos (não bloqueia, mas requer atenção)

Uso:
    python3 validador_base_legal.py --skill-dir /caminho/para/skill
    python3 validador_base_legal.py --skill-dir . --json  # saída machine-readable
    python3 validador_base_legal.py --teste              # auto-testes do validador
"""
import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Optional


VERSAO_VALIDADOR = "1.0.0 (2026-05-11)"

SEVERIDADES = ("CRITICA", "ALTA", "MEDIA", "BAIXA", "INFO")


@dataclass
class Achado:
    """Representa um achado de auditoria."""
    severidade: str
    regra: str
    descricao: str
    arquivo: str
    linha: Optional[int] = None
    trecho: Optional[str] = None
    sugestao: Optional[str] = None
    base_legal: Optional[str] = None

    def __str__(self):
        loc = f"{self.arquivo}:{self.linha}" if self.linha else self.arquivo
        s = f"[{self.severidade}] {self.regra}\n  📁 {loc}\n  ➤ {self.descricao}"
        if self.trecho:
            s += f"\n  📝 {self.trecho.strip()}"
        if self.sugestao:
            s += f"\n  💡 {self.sugestao}"
        if self.base_legal:
            s += f"\n  ⚖️  {self.base_legal}"
        return s


# ═══════════════════════════════════════════════════════════════════
#  REGRAS DE AUDITORIA
# ═══════════════════════════════════════════════════════════════════
#
# Cada regra é uma função (caminho, conteudo) → list[Achado].
# As regras são chamadas para cada arquivo do skill.

# ─── REGRA 1: Erro do Art. 145 §1° (IRPF vs IRPJ na presunção) ───
RX_RECEITA_X_32_MENOS_IRPF = re.compile(
    r"(?:receita|faturamento)[\s\w]*[\*×x]\s*0?[.,]?32\s*[\-−]\s*irpf",
    re.IGNORECASE,
)
RX_BRUTO_X_32_MENOS_IRPF = re.compile(
    r"bruto\s*[\*×x]\s*32\s*%?\s*[\-−]\s*irpf",
    re.IGNORECASE,
)
RX_FORMA2_LITERAL_ERRADA = re.compile(
    r"forma\s*2\s*:?[\s\S]{0,80}(?:32\s*%?|0?[.,]?32)[\s\S]{0,40}[\-−]\s*irpf",
    re.IGNORECASE,
)

def regra_art145_irpj_vs_irpf(caminho: str, conteudo: str) -> List[Achado]:
    """Detecta a fórmula errada 'Faturamento × 32% − IRPF'."""
    achados = []
    # Pula o próprio arquivo de instruções do projeto e este validador
    base = os.path.basename(caminho)
    if base in ("validador_base_legal.py", "RELATORIO_CORRECAO.md",
                "calc_rendimentos_isentos_simples.py"):
        return achados
    # Pula o módulo de cálculo correto (que cita o erro em comentários para corrigir)
    if "calc_rendimentos_isentos_simples" in base:
        return achados

    for i, linha in enumerate(conteudo.splitlines(), 1):
        # Ignora linhas que sejam claramente do tipo "ERRO" / "ATENÇÃO" /
        # "INCORRETO" / "NÃO usar" — são alertas pedagógicos legítimos.
        marca_alerta = re.search(
            r"errad[ao]|incorret[ao]|n[aã]o\s+usar|nunca|atenção|alerta|"
            r"obsolet|deprecated|substitu|substitui|antigo",
            linha,
            re.IGNORECASE,
        )
        if marca_alerta:
            continue

        if (RX_RECEITA_X_32_MENOS_IRPF.search(linha) or
                RX_BRUTO_X_32_MENOS_IRPF.search(linha) or
                RX_FORMA2_LITERAL_ERRADA.search(linha)):
            achados.append(Achado(
                severidade="CRITICA",
                regra="ART145_IRPF_VS_IRPJ",
                descricao=(
                    "Encontrada fórmula 'Faturamento × 32% − IRPF' (errada). "
                    "O correto é '(Receita Bruta × % presunção Art. 15 Lei 9.249/95) "
                    "− IRPJ devido no Simples no período'."
                ),
                arquivo=caminho,
                linha=i,
                trecho=linha[:200],
                sugestao=(
                    "Use calc_rendimentos_isentos_simples.calcular_rendimentos_isentos(). "
                    "% NÃO é fixo em 32% e o que se subtrai é o IRPJ (parte do DAS), "
                    "não o IRPF do sócio."
                ),
                base_legal="Resolução CGSN 140/2018, Art. 145, §1°",
            ))
    return achados


# ─── REGRA 2: Percentual 32% hard-coded sem contexto ───
RX_32_PCT_HARDCODED = re.compile(
    r"\b(?:0\.32|0,32|32\s*%)\b",
)

def regra_presuncao_hardcoded(caminho: str, conteudo: str) -> List[Achado]:
    """
    Detecta uso de 32% hard-coded em contextos onde a presunção deveria
    variar por atividade. Marca como MEDIA (não CRITICA — pode ser válido
    em contexto de Lucro Presumido para serviços, por exemplo).
    """
    achados = []
    base = os.path.basename(caminho)

    # Whitelist — arquivos onde 32% pode aparecer legitimamente
    whitelist = (
        "validador_base_legal.py",
        "calc_rendimentos_isentos_simples.py",
        "lucro_presumido.json",      # tabela oficial
        "tributario.md",             # documentação que cita TODOS os %
        "calc_presumido.py",         # cálculo legítimo de presumido
        "calc_comparativo_regimes.py",
        "calc_distribuicao_lucros.py",
        "RELATORIO_CORRECAO.md",
        "patches",
    )
    if any(w in base for w in whitelist):
        return achados

    # Em outros arquivos, 32% sem contexto pode ser problemático
    for i, linha in enumerate(conteudo.splitlines(), 1):
        if RX_32_PCT_HARDCODED.search(linha):
            # Não alerta se a linha já cita "presunção" + "atividade"
            if re.search(r"presun.*ativ|ativ.*presun", linha, re.IGNORECASE):
                continue
            # Não alerta se está em string de teste
            if "teste" in linha.lower() or "test" in linha.lower():
                continue
            achados.append(Achado(
                severidade="MEDIA",
                regra="PRESUNCAO_HARDCODED_32PCT",
                descricao=(
                    "Uso de 32% hard-coded fora de contexto explícito. "
                    "Em cálculos de presunção (Art. 15 Lei 9.249/95 ou "
                    "Art. 145 §1° CGSN 140/2018), o % varia por atividade."
                ),
                arquivo=caminho,
                linha=i,
                trecho=linha[:200],
                sugestao=(
                    "Importe PRESUNCAO_IRPJ_ART15 de "
                    "calc_rendimentos_isentos_simples e use a chave correta."
                ),
                base_legal="Lei 9.249/1995, Art. 15",
            ))
    return achados


# ─── REGRA 3: Citação de lei sem vigência/data ───
# Detecta "Lei <numero>" não seguido de "/<ano de 4 dígitos>".
# Aceita números com separadores: "Lei 9.249", "Lei 14.754", "Lei 12431".
RX_LEI_SEM_ANO = re.compile(
    r"\bLei\s+\d{1,3}(?:[.,]\d{3})?\b(?!\s*[/.]\s*\d{2,4})",
)

def regra_lei_sem_versao(caminho: str, conteudo: str) -> List[Achado]:
    """Detecta citações 'Lei XXXX' sem ano associado (e.g. 'Lei 9.249' sem '/1995')."""
    achados = []
    base = os.path.basename(caminho)
    if base == "validador_base_legal.py":
        return achados
    # Reduz ruído: só roda em .md e .py
    if not caminho.endswith((".md", ".py")):
        return achados

    for i, linha in enumerate(conteudo.splitlines(), 1):
        for m in RX_LEI_SEM_ANO.finditer(linha):
            achados.append(Achado(
                severidade="BAIXA",
                regra="LEI_SEM_ANO",
                descricao=(
                    "Citação de lei sem ano explícito — dificulta "
                    "rastreamento de vigência e revogação."
                ),
                arquivo=caminho,
                linha=i,
                trecho=linha[:200],
                sugestao="Inclua o ano: 'Lei 9.249/1995' em vez de 'Lei 9.249'.",
            ))
    return achados


# ─── REGRA 4: Consistência percentuais de presunção × tabela oficial ───
PRESUNCAO_OFICIAL = {
    "comercio": 0.08,
    "industria": 0.08,
    "transporte_cargas": 0.08,
    "servicos_hospitalares": 0.08,
    "imobiliario": 0.08,
    "transporte_passageiros": 0.16,
    "instituicoes_financeiras": 0.16,
    "servicos": 0.32,
    "intermediacao": 0.32,
    "locacao_bens_moveis": 0.32,
    "profissionais": 0.32,
    "administracao": 0.32,
    "combustiveis": 0.016,
}

def regra_tabela_presuncao_oficial(caminho: str, conteudo: str) -> List[Achado]:
    """Valida que tabelas de presunção batem com a oficial (Art. 15 L.9.249/95)."""
    achados = []
    if not caminho.endswith("lucro_presumido.json"):
        return achados
    try:
        dados = json.loads(conteudo)
    except json.JSONDecodeError as e:
        achados.append(Achado(
            severidade="CRITICA",
            regra="TABELA_JSON_INVALIDO",
            descricao=f"JSON inválido: {e}",
            arquivo=caminho,
        ))
        return achados

    atividades = dados.get("atividades", {})
    if not atividades:
        return achados

    # Mapeamento exato nome→presunção esperada (Art. 15 Lei 9.249/95).
    # Use chaves de prefixo com '|' separando alternativas.
    # IMPORTANTE: serviços hospitalares são EXCEÇÃO legal (8%, não 32%) —
    # Art. 15, §1°, III, 'a' da Lei 9.249/95. Por isso o match é por
    # PALAVRA-CHAVE COMPLETA, não por substring de "servicos".
    PRESUNCOES_OFICIAIS = {
        # 1,6%
        0.016: ["combustiveis", "revenda_combustiveis", "revenda_de_combustiveis"],
        # 8%
        0.08:  ["comercio", "industria", "transporte_cargas",
                "transporte_de_cargas", "servicos_hospitalares",
                "servicos_de_saude", "imobiliaria", "imobiliario",
                "atividade_imobiliaria", "rural"],
        # 16%
        0.16:  ["transporte_passageiros", "transporte_de_passageiros",
                "instituicoes_financeiras", "factoring_bancario"],
        # 32%
        0.32:  ["servicos", "servicos_gerais", "servicos_profissionais",
                "intermediacao", "intermediacao_negocios",
                "intermediacao_de_negocios", "locacao_bens_moveis",
                "locacao_de_bens_moveis", "administracao",
                "administracao_de_bens", "factoring"],
    }
    # Construir lookup inverso (nome → percentual esperado)
    nome_para_pct = {}
    for pct, nomes in PRESUNCOES_OFICIAIS.items():
        for n in nomes:
            nome_para_pct[n] = pct

    for nome, dados_atv in atividades.items():
        p_irpj = dados_atv.get("presuncao_irpj")
        if p_irpj is None:
            continue
        # Validações de sanidade
        if not (0 <= p_irpj <= 1):
            achados.append(Achado(
                severidade="CRITICA",
                regra="PRESUNCAO_FORA_RANGE",
                descricao=f"Presunção '{nome}' = {p_irpj} fora do range [0,1]",
                arquivo=caminho,
            ))
            continue

        # Match EXATO (case-insensitive, normalizando espaços/hifens)
        nome_norm = nome.lower().replace(" ", "_").replace("-", "_")
        pct_esperado = nome_para_pct.get(nome_norm)
        if pct_esperado is None:
            # Atividade não mapeada — não geramos alerta (pode ser custom)
            continue

        if abs(p_irpj - pct_esperado) > 0.001:
            achados.append(Achado(
                severidade="ALTA",
                regra="PRESUNCAO_DIVERGENTE_DA_LEI",
                descricao=(
                    f"Atividade '{nome}' tem presunção {p_irpj} esperada "
                    f"{pct_esperado} conforme Art. 15 Lei 9.249/95."
                ),
                arquivo=caminho,
                sugestao=f"Ajustar presuncao_irpj de '{nome}' para {pct_esperado}",
                base_legal="Lei 9.249/1995, Art. 15",
            ))
    return achados


# ─── REGRA 5: Cálculos de IRPF sem referência ao Art. 145 ───
RX_RENDIMENTOS_ISENTOS_SIMPLES = re.compile(
    r"rendimentos?\s+isent[ao]s?[\s\S]{0,200}(?:simples|sócio|PJ|distribu)",
    re.IGNORECASE,
)
RX_REFERENCIA_ART145 = re.compile(r"art\.?\s*145|145\s*(?:CGSN|/2018)", re.IGNORECASE)

def regra_doc_isentos_cita_art145(caminho: str, conteudo: str) -> List[Achado]:
    """Documentação/scripts que tratam de isentos do Simples DEVEM citar Art. 145."""
    achados = []
    base = os.path.basename(caminho)
    if base in ("validador_base_legal.py",):
        return achados
    # Só roda em documentação e scripts relevantes
    if not caminho.endswith((".md", ".py", ".json")):
        return achados

    if RX_RENDIMENTOS_ISENTOS_SIMPLES.search(conteudo):
        if not RX_REFERENCIA_ART145.search(conteudo):
            achados.append(Achado(
                severidade="MEDIA",
                regra="ISENTOS_SIMPLES_SEM_ART145",
                descricao=(
                    "Arquivo trata de rendimentos isentos de sócio/Simples "
                    "mas NÃO cita o Art. 145 da Res. CGSN 140/2018 — base "
                    "legal direta da regra."
                ),
                arquivo=caminho,
                sugestao=(
                    "Adicionar referência: 'Resolução CGSN 140/2018, Art. 145' "
                    "no docstring ou na seção de base legal."
                ),
                base_legal="Res. CGSN 140/2018, Art. 145",
            ))
    return achados


# ─── REGRA 6: Citação de IRRF 10% sem distinguir Art. 145 ───
def regra_irrf10_x_art145(caminho: str, conteudo: str) -> List[Achado]:
    """Avisa quando IRRF 10% (Lei 15.270/2025) aparece junto a Simples sem distinção."""
    achados = []
    base = os.path.basename(caminho)
    if base in ("validador_base_legal.py", "calc_distribuicao_lucros.py",
                "calc_rendimentos_isentos_simples.py"):
        return achados
    if not caminho.endswith((".md", ".py")):
        return achados

    if re.search(r"IRRF\s+10\s*%|15\.?270", conteudo, re.IGNORECASE):
        if re.search(r"Simples", conteudo, re.IGNORECASE) and not re.search(
            r"controvers|art\.?\s*14|art\.?\s*145|LC\s*123", conteudo, re.IGNORECASE
        ):
            achados.append(Achado(
                severidade="MEDIA",
                regra="IRRF10_SIMPLES_SEM_DISTINCAO",
                descricao=(
                    "Cita IRRF 10% (Lei 15.270/2025) e Simples sem distinguir "
                    "do Art. 145 (isenção presumida) ou da controvérsia LC 123."
                ),
                arquivo=caminho,
                sugestao=(
                    "Explicar que a Lei 15.270/2025 (IRRF 10%) é regra de "
                    "RETENÇÃO na fonte, distinta do limite de isenção do "
                    "Art. 145 §1° (que vai na declaração de ajuste)."
                ),
            ))
    return achados


# ─── REGRA 7: Funções de cálculo sem teste interno ───
RX_FUNCAO_CALC = re.compile(r"^def\s+(calc\w+)\s*\(", re.MULTILINE)

def regra_funcao_calc_sem_teste(caminho: str, conteudo: str) -> List[Achado]:
    """Verifica se funções de cálculo têm rotina de testes no mesmo arquivo."""
    achados = []
    if not caminho.endswith(".py"):
        return achados
    if "calc_" not in os.path.basename(caminho):
        return achados
    base = os.path.basename(caminho)
    if base == "validador_base_legal.py":
        return achados

    funcoes = RX_FUNCAO_CALC.findall(conteudo)
    if not funcoes:
        return achados

    tem_testes = bool(re.search(
        r"def\s+(rodar_testes|_rodar_testes|teste|test_)|--teste",
        conteudo,
    ))
    if not tem_testes:
        achados.append(Achado(
            severidade="MEDIA",
            regra="CALC_SEM_TESTE",
            descricao=(
                f"Arquivo possui {len(funcoes)} função(ões) de cálculo "
                f"({', '.join(funcoes[:3])}{'...' if len(funcoes) > 3 else ''}) "
                f"sem rotina de testes detectável."
            ),
            arquivo=caminho,
            sugestao="Adicione `def rodar_testes()` e flag `--teste` na CLI.",
        ))
    return achados


REGRAS = [
    regra_art145_irpj_vs_irpf,
    regra_presuncao_hardcoded,
    regra_lei_sem_versao,
    regra_tabela_presuncao_oficial,
    regra_doc_isentos_cita_art145,
    regra_irrf10_x_art145,
    regra_funcao_calc_sem_teste,
]


# ═══════════════════════════════════════════════════════════════════
#  EXECUTOR
# ═══════════════════════════════════════════════════════════════════

EXTENSOES_AUDITADAS = (".py", ".md", ".json", ".yaml", ".yml", ".txt")

def percorrer_skill(skill_dir: str) -> List[Achado]:
    """Percorre o diretório do skill aplicando todas as regras."""
    achados = []
    for raiz, _, arquivos in os.walk(skill_dir):
        # Pula caches e diretórios internos
        if any(p in raiz for p in ("__pycache__", ".git", "node_modules")):
            continue
        for nome in arquivos:
            if not nome.endswith(EXTENSOES_AUDITADAS):
                continue
            caminho = os.path.join(raiz, nome)
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    conteudo = f.read()
            except (UnicodeDecodeError, OSError):
                continue
            for regra in REGRAS:
                try:
                    achados.extend(regra(caminho, conteudo))
                except Exception as e:
                    achados.append(Achado(
                        severidade="INFO",
                        regra="REGRA_FALHOU",
                        descricao=f"Regra {regra.__name__} falhou: {e}",
                        arquivo=caminho,
                    ))
    return achados


def imprimir_relatorio(achados: List[Achado], skill_dir: str) -> int:
    """Imprime relatório legível. Retorna exit code."""
    by_sev = {s: [] for s in SEVERIDADES}
    for a in achados:
        by_sev.setdefault(a.severidade, []).append(a)

    print("\n" + "═" * 75)
    print(f"  VALIDADOR DE BASE LEGAL — Skill: {skill_dir}")
    print(f"  Versão {VERSAO_VALIDADOR}")
    print("═" * 75)
    total = sum(len(v) for v in by_sev.values())
    print(f"\n  Total de achados: {total}")
    for s in SEVERIDADES:
        if by_sev[s]:
            icone = {"CRITICA": "🚨", "ALTA": "❌", "MEDIA": "⚠️",
                     "BAIXA": "ℹ️", "INFO": "💬"}.get(s, "")
            print(f"    {icone} {s}: {len(by_sev[s])}")

    for s in SEVERIDADES:
        if not by_sev[s]:
            continue
        print(f"\n{'─' * 75}")
        print(f"  {s} ({len(by_sev[s])})")
        print("─" * 75)
        for a in by_sev[s]:
            print()
            print(str(a))

    print("\n" + "═" * 75)
    if by_sev["CRITICA"]:
        print("  ❌ HÁ ACHADOS CRÍTICOS — bloqueia produção até resolução.")
        return 1
    if by_sev["ALTA"]:
        print("  ⚠️ HÁ ACHADOS ALTOS — requer revisão antes de release.")
        return 2
    if total == 0:
        print("  ✅ NENHUM ACHADO — skill consistente com a base legal!")
    else:
        print("  ℹ️ Apenas achados informativos — skill aprovado para uso.")
    print("═" * 75 + "\n")
    return 0


def saida_json(achados: List[Achado]) -> str:
    return json.dumps(
        {
            "versao": VERSAO_VALIDADOR,
            "total": len(achados),
            "achados": [asdict(a) for a in achados],
        },
        ensure_ascii=False,
        indent=2,
    )


# ═══════════════════════════════════════════════════════════════════
#  AUTOTESTES
# ═══════════════════════════════════════════════════════════════════

def rodar_testes():
    """Auto-testes do validador."""
    ok = 0
    total = 0

    def t(desc, cond):
        nonlocal ok, total
        total += 1
        status = "PASSOU" if cond else "FALHOU"
        if cond:
            ok += 1
        print(f"  [{status}] {desc}")

    print("=" * 70)
    print("  TESTES — validador_base_legal.py")
    print("=" * 70)

    # ── Regra 1: detecta o erro clássico ──
    print("\n🚨 Regra ART145_IRPF_VS_IRPF")
    codigo_erro = "isento = receita_bruta * 0.32 - irpf"
    a1 = regra_art145_irpj_vs_irpf("teste.py", codigo_erro)
    t("Detecta 'receita_bruta * 0.32 - irpf'", len(a1) == 1)
    t("Severidade CRITICA", a1 and a1[0].severidade == "CRITICA")
    t("Cita Art. 145", a1 and "145" in (a1[0].base_legal or ""))

    codigo_erro2 = "# Forma 2: Faturamento Bruto x 32% - IRPF = Rendimentos Isentos."
    a1b = regra_art145_irpj_vs_irpf("teste.md", codigo_erro2)
    t("Detecta variante 'Faturamento Bruto x 32% - IRPF'", len(a1b) >= 1)

    codigo_ok = "isento = receita_bruta * pct_presuncao - irpj_devido_no_simples"
    a1c = regra_art145_irpj_vs_irpf("teste.py", codigo_ok)
    t("NÃO marca código correto (IRPJ)", len(a1c) == 0)

    # Linha que cita o erro em contexto pedagógico
    codigo_alerta = "# ERRADO: Faturamento * 32% - IRPF (não fazer isso)"
    a1d = regra_art145_irpj_vs_irpf("teste.py", codigo_alerta)
    t("Tolera contexto pedagógico (palavra 'ERRADO')", len(a1d) == 0)

    # ── Regra 2: presunção hard-coded ──
    print("\n⚠️ Regra PRESUNCAO_HARDCODED_32PCT")
    codigo_hardcoded = "result = receita * 0.32  # serviços"
    a2 = regra_presuncao_hardcoded("calc_random.py", codigo_hardcoded)
    t("Detecta 0.32 hard-coded", len(a2) == 1)

    # Whitelisted file
    a2b = regra_presuncao_hardcoded(
        "/path/calc_rendimentos_isentos_simples.py", codigo_hardcoded
    )
    t("Whitelist do módulo correto", len(a2b) == 0)

    # ── Regra 3: lei sem ano ──
    print("\nℹ️ Regra LEI_SEM_ANO")
    a3 = regra_lei_sem_versao("teste.md", "Conforme Lei 9.249, art. 15 ...")
    t("Detecta 'Lei 9.249' sem /YYYY", len(a3) >= 1)
    a3b = regra_lei_sem_versao("teste.md", "Conforme Lei 9.249/1995, art. 15 ...")
    t("NÃO marca 'Lei 9.249/1995'", len(a3b) == 0)

    # ── Regra 4: tabela oficial ──
    print("\n❌ Regra TABELA_DIVERGENTE_DA_LEI")
    tabela_errada = json.dumps({
        "atividades": {
            "comercio": {"presuncao_irpj": 0.32},   # ERRADO
            "servicos": {"presuncao_irpj": 0.32},   # OK
        }
    })
    a4 = regra_tabela_presuncao_oficial(
        "/path/lucro_presumido.json", tabela_errada
    )
    t("Detecta comércio com 32% (deveria ser 8%)", len(a4) == 1)
    t("Severidade ALTA", a4 and a4[0].severidade == "ALTA")

    # ── Regra 5: doc sem Art. 145 ──
    print("\n⚠️ Regra ISENTOS_SIMPLES_SEM_ART145")
    doc_sem = "Rendimentos isentos do sócio de PJ optante pelo Simples..."
    a5 = regra_doc_isentos_cita_art145("teste.md", doc_sem)
    t("Marca doc sem Art. 145", len(a5) == 1)
    doc_com = doc_sem + " Conforme Art. 145 CGSN 140/2018."
    a5b = regra_doc_isentos_cita_art145("teste.md", doc_com)
    t("NÃO marca doc com Art. 145", len(a5b) == 0)

    # ── Regra 6: IRRF 10% × Simples ──
    print("\n⚠️ Regra IRRF10_SIMPLES_SEM_DISTINCAO")
    doc_irrf = "IRRF 10% sobre lucros distribuídos por empresa do Simples..."
    a6 = regra_irrf10_x_art145("teste.md", doc_irrf)
    t("Marca IRRF 10% + Simples sem distinção", len(a6) == 1)
    doc_irrf2 = doc_irrf + " Há controvérsia com Art. 14 da LC 123/2006."
    a6b = regra_irrf10_x_art145("teste.md", doc_irrf2)
    t("NÃO marca quando explica controvérsia", len(a6b) == 0)

    # ── Regra 7: calc sem teste ──
    print("\n⚠️ Regra CALC_SEM_TESTE")
    py_sem = "def calcular_algo(x):\n    return x * 2\n"
    a7 = regra_funcao_calc_sem_teste("/p/calc_dummy.py", py_sem)
    t("Marca arquivo calc_*.py sem testes", len(a7) == 1)
    py_com = py_sem + "def rodar_testes():\n    pass\n"
    a7b = regra_funcao_calc_sem_teste("/p/calc_dummy.py", py_com)
    t("NÃO marca quando há rodar_testes", len(a7b) == 0)

    print(f"\n{'═' * 70}")
    print(f"  RESULTADO: {ok}/{total} testes passaram")
    if ok == total:
        print("  ✅ TODOS OS TESTES DO VALIDADOR PASSARAM!")
    else:
        print(f"  ❌ {total - ok} falha(s)")
    print(f"{'═' * 70}\n")
    return ok == total


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skill-dir", help="Diretório do skill a auditar.")
    ap.add_argument("--json", action="store_true", help="Saída JSON (machine-readable).")
    ap.add_argument("--teste", action="store_true", help="Roda autotestes do validador.")
    args = ap.parse_args()

    if args.teste:
        ok = rodar_testes()
        sys.exit(0 if ok else 1)

    if not args.skill_dir:
        ap.print_help()
        sys.exit(2)

    if not os.path.isdir(args.skill_dir):
        print(f"❌ Diretório não encontrado: {args.skill_dir}")
        sys.exit(2)

    achados = percorrer_skill(args.skill_dir)

    if args.json:
        print(saida_json(achados))
        sys.exit(0 if not any(a.severidade == "CRITICA" for a in achados) else 1)

    code = imprimir_relatorio(achados, args.skill_dir)
    sys.exit(code)


if __name__ == "__main__":
    main()
