#!/usr/bin/env python3
"""
Parser de Informes de Rendimentos (PDF → JSON estruturado)
RRT-Group-Contador v4.0 — Exercício 2026 (Ano-Calendário 2025)

Extrai dados de informes de rendimentos em PDF emitidos por bancos,
corretoras e empregadores, produzindo JSON padronizado para alimentar
o calc_irpf_integrado.py e o gerador de dossiê.

Templates suportados:
  - Genérico (fallback — regex em campos-chave)
  - Itaú Unibanco (CNPJ 60.701.190/0001-04)
  - Bradesco (CNPJ 60.746.948/0001-12)
  - Nubank (CNPJ 18.236.120/0001-58)
  - XP Investimentos (CNPJ 02.332.886/0001-04)
  - Empregador CLT (layout DIRF padrão)

Base legal: IN RFB 2.060/2021; IN RFB 2.312/2026; RIR/2018 Art. 86

Uso:
    python3 parse_informe_rendimentos.py --teste
    python3 parse_informe_rendimentos.py --arquivo informe.pdf
    python3 parse_informe_rendimentos.py --exemplo

Importação:
    from parse_informe_rendimentos import parsear_informe, identificar_fonte
"""

import json
import re
import sys
import os
from datetime import datetime, date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── CONSTANTES ──────────────────────────────────────────────────

VERSAO = "4.0"
EXERCICIO = 2026
ANO_CALENDARIO = 2025

# CNPJs conhecidos (raiz — 8 primeiros dígitos)
CNPJ_MAP = {
    "60701190": "itau",
    "60746948": "bradesco",
    "18236120": "nubank",
    "02332886": "xp",
    "33657248": "bb",
    "00360305": "caixa",
    "02819125": "btg",
    "13370835": "inter",
    "62232889": "c6",
}


# ─── UTILIDADES ──────────────────────────────────────────────────

def limpar_cnpj(cnpj_str):
    """Remove pontuação de CNPJ/CPF, retorna apenas dígitos."""
    if not cnpj_str:
        return ""
    return re.sub(r"[^\d]", "", str(cnpj_str))


def limpar_valor(valor_str):
    """
    Converte string BRL em float.
    '1.234,56' → 1234.56
    '1234.56' → 1234.56
    '-1.234,56' → -1234.56
    'R$ 1.234,56' → 1234.56
    '' ou None → 0.0
    """
    if not valor_str:
        return 0.0
    s = str(valor_str).strip()
    s = re.sub(r"R\$\s*", "", s).strip()
    if not s or s == "-":
        return 0.0

    negativo = s.startswith("-") or s.startswith("(")
    if negativo:
        s = s.replace("(", "").replace(")", "")
        if s.startswith("-"):
            s = s[1:]

    # Detecta formato brasileiro vs americano
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        partes = s.split(",")
        if len(partes) == 2 and len(partes[1]) <= 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "." in s:
        # Só ponto — detecta se é milhar BR (1.000) vs decimal (1.5)
        partes = s.split(".")
        if len(partes) == 2 and len(partes[1]) == 3:
            # Padrão brasileiro: "1.000" = mil, "10.500" = dez mil e quinhentos
            s = s.replace(".", "")
        # senão mantém como decimal

    try:
        val = float(s)
        return -val if negativo else val
    except ValueError:
        return 0.0


def extrair_cnpj_do_texto(texto):
    """Extrai primeiro CNPJ encontrado no texto."""
    match = re.search(r"\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2}", texto)
    if match:
        return limpar_cnpj(match.group())
    return ""


def extrair_cpf_do_texto(texto):
    """Extrai primeiro CPF encontrado no texto."""
    match = re.search(r"\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}", texto)
    if match:
        return limpar_cnpj(match.group())
    return ""


# ─── IDENTIFICAÇÃO DE FONTE ─────────────────────────────────────

def identificar_fonte(texto_ou_cnpj):
    """
    Identifica a fonte pagadora pelo CNPJ ou texto do informe.

    Returns:
        dict com {fonte, cnpj, tipo, template}
    """
    cnpj = limpar_cnpj(texto_ou_cnpj)
    if len(cnpj) < 14:
        cnpj = extrair_cnpj_do_texto(texto_ou_cnpj)

    raiz = cnpj[:8] if len(cnpj) >= 8 else ""
    template = CNPJ_MAP.get(raiz, "generico")

    texto_lower = texto_ou_cnpj.lower() if len(texto_ou_cnpj) > 20 else ""
    tipo = "banco"

    if any(k in texto_lower for k in ["corretora", "investiment", "xp ", "btg", "rico", "clear"]):
        tipo = "corretora"
    elif any(k in texto_lower for k in ["empregador", "fonte pagadora pessoa jurídica", "dirf", "salário", "salario"]):
        tipo = "empregador"
    elif any(k in texto_lower for k in ["banco", "poupança", "poupanca", "cdb", "lci", "lca"]):
        tipo = "banco"

    nomes = {
        "itau": "Itaú Unibanco", "bradesco": "Bradesco", "nubank": "Nubank",
        "xp": "XP Investimentos", "bb": "Banco do Brasil", "caixa": "Caixa Econômica Federal",
        "btg": "BTG Pactual", "inter": "Banco Inter", "c6": "C6 Bank",
        "generico": "Fonte não identificada",
    }

    return {
        "fonte": nomes.get(template, template),
        "cnpj": cnpj,
        "tipo": tipo,
        "template": template,
    }


# ─── REGEX PATTERNS ─────────────────────────────────────────────

PATTERNS = {
    "rendimentos_tributaveis_total": [
        r"(?:total\s+de\s+)?rendimentos?\s+tribut[aá]v\w+\s*[:\-]?\s*([\d.,]+)",
        r"1[\s\-\.]+rendimentos?\s+tribut[aá]v\w+.*?([\d.,]+)",
    ],
    "irrf_retido": [
        r"(?:imposto\s+(?:de\s+)?renda\s+retido|irrf|ir\s+retido|imposto\s+retido)\s*(?:na?\s+fonte)?\s*[:\-]?\s*([\d.,]+)",
        r"3[\s\-\.]+imposto.*?retido.*?([\d.,]+)",
    ],
    "inss_retido": [
        r"(?:contribui[çc][aã]o\s+previdenci[aá]ria|inss)\s*(?:oficial|retid[oa])?\s*[:\-]?\s*([\d.,]+)",
        r"4[\s\-\.]+contribui.*?previdenci.*?([\d.,]+)",
    ],
    "decimo_terceiro": [
        r"(?:13[°º]?\s*sal[aá]rio|d[eé]cimo\s+terceiro)\s*[:\-]?\s*([\d.,]+)",
    ],
    "irrf_13o": [
        r"(?:irrf?\s+(?:s[/]?\s*)?13|imposto.*?retido.*?13)\s*[°º]?\s*[:\-]?\s*([\d.,]+)",
    ],
    "rendimentos_isentos_total": [
        r"(?:total\s+de\s+)?rendimentos?\s+isento[s]?\s*(?:e\s+n[aã]o\s+tribut[aá]v\w+)?\s*[:\-]?\s*([\d.,]+)",
        r"5[\s\-\.]+rendimentos?\s+isento.*?([\d.,]+)",
    ],
    "rendimentos_exclusivos_total": [
        r"(?:rendimentos?\s+sujeitos?\s+[aà]\s+tributa[çc][aã]o\s+exclusiva|tributa[çc][aã]o\s+exclusiva)\s*[:\-]?\s*([\d.,]+)",
        r"6[\s\-\.]+rendimentos?\s+sujeit.*?exclusiv.*?([\d.,]+)",
    ],
    "pensao_alimenticia": [
        r"pens[aã]o\s+aliment[ií]cia\s*[:\-]?\s*([\d.,]+)",
    ],
    "poupanca": [
        r"(?:caderneta\s+de\s+)?poupan[çc]a\s*[:\-]?\s*([\d.,]+)",
    ],
    "lci_lca": [
        r"(?:lci|lca|letra\s+de\s+cr[eé]dito)\s*[:\-]?\s*([\d.,]+)",
    ],
    "cri_cra": [
        r"(?:cri|cra|certificado\s+de\s+receb[ií]v[ei]s)\s*[:\-]?\s*([\d.,]+)",
    ],
    "cdb_rdb": [
        r"(?:cdb|rdb|certificado\s+de\s+dep[oó]sito)\s*[:\-]?\s*([\d.,]+)",
    ],
    "nome_beneficiario": [
        r"(?:nome|benefici[aá]rio|titular)\s*[:\-]?\s*([A-ZÀ-Ü][A-ZÀ-Ü\s]{3,50})",
    ],
    "cpf_beneficiario": [
        r"(?:cpf)\s*[:\-]?\s*(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2})",
    ],
}


def aplicar_patterns(texto, campo):
    """Aplica regex patterns para um campo e retorna o primeiro match."""
    patterns = PATTERNS.get(campo, [])
    for pattern in patterns:
        match = re.search(pattern, texto, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


# ─── PARSERS POR TIPO ────────────────────────────────────────────

def parsear_generico(texto):
    """Parser genérico (fallback) — extrai dados por regex de campos conhecidos."""
    dados = {
        "rendimentos_tributaveis": {
            "total": limpar_valor(aplicar_patterns(texto, "rendimentos_tributaveis_total")),
            "decimo_terceiro": limpar_valor(aplicar_patterns(texto, "decimo_terceiro")),
        },
        "irrf_retido": {
            "sobre_rendimentos": limpar_valor(aplicar_patterns(texto, "irrf_retido")),
            "sobre_13o": limpar_valor(aplicar_patterns(texto, "irrf_13o")),
        },
        "inss_retido": {
            "contribuicao_previdenciaria": limpar_valor(aplicar_patterns(texto, "inss_retido")),
        },
        "rendimentos_isentos": {
            "total": limpar_valor(aplicar_patterns(texto, "rendimentos_isentos_total")),
            "poupanca": limpar_valor(aplicar_patterns(texto, "poupanca")),
            "lci_lca": limpar_valor(aplicar_patterns(texto, "lci_lca")),
            "cri_cra": limpar_valor(aplicar_patterns(texto, "cri_cra")),
        },
        "rendimentos_exclusivos": {
            "total": limpar_valor(aplicar_patterns(texto, "rendimentos_exclusivos_total")),
            "cdb_rdb": limpar_valor(aplicar_patterns(texto, "cdb_rdb")),
        },
        "pensao_alimenticia": limpar_valor(aplicar_patterns(texto, "pensao_alimenticia")),
    }
    irrf_total = dados["irrf_retido"]["sobre_rendimentos"] + dados["irrf_retido"]["sobre_13o"]
    dados["irrf_retido"]["total"] = round(irrf_total, 2)
    return dados


def parsear_empregador(texto):
    """Parser para informe de rendimentos de empregador (layout DIRF)."""
    dados = parsear_generico(texto)
    match_previd = re.search(r"previd[eê]ncia\s+complementar\s*[:\-]?\s*([\d.,]+)", texto, re.IGNORECASE)
    if match_previd:
        dados["previdencia_complementar"] = limpar_valor(match_previd.group(1))
    dados["tipo_informe"] = "empregador"
    return dados


def parsear_banco(texto, template="generico"):
    """Parser para informe de banco (rendimentos de aplicações financeiras)."""
    dados = parsear_generico(texto)
    dados["tipo_informe"] = "banco"
    dados["template"] = template
    return dados


def parsear_corretora(texto, template="generico"):
    """Parser para informe de corretora (ações, FIIs, renda fixa, ETFs)."""
    dados = parsear_generico(texto)

    match_div = re.search(r"dividendos?\s*[:\-]?\s*([\d.,]+)", texto, re.IGNORECASE)
    if match_div:
        dados.setdefault("rendimentos_isentos", {})["dividendos"] = limpar_valor(match_div.group(1))

    match_jcp = re.search(r"(?:jcp|juros\s+sobre\s+capital\s+pr[oó]prio)\s*[:\-]?\s*([\d.,]+)", texto, re.IGNORECASE)
    if match_jcp:
        dados.setdefault("rendimentos_exclusivos", {})["jcp"] = limpar_valor(match_jcp.group(1))

    match_fii = re.search(r"(?:fii|fundo[s]?\s+imobili[aá]rio|rendimento[s]?\s+de\s+fii)\s*[:\-]?\s*([\d.,]+)", texto, re.IGNORECASE)
    if match_fii:
        dados.setdefault("rendimentos_isentos", {})["fii"] = limpar_valor(match_fii.group(1))

    match_daytrade = re.search(r"(?:day[\s-]?trade|opera[çc][oõ]es?\s+day[\s-]?trade)\s*[:\-]?\s*([\d.,]+)", texto, re.IGNORECASE)
    if match_daytrade:
        dados["day_trade"] = {"resultado": limpar_valor(match_daytrade.group(1))}

    match_swing = re.search(r"(?:opera[çc][oõ]es?\s+(?:comuns?|normais?)|swing[\s-]?trade)\s*[:\-]?\s*([\d.,]+)", texto, re.IGNORECASE)
    if match_swing:
        dados["operacoes_comuns"] = {"resultado": limpar_valor(match_swing.group(1))}

    dados["tipo_informe"] = "corretora"
    dados["template"] = template
    return dados


# ─── CLASSIFICADOR DE RENDIMENTOS ISENTOS ────────────────────────

def classificar_rendimentos_isentos(dados):
    """
    Classifica rendimentos isentos usando codigos_rendimentos_isentos.json.
    Aplica regras v3.1: CRI→06, LCA→08, Poupança→12.
    """
    tabela_path = os.path.join(SCRIPT_DIR, "tabelas", "codigos_rendimentos_isentos.json")
    codigos = {}
    try:
        with open(tabela_path, "r", encoding="utf-8") as f:
            tabela = json.load(f)
            for item in tabela.get("codigos", []):
                codigos[item["codigo"]] = item["descricao"]
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    isentos = dados.get("rendimentos_isentos", {})
    classificados = []

    mapping = [
        ("poupanca", "12", "Caderneta de poupança"),
        ("lci_lca", "08", "LCI e LCA"),
        ("cri_cra", "06", "CRI/CRA/Debêntures incentivadas"),
        ("dividendos", "05", "Lucros e dividendos"),
        ("fii", "26", "Rendimentos de FII (isentos PF)"),
        ("fgts", "04", "FGTS e indenizações"),
    ]

    for campo, codigo, desc_fallback in mapping:
        val = isentos.get(campo, 0.0)
        if val > 0:
            classificados.append({
                "codigo": codigo,
                "descricao": codigos.get(codigo, desc_fallback),
                "valor": round(val, 2),
            })

    return classificados


# ─── FUNÇÃO PRINCIPAL ────────────────────────────────────────────

def parsear_informe(fonte, texto=None, arquivo_pdf=None):
    """
    Parsea um informe de rendimentos (texto ou PDF).

    Returns:
        dict com fonte_pagadora, beneficiario, dados, isentos classificados,
        metadados, alertas, status
    """
    if texto is None and arquivo_pdf:
        try:
            import pdfplumber
            with pdfplumber.open(arquivo_pdf) as pdf:
                paginas = []
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        paginas.append(t)
                texto = "\n".join(paginas)
        except ImportError:
            return {"erro": "pdfplumber não instalado", "status": "ERRO"}
        except Exception as e:
            return {"erro": f"Falha ao ler PDF: {str(e)}", "status": "ERRO"}

    if not texto:
        return {"erro": "Nenhum texto fornecido para parsing", "status": "ERRO"}

    info_fonte = identificar_fonte(texto if len(texto) > 20 else fonte)
    tipo = info_fonte["tipo"]
    template = info_fonte["template"]

    if tipo == "empregador":
        dados = parsear_empregador(texto)
    elif tipo == "corretora":
        dados = parsear_corretora(texto, template)
    else:
        dados = parsear_banco(texto, template)

    isentos_classificados = classificar_rendimentos_isentos(dados)

    nome_benef = aplicar_patterns(texto, "nome_beneficiario") or ""
    cpf_benef = aplicar_patterns(texto, "cpf_beneficiario") or ""
    if cpf_benef:
        cpf_benef = limpar_cnpj(cpf_benef)

    alertas = []
    rt = dados.get("rendimentos_tributaveis", {})
    if isinstance(rt, dict) and rt.get("total", 0) == 0:
        alertas.append({"severidade": "info", "campo": "rendimentos_tributaveis",
                        "mensagem": "Nenhum rendimento tributável encontrado"})

    irrf_total = dados.get("irrf_retido", {}).get("total", 0)
    rt_total = dados.get("rendimentos_tributaveis", {}).get("total", 0)
    if irrf_total > 0 and rt_total == 0:
        alertas.append({"severidade": "atencao", "campo": "irrf_retido",
                        "mensagem": "IRRF encontrado sem rendimento tributável correspondente"})

    confianca = "alta" if template != "generico" else "media"
    if template == "generico":
        alertas.append({"severidade": "info", "campo": "template",
                        "mensagem": f"Parser genérico — conferir valores manualmente"})

    if dados.get("rendimentos_isentos", {}).get("cri_cra", 0) > 0:
        alertas.append({"severidade": "info", "campo": "rendimentos_isentos.cri_cra",
                        "mensagem": "CRI/CRA classificado como código 06 (Lei 12.431/2011)"})

    return {
        "fonte_pagadora": {"cnpj": info_fonte["cnpj"], "nome": info_fonte["fonte"], "tipo": info_fonte["tipo"]},
        "beneficiario": {"cpf": cpf_benef, "nome": nome_benef},
        "dados": dados,
        "rendimentos_isentos_classificados": isentos_classificados,
        "metadados": {"exercicio": EXERCICIO, "ano_calendario": ANO_CALENDARIO,
                      "parser_versao": VERSAO, "template": template,
                      "confianca": confianca, "data_parsing": date.today().isoformat()},
        "alertas": alertas,
        "status": "OK",
    }


# ─── CONSOLIDADOR ────────────────────────────────────────────────

def consolidar_informes(lista_informes):
    """Consolida dados de múltiplos informes em um único resumo."""
    consolidado = {
        "fontes": [],
        "totais": {
            "rendimentos_tributaveis": 0.0, "irrf_retido": 0.0,
            "inss_retido": 0.0, "rendimentos_isentos": 0.0,
            "rendimentos_exclusivos": 0.0, "pensao_alimenticia": 0.0,
        },
        "rendimentos_isentos_classificados": [],
        "alertas": [],
        "num_informes": 0,
    }

    for informe in lista_informes:
        if informe.get("status") != "OK":
            consolidado["alertas"].append({"severidade": "erro",
                                           "mensagem": f"Informe ignorado: {informe.get('erro', 'status não OK')}"})
            continue

        consolidado["num_informes"] += 1
        consolidado["fontes"].append(informe["fonte_pagadora"])
        dados = informe.get("dados", {})

        rt = dados.get("rendimentos_tributaveis", {})
        if isinstance(rt, dict):
            consolidado["totais"]["rendimentos_tributaveis"] += rt.get("total", 0.0)

        irrf = dados.get("irrf_retido", {})
        if isinstance(irrf, dict):
            consolidado["totais"]["irrf_retido"] += irrf.get("total", 0.0)

        inss = dados.get("inss_retido", {})
        if isinstance(inss, dict):
            consolidado["totais"]["inss_retido"] += inss.get("contribuicao_previdenciaria", 0.0)

        ri = dados.get("rendimentos_isentos", {})
        if isinstance(ri, dict):
            consolidado["totais"]["rendimentos_isentos"] += ri.get("total", 0.0)

        re_val = dados.get("rendimentos_exclusivos", {})
        if isinstance(re_val, dict):
            consolidado["totais"]["rendimentos_exclusivos"] += re_val.get("total", 0.0)

        pa = dados.get("pensao_alimenticia", 0.0)
        if isinstance(pa, (int, float)):
            consolidado["totais"]["pensao_alimenticia"] += pa

        for item in informe.get("rendimentos_isentos_classificados", []):
            encontrado = False
            for existing in consolidado["rendimentos_isentos_classificados"]:
                if existing["codigo"] == item["codigo"]:
                    existing["valor"] = round(existing["valor"] + item["valor"], 2)
                    encontrado = True
                    break
            if not encontrado:
                consolidado["rendimentos_isentos_classificados"].append(dict(item))

        consolidado["alertas"].extend(informe.get("alertas", []))

    for k in consolidado["totais"]:
        consolidado["totais"][k] = round(consolidado["totais"][k], 2)

    return consolidado


# ─── ADAPTER PARA calc_irpf_integrado ────────────────────────────

def converter_para_irpf_integrado(consolidado, dados_extras=None):
    """Converte dados consolidados para parâmetros de calcular_irpf_integrado()."""
    if dados_extras is None:
        dados_extras = {}

    totais = consolidado.get("totais", {})
    salarios = dados_extras.get("salarios_mensais")
    if not salarios and totais.get("rendimentos_tributaveis", 0) > 0:
        mensal = totais["rendimentos_tributaveis"] / 12
        salarios = [round(mensal, 2)] * 12

    return {
        "salarios_mensais": salarios or [],
        "num_dependentes": dados_extras.get("num_dependentes", 0),
        "pensao_alimenticia_mensal": dados_extras.get("pensao_alimenticia_mensal", 0.0),
        "deducoes_anuais": dados_extras.get("deducoes_anuais", []),
        "rendimentos_exterior": dados_extras.get("rendimentos_exterior", []),
        "ganhos_capital": dados_extras.get("ganhos_capital", []),
        "irrf_ja_retido_anual": totais.get("irrf_retido", 0.0),
    }


# ─── TESTES ──────────────────────────────────────────────────────

def rodar_testes():
    """Executa testes do parser de informes."""
    print("\n" + "=" * 70)
    print("  TESTES: PARSE_INFORME_RENDIMENTOS v" + VERSAO)
    print("=" * 70)

    testes_ok = 0
    testes_total = 0

    def teste(descricao, obtido, condicao):
        nonlocal testes_ok, testes_total
        testes_total += 1
        passou = condicao(obtido) if callable(condicao) else (obtido == condicao)
        status = "PASSOU" if passou else "FALHOU"
        if passou:
            testes_ok += 1
        print(f"  [{status}] {descricao}")
        if not passou and not callable(condicao):
            print(f"         Obtido:   {obtido!r}")
            print(f"         Esperado: {condicao!r}")

    # ─── limpar_valor ─────────────────────────────────────────
    print("\n  --- limpar_valor ---")
    teste("T01: BRL '1.234,56'", limpar_valor("1.234,56"), 1234.56)
    teste("T02: BRL 'R$ 1.234,56'", limpar_valor("R$ 1.234,56"), 1234.56)
    teste("T03: BRL '-1.234,56'", limpar_valor("-1.234,56"), -1234.56)
    teste("T04: BRL '0,00'", limpar_valor("0,00"), 0.0)
    teste("T05: BRL ''", limpar_valor(""), 0.0)
    teste("T06: BRL None", limpar_valor(None), 0.0)
    teste("T07: BRL '1234.56'", limpar_valor("1234.56"), 1234.56)
    teste("T08: BRL '1,234.56'", limpar_valor("1,234.56"), 1234.56)
    teste("T09: BRL 'R$  10.500,00'", limpar_valor("R$  10.500,00"), 10500.0)
    teste("T10: BRL '(500,00)'", limpar_valor("(500,00)"), -500.0)
    teste("T11: BRL '99,9'", limpar_valor("99,9"), 99.9)
    teste("T12: BRL '1.000'", limpar_valor("1.000"), 1000.0)

    # ─── limpar_cnpj ─────────────────────────────────────────
    print("\n  --- limpar_cnpj ---")
    teste("T13: CNPJ", limpar_cnpj("60.701.190/0001-04"), "60701190000104")
    teste("T14: CNPJ limpo", limpar_cnpj("60701190000104"), "60701190000104")
    teste("T15: CPF", limpar_cnpj("123.456.789-00"), "12345678900")
    teste("T16: Vazio", limpar_cnpj(""), "")
    teste("T17: None", limpar_cnpj(None), "")

    # ─── identificar_fonte ───────────────────────────────────
    print("\n  --- identificar_fonte ---")
    teste("T18: Itaú", identificar_fonte("60.701.190/0001-04")["template"], "itau")
    teste("T19: Bradesco", identificar_fonte("60.746.948/0001-12")["template"], "bradesco")
    teste("T20: Nubank", identificar_fonte("18.236.120/0001-58")["template"], "nubank")
    teste("T21: XP", identificar_fonte("02.332.886/0001-04")["template"], "xp")
    teste("T22: BB", identificar_fonte("33.657.248/0001-79")["template"], "bb")
    teste("T23: Desconhecido", identificar_fonte("99.999.999/0001-99")["template"], "generico")
    teste("T24: Tipo banco", identificar_fonte("CNPJ: 60.701.190/0001-04 Banco Itaú poupança CDB")["tipo"], "banco")
    teste("T25: Tipo corretora", identificar_fonte("XP Investimentos Corretora CNPJ 02.332.886/0001-04")["tipo"], "corretora")
    teste("T26: Tipo empregador", identificar_fonte("Empregador: EMPRESA SA - Fonte Pagadora Pessoa Jurídica - DIRF salário")["tipo"], "empregador")

    # ─── aplicar_patterns ────────────────────────────────────
    print("\n  --- aplicar_patterns ---")
    texto_emp = """
    COMPROVANTE DE RENDIMENTOS PAGOS E DE IMPOSTO SOBRE A RENDA RETIDO NA FONTE
    Fonte Pagadora Pessoa Jurídica
    CNPJ: 12.345.678/0001-90
    CPF: 123.456.789-00
    Nome: JOAO SILVA SOUZA

    1. Total de Rendimentos Tributáveis: 96.000,00
    2. Contribuição Previdenciária Oficial: 8.157,60
    3. Imposto de Renda Retido na Fonte: 7.200,00
    4. 13° Salário: 8.000,00
    5. IRRF sobre 13°: 600,00
    """
    teste("T27: Rend tributáveis", aplicar_patterns(texto_emp, "rendimentos_tributaveis_total"), lambda x: x is not None and "96" in x)
    teste("T28: IRRF", aplicar_patterns(texto_emp, "irrf_retido"), lambda x: x is not None and "7.200" in x)
    teste("T29: INSS", aplicar_patterns(texto_emp, "inss_retido"), lambda x: x is not None and "8.157" in x)
    teste("T30: 13°", aplicar_patterns(texto_emp, "decimo_terceiro"), lambda x: x is not None and "8.000" in x)
    teste("T31: Nome", aplicar_patterns(texto_emp, "nome_beneficiario"), lambda x: x is not None and "JOAO" in x)
    teste("T32: CPF", aplicar_patterns(texto_emp, "cpf_beneficiario"), lambda x: x is not None and "123" in x)

    # ─── parsear_generico ────────────────────────────────────
    print("\n  --- parsear_generico ---")
    r_gen = parsear_generico(texto_emp)
    teste("T33: RT > 0", r_gen["rendimentos_tributaveis"]["total"], lambda x: x > 0)
    teste("T34: IRRF > 0", r_gen["irrf_retido"]["sobre_rendimentos"], lambda x: x > 0)
    teste("T35: INSS > 0", r_gen["inss_retido"]["contribuicao_previdenciaria"], lambda x: x > 0)
    teste("T36: IRRF total", r_gen["irrf_retido"]["total"], lambda x: x > 0)

    # ─── parsear_empregador ──────────────────────────────────
    print("\n  --- parsear_empregador ---")
    r_emp = parsear_empregador(texto_emp)
    teste("T37: tipo_informe", r_emp["tipo_informe"], "empregador")
    teste("T38: herda genérico", r_emp["rendimentos_tributaveis"]["total"], lambda x: x > 0)

    # ─── parsear_banco ───────────────────────────────────────
    print("\n  --- parsear_banco ---")
    texto_banco = """
    INFORME DE RENDIMENTOS FINANCEIROS
    CNPJ: 60.701.190/0001-04
    Banco Itaú Unibanco
    CPF: 987.654.321-00
    Nome: MARIA SANTOS OLIVEIRA

    Rendimentos sujeitos à tributação exclusiva: 2.500,00
    CDB: 1.800,00
    Caderneta de Poupança: 350,00
    LCI: 1.200,00
    CRI: 800,00
    Rendimentos isentos e não tributáveis: 2.350,00
    """
    r_banco = parsear_banco(texto_banco, "itau")
    teste("T39: tipo_informe", r_banco["tipo_informe"], "banco")
    teste("T40: template", r_banco["template"], "itau")
    teste("T41: poupança", r_banco["rendimentos_isentos"]["poupanca"], lambda x: x > 0)
    teste("T42: LCI/LCA", r_banco["rendimentos_isentos"]["lci_lca"], lambda x: x > 0)
    teste("T43: CRI/CRA", r_banco["rendimentos_isentos"]["cri_cra"], lambda x: x > 0)
    teste("T44: CDB", r_banco["rendimentos_exclusivos"]["cdb_rdb"], lambda x: x > 0)

    # ─── parsear_corretora ───────────────────────────────────
    print("\n  --- parsear_corretora ---")
    texto_corr = """
    XP Investimentos CCTVM S/A
    Corretora - CNPJ: 02.332.886/0001-04

    Dividendos: 5.600,00
    JCP - Juros sobre Capital Próprio: 1.200,00
    Rendimentos de FII: 3.800,00
    Operações comuns: 15.000,00
    Day-trade: 2.500,00
    """
    r_corr = parsear_corretora(texto_corr, "xp")
    teste("T45: tipo_informe", r_corr["tipo_informe"], "corretora")
    teste("T46: dividendos", r_corr["rendimentos_isentos"]["dividendos"], lambda x: x > 0)
    teste("T47: JCP", r_corr["rendimentos_exclusivos"]["jcp"], lambda x: x > 0)
    teste("T48: FII", r_corr["rendimentos_isentos"]["fii"], lambda x: x > 0)
    teste("T49: day-trade", r_corr["day_trade"]["resultado"], lambda x: x > 0)
    teste("T50: swing", r_corr["operacoes_comuns"]["resultado"], lambda x: x > 0)

    # ─── classificar_rendimentos_isentos ─────────────────────
    print("\n  --- classificar_rendimentos_isentos ---")
    dados_class = {"rendimentos_isentos": {"poupanca": 350.0, "lci_lca": 1200.0, "cri_cra": 800.0, "dividendos": 5600.0, "fii": 3800.0}}
    classificados = classificar_rendimentos_isentos(dados_class)
    teste("T51: 5 itens", len(classificados), 5)
    codigos_enc = {c["codigo"] for c in classificados}
    teste("T52: Poupança→12", "12" in codigos_enc, True)
    teste("T53: LCI→08", "08" in codigos_enc, True)
    teste("T54: CRI→06", "06" in codigos_enc, True)
    teste("T55: Dividendos→05", "05" in codigos_enc, True)
    teste("T56: FII→26", "26" in codigos_enc, True)
    for c in classificados:
        if c["codigo"] == "12":
            teste("T57: Cód 12 ≠ CRI", "CRI" not in c["descricao"].upper(), True)

    # ─── parsear_informe (integração) ────────────────────────
    print("\n  --- parsear_informe ---")
    r_full = parsear_informe("empregador", texto=texto_emp)
    teste("T58: Status OK", r_full["status"], "OK")
    teste("T59: fonte_pagadora", "fonte_pagadora" in r_full, True)
    teste("T60: beneficiario", "beneficiario" in r_full, True)
    teste("T61: dados", "dados" in r_full, True)
    teste("T62: metadados", "metadados" in r_full, True)
    teste("T63: Exercício", r_full["metadados"]["exercicio"], 2026)
    teste("T64: Versão", r_full["metadados"]["parser_versao"], VERSAO)

    r_banco_full = parsear_informe("banco", texto=texto_banco)
    teste("T65: Isentos classificados", len(r_banco_full["rendimentos_isentos_classificados"]), lambda x: x >= 2)

    r_err = parsear_informe("teste", texto=None, arquivo_pdf=None)
    teste("T66: Sem texto → ERRO", r_err["status"], "ERRO")

    # ─── consolidar_informes ─────────────────────────────────
    print("\n  --- consolidar_informes ---")
    inf1 = parsear_informe("empregador", texto=texto_emp)
    inf2 = parsear_informe("banco", texto=texto_banco)
    cons = consolidar_informes([inf1, inf2])
    teste("T67: 2 informes", cons["num_informes"], 2)
    teste("T68: 2 fontes", len(cons["fontes"]), 2)
    teste("T69: RT >= empregador", cons["totais"]["rendimentos_tributaveis"], lambda x: x >= 90000)
    teste("T70: IRRF acumulado", cons["totais"]["irrf_retido"], lambda x: x > 0)
    teste("T71: Isentos consolidados", len(cons["rendimentos_isentos_classificados"]), lambda x: x >= 2)

    cons2 = consolidar_informes([inf1, {"status": "ERRO", "erro": "teste"}])
    teste("T72: Ignora erro", cons2["num_informes"], 1)
    teste("T73: Alerta sobre erro", len(cons2["alertas"]), lambda x: x >= 1)

    # ─── converter_para_irpf_integrado ───────────────────────
    print("\n  --- converter_para_irpf_integrado ---")
    params = converter_para_irpf_integrado(cons)
    teste("T74: salarios_mensais", "salarios_mensais" in params, True)
    teste("T75: 12 meses", len(params["salarios_mensais"]), 12)
    teste("T76: IRRF", params["irrf_ja_retido_anual"], lambda x: x > 0)
    teste("T77: num_dependentes", "num_dependentes" in params, True)
    teste("T78: deducoes_anuais", "deducoes_anuais" in params, True)

    params2 = converter_para_irpf_integrado(cons, dados_extras={"salarios_mensais": [8000.0] * 12, "num_dependentes": 2})
    teste("T79: Salários sobrescritos", params2["salarios_mensais"][0], 8000.0)
    teste("T80: Dependentes", params2["num_dependentes"], 2)

    # ─── Edge cases ──────────────────────────────────────────
    print("\n  --- Edge cases ---")
    teste("T81: limpar_valor espaços", limpar_valor("  R$   1.500,00  "), 1500.0)
    teste("T82: limpar_valor '-'", limpar_valor("-"), 0.0)
    teste("T83: extrair_cnpj vazio", extrair_cnpj_do_texto(""), "")
    teste("T84: extrair_cpf vazio", extrair_cpf_do_texto(""), "")
    teste("T85: fonte texto curto", identificar_fonte("xx")["template"], "generico")
    cons_vazio = consolidar_informes([])
    teste("T86: Consolida vazio", cons_vazio["num_informes"], 0)
    teste("T87: Totais zero", cons_vazio["totais"]["rendimentos_tributaveis"], 0.0)
    params_vazio = converter_para_irpf_integrado(cons_vazio)
    teste("T88: Converter vazio", params_vazio["salarios_mensais"], [])
    teste("T89: Classificar vazio", classificar_rendimentos_isentos({}), [])
    teste("T90: Classificar sem sub", classificar_rendimentos_isentos({"rendimentos_isentos": {}}), [])

    print(f"\n{'='*70}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print(f"  ❌ {testes_total - testes_ok} falha(s)")
    print(f"{'='*70}\n")
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        ok = rodar_testes()
        sys.exit(0 if ok else 1)
    elif len(sys.argv) > 1 and sys.argv[1] == "--arquivo":
        if len(sys.argv) < 3:
            print("Uso: python3 parse_informe_rendimentos.py --arquivo <caminho.pdf>")
            sys.exit(1)
        resultado = parsear_informe("", arquivo_pdf=sys.argv[2])
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "--exemplo":
        texto_exemplo = """
        COMPROVANTE DE RENDIMENTOS PAGOS E DE IMPOSTO SOBRE A RENDA RETIDO NA FONTE
        Ano-calendário 2025 — Exercício 2026
        Fonte Pagadora: EMPRESA EXEMPLO LTDA
        CNPJ: 12.345.678/0001-90  CPF: 123.456.789-00
        Nome: CARLOS EDUARDO SILVA
        1. Total de Rendimentos Tributáveis: 120.000,00
        2. Contribuição Previdenciária Oficial: 10.166,64
        3. Imposto de Renda Retido na Fonte: 15.600,00
        4. 13° Salário: 10.000,00
        5. IRRF sobre 13°: 1.200,00
        """
        r = parsear_informe("empregador", texto=texto_exemplo)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        print(f"parse_informe_rendimentos.py v{VERSAO}")
        print("  --teste    Rodar testes")
        print("  --arquivo  Parsear PDF")
        print("  --exemplo  Exemplo com texto")
