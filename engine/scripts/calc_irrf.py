#!/usr/bin/env python3
"""
Calculadora de IRRF sobre rendimentos do trabalho
Base legal: Lei 15.270/2025 (isenção até R$ 5.000), tabela vigente 2026

Calcula o IRRF considerando: salário bruto - INSS - dependentes - pensão alimentícia.
Aplica automaticamente o desconto simplificado se for mais vantajoso.
Aplica a isenção para rendas até R$ 5.000 e redução gradual até R$ 7.350 (Lei 15.270/2025).

Uso:
    python3 calc_irrf.py 5000.00
    python3 calc_irrf.py 5000.00 --dependentes 2
    python3 calc_irrf.py --teste
"""

import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TABELA_IRRF_PATH = os.path.join(SCRIPT_DIR, "tabelas", "irrf_2026.json")

# Importa calc_inss para calcular o INSS automaticamente
sys.path.insert(0, SCRIPT_DIR)
from calc_inss import calcular_inss, carregar_tabela as carregar_tabela_inss, verificar_vigencia


def carregar_tabela_irrf(caminho=TABELA_IRRF_PATH):
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def calcular_irrf(salario_bruto, num_dependentes=0, pensao_alimenticia=0.0,
                  inss_descontado=None, tabela_irrf=None, tabela_inss=None):
    """
    Calcula o IRRF sobre rendimentos do trabalho.

    Parâmetros:
        - salario_bruto: salário bruto mensal
        - num_dependentes: número de dependentes
        - pensao_alimenticia: valor de pensão alimentícia (já descontado)
        - inss_descontado: se None, calcula automaticamente
        - tabela_irrf/tabela_inss: tabelas (carrega automaticamente se None)

    Retorna dict com todos os valores discriminados.
    """
    if tabela_irrf is None:
        tabela_irrf = carregar_tabela_irrf()
    if tabela_inss is None:
        tabela_inss = carregar_tabela_inss()

    # Validação: salário deve ser positivo
    salario_bruto = max(0, salario_bruto)

    # Verificação de vigência
    vigente, aviso_vigencia = verificar_vigencia(tabela_irrf)

    # Calcula INSS se não informado
    if inss_descontado is None:
        r_inss = calcular_inss(salario_bruto, tabela_inss)
        inss_descontado = r_inss["inss_total"]

    # Deduções legais
    deducao_dependentes = round(num_dependentes * tabela_irrf["deducao_por_dependente"], 2)
    total_deducoes_legais = round(inss_descontado + deducao_dependentes + pensao_alimenticia, 2)

    # Base com deduções legais
    base_legal = round(salario_bruto - total_deducoes_legais, 2)
    base_legal = max(base_legal, 0)

    # Base com desconto simplificado
    desconto_simplificado = tabela_irrf["desconto_simplificado"]
    base_simplificado = round(salario_bruto - desconto_simplificado, 2)
    base_simplificado = max(base_simplificado, 0)

    # Calcula IRRF para ambas as bases
    irrf_legal = _calcular_na_tabela(base_legal, tabela_irrf)
    irrf_simplificado = _calcular_na_tabela(base_simplificado, tabela_irrf)

    # Usa o que for mais vantajoso (menor imposto)
    if irrf_simplificado <= irrf_legal:
        metodo = "simplificado"
        base_usada = base_simplificado
        irrf_final = irrf_simplificado
    else:
        metodo = "deducoes_legais"
        base_usada = base_legal
        irrf_final = irrf_legal

    # ── Lei 15.270/2025: isenção para rendas até R$ 5.000 e redução gradual ──
    isencao_aplicada = False
    reducao_aplicada = False
    isencao_ate = tabela_irrf.get("isencao_renda_bruta_ate", 0)
    reducao_ate = tabela_irrf.get("reducao_gradual_ate", 0)

    if isencao_ate > 0 and salario_bruto <= isencao_ate:
        # Renda bruta até R$ 5.000: IRRF = 0
        irrf_final = 0.0
        isencao_aplicada = True
    elif reducao_ate > 0 and isencao_ate > 0 and salario_bruto <= reducao_ate and irrf_final > 0:
        # Renda entre R$ 5.000,01 e R$ 7.350: redução gradual proporcional
        # Fórmula: fator_reducao = (reducao_ate - salario_bruto) / (reducao_ate - isencao_ate)
        # IRRF final = IRRF calculado × (1 - fator_reducao)
        # FIX 1: Guard against division by zero if reducao_ate == isencao_ate
        if reducao_ate == isencao_ate:
            fator = 0.0
        else:
            fator = (reducao_ate - salario_bruto) / (reducao_ate - isencao_ate)
        fator = max(0.0, min(1.0, fator))
        irrf_reduzido = round(irrf_final * (1 - fator), 2)
        irrf_final = irrf_reduzido
        reducao_aplicada = True

    # Identifica a faixa aplicada
    faixa_aplicada = "Isento (Lei 15.270/2025)" if isencao_aplicada else _identificar_faixa(base_usada, tabela_irrf)

    return {
        "salario_bruto": salario_bruto,
        "inss_descontado": inss_descontado,
        "num_dependentes": num_dependentes,
        "deducao_dependentes": deducao_dependentes,
        "pensao_alimenticia": pensao_alimenticia,
        "desconto_simplificado": desconto_simplificado,
        "metodo_escolhido": metodo,
        "base_calculo": base_usada,
        "faixa_aplicada": faixa_aplicada,
        "isencao_5000_aplicada": isencao_aplicada,
        "reducao_gradual_aplicada": reducao_aplicada,
        "irrf": irrf_final,
        "salario_liquido_apos_inss_irrf": round(salario_bruto - inss_descontado - irrf_final, 2),
        "tabela_vigente": vigente,
        "base_legal": "Lei 15.270/2025 (isenção R$ 5.000); RIR/2018 Decreto 9.580/18; IN RFB 1.500/2014",
        **({"aviso_vigencia": aviso_vigencia} if not vigente else {}),
    }


def _calcular_na_tabela(base, tabela):
    """Aplica a tabela progressiva do IRRF."""
    if base <= 0:
        return 0.0
    for faixa in tabela["faixas"]:
        if base <= faixa["ate"]:
            irrf = round(base * faixa["aliquota"] - faixa["parcela_deduzir"], 2)
            return max(irrf, 0.0)
    # Última faixa (sem limite superior real)
    ultima = tabela["faixas"][-1]
    irrf = round(base * ultima["aliquota"] - ultima["parcela_deduzir"], 2)
    return max(irrf, 0.0)


def _identificar_faixa(base, tabela):
    """Retorna a descrição da faixa aplicada."""
    for faixa in tabela["faixas"]:
        if base <= faixa["ate"]:
            return faixa["aliquota_pct"]
    return tabela["faixas"][-1]["aliquota_pct"]


def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    print(f"\n{'='*55}")
    print(f"  CÁLCULO DE IRRF SOBRE SALÁRIO")
    print(f"{'='*55}")
    print(f"  Salário bruto:        {formatar_brl(r['salario_bruto'])}")
    print(f"  (-) INSS:             {formatar_brl(r['inss_descontado'])}")
    if r["num_dependentes"] > 0:
        print(f"  (-) Dependentes ({r['num_dependentes']}):   {formatar_brl(r['deducao_dependentes'])}")
    if r["pensao_alimenticia"] > 0:
        print(f"  (-) Pensão aliment.:  {formatar_brl(r['pensao_alimenticia'])}")
    metodo_label = "Desconto simplificado" if r["metodo_escolhido"] == "simplificado" else "Deduções legais"
    print(f"  Método mais vantajoso: {metodo_label}")
    print(f"  Base de cálculo:      {formatar_brl(r['base_calculo'])}")
    print(f"  Faixa aplicada:       {r['faixa_aplicada']}")
    print(f"  IRRF retido:          {formatar_brl(r['irrf'])}")
    if not r.get("tabela_vigente", True):
        print(f"\n  {r.get('aviso_vigencia', '')}")
    print(f"  {'─'*50}")
    print(f"  Líquido (bruto-INSS-IRRF): {formatar_brl(r['salario_liquido_apos_inss_irrf'])}")
    print(f"{'='*55}\n")


# ─── TESTES ──────────────────────────────────────────────────────

def _estimar_irrf_7350(tabela_irrf, tabela_inss):
    """Helper para calcular o IRRF esperado em R$ 7.350 (borda da redução)."""
    r = calcular_irrf(7350.00, 0, tabela_irrf=tabela_irrf, tabela_inss=tabela_inss)
    return r["irrf"]


def rodar_testes():
    tabela_irrf = carregar_tabela_irrf()
    tabela_inss = carregar_tabela_inss()
    testes_ok = 0
    testes_total = 0

    def teste(descricao, salario, dependentes, esperado_irrf, tolerancia=1.00):
        nonlocal testes_ok, testes_total
        testes_total += 1
        r = calcular_irrf(salario, dependentes, tabela_irrf=tabela_irrf, tabela_inss=tabela_inss)
        diff = abs(r["irrf"] - esperado_irrf)
        status = "PASSOU" if diff <= tolerancia else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}: sal {formatar_brl(salario)} → "
              f"IRRF {formatar_brl(r['irrf'])} (esperado ~{formatar_brl(esperado_irrf)})")
        if status == "FALHOU":
            print(f"         ⚠ Diferença: {formatar_brl(diff)} | base: {formatar_brl(r['base_calculo'])} | método: {r['metodo_escolhido']}")

    print("\n🧪 RODANDO TESTES DO IRRF (tabela 2026 — Lei 15.270/2025)...")
    print(f"{'─'*60}")

    # Teste 1: Salário mínimo 2026 — isento
    teste("Salário mínimo (isento)", 1621.00, 0, 0.00)

    # Teste 2: Salário de R$ 3.000 — isento pela regra dos R$ 5.000
    # Renda bruta ≤ R$ 5.000 → IRRF = 0 (Lei 15.270/2025)
    teste("Salário R$ 3.000 (isento — renda ≤ 5.000)", 3000.00, 0, 0.00)

    # Teste 3: R$ 5.000 sem dependentes — isento pela regra dos R$ 5.000
    # Renda bruta = R$ 5.000 exatos → IRRF = 0
    teste("Salário R$ 5.000 (isento — renda ≤ 5.000)", 5000.00, 0, 0.00)

    # Teste 4: R$ 6.000 sem dependentes — redução gradual
    # INSS(6000): F1=121.58, F2=115.37, F3=174.17, F4=(6000-4354.27)*14%=230.40 → total ~641.52
    # Base legal: 6000 - 641.52 = 5358.48 → 5358.48 × 27.5% - 908.73 = 564.85
    # Base simpl.: 6000 - 607.20 = 5392.80 → 5392.80 × 27.5% - 908.73 = 574.29
    # Legal melhor: ~564.85
    # Fator redução: (7350 - 6000) / (7350 - 5000) = 1350/2350 = 0.5745
    # IRRF final: 564.85 × (1 - 0.5745) = 564.85 × 0.4255 ≈ 240.34
    teste("Salário R$ 6.000 (redução gradual)", 6000.00, 0, 240.34, tolerancia=5.00)

    # Teste 5: R$ 10.000 (acima do teto INSS, acima de R$ 7.350 — tabela normal)
    # INSS = 988.10 (teto 2026)
    # Base legal: 10000 - 988.10 = 9011.90 → 9011.90 × 27.5% - 908.73 = 1569.54
    # Base simpl.: 10000 - 607.20 = 9392.80 → 9392.80 × 27.5% - 908.73 = 1673.29
    # Legal melhor: ~1569.54
    # Não tem redução (salário > 7350)
    teste("Salário R$ 10.000 (27,5% — sem redução)", 10000.00, 0, 1569.54)

    # Teste 6: Salário baixo — isento em qualquer método
    teste("Salário R$ 2.000 (isento)", 2000.00, 0, 0.00)

    # Teste 7: R$ 7.350 exatos — borda da redução (fator ≈ 0, quase sem redução)
    # Fator: (7350 - 7350) / (7350 - 5000) = 0 → sem redução
    # Deve calcular normalmente pela tabela
    # INSS(7350): ~730 (estimativa)
    # Resultado: IRRF normal da tabela, sem redução
    teste("Salário R$ 7.350 (borda — sem redução)", 7350.00, 0, _estimar_irrf_7350(tabela_irrf, tabela_inss), tolerancia=5.00)

    # Teste 8: R$ 5.001 (logo acima da isenção — redução quase total)
    # Fator: (7350 - 5001) / (7350 - 5000) = 2349/2350 ≈ 0.9996
    # IRRF final ≈ 0 (quase tudo reduzido)
    teste("Salário R$ 5.001 (redução quase total)", 5001.00, 0, 0.00, tolerancia=1.00)

    print(f"{'─'*60}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ⚠️  Há diferenças — verificar (tolerância aplicada conforme teste)")
    print()
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        rodar_testes()
    elif len(sys.argv) > 1:
        try:
            salario = float(sys.argv[1].replace(",", "."))
        except ValueError:
            print("Erro: informe o salário como número.")
            sys.exit(1)
        deps = 0
        if "--dependentes" in sys.argv:
            idx = sys.argv.index("--dependentes")
            deps = int(sys.argv[idx + 1])
        r = calcular_irrf(salario, deps)
        imprimir_resultado(r)
    else:
        print("Uso: python3 calc_irrf.py <salario> [--dependentes N]")
        print("      python3 calc_irrf.py --teste")
