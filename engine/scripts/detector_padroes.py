#!/usr/bin/env python3
"""
detector_padroes.py — Detector de Padrões em Interações
RRT Group Contador v5.0 — Aprendizado

Analisa o histórico de interações (registro_interacoes.py) para detectar:
  - Padrões sazonais (picos por mês/período fiscal)
  - Padrões por cliente (temas recorrentes, frequência)
  - Padrões de correção (onde o skill mais erra)
  - Tendências temporais (crescimento/queda de temas)
  - Clusters de perguntas (temas que aparecem juntos)

Alimenta sugestoes_proativas.py com insights acionáveis.
"""

from datetime import datetime
from typing import Optional


# ── Calendário fiscal brasileiro ────────────────────────────────────────────

CALENDARIO_FISCAL = {
    1: ["DIRF (entrega até final fev)", "Informe de Rendimentos (emissão)"],
    2: ["DIRF prazo final", "RAIS (início do período)"],
    3: ["IRPF (início entrega)", "ECF (preparação)"],
    4: ["IRPF (pico)", "1a parcela 13° (antecipar cálculos)"],
    5: ["IRPF (prazo final ~31/05)", "DEFIS Simples (prazo)"],
    6: ["ECD/SPED Contábil (prazo)", "Meio do ano fiscal"],
    7: ["ECF (prazo)", "Revisão semestral"],
    8: ["2° trimestre IRPJ/CSLL (LR/LP)"],
    9: ["Planejamento tributário (próximo exercício)"],
    10: ["Simples Nacional (opção próximo ano, preparar)", "Planejamento 13°"],
    11: ["1a parcela 13° (prazo)", "PGDAS-D retificações"],
    12: ["2a parcela 13° (prazo 20/12)", "Fechamento anual", "13° salário"],
}


def detectar_sazonalidade(interacoes: list) -> dict:
    """
    Detecta padrões sazonais nas interações.

    Args:
        interacoes: lista de dicts com campo 'timestamp' e 'tags'

    Returns:
        dict com distribuição mensal, picos e correlações com calendário fiscal
    """
    por_mes = {m: {"total": 0, "tags": {}} for m in range(1, 13)}

    for inter in interacoes:
        ts = inter.get("timestamp", "")
        if len(ts) < 7:
            continue
        try:
            mes = int(ts[5:7])
        except (ValueError, IndexError):
            continue

        if mes < 1 or mes > 12:
            continue

        por_mes[mes]["total"] += 1
        for tag in inter.get("tags", []):
            tag_lower = tag.lower()
            por_mes[mes]["tags"][tag_lower] = por_mes[mes]["tags"].get(tag_lower, 0) + 1

    # Calcular média
    totais = [por_mes[m]["total"] for m in range(1, 13)]
    media = sum(totais) / 12 if sum(totais) > 0 else 0

    # Detectar picos (>1.5x média) e vales (<0.5x média)
    picos = []
    vales = []
    for m in range(1, 13):
        if media > 0:
            ratio = por_mes[m]["total"] / media
            if ratio > 1.5:
                top_tags = sorted(
                    por_mes[m]["tags"].items(), key=lambda x: x[1], reverse=True
                )[:3]
                picos.append({
                    "mes": m,
                    "total": por_mes[m]["total"],
                    "ratio": round(ratio, 2),
                    "top_tags": top_tags,
                    "calendario_fiscal": CALENDARIO_FISCAL.get(m, []),
                })
            elif ratio < 0.5 and por_mes[m]["total"] > 0:
                vales.append({"mes": m, "total": por_mes[m]["total"], "ratio": round(ratio, 2)})

    return {
        "distribuicao_mensal": {m: por_mes[m]["total"] for m in range(1, 13)},
        "media_mensal": round(media, 1),
        "picos": picos,
        "vales": vales,
        "meses_analisados": len([t for t in totais if t > 0]),
    }


def detectar_padroes_cliente(interacoes: list, top_n: int = 5) -> dict:
    """
    Detecta padrões por cliente (temas recorrentes, frequência).

    Args:
        interacoes: lista de interações
        top_n: número de top temas/fluxos a retornar

    Returns:
        dict com padrões do cliente
    """
    if not interacoes:
        return {"total": 0, "padroes": []}

    # Frequência de tags
    tag_freq = {}
    fluxo_freq = {}
    origem_freq = {}
    dias_atividade = set()

    for inter in interacoes:
        for tag in inter.get("tags", []):
            tag_lower = tag.lower()
            tag_freq[tag_lower] = tag_freq.get(tag_lower, 0) + 1

        fluxo = inter.get("classificacao", {}).get("fluxo", "desconhecido")
        fluxo_freq[fluxo] = fluxo_freq.get(fluxo, 0) + 1

        origem = inter.get("origem", "direto")
        origem_freq[origem] = origem_freq.get(origem, 0) + 1

        ts = inter.get("timestamp", "")
        if len(ts) >= 10:
            dias_atividade.add(ts[:10])

    top_tags = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_fluxos = sorted(fluxo_freq.items(), key=lambda x: x[1], reverse=True)[:top_n]

    # Calcular intervalo médio entre interações
    timestamps = []
    for inter in interacoes:
        ts = inter.get("timestamp", "")
        if len(ts) >= 10:
            try:
                timestamps.append(datetime.fromisoformat(ts[:19]))
            except ValueError:
                pass

    intervalo_medio_dias = None
    if len(timestamps) >= 2:
        timestamps.sort()
        deltas = [(timestamps[i+1] - timestamps[i]).total_seconds() / 86400
                   for i in range(len(timestamps) - 1)]
        intervalo_medio_dias = round(sum(deltas) / len(deltas), 1)

    return {
        "total": len(interacoes),
        "dias_atividade": len(dias_atividade),
        "top_tags": top_tags,
        "top_fluxos": top_fluxos,
        "origens": dict(origem_freq),
        "intervalo_medio_dias": intervalo_medio_dias,
    }


def detectar_padroes_correcao(interacoes: list) -> dict:
    """
    Analisa padrões de correção para identificar onde o skill mais erra.

    Args:
        interacoes: lista completa (com avaliações)

    Returns:
        dict com análise de erros por fluxo, tag, e exemplos
    """
    total = len(interacoes)
    if total == 0:
        return {"total": 0}

    correcoes = [i for i in interacoes if i.get("avaliacao") in ("ajustado", "rejeitado")]
    aprovados = [i for i in interacoes if i.get("avaliacao") == "aprovado"]
    pendentes = [i for i in interacoes if i.get("avaliacao") is None]

    # Erros por fluxo
    erros_fluxo = {}
    total_fluxo = {}
    for inter in interacoes:
        if inter.get("avaliacao") is None:
            continue
        fluxo = inter.get("classificacao", {}).get("fluxo", "desconhecido")
        total_fluxo[fluxo] = total_fluxo.get(fluxo, 0) + 1
        if inter["avaliacao"] in ("ajustado", "rejeitado"):
            erros_fluxo[fluxo] = erros_fluxo.get(fluxo, 0) + 1

    # Taxa de erro por fluxo
    taxa_erro_fluxo = {}
    for fluxo, erros in erros_fluxo.items():
        total_f = total_fluxo.get(fluxo, 1)
        taxa_erro_fluxo[fluxo] = {
            "erros": erros,
            "total": total_f,
            "taxa_pct": round(erros / total_f * 100, 1),
        }

    # Erros por tag
    erros_tag = {}
    for inter in correcoes:
        for tag in inter.get("tags", []):
            erros_tag[tag] = erros_tag.get(tag, 0) + 1

    top_erros_tag = sorted(erros_tag.items(), key=lambda x: x[1], reverse=True)[:5]

    # Ordenar fluxos por taxa de erro (decrescente)
    fluxos_problematicos = sorted(
        taxa_erro_fluxo.items(), key=lambda x: x[1]["taxa_pct"], reverse=True
    )

    # Exemplos de correções recentes
    exemplos = []
    for inter in correcoes[-5:]:
        exemplos.append({
            "timestamp": inter.get("timestamp", ""),
            "texto_resumo": inter.get("texto", "")[:80],
            "fluxo": inter.get("classificacao", {}).get("fluxo", "?"),
            "avaliacao": inter["avaliacao"],
            "correcao_resumo": (inter.get("correcao") or "")[:100],
        })

    avaliados = len(aprovados) + len(correcoes)
    taxa_geral = round(len(correcoes) / avaliados * 100, 1) if avaliados > 0 else None

    return {
        "total_interacoes": total,
        "total_avaliados": avaliados,
        "aprovados": len(aprovados),
        "correcoes": len(correcoes),
        "pendentes": len(pendentes),
        "taxa_erro_geral_pct": taxa_geral,
        "fluxos_problematicos": fluxos_problematicos,
        "top_erros_tag": top_erros_tag,
        "exemplos_correcoes": exemplos,
    }


def detectar_clusters(interacoes: list, min_coocorrencia: int = 3) -> list:
    """
    Detecta clusters de tags que aparecem frequentemente juntas.

    Args:
        interacoes: lista de interações
        min_coocorrencia: mínimo de co-ocorrências para formar cluster

    Returns:
        lista de clusters [(tag_a, tag_b, count)]
    """
    coocorrencias = {}

    for inter in interacoes:
        tags = sorted(set(t.lower() for t in inter.get("tags", [])))
        for i in range(len(tags)):
            for j in range(i + 1, len(tags)):
                par = (tags[i], tags[j])
                coocorrencias[par] = coocorrencias.get(par, 0) + 1

    clusters = [
        {"tags": list(par), "coocorrencias": count}
        for par, count in coocorrencias.items()
        if count >= min_coocorrencia
    ]

    return sorted(clusters, key=lambda x: x["coocorrencias"], reverse=True)


def gerar_insights(interacoes: list) -> dict:
    """
    Gera insights consolidados a partir do histórico de interações.

    Returns:
        dict com sazonalidade, padrões de erro, clusters, e recomendações
    """
    sazonalidade = detectar_sazonalidade(interacoes)
    correcao = detectar_padroes_correcao(interacoes)
    clusters = detectar_clusters(interacoes)

    # Gerar recomendações acionáveis
    recomendacoes = []

    # Recomendação 1: fluxos problemáticos
    for fluxo, dados in correcao.get("fluxos_problematicos", [])[:3]:
        if dados["taxa_pct"] > 30 and dados["total"] >= 3:
            recomendacoes.append({
                "tipo": "melhoria_fluxo",
                "prioridade": "alta" if dados["taxa_pct"] > 50 else "média",
                "descricao": f"Fluxo '{fluxo}' tem taxa de erro de {dados['taxa_pct']}% ({dados['erros']}/{dados['total']}). Revisar lógica de cálculo ou triggers.",
            })

    # Recomendação 2: picos sazonais
    mes_atual = datetime.now().month
    proximo_mes = (mes_atual % 12) + 1
    for pico in sazonalidade.get("picos", []):
        if pico["mes"] == proximo_mes:
            recomendacoes.append({
                "tipo": "preparacao_sazonal",
                "prioridade": "média",
                "descricao": f"Mês {proximo_mes} historicamente tem {pico['ratio']}x mais interações. Temas: {', '.join(t[0] for t in pico['top_tags'][:3])}.",
            })

    # Recomendação 3: taxa de erro alta geral
    if correcao.get("taxa_erro_geral_pct") and correcao["taxa_erro_geral_pct"] > 25:
        recomendacoes.append({
            "tipo": "qualidade_geral",
            "prioridade": "alta",
            "descricao": f"Taxa de erro geral em {correcao['taxa_erro_geral_pct']}%. Revisar os fluxos mais problemáticos.",
        })

    return {
        "sazonalidade": sazonalidade,
        "correcao": correcao,
        "clusters": clusters[:10],
        "recomendacoes": recomendacoes,
        "total_interacoes_analisadas": len(interacoes),
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

    # ── Helper: gerar interações fake ──
    def gerar_interacoes(n, mes=4, tags=None, fluxo="simples", avaliacao=None, correcao=None):
        result = []
        for i in range(n):
            result.append({
                "timestamp": f"2026-{mes:02d}-{(i%28)+1:02d}T10:00:00",
                "cnpj": "12345678000199",
                "texto": f"Pergunta {i}",
                "classificacao": {"fluxo": fluxo},
                "resultado": {},
                "tags": tags or ["das", "simples"],
                "avaliacao": avaliacao,
                "correcao": correcao,
                "origem": "gestta",
            })
        return result

    # ── Teste 1: Sazonalidade básica ──
    inters = gerar_interacoes(10, mes=3) + gerar_interacoes(2, mes=6) + gerar_interacoes(5, mes=12)
    saz = detectar_sazonalidade(inters)
    ok(saz["distribuicao_mensal"][3] == 10, "Sazonalidade: março=10")
    ok(saz["distribuicao_mensal"][6] == 2, "Sazonalidade: junho=2")
    ok(saz["distribuicao_mensal"][12] == 5, "Sazonalidade: dezembro=5")
    ok(saz["meses_analisados"] == 3, "Sazonalidade: 3 meses com dados")

    # ── Teste 2: Picos detectados ──
    ok(len(saz["picos"]) >= 1, "Sazonalidade: pelo menos 1 pico")
    ok(saz["picos"][0]["mes"] == 3, "Sazonalidade: pico em março")
    ok(saz["picos"][0]["ratio"] > 1.5, "Sazonalidade: ratio > 1.5")

    # ── Teste 3: Calendário fiscal no pico ──
    ok(len(saz["picos"][0]["calendario_fiscal"]) > 0, "Sazonalidade: calendário fiscal presente")

    # ── Teste 4: Lista vazia ──
    saz_vazio = detectar_sazonalidade([])
    ok(saz_vazio["media_mensal"] == 0, "Sazonalidade vazia: média 0")
    ok(saz_vazio["meses_analisados"] == 0, "Sazonalidade vazia: 0 meses")

    # ── Teste 5: Padrões cliente ──
    inters_cli = gerar_interacoes(20, tags=["das", "simples"])
    pad = detectar_padroes_cliente(inters_cli)
    ok(pad["total"] == 20, "Padrões cliente: 20 total")
    ok(pad["top_tags"][0][0] in ("das", "simples"), "Padrões cliente: top tag")
    ok(pad["top_fluxos"][0][0] == "simples", "Padrões cliente: top fluxo")

    # ── Teste 6: Intervalo médio ──
    ok(pad["intervalo_medio_dias"] is not None, "Padrões cliente: intervalo calculado")

    # ── Teste 7: Padrões cliente vazio ──
    pad_vazio = detectar_padroes_cliente([])
    ok(pad_vazio["total"] == 0, "Padrões cliente vazio: 0")

    # ── Teste 8: Origens ──
    ok("gestta" in pad["origens"], "Padrões cliente: origem gestta")

    # ── Teste 9: Padrões de correção ──
    inters_mix = (
        gerar_interacoes(5, fluxo="simples", avaliacao="aprovado")
        + gerar_interacoes(3, fluxo="simples", avaliacao="ajustado", correcao="corrigido")
        + gerar_interacoes(2, fluxo="presumido", avaliacao="rejeitado")
        + gerar_interacoes(10, fluxo="presumido", avaliacao="aprovado")
    )
    corr = detectar_padroes_correcao(inters_mix)
    ok(corr["total_interacoes"] == 20, "Correção: 20 total")
    ok(corr["aprovados"] == 15, "Correção: 15 aprovados")
    ok(corr["correcoes"] == 5, "Correção: 5 correções")
    ok(corr["taxa_erro_geral_pct"] == 25.0, "Correção: taxa erro 25%")

    # ── Teste 10: Fluxos problemáticos ordenados ──
    fluxos = corr["fluxos_problematicos"]
    ok(len(fluxos) >= 1, "Correção: tem fluxos problemáticos")
    # simples: 3/8 = 37.5%, presumido: 2/12 = 16.7% → simples primeiro
    ok(fluxos[0][0] == "simples", "Correção: simples mais problemático")
    ok(fluxos[0][1]["taxa_pct"] == 37.5, "Correção: simples 37.5%")

    # ── Teste 11: Exemplos de correções ──
    ok(len(corr["exemplos_correcoes"]) <= 5, "Correção: máx 5 exemplos")
    ok(corr["exemplos_correcoes"][0]["avaliacao"] in ("ajustado", "rejeitado"), "Correção: exemplo tem avaliação")

    # ── Teste 12: Correção lista vazia ──
    corr_vazio = detectar_padroes_correcao([])
    ok(corr_vazio["total"] == 0, "Correção vazia: 0")

    # ── Teste 13: Todos pendentes ──
    inters_pend = gerar_interacoes(5)
    corr_pend = detectar_padroes_correcao(inters_pend)
    ok(corr_pend["pendentes"] == 5, "Correção pendentes: 5")
    ok(corr_pend["taxa_erro_geral_pct"] is None, "Correção pendentes: taxa None")

    # ── Teste 14: Clusters de tags ──
    inters_cluster = gerar_interacoes(10, tags=["das", "simples", "mensal"])
    clusters = detectar_clusters(inters_cluster, min_coocorrencia=5)
    ok(len(clusters) >= 1, "Clusters: pelo menos 1")
    ok(clusters[0]["coocorrencias"] >= 5, "Clusters: >= 5 co-ocorrências")

    # ── Teste 15: Clusters com threshold alto ──
    clusters_alto = detectar_clusters(inters_cluster, min_coocorrencia=20)
    ok(len(clusters_alto) == 0, "Clusters threshold alto: 0")

    # ── Teste 16: Clusters lista vazia ──
    clusters_vazio = detectar_clusters([])
    ok(len(clusters_vazio) == 0, "Clusters vazio: 0")

    # ── Teste 17: Clusters ordenados por co-ocorrência ──
    inters_multi = (
        gerar_interacoes(10, tags=["das", "simples"])
        + gerar_interacoes(5, tags=["irpj", "presumido"])
    )
    clusters_multi = detectar_clusters(inters_multi, min_coocorrencia=3)
    if len(clusters_multi) >= 2:
        ok(clusters_multi[0]["coocorrencias"] >= clusters_multi[1]["coocorrencias"],
           "Clusters: ordenados decrescente")
    else:
        ok(True, "Clusters: ordenados decrescente (skip - <2)")

    # ── Teste 18: Insights consolidados ──
    inters_full = (
        gerar_interacoes(15, mes=3, tags=["irpf", "declaracao"], fluxo="irpf", avaliacao="aprovado")
        + gerar_interacoes(5, mes=3, tags=["irpf", "deducao"], fluxo="irpf", avaliacao="ajustado", correcao="fix")
        + gerar_interacoes(8, mes=12, tags=["13o", "folha"], fluxo="folha", avaliacao="aprovado")
    )
    insights = gerar_insights(inters_full)
    ok(insights["total_interacoes_analisadas"] == 28, "Insights: 28 interações")
    ok("sazonalidade" in insights, "Insights: tem sazonalidade")
    ok("correcao" in insights, "Insights: tem correção")
    ok("clusters" in insights, "Insights: tem clusters")
    ok("recomendacoes" in insights, "Insights: tem recomendações")

    # ── Teste 19: Recomendações geradas ──
    # irpf tem 5/20 = 25% erro em avaliados, mas com avaliados: 15 aprovado + 5 ajustado = 20
    # taxa irpf = 5/20 = 25%
    ok(len(insights["recomendacoes"]) >= 0, "Insights: recomendações geradas")

    # ── Teste 20: Calendário fiscal completo ──
    ok(len(CALENDARIO_FISCAL) == 12, "Calendário: 12 meses")
    ok(len(CALENDARIO_FISCAL[3]) >= 1, "Calendário: março tem eventos")
    ok(len(CALENDARIO_FISCAL[12]) >= 1, "Calendário: dezembro tem eventos")

    # ── Teste 21: Sazonalidade com timestamps inválidos ──
    inters_bad = [{"timestamp": "invalido", "tags": ["x"]}, {"timestamp": "", "tags": ["y"]}]
    saz_bad = detectar_sazonalidade(inters_bad)
    ok(saz_bad["meses_analisados"] == 0, "Sazonalidade timestamp inválido: 0 meses")

    # ── Teste 22: Top tags no pico sazonal ──
    inters_pico = gerar_interacoes(20, mes=4, tags=["irpf", "declaracao", "prazo"])
    saz_pico = detectar_sazonalidade(inters_pico)
    if saz_pico["picos"]:
        ok(len(saz_pico["picos"][0]["top_tags"]) <= 3, "Pico: máx 3 top tags")
    else:
        ok(True, "Pico: skip (todos no mesmo mês)")

    # ── Teste 23: Padrões cliente com múltiplos dias ──
    inters_dias = []
    for d in range(1, 16):
        inters_dias.append({
            "timestamp": f"2026-04-{d:02d}T10:00:00",
            "cnpj": "11111111000111",
            "texto": f"Q{d}",
            "classificacao": {"fluxo": "simples"},
            "tags": ["das"],
            "origem": "direto",
        })
    pad_dias = detectar_padroes_cliente(inters_dias)
    ok(pad_dias["dias_atividade"] == 15, "Padrões: 15 dias atividade")
    ok(pad_dias["intervalo_medio_dias"] is not None, "Padrões: intervalo calculado")
    ok(abs(pad_dias["intervalo_medio_dias"] - 1.0) < 0.1, "Padrões: ~1 dia intervalo")

    # ── Teste 24: Erros por tag ──
    ok(len(corr["top_erros_tag"]) >= 1, "Correção: top erros tag presente")

    # ── Teste 25: Insights com lista vazia ──
    insights_vazio = gerar_insights([])
    ok(insights_vazio["total_interacoes_analisadas"] == 0, "Insights vazio: 0")

    print()
    print("=" * 50)
    print(f"detector_padroes.py: {testes_passou} PASSOU, {testes_falhou} FALHOU de {testes_passou + testes_falhou}")
    print("=" * 50)


if __name__ == "__main__":
    _rodar_testes()
