#!/usr/bin/env python3
"""
inteligencia_documental.py — Orquestrador de Inteligência Documental
RRT Group Contador v4.5

Recebe qualquer documento (PDF, XML, áudio transcrito, texto) e:
  1. Detecta automaticamente o tipo de documento
  2. Roteia para o parser especializado correto
  3. Consolida resultados em formato padronizado
  4. Gera resumo executivo e alertas

Parsers integrados:
  - parser_das_pdf.py → guias DAS (Simples Nacional / MEI)
  - parse_informe_rendimentos.py → informes de rendimentos PDF (v4.0)
  - parser_xml_nfe.py → NF-e, NFC-e, NFS-e, CT-e
  - ponte_transcriber.py → áudios transcritos

Módulo central da Fase 2 (v4.5) do plano de evolução.
"""

import re
from typing import Optional
from datetime import datetime


# ── Constantes de tipo ───────────────────────────────────────────────────────

TIPO_DAS_PDF = "das_pdf"
TIPO_INFORME_PDF = "informe_rendimentos_pdf"
TIPO_XML_NFE = "xml_nfe"
TIPO_XML_NFSE = "xml_nfse"
TIPO_XML_NFCE = "xml_nfce"
TIPO_XML_CTE = "xml_cte"
TIPO_AUDIO = "audio_transcricao"
TIPO_TEXTO = "texto_mensagem"
TIPO_DESCONHECIDO = "desconhecido"

# Extensões de áudio reconhecidas
EXTENSOES_AUDIO = {'.opus', '.ogg', '.mp3', '.wav', '.m4a', '.wma', '.aac'}


# ── Detecção de tipo ─────────────────────────────────────────────────────────

def detectar_tipo_documento(conteudo: str, nome_arquivo: Optional[str] = None,
                             eh_xml: bool = False, eh_pdf_texto: bool = False,
                             eh_audio: bool = False) -> dict:
    """
    Detecta o tipo de documento a partir do conteúdo e/ou metadados.

    Args:
        conteudo: Texto do documento (extraído de PDF, XML raw, transcrição, ou mensagem)
        nome_arquivo: Nome do arquivo original (se disponível)
        eh_xml: True se o conteúdo é XML
        eh_pdf_texto: True se o conteúdo é texto extraído de PDF
        eh_audio: True se é transcrição de áudio

    Returns:
        dict com tipo detectado, confiança e metadados
    """
    if not conteudo and not nome_arquivo:
        return {
            "tipo": TIPO_DESCONHECIDO,
            "confianca": 0.0,
            "erro": "Sem conteúdo ou nome de arquivo"
        }

    # ── Áudio ──
    if eh_audio:
        return {"tipo": TIPO_AUDIO, "confianca": 1.0, "parser": "ponte_transcriber"}

    if nome_arquivo:
        ext = '.' + nome_arquivo.rsplit('.', 1)[-1].lower() if '.' in nome_arquivo else ''
        if ext in EXTENSOES_AUDIO:
            return {"tipo": TIPO_AUDIO, "confianca": 1.0, "parser": "ponte_transcriber"}

    # ── XML ──
    if eh_xml or (conteudo and conteudo.strip().startswith('<?xml')) or (conteudo and conteudo.strip().startswith('<')):
        # Importar parser_xml_nfe para detectar subtipo
        try:
            from scripts.parser_xml_nfe import detectar_tipo_xml
            tipo_xml = detectar_tipo_xml(conteudo)
            tipo = tipo_xml["tipo"]

            mapa = {
                "nfe": (TIPO_XML_NFE, "parser_xml_nfe"),
                "nfce": (TIPO_XML_NFCE, "parser_xml_nfe"),
                "nfse": (TIPO_XML_NFSE, "parser_xml_nfe"),
                "cte": (TIPO_XML_CTE, "parser_xml_nfe"),
            }

            if tipo in mapa:
                return {
                    "tipo": mapa[tipo][0],
                    "confianca": 0.95,
                    "parser": mapa[tipo][1],
                    "subtipo_xml": tipo
                }
        except ImportError:
            pass

        # Fallback se parser não disponível
        conteudo_lower = (conteudo or "")[:2000].lower()
        if '<nfe' in conteudo_lower or '<infnfe' in conteudo_lower:
            return {"tipo": TIPO_XML_NFE, "confianca": 0.8, "parser": "parser_xml_nfe"}
        if '<nfse' in conteudo_lower or '<compnfse' in conteudo_lower:
            return {"tipo": TIPO_XML_NFSE, "confianca": 0.8, "parser": "parser_xml_nfe"}
        if '<cte' in conteudo_lower:
            return {"tipo": TIPO_XML_CTE, "confianca": 0.8, "parser": "parser_xml_nfe"}

    # ── PDF (texto extraído) ──
    if eh_pdf_texto or (nome_arquivo and nome_arquivo.lower().endswith('.pdf')):
        conteudo_check = (conteudo or "").lower()

        # Verificar se é guia DAS
        marcadores_das = [
            'pgdas', 'das-mei', 'simples nacional', 'documento de arrecadação',
            'período de apuração', 'dasn-simei', 'microempreendedor individual',
        ]
        score_das = sum(1 for m in marcadores_das if m in conteudo_check)

        # Verificar se é informe de rendimentos
        marcadores_informe = [
            'informe de rendimentos', 'comprovante de rendimentos',
            'rendimentos tributáveis', 'rendimentos isentos',
            'imposto de renda retido', 'fonte pagadora',
            'rendimentos sujeitos', 'comprovante anual',
        ]
        score_informe = sum(1 for m in marcadores_informe if m in conteudo_check)

        if score_das > score_informe and score_das >= 2:
            return {"tipo": TIPO_DAS_PDF, "confianca": min(0.5 + score_das * 0.15, 0.95), "parser": "parser_das_pdf"}
        elif score_informe > score_das and score_informe >= 2:
            return {"tipo": TIPO_INFORME_PDF, "confianca": min(0.5 + score_informe * 0.15, 0.95), "parser": "parse_informe_rendimentos"}
        elif score_das >= 1:
            return {"tipo": TIPO_DAS_PDF, "confianca": 0.5, "parser": "parser_das_pdf"}
        elif score_informe >= 1:
            return {"tipo": TIPO_INFORME_PDF, "confianca": 0.5, "parser": "parse_informe_rendimentos"}

    # ── Texto simples (mensagem) ──
    if conteudo and not eh_xml and not eh_pdf_texto:
        return {"tipo": TIPO_TEXTO, "confianca": 0.7, "parser": "classificar_mensagem"}

    return {"tipo": TIPO_DESCONHECIDO, "confianca": 0.1, "erro": "Tipo não reconhecido"}


# ── Processamento ────────────────────────────────────────────────────────────

def processar_documento(conteudo: str, nome_arquivo: Optional[str] = None,
                         eh_xml: bool = False, eh_pdf_texto: bool = False,
                         eh_audio: bool = False,
                         metadata: Optional[dict] = None) -> dict:
    """
    Processa qualquer documento roteando para o parser correto.

    Args:
        conteudo: Conteúdo do documento
        nome_arquivo: Nome do arquivo
        eh_xml: Se é XML
        eh_pdf_texto: Se é texto extraído de PDF
        eh_audio: Se é transcrição de áudio
        metadata: Metadados adicionais

    Returns:
        dict padronizado com resultado do parser
    """
    meta = metadata or {}
    timestamp_inicio = datetime.now()

    # Step 1: Detectar tipo
    deteccao = detectar_tipo_documento(conteudo, nome_arquivo, eh_xml, eh_pdf_texto, eh_audio)
    tipo = deteccao["tipo"]
    confianca_tipo = deteccao["confianca"]

    resultado = {
        "tipo_detectado": tipo,
        "confianca_deteccao": confianca_tipo,
        "parser_usado": deteccao.get("parser"),
        "nome_arquivo": nome_arquivo,
        "timestamp_processamento": timestamp_inicio.isoformat(),
        "metadata": meta,
    }

    if tipo == TIPO_DESCONHECIDO:
        resultado["sucesso"] = False
        resultado["erro"] = deteccao.get("erro", "Tipo de documento não reconhecido")
        resultado["alertas"] = ["Documento não reconhecido. Envie como PDF, XML ou áudio."]
        return resultado

    # Step 2: Rotear para parser
    try:
        if tipo == TIPO_DAS_PDF:
            from scripts.parser_das_pdf import extrair_dados_das
            parse_result = extrair_dados_das(conteudo)
            resultado["dados"] = parse_result.get("dados", {})
            resultado["sucesso"] = parse_result.get("sucesso", False)
            resultado["confianca_parse"] = parse_result.get("confianca", "baixa")
            resultado["alertas"] = parse_result.get("alertas", [])

        elif tipo == TIPO_INFORME_PDF:
            # parse_informe_rendimentos é do v4.0 — chamar se disponível
            try:
                from scripts.parse_informe_rendimentos import parsear_informe
                parse_result = parsear_informe(conteudo)
                resultado["dados"] = parse_result
                resultado["sucesso"] = True
                resultado["confianca_parse"] = parse_result.get("confianca", "media")
                resultado["alertas"] = parse_result.get("alertas", [])
            except ImportError:
                resultado["sucesso"] = False
                resultado["erro"] = "Parser de informes não disponível neste ambiente"
                resultado["alertas"] = ["Instale parse_informe_rendimentos.py para processar informes"]

        elif tipo in (TIPO_XML_NFE, TIPO_XML_NFCE):
            from scripts.parser_xml_nfe import parsear_nfe
            parse_result = parsear_nfe(conteudo)
            resultado["dados"] = parse_result.get("dados", {})
            resultado["sucesso"] = parse_result.get("sucesso", False)
            resultado["confianca_parse"] = parse_result.get("confianca", "baixa")
            resultado["alertas"] = parse_result.get("alertas", [])

        elif tipo == TIPO_XML_NFSE:
            from scripts.parser_xml_nfe import parsear_nfse
            parse_result = parsear_nfse(conteudo)
            resultado["dados"] = parse_result.get("dados", {})
            resultado["sucesso"] = parse_result.get("sucesso", False)
            resultado["confianca_parse"] = parse_result.get("confianca", "baixa")
            resultado["alertas"] = parse_result.get("alertas", [])

        elif tipo == TIPO_XML_CTE:
            resultado["sucesso"] = False
            resultado["erro"] = "Parser CT-e ainda não implementado (planejado para v4.6)"
            resultado["alertas"] = ["CT-e será suportado na próxima versão"]

        elif tipo == TIPO_AUDIO:
            from scripts.ponte_transcriber import preparar_para_pipeline
            parse_result = preparar_para_pipeline(conteudo, meta)
            resultado["dados"] = parse_result
            resultado["sucesso"] = parse_result.get("sucesso", False)
            resultado["confianca_parse"] = parse_result.get("analise", {}).get("confianca", 0)
            resultado["alertas"] = parse_result.get("alertas", [])

        elif tipo == TIPO_TEXTO:
            # Texto simples — preparar para classificação
            resultado["sucesso"] = True
            resultado["dados"] = {"texto": conteudo}
            resultado["confianca_parse"] = 0.9
            resultado["alertas"] = []

    except Exception as e:
        resultado["sucesso"] = False
        resultado["erro"] = f"Erro no parser: {str(e)}"
        resultado["alertas"] = [f"Falha ao processar: {str(e)}"]

    # Step 3: Calcular tempo
    duracao = (datetime.now() - timestamp_inicio).total_seconds()
    resultado["duracao_seg"] = round(duracao, 3)

    return resultado


def processar_lote_documentos(documentos: list[dict]) -> dict:
    """
    Processa múltiplos documentos heterogêneos.

    Args:
        documentos: lista de dicts com campos:
            - conteudo: str
            - nome_arquivo: str (opcional)
            - eh_xml, eh_pdf_texto, eh_audio: bool (opcional)
            - metadata: dict (opcional)

    Returns:
        dict consolidado com resultados por tipo e contagens
    """
    resultados = []
    por_tipo = {}
    alertas_globais = []

    for i, doc in enumerate(documentos):
        resultado = processar_documento(
            conteudo=doc.get("conteudo", ""),
            nome_arquivo=doc.get("nome_arquivo"),
            eh_xml=doc.get("eh_xml", False),
            eh_pdf_texto=doc.get("eh_pdf_texto", False),
            eh_audio=doc.get("eh_audio", False),
            metadata=doc.get("metadata", {}),
        )
        resultado["indice"] = i
        resultados.append(resultado)

        tipo = resultado["tipo_detectado"]
        if tipo not in por_tipo:
            por_tipo[tipo] = {"quantidade": 0, "sucesso": 0, "falha": 0}
        por_tipo[tipo]["quantidade"] += 1
        if resultado.get("sucesso"):
            por_tipo[tipo]["sucesso"] += 1
        else:
            por_tipo[tipo]["falha"] += 1

    total = len(documentos)
    sucesso = sum(1 for r in resultados if r.get("sucesso"))

    return {
        "total_documentos": total,
        "processados_com_sucesso": sucesso,
        "falhas": total - sucesso,
        "por_tipo": por_tipo,
        "resultados": resultados,
        "alertas_globais": alertas_globais,
    }


def gerar_resumo_lote(resultado_lote: dict) -> str:
    """Gera resumo textual do processamento em lote."""
    linhas = []
    linhas.append("=" * 60)
    linhas.append("  INTELIGÊNCIA DOCUMENTAL — RESUMO DO LOTE")
    linhas.append("=" * 60)
    linhas.append(f"\nTotal: {resultado_lote['total_documentos']} documentos")
    linhas.append(f"Sucesso: {resultado_lote['processados_com_sucesso']}")
    linhas.append(f"Falhas: {resultado_lote['falhas']}")

    for tipo, stats in sorted(resultado_lote["por_tipo"].items()):
        linhas.append(f"\n  {tipo}: {stats['quantidade']} ({stats['sucesso']} ok, {stats['falha']} falha)")

    alertas = []
    for r in resultado_lote["resultados"]:
        for a in r.get("alertas", []):
            label = r.get('nome_arquivo') or f"doc#{r.get('indice', '?')}"
            alertas.append(f"  [{label}] {a}")

    if alertas:
        linhas.append(f"\n{'!'*60}")
        linhas.append("ALERTAS:")
        for a in alertas[:20]:  # Limitar a 20 alertas
            linhas.append(a)
        if len(alertas) > 20:
            linhas.append(f"  ... e mais {len(alertas) - 20} alertas")

    return '\n'.join(linhas)


# ══════════════════════════════════════════════════════════════════════════════
# TESTES
# ══════════════════════════════════════════════════════════════════════════════

# XMLs de teste (inline para independência)
_XML_NFE_TEST = '''<?xml version="1.0"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
<infNFe Id="NFe35260612345678000199550010000001231234567890" versao="4.00">
  <ide><mod>55</mod><serie>1</serie><nNF>123</nNF><dhEmi>2026-03-15</dhEmi><tpNF>1</tpNF></ide>
  <emit><CNPJ>12345678000199</CNPJ><xNome>TESTE</xNome><CRT>3</CRT><enderEmit><UF>SP</UF></enderEmit></emit>
  <dest><CNPJ>98765432000110</CNPJ><xNome>DEST</xNome><enderDest><UF>SP</UF></enderDest></dest>
  <det nItem="1">
    <prod><cProd>1</cProd><xProd>PROD</xProd><CFOP>5102</CFOP><vProd>100.00</vProd></prod>
    <imposto><ICMS><ICMS00><orig>0</orig><CST>00</CST></ICMS00></ICMS></imposto>
  </det>
  <total><ICMSTot><vBC>100</vBC><vICMS>18</vICMS><vBCST>0</vBCST><vST>0</vST><vProd>100</vProd>
  <vFrete>0</vFrete><vSeg>0</vSeg><vDesc>0</vDesc><vOutro>0</vOutro><vIPI>0</vIPI>
  <vPIS>0</vPIS><vCOFINS>0</vCOFINS><vNF>100</vNF></ICMSTot></total>
</infNFe></NFe></nfeProc>'''

_TEXTO_DAS_TEST = """
PGDAS-D - Programa Gerador do DAS
Simples Nacional
CNPJ: 12.345.678/0001-99
Período de Apuração: 03/2026
Vencimento: 20/04/2026
Valor Total: R$ 1.500,00
"""


def _rodar_testes():
    """Testes unitários para inteligencia_documental.py"""
    testes_passou = 0
    testes_falhou = 0

    def ok(condicao, descricao):
        nonlocal testes_passou, testes_falhou
        if condicao:
            testes_passou += 1
        else:
            testes_falhou += 1
            print(f"  FALHOU: {descricao}")

    # ── Teste 1: Detectar XML NF-e ──
    d = detectar_tipo_documento(_XML_NFE_TEST, "nota.xml", eh_xml=True)
    ok(d["tipo"] == TIPO_XML_NFE, "Detectar: XML NF-e")
    ok(d["confianca"] >= 0.8, "Detectar: alta confiança XML")

    # ── Teste 2: Detectar DAS PDF ──
    d2 = detectar_tipo_documento(_TEXTO_DAS_TEST, "guia.pdf", eh_pdf_texto=True)
    ok(d2["tipo"] == TIPO_DAS_PDF, "Detectar: DAS PDF")
    ok(d2["confianca"] >= 0.6, "Detectar: confiança DAS")

    # ── Teste 3: Detectar informe de rendimentos ──
    texto_informe = """
    COMPROVANTE DE RENDIMENTOS PAGOS E DE IMPOSTO DE RENDA RETIDO NA FONTE
    Rendimentos Tributáveis: R$ 120.000,00
    Imposto de Renda Retido na Fonte: R$ 15.000,00
    Rendimentos Isentos e Não Tributáveis: R$ 5.000,00
    """
    d3 = detectar_tipo_documento(texto_informe, "informe.pdf", eh_pdf_texto=True)
    ok(d3["tipo"] == TIPO_INFORME_PDF, "Detectar: Informe Rendimentos")

    # ── Teste 4: Detectar áudio ──
    d4 = detectar_tipo_documento("transcrição aqui", "audio.opus", eh_audio=True)
    ok(d4["tipo"] == TIPO_AUDIO, "Detectar: áudio por flag")

    d5 = detectar_tipo_documento("", "mensagem.ogg")
    ok(d5["tipo"] == TIPO_AUDIO, "Detectar: áudio por extensão")

    d6 = detectar_tipo_documento("", "voice.mp3")
    ok(d6["tipo"] == TIPO_AUDIO, "Detectar: mp3")

    # ── Teste 5: Detectar texto simples ──
    d7 = detectar_tipo_documento("Quanto pago de imposto?")
    ok(d7["tipo"] == TIPO_TEXTO, "Detectar: texto simples")

    # ── Teste 6: Vazio ──
    d8 = detectar_tipo_documento("", None)
    ok(d8["tipo"] == TIPO_DESCONHECIDO, "Detectar: vazio")

    # ── Teste 7: Processar NF-e XML ──
    r = processar_documento(_XML_NFE_TEST, "nota.xml", eh_xml=True)
    ok(r["sucesso"] == True, "Processar: NF-e sucesso")
    ok(r["tipo_detectado"] == TIPO_XML_NFE, "Processar: tipo NF-e")
    ok(r["parser_usado"] == "parser_xml_nfe", "Processar: parser correto")
    ok("dados" in r, "Processar: dados presentes")
    ok(r["dados"].get("numero") == 123, "Processar: número NF-e correto")

    # ── Teste 8: Processar DAS PDF ──
    r2 = processar_documento(_TEXTO_DAS_TEST, "guia.pdf", eh_pdf_texto=True)
    ok(r2["sucesso"] == True, "Processar: DAS sucesso")
    ok(r2["tipo_detectado"] == TIPO_DAS_PDF, "Processar: tipo DAS")
    ok(r2["dados"].get("valor_total") == 1500.0, "Processar: valor DAS")

    # ── Teste 9: Processar áudio ──
    r3 = processar_documento(
        "éh quanto que eu pago de ICMS?",
        "audio.opus", eh_audio=True,
        metadata={"remetente": "Cliente"}
    )
    ok(r3["sucesso"] == True, "Processar: áudio sucesso")
    ok(r3["tipo_detectado"] == TIPO_AUDIO, "Processar: tipo áudio")

    # ── Teste 10: Processar texto ──
    r4 = processar_documento("Quanto custa o DAS do MEI?")
    ok(r4["sucesso"] == True, "Processar: texto sucesso")
    ok(r4["tipo_detectado"] == TIPO_TEXTO, "Processar: tipo texto")

    # ── Teste 11: Processar desconhecido ──
    r5 = processar_documento("", None)
    ok(r5["sucesso"] == False, "Processar: desconhecido falha")
    ok(r5["tipo_detectado"] == TIPO_DESCONHECIDO, "Processar: tipo desconhecido")

    # ── Teste 12: CT-e (não implementado) ──
    r6 = processar_documento('<cteProc xmlns="http://www.portalfiscal.inf.br/cte"><CTe><infCte></infCte></CTe></cteProc>', "cte.xml", eh_xml=True)
    ok(r6["sucesso"] == False, "Processar: CT-e não implementado")
    ok("4.6" in r6.get("erro", ""), "Processar: CT-e menciona v4.6")

    # ── Teste 13: Tempo de processamento ──
    ok("duracao_seg" in r, "Processar: duracao_seg presente")
    ok(isinstance(r["duracao_seg"], float), "Processar: duracao_seg é float")

    # ── Teste 14: Lote de documentos ──
    lote = processar_lote_documentos([
        {"conteudo": _XML_NFE_TEST, "nome_arquivo": "nfe1.xml", "eh_xml": True},
        {"conteudo": _TEXTO_DAS_TEST, "nome_arquivo": "das.pdf", "eh_pdf_texto": True},
        {"conteudo": "Quanto pago de ISS?", "nome_arquivo": None},
        {"conteudo": "transcrição do áudio", "nome_arquivo": "audio.opus", "eh_audio": True},
    ])
    ok(lote["total_documentos"] == 4, "Lote: total 4")
    ok(lote["processados_com_sucesso"] == 4, "Lote: 4 sucesso")
    ok(TIPO_XML_NFE in lote["por_tipo"], "Lote: tem NF-e")
    ok(TIPO_DAS_PDF in lote["por_tipo"], "Lote: tem DAS")
    ok(TIPO_AUDIO in lote["por_tipo"], "Lote: tem áudio")
    ok(TIPO_TEXTO in lote["por_tipo"], "Lote: tem texto")

    # ── Teste 15: Resumo do lote ──
    resumo = gerar_resumo_lote(lote)
    ok("INTELIGÊNCIA DOCUMENTAL" in resumo, "Resumo: título")
    ok("4" in resumo, "Resumo: total presente")

    # ── Teste 16: Lote vazio ──
    lote_vazio = processar_lote_documentos([])
    ok(lote_vazio["total_documentos"] == 0, "Lote vazio: zero")

    # ── Teste 17: NFS-e via auto-detect ──
    XML_NFSE = '''<?xml version="1.0"?>
<CompNfse><Nfse><InfNfse>
  <Numero>999</Numero>
  <DataEmissao>2026-04-01</DataEmissao>
  <PrestadorServico>
    <IdentificacaoPrestador><CpfCnpj><Cnpj>11111111000111</Cnpj></CpfCnpj></IdentificacaoPrestador>
    <RazaoSocial>SERVICO LTDA</RazaoSocial>
  </PrestadorServico>
  <Servico>
    <ValorServicos>1000.00</ValorServicos>
    <Aliquota>5.00</Aliquota>
    <ValorIss>50.00</ValorIss>
    <Discriminacao>Servico teste</Discriminacao>
  </Servico>
</InfNfse></Nfse></CompNfse>'''
    r7 = processar_documento(XML_NFSE, "nfse.xml", eh_xml=True)
    ok(r7["sucesso"] == True, "NFS-e auto: sucesso")
    ok(r7["tipo_detectado"] == TIPO_XML_NFSE, "NFS-e auto: tipo correto")

    # ── Teste 18: PDF sem marcadores (ambíguo) ──
    d9 = detectar_tipo_documento("Este é um PDF qualquer sem marcadores fiscais", "doc.pdf", eh_pdf_texto=True)
    ok(d9["tipo"] == TIPO_DESCONHECIDO, "Detectar: PDF ambíguo = desconhecido")

    # ── Teste 19: Metadata preservada ──
    r8 = processar_documento("teste", metadata={"cliente": "João"})
    ok(r8["metadata"]["cliente"] == "João", "Metadata: preservada")

    # ── Teste 20: XML auto-detect (sem flag eh_xml) ──
    d10 = detectar_tipo_documento('<?xml version="1.0"?><nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe></NFe></nfeProc>')
    ok(d10["tipo"] in (TIPO_XML_NFE, TIPO_XML_NFCE), "Auto XML: detecta NF-e sem flag")

    print(f"\n{'='*50}")
    print(f"inteligencia_documental.py: {testes_passou} PASSOU, {testes_falhou} FALHOU de {testes_passou + testes_falhou}")
    print(f"{'='*50}")

    return testes_falhou == 0


if __name__ == "__main__":
    import sys, os
    # Ensure parent directory is in path for 'from scripts.X import Y'
    parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent not in sys.path:
        sys.path.insert(0, parent)
    _rodar_testes()
