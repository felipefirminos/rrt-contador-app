#!/usr/bin/env python3
"""
Gerador de Rascunhos de Resposta WhatsApp — RRT-Group-Contador v4.2

Recebe a saída de ponte_whatsapp.py (classificação + cálculo) e gera
um rascunho de mensagem formatado para WhatsApp, pronto para revisão
pelo contador antes do envio.

⚠️  REGRA ABSOLUTA: Este módulo NUNCA envia mensagens automaticamente.
    Toda saída é RASCUNHO que requer aprovação humana.

Uso:
    python3 rascunho_resposta.py --teste

Importação:
    from rascunho_resposta import gerar_rascunho, gerar_relatorio_pendencias
"""

import sys
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from output_formatter import formatar_brl, VERSAO_SKILL


# ═══════════════════════════════════════════════════════════════
# FORMATADORES POR FLUXO
# Cada formatador transforma o resultado do calculador em texto
# natural para WhatsApp (sem markdown pesado — WhatsApp suporta
# apenas *negrito*, _itálico_ e ```código```)
# ═══════════════════════════════════════════════════════════════

def _fmt_simples(resultado, params):
    """Formata resultado do DAS Simples Nacional."""
    r = resultado
    das = r.get("das_mensal", r.get("valor_das", 0))
    aliq_efetiva = r.get("aliquota_efetiva", r.get("aliquota_efetiva_pct", 0))

    linhas = [
        f"📊 *Cálculo DAS — Simples Nacional*",
        f"",
        f"Receita no mês: {formatar_brl(params.get('receita_mes', 0))}",
        f"DAS a pagar: *{formatar_brl(das)}*",
    ]
    if aliq_efetiva:
        linhas.append(f"Alíquota efetiva: {aliq_efetiva:.2f}%")

    return "\n".join(linhas)


def _fmt_rescisao(resultado, params):
    """Formata resultado de rescisão trabalhista."""
    r = resultado
    tipo_nome = {
        "sem_justa_causa": "Demissão sem justa causa",
        "pedido_demissao": "Pedido de demissão",
        "justa_causa": "Justa causa",
        "acordo_mutuo": "Acordo mútuo (Art. 484-A)",
    }
    tipo = params.get("tipo", "sem_justa_causa")

    linhas = [
        f"📋 *Cálculo Rescisão — {tipo_nome.get(tipo, tipo)}*",
        f"",
        f"Salário base: {formatar_brl(r.get('salario_base', 0))}",
        f"Saldo de salário: {formatar_brl(r.get('saldo_salario', 0))}",
        f"Aviso prévio: {formatar_brl(r.get('aviso_previo_valor', 0))}",
        f"13° proporcional: {formatar_brl(r.get('decimo_terceiro_prop', 0))}",
        f"Férias proporcionais + 1/3: {formatar_brl(r.get('ferias_proporcionais', 0) + r.get('terco_ferias_proporcionais', 0))}",
    ]
    if r.get("ferias_vencidas", 0) > 0:
        linhas.append(f"Férias vencidas + 1/3: {formatar_brl(r.get('ferias_vencidas', 0) + r.get('terco_ferias_vencidas', 0))}")

    linhas.extend([
        f"",
        f"Total bruto: {formatar_brl(r.get('total_bruto', 0))}",
        f"INSS: -{formatar_brl(r.get('inss_normal', 0))}",
        f"IRRF: -{formatar_brl(r.get('irrf_total', 0))}",
        f"",
        f"💰 *Líquido estimado: {formatar_brl(r.get('total_liquido', 0))}*",
    ])

    if r.get("multa_fgts", 0) > 0:
        linhas.append(f"Multa FGTS: {formatar_brl(r.get('multa_fgts', 0))}")
    if r.get("direito_saque_fgts"):
        pct = r.get("saque_fgts_percentual", 1.0)
        if pct < 1.0:
            linhas.append(f"Saque FGTS: limitado a {pct:.0%} do saldo")
        else:
            linhas.append(f"Saque FGTS: integral")

    return "\n".join(linhas)


def _fmt_custo_clt(resultado, params):
    """Formata custo total CLT."""
    r = resultado
    linhas = [
        f"💼 *Custo Total do Empregado CLT*",
        f"",
        f"Salário bruto: {formatar_brl(r.get('salario_bruto', 0))}",
        f"INSS patronal: {formatar_brl(r.get('inss_patronal', 0))}",
        f"RAT×FAP: {formatar_brl(r.get('rat_fap', 0))}",
        f"Terceiros: {formatar_brl(r.get('terceiros', 0))}",
        f"FGTS: {formatar_brl(r.get('fgts', 0))}",
        f"Provisão 13°: {formatar_brl(r.get('provisao_13', 0))}",
        f"Provisão férias+1/3: {formatar_brl(r.get('provisao_ferias', 0))}",
        f"",
        f"📈 *Custo mensal total: {formatar_brl(r.get('custo_mensal', 0))}*",
        f"Custo anual: {formatar_brl(r.get('custo_anual', 0))}",
        f"Encargos sobre salário: {r.get('percentual_encargos', 0):.1f}%",
    ]
    return "\n".join(linhas)


def _fmt_folha(resultado, params):
    """Formata holerite/contracheque."""
    r = resultado
    linhas = [
        f"📄 *Folha de Pagamento*",
        f"",
        f"Total proventos: {formatar_brl(r.get('total_proventos', 0))}",
        f"INSS empregado: -{formatar_brl(r.get('inss_empregado', 0))}",
        f"IRRF: -{formatar_brl(r.get('irrf', 0))}",
    ]
    if r.get("desconto_vt", 0) > 0:
        linhas.append(f"VT: -{formatar_brl(r.get('desconto_vt', 0))}")
    linhas.extend([
        f"Total descontos: -{formatar_brl(r.get('total_descontos', 0))}",
        f"",
        f"💰 *Salário líquido: {formatar_brl(r.get('salario_liquido', 0))}*",
    ])
    return "\n".join(linhas)


def _fmt_prolabore(resultado, params):
    """Formata pró-labore."""
    r = resultado
    linhas = [
        f"👔 *Pró-labore*",
        f"",
        f"Valor bruto: {formatar_brl(r.get('valor_bruto', r.get('prolabore_bruto', 0)))}",
        f"INSS (11%): -{formatar_brl(r.get('inss_socio', r.get('inss_contribuinte', 0)))}",
        f"IRRF: -{formatar_brl(r.get('irrf', 0))}",
        f"",
        f"💰 *Líquido: {formatar_brl(r.get('liquido', r.get('valor_liquido', 0)))}*",
    ]
    if r.get("inss_patronal", 0) > 0:
        linhas.append(f"INSS patronal (empresa): {formatar_brl(r.get('inss_patronal', 0))}")
    return "\n".join(linhas)


def _fmt_generico(resultado, params):
    """Formatador genérico para fluxos sem formatador específico."""
    linhas = ["📊 *Resultado do Cálculo*", ""]
    for k, v in resultado.items():
        if k.startswith("_") or k in ("base_legal", "disclaimer", "timestamp"):
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            linhas.append(f"{k}: {formatar_brl(v) if v > 100 else v}")
        elif isinstance(v, str) and len(v) < 200:
            linhas.append(f"{k}: {v}")
    return "\n".join(linhas[:20])  # max 20 linhas


FORMATADORES = {
    2: _fmt_simples,
    3: _fmt_rescisao,
    8: _fmt_custo_clt,
    14: _fmt_folha,
    20: _fmt_prolabore,
}


# ═══════════════════════════════════════════════════════════════
# GERADOR DE RASCUNHO
# ═══════════════════════════════════════════════════════════════

def gerar_rascunho(resultado_ponte):
    """
    Gera rascunho de resposta WhatsApp a partir do resultado de ponte_whatsapp.

    Args:
        resultado_ponte: dict retornado por executar_calculo()

    Returns:
        dict com:
            - rascunho: str — texto formatado para WhatsApp
            - status: "pronto", "incompleto", "manual", "ignorar"
            - fluxo_id: int
            - grupo_nome: str
            - cliente_nome: str
            - requer_revisao: bool (sempre True)
            - motivo_revisao: str
            - timestamp: str
    """
    fluxo_id = resultado_ponte.get("fluxo_id", 0)
    pode_responder = resultado_ponte.get("pode_responder", False)
    necessita_info = resultado_ponte.get("necessita_mais_info", False)
    resultado_calc = resultado_ponte.get("resultado_calculo")
    params = resultado_ponte.get("params_usados", {})

    base = {
        "fluxo_id": fluxo_id,
        "fluxo_nome": resultado_ponte.get("fluxo_nome", "N/A"),
        "grupo_nome": resultado_ponte.get("grupo_nome"),
        "cliente_nome": resultado_ponte.get("cliente_nome"),
        "pergunta_original": resultado_ponte.get("pergunta_resumida", ""),
        "requer_revisao": True,  # SEMPRE True — nunca auto-enviar
        "timestamp": datetime.now().isoformat(),
    }

    # Caso 1: Pode responder com cálculo
    if pode_responder and resultado_calc:
        formatador = FORMATADORES.get(fluxo_id, _fmt_generico)
        corpo = formatador(resultado_calc, params)

        disclaimer = (
            f"\n\n_⚠️ Cálculo estimado (RRT-Group-Contador v{VERSAO_SKILL}). "
            f"Valores sujeitos a confirmação pelo contador._"
        )

        rascunho = f"{corpo}{disclaimer}"

        return {
            **base,
            "rascunho": rascunho,
            "status": "pronto",
            "motivo_revisao": "Cálculo automático — verificar se os parâmetros assumidos estão corretos para este cliente.",
        }

    # Caso 2: Faltam parâmetros
    if necessita_info:
        sugestao = resultado_ponte.get("sugestao_pergunta", "Pode fornecer mais detalhes?")
        return {
            **base,
            "rascunho": f"❓ {sugestao}",
            "status": "incompleto",
            "motivo_revisao": f"Parâmetros insuficientes: {', '.join(resultado_ponte.get('params_faltantes', []))}. Sugestão de pergunta ao cliente gerada.",
        }

    # Caso 3: Não classificável (fluxo_id == 0 ou confiança nenhuma)
    if fluxo_id == 0 or resultado_ponte.get("confianca_classificacao") == "nenhuma":
        return {
            **base,
            "rascunho": "",
            "status": "ignorar",
            "motivo_revisao": "Mensagem não contém pergunta contábil/fiscal classificável.",
        }

    # Caso 4: Fluxo reconhecido mas sem calculador ou erro
    if resultado_ponte.get("erro"):
        return {
            **base,
            "rascunho": "",
            "status": "manual",
            "motivo_revisao": resultado_ponte["erro"],
        }

    # Fallback
    return {
        **base,
        "rascunho": "",
        "status": "manual",
        "motivo_revisao": "Situação não prevista — requer análise manual.",
    }


# ═══════════════════════════════════════════════════════════════
# RELATÓRIO DE PENDÊNCIAS (integração monitora-whatsapp)
# ═══════════════════════════════════════════════════════════════

def gerar_relatorio_pendencias(resultados_ponte):
    """
    Gera relatório consolidado de todas as pendências processadas.
    Input: lista de resultados de processar_pendencias()

    Returns:
        dict com:
            - total: int
            - prontos: list[dict] — rascunhos prontos para envio
            - incompletos: list[dict] — precisam de mais info
            - manuais: list[dict] — requerem resposta humana
            - ignorados: list[dict] — sem pergunta contábil
            - resumo_texto: str — resumo formatado
    """
    rascunhos = [gerar_rascunho(r) for r in resultados_ponte]

    prontos = [r for r in rascunhos if r["status"] == "pronto"]
    incompletos = [r for r in rascunhos if r["status"] == "incompleto"]
    manuais = [r for r in rascunhos if r["status"] == "manual"]
    ignorados = [r for r in rascunhos if r["status"] == "ignorar"]

    resumo = [
        "╔═══════════════════════════════════════════════════╗",
        "║  RELATÓRIO DE PENDÊNCIAS — Ponte WhatsApp→Calc   ║",
        "╠═══════════════════════════════════════════════════╣",
        f"║  Total processado:    {len(rascunhos):>3}                        ║",
        f"║  ✅ Prontos (cálculo): {len(prontos):>3}                        ║",
        f"║  ❓ Precisam de info:  {len(incompletos):>3}                        ║",
        f"║  ✋ Resposta manual:   {len(manuais):>3}                        ║",
        f"║  ⏭️  Ignorados:        {len(ignorados):>3}                        ║",
        "╚═══════════════════════════════════════════════════╝",
    ]

    if prontos:
        resumo.append("\n🟢 RASCUNHOS PRONTOS:")
        for r in prontos:
            grupo = r.get("grupo_nome", "?")
            cliente = r.get("cliente_nome", "?")
            resumo.append(f"  • {grupo} ({cliente})")
            resumo.append(f"    {r['pergunta_original'][:80]}")
            resumo.append("")

    if incompletos:
        resumo.append("\n🟡 PRECISAM DE MAIS INFORMAÇÃO:")
        for r in incompletos:
            grupo = r.get("grupo_nome", "?")
            resumo.append(f"  • {grupo}: {r['motivo_revisao'][:80]}")

    if manuais:
        resumo.append("\n🔴 REQUEREM RESPOSTA MANUAL:")
        for r in manuais:
            grupo = r.get("grupo_nome", "?")
            resumo.append(f"  • {grupo}: {r['motivo_revisao'][:80]}")

    return {
        "total": len(rascunhos),
        "prontos": prontos,
        "incompletos": incompletos,
        "manuais": manuais,
        "ignorados": ignorados,
        "resumo_texto": "\n".join(resumo),
    }


# ═══════════════════════════════════════════════════════════════
# TESTES
# ═══════════════════════════════════════════════════════════════

def rodar_testes():
    from classificar_mensagem import classificar_mensagem, classificar_lote
    from ponte_whatsapp import executar_calculo, processar_pendencias

    testes_ok = 0
    testes_total = 0

    def teste(descricao, resultado, campo, esperado):
        nonlocal testes_ok, testes_total
        testes_total += 1
        obtido = resultado.get(campo)
        passou = obtido == esperado
        if passou:
            testes_ok += 1
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}")
        if not passou:
            print(f"         {campo}: {obtido!r} (esperado {esperado!r})")

    def teste_contem(descricao, texto, substring):
        nonlocal testes_ok, testes_total
        testes_total += 1
        passou = substring in texto
        if passou:
            testes_ok += 1
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}")
        if not passou:
            print(f"         Texto não contém: {substring!r}")

    print("\n🧪 RODANDO TESTES DO GERADOR DE RASCUNHOS...")
    print(f"{'─'*65}")

    # ═══ Rascunho de Rescisão ═══
    print("\n  ── Rascunho: Rescisão ──")
    c = classificar_mensagem("Rescisão sem justa causa, salário R$ 4.500, 5 anos de casa")
    p = executar_calculo(c)
    r = gerar_rascunho(p)
    teste("Rescisão: status pronto", r, "status", "pronto")
    teste("Rescisão: requer revisão", r, "requer_revisao", True)
    teste_contem("Rescisão: rascunho contém emoji", r["rascunho"], "📋")
    teste_contem("Rescisão: rascunho contém 'Líquido'", r["rascunho"], "Líquido")
    teste_contem("Rescisão: rascunho contém disclaimer", r["rascunho"], "⚠️")

    # ═══ Rascunho de Folha ═══
    print("\n  ── Rascunho: Folha ──")
    c = classificar_mensagem("Holerite de R$ 5.000 bruto")
    p = executar_calculo(c)
    r = gerar_rascunho(p)
    teste("Folha: status pronto", r, "status", "pronto")
    teste_contem("Folha: contém 'Salário líquido'", r["rascunho"], "Salário líquido")

    # ═══ Rascunho incompleto ═══
    print("\n  ── Rascunho: Parâmetros Insuficientes ──")
    c = classificar_mensagem("Quanto de DAS esse mês?")
    p = executar_calculo(c)
    r = gerar_rascunho(p)
    teste("Incompleto: status", r, "status", "incompleto")
    teste_contem("Incompleto: sugere pergunta", r["rascunho"], "❓")

    # ═══ Rascunho manual ═══
    print("\n  ── Rascunho: Resposta Manual ──")
    c = classificar_mensagem("Qual o prazo do eSocial esse mês?")
    p = executar_calculo(c)
    r = gerar_rascunho(p)
    teste("Manual: status", r, "status", "manual")
    teste("Manual: rascunho vazio", r, "rascunho", "")

    # ═══ Ignorar saudação ═══
    print("\n  ── Rascunho: Ignorar ──")
    c = classificar_mensagem("Bom dia pessoal!")
    p = executar_calculo(c)
    r = gerar_rascunho(p)
    teste("Ignorar: status", r, "status", "ignorar")

    # ═══ Relatório consolidado ═══
    print("\n  ── Relatório de Pendências ──")
    msgs = [
        {"texto": "Quanto de DAS? Faturei R$ 40.000", "cliente_nome": "João", "grupo_nome": "RRT Contabilidade - Tech LTDA"},
        {"texto": "Bom dia!", "cliente_nome": "Ana", "grupo_nome": "RRT Contabilidade - Padaria"},
        {"texto": "Rescisão do Pedro, 3 anos, R$ 3.500", "cliente_nome": "Carlos", "grupo_nome": "RRT Contabilidade - Metalúrgica"},
        {"texto": "Qual prazo do eSocial?", "cliente_nome": "Marcos", "grupo_nome": "RRT Contabilidade - Consultoria"},
        {"texto": "Quanto pago de prolabore de 4 mil?", "cliente_nome": "Rita", "grupo_nome": "RRT Contabilidade - Design"},
    ]
    classificacoes = classificar_lote(msgs)
    resultados_ponte = processar_pendencias(classificacoes)
    relatorio = gerar_relatorio_pendencias(resultados_ponte)

    teste("Relatório: total = 5", relatorio, "total", 5)
    teste("Relatório: 3 prontos", {"n": len(relatorio["prontos"])}, "n", 3)
    teste("Relatório: 1 ignorado", {"n": len(relatorio["ignorados"])}, "n", 1)
    teste_contem("Relatório: resumo contém 'PRONTOS'", relatorio["resumo_texto"], "PRONTOS")

    print(f"\n{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ❌ Há falhas — VERIFICAR antes de usar em produção")
    print()
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        ok = rodar_testes()
        sys.exit(0 if ok else 1)
    else:
        print("Uso: python3 rascunho_resposta.py --teste")
        print("\nGerador de rascunhos de resposta WhatsApp — RRT-Group-Contador")
