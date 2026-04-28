#!/usr/bin/env python3
"""
sugestoes_proativas.py — Gerador de Sugestões Proativas
RRT Group Contador v5.0 — Aprendizado

Gera sugestões proativas baseadas em:
  - Calendário fiscal (prazos e obrigações)
  - Histórico do cliente (temas recorrentes, padrões)
  - Padrões de correção (onde reforçar validação)
  - Sazonalidade (antecipar picos de demanda)

Tipos de sugestão:
  - ALERTA_PRAZO: prazo fiscal se aproximando
  - LEMBRETE_RECORRENTE: tema que o cliente sempre pergunta neste período
  - VALIDACAO_REFORÇADA: fluxo com alta taxa de erro — pedir confirmação extra
  - ANTECIPACAO: preparar material/cálculo antes que o cliente peça
  - OPORTUNIDADE: regime ou benefício que o cliente pode não conhecer
"""

from datetime import datetime, timedelta
from typing import Optional


# ── Prazos fiscais fixos (dia do mês) ───────────────────────────────────────

PRAZOS_MENSAIS = [
    {"dia": 7, "descricao": "FGTS (GRF)", "regimes": ["simples", "presumido", "real"]},
    {"dia": 15, "descricao": "INSS (GPS) — contribuinte individual", "regimes": ["simples", "presumido", "real"]},
    {"dia": 20, "descricao": "DAS Simples Nacional (PGDAS-D)", "regimes": ["simples"]},
    {"dia": 20, "descricao": "DAS-MEI", "regimes": ["mei"]},
    {"dia": 20, "descricao": "INSS (GPS) — empregadores", "regimes": ["presumido", "real"]},
    {"dia": 20, "descricao": "PIS/COFINS (DARF)", "regimes": ["presumido", "real"]},
    {"dia": 25, "descricao": "ICMS (GIA/EFD)", "regimes": ["simples_sublimite", "presumido", "real"]},
    {"dia": 25, "descricao": "ISS (guia municipal)", "regimes": ["simples", "presumido", "real"]},
]

PRAZOS_ANUAIS = [
    {"mes": 2, "dia": 28, "descricao": "DIRF — Declaração do Imposto de Renda Retido na Fonte"},
    {"mes": 2, "dia": 28, "descricao": "Informe de Rendimentos (entrega ao beneficiário)"},
    {"mes": 3, "dia": 15, "descricao": "IRPF — Início do período de entrega"},
    {"mes": 3, "dia": 31, "descricao": "DEFIS — Declaração Simples Nacional"},
    {"mes": 5, "dia": 31, "descricao": "IRPF — Prazo final de entrega"},
    {"mes": 6, "dia": 30, "descricao": "ECD — Escrituração Contábil Digital"},
    {"mes": 7, "dia": 31, "descricao": "ECF — Escrituração Contábil e Fiscal"},
    {"mes": 11, "dia": 30, "descricao": "13° salário — 1ª parcela (prazo)"},
    {"mes": 12, "dia": 20, "descricao": "13° salário — 2ª parcela (prazo)"},
    {"mes": 12, "dia": 30, "descricao": "Fechamento anual — ajustes e provisões"},
]


def gerar_alertas_prazo(
    data_referencia: Optional[str] = None,
    regime: Optional[str] = None,
    dias_antecedencia: int = 5,
) -> list:
    """
    Gera alertas de prazos fiscais próximos.

    Args:
        data_referencia: Data ISO (default: hoje)
        regime: Filtrar por regime ('simples', 'presumido', 'real', 'mei')
        dias_antecedencia: Dias de antecedência para alertar

    Returns:
        lista de alertas com tipo, prazo, descrição, urgência
    """
    if data_referencia:
        try:
            hoje = datetime.strptime(data_referencia[:10], "%Y-%m-%d")
        except ValueError:
            hoje = datetime.now()
    else:
        hoje = datetime.now()

    limite = hoje + timedelta(days=dias_antecedencia)
    alertas = []

    # Prazos mensais
    for prazo in PRAZOS_MENSAIS:
        if regime and regime not in prazo["regimes"]:
            continue

        # Calcular data do prazo no mês atual
        try:
            data_prazo = hoje.replace(day=prazo["dia"])
        except ValueError:
            # Mês com menos dias (ex: fev 28)
            continue

        if hoje <= data_prazo <= limite:
            dias_restantes = (data_prazo - hoje).days
            urgencia = "critico" if dias_restantes <= 1 else "urgente" if dias_restantes <= 3 else "atencao"
            alertas.append({
                "tipo": "ALERTA_PRAZO",
                "descricao": prazo["descricao"],
                "data_prazo": data_prazo.strftime("%Y-%m-%d"),
                "dias_restantes": dias_restantes,
                "urgencia": urgencia,
                "regimes": prazo["regimes"],
                "periodicidade": "mensal",
            })

    # Prazos anuais
    for prazo in PRAZOS_ANUAIS:
        try:
            data_prazo = hoje.replace(month=prazo["mes"], day=prazo["dia"])
        except ValueError:
            continue

        if hoje <= data_prazo <= limite:
            dias_restantes = (data_prazo - hoje).days
            urgencia = "critico" if dias_restantes <= 2 else "urgente" if dias_restantes <= 7 else "atencao"
            alertas.append({
                "tipo": "ALERTA_PRAZO",
                "descricao": prazo["descricao"],
                "data_prazo": data_prazo.strftime("%Y-%m-%d"),
                "dias_restantes": dias_restantes,
                "urgencia": urgencia,
                "periodicidade": "anual",
            })

    return sorted(alertas, key=lambda x: x["dias_restantes"])


def gerar_lembretes_recorrentes(
    interacoes_cliente: list,
    mes_referencia: Optional[int] = None,
) -> list:
    """
    Gera lembretes baseados em temas que o cliente pergunta recorrentemente.

    Args:
        interacoes_cliente: lista de interações do cliente
        mes_referencia: mês para verificar recorrência (default: mês atual)

    Returns:
        lista de lembretes com tema, frequência, última vez
    """
    if not interacoes_cliente:
        return []

    mes_ref = mes_referencia or datetime.now().month
    lembretes = []

    # Agrupar por mês e tag
    tags_por_mes = {}
    for inter in interacoes_cliente:
        ts = inter.get("timestamp", "")
        if len(ts) < 7:
            continue
        try:
            mes = int(ts[5:7])
        except (ValueError, IndexError):
            continue
        for tag in inter.get("tags", []):
            tag_lower = tag.lower()
            if tag_lower not in tags_por_mes:
                tags_por_mes[tag_lower] = {}
            tags_por_mes[tag_lower][mes] = tags_por_mes[tag_lower].get(mes, 0) + 1

    # Encontrar tags que aparecem no mês de referência em múltiplos anos/ocorrências
    for tag, meses in tags_por_mes.items():
        if mes_ref in meses and meses[mes_ref] >= 2:
            # Encontrar última interação com essa tag
            ultima = None
            for inter in reversed(interacoes_cliente):
                if tag in [t.lower() for t in inter.get("tags", [])]:
                    ultima = inter.get("timestamp", "")[:10]
                    break

            lembretes.append({
                "tipo": "LEMBRETE_RECORRENTE",
                "tema": tag,
                "frequencia_no_mes": meses[mes_ref],
                "total_historico": sum(meses.values()),
                "ultima_interacao": ultima,
                "sugestao": f"Cliente costuma perguntar sobre '{tag}' neste período. Antecipar preparação.",
            })

    return sorted(lembretes, key=lambda x: x["frequencia_no_mes"], reverse=True)


def gerar_validacoes_reforcadas(padroes_correcao: dict) -> list:
    """
    Gera alertas de validação reforçada para fluxos com alta taxa de erro.

    Args:
        padroes_correcao: output de detector_padroes.detectar_padroes_correcao()

    Returns:
        lista de validações com fluxo, taxa, recomendação
    """
    validacoes = []

    for fluxo, dados in padroes_correcao.get("fluxos_problematicos", []):
        if dados["taxa_pct"] >= 20 and dados["total"] >= 3:
            nivel = "critico" if dados["taxa_pct"] >= 50 else "alto" if dados["taxa_pct"] >= 35 else "moderado"
            validacoes.append({
                "tipo": "VALIDACAO_REFORCADA",
                "fluxo": fluxo,
                "taxa_erro_pct": dados["taxa_pct"],
                "erros": dados["erros"],
                "total": dados["total"],
                "nivel": nivel,
                "recomendacao": (
                    f"Fluxo '{fluxo}' tem {dados['taxa_pct']}% de erro. "
                    f"Solicitar confirmação extra do contador antes de enviar."
                    if nivel != "critico"
                    else f"Fluxo '{fluxo}' tem {dados['taxa_pct']}% de erro. "
                    f"BLOQUEAR envio automático — exigir revisão manual completa."
                ),
            })

    return validacoes


def gerar_antecipacoes(
    interacoes_cliente: list,
    regime: Optional[str] = None,
    mes_referencia: Optional[int] = None,
) -> list:
    """
    Sugere cálculos/materiais para preparar proativamente.

    Args:
        interacoes_cliente: interações do cliente
        regime: regime tributário do cliente
        mes_referencia: mês de referência (default: próximo mês)

    Returns:
        lista de antecipações com ação, motivo, prioridade
    """
    mes_ref = mes_referencia or ((datetime.now().month % 12) + 1)
    antecipacoes = []

    # Antecipações baseadas no calendário fiscal + regime
    antecipacoes_calendario = {
        3: [
            {"acao": "Preparar checklist IRPF para clientes PF", "regime_filtro": None, "prioridade": "alta"},
            {"acao": "Coletar informes de rendimentos pendentes", "regime_filtro": None, "prioridade": "alta"},
        ],
        4: [
            {"acao": "Rodar simulador IRPF completa × simplificada para todos os PFs", "regime_filtro": None, "prioridade": "alta"},
        ],
        5: [
            {"acao": "Verificar DEFIS pendentes (Simples Nacional)", "regime_filtro": "simples", "prioridade": "alta"},
            {"acao": "Última revisão IRPF antes do prazo", "regime_filtro": None, "prioridade": "critica"},
        ],
        6: [
            {"acao": "Preparar ECD — levantar balancetes", "regime_filtro": "real", "prioridade": "alta"},
        ],
        7: [
            {"acao": "Preparar ECF — confrontar dados", "regime_filtro": "real", "prioridade": "alta"},
        ],
        10: [
            {"acao": "Simular opção Simples Nacional para próximo ano", "regime_filtro": "simples", "prioridade": "media"},
            {"acao": "Rodar comparativo de regimes para clientes em dúvida", "regime_filtro": None, "prioridade": "media"},
        ],
        11: [
            {"acao": "Calcular 1ª parcela 13° para todos CLT", "regime_filtro": None, "prioridade": "alta"},
        ],
        12: [
            {"acao": "Calcular 2ª parcela 13° (prazo 20/12)", "regime_filtro": None, "prioridade": "critica"},
            {"acao": "Planejar fechamento anual", "regime_filtro": None, "prioridade": "alta"},
        ],
    }

    for ant in antecipacoes_calendario.get(mes_ref, []):
        if ant["regime_filtro"] and regime and ant["regime_filtro"] != regime:
            continue
        antecipacoes.append({
            "tipo": "ANTECIPACAO",
            "acao": ant["acao"],
            "mes_alvo": mes_ref,
            "prioridade": ant["prioridade"],
            "fonte": "calendario_fiscal",
        })

    # Antecipações baseadas em histórico do cliente
    if interacoes_cliente:
        tags_mes = {}
        for inter in interacoes_cliente:
            ts = inter.get("timestamp", "")
            if len(ts) < 7:
                continue
            try:
                mes = int(ts[5:7])
            except (ValueError, IndexError):
                continue
            if mes == mes_ref:
                for tag in inter.get("tags", []):
                    tags_mes[tag.lower()] = tags_mes.get(tag.lower(), 0) + 1

        for tag, count in sorted(tags_mes.items(), key=lambda x: x[1], reverse=True)[:3]:
            if count >= 2:
                antecipacoes.append({
                    "tipo": "ANTECIPACAO",
                    "acao": f"Preparar material sobre '{tag}' — cliente pergunta {count}x neste mês historicamente",
                    "mes_alvo": mes_ref,
                    "prioridade": "media",
                    "fonte": "historico_cliente",
                })

    return antecipacoes


def gerar_sugestoes_consolidadas(
    interacoes_cliente: list,
    padroes_correcao: Optional[dict] = None,
    regime: Optional[str] = None,
    data_referencia: Optional[str] = None,
    dias_antecedencia: int = 7,
) -> dict:
    """
    Consolida todas as sugestões proativas para um cliente.

    Returns:
        dict com alertas, lembretes, validações, antecipações, resumo
    """
    alertas = gerar_alertas_prazo(data_referencia, regime, dias_antecedencia)
    lembretes = gerar_lembretes_recorrentes(interacoes_cliente)
    validacoes = gerar_validacoes_reforcadas(padroes_correcao or {})
    antecipacoes = gerar_antecipacoes(interacoes_cliente, regime)

    total = len(alertas) + len(lembretes) + len(validacoes) + len(antecipacoes)
    criticos = (
        len([a for a in alertas if a.get("urgencia") == "critico"])
        + len([v for v in validacoes if v.get("nivel") == "critico"])
        + len([a for a in antecipacoes if a.get("prioridade") == "critica"])
    )

    return {
        "alertas_prazo": alertas,
        "lembretes_recorrentes": lembretes,
        "validacoes_reforcadas": validacoes,
        "antecipacoes": antecipacoes,
        "resumo": {
            "total_sugestoes": total,
            "criticos": criticos,
            "alertas": len(alertas),
            "lembretes": len(lembretes),
            "validacoes": len(validacoes),
            "antecipacoes": len(antecipacoes),
        },
    }


# ── Testes ─────────────────────────────────────────────────────────────────────

def _rodar_testes():
    testes_passou = 0
    testes_falhou = 0

    def ok(condicao, descricao):
        nonlocal testes_passou, testes_falhou
        if condicao:
            testes_passou += 1
        else:
            testes_falhou += 1
            print(f"  FALHOU: {descricao}")

    # ── Teste 1: Alertas de prazo — DAS dia 20 ──
    alertas = gerar_alertas_prazo("2026-04-16", regime="simples", dias_antecedencia=5)
    das_alerta = [a for a in alertas if "DAS Simples" in a["descricao"]]
    ok(len(das_alerta) == 1, "Prazo DAS: encontrado (16→20 = 4 dias)")
    ok(das_alerta[0]["dias_restantes"] == 4, "Prazo DAS: 4 dias restantes")
    ok(das_alerta[0]["urgencia"] == "atencao", "Prazo DAS: urgência atenção")

    # ── Teste 2: Alertas filtrados por regime ──
    alertas_mei = gerar_alertas_prazo("2026-04-16", regime="mei", dias_antecedencia=5)
    das_mei = [a for a in alertas_mei if "DAS-MEI" in a["descricao"]]
    ok(len(das_mei) == 1, "Prazo MEI: DAS-MEI encontrado")
    simples_mei = [a for a in alertas_mei if "DAS Simples Nacional" in a["descricao"]]
    ok(len(simples_mei) == 0, "Prazo MEI: DAS Simples filtrado")

    # ── Teste 3: Alertas sem regime (todos) ──
    alertas_todos = gerar_alertas_prazo("2026-04-16", dias_antecedencia=10)
    ok(len(alertas_todos) >= 2, "Prazo todos: múltiplos alertas")

    # ── Teste 4: Urgência crítico (1 dia) ──
    alertas_crit = gerar_alertas_prazo("2026-04-19", regime="simples", dias_antecedencia=2)
    das_crit = [a for a in alertas_crit if "DAS Simples" in a["descricao"]]
    if das_crit:
        ok(das_crit[0]["dias_restantes"] == 1, "Prazo crítico: 1 dia")
        ok(das_crit[0]["urgencia"] == "critico", "Prazo crítico: urgência critico")
    else:
        ok(False, "Prazo crítico: DAS não encontrado")
        ok(False, "Prazo crítico: urgência critico")

    # ── Teste 5: Sem alertas fora do range ──
    alertas_vazio = gerar_alertas_prazo("2026-04-22", regime="simples", dias_antecedencia=3)
    das_vazio = [a for a in alertas_vazio if "DAS Simples" in a["descricao"]]
    ok(len(das_vazio) == 0, "Prazo fora range: 0 alertas DAS")

    # ── Teste 6: Ordenação por dias restantes ──
    alertas_ord = gerar_alertas_prazo("2026-04-15", dias_antecedencia=15)
    if len(alertas_ord) >= 2:
        ok(alertas_ord[0]["dias_restantes"] <= alertas_ord[-1]["dias_restantes"],
           "Prazo ordenação: mais urgente primeiro")
    else:
        ok(True, "Prazo ordenação: skip (<2)")

    # ── Teste 7: Alertas anuais — IRPF maio ──
    alertas_mai = gerar_alertas_prazo("2026-05-25", dias_antecedencia=7)
    irpf = [a for a in alertas_mai if "IRPF" in a["descricao"] and "Prazo final" in a["descricao"]]
    ok(len(irpf) == 1, "Prazo anual: IRPF maio encontrado")
    ok(irpf[0]["periodicidade"] == "anual", "Prazo anual: periodicidade ok")

    # ── Teste 8: Data inválida fallback ──
    alertas_fb = gerar_alertas_prazo("invalido")
    ok(isinstance(alertas_fb, list), "Data inválida: retorna lista")

    # ── Teste 9: Lembretes recorrentes ──
    inters_recorr = []
    for i in range(5):
        inters_recorr.append({
            "timestamp": f"2026-04-{(i+1):02d}T10:00:00",
            "tags": ["das", "simples"],
        })
    for i in range(3):
        inters_recorr.append({
            "timestamp": f"2026-04-{(i+10):02d}T10:00:00",
            "tags": ["irpf"],
        })
    lembretes = gerar_lembretes_recorrentes(inters_recorr, mes_referencia=4)
    ok(len(lembretes) >= 1, "Lembretes: pelo menos 1")
    ok(lembretes[0]["tema"] in ("das", "simples"), "Lembretes: tema recorrente")
    ok(lembretes[0]["frequencia_no_mes"] >= 2, "Lembretes: frequência >= 2")

    # ── Teste 10: Lembretes sem histórico ──
    lembretes_vazio = gerar_lembretes_recorrentes([])
    ok(len(lembretes_vazio) == 0, "Lembretes vazio: 0")

    # ── Teste 11: Lembretes mês sem dados ──
    lembretes_outro = gerar_lembretes_recorrentes(inters_recorr, mes_referencia=8)
    ok(len(lembretes_outro) == 0, "Lembretes mês sem dados: 0")

    # ── Teste 12: Lembretes com última interação ──
    ok(lembretes[0]["ultima_interacao"] is not None, "Lembretes: última interação presente")

    # ── Teste 13: Validações reforçadas ──
    padroes = {
        "fluxos_problematicos": [
            ("simples", {"taxa_pct": 40.0, "erros": 4, "total": 10}),
            ("irpf", {"taxa_pct": 15.0, "erros": 3, "total": 20}),
            ("folha", {"taxa_pct": 60.0, "erros": 6, "total": 10}),
        ]
    }
    validacoes = gerar_validacoes_reforcadas(padroes)
    ok(len(validacoes) == 2, "Validações: 2 (>=20% e >=3)")
    ok(validacoes[0]["fluxo"] == "simples", "Validações: simples primeiro")
    ok(validacoes[0]["nivel"] == "alto", "Validações: simples nível alto")

    # ── Teste 14: Validação nível crítico ──
    val_crit = [v for v in validacoes if v["nivel"] == "critico"]
    ok(len(val_crit) == 1, "Validações: 1 crítico (folha 60%)")
    ok("BLOQUEAR" in val_crit[0]["recomendacao"], "Validações: recomendação BLOQUEAR")

    # ── Teste 15: Validações sem dados ──
    val_vazio = gerar_validacoes_reforcadas({})
    ok(len(val_vazio) == 0, "Validações vazio: 0")

    # ── Teste 16: Validações com poucos dados (total<3) ──
    padroes_poucos = {
        "fluxos_problematicos": [
            ("teste", {"taxa_pct": 100.0, "erros": 2, "total": 2}),
        ]
    }
    val_poucos = gerar_validacoes_reforcadas(padroes_poucos)
    ok(len(val_poucos) == 0, "Validações poucos dados: filtrado")

    # ── Teste 17: Antecipações por calendário ──
    ant_nov = gerar_antecipacoes([], regime="simples", mes_referencia=11)
    ok(len(ant_nov) >= 1, "Antecipações nov: pelo menos 1")
    ok(any("13°" in a["acao"] for a in ant_nov), "Antecipações nov: 13°")

    # ── Teste 18: Antecipações com filtro de regime ──
    ant_jun_real = gerar_antecipacoes([], regime="real", mes_referencia=6)
    ok(any("ECD" in a["acao"] for a in ant_jun_real), "Antecipações jun real: ECD")

    ant_jun_simples = gerar_antecipacoes([], regime="simples", mes_referencia=6)
    ecd_simples = [a for a in ant_jun_simples if "ECD" in a["acao"]]
    ok(len(ecd_simples) == 0, "Antecipações jun simples: sem ECD")

    # ── Teste 19: Antecipações baseadas em histórico ──
    inters_hist = []
    for i in range(5):
        inters_hist.append({
            "timestamp": f"2025-11-{(i+1):02d}T10:00:00",
            "tags": ["13o", "folha"],
        })
    ant_hist = gerar_antecipacoes(inters_hist, mes_referencia=11)
    ant_hist_fonte = [a for a in ant_hist if a.get("fonte") == "historico_cliente"]
    ok(len(ant_hist_fonte) >= 1, "Antecipações histórico: pelo menos 1")

    # ── Teste 20: Antecipações mês sem calendário ──
    ant_1 = gerar_antecipacoes([], mes_referencia=1)
    # Janeiro não tem antecipações no calendário
    ok(isinstance(ant_1, list), "Antecipações jan: retorna lista")

    # ── Teste 21: Consolidadas ──
    cons = gerar_sugestoes_consolidadas(
        interacoes_cliente=inters_recorr,
        padroes_correcao=padroes,
        regime="simples",
        data_referencia="2026-04-16",
        dias_antecedencia=5,
    )
    ok("alertas_prazo" in cons, "Consolidadas: tem alertas")
    ok("lembretes_recorrentes" in cons, "Consolidadas: tem lembretes")
    ok("validacoes_reforcadas" in cons, "Consolidadas: tem validações")
    ok("antecipacoes" in cons, "Consolidadas: tem antecipações")
    ok("resumo" in cons, "Consolidadas: tem resumo")
    ok(cons["resumo"]["total_sugestoes"] > 0, "Consolidadas: total > 0")

    # ── Teste 22: Resumo correto ──
    res = cons["resumo"]
    ok(res["alertas"] == len(cons["alertas_prazo"]), "Resumo: contagem alertas ok")
    ok(res["lembretes"] == len(cons["lembretes_recorrentes"]), "Resumo: contagem lembretes ok")
    ok(res["validacoes"] == len(cons["validacoes_reforcadas"]), "Resumo: contagem validações ok")

    # ── Teste 23: Consolidadas sem dados ──
    cons_vazio = gerar_sugestoes_consolidadas(
        interacoes_cliente=[],
        data_referencia="2026-01-10",
        dias_antecedencia=1,
    )
    ok(cons_vazio["resumo"]["total_sugestoes"] >= 0, "Consolidadas vazio: ok")

    # ── Teste 24: Prazos mensais cobertura ──
    ok(len(PRAZOS_MENSAIS) >= 8, "Prazos mensais: >=8 definidos")
    ok(all("dia" in p for p in PRAZOS_MENSAIS), "Prazos mensais: todos têm dia")

    # ── Teste 25: Prazos anuais cobertura ──
    ok(len(PRAZOS_ANUAIS) >= 9, "Prazos anuais: >=9 definidos")
    meses_anuais = set(p["mes"] for p in PRAZOS_ANUAIS)
    ok(len(meses_anuais) >= 6, "Prazos anuais: cobrem >=6 meses")

    # ── Teste 26: Alerta ICMS dia 25 para presumido ──
    alertas_icms = gerar_alertas_prazo("2026-04-21", regime="presumido", dias_antecedencia=5)
    icms = [a for a in alertas_icms if "ICMS" in a["descricao"]]
    ok(len(icms) == 1, "ICMS: encontrado para presumido")
    ok(icms[0]["dias_restantes"] == 4, "ICMS: 4 dias restantes")

    # ── Teste 27: Sem alertas ICMS para simples (não sublimite) ──
    alertas_simples = gerar_alertas_prazo("2026-04-21", regime="simples", dias_antecedencia=5)
    icms_simples = [a for a in alertas_simples if "ICMS" in a["descricao"]]
    ok(len(icms_simples) == 0, "ICMS: filtrado para simples normal")

    # ── Teste 28: Urgência gradual ──
    # dia 20: 19→20 = 1 dia = crítico
    a_crit = gerar_alertas_prazo("2026-04-19", regime="simples", dias_antecedencia=2)
    das_c = [a for a in a_crit if "DAS Simples" in a["descricao"]]
    # dia 20: 17→20 = 3 dias = urgente
    a_urg = gerar_alertas_prazo("2026-04-17", regime="simples", dias_antecedencia=4)
    das_u = [a for a in a_urg if "DAS Simples" in a["descricao"]]
    if das_c:
        ok(das_c[0]["urgencia"] == "critico", "Urgência: 1 dia = crítico")
    else:
        ok(False, "Urgência: 1 dia = crítico (not found)")
    if das_u:
        ok(das_u[0]["urgencia"] == "urgente", "Urgência: 3 dias = urgente")
    else:
        ok(False, "Urgência: 3 dias = urgente (not found)")

    # ── Teste 29: Consolidadas contagem criticos ──
    cons2 = gerar_sugestoes_consolidadas(
        interacoes_cliente=[],
        padroes_correcao={"fluxos_problematicos": [("x", {"taxa_pct": 70.0, "erros": 7, "total": 10})]},
        regime="simples",
        data_referencia="2026-04-19",
        dias_antecedencia=2,
    )
    ok(cons2["resumo"]["criticos"] >= 1, "Consolidadas: >=1 crítico")

    # ── Teste 30: Antecipação dezembro — 13° e fechamento ──
    ant_dez = gerar_antecipacoes([], mes_referencia=12)
    ok(any("13°" in a["acao"] for a in ant_dez), "Antecipação dez: 13°")
    ok(any("fechamento" in a["acao"].lower() for a in ant_dez), "Antecipação dez: fechamento")

    # ── Teste 31: Antecipação maio — IRPF prazo final ──
    ant_mai = gerar_antecipacoes([], mes_referencia=5)
    ok(any("IRPF" in a["acao"] or "DEFIS" in a["acao"] for a in ant_mai), "Antecipação mai: IRPF ou DEFIS")

    # ── Teste 32: Validação nível moderado ──
    padroes_mod = {
        "fluxos_problematicos": [
            ("rescisao", {"taxa_pct": 25.0, "erros": 5, "total": 20}),
        ]
    }
    val_mod = gerar_validacoes_reforcadas(padroes_mod)
    ok(len(val_mod) == 1, "Validação moderado: 1")
    ok(val_mod[0]["nivel"] == "moderado", "Validação moderado: nível correto")

    print()
    print("=" * 50)
    print(f"sugestoes_proativas.py: {testes_passou} PASSOU, {testes_falhou} FALHOU de {testes_passou + testes_falhou}")
    print("=" * 50)


if __name__ == "__main__":
    _rodar_testes()
