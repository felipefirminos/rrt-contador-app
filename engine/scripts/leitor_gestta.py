#!/usr/bin/env python3
"""
Leitor Gestta — Extrai e estrutura conversas do portal Gestta/ONVIO v4.3

Recebe dados estruturados do portal Gestta (app.gestta.com.br/attendance)
extraídos via read_page do Claude in Chrome e:
  1. Parseia a lista de atendimentos (sidebar) em dicts estruturados
  2. Parseia uma thread de conversa em mensagens individuais
  3. Identifica mensagens de clientes vs equipe RRT
  4. Detecta perguntas sem resposta da equipe
  5. Alimenta o pipeline classificar_mensagem → ponte_whatsapp → rascunho_resposta

Uso:
    python3 leitor_gestta.py --teste

Importação:
    from leitor_gestta import (
        parsear_sidebar, parsear_conversa, identificar_pendencias,
        preparar_para_classificacao, pipeline_gestta_completo
    )

URL do portal: https://app.gestta.com.br/attendance/#/chat/ongoing
"""

import re
import sys
import json
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════════
# CONSTANTES — Equipe RRT (membros conhecidos)
# ═══════════════════════════════════════════════════════════════

EQUIPE_RRT = {
    # Nomes exatos como aparecem no Gestta
    "MARI FALAVIGNA",
    "MARINA DANTAS",
    "Marcia Gomes",
    "Adriana Russo",
    "Maria Sartorelli.",
    "Bianca P",
    "Arthur",
    "Jonatas Guimaraes",
    "RRT Richard Mendes",
    "Thiago Francisco",
    # Variações comuns
    "Richard Mendes",
    "Richard",
    "Mari",
    "Marina",
    "Adriana",
    "Bianca",
    "Jonatas",
    "Maria",
    "Marcia",
    "Thiago",
}

# Palavras que indicam mensagens de sistema (não são perguntas)
MENSAGENS_SISTEMA = [
    "atendimento transferido",
    "atendimento iniciado",
    "mensagem interna",
]

# Mensagens curtas genéricas que NÃO são perguntas
SAUDACOES = [
    "bom dia", "boa tarde", "boa noite", "obrigado", "obrigada",
    "obg", "obgd", "vlw", "valeu", "ok", "ta bom", "tá bom",
    "beleza", "belezinha", "show", "pode ser", "pode mandar",
    "sim", "não", "nao", "certo", "blz", "blza", "top",
    "imagina", "de nada", "disponha", "grande abraço",
]


# ═══════════════════════════════════════════════════════════════
# PARSER DA SIDEBAR (lista de atendimentos)
# ═══════════════════════════════════════════════════════════════

def parsear_sidebar(elementos_sidebar):
    """
    Parseia a lista de atendimentos do sidebar do Gestta.

    Args:
        elementos_sidebar: list[dict] — cada dict com campos extraídos
            do read_page. Formato esperado:
            {
                "grupo_nome": "RRT Contabilidade - Wesley e Suzana",
                "responsavel": "Adriana Russo",
                "ultima_mensagem": "No último que pagamos não tinha PIS COFINS",
                "tempo": "3 horas",
                "badge": 11,
                "tab": "em_atendimento" | "pendente"
            }

    Returns:
        list[dict] — atendimentos parseados e enriquecidos:
        {
            "grupo_nome_completo": str,
            "cliente_nome": str,       # extraído de "RRT Contabilidade - X"
            "responsavel": str,
            "ultima_mensagem": str,
            "tempo_texto": str,
            "minutos_estimados": int,   # conversão para minutos
            "badge": int,
            "tab": str,
            "prioridade": str,         # "alta" | "media" | "baixa"
        }
    """
    atendimentos = []

    for elem in elementos_sidebar:
        grupo = elem.get("grupo_nome", "")
        cliente = _extrair_cliente_nome(grupo)

        tempo_texto = elem.get("tempo", "")
        minutos = _converter_tempo_para_minutos(tempo_texto)

        ultima_msg = elem.get("ultima_mensagem", "")
        badge = elem.get("badge", 0)
        tab = elem.get("tab", "em_atendimento")

        # Calcular prioridade
        prioridade = _calcular_prioridade(
            ultima_msg=ultima_msg,
            minutos=minutos,
            badge=badge,
            tab=tab,
        )

        atendimentos.append({
            "grupo_nome_completo": grupo,
            "cliente_nome": cliente,
            "responsavel": elem.get("responsavel", ""),
            "ultima_mensagem": ultima_msg,
            "tempo_texto": tempo_texto,
            "minutos_estimados": minutos,
            "badge": badge,
            "tab": tab,
            "prioridade": prioridade,
        })

    # Ordenar: pendentes primeiro, depois por prioridade, depois por tempo
    ordem_prioridade = {"alta": 0, "media": 1, "baixa": 2}
    ordem_tab = {"pendente": 0, "em_atendimento": 1}
    atendimentos.sort(key=lambda a: (
        ordem_tab.get(a["tab"], 1),
        ordem_prioridade.get(a["prioridade"], 2),
        -a["minutos_estimados"],  # mais antigo = mais urgente
    ))

    return atendimentos


def _extrair_cliente_nome(grupo_nome):
    """Extrai nome do cliente de 'RRT Contabilidade - Nome Cliente'."""
    if " - " in grupo_nome:
        return grupo_nome.split(" - ", 1)[1].strip()
    # Fallback: se não segue padrão RRT
    return grupo_nome.strip()


def _converter_tempo_para_minutos(tempo_texto):
    """Converte texto de tempo do Gestta para minutos estimados."""
    if not tempo_texto:
        return 0

    texto = tempo_texto.lower().strip()

    # "22 minutos", "39 minutos"
    match = re.search(r'(\d+)\s*minuto', texto)
    if match:
        return int(match.group(1))

    # "uma hora", "2 horas", "3 horas"
    match = re.search(r'(\d+)\s*hora', texto)
    if match:
        return int(match.group(1)) * 60

    if "uma hora" in texto:
        return 60

    # "17 horas"
    match = re.search(r'(\d+)\s*hora', texto)
    if match:
        return int(match.group(1)) * 60

    # "1 dia", "2 dias"
    match = re.search(r'(\d+)\s*dia', texto)
    if match:
        return int(match.group(1)) * 1440

    if "um dia" in texto:
        return 1440

    # "1 semana"
    match = re.search(r'(\d+)\s*semana', texto)
    if match:
        return int(match.group(1)) * 10080

    return 0


def _calcular_prioridade(ultima_msg, minutos, badge, tab):
    """Calcula prioridade do atendimento."""
    # Pendentes são sempre alta prioridade
    if tab == "pendente":
        return "alta"

    # Alta: mensagem contém pergunta fiscal + tempo > 30min sem resposta
    msg_lower = ultima_msg.lower()
    tem_pergunta = "?" in ultima_msg
    tem_termo_fiscal = any(t in msg_lower for t in [
        "pis", "cofins", "icms", "das", "darf", "simples", "imposto",
        "alíquota", "aliquota", "guia", "rescisão", "rescisao",
        "férias", "ferias", "nota fiscal", "retenção", "retencao",
        "faturamento", "receita", "lucro", "tribut",
    ])

    if (tem_pergunta or tem_termo_fiscal) and minutos > 30:
        return "alta"

    if tem_pergunta and minutos > 120:
        return "alta"

    if minutos > 240:  # Mais de 4h sem resposta
        return "media"

    # Verificar se é apenas saudação/agradecimento
    if _eh_saudacao(msg_lower):
        return "baixa"

    if tem_pergunta or tem_termo_fiscal:
        return "media"

    return "baixa"


def _eh_saudacao(texto_lower):
    """Verifica se é apenas saudação ou mensagem genérica."""
    texto_limpo = re.sub(r'[!.,;]', '', texto_lower).strip()
    return texto_limpo in SAUDACOES or len(texto_limpo) < 5


# ═══════════════════════════════════════════════════════════════
# PARSER DE CONVERSA (thread de mensagens)
# ═══════════════════════════════════════════════════════════════

def parsear_conversa(mensagens_raw, grupo_nome=None):
    """
    Parseia uma thread de conversa do Gestta.

    Args:
        mensagens_raw: list[dict] — mensagens extraídas via read_page.
            Formato esperado:
            {
                "remetente": "Wesley - SW7",
                "texto": "No último que pagamos não tinha PIS COFINS",
                "timestamp": "16/04/2026 - 10:01",
                "flags": ["Editada"],        # opcional
                "arquivo": "nome.pdf",        # opcional
                "arquivo_tipo": "application/pdf",  # opcional
            }
        grupo_nome: str — nome do grupo (para contexto)

    Returns:
        list[dict] — mensagens parseadas e enriquecidas:
        {
            "remetente": str,
            "texto": str,
            "timestamp_str": str,
            "timestamp_dt": datetime | None,
            "eh_equipe": bool,
            "eh_sistema": bool,
            "eh_arquivo": bool,
            "arquivo_nome": str | None,
            "flags": list[str],
            "grupo_nome": str | None,
            "cliente_nome": str | None,  # extraído do remetente
        }
    """
    mensagens = []
    cliente_nome_do_grupo = _extrair_cliente_nome(grupo_nome) if grupo_nome else None

    for msg_raw in mensagens_raw:
        remetente = msg_raw.get("remetente", "").strip()
        texto = msg_raw.get("texto", "").strip()
        timestamp_str = msg_raw.get("timestamp", "")
        flags = msg_raw.get("flags", [])

        # Detectar tipo
        eh_sistema = _eh_mensagem_sistema(texto, remetente)
        eh_equipe = _eh_membro_equipe(remetente) if not eh_sistema else False
        eh_arquivo = bool(msg_raw.get("arquivo"))

        # Parsear timestamp
        timestamp_dt = _parsear_timestamp(timestamp_str)

        # Extrair nome do cliente do remetente
        cliente_nome = None
        if not eh_equipe and not eh_sistema:
            cliente_nome = _extrair_nome_do_remetente(remetente)

        mensagens.append({
            "remetente": remetente,
            "texto": texto,
            "timestamp_str": timestamp_str,
            "timestamp_dt": timestamp_dt,
            "eh_equipe": eh_equipe,
            "eh_sistema": eh_sistema,
            "eh_arquivo": eh_arquivo,
            "arquivo_nome": msg_raw.get("arquivo"),
            "flags": flags,
            "grupo_nome": grupo_nome,
            "cliente_nome": cliente_nome or cliente_nome_do_grupo,
        })

    return mensagens


def _eh_membro_equipe(remetente):
    """Verifica se o remetente é membro da equipe RRT."""
    if not remetente:
        return False

    # Check exato
    if remetente in EQUIPE_RRT:
        return True

    # Check por prefixo "RRT"
    if remetente.startswith("RRT "):
        return True

    # Check normalizado (sem case)
    remetente_lower = remetente.lower()
    for membro in EQUIPE_RRT:
        if membro.lower() == remetente_lower:
            return True

    return False


def _eh_mensagem_sistema(texto, remetente):
    """Verifica se é mensagem de sistema do Gestta."""
    texto_lower = texto.lower()
    for padrao in MENSAGENS_SISTEMA:
        if padrao in texto_lower:
            return True

    # Padrão "Por X em Atendimento transferido"
    if remetente.startswith("Por ") and "em" in remetente:
        return True

    return False


def _parsear_timestamp(ts_str):
    """Parseia timestamp do formato Gestta: '16/04/2026 - 10:01'."""
    if not ts_str:
        return None
    try:
        return datetime.strptime(ts_str.strip(), "%d/%m/%Y - %H:%M")
    except ValueError:
        return None


def _extrair_nome_do_remetente(remetente):
    """Extrai primeiro nome do remetente (remove sufixo da empresa)."""
    # "Wesley - SW7" → "Wesley"
    if " - " in remetente:
        return remetente.split(" - ")[0].strip()
    return remetente.strip()


# ═══════════════════════════════════════════════════════════════
# DETECTOR DE PENDÊNCIAS (mensagens sem resposta)
# ═══════════════════════════════════════════════════════════════

def identificar_pendencias(mensagens_parseadas, horas_limite=24):
    """
    Identifica mensagens de clientes que não foram respondidas pela equipe.

    Lógica:
    - Percorre as mensagens do mais recente ao mais antigo
    - Se a última mensagem é do cliente → há pendência
    - Se a última mensagem é da equipe → resolvido
    - Ignora saudações genéricas e mensagens de sistema

    Args:
        mensagens_parseadas: list[dict] — output de parsear_conversa()
        horas_limite: int — quantas horas para trás verificar (default 24)

    Returns:
        dict:
        {
            "tem_pendencia": bool,
            "mensagens_pendentes": list[dict],  # mensagens do cliente sem resposta
            "ultima_resposta_equipe": dict | None,
            "tempo_espera_minutos": int | None,  # desde a pergunta do cliente
            "resumo": str,  # descrição para o relatório
        }
    """
    if not mensagens_parseadas:
        return {
            "tem_pendencia": False,
            "mensagens_pendentes": [],
            "ultima_resposta_equipe": None,
            "tempo_espera_minutos": None,
            "resumo": "Sem mensagens",
        }

    # Filtrar mensagens dentro do limite de tempo
    agora = datetime.now()
    limite = agora - timedelta(hours=horas_limite)

    mensagens_recentes = [
        m for m in mensagens_parseadas
        if not m["eh_sistema"]
        and (m["timestamp_dt"] is None or m["timestamp_dt"] >= limite)
    ]

    if not mensagens_recentes:
        return {
            "tem_pendencia": False,
            "mensagens_pendentes": [],
            "ultima_resposta_equipe": None,
            "tempo_espera_minutos": None,
            "resumo": f"Sem mensagens nas últimas {horas_limite}h",
        }

    # Ordenar por timestamp (mais recente primeiro)
    mensagens_recentes.sort(
        key=lambda m: m["timestamp_dt"] or datetime.min,
        reverse=True,
    )

    # Coletar mensagens pendentes do cliente (antes da primeira resposta da equipe)
    pendentes = []
    ultima_equipe = None

    for msg in mensagens_recentes:
        if msg["eh_equipe"]:
            ultima_equipe = msg
            break  # Encontrou resposta da equipe → parar
        elif not msg["eh_sistema"]:
            # É mensagem do cliente
            texto_lower = msg["texto"].lower().strip()
            # Pular saudações vazias / mensagens genéricas
            if not _eh_saudacao(texto_lower) or "?" in msg["texto"]:
                pendentes.append(msg)
            elif not pendentes:
                # Se a ÚNICA mensagem recente é uma saudação, ainda é pendente
                pendentes.append(msg)

    if not pendentes:
        return {
            "tem_pendencia": False,
            "mensagens_pendentes": [],
            "ultima_resposta_equipe": ultima_equipe,
            "tempo_espera_minutos": None,
            "resumo": "Equipe já respondeu",
        }

    # Calcular tempo de espera
    tempo_espera = None
    msg_mais_antiga = pendentes[-1]
    if msg_mais_antiga["timestamp_dt"]:
        delta = agora - msg_mais_antiga["timestamp_dt"]
        tempo_espera = int(delta.total_seconds() / 60)

    # Gerar resumo
    textos_pendentes = [m["texto"] for m in pendentes if m["texto"]]
    resumo_texto = " | ".join(textos_pendentes[:3])
    if len(resumo_texto) > 150:
        resumo_texto = resumo_texto[:147] + "..."

    return {
        "tem_pendencia": True,
        "mensagens_pendentes": pendentes,
        "ultima_resposta_equipe": ultima_equipe,
        "tempo_espera_minutos": tempo_espera,
        "resumo": resumo_texto,
    }


# ═══════════════════════════════════════════════════════════════
# PREPARAÇÃO PARA O PIPELINE (Gestta → classificar_mensagem)
# ═══════════════════════════════════════════════════════════════

def preparar_para_classificacao(pendencias_resultado, grupo_nome=None):
    """
    Converte pendências detectadas para o formato de entrada
    do classificar_lote() / classificar_mensagem().

    Args:
        pendencias_resultado: dict — output de identificar_pendencias()
        grupo_nome: str — nome do grupo para contexto

    Returns:
        list[dict] — formato esperado por classificar_lote():
        [
            {
                "texto": str,
                "cliente_nome": str,
                "grupo_nome": str,
                "data": str,
                "status_atendimento": str,
            }
        ]
    """
    if not pendencias_resultado["tem_pendencia"]:
        return []

    mensagens_para_classificar = []

    for msg in pendencias_resultado["mensagens_pendentes"]:
        # Pular mensagens que são apenas arquivos sem texto
        if msg["eh_arquivo"] and not msg["texto"]:
            continue

        mensagens_para_classificar.append({
            "texto": msg["texto"],
            "cliente_nome": msg.get("cliente_nome", ""),
            "grupo_nome": grupo_nome or msg.get("grupo_nome", ""),
            "data": msg.get("timestamp_str", ""),
            "status_atendimento": "pendente",
        })

    return mensagens_para_classificar


def pipeline_gestta_completo(
    mensagens_raw,
    grupo_nome=None,
    horas_limite=24,
    apenas_calculaveis=False,
):
    """
    Pipeline completo: Gestta → parse → pendências → classificação.

    Executa todo o fluxo de:
    1. Parsear mensagens raw do Gestta
    2. Identificar pendências (mensagens sem resposta)
    3. Preparar para classificação
    4. Classificar usando classificar_mensagem.py
    5. (Opcional) Filtrar apenas calculáveis

    Args:
        mensagens_raw: list[dict] — dados brutos do read_page
        grupo_nome: str — nome do grupo
        horas_limite: int — janela de tempo (default 24h)
        apenas_calculaveis: bool — se True, filtra só mensagens com cálculo

    Returns:
        dict:
        {
            "grupo_nome": str,
            "cliente_nome": str,
            "total_mensagens": int,
            "tem_pendencia": bool,
            "tempo_espera_minutos": int | None,
            "mensagens_classificadas": list[dict],
            "resumo_pendencias": str,
            "pronto_para_ponte": bool,   # se há algo para a ponte_whatsapp
        }
    """
    # Importar classificador (lazy import para evitar circular)
    try:
        from classificar_mensagem import classificar_lote, filtrar_calculaveis
    except ImportError:
        # Fallback se não conseguir importar
        classificar_lote = None
        filtrar_calculaveis = None

    # Step 1: Parsear
    mensagens = parsear_conversa(mensagens_raw, grupo_nome)
    cliente_nome = _extrair_cliente_nome(grupo_nome) if grupo_nome else ""

    # Step 2: Identificar pendências
    pendencias = identificar_pendencias(mensagens, horas_limite)

    # Step 3: Preparar para classificação
    para_classificar = preparar_para_classificacao(pendencias, grupo_nome)

    # Step 4: Classificar
    classificadas = []
    if para_classificar and classificar_lote:
        classificadas = classificar_lote(para_classificar)
        if apenas_calculaveis and filtrar_calculaveis:
            classificadas = filtrar_calculaveis(classificadas)

    return {
        "grupo_nome": grupo_nome or "",
        "cliente_nome": cliente_nome,
        "total_mensagens": len(mensagens),
        "tem_pendencia": pendencias["tem_pendencia"],
        "tempo_espera_minutos": pendencias.get("tempo_espera_minutos"),
        "mensagens_classificadas": classificadas,
        "resumo_pendencias": pendencias["resumo"],
        "pronto_para_ponte": len(classificadas) > 0 and any(
            c.get("calculavel") and c.get("confianca") in ("alta", "media")
            for c in classificadas
        ),
    }


# ═══════════════════════════════════════════════════════════════
# CONSOLIDADOR (múltiplos grupos → relatório)
# ═══════════════════════════════════════════════════════════════

def consolidar_atendimentos(resultados_pipeline):
    """
    Consolida resultados de múltiplos grupos em relatório único.

    Args:
        resultados_pipeline: list[dict] — outputs de pipeline_gestta_completo()

    Returns:
        dict:
        {
            "total_grupos": int,
            "com_pendencia": int,
            "prontos_para_ponte": int,
            "grupos_urgentes": list[dict],      # pendência + calculável
            "grupos_pendentes": list[dict],      # pendência mas não calculável
            "grupos_ok": list[dict],             # sem pendência
            "resumo_geral": str,
        }
    """
    urgentes = []
    pendentes = []
    ok = []

    for r in resultados_pipeline:
        if r["pronto_para_ponte"]:
            urgentes.append(r)
        elif r["tem_pendencia"]:
            pendentes.append(r)
        else:
            ok.append(r)

    # Ordenar urgentes por tempo de espera (maior primeiro)
    urgentes.sort(
        key=lambda r: r.get("tempo_espera_minutos") or 0,
        reverse=True,
    )

    resumo_parts = []
    if urgentes:
        resumo_parts.append(
            f"🔴 {len(urgentes)} grupo(s) com pergunta fiscal pendente"
        )
    if pendentes:
        resumo_parts.append(
            f"🟡 {len(pendentes)} grupo(s) com mensagem pendente"
        )
    if ok:
        resumo_parts.append(
            f"🟢 {len(ok)} grupo(s) OK"
        )

    return {
        "total_grupos": len(resultados_pipeline),
        "com_pendencia": len(urgentes) + len(pendentes),
        "prontos_para_ponte": len(urgentes),
        "grupos_urgentes": urgentes,
        "grupos_pendentes": pendentes,
        "grupos_ok": ok,
        "resumo_geral": " | ".join(resumo_parts) if resumo_parts else "Sem dados",
    }


# ═══════════════════════════════════════════════════════════════
# TRIAGEM DE SIDEBAR (decidir quais grupos abrir)
# ═══════════════════════════════════════════════════════════════

def triar_sidebar(atendimentos_parseados, max_abrir=10):
    """
    Decide quais grupos devem ser abertos para leitura completa
    durante um scan automático (otimiza tempo de scan).

    Lógica:
    - SEMPRE abrir: tab "pendente" (sem atendente)
    - SEMPRE abrir: prioridade "alta"
    - ABRIR se: última mensagem NÃO é da equipe (provável pendência)
    - PULAR: última mensagem é saudação/agradecimento da equipe
    - Limitar a max_abrir para não demorar demais

    Args:
        atendimentos_parseados: list[dict] — output de parsear_sidebar()
        max_abrir: int — máximo de grupos para abrir (default 10)

    Returns:
        dict:
        {
            "abrir": list[dict],      # grupos que devem ser abertos
            "pular": list[dict],      # grupos que podem ser ignorados
            "motivos": dict[str, str], # grupo_nome → motivo da decisão
        }
    """
    abrir = []
    pular = []
    motivos = {}

    for atendimento in atendimentos_parseados:
        nome = atendimento["grupo_nome_completo"]
        tab = atendimento.get("tab", "em_atendimento")
        prioridade = atendimento.get("prioridade", "baixa")
        responsavel = atendimento.get("responsavel", "")
        ultima_msg = atendimento.get("ultima_mensagem", "").lower()

        # Regra 1: Pendentes sempre abrir
        if tab == "pendente":
            abrir.append(atendimento)
            motivos[nome] = "Pendente (sem atendente)"
            continue

        # Regra 2: Prioridade alta sempre abrir
        if prioridade == "alta":
            abrir.append(atendimento)
            motivos[nome] = f"Prioridade alta — {atendimento.get('ultima_mensagem', '')[:50]}"
            continue

        # Regra 3: Se última mensagem parece ser do cliente
        ultima_eh_equipe = _eh_membro_equipe(responsavel) if responsavel else False
        if not ultima_eh_equipe and not _eh_saudacao(ultima_msg):
            abrir.append(atendimento)
            motivos[nome] = f"Última mensagem do cliente — {atendimento.get('ultima_mensagem', '')[:50]}"
            continue

        # Regra 4: Média prioridade, vale checar
        if prioridade == "media":
            abrir.append(atendimento)
            motivos[nome] = "Prioridade média"
            continue

        # Default: pular
        pular.append(atendimento)
        motivos[nome] = "Equipe respondeu / saudação"

    # Limitar
    if len(abrir) > max_abrir:
        # Manter os mais urgentes
        abrir_final = abrir[:max_abrir]
        pular.extend(abrir[max_abrir:])
        for a in abrir[max_abrir:]:
            motivos[a["grupo_nome_completo"]] += " (excedeu limite de scan)"
        abrir = abrir_final

    return {
        "abrir": abrir,
        "pular": pular,
        "motivos": motivos,
    }


# ═══════════════════════════════════════════════════════════════
# SLA — Alertas de Tempo de Resposta
# ═══════════════════════════════════════════════════════════════

SLA_LIMITES = {
    "critico": 120,    # 2h — mensagem fiscal sem resposta
    "urgente": 240,    # 4h — qualquer mensagem sem resposta
    "atencao": 480,    # 8h — informacional
}

def avaliar_sla(atendimentos_parseados):
    """
    Avalia SLA de resposta para cada atendimento.

    Args:
        atendimentos_parseados: list[dict] — output de parsear_sidebar()

    Returns:
        dict:
        {
            "criticos": list[dict],    # > 2h com pergunta fiscal
            "urgentes": list[dict],    # > 4h qualquer pendência
            "atencao": list[dict],     # > 8h
            "ok": list[dict],          # dentro do SLA
            "resumo_sla": str,
        }
    """
    criticos = []
    urgentes = []
    atencao = []
    ok = []

    for a in atendimentos_parseados:
        minutos = a.get("minutos_estimados", 0)
        prioridade = a.get("prioridade", "baixa")
        tab = a.get("tab", "em_atendimento")

        # Pendentes sem atendente = sempre crítico
        if tab == "pendente" and minutos >= SLA_LIMITES["critico"]:
            a["sla_status"] = "critico"
            a["sla_motivo"] = f"Pendente há {_formatar_tempo_sla(minutos)} sem atendente"
            criticos.append(a)
        elif prioridade == "alta" and minutos >= SLA_LIMITES["critico"]:
            a["sla_status"] = "critico"
            a["sla_motivo"] = f"Pergunta fiscal há {_formatar_tempo_sla(minutos)} sem resposta"
            criticos.append(a)
        elif minutos >= SLA_LIMITES["urgente"]:
            a["sla_status"] = "urgente"
            a["sla_motivo"] = f"Sem resposta há {_formatar_tempo_sla(minutos)}"
            urgentes.append(a)
        elif minutos >= SLA_LIMITES["atencao"]:
            a["sla_status"] = "atencao"
            a["sla_motivo"] = f"Atenção: {_formatar_tempo_sla(minutos)} sem interação"
            atencao.append(a)
        else:
            a["sla_status"] = "ok"
            a["sla_motivo"] = ""
            ok.append(a)

    partes = []
    if criticos:
        partes.append(f"🔴 {len(criticos)} CRÍTICO(S)")
    if urgentes:
        partes.append(f"🟠 {len(urgentes)} urgente(s)")
    if atencao:
        partes.append(f"🟡 {len(atencao)} atenção")
    if ok:
        partes.append(f"🟢 {len(ok)} OK")

    return {
        "criticos": criticos,
        "urgentes": urgentes,
        "atencao": atencao,
        "ok": ok,
        "resumo_sla": " | ".join(partes) if partes else "Sem dados",
    }


def _formatar_tempo_sla(minutos):
    """Formata minutos em texto legível para SLA."""
    if minutos < 60:
        return f"{minutos}min"
    horas = minutos // 60
    mins = minutos % 60
    if mins:
        return f"{horas}h{mins}min"
    return f"{horas}h"


# ═══════════════════════════════════════════════════════════════
# TESTES
# ═══════════════════════════════════════════════════════════════

def rodar_testes():
    testes_ok = 0
    testes_total = 0

    def teste(descricao, obtido, esperado):
        nonlocal testes_ok, testes_total
        testes_total += 1
        if obtido == esperado:
            testes_ok += 1
            print(f"  ✅ PASSOU: {descricao}")
        else:
            print(f"  ❌ FALHOU: {descricao}")
            print(f"     Esperado: {esperado}")
            print(f"     Obtido:   {obtido}")

    print("\n🧪 Leitor Gestta — Testes\n")

    # ─── Teste 1: Extração de nome do cliente ─────────────────
    print("── Extração de Nome ──")
    teste(
        "Cliente de grupo padrão",
        _extrair_cliente_nome("RRT Contabilidade - Wesley e Suzana"),
        "Wesley e Suzana",
    )
    teste(
        "Cliente com nome longo",
        _extrair_cliente_nome("RRT Contabilidade - Condominio Residencial JoãoXXIII"),
        "Condominio Residencial JoãoXXIII",
    )
    teste(
        "Nome sem padrão RRT",
        _extrair_cliente_nome("Gabriel Mello"),
        "Gabriel Mello",
    )

    # ─── Teste 2: Conversão de tempo ──────────────────────────
    print("\n── Conversão de Tempo ──")
    teste("22 minutos", _converter_tempo_para_minutos("22 minutos"), 22)
    teste("uma hora", _converter_tempo_para_minutos("uma hora"), 60)
    teste("3 horas", _converter_tempo_para_minutos("3 horas"), 180)
    teste("17 horas", _converter_tempo_para_minutos("17 horas"), 1020)
    teste("2 dias", _converter_tempo_para_minutos("2 dias"), 2880)
    teste("vazio", _converter_tempo_para_minutos(""), 0)

    # ─── Teste 3: Identificação equipe vs cliente ─────────────
    print("\n── Identificação Equipe/Cliente ──")
    teste("MARI FALAVIGNA é equipe", _eh_membro_equipe("MARI FALAVIGNA"), True)
    teste("Adriana Russo é equipe", _eh_membro_equipe("Adriana Russo"), True)
    teste("RRT Richard Mendes é equipe", _eh_membro_equipe("RRT Richard Mendes"), True)
    teste("Arthur é equipe", _eh_membro_equipe("Arthur"), True)
    teste("Wesley - SW7 NÃO é equipe", _eh_membro_equipe("Wesley - SW7"), False)
    teste("Suzana - SW7 NÃO é equipe", _eh_membro_equipe("Suzana - SW7"), False)
    teste("Gabriel Mello NÃO é equipe", _eh_membro_equipe("Gabriel Mello"), False)

    # ─── Teste 4: Detecção de mensagem de sistema ─────────────
    print("\n── Mensagens de Sistema ──")
    teste(
        "Transferência é sistema",
        _eh_mensagem_sistema(
            "Atendimento transferido por MARI FALAVIGNA para Bianca P",
            "MARI FALAVIGNA",
        ),
        True,
    )
    teste(
        "Mensagem normal NÃO é sistema",
        _eh_mensagem_sistema("No último que pagamos não tinha PIS COFINS", "Wesley - SW7"),
        False,
    )

    # ─── Teste 5: Parsing de timestamp ────────────────────────
    print("\n── Parsing de Timestamp ──")
    dt = _parsear_timestamp("16/04/2026 - 10:01")
    teste("Data parseada corretamente", dt, datetime(2026, 4, 16, 10, 1))
    teste("Timestamp inválido retorna None", _parsear_timestamp("inválido"), None)
    teste("Timestamp vazio retorna None", _parsear_timestamp(""), None)

    # ─── Teste 6: Extração nome do remetente ──────────────────
    print("\n── Nome do Remetente ──")
    teste(
        "Wesley - SW7 → Wesley",
        _extrair_nome_do_remetente("Wesley - SW7"),
        "Wesley",
    )
    teste(
        "Suzana - SW7 → Suzana",
        _extrair_nome_do_remetente("Suzana - SW7"),
        "Suzana",
    )
    teste(
        "Gabriel Mello (sem sufixo)",
        _extrair_nome_do_remetente("Gabriel Mello"),
        "Gabriel Mello",
    )

    # ─── Teste 7: Saudação detector ──────────────────────────
    print("\n── Detector de Saudação ──")
    teste("'obrigada' é saudação", _eh_saudacao("obrigada"), True)
    teste("'bom dia' é saudação", _eh_saudacao("bom dia"), True)
    teste("'ok' é saudação", _eh_saudacao("ok"), True)
    teste("Pergunta fiscal NÃO é saudação",
          _eh_saudacao("no último que pagamos não tinha pis cofins"), False)
    teste("'grande abraço' é saudação", _eh_saudacao("grande abraço"), True)

    # ─── Teste 8: Parsear conversa completa ───────────────────
    print("\n── Parsear Conversa ──")
    raw = [
        {
            "remetente": "Arthur",
            "texto": "Oi pessoal, boa noite. Segue guia DAS do mês com vencimento para o dia 20/04",
            "timestamp": "15/04/2026 - 20:00",
            "arquivo": "DAS SW7 03.2026.pdf",
        },
        {
            "remetente": "Wesley - SW7",
            "texto": "Boa noite. Aumentou a alíquota?",
            "timestamp": "15/04/2026 - 20:08",
        },
        {
            "remetente": "Wesley - SW7",
            "texto": "Bom dia",
            "timestamp": "16/04/2026 - 09:46",
            "flags": ["Editada"],
        },
        {
            "remetente": "Wesley - SW7",
            "texto": "No último que pagamos não tinha PIS COFINS",
            "timestamp": "16/04/2026 - 10:01",
        },
    ]

    conversa = parsear_conversa(raw, "RRT Contabilidade - Wesley e Suzana")
    teste("4 mensagens parseadas", len(conversa), 4)
    teste("Arthur é equipe", conversa[0]["eh_equipe"], True)
    teste("Wesley não é equipe", conversa[1]["eh_equipe"], False)
    teste("Wesley tem cliente_nome", conversa[1]["cliente_nome"], "Wesley")
    teste("Arquivo detectado", conversa[0]["eh_arquivo"], True)
    teste("Flag Editada preservada", "Editada" in conversa[2]["flags"], True)

    # ─── Teste 9: Identificar pendências ──────────────────────
    print("\n── Identificar Pendências ──")
    pendencias = identificar_pendencias(conversa, horas_limite=720)  # 30 dias p/ teste
    teste("Tem pendência (cliente sem resposta)", pendencias["tem_pendencia"], True)
    teste(
        "Pendência menciona PIS COFINS",
        any("PIS COFINS" in m["texto"] for m in pendencias["mensagens_pendentes"]),
        True,
    )
    teste(
        "Pendência menciona alíquota",
        any("alíquota" in m["texto"] for m in pendencias["mensagens_pendentes"]),
        True,
    )

    # ─── Teste 10: Conversa sem pendência (equipe respondeu) ──
    print("\n── Sem Pendência ──")
    raw_ok = [
        {
            "remetente": "Wesley - SW7",
            "texto": "quanto pago de DAS esse mês?",
            "timestamp": "16/04/2026 - 08:00",
        },
        {
            "remetente": "Adriana Russo",
            "texto": "Bom dia Wesley, o DAS deste mês é R$ 1.250,00",
            "timestamp": "16/04/2026 - 08:30",
        },
    ]
    conversa_ok = parsear_conversa(raw_ok, "RRT Contabilidade - Wesley e Suzana")
    pend_ok = identificar_pendencias(conversa_ok, horas_limite=720)
    teste("Sem pendência (equipe respondeu)", pend_ok["tem_pendencia"], False)

    # ─── Teste 11: Preparar para classificação ────────────────
    print("\n── Preparar para Classificação ──")
    para_class = preparar_para_classificacao(pendencias, "RRT Contabilidade - Wesley e Suzana")
    teste("Mensagens preparadas > 0", len(para_class) > 0, True)
    teste(
        "Formato correto (tem texto)",
        all("texto" in m for m in para_class),
        True,
    )
    teste(
        "Formato correto (tem grupo_nome)",
        all("grupo_nome" in m for m in para_class),
        True,
    )

    # ─── Teste 12: Sidebar parsing ────────────────────────────
    print("\n── Parsear Sidebar ──")
    sidebar_data = [
        {
            "grupo_nome": "RRT Contabilidade - Wesley e Suzana",
            "responsavel": "Adriana Russo",
            "ultima_mensagem": "No último que pagamos não tinha PIS COFINS",
            "tempo": "3 horas",
            "badge": 11,
            "tab": "em_atendimento",
        },
        {
            "grupo_nome": "RRT Contabilidade - Alice Arquiteta",
            "responsavel": "Adriana Russo",
            "ultima_mensagem": "Obrigada",
            "tempo": "3 horas",
            "badge": 6,
            "tab": "em_atendimento",
        },
        {
            "grupo_nome": "RRT Contabilidade - Helkia",
            "responsavel": "",
            "ultima_mensagem": "Boa tarde, obrigada.",
            "tempo": "27 minutos",
            "badge": 1,
            "tab": "pendente",
        },
    ]
    sidebar = parsear_sidebar(sidebar_data)
    teste("3 atendimentos parseados", len(sidebar), 3)
    # Pendente deve vir primeiro
    teste("Pendente vem primeiro", sidebar[0]["tab"], "pendente")
    teste("Helkia é pendente", sidebar[0]["cliente_nome"], "Helkia")
    # Wesley tem prioridade alta (tem termo fiscal + tempo > 30min)
    wesley = next(s for s in sidebar if s["cliente_nome"] == "Wesley e Suzana")
    teste("Wesley tem prioridade alta", wesley["prioridade"], "alta")
    # Alice tem prioridade baixa (só "Obrigada")
    alice = next(s for s in sidebar if s["cliente_nome"] == "Alice Arquiteta")
    teste("Alice tem prioridade baixa", alice["prioridade"], "baixa")

    # ─── Teste 13: Consolidador ───────────────────────────────
    print("\n── Consolidador ──")
    # Simular resultados do pipeline
    resultados_mock = [
        {
            "grupo_nome": "RRT Contabilidade - Wesley e Suzana",
            "cliente_nome": "Wesley e Suzana",
            "total_mensagens": 4,
            "tem_pendencia": True,
            "tempo_espera_minutos": 180,
            "mensagens_classificadas": [
                {"calculavel": True, "confianca": "alta", "fluxo_nome": "Tributário Federal"}
            ],
            "resumo_pendencias": "PIS COFINS",
            "pronto_para_ponte": True,
        },
        {
            "grupo_nome": "RRT Contabilidade - Alice Arquiteta",
            "cliente_nome": "Alice Arquiteta",
            "total_mensagens": 6,
            "tem_pendencia": False,
            "tempo_espera_minutos": None,
            "mensagens_classificadas": [],
            "resumo_pendencias": "Equipe já respondeu",
            "pronto_para_ponte": False,
        },
    ]
    consolidado = consolidar_atendimentos(resultados_mock)
    teste("Total grupos = 2", consolidado["total_grupos"], 2)
    teste("1 urgente", consolidado["prontos_para_ponte"], 1)
    teste("1 pendência total", consolidado["com_pendencia"], 1)
    teste("1 grupo OK", len(consolidado["grupos_ok"]), 1)

    # ─── Teste 14: Prioridade calculada ───────────────────────
    print("\n── Cálculo de Prioridade ──")
    teste(
        "Pergunta fiscal + tempo > 30min = alta",
        _calcular_prioridade("quanto pago de imposto?", 60, 3, "em_atendimento"),
        "alta",
    )
    teste(
        "Saudação genérica = baixa",
        _calcular_prioridade("Obrigada", 30, 1, "em_atendimento"),
        "baixa",
    )
    teste(
        "Pendente sempre alta",
        _calcular_prioridade("qualquer coisa", 5, 1, "pendente"),
        "alta",
    )
    teste(
        "Sem termo fiscal + tempo > 4h = media",
        _calcular_prioridade("preciso saber sobre meu caso", 300, 5, "em_atendimento"),
        "media",
    )

    # ─── Teste 15: Triagem de sidebar ────────────────────────
    print("\n── Triagem de Sidebar ──")
    sidebar_triagem = [
        {
            "grupo_nome_completo": "RRT Contabilidade - Helkia",
            "cliente_nome": "Helkia",
            "responsavel": "",
            "ultima_mensagem": "Boa tarde, obrigada.",
            "tempo_texto": "27 minutos",
            "minutos_estimados": 27,
            "badge": 1,
            "tab": "pendente",
            "prioridade": "alta",
        },
        {
            "grupo_nome_completo": "RRT Contabilidade - Wesley e Suzana",
            "cliente_nome": "Wesley e Suzana",
            "responsavel": "Adriana Russo",
            "ultima_mensagem": "No último que pagamos não tinha PIS COFINS",
            "tempo_texto": "3 horas",
            "minutos_estimados": 180,
            "badge": 11,
            "tab": "em_atendimento",
            "prioridade": "alta",
        },
        {
            "grupo_nome_completo": "RRT Contabilidade - Alice Arquiteta",
            "cliente_nome": "Alice Arquiteta",
            "responsavel": "Adriana Russo",
            "ultima_mensagem": "Obrigada",
            "tempo_texto": "3 horas",
            "minutos_estimados": 180,
            "badge": 6,
            "tab": "em_atendimento",
            "prioridade": "baixa",
        },
    ]
    triagem = triar_sidebar(sidebar_triagem)
    teste("Pendente Helkia deve abrir", "Helkia" in [a["cliente_nome"] for a in triagem["abrir"]], True)
    teste("Alta prioridade Wesley deve abrir", "Wesley e Suzana" in [a["cliente_nome"] for a in triagem["abrir"]], True)
    teste("Alice (baixa, saudação) pode pular", "Alice Arquiteta" in [a["cliente_nome"] for a in triagem["pular"]], True)
    teste("Motivos preenchidos", len(triagem["motivos"]) == 3, True)

    # ─── Teste 16: Triagem com limite ─────────────────────────
    print("\n── Triagem com Limite ──")
    triagem_limitada = triar_sidebar(sidebar_triagem, max_abrir=1)
    teste("Limite respeitado", len(triagem_limitada["abrir"]) <= 1, True)
    teste("Excedentes vão para pular", len(triagem_limitada["pular"]) >= 2, True)

    # ─── Teste 17: SLA ────────────────────────────────────────
    print("\n── Avaliação de SLA ──")
    sidebar_sla = [
        {
            "grupo_nome_completo": "RRT Contabilidade - Wesley e Suzana",
            "cliente_nome": "Wesley e Suzana",
            "minutos_estimados": 180,
            "prioridade": "alta",
            "tab": "em_atendimento",
        },
        {
            "grupo_nome_completo": "RRT Contabilidade - Helkia",
            "cliente_nome": "Helkia",
            "minutos_estimados": 150,
            "prioridade": "alta",
            "tab": "pendente",
        },
        {
            "grupo_nome_completo": "RRT Contabilidade - Retrapack",
            "cliente_nome": "Retrapack",
            "minutos_estimados": 300,
            "prioridade": "media",
            "tab": "em_atendimento",
        },
        {
            "grupo_nome_completo": "RRT Contabilidade - Alice",
            "cliente_nome": "Alice",
            "minutos_estimados": 30,
            "prioridade": "baixa",
            "tab": "em_atendimento",
        },
    ]
    sla = avaliar_sla(sidebar_sla)
    teste("Wesley (alta + 3h) é crítico", len(sla["criticos"]) >= 1, True)
    teste("Helkia (pendente + 2.5h) é crítico", any(c["cliente_nome"] == "Helkia" for c in sla["criticos"]), True)
    teste("Retrapack (media + 5h) é urgente", any(u["cliente_nome"] == "Retrapack" for u in sla["urgentes"]), True)
    teste("Alice (30min) é OK", any(o["cliente_nome"] == "Alice" for o in sla["ok"]), True)
    teste("Resumo SLA contém CRÍTICO", "CRÍTICO" in sla["resumo_sla"], True)

    # ─── Teste 18: Formatação SLA ─────────────────────────────
    print("\n── Formatação Tempo SLA ──")
    teste("30min", _formatar_tempo_sla(30), "30min")
    teste("150min = 2h30min", _formatar_tempo_sla(150), "2h30min")
    teste("60min = 1h", _formatar_tempo_sla(60), "1h")

    # ─── Resultado ────────────────────────────────────────────
    print(f"\n{'═' * 50}")
    print(f"  Leitor Gestta: {testes_ok}/{testes_total} testes passaram")
    print(f"{'═' * 50}\n")

    if testes_ok < testes_total:
        print(f"  ❌ {testes_total - testes_ok} teste(s) falharam!")
        sys.exit(1)
    else:
        print(f"  ✅ TODOS OS TESTES PASSARAM")

    return testes_ok, testes_total


if __name__ == "__main__":
    if "--teste" in sys.argv:
        rodar_testes()
    else:
        print("Uso: python3 leitor_gestta.py --teste")
        print("Ou importe: from leitor_gestta import pipeline_gestta_completo")
