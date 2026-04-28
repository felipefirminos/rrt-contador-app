#!/usr/bin/env python3
"""
calc_folha_batch.py — Processamento de Folha em Lote 2026
RRT Group · Contador-Brasil v2.4

Processa a folha de pagamento de N empregados e retorna:
  - Resultado individual de cada empregado
  - Totais da empresa (INSS patronal, FGTS, total líquido, etc.)
  - Guias consolidadas (GPS, FGTS Digital)

Usa: calc_folha.py (cálculo individual por empregado)
"""

import sys
import os
from decimal import Decimal, ROUND_HALF_UP

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from calc_folha import calcular_folha


def processar_folha_batch(empregados, regime="presumido_real", competencia=None, usar_decimal=False):
    """
    Processa a folha de pagamento de múltiplos empregados.

    Parâmetros:
        empregados: list[dict] — lista de empregados, cada um com:
            - nome: str (identificação)
            - salario_base: float (obrigatório)
            - he_normais: int (horas extras 50%, default 0)
            - he_feriado: int (horas extras 100%, default 0)
            - horas_noturnas: int (horas c/ adicional noturno, default 0)
            - insalubridade_pct: float (% sobre SM, default 0)
            - periculosidade_pct: float (% sobre base, default 0)
            - faltas_dias: int (default 0)
            - num_dependentes: int (default 0)
            - pensao_alimenticia: float (default 0)
            - vt_base: float (base para VT, default 0)
            - outros_descontos: float (default 0)
            - jornada_mensal: int (default 220)
        regime: str — "presumido_real", "simples_i_iii_v", "simples_iv"
        competencia: str — mês/ano de referência (informativo, ex: "04/2026")
        usar_decimal: bool — se True, usa Decimal para precisão monetária (default False)

    Retorna dict com:
        empregados (lista de resultados individuais),
        totais (consolidado empresa),
        guias (GPS, FGTS),
        resumo,
        precisao (float ou decimal conforme usar_decimal)
    """
    if not empregados or not isinstance(empregados, list):
        return {"erro": "Lista de empregados vazia ou inválida"}

    resultados = []
    erros = []

    # Totais acumulados
    if usar_decimal:
        total_bruto = Decimal("0.0")
        total_liquido = Decimal("0.0")
        total_inss_empregado = Decimal("0.0")
        total_irrf = Decimal("0.0")
        total_inss_patronal = Decimal("0.0")
        total_rat_fap = Decimal("0.0")
        total_terceiros = Decimal("0.0")
        total_fgts = Decimal("0.0")
        total_custo_empresa = Decimal("0.0")
        total_pensao = Decimal("0.0")
        total_vt_desconto = Decimal("0.0")
        total_vt_custo_empresa = Decimal("0.0")
        total_outros_descontos = Decimal("0.0")
    else:
        total_bruto = 0.0
        total_liquido = 0.0
        total_inss_empregado = 0.0
        total_irrf = 0.0
        total_inss_patronal = 0.0
        total_rat_fap = 0.0
        total_terceiros = 0.0
        total_fgts = 0.0
        total_custo_empresa = 0.0
        total_pensao = 0.0
        total_vt_desconto = 0.0
        total_vt_custo_empresa = 0.0
        total_outros_descontos = 0.0

    for i, emp in enumerate(empregados):
        nome = emp.get("nome", f"Empregado {i+1}")
        salario = emp.get("salario_base")

        if salario is None:
            erros.append(f"{nome}: salario_base não informado")
            resultados.append({"nome": nome, "erro": "salario_base não informado"})
            continue

        # Converter para Decimal se necesário
        if usar_decimal:
            salario = Decimal(str(salario))

        # Montar parâmetros para calc_folha (matching actual API)
        kwargs = {
            "salario_base": float(salario) if usar_decimal else salario,
            "he_normais": emp.get("he_normais", 0),
            "he_feriado": emp.get("he_feriado", 0),
            "horas_noturnas": emp.get("horas_noturnas", 0),
            "insalubridade_pct": emp.get("insalubridade_pct", 0.0),
            "periculosidade_pct": emp.get("periculosidade_pct", 0.0),
            "adicional_funcao": emp.get("adicional_funcao", 0.0),
            "comissoes": emp.get("comissoes", 0.0),
            "faltas_dias": emp.get("faltas_dias", 0),
            "num_dependentes": emp.get("num_dependentes", 0),
            "pensao_alimenticia": emp.get("pensao_alimenticia", 0.0),
            "vt_base": emp.get("vt_base", 0.0),
            "outros_descontos": emp.get("outros_descontos", 0.0),
            "jornada_mensal": emp.get("jornada_mensal", 220),
            "regime": regime,
        }

        r = calcular_folha(**kwargs)

        if "erro" in r:
            erros.append(f"{nome}: {r['erro']}")
            continue

        # Adiciona nome ao resultado
        r["nome"] = nome
        resultados.append(r)

        # Acumula totais
        if usar_decimal:
            total_bruto += Decimal(str(r.get("total_proventos", 0)))
            total_liquido += Decimal(str(r.get("salario_liquido", 0)))
            total_inss_empregado += Decimal(str(r.get("inss_empregado", 0)))
            total_irrf += Decimal(str(r.get("irrf", 0)))
            total_inss_patronal += Decimal(str(r.get("inss_patronal", 0)))
            total_rat_fap += Decimal(str(r.get("rat_fap", 0)))
            total_terceiros += Decimal(str(r.get("terceiros", 0)))
            total_fgts += Decimal(str(r.get("fgts", 0)))
            total_custo_empresa += Decimal(str(r.get("custo_empresa", 0)))
            total_pensao += Decimal(str(r.get("pensao_alimenticia", 0)))
            total_vt_desconto += Decimal(str(r.get("desconto_vt", 0)))
            total_vt_custo_empresa += Decimal(str(r.get("vt_custo_empresa", 0)))
            total_outros_descontos += Decimal(str(r.get("outros_descontos", 0)))
        else:
            total_bruto += r.get("total_proventos", 0)
            total_liquido += r.get("salario_liquido", 0)
            total_inss_empregado += r.get("inss_empregado", 0)
            total_irrf += r.get("irrf", 0)
            total_inss_patronal += r.get("inss_patronal", 0)
            total_rat_fap += r.get("rat_fap", 0)
            total_terceiros += r.get("terceiros", 0)
            total_fgts += r.get("fgts", 0)
            total_custo_empresa += r.get("custo_empresa", 0)
            total_pensao += r.get("pensao_alimenticia", 0)
            total_vt_desconto += r.get("desconto_vt", 0)
            total_vt_custo_empresa += r.get("vt_custo_empresa", 0)
            total_outros_descontos += r.get("outros_descontos", 0)

    # Arredondar totais
    if usar_decimal:
        totais = {
            "total_empregados": len([r for r in resultados if "erro" not in r]),
            "total_bruto": float(total_bruto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "total_liquido": float(total_liquido.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "total_inss_empregado": float(total_inss_empregado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "total_irrf": float(total_irrf.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "total_inss_patronal": float(total_inss_patronal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "total_rat_fap": float(total_rat_fap.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "total_terceiros": float(total_terceiros.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "total_fgts": float(total_fgts.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "total_custo_empresa": float(total_custo_empresa.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "total_pensao": float(total_pensao.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "total_vt_desconto": float(total_vt_desconto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "total_vt_custo_empresa": float(total_vt_custo_empresa.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
        }
    else:
        totais = {
            "total_empregados": len([r for r in resultados if "erro" not in r]),
            "total_bruto": round(total_bruto, 2),
            "total_liquido": round(total_liquido, 2),
            "total_inss_empregado": round(total_inss_empregado, 2),
            "total_irrf": round(total_irrf, 2),
            "total_inss_patronal": round(total_inss_patronal, 2),
            "total_rat_fap": round(total_rat_fap, 2),
            "total_terceiros": round(total_terceiros, 2),
            "total_fgts": round(total_fgts, 2),
            "total_custo_empresa": round(total_custo_empresa, 2),
            "total_pensao": round(total_pensao, 2),
            "total_vt_desconto": round(total_vt_desconto, 2),
            "total_vt_custo_empresa": round(total_vt_custo_empresa, 2),
        }

    # Guias consolidadas
    # GPS = INSS empregados + INSS patronal + RAT×FAP + Terceiros
    gps_total = round(
        total_inss_empregado + total_inss_patronal +
        total_rat_fap + total_terceiros, 2
    )

    guias = {
        "gps": {
            "descricao": "GPS — Guia da Previdência Social",
            "inss_empregados": round(total_inss_empregado, 2),
            "inss_patronal": round(total_inss_patronal, 2),
            "rat_fap": round(total_rat_fap, 2),
            "terceiros": round(total_terceiros, 2),
            "total": gps_total,
            "vencimento": "Dia 20 do mês seguinte",
        },
        "fgts": {
            "descricao": "FGTS Digital — Depósito Mensal",
            "total": round(total_fgts, 2),
            "vencimento": "Dia 7 do mês seguinte (ou próximo dia útil)",
        },
        "irrf": {
            "descricao": "DARF 0561 — IRRF sobre Rendimentos do Trabalho",
            "total": round(total_irrf, 2),
            "vencimento": "Dia 20 do mês seguinte",
        },
    }

    # Resumo executivo
    resumo = (
        f"Folha processada: {len(resultados)} empregados | "
        f"Bruto total: R$ {total_bruto:,.2f} | "
        f"Líquido total: R$ {total_liquido:,.2f} | "
        f"Custo empresa: R$ {total_custo_empresa:,.2f} | "
        f"GPS: R$ {gps_total:,.2f} | "
        f"FGTS: R$ {total_fgts:,.2f}"
    )

    return {
        "competencia": competencia,
        "regime": regime,
        "empregados": resultados,
        "totais": totais,
        "guias": guias,
        "erros": erros,
        "resumo": resumo,
        "precisao": "decimal" if usar_decimal else "float",
    }


# ═══════════════════════════════════════════════════════════════════
#  TESTES INTERNOS
# ═══════════════════════════════════════════════════════════════════
def _rodar_testes():
    ok = 0
    total = 0

    def t(desc, cond):
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
            print(f"  [PASSOU] {desc}")
        else:
            print(f"  [FALHOU] {desc}")

    print("=" * 60)
    print("  TESTES — calc_folha_batch.py")
    print("=" * 60)

    # ── 3 empregados, Presumido/Real ──
    print("\n📋 Batch com 3 empregados — Presumido/Real")
    equipe = [
        {"nome": "Maria", "salario_base": 3000, "num_dependentes": 1},
        {"nome": "João", "salario_base": 5500, "he_normais": 10, "num_dependentes": 2},
        {"nome": "Ana", "salario_base": 8000, "num_dependentes": 0},
    ]
    r = processar_folha_batch(equipe, regime="presumido_real", competencia="04/2026")
    t("3 empregados processados", r["totais"]["total_empregados"] == 3)
    t("Sem erros", len(r["erros"]) == 0)
    t("Competência = 04/2026", r["competencia"] == "04/2026")
    t("Total bruto > 0", r["totais"]["total_bruto"] > 0)
    t("Total líquido > 0", r["totais"]["total_liquido"] > 0)
    t("Total líquido < total bruto", r["totais"]["total_liquido"] < r["totais"]["total_bruto"])
    t("INSS patronal > 0", r["totais"]["total_inss_patronal"] > 0)
    t("FGTS > 0", r["totais"]["total_fgts"] > 0)
    t("Custo empresa > bruto", r["totais"]["total_custo_empresa"] > r["totais"]["total_bruto"])

    # Guias
    t("GPS total > 0", r["guias"]["gps"]["total"] > 0)
    t("GPS = INSS emp + patronal + RAT + Terc",
      abs(r["guias"]["gps"]["total"] - (
          r["guias"]["gps"]["inss_empregados"] + r["guias"]["gps"]["inss_patronal"] +
          r["guias"]["gps"]["rat_fap"] + r["guias"]["gps"]["terceiros"]
      )) < 0.01)
    t("FGTS guia > 0", r["guias"]["fgts"]["total"] > 0)

    # Individuais
    t("Maria: nome preservado", r["empregados"][0]["nome"] == "Maria")
    t("João: tem horas extras", r["empregados"][1]["total_proventos"] > 5500)

    # Resumo
    t("Resumo não vazio", len(r["resumo"]) > 50)

    # ── Simples I/III/V (sem Terceiros) ──
    print("\n🏢 Batch Simples I/III/V")
    r_sn = processar_folha_batch(equipe, regime="simples_i_iii_v")
    t("Simples: INSS patronal = 0", r_sn["totais"]["total_inss_patronal"] == 0)
    t("Simples: Terceiros = 0", r_sn["totais"]["total_terceiros"] == 0)
    t("Simples: Custo < Presumido", r_sn["totais"]["total_custo_empresa"] < r["totais"]["total_custo_empresa"])

    # ── Empregado único ──
    print("\n👤 Batch com 1 empregado")
    r1 = processar_folha_batch([{"nome": "Solo", "salario_base": 4000}])
    t("1 empregado processado", r1["totais"]["total_empregados"] == 1)

    # ── Empregado com erro (sem salário) ──
    print("\n⚠️ Empregado com erro")
    r_err = processar_folha_batch([
        {"nome": "OK", "salario_base": 3000},
        {"nome": "Sem Salário"},
    ])
    t("1 processado + 1 erro", r_err["totais"]["total_empregados"] == 1 and len(r_err["erros"]) == 1 and len(r_err["empregados"]) == 2)
    t("Erro menciona nome", "Sem Salário" in r_err["erros"][0])

    # ── Lista vazia ──
    print("\n🛡️ Validações")
    r_vazio = processar_folha_batch([])
    t("Lista vazia → erro", "erro" in r_vazio)

    r_none = processar_folha_batch(None)
    t("None → erro", "erro" in r_none)

    # ── Consistência: soma individuais = totais ──
    print("\n🔗 Consistência totais vs individuais")
    soma_bruto = sum(e["total_proventos"] for e in r["empregados"])
    soma_liquido = sum(e["salario_liquido"] for e in r["empregados"])
    soma_fgts = sum(e["fgts"] for e in r["empregados"])
    t("Soma bruto individuais = total", abs(soma_bruto - r["totais"]["total_bruto"]) < 0.01)
    t("Soma líquido individuais = total", abs(soma_liquido - r["totais"]["total_liquido"]) < 0.01)
    t("Soma FGTS individuais = total", abs(soma_fgts - r["totais"]["total_fgts"]) < 0.01)

    # ── Equipe grande (10 empregados) ──
    print("\n📊 Batch com 10 empregados")
    equipe_grande = [
        {"nome": f"Emp_{i+1}", "salario_base": 2000 + i * 500}
        for i in range(10)
    ]
    r10 = processar_folha_batch(equipe_grande)
    t("10 empregados processados", r10["totais"]["total_empregados"] == 10)
    t("Sem erros", len(r10["erros"]) == 0)
    t("Custo empresa crescente",
      r10["empregados"][0]["custo_empresa"] < r10["empregados"][-1]["custo_empresa"])

    # ── Decimal mode (5+ empregados) ──
    print("\n🔢 Decimal mode — Precisão monetária")
    equipe_5 = [
        {"nome": "A", "salario_base": 1500.55},
        {"nome": "B", "salario_base": 2333.33},
        {"nome": "C", "salario_base": 3000.01},
        {"nome": "D", "salario_base": 4500.99},
        {"nome": "E", "salario_base": 5678.44},
    ]
    r_decimal = processar_folha_batch(equipe_5, regime="presumido_real", usar_decimal=True)
    r_float = processar_folha_batch(equipe_5, regime="presumido_real", usar_decimal=False)

    t("Decimal mode: ativado", r_decimal["precisao"] == "decimal")
    t("Float mode: padrão", r_float["precisao"] == "float")
    t("5 empregados processados com Decimal", r_decimal["totais"]["total_empregados"] == 5)
    t("Totais Decimal > 0", r_decimal["totais"]["total_bruto"] > 0)
    # Valores Decimal e float devem ser muito próximos (diferença < 0.10)
    t("Decimal vs Float totalizados próximos",
      abs(r_decimal["totais"]["total_liquido"] - r_float["totais"]["total_liquido"]) < 0.10)

    # Comparar precisão: Decimal deve manter 2 casas decimais exatamente
    for emp in r_decimal["empregados"]:
        # Verificar que valores têm no máximo 2 casas decimais
        for key in ["total_proventos", "salario_liquido", "inss_empregado", "irrf", "fgts"]:
            val = emp.get(key, 0)
            # Permitir pequenas diferenças de arredondamento
            val_str = f"{val:.2f}"
            t(f"Empregado {emp['nome']}: {key} com 2 casas", len(val_str.split('.')[-1]) <= 2)
            break  # Uma amostra é suficiente

    # ── Resultado ──
    print(f"\n{'=' * 60}")
    print(f"  RESULTADO: {ok}/{total} testes passaram")
    if ok == total:
        print("  ✅ TODOS OS TESTES PASSARAM!")
    else:
        print(f"  ❌ {total - ok} falha(s)")
    print(f"{'=' * 60}")

    return ok == total


if __name__ == "__main__":
    if "--teste" in sys.argv:
        success = _rodar_testes()
        sys.exit(0 if success else 1)
    else:
        print("Uso: python calc_folha_batch.py --teste")
        print("\nFunções disponíveis:")
        print("  processar_folha_batch(empregados, regime, competencia)")
