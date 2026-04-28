#!/usr/bin/env python3
"""
Calculadora de INSS do EMPREGADO (CLT) — Tabela progressiva
Base legal: Art. 28 da Lei 8.212/91; EC 103/2019 (alíquotas progressivas);
            Portaria Interministerial MPS/MF nº 13/2026 (teto R$ 8.475,55 e faixas).

Cálculo PROGRESSIVO: cada faixa aplica sua própria alíquota (igual ao IRPF).
Não é alíquota única sobre o total.

⚠️ NÃO USE PARA SÓCIO COM PRÓ-LABORE.
   O sócio é "contribuinte individual" e paga ALÍQUOTA FIXA DE 11% sobre
   o pró-labore (limitado ao teto), conforme IN RFB 971/2009, art. 65.
   Para sócio, use calc_prolabore.calcular_prolabore() — que aplica 11%.

   Aplicar a tabela progressiva (7,5% / 9% / 12% / 14%) ao sócio é ERRO
   recorrente identificado em auditoria técnica interna (23/04/2026). No teto:
     - Tabela progressiva (empregado, máximo): R$ 988,10
     - Alíquota fixa 11% (sócio, correta):     R$ 932,31

Uso:
    python3 calc_inss.py 5000.00
    python3 calc_inss.py 5000.00 --detalhado
"""

import json
import sys
import os
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TABELA_PATH = os.path.join(SCRIPT_DIR, "tabelas", "inss_2026.json")


def carregar_tabela(caminho=TABELA_PATH):
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def verificar_vigencia(tabela):
    """
    Verifica se a tabela está dentro do prazo de vigência.
    Retorna (vigente: bool, mensagem: str).
    Se vigencia_ate == 'permanente', sempre vigente.
    """
    vigencia_ate = tabela.get("vigencia_ate")
    if vigencia_ate is None or vigencia_ate == "permanente":
        return True, ""
    try:
        data_fim = date.fromisoformat(vigencia_ate)
        hoje = date.today()
        if hoje > data_fim:
            return False, (
                f"⚠️  ATENÇÃO: Esta tabela tem vigência até {vigencia_ate}. "
                f"Hoje é {hoje.isoformat()}. Os valores podem estar DESATUALIZADOS. "
                f"Atualize os JSONs em scripts/tabelas/ com os novos valores antes de usar."
            )
        return True, ""
    except (ValueError, TypeError):
        return True, ""


def calcular_inss(salario_bruto, tabela=None, detalhado=False,
                  tipo_segurado="empregado"):
    """
    Calcula o INSS de forma progressiva (empregado CLT) OU fixa 11%
    (contribuinte individual / sócio com pró-labore).

    Parâmetros:
        salario_bruto: float — base de cálculo
        tabela: dict ou None — tabela INSS (carrega de tabelas/inss_2026.json)
        detalhado: bool — se True, inclui detalhamento por faixa
        tipo_segurado: str — "empregado" (default, tabela progressiva) OU
                       "contribuinte_individual" (sócio, alíquota fixa 11%)

    GUARD: se tipo_segurado="contribuinte_individual", aplica 11% × min(base, teto)
    e retorna metadados marcando esse caminho — preserva contrato de retorno.

    Retorna dict com:
        - salario_bruto: valor informado
        - base_calculo: valor limitado ao teto
        - inss_total: desconto total do INSS
        - aliquota_efetiva: percentual efetivo sobre o bruto
        - tipo_segurado: ecoado (para auditoria)
        - faixas_detalhadas: lista com o cálculo por faixa (só quando empregado e detalhado)
    """
    if tabela is None:
        tabela = carregar_tabela()

    # ── GUARD: contribuinte individual (sócio) usa 11% fixo ──
    if str(tipo_segurado).lower() in ("contribuinte_individual", "socio", "sócio", "ci"):
        teto = tabela["teto_contribuicao"]
        base = max(0.0, min(salario_bruto, teto))
        inss_ci = round(base * 0.11, 2)
        aliquota_efetiva_ci = round((inss_ci / salario_bruto) * 100, 2) if salario_bruto > 0 else 0.0
        return {
            "salario_bruto": salario_bruto,
            "base_calculo": round(base, 2),
            "teto_aplicado": salario_bruto > teto,
            "inss_total": inss_ci,
            "aliquota_efetiva_pct": aliquota_efetiva_ci,
            "tipo_segurado": "contribuinte_individual",
            "aliquota_aplicada_pct": 11.0,
            "tabela_vigente": True,
            "base_legal": (
                "IN RFB 971/2009, art. 65 (contribuinte individual — alíquota fixa 11%); "
                "Lei 8.212/91, art. 21; Portaria Interministerial MPS/MF 13/2026 (teto)."
            ),
        }

    # Validação: salário deve ser positivo
    alertas = []
    if salario_bruto < 0:
        alertas.append(f"⚠️ Salário bruto negativo ({salario_bruto}) informado — tratado como R$ 0,00.")
        salario_bruto = 0

    # Verificação de vigência
    vigente, aviso_vigencia = verificar_vigencia(tabela)

    teto = tabela["teto_contribuicao"]
    faixas = tabela["faixas"]
    base = min(salario_bruto, teto)

    inss_total = 0.0
    detalhes = []
    restante = base

    for i, faixa in enumerate(faixas):
        if restante <= 0:
            break

        limite_inferior = faixa["de"]
        limite_superior = faixa["ate"]
        aliquota = faixa["aliquota"]

        # Largura desta faixa
        if i == 0:
            largura_faixa = limite_superior
        else:
            largura_faixa = limite_superior - faixas[i - 1]["ate"]

        # Quanto do salário cai nesta faixa
        valor_na_faixa = min(restante, largura_faixa)
        contribuicao_faixa = round(valor_na_faixa * aliquota, 2)

        inss_total += contribuicao_faixa
        restante -= valor_na_faixa

        if detalhado:
            detalhes.append({
                "faixa": faixa["faixa"],
                "de": limite_inferior,
                "ate": limite_superior,
                "aliquota_pct": faixa["aliquota_pct"],
                "valor_na_faixa": round(valor_na_faixa, 2),
                "contribuicao": contribuicao_faixa,
            })

    inss_total = round(inss_total, 2)
    aliquota_efetiva = round((inss_total / salario_bruto) * 100, 2) if salario_bruto > 0 else 0.0

    resultado = {
        "salario_bruto": salario_bruto,
        "base_calculo": round(base, 2),
        "teto_aplicado": salario_bruto > teto,
        "inss_total": inss_total,
        "aliquota_efetiva_pct": aliquota_efetiva,
        "tabela_vigente": vigente,
        "base_legal": "Lei 8.212/91 Art. 28; EC 103/2019 (alíquotas progressivas); Portaria MPS/MF 2025",
    }

    if alertas:
        resultado["alertas"] = alertas

    if not vigente:
        resultado["aviso_vigencia"] = aviso_vigencia

    if detalhado:
        resultado["faixas_detalhadas"] = detalhes

    return resultado


def formatar_brl(valor):
    """Formata valor em R$ brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    """Imprime resultado formatado para o terminal."""
    print(f"\n{'='*55}")
    print(f"  CÁLCULO DE INSS DO EMPREGADO")
    print(f"{'='*55}")
    print(f"  Salário bruto:      {formatar_brl(r['salario_bruto'])}")
    print(f"  Base de cálculo:    {formatar_brl(r['base_calculo'])}")
    if r["teto_aplicado"]:
        print(f"  ⚠ Teto aplicado (salário acima do teto de contribuição)")
    print(f"  INSS descontado:    {formatar_brl(r['inss_total'])}")
    print(f"  Alíquota efetiva:   {r['aliquota_efetiva_pct']}%")

    if not r.get("tabela_vigente", True):
        print(f"\n  {r.get('aviso_vigencia', '')}")

    if "faixas_detalhadas" in r:
        print(f"\n  {'─'*50}")
        print(f"  Detalhamento por faixa:")
        print(f"  {'Faixa':<8} {'Alíquota':<10} {'Base na faixa':<18} {'INSS':<12}")
        print(f"  {'─'*50}")
        for f in r["faixas_detalhadas"]:
            print(f"  {f['faixa']:<8} {f['aliquota_pct']:<10} {formatar_brl(f['valor_na_faixa']):<18} {formatar_brl(f['contribuicao']):<12}")

    print(f"{'='*55}\n")


# ─── TESTES INTEGRADOS ────────────────────────────────────────────

def rodar_testes():
    """
    Testes com valores conhecidos para validar o cálculo progressivo.
    Executa automaticamente e mostra PASSOU/FALHOU.
    """
    tabela = carregar_tabela()
    testes_ok = 0
    testes_total = 0

    def teste(descricao, salario, esperado, tolerancia=0.02):
        nonlocal testes_ok, testes_total
        testes_total += 1
        r = calcular_inss(salario, tabela)
        diff = abs(r["inss_total"] - esperado)
        status = "PASSOU" if diff <= tolerancia else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}: salário {formatar_brl(salario)} → "
              f"INSS {formatar_brl(r['inss_total'])} (esperado {formatar_brl(esperado)})")
        if status == "FALHOU":
            print(f"         ⚠ Diferença: {formatar_brl(diff)}")

    print("\n🧪 RODANDO TESTES DO INSS (tabela 2026)...")
    print(f"{'─'*60}")

    # Teste 1: Salário mínimo 2026 (1ª faixa apenas)
    # 1621.00 × 7.5% = 121.575 → 121.58
    teste("Salário mínimo (1ª faixa)", 1621.00, 121.58)

    # Teste 2: Salário na 2ª faixa
    # Faixa 1: 1621.00 × 7.5% = 121.58
    # Faixa 2: (2500.00 - 1621.00) × 9% = 879.00 × 9% = 79.11
    # Total: 121.58 + 79.11 = 200.69
    teste("Salário R$ 2.500 (2 faixas)", 2500.00, 200.69)

    # Teste 3: Salário de R$ 4.400 (4 faixas)
    # Faixa 1: 1621.00 × 7.5% = 121.58
    # Faixa 2: (2902.84 - 1621.00) × 9% = 1281.84 × 9% = 115.37
    # Faixa 3: (4354.27 - 2902.84) × 12% = 1451.43 × 12% = 174.17
    # Faixa 4: (4400.00 - 4354.27) × 14% = 45.73 × 14% = 6.40
    # Total: 121.58 + 115.37 + 174.17 + 6.40 = 417.52
    teste("Salário R$ 4.400 (4 faixas)", 4400.00, 417.52)

    # Teste 4: Salário de R$ 5.800 (4 faixas)
    # Faixa 1: 1621.00 × 7.5% = 121.58
    # Faixa 2: 1281.84 × 9% = 115.37
    # Faixa 3: 1451.43 × 12% = 174.17
    # Faixa 4: (5800.00 - 4354.27) × 14% = 1445.73 × 14% = 202.40
    # Total: 121.58 + 115.37 + 174.17 + 202.40 = 613.52
    teste("Salário R$ 5.800 (4 faixas)", 5800.00, 613.52)

    # Teste 5: Acima do teto 2026 (usa teto R$ 8.475,55)
    # Faixa 1: 1621.00 × 7.5% = 121.58
    # Faixa 2: 1281.84 × 9% = 115.37
    # Faixa 3: 1451.43 × 12% = 174.17
    # Faixa 4: (8475.55 - 4354.27) × 14% = 4121.28 × 14% = 576.98
    # Total: 121.58 + 115.37 + 174.17 + 576.98 = 988.10
    teste("Salário R$ 15.000 (teto aplicado)", 15000.00, 988.10)

    # Teste 6: Salário zero
    teste("Salário R$ 0", 0.00, 0.00)

    # ─────────────────────────────────────────────────────────────
    #  v6.1 — GUARD contribuinte individual (sócio): alíquota fixa 11%
    # ─────────────────────────────────────────────────────────────
    print(f"\n  ── v6.1: Sócio (contribuinte_individual) — alíquota fixa 11% ──")
    # 11% × R$ 1.621,00 = R$ 178,31
    r_ci_min = calcular_inss(1621.00, tabela, tipo_segurado="contribuinte_individual")
    diff = abs(r_ci_min["inss_total"] - 178.31)
    status = "PASSOU" if diff <= 0.02 else "FALHOU"
    if status == "PASSOU":
        testes_ok += 1
    testes_total += 1
    print(f"  [{status}] Sócio R$ 1.621 → INSS {formatar_brl(r_ci_min['inss_total'])} (esperado R$ 178,31)")

    # 11% × R$ 5.000 = R$ 550,00
    r_ci_5k = calcular_inss(5000.00, tabela, tipo_segurado="contribuinte_individual")
    diff = abs(r_ci_5k["inss_total"] - 550.00)
    status = "PASSOU" if diff <= 0.02 else "FALHOU"
    if status == "PASSOU":
        testes_ok += 1
    testes_total += 1
    print(f"  [{status}] Sócio R$ 5.000 → INSS {formatar_brl(r_ci_5k['inss_total'])} (esperado R$ 550,00)")

    # 11% × teto R$ 8.475,55 = R$ 932,31 (NÃO R$ 988,10)
    r_ci_teto = calcular_inss(15000.00, tabela, tipo_segurado="contribuinte_individual")
    diff = abs(r_ci_teto["inss_total"] - 932.31)
    status = "PASSOU" if diff <= 0.02 else "FALHOU"
    if status == "PASSOU":
        testes_ok += 1
    testes_total += 1
    print(f"  [{status}] Sócio R$ 15K (teto) → INSS {formatar_brl(r_ci_teto['inss_total'])} (esperado R$ 932,31)")
    # Confirma diferença vs empregado no teto
    r_emp_teto = calcular_inss(15000.00, tabela)
    testes_total += 1
    if abs(r_emp_teto["inss_total"] - 988.10) <= 0.02 and abs(r_ci_teto["inss_total"] - 932.31) <= 0.02:
        testes_ok += 1
        print(f"  [PASSOU] Diferença sócio×empregado no teto: R$ {r_emp_teto['inss_total'] - r_ci_teto['inss_total']:.2f} (~R$ 55,79)")
    else:
        print(f"  [FALHOU] Diferença sócio×empregado no teto incorreta")

    # Aliases aceitos
    testes_total += 1
    r_alias = calcular_inss(5000.00, tabela, tipo_segurado="socio")
    if abs(r_alias["inss_total"] - 550.00) <= 0.02:
        testes_ok += 1
        print(f"  [PASSOU] Alias 'socio' → mesmo cálculo (R$ 550,00)")
    else:
        print(f"  [FALHOU] Alias 'socio' não funcionou")

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
    elif len(sys.argv) > 1:
        try:
            salario = float(sys.argv[1].replace(",", "."))
        except ValueError:
            print("Erro: informe o salário como número. Ex: python3 calc_inss.py 5000.00")
            sys.exit(1)

        detalhado = "--detalhado" in sys.argv or "-d" in sys.argv
        r = calcular_inss(salario, detalhado=detalhado)
        imprimir_resultado(r)
    else:
        print("Uso: python3 calc_inss.py <salario_bruto> [--detalhado]")
        print("      python3 calc_inss.py --teste")
