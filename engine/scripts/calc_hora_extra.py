#!/usr/bin/env python3
"""
Calculadora de Horas Extras e DSR (Descanso Semanal Remunerado)
Base legal: CLT Arts. 59, 70; Lei 605/49 (DSR)

Cálculo de horas extras com diferentes alíquotas (dias normais vs. domingos/feriados)
e DSR sobre verbas variáveis (HE + comissões).

Uso:
    python3 calc_hora_extra.py --salario 3000 --horas 10
    python3 calc_hora_extra.py --salario 3000 --horas 10 --feriado 4 --dias-uteis 22 --domingos 8
    python3 calc_hora_extra.py --teste
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def calcular_hora_extra(salario, horas_normais, horas_feriado=0, adicional_normal=50.0,
                        adicional_feriado=100.0, jornada_mensal=220, comissoes=0):
    """
    Calcula horas extras com alíquotas diferenciadas.

    Parâmetros:
        - salario: salário mensal
        - horas_normais: horas extras em dias normais (50% mínimo)
        - horas_feriado: horas extras em domingos/feriados (100% mínimo)
        - adicional_normal: percentual adicional para dias normais (default 50%)
        - adicional_feriado: percentual adicional para domingos/feriados (default 100%)
        - jornada_mensal: horas mensais de trabalho (default 220h para 44h/sem)
        - comissoes: comissões (para cálculo do DSR)

    Retorna dict com valores discriminados.
    """
    # Calcula valor da hora normal
    hora_normal = salario / jornada_mensal if jornada_mensal > 0 else 0

    # Horas extras em dias normais
    fator_normal = 1 + (adicional_normal / 100)
    valor_he_normal = round(hora_normal * fator_normal * horas_normais, 2)

    # Horas extras em domingos/feriados
    fator_feriado = 1 + (adicional_feriado / 100)
    valor_he_feriado = round(hora_normal * fator_feriado * horas_feriado, 2)

    # Total de horas extras
    total_he = round(valor_he_normal + valor_he_feriado, 2)

    # Total variáveis (para DSR)
    total_variaveis = round(total_he + comissoes, 2)

    return {
        "salario": salario,
        "jornada_mensal": jornada_mensal,
        "hora_normal": round(hora_normal, 2),
        "horas_normais": horas_normais,
        "adicional_normal_pct": adicional_normal,
        "fator_normal": round(fator_normal, 2),
        "valor_he_normal": valor_he_normal,
        "horas_feriado": horas_feriado,
        "adicional_feriado_pct": adicional_feriado,
        "fator_feriado": round(fator_feriado, 2),
        "valor_he_feriado": valor_he_feriado,
        "total_he": total_he,
        "comissoes": comissoes,
        "total_variaveis": total_variaveis,
        "base_legal_he": "CLT Arts. 59 (normal), 70 (feriado)",
    }


def calcular_dsr(total_variaveis, dias_uteis, domingos_feriados):
    """
    Calcula DSR (Descanso Semanal Remunerado) sobre verbas variáveis.

    Parâmetros:
        - total_variaveis: soma de HE + comissões
        - dias_uteis: dias úteis do mês
        - domingos_feriados: domingos + feriados do mês

    Retorna float com valor do DSR.
    """
    if dias_uteis == 0 or total_variaveis == 0:
        return 0.0

    dsr = round((total_variaveis / dias_uteis) * domingos_feriados, 2)
    return dsr


def formatar_brl(valor):
    """Formata valor em R$ brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r, dsr=None):
    """Imprime resultado formatado para o terminal."""
    print(f"\n{'='*60}")
    print(f"  CÁLCULO DE HORAS EXTRAS E DSR")
    print(f"{'='*60}")
    print(f"  Salário mensal:        {formatar_brl(r['salario'])}")
    print(f"  Jornada mensal:        {r['jornada_mensal']}h")
    print(f"  Valor da hora normal:  {formatar_brl(r['hora_normal'])}")

    print(f"\n  {'─'*55}")
    print(f"  HORAS EXTRAS EM DIAS NORMAIS (adicional {r['adicional_normal_pct']:.0f}%):")
    print(f"  Horas:                 {r['horas_normais']}h")
    print(f"  Fator (1 + {r['adicional_normal_pct']:.0f}%):  {r['fator_normal']}")
    print(f"  Valor:                 {formatar_brl(r['valor_he_normal'])}")

    if r['horas_feriado'] > 0:
        print(f"\n  {'─'*55}")
        print(f"  HORAS EXTRAS EM DOMINGOS/FERIADOS (adicional {r['adicional_feriado_pct']:.0f}%):")
        print(f"  Horas:                 {r['horas_feriado']}h")
        print(f"  Fator (1 + {r['adicional_feriado_pct']:.0f}%):  {r['fator_feriado']}")
        print(f"  Valor:                 {formatar_brl(r['valor_he_feriado'])}")

    print(f"\n  {'─'*55}")
    print(f"  TOTAL HORAS EXTRAS:    {formatar_brl(r['total_he'])}")
    if r['comissoes'] > 0:
        print(f"  Comissões:             {formatar_brl(r['comissoes'])}")
        print(f"  Total variáveis:       {formatar_brl(r['total_variaveis'])}")

    if dsr is not None and dsr > 0:
        print(f"\n  {'─'*55}")
        print(f"  DSR (Descanso Semanal Remunerado):")
        print(f"  Valor:                 {formatar_brl(dsr)}")
        print(f"  ⚖️  Base legal: Lei 605/49 (Lei do Repouso Semanal Remunerado)")

    print(f"{'='*60}\n")


# ─── TESTES INTEGRADOS ────────────────────────────────────────────

def rodar_testes():
    """
    Testes com valores conhecidos para validar cálculos de HE e DSR.
    Executa automaticamente e mostra PASSOU/FALHOU.
    """
    testes_ok = 0
    testes_total = 0

    def teste_he(descricao, salario, horas, feriado=0, campo="total_he", esperado=None,
                 jornada=220, adicional_n=50.0, adicional_f=100.0, tol=0.1):
        nonlocal testes_ok, testes_total
        testes_total += 1
        r = calcular_hora_extra(salario, horas, feriado, adicional_n, adicional_f, jornada)
        valor = r[campo]
        if esperado is None:
            # Se não informado esperado, apenas mostra
            print(f"  [INFO ] {descricao}: {campo}={formatar_brl(valor)}")
            testes_ok += 1
            return

        diff = abs(valor - esperado)
        status = "PASSOU" if diff <= tol else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}: {formatar_brl(valor)} "
              f"(esperado {formatar_brl(esperado)})")
        if status == "FALHOU":
            print(f"         ⚠ Diff: {formatar_brl(diff)}")

    def teste_dsr(descricao, total_var, dias_uteis, dom_fer, esperado, tol=0.1):
        nonlocal testes_ok, testes_total
        testes_total += 1
        dsr = calcular_dsr(total_var, dias_uteis, dom_fer)
        diff = abs(dsr - esperado)
        status = "PASSOU" if diff <= tol else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}: {formatar_brl(dsr)} "
              f"(esperado {formatar_brl(esperado)})")
        if status == "FALHOU":
            print(f"         ⚠ Diff: {formatar_brl(diff)}")

    print("\n🧪 RODANDO TESTES DE HORAS EXTRAS E DSR...")
    print(f"{'─'*65}")

    # ═══════════════════════════════════════════════════════════════
    # TESTES DE HORAS EXTRAS
    # ═══════════════════════════════════════════════════════════════

    print(f"\n  ▶ TESTES DE HORAS EXTRAS:")

    # Teste 1: HE básica (50% em dias normais)
    # Salário: 3000, jornada: 220h
    # Hora normal: 3000 / 220 = 13.636363...
    # HE: 13.636363 × 1.5 × 10 = 204.545454... ≈ 204.55
    teste_he("1. HE básica (50%, dias normais): sal=3000, 10h",
             3000, 10, 0, "total_he", 204.55)

    # Teste 2: HE em feriado (100%)
    # Hora normal: 13.636363
    # HE feriado: 13.636363 × 2.0 × 5 = 136.363636... ≈ 136.36
    teste_he("2. HE em feriado (100%): sal=3000, 5h feriado",
             3000, 0, 5, "total_he", 136.36)

    # Teste 3: HE mista (dias normais + feriados)
    # HE normal: 204.55 + HE feriado: 136.36 = 340.91
    teste_he("3. HE mista: sal=3000, 10h normais + 5h feriado",
             3000, 10, 5, "total_he", 340.91)

    # Teste 4: Jornada diferente (180h)
    # Hora normal: 3000 / 180 = 16.666666...
    # HE: 16.666666 × 1.5 × 10 = 250.00
    teste_he("4. Jornada 180h: sal=3000, 10h",
             3000, 10, 0, "total_he", 250.00, jornada=180)

    # Teste 5: Zero horas
    teste_he("5. Zero horas: sal=3000, 0h",
             3000, 0, 0, "total_he", 0.00)

    # Teste 6: Salário alto, poucas horas
    # Hora normal: 15000 / 220 = 68.181818...
    # HE: 68.181818 × 1.5 × 2 = 204.545454... ≈ 204.55
    teste_he("6. Salário alto: sal=15000, 2h normais",
             15000, 2, 0, "total_he", 204.55)

    # Teste 7: Adicional diferente (CCT 70%)
    # Hora normal: 3000 / 220 = 13.636363
    # HE: 13.636363 × 1.7 × 10 = 231.818181... ≈ 231.82
    teste_he("7. Adicional 70% (CCT): sal=3000, 10h",
             3000, 10, 0, "total_he", 231.82, adicional_n=70.0)

    # Teste 8: Salário zero
    teste_he("8. Salário zero: sal=0, 10h",
             0, 10, 0, "total_he", 0.00)

    # ═══════════════════════════════════════════════════════════════
    # TESTES DE DSR
    # ═══════════════════════════════════════════════════════════════

    print(f"\n  ▶ TESTES DE DSR (Descanso Semanal Remunerado):")

    # Teste 9: DSR simples
    # Total var: 340.91, dias úteis: 22, dom/feriados: 8
    # DSR: (340.91 / 22) × 8 = 15.495909 × 8 = 123.967272... ≈ 123.97
    teste_dsr("9. DSR simples: total=340.91, dias=22, dom=8",
              340.91, 22, 8, 123.97)

    # Teste 10: DSR com comissões
    # HE: 500, Comissões: 300, Total: 800
    # Dias úteis: 25, Dom: 5
    # DSR: (800 / 25) × 5 = 32 × 5 = 160.00
    teste_dsr("10. DSR com comissões: HE=500+com=300, dias=25, dom=5",
              800, 25, 5, 160.00)

    print(f"{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ❌ Há falhas — VERIFICAR antes de usar em produção")
    print()
    return testes_ok == testes_total


# ─── MAIN ────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        rodar_testes()
    elif "--salario" in sys.argv:
        try:
            salario = float(sys.argv[sys.argv.index("--salario") + 1])
        except (IndexError, ValueError):
            print("Erro: informe --salario <valor>")
            sys.exit(1)

        horas = float(sys.argv[sys.argv.index("--horas") + 1]) if "--horas" in sys.argv else 0
        feriado = float(sys.argv[sys.argv.index("--feriado") + 1]) if "--feriado" in sys.argv else 0
        dias_uteis = int(sys.argv[sys.argv.index("--dias-uteis") + 1]) if "--dias-uteis" in sys.argv else 0
        domingos = int(sys.argv[sys.argv.index("--domingos") + 1]) if "--domingos" in sys.argv else 0
        comissoes = float(sys.argv[sys.argv.index("--comissoes") + 1]) if "--comissoes" in sys.argv else 0
        jornada = float(sys.argv[sys.argv.index("--jornada") + 1]) if "--jornada" in sys.argv else 220
        adic_normal = float(sys.argv[sys.argv.index("--adic-normal") + 1]) if "--adic-normal" in sys.argv else 50.0
        adic_feriado = float(sys.argv[sys.argv.index("--adic-feriado") + 1]) if "--adic-feriado" in sys.argv else 100.0

        r = calcular_hora_extra(salario, horas, feriado, adic_normal, adic_feriado, jornada, comissoes)
        dsr = None
        if dias_uteis > 0 and domingos > 0:
            dsr = calcular_dsr(r["total_variaveis"], dias_uteis, domingos)
        imprimir_resultado(r, dsr)
    else:
        print("Uso: python3 calc_hora_extra.py --salario <valor> --horas <qtd> [--feriado <qtd>]")
        print("       [--dias-uteis <int>] [--domingos <int>] [--comissoes <valor>]")
        print("       [--jornada <horas>] [--adic-normal <pct>] [--adic-feriado <pct>]")
        print("      python3 calc_hora_extra.py --teste")
