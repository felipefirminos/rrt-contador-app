#!/usr/bin/env python3
"""
ponte_transcriber.py — Bridge entre rrt-transcriber (áudio→texto) e o pipeline contábil
RRT Group Contador v4.5 — Inteligência Documental

Recebe transcrições de áudio (do WhatsApp ou outras fontes) e:
  1. Limpa e normaliza o texto transcrito
  2. Detecta se contém perguntas contábeis/fiscais
  3. Extrai dados numéricos relevantes (valores, datas, CNPJs, CPFs)
  4. Classifica o assunto via classificar_mensagem.py
  5. Prepara payload para o pipeline de resposta

Integra com:
  - rrt-transcriber (skill de transcrição Whisper)
  - classificar_mensagem.py (NLP de classificação)
  - rascunho_resposta.py (geração de rascunho)
  - orquestrador_gestta.py (se veio do Gestta)
"""

import re
from datetime import datetime
from typing import Optional


# ── Padrões de extração ──────────────────────────────────────────────────────

RE_CNPJ = re.compile(r'\d{2}[\.\s]?\d{3}[\.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2}')
RE_CPF = re.compile(r'\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[-\s]?\d{2}')
RE_VALOR = re.compile(
    r'(?:R\$?\s*)?(\d{1,3}(?:[.\s]\d{3})*[,]\d{2})'  # R$ 1.234,56
    r'|'
    r'(\d+(?:[,.]\d+)?)\s*(?:mil|reais|conto)',  # 5 mil, 300 reais
    re.IGNORECASE
)
RE_DATA = re.compile(
    r'\b(\d{1,2})\s*(?:de\s+)?(janeiro|fevereiro|mar[çc]o|abril|maio|junho|'
    r'julho|agosto|setembro|outubro|novembro|dezembro)\b'
    r'|'
    r'\b(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?\b',
    re.IGNORECASE
)
RE_PERCENTUAL = re.compile(r'(\d{1,3}[,.]?\d{0,2})\s*(?:por\s+cento|porcento|%)', re.IGNORECASE)

# Termos fiscais/contábeis para detecção
TERMOS_CONTABEIS = {
    "imposto", "tributo", "fiscal", "nota fiscal", "nf", "nfe",
    "icms", "iss", "irpj", "csll", "pis", "cofins", "inss", "fgts",
    "das", "simples", "mei", "lucro presumido", "lucro real",
    "rescisão", "férias", "décimo", "13", "folha", "holerite",
    "guia", "darf", "gps", "parcelamento", "multa",
    "declaração", "irpf", "imposto de renda", "carnê-leão",
    "pró-labore", "prolabore", "distribuição de lucros",
    "alíquota", "faturamento", "receita", "despesa",
    "esocial", "sped", "dctf", "efd",
    "balanço", "balancete", "dre", "contabilidade",
    "certidão", "cnd", "regularidade",
    "admissão", "demissão", "aviso prévio", "seguro desemprego",
    "cbs", "ibs", "reforma tributária",
}

# Marcadores de pergunta em fala transcrita
MARCADORES_PERGUNTA = [
    "quanto", "qual", "como", "quando", "pode", "posso", "preciso",
    "tem como", "dá pra", "é possível", "será que", "o que",
    "por que", "pra que", "né", "certo", "correto",
]

# Meses por extenso
MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}


def limpar_transcricao(texto_bruto: str) -> str:
    """
    Limpa e normaliza texto transcrito de áudio.

    Trata problemas comuns de transcrição automática:
    - Repetições de palavras (gagueira/eco)
    - Marcadores de hesitação (ãh, éh, tipo assim)
    - Espaçamento inconsistente
    - Pontuação ausente ou incorreta

    Args:
        texto_bruto: Texto raw do Whisper/transcritor

    Returns:
        Texto limpo e normalizado
    """
    if not texto_bruto:
        return ""

    texto = texto_bruto.strip()

    # Remover marcadores de hesitação comuns
    hesitacoes = [
        r'\b[aá]h+\b', r'\b[eé]h+\b', r'\buh+\b', r'\bhm+\b',
        r'\btipo assim\b', r'\bsabe\b(?=[\s,])', r'\bentendeu\b(?=[\s,?])',
        r'\bné\b(?=[\s,])', r'\bé\.\.\.\b', r'\bai\b(?=[\s,])',
        r'\btá\b(?=[\s,](?!bom|ok|certo))',
    ]
    for pattern in hesitacoes:
        texto = re.sub(pattern, '', texto, flags=re.IGNORECASE)

    # Remover repetições de palavras (ex: "o o imposto" → "o imposto")
    texto = re.sub(r'\b(\w+)\s+\1\b', r'\1', texto, flags=re.IGNORECASE)

    # Normalizar espaçamento
    texto = re.sub(r'\s{2,}', ' ', texto)
    texto = re.sub(r'\s+([,.])', r'\1', texto)

    # Capitalizar primeira letra
    texto = texto.strip()
    if texto:
        texto = texto[0].upper() + texto[1:]

    return texto


def extrair_dados_transcritos(texto: str) -> dict:
    """
    Extrai dados estruturados de texto transcrito.

    Args:
        texto: Texto limpo da transcrição

    Returns:
        dict com CNPJs, CPFs, valores, datas, percentuais encontrados
    """
    dados = {}

    # CNPJs
    cnpjs = RE_CNPJ.findall(texto)
    if cnpjs:
        dados["cnpjs"] = [re.sub(r'[\s]', '', c) for c in cnpjs]

    # CPFs
    cpfs = RE_CPF.findall(texto)
    if cpfs:
        # Filtrar CNPJs que foram pegos como CPF (mais de 11 dígitos)
        cpfs_limpos = []
        for cpf in cpfs:
            digitos = re.sub(r'\D', '', cpf)
            if len(digitos) == 11:
                cpfs_limpos.append(cpf)
        if cpfs_limpos:
            dados["cpfs"] = cpfs_limpos

    # Valores monetários
    valores = []
    for m in RE_VALOR.finditer(texto):
        if m.group(1):  # R$ format
            val_str = m.group(1).replace('.', '').replace(',', '.')
            try:
                valores.append(float(val_str))
            except ValueError:
                pass
        elif m.group(2):  # "X mil" format
            val_str = m.group(2).replace(',', '.')
            try:
                val = float(val_str)
                contexto = texto[max(0, m.start()-5):m.end()+10].lower()
                if 'mil' in contexto:
                    val *= 1000
                valores.append(val)
            except ValueError:
                pass
    if valores:
        dados["valores"] = valores

    # Datas
    datas = []
    for m in RE_DATA.finditer(texto):
        if m.group(1) and m.group(2):  # "15 de março" format
            dia = int(m.group(1))
            mes = MESES.get(m.group(2).lower(), 0)
            if 1 <= dia <= 31 and mes > 0:
                datas.append(f"{dia:02d}/{mes:02d}")
        elif m.group(3) and m.group(4):  # DD/MM or DD/MM/YYYY
            datas.append(f"{m.group(3)}/{m.group(4)}" + (f"/{m.group(5)}" if m.group(5) else ""))
    if datas:
        dados["datas"] = datas

    # Percentuais
    percentuais = []
    for m in RE_PERCENTUAL.finditer(texto):
        val_str = m.group(1).replace(',', '.')
        try:
            percentuais.append(float(val_str))
        except ValueError:
            pass
    if percentuais:
        dados["percentuais"] = percentuais

    return dados


def detectar_pergunta_contabil(texto: str) -> dict:
    """
    Analisa se o texto transcrito contém uma pergunta contábil/fiscal.

    Args:
        texto: Texto limpo da transcrição

    Returns:
        dict com:
          - eh_pergunta: bool
          - eh_contabil: bool
          - confianca: float (0-1)
          - termos_encontrados: list
          - marcadores_pergunta: list
    """
    texto_lower = texto.lower()

    # Detectar termos contábeis
    termos_encontrados = []
    for termo in TERMOS_CONTABEIS:
        if termo in texto_lower:
            termos_encontrados.append(termo)

    # Detectar marcadores de pergunta
    marcadores = []
    for marcador in MARCADORES_PERGUNTA:
        if marcador in texto_lower:
            marcadores.append(marcador)

    # Verificar se termina com "?" ou tem entonação de pergunta
    tem_interrogacao = "?" in texto
    tem_marcador = len(marcadores) > 0

    eh_pergunta = tem_interrogacao or tem_marcador
    eh_contabil = len(termos_encontrados) > 0

    # Calcular confiança
    if eh_pergunta and eh_contabil:
        confianca = min(0.5 + len(termos_encontrados) * 0.15 + len(marcadores) * 0.1, 1.0)
    elif eh_contabil:
        confianca = min(0.3 + len(termos_encontrados) * 0.1, 0.7)
    elif eh_pergunta:
        confianca = 0.2
    else:
        confianca = 0.1

    return {
        "eh_pergunta": eh_pergunta,
        "eh_contabil": eh_contabil,
        "confianca": round(confianca, 2),
        "termos_encontrados": termos_encontrados,
        "marcadores_pergunta": marcadores,
    }


def preparar_para_pipeline(texto_transcrito: str, metadata: Optional[dict] = None) -> dict:
    """
    Prepara transcrição completa para entrar no pipeline contábil.

    Pipeline: áudio → transcrição → limpar → extrair → detectar → classificar → responder

    Args:
        texto_transcrito: Texto bruto da transcrição (output do Whisper)
        metadata: Metadados opcionais (remetente, grupo, timestamp, duracao_audio)

    Returns:
        dict pronto para injetar em classificar_mensagem / orquestrador_gestta
    """
    meta = metadata or {}

    # Step 1: Limpar
    texto_limpo = limpar_transcricao(texto_transcrito)

    if not texto_limpo:
        return {
            "sucesso": False,
            "erro": "Transcrição vazia após limpeza",
            "texto_original": texto_transcrito,
        }

    # Step 2: Extrair dados
    dados_extraidos = extrair_dados_transcritos(texto_limpo)

    # Step 3: Detectar pergunta contábil
    analise = detectar_pergunta_contabil(texto_limpo)

    # Step 4: Montar payload para o pipeline
    resultado = {
        "sucesso": True,
        "origem": "audio_transcrito",
        "texto_original": texto_transcrito,
        "texto_limpo": texto_limpo,
        "dados_extraidos": dados_extraidos,
        "analise": analise,
        "remetente": meta.get("remetente"),
        "grupo": meta.get("grupo"),
        "timestamp": meta.get("timestamp") or datetime.now().isoformat(),
        "duracao_audio_seg": meta.get("duracao_audio"),
    }

    # Se é pergunta contábil, preparar para classificar_mensagem
    if analise["eh_pergunta"] and analise["eh_contabil"]:
        resultado["pronto_para_classificacao"] = True
        resultado["payload_classificacao"] = {
            "texto": texto_limpo,
            "origem": "audio",
            "remetente": meta.get("remetente"),
            "dados_auxiliares": dados_extraidos,
        }
    else:
        resultado["pronto_para_classificacao"] = False
        if not analise["eh_contabil"]:
            resultado["motivo_skip"] = "Não identificado como assunto contábil/fiscal"
        elif not analise["eh_pergunta"]:
            resultado["motivo_skip"] = "Não identificado como pergunta (pode ser informativo)"

    # Alertas
    alertas = []
    if meta.get("duracao_audio") and meta["duracao_audio"] > 120:
        alertas.append("Áudio longo (>2min). Transcrição pode ter imprecisões.")
    if len(texto_limpo) < 10:
        alertas.append("Transcrição muito curta. Pode estar incompleta.")
    if analise["confianca"] < 0.4 and analise["eh_contabil"]:
        alertas.append("Baixa confiança na detecção. Recomenda-se leitura humana.")

    resultado["alertas"] = alertas

    return resultado


def processar_lote_transcricoes(transcricoes: list[dict]) -> dict:
    """
    Processa múltiplas transcrições de uma vez.

    Args:
        transcricoes: lista de dicts com {"texto": str, "metadata": dict}

    Returns:
        dict consolidado com contagens e resultados
    """
    resultados = []
    contadores = {
        "total": 0,
        "sucesso": 0,
        "perguntas_contabeis": 0,
        "prontas_classificacao": 0,
        "nao_contabeis": 0,
    }

    for item in transcricoes:
        texto = item.get("texto", "")
        meta = item.get("metadata", {})
        resultado = preparar_para_pipeline(texto, meta)
        resultados.append(resultado)

        contadores["total"] += 1
        if resultado.get("sucesso"):
            contadores["sucesso"] += 1
            if resultado.get("analise", {}).get("eh_contabil"):
                contadores["perguntas_contabeis"] += 1
            else:
                contadores["nao_contabeis"] += 1
            if resultado.get("pronto_para_classificacao"):
                contadores["prontas_classificacao"] += 1

    return {
        "contadores": contadores,
        "resultados": resultados,
    }


# ══════════════════════════════════════════════════════════════════════════════
# TESTES
# ══════════════════════════════════════════════════════════════════════════════

def _rodar_testes():
    """Testes unitários para ponte_transcriber.py"""
    testes_passou = 0
    testes_falhou = 0

    def ok(condicao, descricao):
        nonlocal testes_passou, testes_falhou
        if condicao:
            testes_passou += 1
        else:
            testes_falhou += 1
            print(f"  FALHOU: {descricao}")

    # ── Teste 1: Limpar hesitações ──
    ok(limpar_transcricao("áh éh tipo assim o imposto") == "O imposto", "Limpar: hesitações removidas")

    # ── Teste 2: Limpar repetições ──
    ok(limpar_transcricao("o o imposto do do mês") == "O imposto do mês", "Limpar: repetições removidas")

    # ── Teste 3: Limpar texto vazio ──
    ok(limpar_transcricao("") == "", "Limpar: vazio")
    ok(limpar_transcricao(None) == "", "Limpar: None")

    # ── Teste 4: Capitalizar ──
    ok(limpar_transcricao("quanto pago de imposto?")[0] == "Q", "Limpar: capitaliza")

    # ── Teste 5: Extrair CNPJ ──
    dados = extrair_dados_transcritos("O CNPJ é 12.345.678/0001-99 da empresa")
    ok("cnpjs" in dados, "Extrair: CNPJ encontrado")
    ok(dados["cnpjs"][0] == "12.345.678/0001-99", "Extrair: CNPJ correto")

    # ── Teste 6: Extrair CPF ──
    dados2 = extrair_dados_transcritos("O CPF dele é 123.456.789-00")
    ok("cpfs" in dados2, "Extrair: CPF encontrado")

    # ── Teste 7: Extrair valores monetários ──
    dados3 = extrair_dados_transcritos("A nota foi de R$ 1.500,00 e o frete R$ 200,50")
    ok("valores" in dados3, "Extrair: valores encontrados")
    ok(1500.0 in dados3["valores"], "Extrair: valor 1500")
    ok(200.5 in dados3["valores"], "Extrair: valor 200.50")

    # ── Teste 8: Extrair "X mil" ──
    dados4 = extrair_dados_transcritos("O faturamento foi de 250 mil reais")
    ok("valores" in dados4, "Extrair: valor 'mil' encontrado")
    ok(any(v >= 250000 for v in dados4["valores"]), "Extrair: 250 mil = 250000")

    # ── Teste 9: Extrair datas ──
    dados5 = extrair_dados_transcritos("Vence dia 15 de março e outra em 20/04/2026")
    ok("datas" in dados5, "Extrair: datas encontradas")

    # ── Teste 10: Extrair percentuais ──
    dados6 = extrair_dados_transcritos("A alíquota é de 5,5 por cento do faturamento")
    ok("percentuais" in dados6, "Extrair: percentual encontrado")
    ok(5.5 in dados6["percentuais"], "Extrair: 5.5%")

    # ── Teste 11: Sem dados ──
    dados7 = extrair_dados_transcritos("Bom dia, tudo bem?")
    ok(len(dados7) == 0, "Extrair: sem dados em texto genérico")

    # ── Teste 12: Detectar pergunta contábil ──
    r = detectar_pergunta_contabil("Quanto vou pagar de imposto no Simples Nacional?")
    ok(r["eh_pergunta"] == True, "Detectar: é pergunta")
    ok(r["eh_contabil"] == True, "Detectar: é contábil")
    ok(r["confianca"] >= 0.6, "Detectar: alta confiança")
    ok("imposto" in r["termos_encontrados"], "Detectar: termo 'imposto'")
    ok("simples" in r["termos_encontrados"], "Detectar: termo 'simples'")

    # ── Teste 13: Detectar não-contábil ──
    r2 = detectar_pergunta_contabil("Qual o melhor restaurante perto daqui?")
    ok(r2["eh_contabil"] == False, "Detectar: não contábil")
    ok(r2["confianca"] <= 0.3, "Detectar: baixa confiança")

    # ── Teste 14: Detectar informativo (não pergunta) ──
    r3 = detectar_pergunta_contabil("O imposto do mês passado foi de mil reais.")
    ok(r3["eh_contabil"] == True, "Detectar: é contábil")
    ok(r3["eh_pergunta"] == False, "Detectar: não é pergunta (informativo)")

    # ── Teste 15: Pipeline completo — pergunta contábil ──
    p = preparar_para_pipeline(
        "áh éh quanto que eu pago de ICMS no meu faturamento de R$ 50.000,00?",
        {"remetente": "Cliente X", "grupo": "RRT Contabilidade - Cliente X", "duracao_audio": 15}
    )
    ok(p["sucesso"] == True, "Pipeline: sucesso")
    ok(p["origem"] == "audio_transcrito", "Pipeline: origem")
    ok("éh" not in p["texto_limpo"], "Pipeline: hesitações limpas")
    ok(p["analise"]["eh_pergunta"] == True, "Pipeline: é pergunta")
    ok(p["analise"]["eh_contabil"] == True, "Pipeline: é contábil")
    ok(p["pronto_para_classificacao"] == True, "Pipeline: pronto para classificação")
    ok(p["payload_classificacao"]["texto"] is not None, "Pipeline: payload tem texto")
    ok(50000.0 in p["dados_extraidos"]["valores"], "Pipeline: valor extraído")

    # ── Teste 16: Pipeline — não contábil ──
    p2 = preparar_para_pipeline("Bom dia, tudo bem com vocês?")
    ok(p2["sucesso"] == True, "Pipeline não-contábil: sucesso")
    ok(p2["pronto_para_classificacao"] == False, "Pipeline não-contábil: skip")
    ok("contábil" in p2.get("motivo_skip", "").lower(), "Pipeline não-contábil: motivo")

    # ── Teste 17: Pipeline — transcrição vazia ──
    p3 = preparar_para_pipeline("")
    ok(p3["sucesso"] == False, "Pipeline vazio: falha")

    p4 = preparar_para_pipeline("   áh  éh  hm  ")
    ok(p4["sucesso"] == False, "Pipeline só hesitações: falha")

    # ── Teste 18: Pipeline — áudio longo ──
    p5 = preparar_para_pipeline(
        "Preciso saber sobre a rescisão do funcionário",
        {"duracao_audio": 180}
    )
    ok(any(">2min" in a for a in p5["alertas"]), "Pipeline: alerta áudio longo")

    # ── Teste 19: Pipeline — transcrição curta ──
    p6 = preparar_para_pipeline("ICMS?")
    ok(any("curta" in a.lower() for a in p6["alertas"]), "Pipeline: alerta transcrição curta")

    # ── Teste 20: Lote de transcrições ──
    lote = processar_lote_transcricoes([
        {"texto": "Quanto pago de DAS no MEI?", "metadata": {"remetente": "Cliente A"}},
        {"texto": "Bom dia pessoal", "metadata": {"remetente": "Cliente B"}},
        {"texto": "A alíquota do ISS é quanto por cento?", "metadata": {"remetente": "Cliente C"}},
    ])
    ok(lote["contadores"]["total"] == 3, "Lote: total 3")
    ok(lote["contadores"]["sucesso"] == 3, "Lote: 3 sucesso")
    ok(lote["contadores"]["perguntas_contabeis"] == 2, "Lote: 2 contábeis")
    ok(lote["contadores"]["prontas_classificacao"] == 2, "Lote: 2 prontas")
    ok(lote["contadores"]["nao_contabeis"] == 1, "Lote: 1 não contábil")

    # ── Teste 21: Detecção de múltiplos termos ──
    r4 = detectar_pergunta_contabil(
        "Como faço a declaração do imposto de renda com carnê-leão e distribuição de lucros?"
    )
    ok(len(r4["termos_encontrados"]) >= 3, "Multi-termos: 3+ termos")
    ok(r4["confianca"] >= 0.8, "Multi-termos: alta confiança")

    # ── Teste 22: Metadata preservada ──
    p7 = preparar_para_pipeline(
        "Quanto pago de imposto?",
        {"remetente": "João", "grupo": "RRT - João", "timestamp": "2026-04-16T10:00:00"}
    )
    ok(p7["remetente"] == "João", "Metadata: remetente")
    ok(p7["grupo"] == "RRT - João", "Metadata: grupo")
    ok(p7["timestamp"] == "2026-04-16T10:00:00", "Metadata: timestamp")

    # ── Teste 23: Lote vazio ──
    lote_vazio = processar_lote_transcricoes([])
    ok(lote_vazio["contadores"]["total"] == 0, "Lote vazio: zero")

    # ── Teste 24: Percentual com vírgula ──
    dados8 = extrair_dados_transcritos("O percentual é de 12,5%")
    ok("percentuais" in dados8, "Percentual vírgula: encontrado")
    ok(12.5 in dados8["percentuais"], "Percentual vírgula: 12.5")

    print(f"\n{'='*50}")
    print(f"ponte_transcriber.py: {testes_passou} PASSOU, {testes_falhou} FALHOU de {testes_passou + testes_falhou}")
    print(f"{'='*50}")

    return testes_falhou == 0


if __name__ == "__main__":
    _rodar_testes()
