#!/usr/bin/env python3
"""
Calculadora de Férias — com tratamento correto de abono pecuniário
Base legal: CLT Arts. 129-153, Art. 144 (abono), Súmula 386 TST

REGRA CRÍTICA: Abono pecuniário + 1/3 do abono são ISENTOS de INSS e IRRF.
A base de cálculo de INSS e IRRF deve EXCLUIR o abono.

Uso:
    python3 calc_ferias.py --salario 5800 --dias 30
    python3 calc_ferias.py --salario 5800 --dias 30 --abono 10
    python3 calc_ferias.py --teste
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from calc_inss import calcular_inss
from calc_irrf import calcular_irrf


def calcular_ferias(salario, dias_ferias=30, dias_abono=0, num_dependentes=0,
                    media_adicionais=0):
    """
    Calcula férias com tratamento correto de incidências.

    Parâmetros:
        - salario: salário mensal
        - dias_ferias: dias de férias gozadas (mínimo 20 se abono, ou 30)
        - dias_abono: dias vendidos (abono pecuniário, máximo 10)
        - num_dependentes: para cálculo do IRRF
        - media_adicionais: média de HE, noturno etc. (incorpora ao cálculo)

    Retorna dict com valores e incidências discriminados.
    """
    # Validação: salário deve ser positivo
    salario = max(0, salario)
    media_adicionais = max(0, media_adicionais)

    base_diaria = (salario + media_adicionais) / 30

    # Verbas
    ferias_gozadas = round(base_diaria * dias_ferias, 2)
    terco_ferias = round(ferias_gozadas / 3, 2)
    abono_pecuniario = round(base_diaria * dias_abono, 2) if dias_abono > 0 else 0
    terco_abono = round(abono_pecuniario / 3, 2) if dias_abono > 0 else 0

    # Totais
    total_tributavel = round(ferias_gozadas + terco_ferias, 2)
    total_isento = round(abono_pecuniario + terco_abono, 2)
    total_bruto = round(total_tributavel + total_isento, 2)

    # INSS: incide APENAS sobre férias gozadas + 1/3 (NÃO sobre abono)
    r_inss = calcular_inss(total_tributavel)
    inss = r_inss["inss_total"]

    # IRRF: incide APENAS sobre férias gozadas + 1/3 - INSS (NÃO sobre abono)
    r_irrf = calcular_irrf(
        total_tributavel,
        num_dependentes=num_dependentes,
        inss_descontado=inss,
    )
    irrf = r_irrf["irrf"]

    total_descontos = round(inss + irrf, 2)
    total_liquido = round(total_bruto - total_descontos, 2)

    return {
        "salario": salario,
        "media_adicionais": media_adicionais,
        "base_diaria": round(base_diaria, 2),
        "dias_ferias": dias_ferias,
        "dias_abono": dias_abono,
        # Verbas tributáveis
        "ferias_gozadas": ferias_gozadas,
        "terco_constitucional": terco_ferias,
        "subtotal_tributavel": total_tributavel,
        # Verbas isentas
        "abono_pecuniario": abono_pecuniario,
        "terco_abono": terco_abono,
        "subtotal_isento": total_isento,
        # Totais
        "total_bruto": total_bruto,
        # Descontos (apenas sobre verbas tributáveis)
        "base_inss": total_tributavel,
        "inss": inss,
        "base_irrf": round(total_tributavel - inss, 2),
        "irrf": irrf,
        "total_descontos": total_descontos,
        # Líquido
        "total_liquido": total_liquido,
        # Notas legais
        "base_legal_abono_isento": "CLT Art. 144 + Súmula 386 TST + Decreto 3.048/99 Art. 214 §9° VII",
        "base_legal_ferias": "CLT Arts. 129-153, CF Art. 7° XVII",
    }


def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    print(f"\n{'='*60}")
    print(f"  CÁLCULO DE FÉRIAS")
    print(f"{'='*60}")
    print(f"  Salário base:          {formatar_brl(r['salario'])}")
    if r["media_adicionais"] > 0:
        print(f"  Média de adicionais:   {formatar_brl(r['media_adicionais'])}")
    print(f"  Base diária:           {formatar_brl(r['base_diaria'])}")
    print(f"  Dias de férias:        {r['dias_ferias']}")
    if r["dias_abono"] > 0:
        print(f"  Dias de abono:         {r['dias_abono']}")

    print(f"\n  {'─'*55}")
    print(f"  VERBAS TRIBUTÁVEIS (incide INSS e IRRF):")
    print(f"  Férias gozadas ({r['dias_ferias']}d):  {formatar_brl(r['ferias_gozadas'])}")
    print(f"  1/3 constitucional:    {formatar_brl(r['terco_constitucional'])}")
    print(f"  Subtotal tributável:   {formatar_brl(r['subtotal_tributavel'])}")

    if r["dias_abono"] > 0:
        print(f"\n  VERBAS ISENTAS (NÃO incide INSS nem IRRF):")
        print(f"  Abono pecuniário:      {formatar_brl(r['abono_pecuniario'])}")
        print(f"  1/3 sobre abono:       {formatar_brl(r['terco_abono'])}")
        print(f"  Subtotal isento:       {formatar_brl(r['subtotal_isento'])}")
        print(f"  ⚖️  Base legal: {r['base_legal_abono_isento']}")

    print(f"\n  {'─'*55}")
    print(f"  TOTAL BRUTO:           {formatar_brl(r['total_bruto'])}")
    print(f"  (-) INSS (base: {formatar_brl(r['base_inss'])}): {formatar_brl(r['inss'])}")
    print(f"  (-) IRRF (base: {formatar_brl(r['base_irrf'])}): {formatar_brl(r['irrf'])}")
    print(f"  {'─'*55}")
    print(f"  ▶ TOTAL LÍQUIDO:       {formatar_brl(r['total_liquido'])}")
    print(f"{'='*60}\n")


# ─── TESTES ──────────────────────────────────────────────────────

def rodar_testes():
    testes_ok = 0
    testes_total = 0

    def teste(descricao, salario, dias, abono, campo, esperado, tol=1.0):
        nonlocal testes_ok, testes_total
        testes_total += 1
        r = calcular_ferias(salario, dias, abono)
        valor = r[campo]
        diff = abs(valor - esperado)
        status = "PASSOU" if diff <= tol else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}: {campo}={formatar_brl(valor)} (esperado ~{formatar_brl(esperado)})")
        if status == "FALHOU":
            print(f"         ⚠ Diff: {formatar_brl(diff)}")

    print("\n🧪 RODANDO TESTES DE FÉRIAS...")
    print(f"{'─'*65}")

    # Teste 1: Férias simples 30 dias, salário R$ 5.800
    # Férias: 5800. 1/3: 1933.33. Total: 7733.33
    teste("Férias 30d, sem abono — férias", 5800, 30, 0, "ferias_gozadas", 5800.00)
    teste("Férias 30d, sem abono — 1/3", 5800, 30, 0, "terco_constitucional", 1933.33)
    teste("Férias 30d, sem abono — bruto", 5800, 30, 0, "total_bruto", 7733.33)

    # Teste 2: Férias 20d + abono 10d, salário R$ 5.800
    # Férias (20d): 5800/30 × 20 = 3866.67. 1/3: 1288.89
    # Abono (10d): 5800/30 × 10 = 1933.33. 1/3 abono: 644.44
    teste("Férias 20d + abono — férias gozadas", 5800, 20, 10, "ferias_gozadas", 3866.67)
    teste("Férias 20d + abono — 1/3 férias", 5800, 20, 10, "terco_constitucional", 1288.89)
    teste("Férias 20d + abono — abono", 5800, 20, 10, "abono_pecuniario", 1933.33)
    teste("Férias 20d + abono — 1/3 abono", 5800, 20, 10, "terco_abono", 644.44)

    # TESTE CRÍTICO: Base do INSS exclui abono
    # Base INSS = 3866.67 + 1288.89 = 5155.56 (NÃO 7733.33)
    teste("CRÍTICO: Base INSS exclui abono", 5800, 20, 10, "base_inss", 5155.56)

    # TESTE CRÍTICO: Total isento
    teste("CRÍTICO: Subtotal isento", 5800, 20, 10, "subtotal_isento", 2577.77)

    # Teste 3: Salário mínimo, 30 dias
    teste("Salário mínimo — bruto", 1518, 30, 0, "total_bruto", 2024.00)

    print(f"{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ❌ Há falhas — VERIFICAR")
    print()
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        rodar_testes()
    elif "--salario" in sys.argv:
        salario = float(sys.argv[sys.argv.index("--salario") + 1])
        dias = int(sys.argv[sys.argv.index("--dias") + 1]) if "--dias" in sys.argv else 30
        abono = int(sys.argv[sys.argv.index("--abono") + 1]) if "--abono" in sys.argv else 0
        deps = int(sys.argv[sys.argv.index("--dependentes") + 1]) if "--dependentes" in sys.argv else 0
        r = calcular_ferias(salario, dias, abono, deps)
        imprimir_resultado(r)
    else:
        print("Uso: python3 calc_ferias.py --salario 5800 --dias 30 [--abono 10] [--dependentes 2]")
        print("      python3 calc_ferias.py --teste")
