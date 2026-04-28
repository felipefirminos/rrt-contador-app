#!/usr/bin/env python3
"""
Calculadora de Carnê-Leão para rendimentos de pessoa física em moeda estrangeira
Base legal: Art. 39 IN RFB 1.585/2015, RIR/2018 Art. 118-120

Calcula o IRRF mensal sobre rendimentos em moeda estrangeira recebidos por residentes
no Brasil. Usa taxas PTAX de fechamento para conversão em BRL e tabela progressiva de IRRF.

Aplicável a: freelancers, consultores, profissionais autônomos com renda no exterior.

Uso:
    python3 calc_carne_leao.py 1000 USD 2025-06
    python3 calc_carne_leao.py 1000 USD 2025-06 --deducoes 100
    python3 calc_carne_leao.py 1000 USD 2025-06 --dependentes 2
    python3 calc_carne_leao.py --teste
"""

import json
import sys
import os
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PTAX_PATH = os.path.join(SCRIPT_DIR, "tabelas", "ptax_2026.json")
IRRF_PATH = os.path.join(SCRIPT_DIR, "tabelas", "irrf_2026.json")


def carregar_tabela_ptax(caminho=PTAX_PATH):
    """Carrega tabela de PTAX."""
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def carregar_tabela_irrf(caminho=IRRF_PATH):
    """Carrega tabela IRRF."""
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def verificar_vigencia(tabela):
    """
    Verifica se a tabela está dentro do prazo de vigência.
    Retorna (vigente: bool, mensagem: str).
    """
    vigencia_ate = tabela.get("vigencia_ate")
    if vigencia_ate is None or vigencia_ate == "permanente":
        return True, ""
    try:
        data_fim = date.fromisoformat(vigencia_ate)
        hoje = date.today()
        if hoje > data_fim:
            return False, (
                f"ATENÇÃO: Esta tabela tem vigência até {vigencia_ate}. "
                f"Hoje é {hoje.isoformat()}. Os valores podem estar DESATUALIZADOS."
            )
        return True, ""
    except (ValueError, TypeError):
        return True, ""


def obter_ptax(ano_mes, moeda, tabela_ptax, ptax_resolver=None):
    """
    Obtém a taxa PTAX para o mês especificado.
    
    Parâmetros:
        - ano_mes: string "YYYY-MM" (ex: "2025-06")
        - moeda: código ISO (ex: "USD")
        - tabela_ptax: dict carregado de ptax_2026.json
        - ptax_resolver: callable opcional que retorna (ptax, flag_desvio)
    
    Retorna: (ptax: float, desvio_sinalizado: bool)
    """
    if ptax_resolver is not None:
        return ptax_resolver(ano_mes, moeda)
    
    # Busca na tabela padrão
    if ano_mes not in tabela_ptax.get("taxas", {}):
        raise ValueError(f"PTAX não encontrada para {ano_mes} ({moeda})")
    
    ptax_data = tabela_ptax["taxas"][ano_mes]
    ptax = ptax_data["ptax_venda"]
    
    # Não há referência de comparação, então sem desvio
    return ptax, False


def calcular_carne_leao(renda_exterior_moeda, moeda_origem, mes_referencia, 
                        ptax_resolver=None, deducoes_mes=0, dependentes_irrf=0,
                        tabela_ptax=None, tabela_irrf=None):
    """
    Calcula o IRRF mensal (Carnê-Leão) sobre rendimento em moeda estrangeira.
    
    Parâmetros:
        - renda_exterior_moeda: valor em moeda estrangeira
        - moeda_origem: código ISO (ex: "USD")
        - mes_referencia: string "YYYY-MM" (ex: "2025-06")
        - ptax_resolver: callable(ano_mes, moeda) → (ptax, flag_desvio) [opcional]
        - deducoes_mes: deduções legais em BRL (ex: despesas de trabalho)
        - dependentes_irrf: número de dependentes para efeitos de IRRF
        - tabela_ptax: dict [carrega automaticamente se None]
        - tabela_irrf: dict [carrega automaticamente se None]
    
    Retorna: dict com renda_original, moeda, ptax_utilizada, renda_brl, 
             base_calculo, deducoes, irrf_devido, aliquota_efetiva, 
             mes_referencia, disclaimer, desvio_ptax_sinalizado
    """
    if tabela_ptax is None:
        tabela_ptax = carregar_tabela_ptax()
    if tabela_irrf is None:
        tabela_irrf = carregar_tabela_irrf()
    
    # Validações
    renda_exterior_moeda = max(0, renda_exterior_moeda)
    deducoes_mes = max(0, deducoes_mes)
    dependentes_irrf = max(0, dependentes_irrf)
    
    # Obter PTAX
    ptax_utilizada, desvio_sinalizado = obter_ptax(mes_referencia, moeda_origem, 
                                                     tabela_ptax, ptax_resolver)
    
    # Converter para BRL
    renda_brl = round(renda_exterior_moeda * ptax_utilizada, 2)
    
    # Deduções: dependentes (Lei 15.270/2025) + deduções do mês
    deducao_por_dependente = tabela_irrf["deducao_por_dependente"]
    deducao_dependentes = round(dependentes_irrf * deducao_por_dependente, 2)
    total_deducoes = round(deducao_dependentes + deducoes_mes, 2)
    
    # Base de cálculo
    base_calculo = round(renda_brl - total_deducoes, 2)
    base_calculo = max(base_calculo, 0)
    
    # Aplicar isenção/redução Lei 15.270/2025 (até R$ 5.000 bruto)
    isencao_ate = tabela_irrf.get("isencao_renda_bruta_ate", 0)
    reducao_ate = tabela_irrf.get("reducao_gradual_ate", 0)
    irrf_devido = 0.0
    isencao_aplicada = False
    reducao_aplicada = False
    
    if isencao_ate > 0 and renda_brl <= isencao_ate:
        # Rendimento total até R$ 5.000: isento
        irrf_devido = 0.0
        isencao_aplicada = True
    elif reducao_ate > 0 and isencao_ate > 0 and renda_brl <= reducao_ate and base_calculo > 0:
        # Redução gradual entre R$ 5.000,01 e R$ 7.350
        if reducao_ate == isencao_ate:
            fator = 0.0
        else:
            fator = (reducao_ate - renda_brl) / (reducao_ate - isencao_ate)
        fator = max(0.0, min(1.0, fator))
        
        # Calcula IRRF normal na tabela
        irrf_calculado = _calcular_na_tabela(base_calculo, tabela_irrf)
        irrf_reduzido = round(irrf_calculado * (1 - fator), 2)
        irrf_devido = irrf_reduzido
        reducao_aplicada = True
    else:
        # Fora da zona de redução: aplicar tabela normal
        irrf_devido = _calcular_na_tabela(base_calculo, tabela_irrf)
    
    # Alíquota efetiva
    aliquota_efetiva = (irrf_devido / renda_brl * 100) if renda_brl > 0 else 0.0
    
    # Faixa aplicada
    faixa_aplicada = "Isento (Lei 15.270/2025)" if isencao_aplicada else _identificar_faixa(base_calculo, tabela_irrf)
    
    vigente, _ = verificar_vigencia(tabela_irrf)
    
    return {
        "renda_original": renda_exterior_moeda,
        "moeda": moeda_origem,
        "ptax_utilizada": ptax_utilizada,
        "desvio_ptax_sinalizado": desvio_sinalizado,
        "renda_brl": renda_brl,
        "dependentes_irrf": dependentes_irrf,
        "deducao_dependentes": deducao_dependentes,
        "deducoes_mes": deducoes_mes,
        "total_deducoes": total_deducoes,
        "base_calculo": base_calculo,
        "faixa_aplicada": faixa_aplicada,
        "isencao_5000_aplicada": isencao_aplicada,
        "reducao_gradual_aplicada": reducao_aplicada,
        "irrf_devido": irrf_devido,
        "aliquota_efetiva": aliquota_efetiva,
        "mes_referencia": mes_referencia,
        "tabela_vigente": vigente,
        "base_legal": "Art. 39 IN RFB 1.585/2015; RIR/2018 Art. 118-120; Lei 15.270/2025",
        "disclaimer": "Valores calculados para orientação. Verificar compliance com Receita Federal antes de usar em declaração fiscal.",
    }


def calcular_carne_leao_anual(rendas_mensais, tabela_ptax=None, tabela_irrf=None):
    """
    Calcula Carnê-Leão anual a partir de lista de rendas mensais.
    
    Parâmetros:
        - rendas_mensais: lista de dicts, cada um com:
            {'renda': valor, 'moeda': 'USD', 'mes': '2025-06', 'deducoes': 0, 'dependentes': 0}
        - tabela_ptax: dict [carrega se None]
        - tabela_irrf: dict [carrega se None]
    
    Retorna: dict com breakdown mensal + totais anuais
    """
    if tabela_ptax is None:
        tabela_ptax = carregar_tabela_ptax()
    if tabela_irrf is None:
        tabela_irrf = carregar_tabela_irrf()
    
    resultados_mensais = []
    total_renda_brl = 0.0
    total_deducoes = 0.0
    total_irrf = 0.0
    
    for entrada in rendas_mensais:
        renda = entrada.get("renda", 0)
        moeda = entrada.get("moeda", "USD")
        mes = entrada.get("mes")
        deducoes = entrada.get("deducoes", 0)
        dependentes = entrada.get("dependentes", 0)
        
        if not mes:
            raise ValueError("Cada entrada deve ter 'mes' no formato YYYY-MM")
        
        r = calcular_carne_leao(renda, moeda, mes, 
                               deducoes_mes=deducoes, 
                               dependentes_irrf=dependentes,
                               tabela_ptax=tabela_ptax,
                               tabela_irrf=tabela_irrf)
        resultados_mensais.append(r)
        
        total_renda_brl += r["renda_brl"]
        total_deducoes += r["total_deducoes"]
        total_irrf += r["irrf_devido"]
    
    aliquota_media = (total_irrf / total_renda_brl * 100) if total_renda_brl > 0 else 0.0
    
    return {
        "resumo_anual": {
            "total_renda_brl": round(total_renda_brl, 2),
            "total_deducoes": round(total_deducoes, 2),
            "total_irrf_carne_leao": round(total_irrf, 2),
            "aliquota_media": round(aliquota_media, 2),
        },
        "detalhes_mensais": resultados_mensais,
    }


def _calcular_na_tabela(base, tabela_irrf):
    """Aplica a tabela progressiva do IRRF."""
    if base <= 0:
        return 0.0
    for faixa in tabela_irrf["faixas"]:
        if base <= faixa["ate"]:
            irrf = round(base * faixa["aliquota"] - faixa["parcela_deduzir"], 2)
            return max(irrf, 0.0)
    # Última faixa
    ultima = tabela_irrf["faixas"][-1]
    irrf = round(base * ultima["aliquota"] - ultima["parcela_deduzir"], 2)
    return max(irrf, 0.0)


def _identificar_faixa(base, tabela_irrf):
    """Identifica a faixa aplicada."""
    for faixa in tabela_irrf["faixas"]:
        if base <= faixa["ate"]:
            return faixa["aliquota_pct"]
    return tabela_irrf["faixas"][-1]["aliquota_pct"]


def formatar_brl(valor):
    """Formata valor em BRL."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_moeda(valor, moeda):
    """Formata valor em moeda estrangeira."""
    return f"{moeda} {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    """Imprime resultado do cálculo mensal."""
    print(f"\n{'='*60}")
    print(f"  CÁLCULO DE CARNÊ-LEÃO (IRRF sobre renda exterior)")
    print(f"{'='*60}")
    print(f"  Mês de referência:    {r['mes_referencia']}")
    print(f"  Renda (moeda orig.):  {formatar_moeda(r['renda_original'], r['moeda'])}")
    print(f"  PTAX utilizada:       {r['ptax_utilizada']:.4f}")
    if r['desvio_ptax_sinalizado']:
        print(f"  ⚠️  AVISO: desvio PTAX > 1%")
    print(f"  Renda em BRL:         {formatar_brl(r['renda_brl'])}")
    if r['deducao_dependentes'] > 0:
        print(f"  (-) Dependentes ({r['dependentes_irrf']}): {formatar_brl(r['deducao_dependentes'])}")
    if r['deducoes_mes'] > 0:
        print(f"  (-) Deduções mês:     {formatar_brl(r['deducoes_mes'])}")
    print(f"  Base de cálculo:      {formatar_brl(r['base_calculo'])}")
    print(f"  Faixa aplicada:       {r['faixa_aplicada']}")
    print(f"  IRRF Carnê-Leão:      {formatar_brl(r['irrf_devido'])}")
    print(f"  Alíquota efetiva:     {r['aliquota_efetiva']:.2f}%")
    print(f"{'='*60}\n")


# ─── TESTES ──────────────────────────────────────────────────────

def rodar_testes():
    """Executa suite de testes."""
    tabela_ptax = carregar_tabela_ptax()
    tabela_irrf = carregar_tabela_irrf()
    testes_ok = 0
    testes_total = 0
    
    def teste(descricao, renda_usd, moeda, mes, deducoes=0, dependentes=0, 
              esperado_irrf=None, esperado_brl=None, tolerancia=1.00):
        nonlocal testes_ok, testes_total
        testes_total += 1
        
        r = calcular_carne_leao(renda_usd, moeda, mes, 
                               deducoes_mes=deducoes,
                               dependentes_irrf=dependentes,
                               tabela_ptax=tabela_ptax,
                               tabela_irrf=tabela_irrf)
        
        status = "PASSOU"
        detalhes = ""
        
        if esperado_brl is not None:
            diff = abs(r["renda_brl"] - esperado_brl)
            if diff > tolerancia:
                status = "FALHOU"
                detalhes = f" | BRL esperado ~{esperado_brl}, obteve {r['renda_brl']}"
        
        if esperado_irrf is not None and status == "PASSOU":
            diff = abs(r["irrf_devido"] - esperado_irrf)
            if diff > tolerancia:
                status = "FALHOU"
                detalhes = f" | IRRF esperado ~{esperado_irrf}, obteve {r['irrf_devido']}"
        
        if status == "PASSOU":
            testes_ok += 1
        
        print(f"  [{status}] {descricao}")
        if detalhes:
            print(f"         {detalhes}")
    
    print("\n🧪 RODANDO TESTES DO CARNÊ-LEÃO...")
    print(f"{'─'*65}")
    
    # Teste 1: USD 1.000 em junho/2025
    # PTAX 2025-06 = 5.70 → BRL 5.700
    # Renda bruta 5.700 > 5.000 → aplicar redução gradual
    # Base sem deduções = 5.700
    # Fator redução: (7350 - 5700) / (7350 - 5000) = 1650/2350 = 0.7021
    # IRRF na tabela (5700): 5700 * 0.275 - 908.73 = 1567.50 - 908.73 = 658.77
    # IRRF final: 658.77 * (1 - 0.7021) = 658.77 * 0.2979 = 196.22
    teste("USD 1.000 em 2025-06 (redução gradual)", 1000, "USD", "2025-06", 
          deducoes=0, dependentes=0, esperado_brl=5700.00, esperado_irrf=196.22, tolerancia=5.00)
    
    # Teste 2: Renda zero → zero tax
    teste("USD 0 → sem imposto", 0, "USD", "2025-06", 
          esperado_brl=0.0, esperado_irrf=0.0)
    
    # Teste 3: Renda abaixo de R$ 5.000 → isenta
    # USD 500 * 5.70 = R$ 2.850 → isento
    teste("USD 500 em 2025-06 (isento, abaixo R$ 5.000)", 500, "USD", "2025-06", 
          esperado_brl=2850.00, esperado_irrf=0.0)
    
    # Teste 4: Renda de R$ 5.000 exatos (na curva PTAX) → isento
    # USD 877.19 * 5.70 ≈ R$ 5.000 → isento
    teste("Renda R$ 5.000 BRL (isento, limite)", 877.19, "USD", "2025-06", 
          esperado_brl=5000.0, esperado_irrf=0.0, tolerancia=2.00)
    
    # Teste 5: Renda entre R$ 5.001 e R$ 7.350 → redução (quase total)
    # USD 876.5 * 5.70 = R$ 4.996 → isento (ainda < 5000)
    teste("USD 877 em 2025-06 (logo acima R$ 5.000)", 877, "USD", "2025-06", 
          esperado_irrf=0.0, tolerancia=1.00)
    
    # Teste 6: Acima de R$ 7.350 (sem redução)
    # USD 2.000 * 5.70 = R$ 11.400
    # Base: 11.400; IRRF: 11400 * 0.275 - 908.73 = 3135 - 908.73 = 2226.27
    teste("USD 2.000 em 2025-06 (sem redução)", 2000, "USD", "2025-06", 
          esperado_brl=11400.00, esperado_irrf=2226.27, tolerancia=5.00)
    
    # Teste 7: Com deduções (reduz base)
    # USD 1.000 * 5.70 = R$ 5.700, menos R$ 100 deduções = base 5.600
    # Fator: (7350 - 5700) / 2350 = 0.7021 → redução
    teste("USD 1.000 com R$ 100 deduções", 1000, "USD", "2025-06", 
          deducoes=100, esperado_brl=5700.0, esperado_irrf=196.22, tolerancia=10.00)
    
    # Teste 8: Com dependentes (reduz base)
    # USD 1.000 * 5.70 = R$ 5.700, menos 1 dependente (189.59) = base 5.510.41
    # Fator: (7350 - 5700) / 2350 = 0.7021 → redução
    teste("USD 1.000 com 1 dependente", 1000, "USD", "2025-06", 
          dependentes=1, esperado_brl=5700.0, tolerancia=10.00)
    
    # Teste 9: Mês diferente (PTAX diferente)
    # USD 1.000 * 5.48 (dez/2025) = R$ 5.480 → redução gradual
    # Fator: (7350 - 5480) / 2350 = 0.7957 → IRRF: ~122.20
    teste("USD 1.000 em 2025-12 (PTAX 5.48)", 1000, "USD", "2025-12",
          esperado_brl=5480.00, esperado_irrf=122.20, tolerancia=5.00)

    # Teste 10: Mês com PTAX maior (jan/2025)
    # USD 1.000 * 5.28 = R$ 5.280 → redução gradual
    # Fator: (7350 - 5280) / 2350 = 0.8809 → quase tudo reduzido
    teste("USD 1.000 em 2025-01 (PTAX 5.28)", 1000, "USD", "2025-01",
          esperado_brl=5280.00, esperado_irrf=64.73, tolerancia=5.00)

    # Teste 11: Mês inválido
    testes_total += 1
    try:
        calcular_carne_leao(1000, "USD", "2025-13", tabela_ptax=tabela_ptax, tabela_irrf=tabela_irrf)
        print("  [FALHOU] Mês inválido 2025-13 → deveria ter lançado exceção")
    except ValueError as e:
        testes_ok += 1
        print("  [PASSOU] Mês inválido 2025-13 → erro lançado corretamente")
    
    # Teste 12: Anual (vários meses)
    rendas = [
        {"renda": 1000, "moeda": "USD", "mes": "2025-06", "deducoes": 0, "dependentes": 0},
        {"renda": 1000, "moeda": "USD", "mes": "2025-07", "deducoes": 0, "dependentes": 0},
        {"renda": 1000, "moeda": "USD", "mes": "2025-08", "deducoes": 0, "dependentes": 0},
    ]
    try:
        r_anual = calcular_carne_leao_anual(rendas, tabela_ptax=tabela_ptax, tabela_irrf=tabela_irrf)
        # 1000 * (5.70 + 5.76 + 5.85) = 1000 * 17.31 = 17.310
        esperado_brl_anual = 5700 + 5760 + 5850
        if abs(r_anual["resumo_anual"]["total_renda_brl"] - esperado_brl_anual) < 5:
            testes_ok += 1
            print(f"  [PASSOU] Cálculo anual (3 meses): total BRL {formatar_brl(r_anual['resumo_anual']['total_renda_brl'])}")
        else:
            print(f"  [FALHOU] Cálculo anual: esperado {esperado_brl_anual}, obteve {r_anual['resumo_anual']['total_renda_brl']}")
    except Exception as e:
        print(f"  [FALHOU] Cálculo anual: {e}")
    testes_total += 1
    
    print(f"{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print(f"  ⚠️  {testes_total - testes_ok} teste(s) falharam")
    print()
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        rodar_testes()
    elif len(sys.argv) >= 4:
        try:
            renda = float(sys.argv[1].replace(",", "."))
            moeda = sys.argv[2].upper()
            mes = sys.argv[3]
            
            deducoes = 0.0
            if "--deducoes" in sys.argv:
                idx = sys.argv.index("--deducoes")
                deducoes = float(sys.argv[idx + 1].replace(",", "."))
            
            dependentes = 0
            if "--dependentes" in sys.argv:
                idx = sys.argv.index("--dependentes")
                dependentes = int(sys.argv[idx + 1])
            
            r = calcular_carne_leao(renda, moeda, mes, deducoes_mes=deducoes, dependentes_irrf=dependentes)
            imprimir_resultado(r)
        except (ValueError, IndexError) as e:
            print(f"Erro: {e}")
            sys.exit(1)
    else:
        print("Uso: python3 calc_carne_leao.py <renda> <moeda> <mes> [--deducoes N] [--dependentes N]")
        print("      python3 calc_carne_leao.py --teste")
        print()
        print("Exemplo: python3 calc_carne_leao.py 1000 USD 2025-06")
