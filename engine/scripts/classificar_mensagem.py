#!/usr/bin/env python3
"""
Classificador de Mensagens WhatsApp → Fluxos RRT-Group-Contador v4.2

Recebe uma mensagem de texto (tipicamente de um grupo WhatsApp) e:
  1. Classifica em um dos 28 fluxos do skill
  2. Extrai parâmetros numéricos (salário, receita, meses, etc.)
  3. Retorna nível de confiança (alta, media, baixa, nenhuma)

Uso:
    python3 classificar_mensagem.py --teste

Importação:
    from classificar_mensagem import classificar_mensagem
"""

import re
import sys
import json
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# MAPA DE FLUXOS — baseado na tabela de detecção do SKILL.md
# Cada fluxo tem: nome, palavras-chave (peso 1.0), e script associado
# ═══════════════════════════════════════════════════════════════

FLUXOS = {
    1: {
        "nome": "Tributário Estadual/Municipal",
        "script": ["calc_icms_st.py", "calc_difal.py", "calc_iss.py"],
        "keywords": [
            "icms", "ipi", "iss", "alíquota", "aliquota", "ncm", "cfop",
            "nota fiscal", "substituição tributária", "st ", "difal", "mva",
            "cest", "interestadual", "interstate",
        ],
        "keywords_forte": ["icms", "difal", "iss", "mva", "cest", "cfop"],
        "calculavel": True,
    },
    2: {
        "nome": "Tributário Federal / Simples Nacional",
        "script": ["calc_simples.py", "calc_presumido.py"],
        "keywords": [
            "irpj", "csll", "pis", "cofins", "simples", "das",
            "lucro presumido", "regime tributário", "enquadramento",
            "simples nacional", "anexo", "fator r",
        ],
        "keywords_forte": ["simples", "das", "lucro presumido", "irpj"],
        "calculavel": True,
    },
    3: {
        "nome": "Trabalhista/DP",
        "script": ["calc_rescisao.py", "calc_ferias.py", "calc_13o.py", "calc_hora_extra.py"],
        "keywords": [
            "rescisão", "rescisao", "férias", "ferias", "décimo terceiro",
            "13°", "13o", "hora extra", "adicional", "aviso prévio",
            "aviso previo", "fgts", "multa 40", "sindicato", "cct",
            "folha", "salário", "salario", "demissão", "demissao",
            "justa causa", "acordo mútuo", "acordo mutuo",
        ],
        "keywords_forte": [
            "rescisão", "rescisao", "férias", "ferias", "13°",
            "hora extra", "demissão", "demissao", "aviso prévio",
        ],
        "calculavel": True,
    },
    4: {
        "nome": "Obrigações Acessórias",
        "script": [],
        "keywords": [
            "sped", "esocial", "e-social", "dctf", "dctweb", "efd",
            "ecf", "dirf", "rais", "obrigação acessória", "prazo",
            "declaração", "declaracao", "entrega", "vencimento",
        ],
        "keywords_forte": ["sped", "esocial", "dctf", "efd", "ecf"],
        "calculavel": False,
    },
    5: {
        "nome": "Societário",
        "script": [],
        "keywords": [
            "abrir empresa", "encerrar", "alterar contrato", "cnpj",
            "cnae", "junta comercial", "mei", "porte", "contrato social",
            "abrir", "fechar empresa",
        ],
        "keywords_forte": ["abrir empresa", "encerrar empresa", "contrato social", "cnae"],
        "calculavel": False,
    },
    6: {
        "nome": "Situação Fiscal",
        "script": [],
        "keywords": [
            "e-cac", "ecac", "situação fiscal", "débito", "debito",
            "parcelamento", "darf", "regularizar", "certidão negativa",
            "certidao negativa", "cnd", "pendência", "pendencia",
        ],
        "keywords_forte": ["e-cac", "situação fiscal", "certidão negativa", "cnd"],
        "calculavel": False,
    },
    7: {
        "nome": "Reforma Tributária (IBS/CBS)",
        "script": ["calc_cbs_ibs.py"],
        "keywords": [
            "ibs", "cbs", "reforma tributária", "reforma tributaria",
            "split payment", "transição", "transicao", "comitê gestor",
        ],
        "keywords_forte": ["ibs", "cbs", "reforma tributária", "split payment"],
        "calculavel": True,
    },
    8: {
        "nome": "Custo de Contratação CLT",
        "script": ["calc_custo_empregado.py"],
        "keywords": [
            "custo empregado", "custo funcionário", "custo funcionario",
            "custo contratação", "custo contratacao", "encargos patronais",
            "inss patronal", "rat", "fap", "terceiros", "custo clt",
            "quanto custa contratar", "custo total empregado",
        ],
        "keywords_forte": ["custo empregado", "custo clt", "quanto custa contratar", "custo contratação"],
        "calculavel": True,
    },
    9: {
        "nome": "Retenções PJ",
        "script": ["calc_retencoes_pj.py"],
        "keywords": [
            "retenção", "retencao", "retenções", "retencoes", "csrf",
            "4,65", "4.65", "irrf sobre nota", "nota de serviço",
            "reter", "retido na fonte", "inss 11", "cessão de mão de obra",
        ],
        "keywords_forte": ["retenção", "csrf", "retido na fonte", "4,65"],
        "calculavel": True,
    },
    14: {
        "nome": "Folha de Pagamento",
        "script": ["calc_folha.py"],
        "keywords": [
            "folha", "holerite", "contracheque", "salário líquido",
            "salario liquido", "bruto ao líquido", "bruto ao liquido",
            "desconto do empregado", "proventos", "vt ", "vale transporte",
            "insalubridade", "periculosidade", "noturno", "folha completa",
        ],
        "keywords_forte": ["holerite", "contracheque", "salário líquido", "folha completa"],
        "calculavel": True,
    },
    15: {
        "nome": "CBS/IBS — Cálculo",
        "script": ["calc_cbs_ibs.py"],
        "keywords": [
            "cbs", "ibs", "reforma tributária cálculo", "quanto de cbs",
            "quanto de ibs", "projeção transição", "carga tributária nova",
            "comparativo reforma",
        ],
        "keywords_forte": ["quanto de cbs", "quanto de ibs"],
        "calculavel": True,
    },
    16: {
        "nome": "Lucro Real",
        "script": ["calc_lucro_real.py"],
        "keywords": [
            "lucro real", "lalur", "adições", "exclusões", "prejuízo fiscal",
            "base negativa", "pis não-cumulativo", "cofins não-cumulativo",
            "pis não cumulativo", "cofins não cumulativo", "créditos pis",
            "créditos cofins", "compensação 30",
        ],
        "keywords_forte": ["lucro real", "lalur", "prejuízo fiscal"],
        "calculavel": True,
    },
    17: {
        "nome": "Comparativo de Regimes",
        "script": ["calc_comparativo_regimes.py"],
        "keywords": [
            "qual regime", "compara regimes", "comparativo", "simples ou presumido",
            "simples ou real", "presumido ou real", "melhor regime",
            "trocar de regime", "planejamento tributário", "vale mais a pena",
            "vale a pena", "o que compensa", "compensa mais",
        ],
        "keywords_forte": [
            "qual regime", "compara regimes", "melhor regime",
            "simples ou presumido", "simples ou real", "presumido ou real",
            "vale mais a pena",
        ],
        "calculavel": True,
    },
    19: {
        "nome": "MEI",
        "script": ["calc_mei.py"],
        "keywords": [
            "mei", "microempreendedor", "das-mei", "das mei",
            "limite mei", "faturamento mei", "desenquadramento",
            "mei caminhoneiro", "dasn-simei", "dasn",
        ],
        "keywords_forte": ["mei", "microempreendedor", "das-mei", "desenquadramento"],
        "calculavel": True,
    },
    20: {
        "nome": "Pró-labore",
        "script": ["calc_prolabore.py"],
        "keywords": [
            "pró-labore", "pro-labore", "prolabore", "pró labore",
            "pro labore", "retirada sócio", "retirada socio",
            "inss sócio", "inss socio", "quanto sócio paga",
            "pró-labore mínimo", "cpp", "contribuinte individual",
        ],
        "keywords_forte": ["pró-labore", "pro-labore", "prolabore", "retirada sócio"],
        "calculavel": True,
    },
    21: {
        "nome": "Distribuição de Lucros",
        "script": ["calc_distribuicao_lucros.py"],
        "keywords": [
            "distribuição de lucros", "distribuicao de lucros", "dividendos",
            "lucros isentos", "50 mil", "otimizar retirada",
            "pró-labore ou lucro", "mix sócio",
        ],
        "keywords_forte": ["distribuição de lucros", "dividendos", "lucros isentos"],
        "calculavel": True,
    },
    22: {
        "nome": "Códigos DARF/GPS",
        "script": ["calc_darf_codes.py"],
        "keywords": [
            "código darf", "codigo darf", "qual darf", "gps",
            "guia inss", "código recolhimento", "darf irpj",
            "darf csll", "vencimento guia",
        ],
        "keywords_forte": ["código darf", "qual darf", "código recolhimento"],
        "calculavel": True,
    },
    23: {
        "nome": "Folha em Lote",
        "script": ["calc_folha_batch.py"],
        "keywords": [
            "folha em lote", "folha batch", "processar folha",
            "folha empresa", "resumo folha", "gps total",
            "fgts total", "guias empresa",
        ],
        "keywords_forte": ["folha em lote", "folha batch", "gps total"],
        "calculavel": True,
    },
    24: {
        "nome": "IRPF PF — Cálculo",
        "script": ["calc_irpf_integrado.py", "calc_irpf_vs_simplificada.py",
                    "calc_carne_leao.py", "calc_gcap_imovel.py", "calc_gcap_veiculo.py"],
        "keywords": [
            "irpf", "declaração pf", "declaracao pf", "dedução", "deducao",
            "educação", "educacao", "saúde", "saude", "dependente",
            "pgbl", "vgbl", "completa", "simplificada", "restituição",
            "restituicao", "malha fina", "imposto de renda pessoa física",
            "imposto de renda pessoa fisica", "carnê-leão", "carne-leao",
            "carne leão", "renda exterior", "ptax", "ganho de capital",
            "gcap", "imóvel venda", "imovel venda", "veículo venda",
            "crypto", "etf exterior", "fator redutor",
        ],
        "keywords_forte": [
            "irpf", "declaração pf", "malha fina", "restituição",
            "carnê-leão", "ganho de capital", "gcap",
        ],
        "calculavel": True,
    },
}

# Aliases comuns no WhatsApp (gírias, abreviações)
ALIASES = {
    "sn": "simples nacional",
    "lp": "lucro presumido",
    "lr": "lucro real",
    "das atrasado": "das mei simples",
    "holerite": "folha de pagamento",
    "gp": "guia da previdência",
    "inss": "inss contribuição",
    "ir": "imposto de renda",
    "pj": "pessoa jurídica",
    "pf": "pessoa física",
    "clt": "trabalhista",
}


# ═══════════════════════════════════════════════════════════════
# EXTRAÇÃO DE PARÂMETROS
# ═══════════════════════════════════════════════════════════════

def extrair_valores_monetarios(texto):
    """
    Extrai valores monetários do texto.
    Reconhece: R$ 3.000, R$ 3000, R$3.000,00, 3 mil, 45k, 3000 reais
    """
    valores = []

    # Padrão R$ com separadores brasileiros: R$ 3.000,00 ou R$ 3000
    for m in re.finditer(r'R\$\s*([\d]{1,3}(?:\.?\d{3})*(?:,\d{1,2})?)', texto):
        v = m.group(1).replace(".", "").replace(",", ".")
        valores.append(float(v))

    # Padrão "X mil" ou "X mil reais"
    for m in re.finditer(r'(\d+(?:[.,]\d+)?)\s*mil(?:\s*reais)?', texto, re.IGNORECASE):
        v = m.group(1).replace(",", ".")
        valores.append(float(v) * 1000)

    # Padrão "Xk" (45k = 45.000)
    for m in re.finditer(r'(\d+(?:[.,]\d+)?)\s*k\b', texto, re.IGNORECASE):
        v = m.group(1).replace(",", ".")
        valores.append(float(v) * 1000)

    # Número seguido de "reais" sem R$
    for m in re.finditer(r'(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s*reais', texto, re.IGNORECASE):
        v = m.group(1).replace(".", "").replace(",", ".")
        valores.append(float(v))

    # Números "soltos" que parecem salários/valores (1000+, sem unidade)
    # Só ativa se nenhum valor já foi encontrado
    if not valores:
        for m in re.finditer(r'(?<!\d)(\d{4,7})(?:\.\d{2})?(?!\d)', texto):
            v = float(m.group(1))
            if 1000 <= v <= 10000000:  # faixa plausível de salário/receita
                valores.append(v)

    return list(set(valores))  # deduplica


def extrair_meses(texto):
    """Extrai número de meses/avos mencionados no texto."""
    for m in re.finditer(r'(\d+)\s*(?:meses|avos|mês|mes)', texto, re.IGNORECASE):
        return int(m.group(1))
    return None


def extrair_anos(texto):
    """Extrai anos de serviço/casa mencionados."""
    for m in re.finditer(r'(\d+)\s*(?:anos?|ano)\s*(?:de casa|de serviço|de servico|trabalhando)?', texto, re.IGNORECASE):
        return int(m.group(1))
    return None


def extrair_percentual(texto):
    """Extrai percentuais mencionados."""
    pcts = []
    for m in re.finditer(r'(\d+(?:[.,]\d+)?)\s*%', texto):
        v = m.group(1).replace(",", ".")
        pcts.append(float(v))
    return pcts


def extrair_horas(texto):
    """Extrai número de horas (extras, trabalhadas)."""
    for m in re.finditer(r'(\d+)\s*(?:horas?|h)\s*(?:extras?)?', texto, re.IGNORECASE):
        return int(m.group(1))
    return None


def extrair_dependentes(texto):
    """Extrai número de dependentes."""
    for m in re.finditer(r'(\d+)\s*dependentes?', texto, re.IGNORECASE):
        return int(m.group(1))
    return None


def extrair_tipo_rescisao(texto):
    """Detecta tipo de rescisão mencionado."""
    t = texto.lower()
    if any(x in t for x in ["justa causa", "por justa"]):
        if "sem justa" in t:
            return "sem_justa_causa"
        return "justa_causa"
    if any(x in t for x in ["acordo mútuo", "acordo mutuo", "484-a", "484a"]):
        return "acordo_mutuo"
    if any(x in t for x in ["pediu demissão", "pediu demissao", "pedido de demissão",
                              "pedido demissão", "quer sair", "vai sair"]):
        return "pedido_demissao"
    if any(x in t for x in ["mandou embora", "demitiu", "sem justa", "dispensou",
                              "mandaram embora", "foi demitido"]):
        return "sem_justa_causa"
    return None


def extrair_regime(texto):
    """Detecta regime tributário mencionado."""
    t = texto.lower()
    if any(x in t for x in ["simples", "sn", "das", "anexo"]):
        return "simples"
    if any(x in t for x in ["presumido", "lp"]):
        return "presumido"
    if any(x in t for x in ["lucro real", "lr", "lalur"]):
        return "real"
    if "mei" in t:
        return "mei"
    return None


def extrair_uf(texto):
    """Detecta UF (estado) mencionado."""
    ufs = [
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO"
    ]
    nomes_uf = {
        "são paulo": "SP", "sao paulo": "SP", "minas": "MG", "minas gerais": "MG",
        "rio de janeiro": "RJ", "bahia": "BA", "paraná": "PR", "parana": "PR",
        "santa catarina": "SC", "rio grande do sul": "RS", "goiás": "GO", "goias": "GO",
        "pernambuco": "PE", "ceará": "CE", "ceara": "CE", "campinas": "SP",
    }

    encontrados = []  # list of (posição, uf)
    t_upper = texto.upper()
    t_lower = texto.lower()

    # Busca siglas (2 letras maiúsculas isoladas)
    for uf in ufs:
        m = re.search(r'\b' + uf + r'\b', t_upper)
        if m:
            encontrados.append((m.start(), uf))

    # Busca nomes por extenso
    for nome, uf in nomes_uf.items():
        pos = t_lower.find(nome)
        if pos >= 0 and uf not in [e[1] for e in encontrados]:
            encontrados.append((pos, uf))

    # Retorna na ordem de aparição no texto
    encontrados.sort(key=lambda x: x[0])
    return [e[1] for e in encontrados]


def extrair_parametros(texto, fluxo_id):
    """
    Extrai todos os parâmetros relevantes da mensagem.
    Retorna dict com os parâmetros encontrados.
    """
    params = {}

    valores = extrair_valores_monetarios(texto)
    if valores:
        params["valores_monetarios"] = sorted(valores, reverse=True)
        # Heurística: o maior valor tende a ser o principal
        if len(valores) == 1:
            params["valor_principal"] = valores[0]
        elif len(valores) >= 2:
            params["valor_principal"] = valores[0]  # maior

    meses = extrair_meses(texto)
    if meses:
        params["meses"] = meses

    anos = extrair_anos(texto)
    if anos:
        params["anos"] = anos

    pcts = extrair_percentual(texto)
    if pcts:
        params["percentuais"] = pcts

    horas = extrair_horas(texto)
    if horas:
        params["horas"] = horas

    deps = extrair_dependentes(texto)
    if deps:
        params["dependentes"] = deps

    # Parâmetros específicos por tipo de fluxo
    if fluxo_id == 3:  # Trabalhista
        tipo_resc = extrair_tipo_rescisao(texto)
        if tipo_resc:
            params["tipo_rescisao"] = tipo_resc

    if fluxo_id in [1, 2, 7, 15, 16, 17]:  # Tributário
        regime = extrair_regime(texto)
        if regime:
            params["regime"] = regime

    ufs = extrair_uf(texto)
    if ufs:
        params["ufs"] = ufs
        if len(ufs) == 2:
            params["uf_origem"] = ufs[0]
            params["uf_destino"] = ufs[1]

    return params


# ═══════════════════════════════════════════════════════════════
# CLASSIFICADOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def classificar_mensagem(texto, cliente_nome=None, grupo_nome=None):
    """
    Classifica uma mensagem de texto em um fluxo do skill.

    Args:
        texto: mensagem bruta do WhatsApp
        cliente_nome: nome do remetente (opcional, para contexto)
        grupo_nome: nome do grupo (opcional, para contexto)

    Returns:
        dict com:
            - fluxo_id: int (ID do fluxo, ou 0 se não classificável)
            - fluxo_nome: str
            - scripts: list[str] — scripts Python associados
            - calculavel: bool — se o skill pode computar uma resposta numérica
            - confianca: "alta", "media", "baixa", "nenhuma"
            - score: float (pontuação interna)
            - params_extraidos: dict com parâmetros numéricos encontrados
            - pergunta_resumida: str — resumo da pergunta em 1 linha
            - texto_original: str
            - timestamp: str ISO
    """
    if not texto or not texto.strip():
        return _resultado_vazio(texto, "Mensagem vazia")

    texto_clean = texto.strip()
    texto_lower = texto_clean.lower()

    # Aplicar aliases
    texto_expandido = texto_lower
    for alias, expansao in ALIASES.items():
        texto_expandido = texto_expandido.replace(alias, f"{alias} {expansao}")

    # Calcular score para cada fluxo
    scores = {}
    for fluxo_id, fluxo in FLUXOS.items():
        score = 0.0
        matches = []

        for kw in fluxo["keywords"]:
            if kw in texto_expandido:
                score += 1.0
                matches.append(kw)

        for kw in fluxo["keywords_forte"]:
            if kw in texto_expandido:
                score += 2.0  # bonus para keywords forte

        if score > 0:
            scores[fluxo_id] = {"score": score, "matches": matches}

    # Se nenhum fluxo matchou
    if not scores:
        return _resultado_vazio(texto_clean, "Nenhuma keyword reconhecida")

    # Ranking por score
    ranking = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
    melhor_id = ranking[0][0]
    melhor_score = ranking[0][1]["score"]
    melhor_fluxo = FLUXOS[melhor_id]

    # Determinar confiança
    if melhor_score >= 6.0:
        confianca = "alta"
    elif melhor_score >= 3.0:
        confianca = "media"
    elif melhor_score >= 1.0:
        confianca = "baixa"
    else:
        confianca = "nenhuma"

    # Se dois fluxos estão muito próximos, reduzir confiança
    if len(ranking) >= 2:
        segundo_score = ranking[1][1]["score"]
        if segundo_score >= melhor_score * 0.8:  # segundo é >= 80% do primeiro
            if confianca == "alta":
                confianca = "media"
            elif confianca == "media":
                confianca = "baixa"

    # Extrair parâmetros
    params = extrair_parametros(texto_clean, melhor_id)

    # Gerar resumo da pergunta
    resumo = _resumir_pergunta(texto_clean, melhor_fluxo["nome"])

    return {
        "fluxo_id": melhor_id,
        "fluxo_nome": melhor_fluxo["nome"],
        "scripts": melhor_fluxo["script"],
        "calculavel": melhor_fluxo["calculavel"],
        "confianca": confianca,
        "score": melhor_score,
        "keywords_matched": scores[melhor_id]["matches"],
        "params_extraidos": params,
        "pergunta_resumida": resumo,
        "alternativas": [
            {"fluxo_id": fid, "fluxo_nome": FLUXOS[fid]["nome"], "score": s["score"]}
            for fid, s in ranking[1:3]  # top 2 alternativas
        ],
        "texto_original": texto_clean,
        "cliente_nome": cliente_nome,
        "grupo_nome": grupo_nome,
        "timestamp": datetime.now().isoformat(),
    }


def _resultado_vazio(texto, motivo):
    """Resultado quando não foi possível classificar."""
    return {
        "fluxo_id": 0,
        "fluxo_nome": "Não classificado",
        "scripts": [],
        "calculavel": False,
        "confianca": "nenhuma",
        "score": 0.0,
        "keywords_matched": [],
        "params_extraidos": {},
        "pergunta_resumida": motivo,
        "alternativas": [],
        "texto_original": texto or "",
        "cliente_nome": None,
        "grupo_nome": None,
        "timestamp": datetime.now().isoformat(),
    }


def _resumir_pergunta(texto, fluxo_nome):
    """Gera resumo conciso da pergunta (1 linha, max 120 chars)."""
    # Limpar emojis e espaços duplos
    resumo = re.sub(r'[\U00010000-\U0010ffff]', '', texto)
    resumo = re.sub(r'\s+', ' ', resumo).strip()

    if len(resumo) <= 120:
        return resumo

    # Truncar com inteligência (não cortar palavra)
    resumo = resumo[:117]
    ultimo_espaco = resumo.rfind(' ')
    if ultimo_espaco > 80:
        resumo = resumo[:ultimo_espaco]
    return resumo + "..."


# ═══════════════════════════════════════════════════════════════
# CLASSIFICAÇÃO EM LOTE (para integração com monitora-whatsapp)
# ═══════════════════════════════════════════════════════════════

def classificar_lote(mensagens):
    """
    Classifica uma lista de mensagens de uma vez.

    Args:
        mensagens: list[dict] com pelo menos {"texto": str}
                   Opcionais: "cliente_nome", "grupo_nome", "data"

    Returns:
        list[dict] — cada item é o resultado de classificar_mensagem()
                     com campos adicionais do input preservados
    """
    resultados = []
    for msg in mensagens:
        r = classificar_mensagem(
            texto=msg.get("texto", ""),
            cliente_nome=msg.get("cliente_nome"),
            grupo_nome=msg.get("grupo_nome"),
        )
        # Preservar campos extras do input
        if "data" in msg:
            r["data_mensagem"] = msg["data"]
        if "status_atendimento" in msg:
            r["status_atendimento"] = msg["status_atendimento"]
        resultados.append(r)

    return resultados


def filtrar_calculaveis(resultados):
    """Filtra apenas mensagens que o skill pode responder com cálculo."""
    return [r for r in resultados if r["calculavel"] and r["confianca"] in ("alta", "media")]


# ═══════════════════════════════════════════════════════════════
# TESTES
# ═══════════════════════════════════════════════════════════════

def rodar_testes():
    testes_ok = 0
    testes_total = 0

    def teste(descricao, resultado, campo, esperado, campo2=None, esperado2=None):
        nonlocal testes_ok, testes_total
        testes_total += 1
        obtido = resultado.get(campo)
        passou = obtido == esperado
        if campo2 and passou:
            obtido2 = resultado.get(campo2)
            passou = obtido2 == esperado2
        if passou:
            testes_ok += 1
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}")
        if not passou:
            print(f"         {campo}: {obtido} (esperado {esperado})")
            if campo2 and resultado.get(campo2) != esperado2:
                print(f"         {campo2}: {resultado.get(campo2)} (esperado {esperado2})")

    def teste_in(descricao, resultado, campo, valor_esperado_contido):
        nonlocal testes_ok, testes_total
        testes_total += 1
        obtido = resultado.get(campo, [])
        passou = valor_esperado_contido in obtido if isinstance(obtido, (list, dict)) else valor_esperado_contido in str(obtido)
        if passou:
            testes_ok += 1
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}")
        if not passou:
            print(f"         {campo}: {obtido} (esperado conter: {valor_esperado_contido})")

    def teste_range(descricao, resultado, campo, vmin, vmax):
        nonlocal testes_ok, testes_total
        testes_total += 1
        obtido = resultado.get(campo, 0)
        passou = vmin <= obtido <= vmax
        if passou:
            testes_ok += 1
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}")
        if not passou:
            print(f"         {campo}: {obtido} (esperado entre {vmin} e {vmax})")

    print("\n🧪 RODANDO TESTES DO CLASSIFICADOR DE MENSAGENS...")
    print(f"{'─'*65}")

    # ═══ GRUPO 1: Classificação por Fluxo ═══
    print("\n  ── Classificação de Fluxos ──")

    # Simples Nacional
    r = classificar_mensagem("Empresa de tecnologia no Simples, faturou R$ 200 mil nos últimos 12 meses. Qual o DAS?")
    teste("Simples Nacional → Fluxo 2", r, "fluxo_id", 2)
    teste_in("Simples: extrai R$ 200k", r, "params_extraidos", "valor_principal")

    # Rescisão trabalhista
    r = classificar_mensagem("Funcionário pediu demissão com 2 anos de casa, salário de R$ 3.000. Quais as verbas?")
    teste("Rescisão → Fluxo 3", r, "fluxo_id", 3)
    teste("Rescisão: tipo = pedido_demissao", r["params_extraidos"], "tipo_rescisao", "pedido_demissao")
    teste("Rescisão: anos = 2", r["params_extraidos"], "anos", 2)

    # ICMS/DIFAL
    r = classificar_mensagem("Qual a alíquota de ICMS de SP pra vender pra MG?")
    teste("ICMS → Fluxo 1", r, "fluxo_id", 1)
    teste("ICMS: detecta SP e MG", r["params_extraidos"], "ufs", ["SP", "MG"])

    # Pró-labore
    r = classificar_mensagem("Quanto o sócio paga de pró-labore de R$ 5.000?")
    teste("Pró-labore → Fluxo 20", r, "fluxo_id", 20)

    # IRPF
    r = classificar_mensagem("Tenho 2 dependentes, ganho R$ 8.000 por mês. Quanto vou pagar de IRPF?")
    teste("IRPF → Fluxo 24", r, "fluxo_id", 24)
    teste("IRPF: dependentes = 2", r["params_extraidos"], "dependentes", 2)

    # MEI
    r = classificar_mensagem("Quanto posso faturar no MEI? Já tô com 70 mil esse ano")
    teste("MEI → Fluxo 19", r, "fluxo_id", 19)

    # Custo CLT
    r = classificar_mensagem("Quanto custa contratar um funcionário com salário de R$ 3.500?")
    teste("Custo CLT → Fluxo 8", r, "fluxo_id", 8)

    # Folha
    r = classificar_mensagem("Calcula o holerite de R$ 4.000 com insalubridade 20%")
    teste("Holerite → Fluxo 14", r, "fluxo_id", 14)

    # Distribuição de lucros
    r = classificar_mensagem("Como faço distribuição de lucros sem pagar imposto? Empresa no Presumido.")
    teste("Distribuição → Fluxo 21", r, "fluxo_id", 21)

    # Comparativo de regimes
    r = classificar_mensagem("Qual melhor regime pra empresa de serviços que fatura 500 mil por ano?")
    teste("Comparativo → Fluxo 17", r, "fluxo_id", 17)

    # Obrigações acessórias
    r = classificar_mensagem("Qual o prazo do eSocial esse mês?")
    teste("Obrigações → Fluxo 4", r, "fluxo_id", 4)
    teste("Obrigações: não calculável", r, "calculavel", False)

    # Acordo mútuo
    r = classificar_mensagem("Rescisão por acordo mútuo, salário R$ 5.800, 3 anos de casa")
    teste("Acordo mútuo → Fluxo 3", r, "fluxo_id", 3)
    teste("Acordo mútuo: tipo correto", r["params_extraidos"], "tipo_rescisao", "acordo_mutuo")
    teste("Acordo mútuo: anos = 3", r["params_extraidos"], "anos", 3)

    # Código DARF
    r = classificar_mensagem("Qual código DARF pro IRPJ trimestral?")
    teste("DARF → Fluxo 22", r, "fluxo_id", 22)

    # Lucro Real
    r = classificar_mensagem("Preciso calcular LALUR, a empresa tem prejuízo fiscal de R$ 200 mil")
    teste("Lucro Real → Fluxo 16", r, "fluxo_id", 16)

    # ═══ GRUPO 2: Extração de Parâmetros ═══
    print("\n  ── Extração de Parâmetros ──")

    # Valores monetários
    r = classificar_mensagem("Salário de R$ 3.500,00 com 10 horas extras")
    teste("Extrai R$ 3.500,00", r["params_extraidos"], "valor_principal", 3500.0)
    teste("Extrai 10 horas", r["params_extraidos"], "horas", 10)

    r = classificar_mensagem("Faturou 45k esse mês no Simples")
    teste("Extrai 45k = 45.000", r["params_extraidos"], "valor_principal", 45000.0)

    r = classificar_mensagem("DAS de empresa que fatura 30 mil por mês")
    teste("Extrai 30 mil = 30.000", r["params_extraidos"], "valor_principal", 30000.0)

    # Meses
    r = classificar_mensagem("13° proporcional de 6 meses, salário R$ 4.000")
    teste("Extrai 6 meses", r["params_extraidos"], "meses", 6)

    # Percentual
    r = classificar_mensagem("Insalubridade de 20%, salário R$ 2.500")
    teste("Extrai 20%", r["params_extraidos"], "percentuais", [20.0])

    # Regime
    r = classificar_mensagem("Empresa no Simples Nacional, faturou 180 mil")
    teste("Extrai regime = simples", r["params_extraidos"], "regime", "simples")

    # UFs
    r = classificar_mensagem("Venda de São Paulo para Bahia, qual DIFAL?")
    teste("Extrai UFs [SP, BA]", r["params_extraidos"], "ufs", ["SP", "BA"])

    # ═══ GRUPO 3: Confiança ═══
    print("\n  ── Níveis de Confiança ──")

    r = classificar_mensagem("Calcula rescisão sem justa causa de funcionário com 5 anos, salário R$ 4.500, aviso prévio indenizado")
    teste_range("Muitas keywords → confiança alta", r, "score", 6.0, 50.0)
    teste("Confiança alta", r, "confianca", "alta")

    r = classificar_mensagem("Oi pessoal, bom dia!")
    teste("Saudação → nenhuma", r, "confianca", "nenhuma")
    teste("Saudação → fluxo 0", r, "fluxo_id", 0)

    r = classificar_mensagem("Pode me mandar o boleto?")
    teste("Boleto → nenhuma (fora do escopo)", r, "confianca", "nenhuma")

    # ═══ GRUPO 4: Classificação em Lote ═══
    print("\n  ── Classificação em Lote ──")

    msgs = [
        {"texto": "Quanto pago de DAS? Faturei 50 mil", "cliente_nome": "João", "grupo_nome": "RRT Contabilidade - Empresa X"},
        {"texto": "Bom dia!", "cliente_nome": "Maria", "grupo_nome": "RRT Contabilidade - Empresa Y"},
        {"texto": "Rescisão do Pedro, 2 anos, R$ 3.000", "cliente_nome": "Carlos", "grupo_nome": "RRT Contabilidade - Empresa Z"},
    ]
    lote = classificar_lote(msgs)
    teste("Lote: 3 resultados", {"n": len(lote)}, "n", 3)

    calculaveis = filtrar_calculaveis(lote)
    teste("Lote: 2 calculáveis (DAS + rescisão)", {"n": len(calculaveis)}, "n", 2)

    # ═══ GRUPO 5: WhatsApp informal ═══
    print("\n  ── Mensagens Informais (WhatsApp real) ──")

    r = classificar_mensagem("ei gente quanto q tá o das desse mês? faturei uns 30k")
    teste("Informal 'das 30k' → Fluxo 2", r, "fluxo_id", 2)

    r = classificar_mensagem("meu funcionario vai sair... quanto vou pagar de rescisão? ele ganha 4500 e tem 3 anos")
    teste("Informal rescisão → Fluxo 3", r, "fluxo_id", 3)
    teste("Informal: salário 4500", r["params_extraidos"], "valor_principal", 4500.0)

    r = classificar_mensagem("pessoal preciso saber se vale mais a pena simples ou presumido pra faturamento de 800 mil ano")
    teste("Informal comparativo → Fluxo 17", r, "fluxo_id", 17)

    r = classificar_mensagem("to com duvida sobre meu imposto de renda, tenho acoes e crypto")
    teste("Informal IRPF+crypto → Fluxo 24", r, "fluxo_id", 24)

    r = classificar_mensagem("quanto meu socio tem que tirar de pro-labore?")
    teste("Informal pró-labore → Fluxo 20", r, "fluxo_id", 20)

    print(f"\n{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ❌ Há falhas — VERIFICAR antes de usar em produção")
    print()
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        ok = rodar_testes()
        sys.exit(0 if ok else 1)
    else:
        print("Uso: python3 classificar_mensagem.py --teste")
        print("\nClassificador de mensagens WhatsApp para fluxos RRT-Group-Contador")
