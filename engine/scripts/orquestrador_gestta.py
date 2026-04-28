#!/usr/bin/env python3
"""
Orquestrador Gestta — Pipeline completo Gestta→Classificação→Cálculo→Rascunho v4.3

Conecta leitor_gestta.py com o pipeline v4.2 (classificar→ponte→rascunho)
para processar automaticamente atendimentos do portal Gestta.

Uso:
    python3 orquestrador_gestta.py --teste

Importação:
    from orquestrador_gestta import (
        processar_atendimento, processar_todos_atendimentos,
        gerar_relatorio_gestta
    )

Fluxo completo:
    1. leitor_gestta.parsear_conversa()       → mensagens estruturadas
    2. leitor_gestta.identificar_pendencias()  → pendências detectadas
    3. leitor_gestta.preparar_para_classificacao() → formato para NLP
    4. classificar_mensagem.classificar_lote() → fluxos identificados
    5. ponte_whatsapp.processar_pendencias()   → cálculos executados
    6. rascunho_resposta.gerar_relatorio_pendencias() → relatório final

URL: https://app.gestta.com.br/attendance/#/chat/ongoing
"""

import sys
import json
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# IMPORTS DO PIPELINE (lazy para evitar problemas de path)
# ═══════════════════════════════════════════════════════════════

def _importar_modulos():
    """Importa todos os módulos do pipeline."""
    from leitor_gestta import (
        parsear_conversa, identificar_pendencias,
        preparar_para_classificacao, parsear_sidebar,
        consolidar_atendimentos,
    )
    from classificar_mensagem import classificar_lote, filtrar_calculaveis
    from ponte_whatsapp import processar_pendencias, executar_calculo
    from rascunho_resposta import gerar_relatorio_pendencias, gerar_rascunho

    return {
        "parsear_conversa": parsear_conversa,
        "identificar_pendencias": identificar_pendencias,
        "preparar_para_classificacao": preparar_para_classificacao,
        "parsear_sidebar": parsear_sidebar,
        "consolidar_atendimentos": consolidar_atendimentos,
        "classificar_lote": classificar_lote,
        "filtrar_calculaveis": filtrar_calculaveis,
        "processar_pendencias": processar_pendencias,
        "executar_calculo": executar_calculo,
        "gerar_relatorio_pendencias": gerar_relatorio_pendencias,
        "gerar_rascunho": gerar_rascunho,
    }


# ═══════════════════════════════════════════════════════════════
# PROCESSAR UM ATENDIMENTO (conversa individual)
# ═══════════════════════════════════════════════════════════════

def processar_atendimento(mensagens_raw, grupo_nome, horas_limite=24):
    """
    Pipeline completo para um atendimento individual.

    Args:
        mensagens_raw: list[dict] — mensagens extraídas do Gestta via read_page
            Cada dict deve ter: remetente, texto, timestamp, e opcionais (flags, arquivo)
        grupo_nome: str — ex: "RRT Contabilidade - Wesley e Suzana"
        horas_limite: int — janela de tempo para buscar pendências

    Returns:
        dict:
        {
            "grupo_nome": str,
            "cliente_nome": str,
            "tem_pendencia": bool,
            "tempo_espera_minutos": int | None,
            "total_mensagens_analisadas": int,
            "pendencias": [
                {
                    "texto_original": str,
                    "classificacao": dict,     # output classificar_mensagem
                    "calculo": dict | None,    # output ponte_whatsapp (se calculável)
                    "rascunho": dict | None,   # output rascunho_resposta (se calculável)
                }
            ],
            "relatorio_ponte": dict | None,  # output gerar_relatorio_pendencias
            "resumo": str,
            "timestamp_processamento": str,
        }
    """
    mod = _importar_modulos()

    # Step 1: Parsear conversa
    mensagens = mod["parsear_conversa"](mensagens_raw, grupo_nome)

    # Step 2: Identificar pendências
    pendencias = mod["identificar_pendencias"](mensagens, horas_limite)

    if not pendencias["tem_pendencia"]:
        cliente_nome = grupo_nome.split(" - ", 1)[1] if " - " in grupo_nome else grupo_nome
        return {
            "grupo_nome": grupo_nome,
            "cliente_nome": cliente_nome,
            "tem_pendencia": False,
            "tempo_espera_minutos": None,
            "total_mensagens_analisadas": len(mensagens),
            "pendencias": [],
            "relatorio_ponte": None,
            "resumo": "✅ Sem pendências — equipe já respondeu",
            "timestamp_processamento": datetime.now().isoformat(),
        }

    # Step 3: Preparar para classificação
    para_classificar = mod["preparar_para_classificacao"](pendencias, grupo_nome)

    # Step 4: Classificar
    classificacoes = mod["classificar_lote"](para_classificar)

    # Step 5: Executar cálculos via ponte
    resultados_ponte = mod["processar_pendencias"](classificacoes)

    # Step 6: Gerar rascunhos individuais e relatório
    pendencias_detalhadas = []
    for i, resultado in enumerate(resultados_ponte):
        rascunho = mod["gerar_rascunho"](resultado)
        classificacao = classificacoes[i] if i < len(classificacoes) else {}

        pendencias_detalhadas.append({
            "texto_original": resultado.get("texto_original", ""),
            "classificacao": {
                "fluxo_id": classificacao.get("fluxo_id", 0),
                "fluxo_nome": classificacao.get("fluxo_nome", ""),
                "confianca": classificacao.get("confianca", "nenhuma"),
                "calculavel": classificacao.get("calculavel", False),
                "params_extraidos": classificacao.get("params_extraidos", {}),
            },
            "calculo": resultado if resultado.get("sucesso") else None,
            "rascunho": rascunho,
        })

    relatorio = mod["gerar_relatorio_pendencias"](resultados_ponte)

    # Gerar resumo
    n_prontos = relatorio.get("prontos", 0) if isinstance(relatorio, dict) else 0
    n_incompletos = relatorio.get("incompletos", 0) if isinstance(relatorio, dict) else 0
    n_manuais = relatorio.get("manuais", 0) if isinstance(relatorio, dict) else 0

    # Contar de forma segura
    if isinstance(relatorio, dict):
        prontos_list = relatorio.get("detalhes", {}).get("prontos", [])
        incompletos_list = relatorio.get("detalhes", {}).get("incompletos", [])
        manuais_list = relatorio.get("detalhes", {}).get("manuais", [])
        n_prontos = len(prontos_list) if isinstance(prontos_list, list) else 0
        n_incompletos = len(incompletos_list) if isinstance(incompletos_list, list) else 0
        n_manuais = len(manuais_list) if isinstance(manuais_list, list) else 0

    partes_resumo = []
    if n_prontos:
        partes_resumo.append(f"🟢 {n_prontos} resposta(s) pronta(s)")
    if n_incompletos:
        partes_resumo.append(f"🟡 {n_incompletos} precisam mais info")
    if n_manuais:
        partes_resumo.append(f"🔴 {n_manuais} precisam resposta manual")

    cliente_nome = grupo_nome.split(" - ", 1)[1] if " - " in grupo_nome else grupo_nome

    return {
        "grupo_nome": grupo_nome,
        "cliente_nome": cliente_nome,
        "tem_pendencia": True,
        "tempo_espera_minutos": pendencias.get("tempo_espera_minutos"),
        "total_mensagens_analisadas": len(mensagens),
        "pendencias": pendencias_detalhadas,
        "relatorio_ponte": relatorio,
        "resumo": " | ".join(partes_resumo) if partes_resumo else "⚠️ Pendência detectada",
        "timestamp_processamento": datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# PROCESSAR MÚLTIPLOS ATENDIMENTOS
# ═══════════════════════════════════════════════════════════════

def processar_todos_atendimentos(atendimentos_data, horas_limite=24):
    """
    Processa múltiplos atendimentos do Gestta em batch.

    Args:
        atendimentos_data: list[dict] — cada item com:
            {
                "grupo_nome": str,
                "mensagens_raw": list[dict],
            }
        horas_limite: int — janela de tempo

    Returns:
        dict:
        {
            "total_processados": int,
            "com_pendencia": int,
            "com_rascunho_pronto": int,
            "atendimentos": list[dict],  # resultados individuais
            "resumo_geral": str,
            "timestamp": str,
        }
    """
    resultados = []

    for atendimento in atendimentos_data:
        try:
            resultado = processar_atendimento(
                mensagens_raw=atendimento["mensagens_raw"],
                grupo_nome=atendimento["grupo_nome"],
                horas_limite=horas_limite,
            )
            resultados.append(resultado)
        except Exception as e:
            resultados.append({
                "grupo_nome": atendimento.get("grupo_nome", "???"),
                "cliente_nome": "???",
                "tem_pendencia": False,
                "erro": str(e),
                "resumo": f"❌ Erro ao processar: {str(e)[:80]}",
                "timestamp_processamento": datetime.now().isoformat(),
            })

    com_pendencia = sum(1 for r in resultados if r.get("tem_pendencia"))
    com_rascunho = sum(
        1 for r in resultados
        if any(
            p.get("rascunho", {}).get("status") == "pronto"
            for p in r.get("pendencias", [])
        )
    )

    partes = []
    if com_rascunho:
        partes.append(f"🟢 {com_rascunho} com rascunho pronto para revisão")
    if com_pendencia - com_rascunho > 0:
        partes.append(f"🟡 {com_pendencia - com_rascunho} com pendência manual")
    ok = len(resultados) - com_pendencia
    if ok:
        partes.append(f"✅ {ok} sem pendências")

    return {
        "total_processados": len(resultados),
        "com_pendencia": com_pendencia,
        "com_rascunho_pronto": com_rascunho,
        "atendimentos": resultados,
        "resumo_geral": " | ".join(partes) if partes else "Nenhum atendimento processado",
        "timestamp": datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# GERADOR DE RELATÓRIO (para o accountant)
# ═══════════════════════════════════════════════════════════════

def gerar_relatorio_gestta(resultado_batch):
    """
    Gera relatório formatado em texto para o contador revisar.

    Args:
        resultado_batch: dict — output de processar_todos_atendimentos()

    Returns:
        str — relatório formatado para WhatsApp/texto
    """
    r = resultado_batch
    linhas = []
    linhas.append("═" * 50)
    linhas.append("📋 RELATÓRIO DE ATENDIMENTOS GESTTA")
    linhas.append(f"   Processados: {r['total_processados']} grupos")
    linhas.append(f"   Com pendência: {r['com_pendencia']}")
    linhas.append(f"   Com rascunho pronto: {r['com_rascunho_pronto']}")
    linhas.append(f"   Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    linhas.append("═" * 50)

    # Seção 1: Rascunhos prontos para revisão
    prontos = [
        a for a in r["atendimentos"]
        if any(
            p.get("rascunho", {}).get("status") == "pronto"
            for p in a.get("pendencias", [])
        )
    ]
    if prontos:
        linhas.append("")
        linhas.append("🟢 RASCUNHOS PRONTOS PARA REVISÃO:")
        linhas.append("─" * 40)
        for a in prontos:
            espera = a.get("tempo_espera_minutos")
            espera_txt = f" (esperando {_formatar_tempo(espera)})" if espera else ""
            linhas.append(f"\n👤 {a['cliente_nome']}{espera_txt}")
            for p in a.get("pendencias", []):
                if p.get("rascunho", {}).get("status") == "pronto":
                    linhas.append(f"   📩 \"{p['texto_original'][:80]}\"")
                    rascunho_texto = p["rascunho"].get("texto_rascunho", "")
                    if rascunho_texto:
                        # Indentar rascunho
                        for linha_r in rascunho_texto.split("\n"):
                            linhas.append(f"   ✏️  {linha_r}")
                    linhas.append(f"   ⚠️  REQUER REVISÃO antes de enviar")

    # Seção 2: Pendências que precisam de resposta manual
    manuais = [
        a for a in r["atendimentos"]
        if a.get("tem_pendencia") and not any(
            p.get("rascunho", {}).get("status") == "pronto"
            for p in a.get("pendencias", [])
        )
    ]
    if manuais:
        linhas.append("")
        linhas.append("🟡 PENDÊNCIAS — RESPOSTA MANUAL NECESSÁRIA:")
        linhas.append("─" * 40)
        for a in manuais:
            espera = a.get("tempo_espera_minutos")
            espera_txt = f" ({_formatar_tempo(espera)})" if espera else ""
            linhas.append(f"\n👤 {a['cliente_nome']}{espera_txt}")
            for p in a.get("pendencias", []):
                linhas.append(f"   📩 \"{p['texto_original'][:100]}\"")
                classif = p.get("classificacao", {})
                if classif.get("fluxo_nome"):
                    linhas.append(f"   🏷️  Tema: {classif['fluxo_nome']}")

    # Seção 3: Erros
    erros = [a for a in r["atendimentos"] if a.get("erro")]
    if erros:
        linhas.append("")
        linhas.append("❌ ERROS NO PROCESSAMENTO:")
        linhas.append("─" * 40)
        for a in erros:
            linhas.append(f"   • {a['grupo_nome']}: {a['erro'][:80]}")

    linhas.append("")
    linhas.append("═" * 50)
    linhas.append("⚠️  Todos os rascunhos requerem revisão humana")
    linhas.append("    antes de envio ao cliente.")
    linhas.append("═" * 50)

    return "\n".join(linhas)


def _formatar_tempo(minutos):
    """Formata minutos em texto legível."""
    if not minutos:
        return ""
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

    print("\n🧪 Orquestrador Gestta — Testes\n")

    # ─── Teste 1: Pipeline completo com pendência fiscal ──────
    print("── Pipeline Completo (com pendência) ──")
    mensagens_wesley = [
        {
            "remetente": "Arthur",
            "texto": "Segue guia DAS do mês com vencimento para o dia 20/04",
            "timestamp": "15/04/2026 - 20:00",
        },
        {
            "remetente": "Wesley - SW7",
            "texto": "Aumentou a alíquota?",
            "timestamp": "15/04/2026 - 20:08",
        },
        {
            "remetente": "Wesley - SW7",
            "texto": "No último que pagamos não tinha PIS COFINS",
            "timestamp": "16/04/2026 - 10:01",
        },
    ]

    resultado = processar_atendimento(
        mensagens_raw=mensagens_wesley,
        grupo_nome="RRT Contabilidade - Wesley e Suzana",
        horas_limite=720,  # 30 dias para teste
    )

    teste("Tem pendência", resultado["tem_pendencia"], True)
    teste("Cliente correto", resultado["cliente_nome"], "Wesley e Suzana")
    teste("Grupo correto", resultado["grupo_nome"], "RRT Contabilidade - Wesley e Suzana")
    teste("Pendências detectadas > 0", len(resultado["pendencias"]) > 0, True)
    teste("Timestamp de processamento presente",
          "timestamp_processamento" in resultado, True)

    # Verificar que classificação funcionou
    if resultado["pendencias"]:
        primeira = resultado["pendencias"][0]
        teste("Classificação presente", "classificacao" in primeira, True)
        teste("Rascunho presente", "rascunho" in primeira, True)
        classif = primeira.get("classificacao", {})
        teste("Fluxo ID > 0 (classificou)", classif.get("fluxo_id", 0) > 0, True)

    # ─── Teste 2: Pipeline sem pendência ──────────────────────
    print("\n── Pipeline Completo (sem pendência) ──")
    mensagens_ok = [
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

    resultado_ok = processar_atendimento(
        mensagens_raw=mensagens_ok,
        grupo_nome="RRT Contabilidade - Wesley e Suzana",
        horas_limite=720,
    )
    teste("Sem pendência", resultado_ok["tem_pendencia"], False)
    teste("Pendências vazia", len(resultado_ok["pendencias"]), 0)
    teste("Resumo indica OK", "✅" in resultado_ok["resumo"], True)

    # ─── Teste 3: Batch processing ────────────────────────────
    print("\n── Batch Processing ──")
    batch = processar_todos_atendimentos([
        {
            "grupo_nome": "RRT Contabilidade - Wesley e Suzana",
            "mensagens_raw": mensagens_wesley,
        },
        {
            "grupo_nome": "RRT Contabilidade - Alice Arquiteta",
            "mensagens_raw": mensagens_ok,
        },
    ], horas_limite=720)

    teste("Total processados = 2", batch["total_processados"], 2)
    teste("1 com pendência", batch["com_pendencia"], 1)
    teste("Resumo presente", len(batch["resumo_geral"]) > 0, True)

    # ─── Teste 4: Geração de relatório ────────────────────────
    print("\n── Geração de Relatório ──")
    relatorio = gerar_relatorio_gestta(batch)
    teste_contem("Relatório tem cabeçalho", relatorio, "RELATÓRIO DE ATENDIMENTOS GESTTA")
    teste_contem("Relatório tem total", relatorio, "Processados: 2")
    teste_contem("Relatório tem aviso revisão", relatorio, "revisão humana")
    teste("Relatório não está vazio", len(relatorio) > 100, True)

    # ─── Teste 5: Formatação de tempo ─────────────────────────
    print("\n── Formatação de Tempo ──")
    teste("30 min", _formatar_tempo(30), "30min")
    teste("90 min = 1h30min", _formatar_tempo(90), "1h30min")
    teste("120 min = 2h", _formatar_tempo(120), "2h")
    teste("None", _formatar_tempo(None), "")

    # ─── Teste 6: Erro gracioso ──────────────────────────────
    print("\n── Erro Gracioso ──")
    batch_com_erro = processar_todos_atendimentos([
        {
            "grupo_nome": "RRT Contabilidade - Teste Erro",
            "mensagens_raw": None,  # Vai causar erro
        },
    ])
    teste("Batch não crashou", batch_com_erro["total_processados"], 1)
    teste("Erro capturado", "erro" in batch_com_erro["atendimentos"][0], True)

    # ─── Resultado ────────────────────────────────────────────
    print(f"\n{'═' * 50}")
    print(f"  Orquestrador Gestta: {testes_ok}/{testes_total} testes passaram")
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
        print("Uso: python3 orquestrador_gestta.py --teste")
        print("Ou importe: from orquestrador_gestta import processar_atendimento")
