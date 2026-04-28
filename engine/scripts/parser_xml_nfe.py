#!/usr/bin/env python3
"""
parser_xml_nfe.py — Parser de XMLs de Notas Fiscais Eletrônicas
RRT Group Contador v4.5 — Inteligência Documental

Suporta:
  - NF-e (Nota Fiscal Eletrônica — modelo 55)
  - NFC-e (Nota Fiscal de Consumidor — modelo 65)
  - NFS-e (Nota Fiscal de Serviço — padrão ABRASF e variantes)
  - CT-e (Conhecimento de Transporte — modelo 57)

Extrai dados estruturados para fechamento fiscal:
  - Emitente/Destinatário (CNPJ, razão social, UF, IE)
  - Valores (produtos, frete, seguro, desconto, total)
  - ICMS (base, alíquota, valor, CST/CSOSN, DIFAL, ST)
  - IPI, PIS, COFINS, ISS
  - CFOP, NCM, produtos/serviços
  - Chave de acesso, número, série, data emissão

Integra com fechamento-fiscal skill para apuração mensal.
"""

import re
from datetime import datetime, date
from typing import Optional
import xml.etree.ElementTree as ET


# ── Namespaces comuns ────────────────────────────────────────────────────────

NS_NFE = 'http://www.portalfiscal.inf.br/nfe'
NS_CTE = 'http://www.portalfiscal.inf.br/cte'
NS_NFSE_ABRASF = 'http://www.abrasf.org.br/nfse.xsd'

# Map para facilitar busca com namespace
def _ns(tag: str, namespace: str = NS_NFE) -> str:
    return f'{{{namespace}}}{tag}'


def _find_text(elem, path: str, ns: str = NS_NFE) -> Optional[str]:
    """Busca texto em elemento XML com namespace."""
    if elem is None:
        return None
    # Tenta com namespace
    parts = path.split('/')
    ns_path = '/'.join(_ns(p, ns) for p in parts)
    el = elem.find(ns_path)
    if el is not None and el.text:
        return el.text.strip()
    # Tenta sem namespace (para XMLs mal formatados)
    el = elem.find(path)
    if el is not None and el.text:
        return el.text.strip()
    return None


def _safe_float(texto: Optional[str]) -> Optional[float]:
    """Converte texto para float de forma segura."""
    if texto is None:
        return None
    try:
        return float(texto)
    except (ValueError, TypeError):
        return None


def _safe_int(texto: Optional[str]) -> Optional[int]:
    """Converte texto para int de forma segura."""
    if texto is None:
        return None
    try:
        return int(texto)
    except (ValueError, TypeError):
        return None


def _parse_data_xml(texto: Optional[str]) -> Optional[str]:
    """Converte data XML para ISO. Aceita YYYY-MM-DD ou YYYY-MM-DDThh:mm:ss."""
    if not texto:
        return None
    try:
        # Remove timezone info se presente
        texto = texto.split('+')[0].split('-03:00')[0].split('-02:00')[0]
        if 'T' in texto:
            dt = datetime.fromisoformat(texto)
        else:
            dt = datetime.strptime(texto[:10], '%Y-%m-%d')
        return dt.date().isoformat()
    except (ValueError, TypeError):
        return None


# ══════════════════════════════════════════════════════════════════════════════
# DETECTAR TIPO DE XML
# ══════════════════════════════════════════════════════════════════════════════

def detectar_tipo_xml(xml_string: str) -> dict:
    """
    Detecta o tipo de documento fiscal a partir do XML.

    Returns:
        dict com tipo ('nfe', 'nfce', 'nfse', 'cte', 'desconhecido'),
        modelo e namespace detectado.
    """
    if not xml_string or not xml_string.strip():
        return {"tipo": "desconhecido", "modelo": None, "erro": "XML vazio"}

    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        return {"tipo": "desconhecido", "modelo": None, "erro": f"XML inválido: {e}"}

    tag = root.tag.lower()
    ns = ''
    if '}' in root.tag:
        ns = root.tag.split('}')[0] + '}'

    # NF-e / NFC-e
    if 'nfe' in tag or NS_NFE in root.tag:
        # Checar modelo (55=NF-e, 65=NFC-e)
        mod_el = _find_any(root, 'mod')
        mod = mod_el.text.strip() if mod_el is not None and mod_el.text else None
        if mod == '65':
            return {"tipo": "nfce", "modelo": "65", "namespace": ns}
        return {"tipo": "nfe", "modelo": mod or "55", "namespace": ns}

    # CT-e
    if 'cte' in tag or NS_CTE in root.tag:
        return {"tipo": "cte", "modelo": "57", "namespace": ns}

    # NFS-e (vários padrões)
    if 'nfse' in tag or 'servico' in tag or 'abrasf' in tag.lower():
        return {"tipo": "nfse", "modelo": "nfse", "namespace": ns}

    # Tentar inferir pelo conteúdo
    xml_lower = xml_string[:2000].lower()
    if '<nfeproc' in xml_lower or '<infnfe' in xml_lower:
        return {"tipo": "nfe", "modelo": "55", "namespace": ns}
    if '<cteproc' in xml_lower or '<infcte' in xml_lower:
        return {"tipo": "cte", "modelo": "57", "namespace": ns}
    if '<compnfse' in xml_lower or '<infnfse' in xml_lower or '<nfse' in xml_lower:
        return {"tipo": "nfse", "modelo": "nfse", "namespace": ns}

    return {"tipo": "desconhecido", "modelo": None, "namespace": ns}


# ══════════════════════════════════════════════════════════════════════════════
# PARSER NF-e / NFC-e
# ══════════════════════════════════════════════════════════════════════════════

def parsear_nfe(xml_string: str) -> dict:
    """
    Extrai dados completos de uma NF-e ou NFC-e.

    Args:
        xml_string: XML da NF-e/NFC-e

    Returns:
        dict com dados extraídos, alertas, e metadados
    """
    alertas = []

    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        return {"sucesso": False, "erro": f"XML inválido: {e}", "alertas": []}

    # Encontrar o nó infNFe (pode estar em NFe/infNFe ou nfeProc/NFe/infNFe)
    inf = None
    for path in [
        f'.//{_ns("infNFe")}',
        './/infNFe',
        f'{_ns("NFe")}/{_ns("infNFe")}',
        f'.//{_ns("NFe")}/{_ns("infNFe")}',
    ]:
        inf = root.find(path)
        if inf is not None:
            break

    if inf is None:
        return {"sucesso": False, "erro": "Elemento infNFe não encontrado", "alertas": []}

    dados = {}
    ns = NS_NFE

    # ── Chave de acesso ──
    chave = inf.get('Id', '')
    if chave.startswith('NFe'):
        chave = chave[3:]
    if chave:
        dados["chave_acesso"] = chave

    # ── Identificação (ide) ──
    ide = inf.find(_ns('ide', ns)) or inf.find('ide')
    if ide is not None:
        dados["numero"] = _safe_int(_find_text(ide, 'nNF', ns))
        dados["serie"] = _safe_int(_find_text(ide, 'serie', ns))
        dados["modelo"] = _find_text(ide, 'mod', ns)
        dados["data_emissao"] = _parse_data_xml(_find_text(ide, 'dhEmi', ns))
        dados["data_saida"] = _parse_data_xml(_find_text(ide, 'dhSaiEnt', ns))
        dados["natureza_operacao"] = _find_text(ide, 'natOp', ns)
        dados["tipo_operacao"] = _find_text(ide, 'tpNF', ns)  # 0=entrada, 1=saída
        dados["finalidade"] = _find_text(ide, 'finNFe', ns)  # 1=normal, 2=complementar, 3=ajuste, 4=devolução
        dados["uf_emitente"] = _safe_int(_find_text(ide, 'cUF', ns))

    # ── Emitente ──
    emit = inf.find(_ns('emit', ns)) or inf.find('emit')
    if emit is not None:
        dados["emitente"] = {
            "cnpj": _find_text(emit, 'CNPJ', ns) or _find_text(emit, 'CPF', ns),
            "razao_social": _find_text(emit, 'xNome', ns),
            "nome_fantasia": _find_text(emit, 'xFant', ns),
            "ie": _find_text(emit, 'IE', ns),
            "crt": _find_text(emit, 'CRT', ns),  # 1=SN, 2=SN sublimite, 3=Normal
        }
        ender_emit = emit.find(_ns('enderEmit', ns)) or emit.find('enderEmit')
        if ender_emit is not None:
            dados["emitente"]["uf"] = _find_text(ender_emit, 'UF', ns)
            dados["emitente"]["municipio"] = _find_text(ender_emit, 'xMun', ns)
            dados["emitente"]["cod_municipio"] = _find_text(ender_emit, 'cMun', ns)

    # ── Destinatário ──
    dest = inf.find(_ns('dest', ns)) or inf.find('dest')
    if dest is not None:
        dados["destinatario"] = {
            "cnpj": _find_text(dest, 'CNPJ', ns) or _find_text(dest, 'CPF', ns),
            "razao_social": _find_text(dest, 'xNome', ns),
            "ie": _find_text(dest, 'IE', ns),
            "suframa": _find_text(dest, 'ISUF', ns),
        }
        ender_dest = dest.find(_ns('enderDest', ns)) or dest.find('enderDest')
        if ender_dest is not None:
            dados["destinatario"]["uf"] = _find_text(ender_dest, 'UF', ns)
            dados["destinatario"]["municipio"] = _find_text(ender_dest, 'xMun', ns)
            dados["destinatario"]["cod_municipio"] = _find_text(ender_dest, 'cMun', ns)

    # ── Produtos/Itens ──
    itens = []
    dets = inf.findall(_ns('det', ns)) or inf.findall('det')
    for det in dets:
        prod = det.find(_ns('prod', ns)) or det.find('prod')
        if prod is None:
            continue

        item = {
            "numero": det.get('nItem'),
            "codigo": _find_text(prod, 'cProd', ns),
            "descricao": _find_text(prod, 'xProd', ns),
            "ncm": _find_text(prod, 'NCM', ns),
            "cfop": _find_text(prod, 'CFOP', ns),
            "unidade": _find_text(prod, 'uCom', ns),
            "quantidade": _safe_float(_find_text(prod, 'qCom', ns)),
            "valor_unitario": _safe_float(_find_text(prod, 'vUnCom', ns)),
            "valor_total": _safe_float(_find_text(prod, 'vProd', ns)),
            "valor_desconto": _safe_float(_find_text(prod, 'vDesc', ns)),
            "ean": _find_text(prod, 'cEAN', ns),
        }

        # Impostos do item
        imposto = det.find(_ns('imposto', ns)) or det.find('imposto')
        if imposto is not None:
            item["impostos"] = _extrair_impostos_item(imposto, ns)

        itens.append(item)

    dados["itens"] = itens
    dados["total_itens"] = len(itens)

    # ── Totais ──
    total = inf.find(_ns('total', ns)) or inf.find('total')
    if total is not None:
        icms_tot = total.find(_ns('ICMSTot', ns)) or total.find('ICMSTot')
        if icms_tot is not None:
            dados["totais"] = {
                "valor_produtos": _safe_float(_find_text(icms_tot, 'vProd', ns)),
                "valor_frete": _safe_float(_find_text(icms_tot, 'vFrete', ns)),
                "valor_seguro": _safe_float(_find_text(icms_tot, 'vSeg', ns)),
                "valor_desconto": _safe_float(_find_text(icms_tot, 'vDesc', ns)),
                "valor_outros": _safe_float(_find_text(icms_tot, 'vOutro', ns)),
                "valor_nf": _safe_float(_find_text(icms_tot, 'vNF', ns)),
                "bc_icms": _safe_float(_find_text(icms_tot, 'vBC', ns)),
                "valor_icms": _safe_float(_find_text(icms_tot, 'vICMS', ns)),
                "bc_icms_st": _safe_float(_find_text(icms_tot, 'vBCST', ns)),
                "valor_icms_st": _safe_float(_find_text(icms_tot, 'vST', ns)),
                "valor_ipi": _safe_float(_find_text(icms_tot, 'vIPI', ns)),
                "valor_pis": _safe_float(_find_text(icms_tot, 'vPIS', ns)),
                "valor_cofins": _safe_float(_find_text(icms_tot, 'vCOFINS', ns)),
                "valor_icms_deson": _safe_float(_find_text(icms_tot, 'vICMSDeson', ns)),
                "valor_fcp": _safe_float(_find_text(icms_tot, 'vFCPUFDest', ns)),
                "valor_icms_uf_dest": _safe_float(_find_text(icms_tot, 'vICMSUFDest', ns)),
                "valor_icms_uf_remet": _safe_float(_find_text(icms_tot, 'vICMSUFRemet', ns)),
            }

    # ── Informações adicionais ──
    inf_adic = inf.find(_ns('infAdic', ns)) or inf.find('infAdic')
    if inf_adic is not None:
        dados["info_complementar"] = _find_text(inf_adic, 'infCpl', ns)
        dados["info_fisco"] = _find_text(inf_adic, 'infAdFisco', ns)

    # ── Validações ──
    _validar_nfe(dados, alertas)

    # ── Confiança ──
    campos_criticos = ["chave_acesso", "emitente", "totais", "data_emissao"]
    presentes = sum(1 for c in campos_criticos if dados.get(c))
    confianca = "alta" if presentes == len(campos_criticos) else ("media" if presentes >= 2 else "baixa")

    return {
        "sucesso": True,
        "tipo": "nfce" if dados.get("modelo") == "65" else "nfe",
        "confianca": confianca,
        "dados": dados,
        "alertas": alertas,
        "campos_extraidos": [k for k in dados.keys() if dados[k] is not None]
    }


def _extrair_impostos_item(imposto_elem, ns: str) -> dict:
    """Extrai impostos de um item da NF-e."""
    impostos = {}

    # ICMS
    icms_group = imposto_elem.find(_ns('ICMS', ns)) or imposto_elem.find('ICMS')
    if icms_group is not None:
        # O ICMS pode estar em ICMS00, ICMS10, ICMS20, etc.
        for child in icms_group:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            impostos["icms"] = {
                "grupo": tag,
                "orig": _find_text(child, 'orig', ns),
                "cst": _find_text(child, 'CST', ns),
                "csosn": _find_text(child, 'CSOSN', ns),
                "bc": _safe_float(_find_text(child, 'vBC', ns)),
                "aliquota": _safe_float(_find_text(child, 'pICMS', ns)),
                "valor": _safe_float(_find_text(child, 'vICMS', ns)),
                "bc_st": _safe_float(_find_text(child, 'vBCST', ns)),
                "aliq_st": _safe_float(_find_text(child, 'pICMSST', ns)),
                "valor_st": _safe_float(_find_text(child, 'vICMSST', ns)),
                "reducao_bc": _safe_float(_find_text(child, 'pRedBC', ns)),
            }
            break

    # PIS
    pis_group = imposto_elem.find(_ns('PIS', ns)) or imposto_elem.find('PIS')
    if pis_group is not None:
        for child in pis_group:
            impostos["pis"] = {
                "cst": _find_text(child, 'CST', ns),
                "bc": _safe_float(_find_text(child, 'vBC', ns)),
                "aliquota": _safe_float(_find_text(child, 'pPIS', ns)),
                "valor": _safe_float(_find_text(child, 'vPIS', ns)),
            }
            break

    # COFINS
    cofins_group = imposto_elem.find(_ns('COFINS', ns)) or imposto_elem.find('COFINS')
    if cofins_group is not None:
        for child in cofins_group:
            impostos["cofins"] = {
                "cst": _find_text(child, 'CST', ns),
                "bc": _safe_float(_find_text(child, 'vBC', ns)),
                "aliquota": _safe_float(_find_text(child, 'pCOFINS', ns)),
                "valor": _safe_float(_find_text(child, 'vCOFINS', ns)),
            }
            break

    # IPI
    ipi_group = imposto_elem.find(_ns('IPI', ns)) or imposto_elem.find('IPI')
    if ipi_group is not None:
        for child in ipi_group:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if 'Trib' in tag or 'NT' in tag:
                impostos["ipi"] = {
                    "cst": _find_text(child, 'CST', ns),
                    "bc": _safe_float(_find_text(child, 'vBC', ns)),
                    "aliquota": _safe_float(_find_text(child, 'pIPI', ns)),
                    "valor": _safe_float(_find_text(child, 'vIPI', ns)),
                }
                break

    return impostos


def _validar_nfe(dados: dict, alertas: list):
    """Validações de consistência nos dados extraídos da NF-e."""

    # Validar CFOP vs tipo de operação
    tipo_op = dados.get("tipo_operacao")
    for item in dados.get("itens", []):
        cfop = item.get("cfop")
        if cfop and tipo_op:
            primeiro = cfop[0] if cfop else ''
            if tipo_op == "1" and primeiro in ('1', '2', '3'):
                alertas.append(
                    f"Item {item.get('numero')}: CFOP {cfop} é de entrada, mas NF-e é de saída (tpNF=1)."
                )
            elif tipo_op == "0" and primeiro in ('5', '6', '7'):
                alertas.append(
                    f"Item {item.get('numero')}: CFOP {cfop} é de saída, mas NF-e é de entrada (tpNF=0)."
                )

    # Validar UF emitente vs destinatário vs CFOP
    emit_uf = dados.get("emitente", {}).get("uf")
    dest_uf = dados.get("destinatario", {}).get("uf")
    if emit_uf and dest_uf:
        interestadual = emit_uf != dest_uf
        for item in dados.get("itens", []):
            cfop = item.get("cfop", "")
            if cfop:
                primeiro = cfop[0]
                if interestadual and primeiro in ('1', '5'):
                    alertas.append(
                        f"Item {item.get('numero')}: CFOP {cfop} é interno, mas operação é interestadual "
                        f"({emit_uf} → {dest_uf}). Deveria ser {cfop.replace(primeiro, '2' if primeiro=='1' else '6', 1)}?"
                    )

    # Validar soma dos itens vs total NF
    totais = dados.get("totais", {})
    valor_nf = totais.get("valor_nf")
    if valor_nf is not None and dados.get("itens"):
        soma_itens = sum(
            (item.get("valor_total") or 0) - (item.get("valor_desconto") or 0)
            for item in dados["itens"]
        )
        frete = totais.get("valor_frete") or 0
        seguro = totais.get("valor_seguro") or 0
        outros = totais.get("valor_outros") or 0
        icms_st = totais.get("valor_icms_st") or 0
        ipi = totais.get("valor_ipi") or 0

        esperado = soma_itens + frete + seguro + outros + icms_st + ipi
        if abs(esperado - valor_nf) > 0.01:
            alertas.append(
                f"Soma itens+frete+seguro+outros+ST+IPI ({esperado:.2f}) difere do "
                f"valor da NF ({valor_nf:.2f}). Diferença: {abs(esperado - valor_nf):.2f}"
            )

    # Validar CRT (regime tributário)
    crt = dados.get("emitente", {}).get("crt")
    if crt:
        for item in dados.get("itens", []):
            icms = item.get("impostos", {}).get("icms", {})
            if crt in ("1", "2") and icms.get("cst"):
                alertas.append(
                    f"Item {item.get('numero')}: Emitente é Simples Nacional (CRT={crt}) "
                    f"mas usa CST ({icms['cst']}) em vez de CSOSN."
                )
            elif crt == "3" and icms.get("csosn"):
                alertas.append(
                    f"Item {item.get('numero')}: Emitente é Regime Normal (CRT=3) "
                    f"mas usa CSOSN ({icms['csosn']}) em vez de CST."
                )


# ══════════════════════════════════════════════════════════════════════════════
# PARSER NFS-e
# ══════════════════════════════════════════════════════════════════════════════

def parsear_nfse(xml_string: str) -> dict:
    """
    Extrai dados de uma NFS-e (padrão ABRASF ou variantes municipais).

    Args:
        xml_string: XML da NFS-e

    Returns:
        dict com dados extraídos
    """
    alertas = []

    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        return {"sucesso": False, "erro": f"XML inválido: {e}", "alertas": []}

    dados = {}

    # Tentar múltiplos caminhos (padrão ABRASF e variantes)
    # A estrutura varia muito entre municípios

    # Busca genérica por tags comuns
    all_text = xml_string

    # Número da NFS-e
    for tag in ['Numero', 'NumeroNfse', 'InfNfse']:
        el = _find_any(root, tag)
        if el is not None and el.text:
            dados["numero"] = el.text.strip()
            break

    # Data emissão
    for tag in ['DataEmissao', 'DataEmissaoNfse', 'dtEmissao']:
        el = _find_any(root, tag)
        if el is not None and el.text:
            dados["data_emissao"] = _parse_data_xml(el.text.strip())
            break

    # Código de verificação
    for tag in ['CodigoVerificacao', 'CodVerificacao']:
        el = _find_any(root, tag)
        if el is not None and el.text:
            dados["codigo_verificacao"] = el.text.strip()
            break

    # Prestador (emitente do serviço)
    prestador = {}
    for tag in ['Prestador', 'PrestadorServico', 'DadosPrestador']:
        el = _find_any(root, tag)
        if el is not None:
            cnpj_el = _find_any_multi(el, ['Cnpj', 'CpfCnpj'])
            if cnpj_el is not None:
                cnpj_inner = _find_any(cnpj_el, 'Cnpj')
                prestador["cnpj"] = (cnpj_inner.text if cnpj_inner is not None else cnpj_el.text or '').strip()
            razao = _find_any_multi(el, ['RazaoSocial', 'Nome'])
            if razao is not None and razao.text:
                prestador["razao_social"] = razao.text.strip()
            im = _find_any(el, 'InscricaoMunicipal')
            if im is not None and im.text:
                prestador["inscricao_municipal"] = im.text.strip()
            break
    if prestador:
        dados["prestador"] = prestador

    # Tomador (destinatário do serviço)
    tomador = {}
    for tag in ['Tomador', 'TomadorServico', 'DadosTomador']:
        el = _find_any(root, tag)
        if el is not None:
            cnpj_el = _find_any_multi(el, ['Cnpj', 'CpfCnpj'])
            if cnpj_el is not None:
                cnpj_inner = _find_any_multi(cnpj_el, ['Cnpj', 'Cpf'])
                tomador["cnpj_cpf"] = (cnpj_inner.text if cnpj_inner is not None else cnpj_el.text or '').strip()
            razao = _find_any_multi(el, ['RazaoSocial', 'Nome'])
            if razao is not None and razao.text:
                tomador["razao_social"] = razao.text.strip()
            break
    if tomador:
        dados["tomador"] = tomador

    # Serviço
    servico = {}
    for tag in ['Servico', 'InfServico', 'Servicos']:
        el = _find_any(root, tag)
        if el is not None:
            for campo, tags in {
                "valor_servicos": ['ValorServicos', 'Valor', 'vServicos'],
                "valor_deducoes": ['ValorDeducoes'],
                "valor_iss": ['ValorIss', 'vISS'],
                "aliquota_iss": ['Aliquota', 'AliquotaIss'],
                "base_calculo": ['BaseCalculo', 'vBC'],
                "codigo_servico": ['ItemListaServico', 'CodigoServico', 'CodigoCnae'],
                "discriminacao": ['Discriminacao', 'Descricao'],
                "municipio_prestacao": ['CodigoMunicipio', 'MunicipioPrestacao'],
                "iss_retido": ['IssRetido'],
                "valor_iss_retido": ['ValorIssRetido'],
            }.items():
                for t in tags:
                    val = _find_any(el, t)
                    if val is not None and val.text:
                        if 'valor' in campo or 'aliquota' in campo or 'base' in campo:
                            servico[campo] = _safe_float(val.text.strip())
                        else:
                            servico[campo] = val.text.strip()
                        break
            break
    if servico:
        dados["servico"] = servico

    # Validações NFS-e
    if servico.get("valor_servicos") and servico.get("aliquota_iss") and servico.get("valor_iss"):
        iss_esperado = round(servico["valor_servicos"] * servico["aliquota_iss"] / 100, 2)
        if servico["aliquota_iss"] > 1:  # alíquota em percentual
            iss_esperado = round(servico["valor_servicos"] * servico["aliquota_iss"] / 100, 2)
        else:  # alíquota em decimal
            iss_esperado = round(servico["valor_servicos"] * servico["aliquota_iss"], 2)
        if abs(iss_esperado - servico["valor_iss"]) > 0.01:
            alertas.append(
                f"ISS calculado ({iss_esperado:.2f}) difere do ISS informado ({servico['valor_iss']:.2f})."
            )

    # Retenções
    retencoes = {}
    for tag in ['ValorPis', 'ValorCofins', 'ValorInss', 'ValorIr', 'ValorCsll']:
        el = _find_any(root, tag)
        if el is not None and el.text:
            val = _safe_float(el.text.strip())
            if val and val > 0:
                nome = tag.replace('Valor', '').upper()
                retencoes[nome] = val
    if retencoes:
        dados["retencoes"] = retencoes

    # Determinar confiança
    campos_criticos = ["prestador", "servico", "data_emissao"]
    presentes = sum(1 for c in campos_criticos if dados.get(c))
    confianca = "alta" if presentes == len(campos_criticos) else ("media" if presentes >= 2 else "baixa")

    if confianca != "alta":
        alertas.append("NFS-e: formato municipal pode variar. Conferir dados manualmente.")

    return {
        "sucesso": True,
        "tipo": "nfse",
        "confianca": confianca,
        "dados": dados,
        "alertas": alertas,
        "campos_extraidos": [k for k in dados.keys() if dados[k] is not None]
    }


def _find_any(root, tag_name: str):
    """Busca tag por nome ignorando namespace.
    NOTA: Sempre usar 'is not None' para checar resultado (não 'or'),
    pois ElementTree elements sem filhos são falsy em Python < 3.12."""
    # Busca direta
    el = root.find(f'.//{tag_name}')
    if el is not None:
        return el
    # Busca com wildcard namespace
    for el in root.iter():
        local = el.tag.split('}')[-1] if '}' in el.tag else el.tag
        if local == tag_name:
            return el
    return None


def _find_any_multi(root, tag_names: list):
    """Busca a primeira tag encontrada de uma lista de nomes possíveis.
    Evita o bug de 'or' com ElementTree elements falsy."""
    for tag in tag_names:
        el = _find_any(root, tag)
        if el is not None:
            return el
    return None


# ══════════════════════════════════════════════════════════════════════════════
# PROCESSAMENTO EM LOTE
# ══════════════════════════════════════════════════════════════════════════════

def processar_xml(xml_string: str) -> dict:
    """
    Processa qualquer XML fiscal, detectando o tipo automaticamente.

    Args:
        xml_string: Conteúdo XML

    Returns:
        dict com resultado do parser apropriado
    """
    tipo_info = detectar_tipo_xml(xml_string)
    tipo = tipo_info["tipo"]

    if tipo in ("nfe", "nfce"):
        return parsear_nfe(xml_string)
    elif tipo == "nfse":
        return parsear_nfse(xml_string)
    elif tipo == "cte":
        # CT-e usa estrutura similar à NF-e
        return {"sucesso": False, "erro": "Parser CT-e ainda não implementado (v4.6)", "tipo": "cte", "alertas": []}
    else:
        return {"sucesso": False, "erro": f"Tipo de XML não reconhecido: {tipo}", "alertas": []}


def processar_lote_xml(xmls: list[str]) -> dict:
    """
    Processa múltiplos XMLs fiscais.

    Args:
        xmls: lista de strings XML

    Returns:
        dict com resultados consolidados para fechamento fiscal
    """
    resultados = []
    totais = {
        "entradas": {"quantidade": 0, "valor": 0.0, "icms": 0.0, "icms_st": 0.0, "ipi": 0.0, "pis": 0.0, "cofins": 0.0},
        "saidas": {"quantidade": 0, "valor": 0.0, "icms": 0.0, "icms_st": 0.0, "ipi": 0.0, "pis": 0.0, "cofins": 0.0},
        "servicos": {"quantidade": 0, "valor": 0.0, "iss": 0.0},
    }
    por_cfop = {}
    alertas_globais = []

    for i, xml in enumerate(xmls):
        resultado = processar_xml(xml)
        resultado["indice"] = i
        resultados.append(resultado)

        if not resultado.get("sucesso"):
            continue

        dados = resultado.get("dados", {})
        tipo = resultado.get("tipo", "")

        if tipo in ("nfe", "nfce"):
            tot = dados.get("totais", {})
            tipo_op = dados.get("tipo_operacao")
            categoria = "saidas" if tipo_op == "1" else "entradas"

            totais[categoria]["quantidade"] += 1
            totais[categoria]["valor"] += tot.get("valor_nf") or 0
            totais[categoria]["icms"] += tot.get("valor_icms") or 0
            totais[categoria]["icms_st"] += tot.get("valor_icms_st") or 0
            totais[categoria]["ipi"] += tot.get("valor_ipi") or 0
            totais[categoria]["pis"] += tot.get("valor_pis") or 0
            totais[categoria]["cofins"] += tot.get("valor_cofins") or 0

            # Agrupar por CFOP
            for item in dados.get("itens", []):
                cfop = item.get("cfop", "????")
                if cfop not in por_cfop:
                    por_cfop[cfop] = {"quantidade": 0, "valor": 0.0}
                por_cfop[cfop]["quantidade"] += 1
                por_cfop[cfop]["valor"] += item.get("valor_total") or 0

        elif tipo == "nfse":
            servico = dados.get("servico", {})
            totais["servicos"]["quantidade"] += 1
            totais["servicos"]["valor"] += servico.get("valor_servicos") or 0
            totais["servicos"]["iss"] += servico.get("valor_iss") or 0

    # Arredondar totais
    for cat in totais.values():
        for k in cat:
            if isinstance(cat[k], float):
                cat[k] = round(cat[k], 2)

    return {
        "total_xmls": len(xmls),
        "processados_com_sucesso": sum(1 for r in resultados if r.get("sucesso")),
        "totais": totais,
        "por_cfop": dict(sorted(por_cfop.items())),
        "resultados": resultados,
        "alertas_globais": alertas_globais
    }


def gerar_resumo_fiscal(resultado_lote: dict) -> str:
    """Gera resumo textual dos XMLs processados para fechamento fiscal."""
    linhas = []
    linhas.append("=" * 60)
    linhas.append("  RESUMO FISCAL — XMLs PROCESSADOS")
    linhas.append("=" * 60)

    t = resultado_lote["totais"]
    linhas.append(f"\nTotal de XMLs: {resultado_lote['total_xmls']}")
    linhas.append(f"Processados com sucesso: {resultado_lote['processados_com_sucesso']}")

    for cat, nome in [("saidas", "SAÍDAS"), ("entradas", "ENTRADAS"), ("servicos", "SERVIÇOS")]:
        dados = t[cat]
        if dados["quantidade"] > 0:
            linhas.append(f"\n{'─'*40}")
            linhas.append(f"  {nome} ({dados['quantidade']} notas)")
            linhas.append(f"  Valor: R$ {dados['valor']:,.2f}")
            if cat != "servicos":
                linhas.append(f"  ICMS: R$ {dados['icms']:,.2f}")
                if dados.get("icms_st", 0) > 0:
                    linhas.append(f"  ICMS-ST: R$ {dados['icms_st']:,.2f}")
                if dados.get("ipi", 0) > 0:
                    linhas.append(f"  IPI: R$ {dados['ipi']:,.2f}")
                linhas.append(f"  PIS: R$ {dados['pis']:,.2f}")
                linhas.append(f"  COFINS: R$ {dados['cofins']:,.2f}")
            else:
                linhas.append(f"  ISS: R$ {dados['iss']:,.2f}")

    cfop = resultado_lote.get("por_cfop", {})
    if cfop:
        linhas.append(f"\n{'─'*40}")
        linhas.append("  POR CFOP:")
        for codigo, vals in cfop.items():
            linhas.append(f"  {codigo}: {vals['quantidade']} itens | R$ {vals['valor']:,.2f}")

    return '\n'.join(linhas)


# ══════════════════════════════════════════════════════════════════════════════
# TESTES
# ══════════════════════════════════════════════════════════════════════════════

def _rodar_testes():
    """Testes unitários para parser_xml_nfe.py"""
    testes_passou = 0
    testes_falhou = 0

    def ok(condicao, descricao):
        nonlocal testes_passou, testes_falhou
        if condicao:
            testes_passou += 1
        else:
            testes_falhou += 1
            print(f"  FALHOU: {descricao}")

    # ── XML de teste NF-e ──
    XML_NFE = f'''<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="{NS_NFE}" versao="4.00">
<NFe xmlns="{NS_NFE}">
<infNFe Id="NFe35260612345678000199550010000001231234567890" versao="4.00">
  <ide>
    <cUF>35</cUF>
    <natOp>VENDA DE MERCADORIA</natOp>
    <mod>55</mod>
    <serie>1</serie>
    <nNF>123</nNF>
    <dhEmi>2026-03-15T10:30:00-03:00</dhEmi>
    <tpNF>1</tpNF>
    <finNFe>1</finNFe>
  </ide>
  <emit>
    <CNPJ>12345678000199</CNPJ>
    <xNome>EMPRESA TESTE LTDA</xNome>
    <xFant>TESTE</xFant>
    <IE>123456789</IE>
    <CRT>1</CRT>
    <enderEmit>
      <UF>SP</UF>
      <xMun>CAMPINAS</xMun>
      <cMun>3509502</cMun>
    </enderEmit>
  </emit>
  <dest>
    <CNPJ>98765432000110</CNPJ>
    <xNome>CLIENTE EXEMPLO SA</xNome>
    <IE>987654321</IE>
    <enderDest>
      <UF>SP</UF>
      <xMun>SAO PAULO</xMun>
      <cMun>3550308</cMun>
    </enderDest>
  </dest>
  <det nItem="1">
    <prod>
      <cProd>001</cProd>
      <xProd>PRODUTO TESTE A</xProd>
      <NCM>84719012</NCM>
      <CFOP>5102</CFOP>
      <uCom>UN</uCom>
      <qCom>10.0000</qCom>
      <vUnCom>100.00</vUnCom>
      <vProd>1000.00</vProd>
    </prod>
    <imposto>
      <ICMS>
        <ICMS00>
          <orig>0</orig>
          <CSOSN>102</CSOSN>
          <vBC>1000.00</vBC>
          <pICMS>18.00</pICMS>
          <vICMS>180.00</vICMS>
        </ICMS00>
      </ICMS>
      <PIS>
        <PISAliq>
          <CST>01</CST>
          <vBC>1000.00</vBC>
          <pPIS>1.65</pPIS>
          <vPIS>16.50</vPIS>
        </PISAliq>
      </PIS>
      <COFINS>
        <COFINSAliq>
          <CST>01</CST>
          <vBC>1000.00</vBC>
          <pCOFINS>7.60</pCOFINS>
          <vCOFINS>76.00</vCOFINS>
        </COFINSAliq>
      </COFINS>
    </imposto>
  </det>
  <det nItem="2">
    <prod>
      <cProd>002</cProd>
      <xProd>PRODUTO TESTE B</xProd>
      <NCM>84719012</NCM>
      <CFOP>5102</CFOP>
      <uCom>UN</uCom>
      <qCom>5.0000</qCom>
      <vUnCom>200.00</vUnCom>
      <vProd>1000.00</vProd>
    </prod>
    <imposto>
      <ICMS>
        <ICMS00>
          <orig>0</orig>
          <CST>00</CST>
          <vBC>1000.00</vBC>
          <pICMS>18.00</pICMS>
          <vICMS>180.00</vICMS>
        </ICMS00>
      </ICMS>
    </imposto>
  </det>
  <total>
    <ICMSTot>
      <vBC>2000.00</vBC>
      <vICMS>360.00</vICMS>
      <vBCST>0.00</vBCST>
      <vST>0.00</vST>
      <vProd>2000.00</vProd>
      <vFrete>50.00</vFrete>
      <vSeg>0.00</vSeg>
      <vDesc>0.00</vDesc>
      <vOutro>0.00</vOutro>
      <vIPI>0.00</vIPI>
      <vPIS>16.50</vPIS>
      <vCOFINS>76.00</vCOFINS>
      <vNF>2050.00</vNF>
    </ICMSTot>
  </total>
  <infAdic>
    <infCpl>Nota fiscal de teste</infCpl>
  </infAdic>
</infNFe>
</NFe>
</nfeProc>'''

    # ── Teste 1: Detectar tipo NF-e ──
    tipo = detectar_tipo_xml(XML_NFE)
    ok(tipo["tipo"] == "nfe", "Detectar: tipo NF-e")
    ok(tipo["modelo"] == "55", "Detectar: modelo 55")

    # ── Teste 2: Detectar XML vazio ──
    tipo_vazio = detectar_tipo_xml("")
    ok(tipo_vazio["tipo"] == "desconhecido", "Detectar: vazio")

    # ── Teste 3: Detectar XML inválido ──
    tipo_inv = detectar_tipo_xml("<not<valid>xml")
    ok(tipo_inv["tipo"] == "desconhecido", "Detectar: inválido")

    # ── Teste 4: Parsear NF-e completa ──
    r = parsear_nfe(XML_NFE)
    ok(r["sucesso"] == True, "NF-e: sucesso")
    ok(r["tipo"] == "nfe", "NF-e: tipo")
    ok(r["confianca"] == "alta", "NF-e: confiança alta")

    # ── Teste 5: Dados identificação ──
    d = r["dados"]
    ok(d["numero"] == 123, "NF-e: número")
    ok(d["serie"] == 1, "NF-e: série")
    ok(d["modelo"] == "55", "NF-e: modelo")
    ok(d["data_emissao"] == "2026-03-15", "NF-e: data emissão")
    ok(d["tipo_operacao"] == "1", "NF-e: tipo operação saída")
    ok(d["natureza_operacao"] == "VENDA DE MERCADORIA", "NF-e: natureza operação")

    # ── Teste 6: Chave de acesso ──
    ok(d["chave_acesso"] == "35260612345678000199550010000001231234567890", "NF-e: chave acesso")

    # ── Teste 7: Emitente ──
    ok(d["emitente"]["cnpj"] == "12345678000199", "NF-e: emitente CNPJ")
    ok(d["emitente"]["razao_social"] == "EMPRESA TESTE LTDA", "NF-e: emitente razão")
    ok(d["emitente"]["uf"] == "SP", "NF-e: emitente UF")
    ok(d["emitente"]["crt"] == "1", "NF-e: emitente CRT Simples Nacional")

    # ── Teste 8: Destinatário ──
    ok(d["destinatario"]["cnpj"] == "98765432000110", "NF-e: dest CNPJ")
    ok(d["destinatario"]["uf"] == "SP", "NF-e: dest UF")

    # ── Teste 9: Itens ──
    ok(d["total_itens"] == 2, "NF-e: 2 itens")
    ok(d["itens"][0]["descricao"] == "PRODUTO TESTE A", "NF-e: item 1 descrição")
    ok(d["itens"][0]["cfop"] == "5102", "NF-e: item 1 CFOP")
    ok(d["itens"][0]["quantidade"] == 10.0, "NF-e: item 1 qtd")
    ok(d["itens"][0]["valor_total"] == 1000.0, "NF-e: item 1 valor")
    ok(d["itens"][0]["ncm"] == "84719012", "NF-e: item 1 NCM")

    # ── Teste 10: Impostos do item ──
    imp = d["itens"][0]["impostos"]
    ok(imp["icms"]["aliquota"] == 18.0, "NF-e: item 1 ICMS alíq")
    ok(imp["icms"]["valor"] == 180.0, "NF-e: item 1 ICMS valor")
    ok(imp["pis"]["valor"] == 16.5, "NF-e: item 1 PIS valor")
    ok(imp["cofins"]["valor"] == 76.0, "NF-e: item 1 COFINS valor")

    # ── Teste 11: Totais ──
    ok(d["totais"]["valor_nf"] == 2050.0, "NF-e: valor NF")
    ok(d["totais"]["valor_produtos"] == 2000.0, "NF-e: valor produtos")
    ok(d["totais"]["valor_icms"] == 360.0, "NF-e: ICMS total")
    ok(d["totais"]["valor_frete"] == 50.0, "NF-e: frete")
    ok(d["totais"]["valor_pis"] == 16.5, "NF-e: PIS total")
    ok(d["totais"]["valor_cofins"] == 76.0, "NF-e: COFINS total")

    # ── Teste 12: Info adicional ──
    ok(d["info_complementar"] == "Nota fiscal de teste", "NF-e: info complementar")

    # ── Teste 13: Validação CRT vs CST/CSOSN ──
    # Item 1 tem CSOSN (correto para SN), Item 2 tem CST (incorreto para SN)
    ok(any("Simples Nacional" in a and "CST" in a for a in r["alertas"]), "NF-e: alerta CRT vs CST")

    # ── Teste 14: NFS-e básica ──
    XML_NFSE = '''<?xml version="1.0" encoding="UTF-8"?>
<CompNfse>
  <Nfse>
    <InfNfse>
      <Numero>12345</Numero>
      <DataEmissao>2026-03-10</DataEmissao>
      <CodigoVerificacao>ABC123</CodigoVerificacao>
      <PrestadorServico>
        <IdentificacaoPrestador>
          <CpfCnpj><Cnpj>12345678000199</Cnpj></CpfCnpj>
          <InscricaoMunicipal>12345</InscricaoMunicipal>
        </IdentificacaoPrestador>
        <RazaoSocial>EMPRESA SERVICOS LTDA</RazaoSocial>
      </PrestadorServico>
      <TomadorServico>
        <IdentificacaoTomador>
          <CpfCnpj><Cnpj>98765432000110</Cnpj></CpfCnpj>
        </IdentificacaoTomador>
        <RazaoSocial>CLIENTE TOMADOR SA</RazaoSocial>
      </TomadorServico>
      <Servico>
        <ValorServicos>5000.00</ValorServicos>
        <Aliquota>5.00</Aliquota>
        <ValorIss>250.00</ValorIss>
        <ItemListaServico>17.01</ItemListaServico>
        <Discriminacao>Servicos de contabilidade ref. 03/2026</Discriminacao>
        <CodigoMunicipio>3509502</CodigoMunicipio>
        <IssRetido>2</IssRetido>
      </Servico>
      <ValorPis>32.50</ValorPis>
      <ValorCofins>150.00</ValorCofins>
      <ValorInss>0.00</ValorInss>
      <ValorIr>75.00</ValorIr>
      <ValorCsll>50.00</ValorCsll>
    </InfNfse>
  </Nfse>
</CompNfse>'''

    tipo_nfse = detectar_tipo_xml(XML_NFSE)
    ok(tipo_nfse["tipo"] == "nfse", "Detectar: tipo NFS-e")

    r2 = parsear_nfse(XML_NFSE)
    ok(r2["sucesso"] == True, "NFS-e: sucesso")
    ok(r2["tipo"] == "nfse", "NFS-e: tipo")
    ok(r2["dados"]["numero"] == "12345", "NFS-e: número")
    ok(r2["dados"]["data_emissao"] == "2026-03-10", "NFS-e: data emissão")
    ok(r2["dados"]["prestador"]["cnpj"] == "12345678000199", "NFS-e: prestador CNPJ")
    ok(r2["dados"]["prestador"]["razao_social"] == "EMPRESA SERVICOS LTDA", "NFS-e: prestador razão")
    ok(r2["dados"]["tomador"]["cnpj_cpf"] == "98765432000110", "NFS-e: tomador CNPJ")
    ok(r2["dados"]["servico"]["valor_servicos"] == 5000.0, "NFS-e: valor serviços")
    ok(r2["dados"]["servico"]["aliquota_iss"] == 5.0, "NFS-e: alíquota ISS")
    ok(r2["dados"]["servico"]["valor_iss"] == 250.0, "NFS-e: valor ISS")
    ok(r2["dados"]["servico"]["codigo_servico"] == "17.01", "NFS-e: código serviço")
    ok(r2["dados"]["servico"]["discriminacao"] == "Servicos de contabilidade ref. 03/2026", "NFS-e: discriminação")

    # ── Teste 15: Retenções NFS-e ──
    ok("PIS" in r2["dados"]["retencoes"], "NFS-e: retenção PIS")
    ok(r2["dados"]["retencoes"]["PIS"] == 32.5, "NFS-e: PIS valor")
    ok(r2["dados"]["retencoes"]["COFINS"] == 150.0, "NFS-e: COFINS valor")
    ok(r2["dados"]["retencoes"]["IR"] == 75.0, "NFS-e: IR valor")
    ok(r2["dados"]["retencoes"]["CSLL"] == 50.0, "NFS-e: CSLL valor")
    ok("INSS" not in r2["dados"]["retencoes"], "NFS-e: INSS zero não incluso")

    # ── Teste 16: Processar XML automático ──
    r3 = processar_xml(XML_NFE)
    ok(r3["sucesso"] == True, "Auto: NF-e processada")
    ok(r3["tipo"] == "nfe", "Auto: tipo correto")

    r4 = processar_xml(XML_NFSE)
    ok(r4["sucesso"] == True, "Auto: NFS-e processada")
    ok(r4["tipo"] == "nfse", "Auto: tipo NFS-e")

    # ── Teste 17: XML inválido ──
    r5 = processar_xml("not xml at all")
    ok(r5["sucesso"] == False, "Inválido: falha")

    # ── Teste 18: Lote de XMLs ──
    lote = processar_lote_xml([XML_NFE, XML_NFSE])
    ok(lote["total_xmls"] == 2, "Lote: total")
    ok(lote["processados_com_sucesso"] == 2, "Lote: sucesso")
    ok(lote["totais"]["saidas"]["quantidade"] == 1, "Lote: 1 saída")
    ok(lote["totais"]["saidas"]["valor"] == 2050.0, "Lote: valor saídas")
    ok(lote["totais"]["servicos"]["quantidade"] == 1, "Lote: 1 serviço")
    ok(lote["totais"]["servicos"]["valor"] == 5000.0, "Lote: valor serviços")
    ok("5102" in lote["por_cfop"], "Lote: CFOP 5102 presente")

    # ── Teste 19: Resumo fiscal ──
    resumo = gerar_resumo_fiscal(lote)
    ok("SAÍDAS" in resumo, "Resumo: saídas presente")
    ok("SERVIÇOS" in resumo, "Resumo: serviços presente")
    ok("5102" in resumo, "Resumo: CFOP presente")

    # ── Teste 20: Lote vazio ──
    lote_vazio = processar_lote_xml([])
    ok(lote_vazio["total_xmls"] == 0, "Lote vazio: zero")

    # ── Teste 21: Helpers ──
    ok(_safe_float("123.45") == 123.45, "Helper: safe_float ok")
    ok(_safe_float("abc") is None, "Helper: safe_float inválido")
    ok(_safe_float(None) is None, "Helper: safe_float None")
    ok(_safe_int("42") == 42, "Helper: safe_int ok")
    ok(_safe_int("abc") is None, "Helper: safe_int inválido")
    ok(_parse_data_xml("2026-03-15T10:30:00-03:00") == "2026-03-15", "Helper: parse data com TZ")
    ok(_parse_data_xml("2026-03-15") == "2026-03-15", "Helper: parse data simples")
    ok(_parse_data_xml(None) is None, "Helper: parse data None")

    # ── Teste 22: NFC-e (modelo 65) ──
    XML_NFCE = f'''<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="{NS_NFE}" versao="4.00">
<NFe xmlns="{NS_NFE}">
<infNFe Id="NFe35260612345678000199650010000004561234567890" versao="4.00">
  <ide>
    <mod>65</mod>
    <serie>1</serie>
    <nNF>456</nNF>
    <dhEmi>2026-03-20T14:00:00-03:00</dhEmi>
    <tpNF>1</tpNF>
  </ide>
  <emit>
    <CNPJ>12345678000199</CNPJ>
    <xNome>LOJA TESTE</xNome>
    <CRT>1</CRT>
    <enderEmit><UF>SP</UF></enderEmit>
  </emit>
  <det nItem="1">
    <prod>
      <cProd>003</cProd>
      <xProd>PRODUTO VAREJO</xProd>
      <NCM>12345678</NCM>
      <CFOP>5102</CFOP>
      <uCom>UN</uCom>
      <qCom>1</qCom>
      <vUnCom>50.00</vUnCom>
      <vProd>50.00</vProd>
    </prod>
    <imposto>
      <ICMS><ICMS00><orig>0</orig><CSOSN>102</CSOSN></ICMS00></ICMS>
    </imposto>
  </det>
  <total>
    <ICMSTot>
      <vBC>0.00</vBC><vICMS>0.00</vICMS><vBCST>0.00</vBCST><vST>0.00</vST>
      <vProd>50.00</vProd><vFrete>0.00</vFrete><vSeg>0.00</vSeg>
      <vDesc>0.00</vDesc><vOutro>0.00</vOutro><vIPI>0.00</vIPI>
      <vPIS>0.00</vPIS><vCOFINS>0.00</vCOFINS><vNF>50.00</vNF>
    </ICMSTot>
  </total>
</infNFe>
</NFe>
</nfeProc>'''

    tipo_nfce = detectar_tipo_xml(XML_NFCE)
    ok(tipo_nfce["tipo"] == "nfce", "Detectar: tipo NFC-e modelo 65")

    r6 = parsear_nfe(XML_NFCE)
    ok(r6["sucesso"] == True, "NFC-e: sucesso")
    ok(r6["tipo"] == "nfce", "NFC-e: tipo correto")
    ok(r6["dados"]["numero"] == 456, "NFC-e: número")

    # ── Teste 23: Interestadual com CFOP interno ──
    XML_INTER = f'''<?xml version="1.0" encoding="UTF-8"?>
<NFe xmlns="{NS_NFE}">
<infNFe Id="NFe1" versao="4.00">
  <ide><mod>55</mod><tpNF>1</tpNF><dhEmi>2026-04-01</dhEmi></ide>
  <emit><CNPJ>11111111000111</CNPJ><xNome>SP LTDA</xNome><CRT>3</CRT><enderEmit><UF>SP</UF></enderEmit></emit>
  <dest><CNPJ>22222222000122</CNPJ><xNome>RJ LTDA</xNome><enderDest><UF>RJ</UF></enderDest></dest>
  <det nItem="1">
    <prod><cProd>X</cProd><xProd>TESTE</xProd><CFOP>5102</CFOP><vProd>100.00</vProd></prod>
    <imposto><ICMS><ICMS00><orig>0</orig><CST>00</CST></ICMS00></ICMS></imposto>
  </det>
  <total><ICMSTot><vProd>100.00</vProd><vNF>100.00</vNF><vBC>0</vBC><vICMS>0</vICMS><vBCST>0</vBCST><vST>0</vST><vFrete>0</vFrete><vSeg>0</vSeg><vDesc>0</vDesc><vOutro>0</vOutro><vIPI>0</vIPI><vPIS>0</vPIS><vCOFINS>0</vCOFINS></ICMSTot></total>
</infNFe>
</NFe>'''

    r7 = parsear_nfe(XML_INTER)
    ok(r7["sucesso"] == True, "Interestadual: sucesso")
    ok(any("interestadual" in a.lower() for a in r7["alertas"]), "Interestadual: alerta CFOP interno em op interestadual")

    # ── Teste 24: CT-e (ainda não implementado) ──
    XML_CTE = f'<cteProc xmlns="{NS_CTE}"><CTe><infCte></infCte></CTe></cteProc>'
    r8 = processar_xml(XML_CTE)
    ok(r8["sucesso"] == False, "CT-e: não implementado")
    ok("4.6" in r8.get("erro", ""), "CT-e: menciona versão futura")

    print(f"\n{'='*50}")
    print(f"parser_xml_nfe.py: {testes_passou} PASSOU, {testes_falhou} FALHOU de {testes_passou + testes_falhou}")
    print(f"{'='*50}")

    return testes_falhou == 0


if __name__ == "__main__":
    _rodar_testes()
