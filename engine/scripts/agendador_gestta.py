#!/usr/bin/env python3
"""
Agendador Gestta — Scan Automático de Atendimentos v4.4

Módulo para scans automáticos do portal Gestta. Gera instruções estruturadas
para o Claude in Chrome executar, processa os resultados, e produz relatório
priorizado com SLA para o escritório.

Uso:
    python3 agendador_gestta.py --teste

Importação:
    from agendador_gestta import (
        gerar_instrucoes_scan, processar_resultado_scan,
        comparar_scans, gerar_relatorio_matinal
    )

Fluxo do scheduled task:
    1. agendador gera instruções de scan (quais passos executar no Chrome)
    2. Claude in Chrome executa os passos no Gestta
    3. agendador processa os resultados e gera relatório
    4. relatório é apresentado ao contador com SLA + prioridades
"""

import sys
import json
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════

GESTTA_URL = "https://app.gestta.com.br/attendance/#/chat/ongoing"
GESTTA_PENDENTES_URL = "https://app.gestta.com.br/attendance/#/chat/pending"

# ═══════════════════════════════════════════════════════════════
# GERADOR DE INSTRUÇÕES (para o scheduled task prompt)
# ═══════════════════════════════════════════════════════════════

def gerar_instrucoes_scan(scan_anterior=None, max_grupos=10):
    """
    Gera instruções estruturadas para o scan do Gestta.

    Estas instruções serão incluídas no prompt do scheduled task
    para que o Claude in Chrome saiba exatamente o que fazer.

    Args:
        scan_anterior: dict | None — resultado do scan anterior (para comparação)
        max_grupos: int — máximo de grupos para abrir (default 10)

    Returns:
        dict:
        {
            "etapas": list[dict],      # passos sequenciais
            "url_inicial": str,
            "max_grupos": int,
            "scan_anterior_id": str | None,
        }
    """
    etapas = [
        {
            "numero": 1,
            "acao": "navegar",
            "descricao": "Navegar para a aba Pendentes do Gestta",
            "url": GESTTA_PENDENTES_URL,
            "extrair": "sidebar_pendentes",
            "campos": ["grupo_nome", "ultima_mensagem", "tempo", "badge"],
        },
        {
            "numero": 2,
            "acao": "navegar",
            "descricao": "Navegar para a aba Em Atendimento",
            "url": GESTTA_URL,
            "extrair": "sidebar_em_atendimento",
            "campos": ["grupo_nome", "responsavel", "ultima_mensagem", "tempo", "badge"],
        },
        {
            "numero": 3,
            "acao": "triar",
            "descricao": "Usar triar_sidebar() para decidir quais grupos abrir",
            "funcao": "leitor_gestta.triar_sidebar",
            "max_abrir": max_grupos,
        },
        {
            "numero": 4,
            "acao": "ler_conversas",
            "descricao": "Para cada grupo triado como 'abrir': clicar, ler mensagens via read_page, extrair últimas 10 mensagens",
            "campos_mensagem": ["remetente", "texto", "timestamp", "flags", "arquivo"],
        },
        {
            "numero": 5,
            "acao": "processar",
            "descricao": "Alimentar dados em processar_resultado_scan()",
            "funcao": "agendador_gestta.processar_resultado_scan",
        },
        {
            "numero": 6,
            "acao": "relatorio",
            "descricao": "Gerar e apresentar relatório com gerar_relatorio_matinal()",
            "funcao": "agendador_gestta.gerar_relatorio_matinal",
        },
    ]

    return {
        "etapas": etapas,
        "url_inicial": GESTTA_PENDENTES_URL,
        "max_grupos": max_grupos,
        "scan_anterior_id": scan_anterior.get("scan_id") if scan_anterior else None,
    }


# ═══════════════════════════════════════════════════════════════
# PROCESSADOR DE RESULTADO DE SCAN
# ═══════════════════════════════════════════════════════════════

def processar_resultado_scan(dados_sidebar, dados_conversas, tab_pendentes=None):
    """
    Processa os dados brutos coletados do Gestta em um scan.

    Args:
        dados_sidebar: list[dict] — atendimentos da aba Em Atendimento
        dados_conversas: dict[str, list[dict]] — grupo_nome → mensagens_raw
        tab_pendentes: list[dict] | None — atendimentos da aba Pendentes

    Returns:
        dict:
        {
            "scan_id": str,
            "timestamp": str,
            "total_em_atendimento": int,
            "total_pendentes": int,
            "atendimentos_triados": dict,   # output de triar_sidebar
            "sla": dict,                     # output de avaliar_sla
            "resultados_pipeline": list[dict], # output de processar cada conversa
            "resumo": str,
        }
    """
    from leitor_gestta import (
        parsear_sidebar, triar_sidebar, avaliar_sla,
    )
    from orquestrador_gestta import processar_atendimento

    scan_id = datetime.now().strftime("scan_%Y%m%d_%H%M%S")
    timestamp = datetime.now().isoformat()

    # Combinar pendentes e em_atendimento
    todos_sidebar = []

    if tab_pendentes:
        for item in tab_pendentes:
            item["tab"] = "pendente"
        todos_sidebar.extend(tab_pendentes)

    for item in dados_sidebar:
        item["tab"] = "em_atendimento"
    todos_sidebar.extend(dados_sidebar)

    # Parsear sidebar
    atendimentos = parsear_sidebar(todos_sidebar)

    # Triagem
    triagem = triar_sidebar(atendimentos)

    # SLA
    sla = avaliar_sla(atendimentos)

    # Processar conversas para os grupos que foram abertos
    resultados = []
    for grupo in triagem["abrir"]:
        nome = grupo["grupo_nome_completo"]
        if nome in dados_conversas:
            try:
                resultado = processar_atendimento(
                    mensagens_raw=dados_conversas[nome],
                    grupo_nome=nome,
                    horas_limite=48,
                )
                resultados.append(resultado)
            except Exception as e:
                resultados.append({
                    "grupo_nome": nome,
                    "cliente_nome": grupo.get("cliente_nome", ""),
                    "tem_pendencia": False,
                    "erro": str(e),
                    "resumo": f"Erro: {str(e)[:80]}",
                })

    # Resumo
    n_criticos = len(sla["criticos"])
    n_pendencias = sum(1 for r in resultados if r.get("tem_pendencia"))
    n_prontos = sum(
        1 for r in resultados
        if any(
            p.get("rascunho", {}).get("status") == "pronto"
            for p in r.get("pendencias", [])
        )
    )

    partes = []
    if n_criticos:
        partes.append(f"🔴 {n_criticos} SLA crítico(s)")
    if n_prontos:
        partes.append(f"🟢 {n_prontos} rascunho(s) pronto(s)")
    if n_pendencias - n_prontos > 0:
        partes.append(f"🟡 {n_pendencias - n_prontos} pendência(s) manual(is)")

    return {
        "scan_id": scan_id,
        "timestamp": timestamp,
        "total_em_atendimento": len(dados_sidebar),
        "total_pendentes": len(tab_pendentes) if tab_pendentes else 0,
        "atendimentos_triados": triagem,
        "sla": sla,
        "resultados_pipeline": resultados,
        "resumo": " | ".join(partes) if partes else "✅ Tudo em dia",
    }


# ═══════════════════════════════════════════════════════════════
# COMPARADOR DE SCANS (detecta mudanças entre rodadas)
# ═══════════════════════════════════════════════════════════════

def comparar_scans(scan_atual, scan_anterior):
    """
    Compara dois scans consecutivos para detectar mudanças.

    Args:
        scan_atual: dict — output de processar_resultado_scan()
        scan_anterior: dict — output de processar_resultado_scan() anterior

    Returns:
        dict:
        {
            "novos_criticos": list[str],     # clientes que entraram em SLA crítico
            "resolvidos": list[str],          # clientes que saíram de pendência
            "novas_mensagens": list[str],     # clientes com mensagens novas
            "piorou_sla": list[str],          # clientes cujo SLA piorou
            "sem_mudanca": bool,
            "resumo_delta": str,
        }
    """
    if not scan_anterior:
        return {
            "novos_criticos": [],
            "resolvidos": [],
            "novas_mensagens": [],
            "piorou_sla": [],
            "sem_mudanca": True,
            "resumo_delta": "Primeiro scan — sem comparação",
        }

    # Clientes críticos anterior vs atual
    criticos_anterior = {c["cliente_nome"] for c in scan_anterior.get("sla", {}).get("criticos", [])}
    criticos_atual = {c["cliente_nome"] for c in scan_atual.get("sla", {}).get("criticos", [])}

    novos_criticos = list(criticos_atual - criticos_anterior)

    # Pendências anterior vs atual
    pendentes_anterior = {
        r["cliente_nome"]
        for r in scan_anterior.get("resultados_pipeline", [])
        if r.get("tem_pendencia")
    }
    pendentes_atual = {
        r["cliente_nome"]
        for r in scan_atual.get("resultados_pipeline", [])
        if r.get("tem_pendencia")
    }

    resolvidos = list(pendentes_anterior - pendentes_atual)
    novas_mensagens = list(pendentes_atual - pendentes_anterior)

    # SLA piorou
    sla_anterior = {}
    for categoria in ["criticos", "urgentes", "atencao", "ok"]:
        for item in scan_anterior.get("sla", {}).get(categoria, []):
            sla_anterior[item["cliente_nome"]] = categoria

    piorou = []
    ordem = {"ok": 0, "atencao": 1, "urgentes": 2, "criticos": 3}
    for categoria in ["criticos", "urgentes", "atencao"]:
        for item in scan_atual.get("sla", {}).get(categoria, []):
            nome = item["cliente_nome"]
            cat_anterior = sla_anterior.get(nome, "ok")
            if ordem.get(categoria, 0) > ordem.get(cat_anterior, 0):
                piorou.append(nome)

    sem_mudanca = not novos_criticos and not resolvidos and not novas_mensagens and not piorou

    partes = []
    if novos_criticos:
        partes.append(f"🆘 Novo(s) crítico(s): {', '.join(novos_criticos)}")
    if resolvidos:
        partes.append(f"✅ Resolvido(s): {', '.join(resolvidos)}")
    if novas_mensagens:
        partes.append(f"📩 Nova(s) pendência(s): {', '.join(novas_mensagens)}")
    if piorou:
        partes.append(f"⬆️ SLA piorou: {', '.join(piorou)}")

    return {
        "novos_criticos": novos_criticos,
        "resolvidos": resolvidos,
        "novas_mensagens": novas_mensagens,
        "piorou_sla": piorou,
        "sem_mudanca": sem_mudanca,
        "resumo_delta": " | ".join(partes) if partes else "Sem mudanças",
    }


# ═══════════════════════════════════════════════════════════════
# GERADOR DE RELATÓRIO MATINAL
# ═══════════════════════════════════════════════════════════════

def gerar_relatorio_matinal(scan_resultado, scan_anterior=None):
    """
    Gera relatório formatado para o contador revisar no início do dia.

    Args:
        scan_resultado: dict — output de processar_resultado_scan()
        scan_anterior: dict | None — scan anterior para comparação

    Returns:
        str — relatório formatado
    """
    r = scan_resultado
    sla = r.get("sla", {})
    delta = comparar_scans(r, scan_anterior) if scan_anterior else None

    linhas = []
    linhas.append("╔═══════════════════════════════════════════════════════╗")
    linhas.append("║  📋 SCAN GESTTA — RELATÓRIO DE ATENDIMENTOS          ║")
    linhas.append("╚═══════════════════════════════════════════════════════╝")
    linhas.append(f"  Scan ID: {r.get('scan_id', '?')}")
    linhas.append(f"  Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    linhas.append(f"  Em atendimento: {r.get('total_em_atendimento', 0)} | Pendentes: {r.get('total_pendentes', 0)}")
    linhas.append(f"  SLA: {sla.get('resumo_sla', 'N/A')}")

    if delta and not delta["sem_mudanca"]:
        linhas.append(f"  Mudanças: {delta['resumo_delta']}")

    linhas.append("")

    # Seção: SLA Críticos
    criticos = sla.get("criticos", [])
    if criticos:
        linhas.append("🔴 SLA CRÍTICO — AÇÃO IMEDIATA:")
        linhas.append("─" * 50)
        for c in criticos:
            linhas.append(f"  👤 {c.get('cliente_nome', '?')}")
            linhas.append(f"     ⏱️  {c.get('sla_motivo', '')}")
            linhas.append(f"     📩 \"{c.get('ultima_mensagem', '')[:80]}\"")
            linhas.append("")

    # Seção: Urgentes
    urgentes = sla.get("urgentes", [])
    if urgentes:
        linhas.append("🟠 URGENTE:")
        linhas.append("─" * 50)
        for u in urgentes:
            linhas.append(f"  👤 {u.get('cliente_nome', '?')} — {u.get('sla_motivo', '')}")
            linhas.append(f"     📩 \"{u.get('ultima_mensagem', '')[:80]}\"")
            linhas.append("")

    # Seção: Resultados do pipeline
    resultados = r.get("resultados_pipeline", [])
    prontos = [
        res for res in resultados
        if any(
            p.get("rascunho", {}).get("status") == "pronto"
            for p in res.get("pendencias", [])
        )
    ]
    if prontos:
        linhas.append("🟢 RASCUNHOS PRONTOS PARA REVISÃO:")
        linhas.append("─" * 50)
        for res in prontos:
            linhas.append(f"  👤 {res.get('cliente_nome', '?')}")
            for p in res.get("pendencias", []):
                if p.get("rascunho", {}).get("status") == "pronto":
                    linhas.append(f"     📩 \"{p.get('texto_original', '')[:80]}\"")
                    rascunho = p.get("rascunho", {}).get("texto_rascunho", "")
                    if rascunho:
                        for linha_r in rascunho.split("\n")[:3]:
                            linhas.append(f"     ✏️  {linha_r}")
                    linhas.append(f"     ⚠️  REQUER REVISÃO antes de enviar")
            linhas.append("")

    # Seção: Pendências manuais
    manuais = [
        res for res in resultados
        if res.get("tem_pendencia") and res not in prontos
    ]
    if manuais:
        linhas.append("🟡 PENDÊNCIAS — RESPOSTA MANUAL:")
        linhas.append("─" * 50)
        for res in manuais:
            linhas.append(f"  👤 {res.get('cliente_nome', '?')} — {res.get('resumo', '')[:80]}")
        linhas.append("")

    # Seção: Atenção (SLA amarelo)
    atencao = sla.get("atencao", [])
    if atencao:
        linhas.append(f"🟡 ATENÇÃO ({len(atencao)} grupos >8h):")
        for a in atencao:
            linhas.append(f"  • {a.get('cliente_nome', '?')} — {a.get('sla_motivo', '')}")
        linhas.append("")

    # Triagem info
    triagem = r.get("atendimentos_triados", {})
    n_pulados = len(triagem.get("pular", []))
    if n_pulados:
        linhas.append(f"ℹ️  {n_pulados} grupo(s) ignorado(s) (equipe já respondeu / saudação)")
        linhas.append("")

    linhas.append("═" * 53)
    linhas.append("⚠️  Todos os rascunhos requerem revisão humana.")
    linhas.append("═" * 53)

    return "\n".join(linhas)


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

    def teste_contem(descricao, texto, substring):
        nonlocal testes_ok, testes_total
        testes_total += 1
        if substring in texto:
            testes_ok += 1
            print(f"  ✅ PASSOU: {descricao}")
        else:
            print(f"  ❌ FALHOU: {descricao}")
            print(f"     Esperado que contenha: '{substring}'")
            print(f"     Texto: {texto[:200]}")

    print("\n🧪 Agendador Gestta — Testes\n")

    # ─── Teste 1: Geração de instruções ───────────────────────
    print("── Instruções de Scan ──")
    instrucoes = gerar_instrucoes_scan()
    teste("6 etapas geradas", len(instrucoes["etapas"]), 6)
    teste("URL inicial é Pendentes", instrucoes["url_inicial"], GESTTA_PENDENTES_URL)
    teste("Max grupos default = 10", instrucoes["max_grupos"], 10)
    teste("Sem scan anterior", instrucoes["scan_anterior_id"], None)

    # Com scan anterior
    instrucoes2 = gerar_instrucoes_scan(scan_anterior={"scan_id": "scan_20260416_120000"})
    teste("Scan anterior referenciado", instrucoes2["scan_anterior_id"], "scan_20260416_120000")

    # ─── Teste 2: Processar resultado de scan ─────────────────
    print("\n── Processar Resultado ──")
    sidebar_em_atendimento = [
        {
            "grupo_nome": "RRT Contabilidade - Wesley e Suzana",
            "responsavel": "Adriana Russo",
            "ultima_mensagem": "No último que pagamos não tinha PIS COFINS",
            "tempo": "3 horas",
            "badge": 11,
        },
        {
            "grupo_nome": "RRT Contabilidade - Alice Arquiteta",
            "responsavel": "Adriana Russo",
            "ultima_mensagem": "Obrigada",
            "tempo": "3 horas",
            "badge": 6,
        },
    ]
    tab_pendentes = [
        {
            "grupo_nome": "RRT Contabilidade - Helkia",
            "responsavel": "",
            "ultima_mensagem": "Boa tarde, obrigada.",
            "tempo": "27 minutos",
            "badge": 1,
        },
    ]
    conversas = {
        "RRT Contabilidade - Wesley e Suzana": [
            {
                "remetente": "Arthur",
                "texto": "Segue guia DAS do mês",
                "timestamp": "15/04/2026 - 20:00",
            },
            {
                "remetente": "Wesley - SW7",
                "texto": "No último que pagamos não tinha PIS COFINS",
                "timestamp": "16/04/2026 - 10:01",
            },
        ],
        "RRT Contabilidade - Helkia": [
            {
                "remetente": "Cliente Helkia",
                "texto": "Boa tarde, obrigada.",
                "timestamp": "16/04/2026 - 12:00",
            },
        ],
    }

    resultado = processar_resultado_scan(
        dados_sidebar=sidebar_em_atendimento,
        dados_conversas=conversas,
        tab_pendentes=tab_pendentes,
    )

    teste("Scan ID gerado", resultado["scan_id"].startswith("scan_"), True)
    teste("Total em atendimento = 2", resultado["total_em_atendimento"], 2)
    teste("Total pendentes = 1", resultado["total_pendentes"], 1)
    teste("SLA presente", "resumo_sla" in resultado["sla"], True)
    teste("Triagem presente", "abrir" in resultado["atendimentos_triados"], True)
    teste("Resultados pipeline > 0", len(resultado["resultados_pipeline"]) > 0, True)

    # ─── Teste 3: Comparar scans ──────────────────────────────
    print("\n── Comparar Scans ──")

    # Primeiro scan (sem anterior)
    delta_primeiro = comparar_scans(resultado, None)
    teste("Primeiro scan sem mudanças", delta_primeiro["sem_mudanca"], True)
    teste("Resumo indica primeiro", "Primeiro scan" in delta_primeiro["resumo_delta"], True)

    # Segundo scan com mudanças
    scan_anterior_mock = {
        "sla": {
            "criticos": [],
            "urgentes": [],
            "atencao": [],
            "ok": [{"cliente_nome": "Wesley e Suzana"}, {"cliente_nome": "Helkia"}],
        },
        "resultados_pipeline": [],
    }
    delta = comparar_scans(resultado, scan_anterior_mock)
    teste("Detecta novos críticos", len(delta["novos_criticos"]) > 0, True)
    teste("Detecta piora SLA", len(delta["piorou_sla"]) > 0, True)
    teste("Não é sem mudança", delta["sem_mudanca"], False)

    # ─── Teste 4: Relatório matinal ───────────────────────────
    print("\n── Relatório Matinal ──")
    relatorio = gerar_relatorio_matinal(resultado)
    teste_contem("Cabeçalho presente", relatorio, "SCAN GESTTA")
    teste_contem("Scan ID no relatório", relatorio, "scan_")
    teste_contem("SLA no relatório", relatorio, "SLA")
    teste_contem("Aviso revisão humana", relatorio, "revisão humana")
    teste("Relatório não vazio", len(relatorio) > 200, True)

    # Com comparação
    relatorio_com_delta = gerar_relatorio_matinal(resultado, scan_anterior_mock)
    teste_contem("Delta de mudanças presente", relatorio_com_delta, "Mudanças:")

    # ─── Teste 5: Scan sem pendências ─────────────────────────
    print("\n── Scan Sem Pendências ──")
    resultado_ok = processar_resultado_scan(
        dados_sidebar=[{
            "grupo_nome": "RRT Contabilidade - Alice Arquiteta",
            "responsavel": "Adriana Russo",
            "ultima_mensagem": "Obrigada",
            "tempo": "3 horas",
            "badge": 6,
        }],
        dados_conversas={},
        tab_pendentes=[],
    )
    teste("Sem pendentes = 0", resultado_ok["total_pendentes"], 0)
    teste("Resumo positivo", "✅" in resultado_ok["resumo"] or len(resultado_ok["resultados_pipeline"]) == 0, True)

    # ─── Resultado ────────────────────────────────────────────
    print(f"\n{'═' * 50}")
    print(f"  Agendador Gestta: {testes_ok}/{testes_total} testes passaram")
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
        print("Uso: python3 agendador_gestta.py --teste")
        print("Ou importe: from agendador_gestta import gerar_instrucoes_scan")
