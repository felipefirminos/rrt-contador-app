#!/usr/bin/env python3
"""
Calculadora de DIFAL (Diferencial de Alíquota de ICMS)
Base legal: EC 87/2015, 100% destinado ao estado de destino desde 2022

DIFAL = Base de cálculo × (Alíquota interna do destino - Alíquota interestadual)

Alíquotas interestaduais:
  - Sul/Sudeste (exceto ES): 12%
  - Norte/Nordeste/Centro-Oeste/ES: 7%
  - Importações: 4%

Uso:
    python3 calc_difal.py --valor 1000 --destino 18 --inter 12
    python3 calc_difal.py --valor 1000 --destino 20 --inter 7
    python3 calc_difal.py --teste
"""

import sys


def calcular_difal(valor_operacao, aliquota_destino, aliquota_interestadual,
                   frete=0.0, seguro=0.0, outras_despesas=0.0):
    """
    Calcula o DIFAL (Diferencial de Alíquota de ICMS).

    Parâmetros:
        - valor_operacao (float): Valor da operação (base inicial)
        - aliquota_destino (float): Alíquota interna do estado de destino em %
        - aliquota_interestadual (float): Alíquota interestadual em %
        - frete (float): Valor do frete
        - seguro (float): Valor do seguro
        - outras_despesas (float): Outras despesas

    Base de cálculo = valor_operacao + frete + seguro + outras_despesas

    Retorna dict com:
        - valor_operacao
        - base_calculo
        - aliquota_destino_pct
        - aliquota_interestadual_pct
        - diferencial_aliquota_pct
        - difal
        - data_100pct_destino: indicativo de que 100% vai para destino (pós 2022)
    """
    base_calculo = round(valor_operacao + frete + seguro + outras_despesas, 2)

    # Converte percentuais para decimais
    aliq_dest = aliquota_destino / 100.0
    aliq_inter = aliquota_interestadual / 100.0

    # Diferencial de alíquota
    diferencial = aliq_dest - aliq_inter
    diferencial_pct = round(diferencial * 100, 2)

    # DIFAL = Base × Diferencial
    difal = round(base_calculo * diferencial, 2)

    return {
        "valor_operacao": round(valor_operacao, 2),
        "frete": round(frete, 2),
        "seguro": round(seguro, 2),
        "outras_despesas": round(outras_despesas, 2),
        "base_calculo": base_calculo,
        "aliquota_destino_pct": aliquota_destino,
        "aliquota_interestadual_pct": aliquota_interestadual,
        "diferencial_aliquota_pct": diferencial_pct,
        "difal": difal,
        "destino_100_pct": True,  # Sempre 100% para destino desde 2022
    }


def formatar_brl(valor):
    """Formata valor em R$ brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    """Imprime resultado formatado para o terminal."""
    print(f"\n{'='*55}")
    print(f"  CÁLCULO DE DIFAL (EC 87/2015)")
    print(f"{'='*55}")
    print(f"  Valor da operação:  {formatar_brl(r['valor_operacao'])}")
    if r["frete"] > 0:
        print(f"  (+) Frete:          {formatar_brl(r['frete'])}")
    if r["seguro"] > 0:
        print(f"  (+) Seguro:         {formatar_brl(r['seguro'])}")
    if r["outras_despesas"] > 0:
        print(f"  (+) Outras desp.:   {formatar_brl(r['outras_despesas'])}")
    print(f"  Base de cálculo:    {formatar_brl(r['base_calculo'])}")
    print(f"  {'─'*50}")
    print(f"  Alíquota destino:   {r['aliquota_destino_pct']}%")
    print(f"  Alíquota interest.: {r['aliquota_interestadual_pct']}%")
    print(f"  Diferencial:        {r['diferencial_aliquota_pct']}%")
    print(f"  {'─'*50}")
    print(f"  DIFAL a pagar:      {formatar_brl(r['difal'])}")
    print(f"  Destino (2022+):    100% para o estado de destino")
    print(f"{'='*55}\n")


# ─── TESTES INTEGRADOS ────────────────────────────────────────────

def rodar_testes():
    """
    Testes com valores conhecidos para validar o cálculo do DIFAL.
    Executa automaticamente e mostra PASSOU/FALHOU.
    """
    testes_ok = 0
    testes_total = 0

    def teste(descricao, valor, destino, inter, frete, seguro, outras, esperado, tolerancia=0.02):
        nonlocal testes_ok, testes_total
        testes_total += 1
        r = calcular_difal(valor, destino, inter, frete, seguro, outras)
        diff = abs(r["difal"] - esperado)
        status = "PASSOU" if diff <= tolerancia else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}: DIFAL {formatar_brl(r['difal'])} "
              f"(esperado {formatar_brl(esperado)})")
        if status == "FALHOU":
            print(f"         ⚠ Diferença: {formatar_brl(diff)} | base: {formatar_brl(r['base_calculo'])}")

    print("\n🧪 RODANDO TESTES DO DIFAL (EC 87/2015 — 100% destino)...")
    print(f"{'─'*60}")

    # Teste 1: SP→MG (dest=18%, inter=12%)
    # DIFAL = 1000 × (18% - 12%) = 1000 × 6% = 60.00
    teste("SP→MG (dest=18%, inter=12%)", 1000.00, 18, 12, 0, 0, 0, 60.00)

    # Teste 2: SP→BA (dest=18%, inter=7%)
    # DIFAL = 1000 × (18% - 7%) = 1000 × 11% = 110.00
    teste("SP→BA (dest=18%, inter=7%)", 1000.00, 18, 7, 0, 0, 0, 110.00)

    # Teste 3: SP→RJ (dest=20%, inter=12%)
    # DIFAL = 5000 × (20% - 12%) = 5000 × 8% = 400.00
    teste("SP→RJ (dest=20%, inter=12%)", 5000.00, 20, 12, 0, 0, 0, 400.00)

    # Teste 4: Importação (dest=18%, inter=4%)
    # DIFAL = 1000 × (18% - 4%) = 1000 × 14% = 140.00
    teste("Importação (dest=18%, inter=4%)", 1000.00, 18, 4, 0, 0, 0, 140.00)

    # Teste 5: Com frete (valor=1000, frete=200, dest=18%, inter=12%)
    # BC = 1000 + 200 = 1200
    # DIFAL = 1200 × (18% - 12%) = 1200 × 6% = 72.00
    teste("Com frete (BC=1200, dest=18%, inter=12%)", 1000.00, 18, 12, 200, 0, 0, 72.00)

    # Teste 6: Mesmo estado (dest=18%, inter=18%)
    # DIFAL = 1000 × (18% - 18%) = 1000 × 0% = 0.00
    teste("Mesmo estado (dest=18%, inter=18%)", 1000.00, 18, 18, 0, 0, 0, 0.00)

    # Teste 7: Valor zero
    # DIFAL = 0 × (18% - 12%) = 0.00
    teste("Valor zero", 0.00, 18, 12, 0, 0, 0, 0.00)

    # Teste 8: Grande valor com todas as despesas
    # valor=50000, frete=2000, seguro=500, outras=500
    # BC = 50000 + 2000 + 500 + 500 = 53000
    # DIFAL = 53000 × (21% - 7%) = 53000 × 14% = 7420.00
    teste("Grande valor (BC=53000, dest=21%, inter=7%)", 50000.00, 21, 7, 2000, 500, 500, 7420.00)

    print(f"{'─'*60}")
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
    elif "--valor" in sys.argv and "--destino" in sys.argv and "--inter" in sys.argv:
        try:
            idx_valor = sys.argv.index("--valor")
            valor = float(sys.argv[idx_valor + 1].replace(",", "."))

            idx_destino = sys.argv.index("--destino")
            aliquota_destino = float(sys.argv[idx_destino + 1].replace(",", "."))

            idx_inter = sys.argv.index("--inter")
            aliquota_inter = float(sys.argv[idx_inter + 1].replace(",", "."))

            # Parâmetros opcionais
            frete = 0.0
            if "--frete" in sys.argv:
                idx_frete = sys.argv.index("--frete")
                frete = float(sys.argv[idx_frete + 1].replace(",", "."))

            seguro = 0.0
            if "--seguro" in sys.argv:
                idx_seguro = sys.argv.index("--seguro")
                seguro = float(sys.argv[idx_seguro + 1].replace(",", "."))

            outras_despesas = 0.0
            if "--outras" in sys.argv:
                idx_outras = sys.argv.index("--outras")
                outras_despesas = float(sys.argv[idx_outras + 1].replace(",", "."))

            r = calcular_difal(valor, aliquota_destino, aliquota_inter, frete, seguro, outras_despesas)
            imprimir_resultado(r)

        except (ValueError, IndexError) as e:
            print("Erro: verifique os parâmetros.")
            print("Uso: python3 calc_difal.py --valor <valor> --destino <aliq%> --inter <aliq%>")
            print("                             [--frete <frete>] [--seguro <seguro>] [--outras <outras>]")
            sys.exit(1)
    else:
        print("Uso: python3 calc_difal.py --valor <valor> --destino <aliq%> --inter <aliq%>")
        print("                             [--frete <frete>] [--seguro <seguro>] [--outras <outras>]")
        print("      python3 calc_difal.py --teste")
        print("\nExemplos:")
        print("      python3 calc_difal.py --valor 1000 --destino 18 --inter 12")
        print("      python3 calc_difal.py --valor 1000 --destino 20 --inter 7 --frete 200")
