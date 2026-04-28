#!/usr/bin/env python3
"""
cross_skill_router.py — Router Inteligente Cross-Skill
RRT Group Contador v4.6 — Cross-Skill Intelligence

Analisa uma solicitação e determina quais skills RRT devem ser ativadas.
Suporta ativação de múltiplas skills quando a tarefa cruza domínios.

Skills mapeadas:
  - rrt-group-contador: cálculos tributários, IRPF, folha, simulações
  - fechamento-fiscal: apuração mensal, XMLs, PGDAS-D, DARF
  - montar-balanco: balanço patrimonial, DRE, balancetes
  - rrt-finance: lançamentos, conciliação, Omie, boletos
  - rrt-detetive: pesquisa de clientes, dossiê empresarial
  - planejamento-transicao: CLT→empreendedor, cenários financeiros
  - monitora-whatsapp-rrt: monitoramento de grupos WhatsApp
  - rrt-transcriber: transcrição de áudios

Cada skill tem triggers (palavras-chave) e prioridade.
O router retorna ranking de skills com score de relevância.
"""

import re
from typing import Optional


# ── Definição de skills e triggers ───────────────────────────────────────────

SKILLS = {
    "rrt-group-contador": {
        "nome_exibicao": "Contador (Cálculos)",
        "triggers": [
            "imposto", "tributo", "icms", "iss", "irpj", "csll", "pis", "cofins",
            "inss", "fgts", "cbs", "ibs", "reforma tributária",
            "rescisão", "férias", "13", "décimo terceiro", "hora extra",
            "folha", "holerite", "custo empregado", "clt",
            "simples", "mei", "presumido", "lucro real",
            "pró-labore", "prolabore", "distribuição de lucros",
            "darf", "gps", "código darf",
            "alíquota", "faturamento", "regime tributário",
            "irpf", "imposto de renda", "declaração", "carnê-leão",
            "ganho de capital", "crypto", "etf",
            "completa", "simplificada", "deduções",
            "retenção", "retido", "retencoes",
            "sped", "esocial", "dctf", "obrigações acessórias",
            "cct", "convenção coletiva",
            "comparativo", "qual regime",
            "calcular", "calcula", "cálculo", "quanto pago",
        ],
        "prioridade": 10,  # Skill principal — sempre candidata
    },
    "fechamento-fiscal": {
        "nome_exibicao": "Fechamento Fiscal",
        "triggers": [
            "fechamento", "apuração", "apurar", "apura",
            "xml", "nfe", "nfce", "nfse", "nota fiscal", "notas fiscais",
            "jettax", "pgdas", "das",
            "cfop", "ncm", "cst", "csosn",
            "sublimite", "excedido",
            "competência", "mês anterior",
            "planilha de apuração", "conferir faturamento",
            "icms débito", "icms crédito", "icms",
            "lucro presumido mensal", "trimestral",
        ],
        "prioridade": 8,
    },
    "montar-balanco": {
        "nome_exibicao": "Balanço / DRE",
        "triggers": [
            "balanço", "balancete", "dre",
            "plano de contas", "reclassificação",
            "divergência", "lançamento de ajuste",
            "confronto", "conciliação contábil",
            "passivo", "ativo", "patrimônio líquido",
            "razão contábil",
        ],
        "prioridade": 7,
    },
    "rrt-finance": {
        "nome_exibicao": "Financeiro RRT",
        "triggers": [
            "lançamento", "conciliação", "extrato",
            "omie", "boleto", "bradesco",
            "inadimplência", "cobrança",
            "guia", "pagamento",
            "fluxo de caixa", "contas a pagar", "contas a receber",
            "cnab", "remessa bancária",
        ],
        "prioridade": 6,
    },
    "rrt-detetive": {
        "nome_exibicao": "Detetive (Pesquisa)",
        "triggers": [
            "pesquisa", "pesquisar", "pesquise",
            "cnpj", "quem é", "levantar",
            "dossiê", "perfil empresarial",
            "prospect", "prospecção",
            "primeiro contato", "reunião comercial",
            "lead", "cliente novo",
        ],
        "prioridade": 5,
    },
    "planejamento-transicao": {
        "nome_exibicao": "Planejamento CLT→PJ",
        "triggers": [
            "transição", "sair da clt", "empreender",
            "renda passiva", "viver de renda",
            "custo de vida", "reserva financeira",
            "quanto preciso", "cenários financeiros",
            "capital necessário",
        ],
        "prioridade": 4,
    },
    "monitora-whatsapp-rrt": {
        "nome_exibicao": "Monitor WhatsApp",
        "triggers": [
            "whatsapp", "grupos rrt", "sem resposta",
            "pendências", "atendimento",
            "rotina matinal", "verificar grupos",
            "cliente esperando",
        ],
        "prioridade": 3,
    },
    "rrt-transcriber": {
        "nome_exibicao": "Transcritor de Áudio",
        "triggers": [
            "áudio", "audio", "transcrever", "transcreve", "transcrição",
            "escuta", "opus", "ogg", "mp3",
            "mensagem de voz", "voice",
        ],
        "prioridade": 3,
    },
}


def rotear(texto: str, contexto: Optional[dict] = None) -> dict:
    """
    Analisa texto e retorna ranking de skills relevantes.

    Args:
        texto: Texto da solicitação (mensagem do cliente ou do contador)
        contexto: dict opcional com:
            - regime: regime tributário do cliente
            - cnpj: CNPJ do cliente
            - origem: 'gestta', 'whatsapp', 'direto'
            - tipo_documento: tipo de documento anexo

    Returns:
        dict com skills rankeadas, scores, e recomendação
    """
    ctx = contexto or {}
    texto_lower = texto.lower()
    scores = {}

    for skill_id, skill_def in SKILLS.items():
        score = 0.0
        matches = []

        for trigger in skill_def["triggers"]:
            if trigger in texto_lower:
                # Peso proporcional ao tamanho do trigger (termos mais específicos valem mais)
                peso = 1.0 + len(trigger) / 20.0
                score += peso
                matches.append(trigger)

        # Bonus por prioridade base da skill
        if score > 0:
            score += skill_def["prioridade"] * 0.1

        # ── Contextual boosts ──

        # Se tem regime, boost para skills que tratam daquele regime
        regime = ctx.get("regime", "")
        if regime:
            if skill_id == "rrt-group-contador":
                score += 2.0  # Sempre relevante quando tem regime
            if skill_id == "fechamento-fiscal" and regime in ("simples", "presumido", "real"):
                score += 1.5

        # Se tem documento anexo, boost inteligência documental / fechamento
        tipo_doc = ctx.get("tipo_documento", "")
        if tipo_doc:
            if "xml" in tipo_doc and skill_id == "fechamento-fiscal":
                score += 3.0
            if "pdf" in tipo_doc and "das" in tipo_doc and skill_id == "rrt-group-contador":
                score += 2.0
            if "audio" in tipo_doc and skill_id == "rrt-transcriber":
                score += 5.0

        # Se origem é Gestta/WhatsApp
        origem = ctx.get("origem", "")
        if origem == "gestta" and skill_id in ("rrt-group-contador", "fechamento-fiscal"):
            score += 1.0
        if origem == "whatsapp" and skill_id == "monitora-whatsapp-rrt":
            score += 2.0

        if score > 0:
            scores[skill_id] = {
                "skill": skill_id,
                "nome": skill_def["nome_exibicao"],
                "score": round(score, 2),
                "matches": matches,
                "prioridade_base": skill_def["prioridade"],
            }

    # Ordenar por score
    ranking = sorted(scores.values(), key=lambda x: x["score"], reverse=True)

    # Determinar recomendação
    if not ranking:
        return {
            "skills_recomendadas": [],
            "skill_principal": None,
            "skills_complementares": [],
            "total_matches": 0,
            "recomendacao": "Nenhuma skill específica identificada. Usar rrt-group-contador como fallback.",
        }

    principal = ranking[0]
    complementares = [s for s in ranking[1:] if s["score"] >= principal["score"] * 0.4]

    # Detectar cross-skill (quando múltiplas skills são fortemente relevantes)
    cross_skill = len(complementares) > 0 and complementares[0]["score"] >= principal["score"] * 0.6

    recomendacao = f"Usar {principal['nome']}"
    if cross_skill:
        nomes_comp = [s["nome"] for s in complementares[:2]]
        recomendacao += f" + {' + '.join(nomes_comp)}"

    return {
        "skills_recomendadas": ranking,
        "skill_principal": principal,
        "skills_complementares": complementares,
        "cross_skill": cross_skill,
        "total_matches": sum(len(s["matches"]) for s in ranking),
        "recomendacao": recomendacao,
    }


def rotear_documento(tipo_documento: str, dados_documento: Optional[dict] = None) -> dict:
    """
    Roteia um documento para a skill/módulo correto.

    Args:
        tipo_documento: tipo retornado por inteligencia_documental.detectar_tipo_documento()
        dados_documento: dados extraídos pelo parser

    Returns:
        dict com skill recomendada e próximos passos
    """
    dados = dados_documento or {}

    roteamento = {
        "das_pdf": {
            "skill": "rrt-group-contador",
            "modulo": "parser_das_pdf",
            "proximo_passo": "Validar dados extraídos e comparar com cálculo",
            "skills_complementares": ["fechamento-fiscal"],
        },
        "informe_rendimentos_pdf": {
            "skill": "rrt-group-contador",
            "modulo": "parse_informe_rendimentos",
            "proximo_passo": "Consolidar para dossiê IRPF (Fluxo 24→25)",
            "skills_complementares": [],
        },
        "xml_nfe": {
            "skill": "fechamento-fiscal",
            "modulo": "parser_xml_nfe + ponte_fechamento_fiscal",
            "proximo_passo": "Classificar CFOPs e consolidar para apuração mensal",
            "skills_complementares": ["rrt-group-contador"],
        },
        "xml_nfce": {
            "skill": "fechamento-fiscal",
            "modulo": "parser_xml_nfe + ponte_fechamento_fiscal",
            "proximo_passo": "Consolidar vendas NFC-e para apuração mensal",
            "skills_complementares": ["rrt-group-contador"],
        },
        "xml_nfse": {
            "skill": "fechamento-fiscal",
            "modulo": "parser_xml_nfe + ponte_fechamento_fiscal",
            "proximo_passo": "Apurar ISS e verificar retenções na fonte",
            "skills_complementares": ["rrt-group-contador"],
        },
        "xml_cte": {
            "skill": "fechamento-fiscal",
            "modulo": "parser_xml_nfe (CT-e — v4.6 placeholder)",
            "proximo_passo": "CT-e parser em desenvolvimento",
            "skills_complementares": [],
        },
        "audio_transcricao": {
            "skill": "rrt-transcriber",
            "modulo": "ponte_transcriber",
            "proximo_passo": "Transcrever e classificar conteúdo contábil",
            "skills_complementares": ["rrt-group-contador"],
        },
        "texto_mensagem": {
            "skill": "rrt-group-contador",
            "modulo": "classificar_mensagem",
            "proximo_passo": "Classificar em fluxo contábil e gerar rascunho de resposta",
            "skills_complementares": [],
        },
    }

    info = roteamento.get(tipo_documento, {
        "skill": "rrt-group-contador",
        "modulo": "classificar_mensagem",
        "proximo_passo": "Analisar manualmente — tipo não reconhecido",
        "skills_complementares": [],
    })

    return {
        "tipo_documento": tipo_documento,
        "skill_principal": info["skill"],
        "modulo": info["modulo"],
        "proximo_passo": info["proximo_passo"],
        "skills_complementares": info["skills_complementares"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# TESTES
# ══════════════════════════════════════════════════════════════════════════════

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

    # ── Teste 1: Rotear pergunta tributária ──
    r = rotear("Quanto pago de ICMS no Simples Nacional?")
    ok(r["skill_principal"] is not None, "Tributário: tem principal")
    ok(r["skill_principal"]["skill"] == "rrt-group-contador", "Tributário: contador é principal")
    ok("icms" in r["skill_principal"]["matches"], "Tributário: match ICMS")
    ok("simples" in r["skill_principal"]["matches"], "Tributário: match Simples")

    # ── Teste 2: Rotear fechamento fiscal ──
    r2 = rotear("Preciso fazer o fechamento fiscal do mês, tenho os XMLs das notas")
    ok(r2["skill_principal"]["skill"] == "fechamento-fiscal", "Fechamento: skill correta")
    ok("xml" in r2["skill_principal"]["matches"], "Fechamento: match XML")

    # ── Teste 3: Rotear balanço ──
    r3 = rotear("Monta o balanço patrimonial e a DRE do trimestre")
    ok(r3["skill_principal"]["skill"] == "montar-balanco", "Balanço: skill correta")

    # ── Teste 4: Rotear pesquisa de cliente ──
    r4 = rotear("Pesquisa esse CNPJ 12.345.678/0001-99 pra mim")
    ok(r4["skill_principal"]["skill"] == "rrt-detetive", "Detetive: skill correta")

    # ── Teste 5: Rotear transcrição ──
    r5 = rotear("Transcreve esse áudio do WhatsApp")
    ok(r5["skill_principal"]["skill"] == "rrt-transcriber", "Transcrever: skill correta")

    # ── Teste 6: Rotear planejamento ──
    r6 = rotear("Quero sair da CLT e empreender, quanto preciso de reserva?")
    ok(r6["skill_principal"]["skill"] == "planejamento-transicao", "Transição: skill correta")

    # ── Teste 7: Rotear financeiro ──
    r7 = rotear("Faz a conciliação do extrato do Bradesco com os lançamentos do Omie")
    ok(r7["skill_principal"]["skill"] == "rrt-finance", "Financeiro: skill correta")

    # ── Teste 8: Rotear WhatsApp ──
    r8 = rotear("Verifica os grupos do WhatsApp, tem cliente esperando resposta?")
    ok(r8["skill_principal"]["skill"] == "monitora-whatsapp-rrt", "WhatsApp: skill correta")

    # ── Teste 9: Cross-skill (fechamento + cálculo) ──
    r9 = rotear("Apura o ICMS das notas fiscais e calcula o DAS do Simples")
    ok(r9["cross_skill"] == True, "Cross-skill: detectado")
    ok(len(r9["skills_complementares"]) >= 1, "Cross-skill: tem complementares")

    # ── Teste 10: Texto vazio / sem match ──
    r10 = rotear("Bom dia, tudo bem?")
    ok(r10["skill_principal"] is None, "Sem match: sem principal")
    ok("fallback" in r10["recomendacao"].lower(), "Sem match: recomenda fallback")

    # ── Teste 11: Contexto com regime ──
    r11 = rotear("Qual o imposto do mês?", {"regime": "simples"})
    ok(r11["skill_principal"]["score"] > rotear("Qual o imposto do mês?")["skill_principal"]["score"],
       "Contexto regime: boost no score")

    # ── Teste 12: Contexto com documento XML ──
    r12 = rotear("Processa esse documento", {"tipo_documento": "xml_nfe"})
    ok(any(s["skill"] == "fechamento-fiscal" for s in r12["skills_recomendadas"]),
       "Contexto XML: fechamento-fiscal presente")

    # ── Teste 13: Contexto com áudio ──
    r13 = rotear("O que tem nesse arquivo?", {"tipo_documento": "audio"})
    ok(r13["skill_principal"]["skill"] == "rrt-transcriber", "Contexto áudio: transcritor")

    # ── Teste 14: Rotear documento — DAS PDF ──
    rd1 = rotear_documento("das_pdf")
    ok(rd1["skill_principal"] == "rrt-group-contador", "Doc DAS: contador")
    ok("fechamento-fiscal" in rd1["skills_complementares"], "Doc DAS: complementar fechamento")

    # ── Teste 15: Rotear documento — XML NF-e ──
    rd2 = rotear_documento("xml_nfe")
    ok(rd2["skill_principal"] == "fechamento-fiscal", "Doc XML: fechamento")
    ok("ponte_fechamento_fiscal" in rd2["modulo"], "Doc XML: módulo correto")

    # ── Teste 16: Rotear documento — NFS-e ──
    rd3 = rotear_documento("xml_nfse")
    ok(rd3["skill_principal"] == "fechamento-fiscal", "Doc NFS-e: fechamento")
    ok("ISS" in rd3["proximo_passo"], "Doc NFS-e: menciona ISS")

    # ── Teste 17: Rotear documento — áudio ──
    rd4 = rotear_documento("audio_transcricao")
    ok(rd4["skill_principal"] == "rrt-transcriber", "Doc áudio: transcritor")

    # ── Teste 18: Rotear documento — texto ──
    rd5 = rotear_documento("texto_mensagem")
    ok(rd5["skill_principal"] == "rrt-group-contador", "Doc texto: contador")
    ok("classificar_mensagem" in rd5["modulo"], "Doc texto: classificador")

    # ── Teste 19: Rotear documento — desconhecido ──
    rd6 = rotear_documento("tipo_inexistente")
    ok(rd6["skill_principal"] == "rrt-group-contador", "Doc desconhecido: fallback contador")

    # ── Teste 20: Múltiplos triggers na mesma mensagem ──
    r14 = rotear("Preciso calcular ICMS, PIS, COFINS e ISS das notas do fechamento mensal")
    ok(r14["total_matches"] >= 5, "Multi-trigger: 5+ matches")
    ok(r14["skill_principal"]["score"] > 5.0, "Multi-trigger: score alto")

    # ── Teste 21: Contexto origem Gestta ──
    r15 = rotear("Pergunta sobre impostos", {"origem": "gestta"})
    score_sem = rotear("Pergunta sobre impostos")["skill_principal"]["score"]
    ok(r15["skill_principal"]["score"] > score_sem, "Contexto Gestta: boost")

    # ── Teste 22: Recomendação textual ──
    r16 = rotear("Faz o fechamento das notas e calcula o DAS")
    ok("Usar" in r16["recomendacao"], "Recomendação: formato correto")

    print(f"\n{'='*50}")
    print(f"cross_skill_router.py: {testes_passou} PASSOU, {testes_falhou} FALHOU de {testes_passou + testes_falhou}")
    print(f"{'='*50}")

    return testes_falhou == 0


if __name__ == "__main__":
    _rodar_testes()
