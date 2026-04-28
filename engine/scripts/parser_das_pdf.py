#!/usr/bin/env python3
"""
parser_das_pdf.py — Parser de guias DAS (Simples Nacional / MEI) em PDF
RRT Group Contador v4.5 — Inteligência Documental

Extrai dados estruturados de guias DAS geradas pelo PGDAS-D ou DAS-MEI:
  - CNPJ, razão social, período de apuração (competência)
  - Valor principal, juros, multa, total
  - Código de barras / linha digitável
  - Número do DAS, data de vencimento, data de acolhimento
  - Composição tributária (IRPJ, CSLL, COFINS, PIS, CPP, ICMS, ISS)

Também detecta se é DAS Simples Nacional ou DAS-MEI e faz validações
cruzadas com calc_simples.py e calc_mei.py.
"""

import re
from datetime import datetime, date
from typing import Optional

# ── Padrões regex para extração ──────────────────────────────────────────────

# CNPJ: 00.000.000/0000-00
RE_CNPJ = re.compile(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}')

# Competência: MM/YYYY ou mês por extenso/YYYY
RE_COMPETENCIA = re.compile(
    r'(?:Per[íi]odo\s+de\s+Apura[çc][ãa]o|Compet[êe]ncia|PA)[:\s]*'
    r'(\d{2}/\d{4})',
    re.IGNORECASE
)

# Valor monetário: R$ 1.234,56 ou 1234,56
RE_VALOR = re.compile(r'R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})')

# Linha digitável DAS: 5 blocos numéricos
RE_LINHA_DIGITAVEL = re.compile(
    r'(\d{11,12})\s+(\d{11,12})\s+(\d{11,12})\s+(\d{1})\s+(\d{14})'
)

# Código de barras numérico (47-48 dígitos)
RE_COD_BARRAS = re.compile(r'\b(\d{47,48})\b')

# Data DD/MM/YYYY
RE_DATA = re.compile(r'\b(\d{2}/\d{2}/\d{4})\b')

# Número do DAS
RE_NUM_DAS = re.compile(
    r'(?:N[úu]mero\s+(?:do\s+)?(?:DAS|Documento)|DAS\s+n[°º]?)[:\s]*(\d{10,20})',
    re.IGNORECASE
)

# Composição tributária — tributo e percentual/valor
RE_TRIBUTO = re.compile(
    r'(IRPJ|CSLL|COFINS|PIS/?PASEP|CPP|ICMS|ISS|CBS|IBS)'
    r'[:\s]+(?:R?\$?\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})(?!\s*%)',
    re.IGNORECASE
)

RE_TRIBUTO_PERCENT = re.compile(
    r'(IRPJ|CSLL|COFINS|PIS/?PASEP|CPP|ICMS|ISS|CBS|IBS)'
    r'[:\s]+(\d{1,2},\d{2,4})\s*%',
    re.IGNORECASE
)

# DAS-MEI vs DAS Simples
RE_DAS_MEI = re.compile(
    r'DAS[\s-]*MEI|DASN[\s-]*SIMEI|Microempreendedor\s+Individual',
    re.IGNORECASE
)

RE_DAS_SIMPLES = re.compile(
    r'PGDAS[\s-]*D|Simples\s+Nacional|DAS[\s-]*(?:Simples|SN)',
    re.IGNORECASE
)

# Razão social (linha após "Razão Social" ou "Nome Empresarial")
RE_RAZAO_SOCIAL = re.compile(
    r'(?:Raz[ãa]o\s+Social|Nome\s+Empresarial)[:\s]+(.+?)(?:\n|$)',
    re.IGNORECASE
)

# Vencimento
RE_VENCIMENTO = re.compile(
    r'(?:Vencimento|Data\s+de\s+Vencimento|Venc\.?)[:\s]*(\d{2}/\d{2}/\d{4})',
    re.IGNORECASE
)

# Valor total / valor do documento
RE_VALOR_TOTAL = re.compile(
    r'(?:Valor\s+(?:Total|do\s+Documento)|Total\s+(?:a\s+)?(?:Pagar|Recolher))[:\s]*'
    r'R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})',
    re.IGNORECASE
)

# Valor principal
RE_VALOR_PRINCIPAL = re.compile(
    r'(?:Valor\s+Principal|Principal)[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})',
    re.IGNORECASE
)

# Juros
RE_JUROS = re.compile(
    r'(?:Juros|Juros\s+de\s+Mora)[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})',
    re.IGNORECASE
)

# Multa
RE_MULTA = re.compile(
    r'(?:Multa|Multa\s+de\s+Mora)[:\s]*R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})',
    re.IGNORECASE
)

# Receita bruta total (faturamento do período)
RE_RECEITA_BRUTA = re.compile(
    r'(?:Receita\s+Bruta\s+(?:Total|Acumulada)|RBT12|Faturamento)[:\s]*'
    r'R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})',
    re.IGNORECASE
)

# Alíquota efetiva
RE_ALIQUOTA_EFETIVA = re.compile(
    r'(?:Al[íi]quota\s+Efetiva|Al[íi]q\.?\s+Efet\.?)[:\s]*(\d{1,2},\d{2,4})\s*%',
    re.IGNORECASE
)


def _parse_valor(texto: str) -> float:
    """Converte '1.234,56' → 1234.56"""
    return float(texto.replace('.', '').replace(',', '.'))


def _parse_data(texto: str) -> Optional[date]:
    """Converte 'DD/MM/YYYY' → date"""
    try:
        return datetime.strptime(texto, '%d/%m/%Y').date()
    except (ValueError, TypeError):
        return None


def _parse_competencia(texto: str) -> Optional[str]:
    """Converte 'MM/YYYY' → 'YYYY-MM' (formato ISO)"""
    try:
        parts = texto.split('/')
        if len(parts) == 2:
            mes, ano = parts
            return f"{ano}-{mes.zfill(2)}"
    except (ValueError, TypeError):
        pass
    return None


def extrair_dados_das(texto_pdf: str) -> dict:
    """
    Extrai dados estruturados de uma guia DAS a partir do texto extraído do PDF.

    Args:
        texto_pdf: Texto extraído do PDF da guia DAS

    Returns:
        dict com campos extraídos, tipo de DAS, e alertas
    """
    if not texto_pdf or not texto_pdf.strip():
        return {
            "sucesso": False,
            "erro": "Texto do PDF vazio ou nulo",
            "dados": {},
            "alertas": ["PDF sem conteúdo para extração"]
        }

    dados = {}
    alertas = []

    # ── Tipo de DAS ──
    is_mei = bool(RE_DAS_MEI.search(texto_pdf))
    is_simples = bool(RE_DAS_SIMPLES.search(texto_pdf))

    if is_mei:
        dados["tipo_das"] = "DAS-MEI"
    elif is_simples:
        dados["tipo_das"] = "DAS-SIMPLES"
    else:
        dados["tipo_das"] = "DAS-INDEFINIDO"
        alertas.append("Não foi possível identificar se é DAS-MEI ou DAS-Simples. Conferir manualmente.")

    # ── CNPJ ──
    cnpjs = RE_CNPJ.findall(texto_pdf)
    if cnpjs:
        dados["cnpj"] = cnpjs[0]
        if len(cnpjs) > 1:
            alertas.append(f"Múltiplos CNPJs encontrados: {cnpjs}. Usando o primeiro.")
    else:
        alertas.append("CNPJ não encontrado no PDF.")

    # ── Razão Social ──
    m_razao = RE_RAZAO_SOCIAL.search(texto_pdf)
    if m_razao:
        dados["razao_social"] = m_razao.group(1).strip()

    # ── Competência ──
    m_comp = RE_COMPETENCIA.search(texto_pdf)
    if m_comp:
        comp_iso = _parse_competencia(m_comp.group(1))
        if comp_iso:
            dados["competencia"] = comp_iso
            dados["competencia_original"] = m_comp.group(1)
    else:
        alertas.append("Competência (período de apuração) não encontrada.")

    # ── Número do DAS ──
    m_num = RE_NUM_DAS.search(texto_pdf)
    if m_num:
        dados["numero_das"] = m_num.group(1)

    # ── Vencimento ──
    m_venc = RE_VENCIMENTO.search(texto_pdf)
    if m_venc:
        dt = _parse_data(m_venc.group(1))
        if dt:
            dados["vencimento"] = dt.isoformat()
            dados["vencimento_original"] = m_venc.group(1)
            # Check if overdue
            if dt < date.today():
                dias_atraso = (date.today() - dt).days
                dados["em_atraso"] = True
                dados["dias_atraso"] = dias_atraso
                alertas.append(f"DAS VENCIDO há {dias_atraso} dias. Verificar juros e multa atualizados.")
            else:
                dados["em_atraso"] = False
    else:
        alertas.append("Data de vencimento não encontrada.")

    # ── Valores ──
    m_total = RE_VALOR_TOTAL.search(texto_pdf)
    if m_total:
        dados["valor_total"] = _parse_valor(m_total.group(1))

    m_principal = RE_VALOR_PRINCIPAL.search(texto_pdf)
    if m_principal:
        dados["valor_principal"] = _parse_valor(m_principal.group(1))

    m_juros = RE_JUROS.search(texto_pdf)
    if m_juros:
        dados["juros"] = _parse_valor(m_juros.group(1))

    m_multa = RE_MULTA.search(texto_pdf)
    if m_multa:
        dados["multa"] = _parse_valor(m_multa.group(1))

    # Validação cruzada de valores
    if all(k in dados for k in ["valor_principal", "juros", "multa", "valor_total"]):
        soma = round(dados["valor_principal"] + dados["juros"] + dados["multa"], 2)
        if abs(soma - dados["valor_total"]) > 0.01:
            alertas.append(
                f"Divergência de valores: Principal ({dados['valor_principal']}) + "
                f"Juros ({dados['juros']}) + Multa ({dados['multa']}) = {soma}, "
                f"mas Total = {dados['valor_total']}. Diferença: {round(abs(soma - dados['valor_total']), 2)}"
            )

    # Se só tem total e não tem principal, assumir que principal = total (sem juros/multa)
    if "valor_total" in dados and "valor_principal" not in dados:
        dados["valor_principal"] = dados["valor_total"]
        dados["juros"] = 0.0
        dados["multa"] = 0.0

    # ── Receita Bruta / Alíquota ──
    m_rb = RE_RECEITA_BRUTA.search(texto_pdf)
    if m_rb:
        dados["receita_bruta"] = _parse_valor(m_rb.group(1))

    m_aliq = RE_ALIQUOTA_EFETIVA.search(texto_pdf)
    if m_aliq:
        dados["aliquota_efetiva"] = _parse_valor(m_aliq.group(1))

    # ── Composição Tributária ──
    composicao = {}
    for m in RE_TRIBUTO.finditer(texto_pdf):
        tributo = m.group(1).upper().replace('/', '')
        valor = _parse_valor(m.group(2))
        composicao[tributo] = {"valor": valor}

    for m in RE_TRIBUTO_PERCENT.finditer(texto_pdf):
        tributo = m.group(1).upper().replace('/', '')
        pct = _parse_valor(m.group(2))
        if tributo in composicao:
            composicao[tributo]["percentual"] = pct
        else:
            composicao[tributo] = {"percentual": pct}

    if composicao:
        dados["composicao_tributaria"] = composicao

        # Validar que soma da composição = valor principal
        soma_comp = sum(v.get("valor", 0) for v in composicao.values())
        if "valor_principal" in dados and soma_comp > 0:
            if abs(soma_comp - dados["valor_principal"]) > 0.01:
                alertas.append(
                    f"Soma da composição tributária ({soma_comp:.2f}) difere do "
                    f"valor principal ({dados['valor_principal']:.2f})."
                )

    # ── Linha digitável / Código de barras ──
    m_ld = RE_LINHA_DIGITAVEL.search(texto_pdf)
    if m_ld:
        dados["linha_digitavel"] = ' '.join(m_ld.groups())

    m_cb = RE_COD_BARRAS.search(texto_pdf)
    if m_cb:
        dados["codigo_barras"] = m_cb.group(1)

    # ── Validações MEI ──
    if dados.get("tipo_das") == "DAS-MEI":
        if "valor_total" in dados:
            # DAS-MEI em 2026: INSS 5% de R$1.621,00 = R$81,05 + ICMS R$1 + ISS R$5
            valor = dados["valor_total"]
            if valor < 75.0 or valor > 200.0:
                alertas.append(
                    f"Valor DAS-MEI ({valor:.2f}) fora da faixa esperada (R$75-200). "
                    f"Conferir se é MEI ou se houve reajuste de SM."
                )

    # ── Validações Simples Nacional ──
    if dados.get("tipo_das") == "DAS-SIMPLES":
        if "aliquota_efetiva" in dados:
            aliq = dados["aliquota_efetiva"]
            if aliq < 4.0 or aliq > 33.0:
                alertas.append(
                    f"Alíquota efetiva ({aliq:.2f}%) fora da faixa do Simples Nacional (4%-33%). "
                    f"Verificar enquadramento ou se o valor inclui sublimite."
                )

    # ── Determinar confiança ──
    campos_criticos = ["cnpj", "competencia", "valor_total", "vencimento"]
    campos_presentes = sum(1 for c in campos_criticos if c in dados)

    if campos_presentes == len(campos_criticos):
        confianca = "alta"
    elif campos_presentes >= 2:
        confianca = "media"
    else:
        confianca = "baixa"
        alertas.append("Poucos campos extraídos. O PDF pode não ser uma guia DAS ou o formato é incomum.")

    return {
        "sucesso": True,
        "confianca": confianca,
        "dados": dados,
        "alertas": alertas,
        "campos_extraidos": list(dados.keys()),
        "campos_criticos_presentes": campos_presentes,
        "campos_criticos_total": len(campos_criticos)
    }


def comparar_com_calculo(dados_das: dict, resultado_calc: dict) -> dict:
    """
    Compara dados extraídos do DAS com resultado de calc_simples.py ou calc_mei.py.

    Args:
        dados_das: dict retornado por extrair_dados_das()["dados"]
        resultado_calc: dict retornado por calc_simples() ou calc_mei()

    Returns:
        dict com divergências encontradas e status de validação
    """
    divergencias = []
    conferencias_ok = []

    # Comparar valor total
    valor_das = dados_das.get("valor_total")
    valor_calc = resultado_calc.get("valor_total") or resultado_calc.get("das_total") or resultado_calc.get("total")

    if valor_das is not None and valor_calc is not None:
        diff = abs(valor_das - valor_calc)
        if diff > 0.01:
            divergencias.append({
                "campo": "valor_total",
                "valor_pdf": valor_das,
                "valor_calculado": valor_calc,
                "diferenca": round(diff, 2),
                "percentual": round((diff / max(valor_das, valor_calc)) * 100, 2)
            })
        else:
            conferencias_ok.append("valor_total")

    # Comparar alíquota efetiva
    aliq_das = dados_das.get("aliquota_efetiva")
    aliq_calc = resultado_calc.get("aliquota_efetiva") or resultado_calc.get("aliquota")

    if aliq_das is not None and aliq_calc is not None:
        diff_aliq = abs(aliq_das - aliq_calc)
        if diff_aliq > 0.01:
            divergencias.append({
                "campo": "aliquota_efetiva",
                "valor_pdf": aliq_das,
                "valor_calculado": aliq_calc,
                "diferenca": round(diff_aliq, 4)
            })
        else:
            conferencias_ok.append("aliquota_efetiva")

    # Comparar composição tributária
    comp_das = dados_das.get("composicao_tributaria", {})
    comp_calc = resultado_calc.get("composicao", {}) or resultado_calc.get("detalhamento", {})

    for tributo, dados_trib in comp_das.items():
        valor_trib_das = dados_trib.get("valor")
        valor_trib_calc = comp_calc.get(tributo, {}).get("valor") if isinstance(comp_calc.get(tributo), dict) else comp_calc.get(tributo)

        if valor_trib_das is not None and valor_trib_calc is not None:
            diff_t = abs(valor_trib_das - valor_trib_calc)
            if diff_t > 0.01:
                divergencias.append({
                    "campo": f"composicao.{tributo}",
                    "valor_pdf": valor_trib_das,
                    "valor_calculado": valor_trib_calc,
                    "diferenca": round(diff_t, 2)
                })
            else:
                conferencias_ok.append(f"composicao.{tributo}")

    status = "ok" if not divergencias else "divergencia"

    return {
        "status": status,
        "divergencias": divergencias,
        "conferencias_ok": conferencias_ok,
        "total_divergencias": len(divergencias),
        "total_ok": len(conferencias_ok),
        "requer_revisao_humana": len(divergencias) > 0
    }


def gerar_resumo_das(resultado: dict) -> str:
    """
    Gera resumo textual formatado dos dados extraídos do DAS.

    Args:
        resultado: dict retornado por extrair_dados_das()

    Returns:
        String formatada com resumo dos dados
    """
    if not resultado.get("sucesso"):
        return f"❌ Erro na extração: {resultado.get('erro', 'desconhecido')}"

    dados = resultado["dados"]
    linhas = []

    # Cabeçalho
    tipo = dados.get("tipo_das", "DAS")
    linhas.append(f"{'='*50}")
    linhas.append(f"  RESUMO {tipo}")
    linhas.append(f"{'='*50}")

    if "cnpj" in dados:
        linhas.append(f"CNPJ: {dados['cnpj']}")
    if "razao_social" in dados:
        linhas.append(f"Razão Social: {dados['razao_social']}")
    if "competencia_original" in dados:
        linhas.append(f"Competência: {dados['competencia_original']}")
    if "vencimento_original" in dados:
        atraso = ""
        if dados.get("em_atraso"):
            atraso = f" ⚠️ VENCIDO ({dados['dias_atraso']} dias)"
        linhas.append(f"Vencimento: {dados['vencimento_original']}{atraso}")

    linhas.append(f"{'-'*50}")

    if "valor_principal" in dados:
        linhas.append(f"Valor Principal: R$ {dados['valor_principal']:,.2f}")
    if dados.get("juros", 0) > 0:
        linhas.append(f"Juros: R$ {dados['juros']:,.2f}")
    if dados.get("multa", 0) > 0:
        linhas.append(f"Multa: R$ {dados['multa']:,.2f}")
    if "valor_total" in dados:
        linhas.append(f"TOTAL A PAGAR: R$ {dados['valor_total']:,.2f}")

    if "aliquota_efetiva" in dados:
        linhas.append(f"Alíquota Efetiva: {dados['aliquota_efetiva']:.2f}%")
    if "receita_bruta" in dados:
        linhas.append(f"Receita Bruta: R$ {dados['receita_bruta']:,.2f}")

    # Composição tributária
    comp = dados.get("composicao_tributaria", {})
    if comp:
        linhas.append(f"\n{'─'*30}")
        linhas.append("COMPOSIÇÃO TRIBUTÁRIA:")
        for tributo, valores in sorted(comp.items()):
            parts = []
            if "valor" in valores:
                parts.append(f"R$ {valores['valor']:,.2f}")
            if "percentual" in valores:
                parts.append(f"{valores['percentual']:.2f}%")
            linhas.append(f"  {tributo}: {' | '.join(parts)}")

    # Linha digitável
    if "linha_digitavel" in dados:
        linhas.append(f"\nLinha Digitável: {dados['linha_digitavel']}")

    # Alertas
    alertas = resultado.get("alertas", [])
    if alertas:
        linhas.append(f"\n{'!'*50}")
        linhas.append("ALERTAS:")
        for a in alertas:
            linhas.append(f"  ⚠ {a}")

    linhas.append(f"\nConfiança: {resultado.get('confianca', '?').upper()}")
    linhas.append(f"Campos extraídos: {resultado.get('campos_criticos_presentes')}/{resultado.get('campos_criticos_total')} críticos")

    return '\n'.join(linhas)


def processar_lote_das(textos_pdf: list[str]) -> dict:
    """
    Processa múltiplas guias DAS de uma vez.

    Args:
        textos_pdf: lista de textos extraídos de PDFs

    Returns:
        dict com resultados consolidados, totais, e alertas agregados
    """
    resultados = []
    total_valor = 0.0
    total_juros = 0.0
    total_multa = 0.0
    por_competencia = {}
    alertas_globais = []

    for i, texto in enumerate(textos_pdf):
        resultado = extrair_dados_das(texto)
        resultado["indice"] = i
        resultados.append(resultado)

        if resultado.get("sucesso"):
            dados = resultado["dados"]
            valor = dados.get("valor_total", 0)
            total_valor += valor
            total_juros += dados.get("juros", 0)
            total_multa += dados.get("multa", 0)

            comp = dados.get("competencia")
            if comp:
                if comp in por_competencia:
                    alertas_globais.append(
                        f"Competência {comp} duplicada (guias {por_competencia[comp]} e {i}). "
                        f"Verificar se não é pagamento em duplicidade."
                    )
                por_competencia[comp] = i

    # Ordenar por competência
    comp_ordenadas = sorted(por_competencia.keys()) if por_competencia else []

    return {
        "total_guias": len(textos_pdf),
        "extraidas_com_sucesso": sum(1 for r in resultados if r.get("sucesso")),
        "total_valor": round(total_valor, 2),
        "total_juros": round(total_juros, 2),
        "total_multa": round(total_multa, 2),
        "competencias": comp_ordenadas,
        "resultados": resultados,
        "alertas_globais": alertas_globais
    }


# ══════════════════════════════════════════════════════════════════════════════
# TESTES
# ══════════════════════════════════════════════════════════════════════════════

def _rodar_testes():
    """Testes unitários para parser_das_pdf.py"""
    testes_passou = 0
    testes_falhou = 0

    def ok(condicao, descricao):
        nonlocal testes_passou, testes_falhou
        if condicao:
            testes_passou += 1
        else:
            testes_falhou += 1
            print(f"  FALHOU: {descricao}")

    # ── Teste 1: Parse valor monetário ──
    ok(_parse_valor("1.234,56") == 1234.56, "parse valor 1.234,56")
    ok(_parse_valor("81,05") == 81.05, "parse valor 81,05")
    ok(_parse_valor("12.345.678,90") == 12345678.90, "parse valor grande")
    ok(_parse_valor("0,00") == 0.0, "parse valor zero")

    # ── Teste 2: Parse data ──
    ok(_parse_data("20/01/2026") == date(2026, 1, 20), "parse data normal")
    ok(_parse_data("invalida") is None, "parse data inválida")
    ok(_parse_data("") is None, "parse data vazia")

    # ── Teste 3: Parse competência ──
    ok(_parse_competencia("03/2026") == "2026-03", "parse competência normal")
    ok(_parse_competencia("12/2025") == "2025-12", "parse competência dezembro")
    ok(_parse_competencia("invalida") is None, "parse competência inválida")

    # ── Teste 4: DAS-MEI básico ──
    texto_mei = """
    DOCUMENTO DE ARRECADAÇÃO DO SIMPLES NACIONAL
    DAS-MEI - Microempreendedor Individual

    CNPJ: 12.345.678/0001-99
    Razão Social: JOAO DA SILVA MEI
    Período de Apuração: 03/2026

    Data de Vencimento: 20/04/2026

    Valor Principal: R$ 81,05
    Juros: R$ 0,00
    Multa: R$ 0,00
    Valor Total: R$ 81,05

    INSS: R$ 81,05
    ICMS: R$ 1,00

    Número do DAS: 12345678901234
    """
    r = extrair_dados_das(texto_mei)
    ok(r["sucesso"] == True, "MEI: sucesso")
    ok(r["dados"]["tipo_das"] == "DAS-MEI", "MEI: tipo correto")
    ok(r["dados"]["cnpj"] == "12.345.678/0001-99", "MEI: CNPJ extraído")
    ok(r["dados"]["razao_social"] == "JOAO DA SILVA MEI", "MEI: razão social")
    ok(r["dados"]["competencia"] == "2026-03", "MEI: competência ISO")
    ok(r["dados"]["valor_total"] == 81.05, "MEI: valor total")
    ok(r["dados"]["valor_principal"] == 81.05, "MEI: valor principal")
    ok(r["dados"]["vencimento"] == "2026-04-20", "MEI: vencimento ISO")
    ok(r["dados"]["numero_das"] == "12345678901234", "MEI: número DAS")
    ok(r["confianca"] == "alta", "MEI: confiança alta")

    # ── Teste 5: DAS Simples Nacional ──
    texto_simples = """
    PGDAS-D - Programa Gerador do DAS
    Simples Nacional

    CNPJ: 98.765.432/0001-10
    Razão Social: EMPRESA EXEMPLO LTDA
    Período de Apuração: 02/2026

    Data de Vencimento: 20/03/2026

    Receita Bruta Total: R$ 250.000,00
    Alíquota Efetiva: 11,20%

    Valor Principal: R$ 5.600,00
    Juros de Mora: R$ 112,00
    Multa de Mora: R$ 56,00
    Valor Total: R$ 5.768,00

    IRPJ: R$ 280,00
    CSLL: R$ 196,00
    COFINS: R$ 728,00
    PIS/PASEP: R$ 158,00
    CPP: R$ 2.408,00
    ICMS: R$ 1.830,00

    IRPJ: 0,50%
    CSLL: 0,35%
    COFINS: 1,30%
    PIS/PASEP: 0,28%
    CPP: 4,30%
    ICMS: 3,27%
    """
    r2 = extrair_dados_das(texto_simples)
    ok(r2["sucesso"] == True, "SN: sucesso")
    ok(r2["dados"]["tipo_das"] == "DAS-SIMPLES", "SN: tipo correto")
    ok(r2["dados"]["cnpj"] == "98.765.432/0001-10", "SN: CNPJ")
    ok(r2["dados"]["competencia"] == "2026-02", "SN: competência")
    ok(r2["dados"]["valor_total"] == 5768.0, "SN: valor total")
    ok(r2["dados"]["valor_principal"] == 5600.0, "SN: valor principal")
    ok(r2["dados"]["juros"] == 112.0, "SN: juros")
    ok(r2["dados"]["multa"] == 56.0, "SN: multa")
    ok(r2["dados"]["receita_bruta"] == 250000.0, "SN: receita bruta")
    ok(r2["dados"]["aliquota_efetiva"] == 11.20, "SN: alíquota efetiva")
    ok(r2["dados"]["em_atraso"] == True, "SN: detectou atraso")
    ok("composicao_tributaria" in r2["dados"], "SN: composição presente")
    ok(r2["dados"]["composicao_tributaria"]["IRPJ"]["valor"] == 280.0, "SN: IRPJ valor")
    ok(r2["dados"]["composicao_tributaria"]["ICMS"]["percentual"] == 3.27, "SN: ICMS %")
    ok(r2["confianca"] == "alta", "SN: confiança alta")

    # ── Teste 6: Validação cruzada principal+juros+multa ──
    texto_divergente = """
    DAS-MEI
    CNPJ: 11.222.333/0001-44
    Período de Apuração: 01/2026
    Vencimento: 20/02/2026
    Valor Principal: R$ 81,05
    Juros: R$ 5,00
    Multa: R$ 3,00
    Valor Total: R$ 100,00
    """
    r3 = extrair_dados_das(texto_divergente)
    ok(r3["sucesso"] == True, "Divergência: sucesso")
    ok(any("Divergência de valores" in a for a in r3["alertas"]), "Divergência: alerta gerado")

    # ── Teste 7: PDF vazio ──
    r4 = extrair_dados_das("")
    ok(r4["sucesso"] == False, "Vazio: falha")
    ok("vazio" in r4["erro"].lower(), "Vazio: mensagem de erro")

    r5 = extrair_dados_das(None)
    ok(r5["sucesso"] == False, "None: falha")

    # ── Teste 8: PDF sem campos reconhecíveis ──
    r6 = extrair_dados_das("Este é um texto qualquer sem dados de DAS")
    ok(r6["sucesso"] == True, "Irreconhecível: sucesso (mas baixa confiança)")
    ok(r6["confianca"] == "baixa", "Irreconhecível: confiança baixa")

    # ── Teste 9: Comparar com cálculo — sem divergência ──
    dados_ok = {"valor_total": 81.05, "aliquota_efetiva": 5.0}
    calc_ok = {"valor_total": 81.05, "aliquota_efetiva": 5.0}
    comp = comparar_com_calculo(dados_ok, calc_ok)
    ok(comp["status"] == "ok", "Comparação ok: status ok")
    ok(comp["total_divergencias"] == 0, "Comparação ok: zero divergências")
    ok(comp["requer_revisao_humana"] == False, "Comparação ok: sem revisão")

    # ── Teste 10: Comparar com cálculo — com divergência ──
    dados_div = {"valor_total": 5768.0}
    calc_div = {"valor_total": 5600.0}
    comp2 = comparar_com_calculo(dados_div, calc_div)
    ok(comp2["status"] == "divergencia", "Comparação div: status divergência")
    ok(comp2["total_divergencias"] == 1, "Comparação div: uma divergência")
    ok(comp2["requer_revisao_humana"] == True, "Comparação div: requer revisão")
    ok(comp2["divergencias"][0]["diferenca"] == 168.0, "Comparação div: diferença correta")

    # ── Teste 11: Gerar resumo MEI ──
    resumo = gerar_resumo_das(r)
    ok("DAS-MEI" in resumo, "Resumo: tipo DAS-MEI presente")
    ok("12.345.678/0001-99" in resumo, "Resumo: CNPJ presente")
    ok("81,05" in resumo or "81.05" in resumo, "Resumo: valor presente")
    ok("ALTA" in resumo, "Resumo: confiança presente")

    # ── Teste 12: Gerar resumo de erro ──
    resumo_err = gerar_resumo_das({"sucesso": False, "erro": "teste"})
    ok("Erro" in resumo_err, "Resumo erro: mensagem de erro")

    # ── Teste 13: Processar lote ──
    lote = processar_lote_das([texto_mei, texto_simples])
    ok(lote["total_guias"] == 2, "Lote: total guias")
    ok(lote["extraidas_com_sucesso"] == 2, "Lote: todas com sucesso")
    ok(lote["total_valor"] == 81.05 + 5768.0, "Lote: total valor")
    ok(len(lote["competencias"]) == 2, "Lote: 2 competências")
    ok("2026-02" in lote["competencias"], "Lote: competência 02")
    ok("2026-03" in lote["competencias"], "Lote: competência 03")

    # ── Teste 14: Lote com competência duplicada ──
    texto_dup = texto_mei  # mesma competência 03/2026
    lote2 = processar_lote_das([texto_mei, texto_dup])
    ok(any("duplicada" in a.lower() for a in lote2["alertas_globais"]), "Lote dup: alerta duplicidade")

    # ── Teste 15: DAS-MEI com valor fora da faixa ──
    texto_mei_caro = """
    DAS-MEI Microempreendedor Individual
    CNPJ: 55.666.777/0001-88
    Período de Apuração: 04/2026
    Vencimento: 20/05/2026
    Valor Total: R$ 500,00
    """
    r7 = extrair_dados_das(texto_mei_caro)
    ok(any("fora da faixa" in a.lower() for a in r7["alertas"]), "MEI caro: alerta faixa")

    # ── Teste 16: DAS Simples com alíquota fora da faixa ──
    texto_sn_aliq = """
    PGDAS-D Simples Nacional
    CNPJ: 44.555.666/0001-77
    Período de Apuração: 01/2026
    Vencimento: 20/02/2026
    Alíquota Efetiva: 40,00%
    Valor Total: R$ 10.000,00
    """
    r8 = extrair_dados_das(texto_sn_aliq)
    ok(any("fora da faixa" in a.lower() for a in r8["alertas"]), "SN alíq alta: alerta faixa")

    # ── Teste 17: Confiança média (faltando alguns campos) ──
    texto_parcial = """
    DAS-MEI
    CNPJ: 33.444.555/0001-66
    Valor Total: R$ 81,05
    """
    r9 = extrair_dados_das(texto_parcial)
    ok(r9["confianca"] == "media", "Parcial: confiança média")

    # ── Teste 18: Múltiplos CNPJs ──
    texto_multi_cnpj = """
    DAS-MEI
    CNPJ: 11.111.111/0001-11
    CNPJ Matriz: 22.222.222/0001-22
    Período de Apuração: 05/2026
    Vencimento: 20/06/2026
    Valor Total: R$ 81,05
    """
    r10 = extrair_dados_das(texto_multi_cnpj)
    ok(r10["dados"]["cnpj"] == "11.111.111/0001-11", "Multi CNPJ: usa primeiro")
    ok(any("Múltiplos CNPJs" in a for a in r10["alertas"]), "Multi CNPJ: alerta")

    # ── Teste 19: Comparar composição tributária ──
    dados_comp = {
        "valor_total": 5600.0,
        "composicao_tributaria": {
            "IRPJ": {"valor": 280.0},
            "CSLL": {"valor": 196.0}
        }
    }
    calc_comp = {
        "valor_total": 5600.0,
        "composicao": {
            "IRPJ": {"valor": 280.0},
            "CSLL": {"valor": 200.0}  # divergência
        }
    }
    comp3 = comparar_com_calculo(dados_comp, calc_comp)
    ok(comp3["total_divergencias"] == 1, "Comp trib: 1 divergência (CSLL)")
    ok(comp3["total_ok"] == 2, "Comp trib: 2 ok (valor_total + IRPJ)")

    # ── Teste 20: Lote vazio ──
    lote_vazio = processar_lote_das([])
    ok(lote_vazio["total_guias"] == 0, "Lote vazio: zero guias")
    ok(lote_vazio["total_valor"] == 0.0, "Lote vazio: total zero")

    # ── Teste 21: Valor total sem principal (assume total = principal) ──
    texto_so_total = """
    DAS-MEI
    CNPJ: 77.888.999/0001-00
    Período de Apuração: 06/2026
    Vencimento: 20/07/2026
    Valor Total: R$ 82,10
    """
    r11 = extrair_dados_das(texto_so_total)
    ok(r11["dados"]["valor_principal"] == 82.10, "Só total: principal = total")
    ok(r11["dados"]["juros"] == 0.0, "Só total: juros = 0")
    ok(r11["dados"]["multa"] == 0.0, "Só total: multa = 0")

    # ── Teste 22: DAS indefinido (sem marcadores MEI ou SN) ──
    texto_indefinido = """
    Documento de Arrecadação
    CNPJ: 66.777.888/0001-99
    Competência: 07/2026
    Vencimento: 20/08/2026
    Valor Total: R$ 1.500,00
    """
    r12 = extrair_dados_das(texto_indefinido)
    ok(r12["dados"]["tipo_das"] == "DAS-INDEFINIDO", "Indefinido: tipo correto")
    ok(any("Não foi possível identificar" in a for a in r12["alertas"]), "Indefinido: alerta tipo")

    print(f"\n{'='*50}")
    print(f"parser_das_pdf.py: {testes_passou} PASSOU, {testes_falhou} FALHOU de {testes_passou + testes_falhou}")
    print(f"{'='*50}")

    return testes_falhou == 0


if __name__ == "__main__":
    _rodar_testes()
