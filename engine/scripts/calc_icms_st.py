#!/usr/bin/env python3
"""
Calculadora de ICMS-ST (Substituição Tributária)
Base legal: Lei Complementar 87/96 (Lei Kandir), com regulamentações estaduais

Calcula o ICMS-ST aplicável na operação interestadual ou intrastadual com
substituição tributária, baseado na Margem de Valor Agregado (MVA) do produto.

Fórmulas:
    BC-ST = (Valor da operação + frete + seguro + outras despesas) × (1 + MVA/100)
    ICMS próprio = Valor da operação × (aliquota_origem / 100)
    ICMS-ST = (BC-ST × aliquota_interna_destino / 100) - ICMS próprio

Se ICMS-ST < 0, considera-se 0 (sem restituição neste cálculo).

Uso:
    python3 calc_icms_st.py --valor 1000 --mva 40 --aliquota 18
    python3 calc_icms_st.py --valor 1000 --mva 40 --aliquota 18 --frete 100 --origem 12
    python3 calc_icms_st.py --teste
"""

import sys
import argparse


def calcular_icms_st(valor_operacao, mva, aliquota_interna, aliquota_origem=None,
                     frete=0.0, seguro=0.0, outras_despesas=0.0):
    """
    Calcula o ICMS-ST (Substituição Tributária).

    Parâmetros:
        - valor_operacao (float): Valor da operação em R$
        - mva (float): Margem de Valor Agregado em % (ex: 40.0 para 40%)
        - aliquota_interna (float): Alíquota ICMS interna do estado de destino em %
        - aliquota_origem (float, REQUIRED): Alíquota ICMS do estado de origem em % — cada UF tem alíquota interna diferente
        - frete (float, default=0): Valor do frete em R$
        - seguro (float, default=0): Valor do seguro em R$
        - outras_despesas (float, default=0): Outras despesas em R$

    Retorna dict com:
        - valor_operacao: valor da operação
        - frete: valor do frete
        - seguro: valor do seguro
        - outras_despesas: valor de outras despesas
        - base_st: base para o ICMS-ST
        - mva_pct: MVA aplicada
        - aliquota_interna_pct: alíquota interna do destino
        - aliquota_origem_pct: alíquota de origem
        - icms_proprio: ICMS próprio (crédito)
        - icms_st_bruto: ICMS-ST antes do ajuste (pode ser negativo)
        - icms_st: ICMS-ST final (0 se bruto for negativo)
    """
    # FIX 6: Make aliquota_origem required
    if aliquota_origem is None:
        return {
            "erro": "aliquota_origem é obrigatória — cada UF tem alíquota interna diferente",
            "icms_st": 0.0,
        }

    # Sanitiza entradas
    valor_operacao = float(valor_operacao)
    mva = float(mva)
    aliquota_interna = float(aliquota_interna)
    aliquota_origem = float(aliquota_origem)
    frete = float(frete)
    seguro = float(seguro)
    outras_despesas = float(outras_despesas)

    # Cálculo da BC-ST
    despesas_acessorias = frete + seguro + outras_despesas
    base_com_despesas = valor_operacao + despesas_acessorias
    bc_st = round(base_com_despesas * (1 + mva / 100), 2)

    # ICMS próprio (crédito)
    icms_proprio = round(valor_operacao * (aliquota_origem / 100), 2)

    # ICMS-ST bruto
    icms_st_bruto = round((bc_st * aliquota_interna / 100) - icms_proprio, 2)

    # ICMS-ST final (0 se negativo — sem restituição)
    icms_st = max(0.0, icms_st_bruto)

    resultado = {
        "valor_operacao": round(valor_operacao, 2),
        "frete": round(frete, 2),
        "seguro": round(seguro, 2),
        "outras_despesas": round(outras_despesas, 2),
        "despesas_acessorias": round(despesas_acessorias, 2),
        "base_st": bc_st,
        "mva_pct": mva,
        "aliquota_interna_pct": aliquota_interna,
        "aliquota_origem_pct": aliquota_origem,
        "icms_proprio": icms_proprio,
        "icms_st_bruto": icms_st_bruto,
        "icms_st": icms_st,
        "tem_restituicao": icms_st_bruto < 0,
        "valor_restituicao": abs(icms_st_bruto) if icms_st_bruto < 0 else 0.0,
    }

    return resultado


def formatar_brl(valor):
    """Formata valor em R$ brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    """Imprime resultado formatado para o terminal."""
    print(f"\n{'='*60}")
    print(f"  CÁLCULO DE ICMS-ST (SUBSTITUIÇÃO TRIBUTÁRIA)")
    print(f"{'='*60}")
    print(f"  Valor da operação:    {formatar_brl(r['valor_operacao'])}")

    if r['frete'] > 0 or r['seguro'] > 0 or r['outras_despesas'] > 0:
        print(f"  Frete:                {formatar_brl(r['frete'])}")
        print(f"  Seguro:               {formatar_brl(r['seguro'])}")
        print(f"  Outras despesas:      {formatar_brl(r['outras_despesas'])}")
        print(f"  ────────────────────────────────────────────────────")
        print(f"  Subtotal:             {formatar_brl(r['valor_operacao'] + r['despesas_acessorias'])}")

    print(f"\n  MVA aplicada:         {r['mva_pct']}%")
    print(f"  Base ST calculada:    {formatar_brl(r['base_st'])}")
    print(f"    (Subtotal × {1 + r['mva_pct']/100:.3f})")

    print(f"\n  Alíquota origem:      {r['aliquota_origem_pct']}%")
    print(f"  ICMS próprio (crédito): {formatar_brl(r['icms_proprio'])}")

    print(f"\n  Alíquota interna:     {r['aliquota_interna_pct']}%")
    print(f"  ICMS ST (cálculo):    {formatar_brl(abs(r['icms_st_bruto']))}", end="")
    if r['tem_restituicao']:
        print(f"  (restituível: {formatar_brl(r['valor_restituicao'])})")
    else:
        print()

    print(f"\n  {'─'*56}")
    print(f"  ICMS-ST A RECOLHER:   {formatar_brl(r['icms_st'])}")
    print(f"{'='*60}\n")


# ─── TESTES INTEGRADOS ────────────────────────────────────────────

def rodar_testes():
    """
    Testes com valores conhecidos para validar o cálculo de ICMS-ST.
    Executa automaticamente e mostra PASSOU/FALHOU.
    """
    testes_ok = 0
    testes_total = 0

    def teste(descricao, esperado_icms_st, **kwargs):
        nonlocal testes_ok, testes_total
        testes_total += 1
        r = calcular_icms_st(**kwargs)
        diff = abs(r["icms_st"] - esperado_icms_st)
        tolerancia = 0.02
        status = "PASSOU" if diff <= tolerancia else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}")
        print(f"           ICMS-ST: {formatar_brl(r['icms_st'])} "
              f"(esperado {formatar_brl(esperado_icms_st)})")
        if status == "FALHOU":
            print(f"           ⚠ Diferença: {formatar_brl(diff)}")
        return r

    print("\n🧪 RODANDO TESTES DO ICMS-ST...")
    print(f"{'─'*60}")

    # Teste 1: Operação básica
    # valor=1000, mva=40%, aliq=18%, origem=18%
    # BC-ST = 1000 × 1.4 = 1400
    # ICMS próprio = 1000 × 18% = 180
    # ICMS-ST = 1400 × 18% - 180 = 252 - 180 = 72
    teste("Teste 1: Operação básica (valor=1000, mva=40%, aliq=18%, origem=18%)",
          72.0,
          valor_operacao=1000, mva=40, aliquota_interna=18, aliquota_origem=18)

    # Teste 2: Com frete
    # valor=1000, frete=200, mva=40%, aliq=18%, origem=18%
    # BC-ST = (1000 + 200) × 1.4 = 1200 × 1.4 = 1680
    # ICMS próprio = 1000 × 18% = 180
    # ICMS-ST = 1680 × 18% - 180 = 302.40 - 180 = 122.40
    teste("Teste 2: Com frete (valor=1000, frete=200, mva=40%)",
          122.40,
          valor_operacao=1000, frete=200, mva=40, aliquota_interna=18, aliquota_origem=18)

    # Teste 3: Alíquota origem diferente (12%)
    # valor=1000, mva=53%, aliq=18%, origem=12%
    # BC-ST = 1000 × 1.53 = 1530
    # ICMS próprio = 1000 × 12% = 120
    # ICMS-ST = 1530 × 18% - 120 = 275.40 - 120 = 155.40
    teste("Teste 3: Alíquota origem 12% (valor=1000, mva=53%, aliq=18%, origem=12%)",
          155.40,
          valor_operacao=1000, mva=53, aliquota_interna=18, aliquota_origem=12)

    # Teste 4: Valor zero
    # Todos os valores devem ser zero
    teste("Teste 4: Valor zero",
          0.0,
          valor_operacao=0, mva=40, aliquota_interna=18, aliquota_origem=18)

    # Teste 5: MVA alta (70%)
    # valor=5000, mva=70%, aliq=18%, origem=18%
    # BC-ST = 5000 × 1.7 = 8500
    # ICMS próprio = 5000 × 18% = 900
    # ICMS-ST = 8500 × 18% - 900 = 1530 - 900 = 630
    teste("Teste 5: MVA alta (valor=5000, mva=70%, aliq=18%)",
          630.0,
          valor_operacao=5000, mva=70, aliquota_interna=18, aliquota_origem=18)

    # Teste 6: MVA zero (apenas diferença de alíquota)
    # valor=1000, mva=0%, aliq=18%, origem=12%
    # BC-ST = 1000 × 1.0 = 1000
    # ICMS próprio = 1000 × 12% = 120
    # ICMS-ST = 1000 × 18% - 120 = 180 - 120 = 60
    teste("Teste 6: MVA zero (valor=1000, mva=0%, aliq=18%, origem=12%)",
          60.0,
          valor_operacao=1000, mva=0, aliquota_interna=18, aliquota_origem=12)

    # Teste 7: Alíquota alta (25% — bebidas)
    # valor=2000, mva=50%, aliq=25%, origem=18%
    # BC-ST = 2000 × 1.5 = 3000
    # ICMS próprio = 2000 × 18% = 360
    # ICMS-ST = 3000 × 25% - 360 = 750 - 360 = 390
    teste("Teste 7: Alíquota 25% (bebidas, valor=2000, mva=50%)",
          390.0,
          valor_operacao=2000, mva=50, aliquota_interna=25, aliquota_origem=18)

    # Teste 8: Com todas as despesas acessórias
    # valor=1000, frete=100, seguro=50, outras=50, mva=40%, aliq=18%, origem=18%
    # BC-ST = (1000 + 100 + 50 + 50) × 1.4 = 1200 × 1.4 = 1680
    # ICMS próprio = 1000 × 18% = 180
    # ICMS-ST = 1680 × 18% - 180 = 302.40 - 180 = 122.40
    teste("Teste 8: Todas despesas (valor=1000, frete=100, seguro=50, outras=50)",
          122.40,
          valor_operacao=1000, frete=100, seguro=50, outras_despesas=50,
          mva=40, aliquota_interna=18, aliquota_origem=18)

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
    # Verifica se é modo teste
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        rodar_testes()
    else:
        # Parser de argumentos CLI
        parser = argparse.ArgumentParser(
            description="Calculadora de ICMS-ST (Substituição Tributária)",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Exemplos de uso:
  python3 calc_icms_st.py --valor 1000 --mva 40 --aliquota 18
  python3 calc_icms_st.py --valor 1000 --mva 40 --aliquota 18 --frete 100 --origem 12
  python3 calc_icms_st.py --teste
            """
        )

        parser.add_argument("--valor", type=float, required=True,
                          help="Valor da operação em R$")
        parser.add_argument("--mva", type=float, required=True,
                          help="Margem de Valor Agregado em %% (ex: 40 para 40%%)")
        parser.add_argument("--aliquota", type=float, required=True,
                          help="Alíquota ICMS interna (destino) em %%")
        parser.add_argument("--origem", type=float, default=18.0,
                          help="Alíquota ICMS origem em %% (padrão: 18)")
        parser.add_argument("--frete", type=float, default=0.0,
                          help="Valor do frete em R$$ (padrão: 0)")
        parser.add_argument("--seguro", type=float, default=0.0,
                          help="Valor do seguro em R$$ (padrão: 0)")
        parser.add_argument("--outras", type=float, default=0.0,
                          help="Outras despesas em R$$ (padrão: 0)")

        args = parser.parse_args()

        try:
            r = calcular_icms_st(
                valor_operacao=args.valor,
                mva=args.mva,
                aliquota_interna=args.aliquota,
                aliquota_origem=args.origem,
                frete=args.frete,
                seguro=args.seguro,
                outras_despesas=args.outras
            )
            imprimir_resultado(r)
        except Exception as e:
            print(f"Erro: {e}")
            sys.exit(1)
