#!/usr/bin/env python3
"""
calc_prolabore.py — Calculadora de Pró-labore 2026
RRT Group · Contador-Brasil v6.1 (release 2026-04-27)

Calcula o custo total e líquido do pró-labore para sócios.

Regras 2026:
  - INSS do sócio: **11% FIXO** (contribuinte individual, IN RFB 971/2009 art. 65),
    limitado ao teto de R$ 8.475,55 (Portaria Interministerial MPS/MF nº 13/2026).
    NUNCA aplique a tabela progressiva (7,5% / 9% / 12% / 14%) ao sócio — essa
    é a tabela do EMPREGADO CLT. Erro recorrente identificado em auditoria
    técnica interna (23/04/2026).

  - INSS patronal: 20% sobre o pró-labore
    → Simples Anexos I, II, III, **V**: ISENTO (CPP já no DAS — LC 123 art. 13 §3°).
       NÃO some 20% × pró-labore para o Anexo V — esse foi o segundo erro
       identificado na mesma auditoria.
    → Simples Anexo IV, Presumido, Lucro Real: 20% recolhidos separadamente.

  - IRRF: tabela progressiva Lei 15.270/2025
    → Isenção até R$ 5.000 de renda
    → Redução gradual R$ 5.000 a R$ 7.350
  - Pró-labore mínimo: 1 SM (R$ 1.621,00)

Resumo dos cálculos no teto (sócio com pró-labore acima de R$ 8.475,55):
  - INSS sócio (11% fixo, correto):                            R$ 932,31
  - Tabela progressiva empregado (NÃO aplicar a sócio):        R$ 988,10
  - Diferença (erro identificado na auditoria):                R$  55,79

Usa: calc_irrf.py (tabela IRRF com Lei 15.270/2025)

Base legal:
  - IN RFB 971/2009, art. 65 (contribuinte individual — alíquota fixa 11%)
  - LC 123/2006, art. 13, § 3° (isenção CPP Simples I/II/III/V)
  - LC 123/2006, art. 18, § 5°-C (Anexo IV — CPP separada)
  - Lei 15.270/2025 (nova faixa IRRF)
  - Portaria Interministerial MPS/MF nº 13/2026 (teto e salário mínimo)
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from calc_irrf import calcular_irrf

# ─── Constantes 2026 ──────────────────────────────────────────────
SALARIO_MINIMO = 1621.00
TETO_INSS = 8475.55
INSS_SOCIO_PCT = 11.0
INSS_PATRONAL_PCT = 20.0

# Regimes onde CPP patronal é paga separadamente sobre pró-labore
REGIMES_COM_CPP = ["presumido", "lucro_real", "simples_iv"]
# Regimes onde CPP já está no DAS (isento de patronal separado)
REGIMES_SEM_CPP = ["simples_i", "simples_ii", "simples_iii", "simples_v",
                   "simples_i_iii_v"]  # atalho genérico


def calcular_prolabore(valor_bruto, regime="presumido", num_dependentes=0,
                       pensao_alimenticia=0.0):
    """
    Calcula o pró-labore completo de um sócio.

    Parâmetros:
        valor_bruto: float — valor bruto do pró-labore
        regime: str — "presumido", "lucro_real", "simples_iv",
                      "simples_i", "simples_ii", "simples_iii", "simples_v",
                      "simples_i_iii_v"
        num_dependentes: int — dependentes para IRRF
        pensao_alimenticia: float — pensão para IRRF

    Retorna dict com:
        valor_bruto, inss_socio, inss_patronal, irrf, valor_liquido,
        custo_empresa, custo_total_mensal, custo_total_anual,
        regime, base_legal, alertas
    """
    regime = regime.lower().strip()

    # Validações
    alertas = []

    if valor_bruto < 0:
        return {"erro": "Valor bruto não pode ser negativo"}

    if valor_bruto < SALARIO_MINIMO and valor_bruto > 0:
        alertas.append(
            f"⚠️ Pró-labore abaixo do salário mínimo (R$ {SALARIO_MINIMO:,.2f}). "
            "O mínimo obrigatório é 1 SM para sócios que exercem atividade na empresa."
        )

    regimes_validos = REGIMES_COM_CPP + REGIMES_SEM_CPP
    if regime not in regimes_validos:
        return {"erro": f"Regime inválido: '{regime}'. Use: {', '.join(regimes_validos)}"}

    # ── INSS do sócio (11% fixo, teto) ──
    base_inss = min(valor_bruto, TETO_INSS)
    inss_socio = round(base_inss * INSS_SOCIO_PCT / 100, 2)

    teto_aplicado = valor_bruto > TETO_INSS
    if teto_aplicado:
        alertas.append(
            f"Teto INSS aplicado: contribuição limitada a R$ {round(TETO_INSS * INSS_SOCIO_PCT / 100, 2):,.2f} "
            f"(11% de R$ {TETO_INSS:,.2f})"
        )

    # ── INSS patronal (20%) ──
    tem_cpp = regime in REGIMES_COM_CPP
    if tem_cpp:
        inss_patronal = round(valor_bruto * INSS_PATRONAL_PCT / 100, 2)
    else:
        inss_patronal = 0.0
        alertas.append(
            f"Regime {regime.upper()}: CPP patronal já incluída no DAS. "
            "Não há recolhimento separado de INSS patronal sobre pró-labore."
        )

    # ── IRRF (usa calc_irrf com Lei 15.270/2025) ──
    r_irrf = calcular_irrf(
        salario_bruto=valor_bruto,
        num_dependentes=num_dependentes,
        pensao_alimenticia=pensao_alimenticia,
        inss_descontado=inss_socio,
    )
    irrf = r_irrf["irrf"]

    # ── Líquido e custo ──
    valor_liquido = round(valor_bruto - inss_socio - irrf - pensao_alimenticia, 2)
    custo_empresa = round(valor_bruto + inss_patronal, 2)
    custo_total_mensal = custo_empresa  # custo para a empresa = bruto + patronal
    custo_total_anual = round(custo_total_mensal * 12, 2)

    # Alíquota efetiva total de encargos
    if valor_bruto > 0:
        encargo_total_pct = round((inss_socio + inss_patronal + irrf) / valor_bruto * 100, 2)
    else:
        encargo_total_pct = 0.0

    return {
        "valor_bruto": valor_bruto,
        "regime": regime,
        # INSS
        "inss_socio": inss_socio,
        "inss_socio_aliquota_pct": INSS_SOCIO_PCT,
        "base_inss": base_inss,
        "teto_inss_aplicado": teto_aplicado,
        "inss_patronal": inss_patronal,
        "inss_patronal_aliquota_pct": INSS_PATRONAL_PCT if tem_cpp else 0.0,
        "cpp_inclusa_no_das": not tem_cpp,
        # IRRF
        "irrf": irrf,
        "irrf_faixa": r_irrf.get("faixa_aplicada", ""),
        "irrf_isencao_5000": r_irrf.get("isencao_5000_aplicada", False),
        "irrf_reducao_gradual": r_irrf.get("reducao_gradual_aplicada", False),
        "irrf_metodo": r_irrf.get("metodo_escolhido", ""),
        # Pensão
        "pensao_alimenticia": pensao_alimenticia,
        # Resultados
        "valor_liquido": valor_liquido,
        "custo_empresa_mensal": custo_empresa,
        "custo_empresa_anual": custo_total_anual,
        "encargo_total_pct": encargo_total_pct,
        # Dependentes
        "num_dependentes": num_dependentes,
        # Meta
        "salario_minimo_2026": SALARIO_MINIMO,
        "teto_inss_2026": TETO_INSS,
        "alertas": alertas,
        "base_legal": "IN RFB 971/2009, art. 57; LC 123/2006, art. 13 §3°; Lei 15.270/2025",
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
    print("  TESTES — calc_prolabore.py")
    print("=" * 60)

    # ── Pró-labore salário mínimo, Lucro Presumido ──
    print("\n📋 Pró-labore no SM (R$ 1.621) — Presumido")
    r1 = calcular_prolabore(1621.00, regime="presumido")
    t("INSS sócio = 11% de 1621 = R$ 178,31", abs(r1["inss_socio"] - 178.31) < 0.01)
    t("INSS patronal = 20% de 1621 = R$ 324,20", abs(r1["inss_patronal"] - 324.20) < 0.01)
    t("IRRF = 0 (isento até R$ 5.000)", r1["irrf"] == 0)
    t("Líquido = 1621 - 178,31 = R$ 1.442,69", abs(r1["valor_liquido"] - 1442.69) < 0.01)
    t("Custo empresa = 1621 + 324,20 = R$ 1.945,20", abs(r1["custo_empresa_mensal"] - 1945.20) < 0.01)

    # ── R$ 5.000 — Isenção IRRF (Lei 15.270/2025) ──
    print("\n💰 Pró-labore R$ 5.000 — Presumido")
    r2 = calcular_prolabore(5000, regime="presumido")
    inss_5k = round(5000 * 0.11, 2)  # 550.00
    t("INSS sócio = R$ 550,00", abs(r2["inss_socio"] - 550.00) < 0.01)
    t("IRRF = 0 (isenção nova)", r2["irrf"] == 0)
    t("Patronal = R$ 1.000", abs(r2["inss_patronal"] - 1000) < 0.01)

    # ── R$ 10.000 — IRRF incide ──
    print("\n📈 Pró-labore R$ 10.000 — Presumido")
    r3 = calcular_prolabore(10_000, regime="presumido")
    t("INSS sócio = R$ 932,31 (11% de 8.475,55)", abs(r3["inss_socio"] - 932.31) < 0.02)
    t("Teto INSS aplicado", r3["teto_inss_aplicado"] is True)
    t("INSS patronal = R$ 2.000 (20% de 10K)", abs(r3["inss_patronal"] - 2000) < 0.01)
    t("IRRF > 0", r3["irrf"] > 0)
    t("Líquido < bruto", r3["valor_liquido"] < 10_000)
    t("Custo empresa = R$ 12.000", abs(r3["custo_empresa_mensal"] - 12_000) < 0.01)

    # ── Simples I/III/V — sem CPP patronal ──
    print("\n🏢 Pró-labore R$ 5.000 — Simples I/III/V (sem CPP)")
    r4 = calcular_prolabore(5000, regime="simples_i_iii_v")
    t("CPP inclusa no DAS", r4["cpp_inclusa_no_das"] is True)
    t("INSS patronal = 0", r4["inss_patronal"] == 0)
    t("Custo empresa = bruto (sem patronal)", abs(r4["custo_empresa_mensal"] - 5000) < 0.01)

    # ── Simples IV — COM CPP patronal ──
    print("\n🏗️ Pró-labore R$ 5.000 — Simples IV (com CPP)")
    r5 = calcular_prolabore(5000, regime="simples_iv")
    t("CPP NÃO inclusa no DAS", r5["cpp_inclusa_no_das"] is False)
    t("INSS patronal = R$ 1.000", abs(r5["inss_patronal"] - 1000) < 0.01)
    t("Custo empresa = R$ 6.000", abs(r5["custo_empresa_mensal"] - 6000) < 0.01)

    # ── Lucro Real ──
    print("\n📊 Pró-labore R$ 8.000 — Lucro Real")
    r6 = calcular_prolabore(8000, regime="lucro_real")
    t("INSS sócio = 11% de 8.000 = R$ 880", abs(r6["inss_socio"] - 880) < 0.01)
    t("INSS patronal = 20% de 8.000 = R$ 1.600", abs(r6["inss_patronal"] - 1600) < 0.01)
    t("IRRF > 0 (acima da faixa de isenção)", r6["irrf"] > 0)
    t("Teto INSS não aplicado", r6["teto_inss_aplicado"] is False)

    # ── Valor alto (acima do teto INSS) ──
    print("\n🔝 Pró-labore R$ 30.000 — Presumido")
    r7 = calcular_prolabore(30_000, regime="presumido")
    inss_teto = round(TETO_INSS * 0.11, 2)
    t(f"INSS sócio limitado ao teto = R$ {inss_teto}", abs(r7["inss_socio"] - inss_teto) < 0.01)
    t("INSS patronal = 20% de 30K = R$ 6.000", abs(r7["inss_patronal"] - 6000) < 0.01)
    t("Custo empresa = R$ 36.000", abs(r7["custo_empresa_mensal"] - 36_000) < 0.01)
    t("Custo anual = R$ 432.000", abs(r7["custo_empresa_anual"] - 432_000) < 0.01)
    t("IRRF alto (faixa 27,5%)", r7["irrf"] > 3000)

    # ── Dependentes afetam IRRF ──
    print("\n👨‍👩‍👧 Com dependentes")
    r8_sem = calcular_prolabore(8000, regime="presumido", num_dependentes=0)
    r8_com = calcular_prolabore(8000, regime="presumido", num_dependentes=3)
    t("3 dependentes reduz IRRF", r8_com["irrf"] < r8_sem["irrf"])
    t("3 dependentes aumenta líquido", r8_com["valor_liquido"] > r8_sem["valor_liquido"])

    # ── Validações ──
    print("\n🛡️ Validações")
    r_neg = calcular_prolabore(-1000)
    t("Valor negativo → erro", "erro" in r_neg)

    r_regime = calcular_prolabore(5000, regime="xyz")
    t("Regime inválido → erro", "erro" in r_regime)

    r_baixo = calcular_prolabore(1000, regime="presumido")
    t("Abaixo do SM → alerta", len(r_baixo["alertas"]) > 0 and "mínimo" in r_baixo["alertas"][0])

    # ── Zero (sócio sem pró-labore) ──
    print("\n⚠️ Edge cases")
    r_zero = calcular_prolabore(0, regime="presumido")
    t("Pró-labore R$ 0 = tudo zero", r_zero["inss_socio"] == 0 and r_zero["irrf"] == 0)

    # ── Comparação regimes: custo empresa ──
    print("\n⚖️ Comparação de regimes")
    rp = calcular_prolabore(5000, regime="presumido")
    rs = calcular_prolabore(5000, regime="simples_i_iii_v")
    t("Custo Presumido > Simples I/III/V (CPP)", rp["custo_empresa_mensal"] > rs["custo_empresa_mensal"])
    diferenca = rp["custo_empresa_mensal"] - rs["custo_empresa_mensal"]
    t("Diferença = patronal (R$ 1.000)", abs(diferenca - 1000) < 0.01)

    # Todos os regimes válidos processam sem erro
    for reg in REGIMES_COM_CPP + REGIMES_SEM_CPP:
        r = calcular_prolabore(3000, regime=reg)
        t(f"Regime {reg}: processa sem erro", "erro" not in r)

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
        print("Uso: python calc_prolabore.py --teste")
        print("\nFunções disponíveis:")
        print("  calcular_prolabore(valor_bruto, regime, num_dependentes, pensao)")
