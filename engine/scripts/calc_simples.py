#!/usr/bin/env python3
"""
Calculadora de DAS — Simples Nacional (Anexos I a V + Fator R)
Base legal: LC 123/2006, Art. 18; LC 155/2016; Resolução CGSN 140/2018.

CPP — INCLUSÃO/EXCLUSÃO POR ANEXO (cuidado, fonte recorrente de erro):
  - Anexos I, II, III, V: CPP **INCLUÍDA** no DAS. NÃO recolha 20% patronal
    sobre folha/pró-labore separadamente (LC 123/2006, art. 13, §3°).
  - Anexo IV: CPP **NÃO** incluída no DAS. A empresa recolhe 20% patronal
    + RAT/FAP/Terceiros sobre a folha e pró-labore como nos demais regimes.

Erro recorrente identificado em auditoria técnica interna (23/04/2026): tratar o Anexo V como se a CPP fosse paga separadamente
(somando 20% × pró-labore). ISSO SUPERESTIMA o custo do Anexo V em ~R$ 324/mês
para um pró-labore de R$ 1.621 e distorce comparativos. Anexo V está nos
REGIMES_SEM_CPP em calc_prolabore.py.

ENQUADRAMENTO Anexos III × IV × V — atenção a engenharia/construção:
  - Engenharia consultiva (projetos, laudos, supervisão): Anexo III/V c/ Fator R.
    CNAE típico: 71.12-0-00 (Serviços de engenharia).
  - Engenharia COM execução de obras OU cessão de mão de obra: Anexo IV.
    Mesmas atividades, contexto diferente — confira sempre a natureza da
    operação antes de enquadrar (LC 123/2006, art. 18, §5°-C).
  - Limpeza, vigilância, construção, advocacia: Anexo IV obrigatório.

Uso:
    python3 calc_simples.py --anexo III --rbt12 780000 --receita-mes 85000 --folha12 250000
    python3 calc_simples.py --teste
"""

import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TABELA_PATH = os.path.join(SCRIPT_DIR, "tabelas", "simples_nacional.json")


def carregar_tabela(caminho=TABELA_PATH):
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── v6.1: Helper de enquadramento Anexo IV vs III/V ──────────────
# CNAEs/atividades em que o enquadramento depende da natureza da operação.
# Quando há EXECUÇÃO DE OBRAS ou CESSÃO DE MÃO DE OBRA, vai para Anexo IV
# (CPP separada). Quando é apenas consultoria/projeto/laudo, fica em III/V.
CNAES_ENGENHARIA_AMBIGUOS = {
    "71.12-0-00": "Serviços de engenharia",
    "71.11-1-00": "Serviços de arquitetura",
    "43.29-1-99": "Outras obras de instalações em construções",
    "42.21-9-04": "Construção de estações e redes de telecomunicações",
    "43.99-1-99": "Serviços especializados para construção não especificados",
    # Limpeza/vigilância/construção: sempre Anexo IV (não ambíguos)
}

# CNAEs sempre Anexo IV (sem ambiguidade)
CNAES_SEMPRE_ANEXO_IV = {
    "81.21-4-00": "Limpeza em prédios e em domicílios",
    "80.11-1-01": "Atividades de vigilância e segurança privada",
    "41.20-4-00": "Construção de edifícios",
    "42.11-1-01": "Construção de rodovias e ferrovias",
    "69.11-7-01": "Serviços advocatícios (Anexo IV obrigatório)",
}


def sugerir_anexo_engenharia(cnae=None, executa_obras=False, cessao_mao_obra=False):
    """
    Sugere o Anexo correto para CNAEs ambíguos de engenharia/construção.

    Parâmetros:
        cnae: str ou None — CNAE da atividade (com ou sem máscara)
        executa_obras: bool — se True, há execução de obras/serviços de campo
        cessao_mao_obra: bool — se True, há cessão de mão de obra

    Retorna:
        dict com 'anexo_sugerido', 'motivo', 'precisa_confirmar' (bool),
        'cpp_separada' (bool — se True, CPP é paga à parte além do DAS).
    """
    cnae_norm = (cnae or "").replace(".", "").replace("-", "").replace("/", "").strip()

    # CNAEs sempre Anexo IV
    for k in CNAES_SEMPRE_ANEXO_IV:
        if cnae_norm == k.replace(".", "").replace("-", ""):
            return {
                "anexo_sugerido": "IV",
                "motivo": f"{CNAES_SEMPRE_ANEXO_IV[k]} — Anexo IV obrigatório (LC 123/2006, art. 18, §5°-C).",
                "precisa_confirmar": False,
                "cpp_separada": True,
                "cnae": cnae,
            }

    # CNAEs ambíguos: depende do contexto
    for k in CNAES_ENGENHARIA_AMBIGUOS:
        if cnae_norm == k.replace(".", "").replace("-", ""):
            if executa_obras or cessao_mao_obra:
                motivo_extra = []
                if executa_obras:
                    motivo_extra.append("execução de obras")
                if cessao_mao_obra:
                    motivo_extra.append("cessão de mão de obra")
                return {
                    "anexo_sugerido": "IV",
                    "motivo": (
                        f"{CNAES_ENGENHARIA_AMBIGUOS[k]} com {', '.join(motivo_extra)} → "
                        f"Anexo IV (CPP paga separadamente sobre folha + pró-labore)."
                    ),
                    "precisa_confirmar": False,
                    "cpp_separada": True,
                    "cnae": cnae,
                }
            return {
                "anexo_sugerido": "III/V c/ Fator R",
                "motivo": (
                    f"{CNAES_ENGENHARIA_AMBIGUOS[k]} prestado como consultoria "
                    f"(projetos, laudos, supervisão técnica) → Anexo III via Fator R "
                    f"(folha 12m / RBT12 ≥ 28%) ou Anexo V (Fator R < 28%). "
                    f"⚠️ CONFIRMAR explicitamente que NÃO há execução de obras "
                    f"nem cessão de mão de obra antes de enquadrar."
                ),
                "precisa_confirmar": True,
                "cpp_separada": False,
                "cnae": cnae,
            }

    # CNAE não mapeado
    return {
        "anexo_sugerido": None,
        "motivo": (
            f"CNAE {cnae or '<não informado>'} não está na lista de ambíguos. "
            f"Consulte a Resolução CGSN 140/2018 e o Anexo VI da LC 123/2006."
        ),
        "precisa_confirmar": True,
        "cpp_separada": None,
        "cnae": cnae,
    }



def calcular_das(anexo_original, rbt12, receita_mes, folha12=0, tabela=None):
    """
    Calcula o DAS mensal do Simples Nacional.

    Parâmetros:
        - anexo_original: "I", "II", "III", "IV" ou "V"
        - rbt12: Receita Bruta Total dos últimos 12 meses
        - receita_mes: Receita bruta do mês de apuração
        - folha12: Folha de pagamento (incluindo pró-labore + encargos) dos últimos 12 meses
                   (obrigatório para Anexo V — verifica Fator R)
        - tabela: dados da tabela (carrega automaticamente se None)

    Retorna dict com todos os valores discriminados.
    """
    if tabela is None:
        tabela = carregar_tabela()

    anexo_str = str(anexo_original).upper().replace("ANEXO ", "").strip()

    # Validações
    if rbt12 > tabela["limite_simples"]:
        return {
            "erro": f"RBT12 ({rbt12:,.2f}) excede o limite do Simples Nacional ({tabela['limite_simples']:,.2f}). Empresa excluída.",
            "das": 0,
        }
    # FIX 2: Guard against RBT12 < 1.00 to prevent division instability
    if rbt12 < 1.00:
        return {"erro": "RBT12 deve ser >= R$ 1,00 para cálculo do Simples", "das": 0}
    if rbt12 <= 0:
        return {"erro": "RBT12 deve ser maior que zero.", "das": 0}
    if receita_mes < 0:
        return {"erro": "Receita do mês não pode ser negativa.", "das": 0}
    if receita_mes == 0:
        return {
            "anexo_aplicado": anexo_str,
            "rbt12": rbt12,
            "receita_mes": 0,
            "das": 0,
            "aliquota_efetiva_pct": 0,
            "nota": "Receita zero no mês — sem DAS a pagar.",
        }

    # Fator R: verifica se Anexo V migra para III
    fator_r = None
    fator_r_aplicado = False
    anexo_efetivo = anexo_str

    if anexo_str == "V" and folha12 > 0 and rbt12 > 0:
        fator_r = round(folha12 / rbt12, 4)
        if fator_r >= tabela["fator_r_minimo"]:
            anexo_efetivo = "III"
            fator_r_aplicado = True

    # Localiza o anexo na tabela
    if anexo_efetivo not in tabela["anexos"]:
        return {"erro": f"Anexo '{anexo_efetivo}' não encontrado. Use I, II, III, IV ou V.", "das": 0}

    anexo_data = tabela["anexos"][anexo_efetivo]

    # Identifica a faixa
    faixa_encontrada = None
    for faixa in anexo_data["faixas"]:
        if rbt12 <= faixa["ate"]:
            faixa_encontrada = faixa
            break

    if faixa_encontrada is None:
        return {"erro": f"RBT12 ({rbt12:,.2f}) não se enquadra em nenhuma faixa do Anexo {anexo_efetivo}.", "das": 0}

    # Cálculo da alíquota efetiva
    aliquota_nominal = faixa_encontrada["aliquota"]
    parcela_deduzir = faixa_encontrada["parcela_deduzir"]

    aliquota_efetiva = ((rbt12 * aliquota_nominal) - parcela_deduzir) / rbt12
    aliquota_efetiva = round(aliquota_efetiva, 6)

    # DAS do mês
    das = round(receita_mes * aliquota_efetiva, 2)

    # Verifica sublimite
    sublimite_nota = None
    if rbt12 > tabela["sublimite_icms_iss"]:
        sublimite_nota = (
            f"RBT12 ({rbt12:,.2f}) excede o sublimite de {tabela['sublimite_icms_iss']:,.2f}. "
            f"ICMS e ISS devem ser recolhidos FORA do DAS (apuração normal pelo estado/município)."
        )

    resultado = {
        "anexo_original": anexo_str,
        "anexo_aplicado": anexo_efetivo,
        "descricao_anexo": anexo_data["descricao"],
        "rbt12": rbt12,
        "receita_mes": receita_mes,
        "faixa": faixa_encontrada["faixa"],
        "faixa_limite": faixa_encontrada["ate"],
        "aliquota_nominal_pct": round(aliquota_nominal * 100, 2),
        "parcela_deduzir": parcela_deduzir,
        "aliquota_efetiva_pct": round(aliquota_efetiva * 100, 2),
        "das": das,
        "base_legal": "LC 123/2006, Arts. 18-19; LC 155/2016; Resolução CGSN 140/2018",
    }

    if fator_r is not None:
        resultado["fator_r"] = round(fator_r * 100, 2)
        resultado["fator_r_aplicado"] = fator_r_aplicado
        resultado["folha12"] = folha12
        if fator_r_aplicado:
            resultado["nota_fator_r"] = (
                f"Fator R = {resultado['fator_r']}% (≥ 28%). "
                f"Empresa migra do Anexo V para o Anexo III (alíquotas menores)."
            )
        else:
            resultado["nota_fator_r"] = (
                f"Fator R = {resultado['fator_r']}% (< 28%). "
                f"Empresa permanece no Anexo V."
            )

    if sublimite_nota:
        resultado["sublimite_excedido"] = True
        resultado["nota_sublimite"] = sublimite_nota
    else:
        resultado["sublimite_excedido"] = False

    return resultado


def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    if "erro" in r:
        print(f"\n❌ ERRO: {r['erro']}")
        return

    print(f"\n{'='*60}")
    print(f"  CÁLCULO DO DAS — SIMPLES NACIONAL")
    print(f"{'='*60}")
    print(f"  Anexo original:       {r['anexo_original']}")
    if r["anexo_original"] != r["anexo_aplicado"]:
        print(f"  Anexo aplicado:       {r['anexo_aplicado']} (migrado pelo Fator R)")
    print(f"  Descrição:            {r['descricao_anexo']}")
    print(f"  RBT12:                {formatar_brl(r['rbt12'])}")
    print(f"  Receita do mês:       {formatar_brl(r['receita_mes'])}")
    print(f"  {'─'*55}")
    print(f"  Faixa:                {r['faixa']}ª (até {formatar_brl(r['faixa_limite'])})")
    print(f"  Alíquota nominal:     {r['aliquota_nominal_pct']}%")
    print(f"  Parcela a deduzir:    {formatar_brl(r['parcela_deduzir'])}")
    print(f"  Alíquota efetiva:     {r['aliquota_efetiva_pct']}%")
    print(f"  {'─'*55}")
    print(f"  ▶ DAS DO MÊS:         {formatar_brl(r['das'])}")

    if "fator_r" in r:
        print(f"\n  📊 Fator R: {r['fator_r']}% — {'APLICADO (V→III)' if r['fator_r_aplicado'] else 'NÃO aplicado'}")

    if r.get("sublimite_excedido"):
        print(f"\n  ⚠️  {r['nota_sublimite']}")

    print(f"{'='*60}\n")


# ─── TESTES ──────────────────────────────────────────────────────

def rodar_testes():
    tabela = carregar_tabela()
    testes_ok = 0
    testes_total = 0

    def teste(descricao, anexo, rbt12, receita_mes, folha12, esperado_das, tolerancia=1.00):
        nonlocal testes_ok, testes_total
        testes_total += 1
        r = calcular_das(anexo, rbt12, receita_mes, folha12, tabela)
        if "erro" in r:
            das = 0
        else:
            das = r["das"]
        diff = abs(das - esperado_das)
        status = "PASSOU" if diff <= tolerancia else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}: DAS {formatar_brl(das)} (esperado ~{formatar_brl(esperado_das)})")
        if status == "FALHOU":
            print(f"         ⚠ Diferença: {formatar_brl(diff)}")
            if "erro" not in r:
                print(f"         Faixa: {r['faixa']}ª | Alíq.nom: {r['aliquota_nominal_pct']}% | Ded: {formatar_brl(r['parcela_deduzir'])} | Alíq.ef: {r['aliquota_efetiva_pct']}%")

    print("\n🧪 RODANDO TESTES DO SIMPLES NACIONAL...")
    print(f"{'─'*65}")

    # Teste 1: Anexo I, 1ª faixa (comércio, faturamento baixo)
    # RBT12 = 150.000 → 1ª faixa → 4% nominal, dedução 0
    # Efetiva = 4%
    # DAS = 20.000 × 4% = 800
    teste("Anexo I, 1ª faixa", "I", 150000, 20000, 0, 800.00)

    # Teste 2: Anexo III, 4ª faixa (caso que FALHOU no stress test)
    # RBT12 = 780.000 → 4ª faixa (720K-1.8M): 16%, dedução 35.640
    # Efetiva = ((780000 × 0.16) - 35640) / 780000 = (124800 - 35640) / 780000 = 89160/780000 = 0.114308
    # DAS = 85.000 × 11.4308% = 9.716,18
    teste("Anexo III, 4ª faixa (stress test #3)", "III", 780000, 85000, 0, 9716.18)

    # Teste 3: Anexo V com Fator R ≥ 28% → migra para Anexo III
    # RBT12 = 780.000, folha12 = 250.000
    # Fator R = 250000/780000 = 32.05% (≥ 28%) → usa Anexo III
    # Mesmo cálculo do teste 2: DAS = 9.716,18
    teste("Anexo V→III (Fator R 32%)", "V", 780000, 85000, 250000, 9716.18)

    # Teste 4: Anexo V SEM Fator R suficiente
    # RBT12 = 780.000, folha12 = 100.000
    # Fator R = 100000/780000 = 12.82% (< 28%) → permanece Anexo V
    # Faixa 4ª Anexo V: 20.5%, dedução 17.100
    # Efetiva = ((780000 × 0.205) - 17100) / 780000 = (159900 - 17100) / 780000 = 142800/780000 = 0.183077
    # DAS = 85.000 × 18.3077% = 15.561,54
    teste("Anexo V sem Fator R", "V", 780000, 85000, 100000, 15561.54)

    # Teste 5: Anexo I, 6ª faixa (sublimite excedido)
    # RBT12 = 4.000.000 → 6ª faixa: 19%, dedução 378.000
    # Efetiva = ((4000000 × 0.19) - 378000) / 4000000 = (760000 - 378000) / 4000000 = 382000/4000000 = 0.0955
    # DAS = 400.000 × 9.55% = 38.200
    teste("Anexo I, 6ª faixa (sublimite)", "I", 4000000, 400000, 0, 38200.00)

    # Teste 6: Receita zero
    teste("Receita zero no mês", "I", 500000, 0, 0, 0.00)

    # Teste 7: Anexo II, 3ª faixa (indústria)
    # RBT12 = 500.000 → 3ª faixa: 10%, dedução 13.860
    # Efetiva = ((500000 × 0.10) - 13860) / 500000 = (50000 - 13860) / 500000 = 36140/500000 = 0.07228
    # DAS = 60.000 × 7.228% = 4.336,80
    teste("Anexo II, 3ª faixa (indústria)", "II", 500000, 60000, 0, 4336.80)

    # Teste 8: Anexo IV, 2ª faixa (advocacia)
    # RBT12 = 300.000 → 2ª faixa: 9%, dedução 8.100
    # Efetiva = ((300000 × 0.09) - 8100) / 300000 = (27000 - 8100) / 300000 = 18900/300000 = 0.063
    # DAS = 30.000 × 6.3% = 1.890
    teste("Anexo IV, 2ª faixa (advocacia)", "IV", 300000, 30000, 0, 1890.00)

    # ─────────────────────────────────────────────────────────────
    #  v6.1: helper sugerir_anexo_engenharia()
    # ─────────────────────────────────────────────────────────────
    print(f"\n  ── v6.1: sugerir_anexo_engenharia() ──")
    def teste_anexo(desc, cond):
        nonlocal testes_ok, testes_total
        testes_total += 1
        status = "PASSOU" if cond else "FALHOU"
        if cond:
            testes_ok += 1
        print(f"  [{status}] {desc}")

    # Engenharia 71.12-0-00 consultiva → III/V (Fator R)
    s1 = sugerir_anexo_engenharia(cnae="71.12-0-00")
    teste_anexo("Eng. consultiva (71.12-0-00) → III/V c/ Fator R",
                s1["anexo_sugerido"] == "III/V c/ Fator R" and s1["cpp_separada"] is False)
    teste_anexo("Eng. consultiva: precisa_confirmar=True",
                s1["precisa_confirmar"] is True)

    # Engenharia COM execução de obras → IV
    s2 = sugerir_anexo_engenharia(cnae="71.12-0-00", executa_obras=True)
    teste_anexo("Eng. com execução de obras → IV",
                s2["anexo_sugerido"] == "IV" and s2["cpp_separada"] is True)

    # Engenharia COM cessão de mão de obra → IV
    s3 = sugerir_anexo_engenharia(cnae="71.12-0-00", cessao_mao_obra=True)
    teste_anexo("Eng. com cessão MO → IV",
                s3["anexo_sugerido"] == "IV" and s3["cpp_separada"] is True)

    # Limpeza (CNAE 81.21-4-00) → sempre IV
    s4 = sugerir_anexo_engenharia(cnae="81.21-4-00")
    teste_anexo("Limpeza (81.21-4-00) → IV obrigatório",
                s4["anexo_sugerido"] == "IV" and s4["precisa_confirmar"] is False)

    # Construção (41.20-4-00) → sempre IV
    s5 = sugerir_anexo_engenharia(cnae="41.20-4-00")
    teste_anexo("Construção (41.20-4-00) → IV obrigatório",
                s5["anexo_sugerido"] == "IV")

    # CNAE não mapeado
    s6 = sugerir_anexo_engenharia(cnae="62.01-5-00")  # desenvolvimento sob encomenda
    teste_anexo("CNAE não mapeado → precisa_confirmar=True",
                s6["anexo_sugerido"] is None and s6["precisa_confirmar"] is True)

    print(f"{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ❌ Há falhas — VERIFICAR antes de usar em produção")
    print()
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        rodar_testes()
    elif "--anexo" in sys.argv and "--rbt12" in sys.argv and "--receita-mes" in sys.argv:
        anexo = sys.argv[sys.argv.index("--anexo") + 1]
        rbt12 = float(sys.argv[sys.argv.index("--rbt12") + 1])
        receita = float(sys.argv[sys.argv.index("--receita-mes") + 1])
        folha = 0
        if "--folha12" in sys.argv:
            folha = float(sys.argv[sys.argv.index("--folha12") + 1])
        r = calcular_das(anexo, rbt12, receita, folha)
        imprimir_resultado(r)
    else:
        print("Uso: python3 calc_simples.py --anexo III --rbt12 780000 --receita-mes 85000 [--folha12 250000]")
        print("      python3 calc_simples.py --teste")
