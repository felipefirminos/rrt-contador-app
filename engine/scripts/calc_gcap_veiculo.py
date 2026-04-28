#!/usr/bin/env python3
"""
Calculadora de Ganho de Capital em Veículo (GCAP) — pessoa física
Base legal: RIR/2018, IN RFB 599/2005

Cálculo:
  1. Ganho Bruto = Valor Venda - Custo Aquisição
  2. Se ganho ≤ 0 (venda com prejuízo ou ao custo) → sem tributação
  3. Se ganho > 0:
     - Veículo de uso pessoal: isenção (orientação para declaração)
     - Veículo atividade comercial: aplicar alíquotas progressivas (15% a 22.5%)
  4. Alerta se veículo de dependente

Uso:
    python3 calc_gcap_veiculo.py 80000 50000
    python3 calc_gcap_veiculo.py 80000 50000 --tipo comercial
    python3 calc_gcap_veiculo.py 80000 50000 --tipo dependente
    python3 calc_gcap_veiculo.py --teste
"""

import json
import sys
import os
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TABELA_PATH = os.path.join(SCRIPT_DIR, "tabelas", "gcap_rules.json")


def carregar_tabela(caminho=TABELA_PATH):
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def formatar_brl(valor):
    """Formata valor em R$ brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def aplicar_aliquotas_progressivas(ganho_tributavel, tabela):
    """
    Aplica alíquotas progressivas para veículos com atividade comercial.
    
    Retorna: (imposto: float, aliquota_efetiva: float)
    """
    # Obter alíquotas de veículo da tabela
    veiculo_rules = [a for a in tabela["ativos"] if a["tipo"] == "veiculo"][0]
    aliquotas = veiculo_rules["aliquotas"]
    
    imposto_total = 0.0
    ganho_restante = ganho_tributavel
    
    for aliq in aliquotas:
        if ganho_restante <= 0:
            break
        
        ganho_de = aliq["ganho_de"]
        ganho_ate = aliq["ganho_ate"]
        aliquota = aliq["aliquota"]
        
        # Calcular valor nesta faixa
        if ganho_ate is None:
            valor_faixa = ganho_restante
        else:
            valor_faixa = min(ganho_restante, ganho_ate - ganho_de)
        
        imposto_faixa = valor_faixa * aliquota
        imposto_total += imposto_faixa
        ganho_restante -= valor_faixa
    
    imposto_total = round(imposto_total, 2)
    aliquota_efetiva = (imposto_total / ganho_tributavel * 100) if ganho_tributavel > 0 else 0.0
    
    return imposto_total, round(aliquota_efetiva, 2)


def calcular_gcap_veiculo(valor_venda, custo_aquisicao, tipo_veiculo="particular"):
    """
    Calcula ganho de capital em veículo de pessoa física.
    
    Args:
        valor_venda: valor de venda do veículo
        custo_aquisicao: valor de custo (compra)
        tipo_veiculo: "particular" (uso pessoal), "comercial" (revenda/aluguel), 
                      ou "dependente" (alerta especial)
    
    Retorna: dict com cálculo completo
    """
    tabela = carregar_tabela()
    
    # Cálculo do ganho bruto
    ganho_bruto = valor_venda - custo_aquisicao
    
    # Se ganho é negativo ou zero, sem tributação
    if ganho_bruto <= 0:
        return {
            "valor_venda": round(valor_venda, 2),
            "custo_aquisicao": round(custo_aquisicao, 2),
            "ganho_bruto": round(ganho_bruto, 2),
            "tipo_veiculo": tipo_veiculo,
            "ganho_tributavel": 0.0,
            "imposto_devido": 0.0,
            "aliquota_efetiva": 0.0,
            "observacoes": ["Venda com prejuízo ou ao preço de custo: nenhuma tributação devida"],
            "alerta": None,
            "base_legal": "RIR/2018; IN RFB 599/2005",
            "disclaimer": "Verificar classificação do veículo (uso pessoal vs comercial) com parecer jurídico antes de declaração."
        }
    
    # Determinar tributação conforme tipo de veículo
    imposto_devido = 0.0
    aliquota_efetiva = 0.0
    observacoes = []
    alerta = None
    
    if tipo_veiculo.lower() in ["particular", "pessoal"]:
        # Veículo de uso pessoal: isenção (mas reportar na IRPF)
        observacoes.append("Veículo de uso pessoal: isento de tributação de ganho de capital")
        observacoes.append("(Mas deve ser reportado na declaração de IRPF)")
        ganho_tributavel = 0.0
    
    elif tipo_veiculo.lower() == "dependente":
        # Veículo de dependente: alerta especial
        alerta = "Veículo de dependente: verificar se ganho é tributável no dependente ou no contribuinte"
        observacoes.append(alerta)
        observacoes.append("Consulte parecer jurídico antes de declarar")
        ganho_tributavel = 0.0  # Por orientação, sem tributação imediata
    
    elif tipo_veiculo.lower() == "comercial":
        # Veículo para atividade comercial (revenda, aluguel): tributável com alíquotas progressivas
        ganho_tributavel = ganho_bruto
        imposto_devido, aliquota_efetiva = aplicar_aliquotas_progressivas(ganho_tributavel, tabela)
        observacoes.append(f"Veículo para atividade comercial: tributável com alíquotas progressivas")
    
    else:
        # Tipo desconhecido: assumir uso pessoal com alerta
        alerta = f"Tipo de veículo '{tipo_veiculo}' não reconhecido. Assumindo uso pessoal."
        observacoes.append(alerta)
        ganho_tributavel = 0.0
    
    return {
        "valor_venda": round(valor_venda, 2),
        "custo_aquisicao": round(custo_aquisicao, 2),
        "ganho_bruto": round(ganho_bruto, 2),
        "tipo_veiculo": tipo_veiculo,
        "ganho_tributavel": round(ganho_tributavel if 'ganho_tributavel' in locals() else 0.0, 2),
        "imposto_devido": round(imposto_devido, 2),
        "aliquota_efetiva": aliquota_efetiva,
        "observacoes": observacoes,
        "alerta": alerta,
        "base_legal": "RIR/2018; IN RFB 599/2005; Lei 9.249/1995 Art. 15",
        "disclaimer": "Verificar classificação do veículo (uso pessoal vs comercial) com parecer jurídico antes de declaração."
    }


def imprimir_resultado(r):
    """Imprime resultado formatado para terminal."""
    print(f"\n{'='*65}")
    print(f"  CÁLCULO DE GANHO DE CAPITAL EM VEÍCULO")
    print(f"{'='*65}")
    print(f"  Valor de venda:       {formatar_brl(r['valor_venda'])}")
    print(f"  Custo de aquisição:   {formatar_brl(r['custo_aquisicao'])}")
    print(f"  Ganho bruto:          {formatar_brl(r['ganho_bruto'])}")
    print(f"  Tipo de veículo:      {r['tipo_veiculo']}")
    print(f"\n  Ganho tributável:     {formatar_brl(r['ganho_tributavel'])}")
    print(f"  IMPOSTO DEVIDO:       {formatar_brl(r['imposto_devido'])}")
    if r['ganho_tributavel'] > 0:
        print(f"  Alíquota efetiva:     {r['aliquota_efetiva']:.2f}%")
    
    print(f"\n  Observações:")
    for obs in r['observacoes']:
        print(f"    • {obs}")
    
    if r['alerta']:
        print(f"\n  ⚠️  ALERTA: {r['alerta']}")
    
    print(f"\n  Base legal: {r['base_legal']}")
    print(f"  ⚠️  {r['disclaimer']}")
    print(f"{'='*65}\n")


# ─── TESTES INTEGRADOS ────────────────────────────────────────────

def rodar_testes():
    """
    Testes com valores conhecidos para validar o cálculo de GCAP veículo.
    """
    testes_ok = 0
    testes_total = 0
    
    def teste(descricao, r, chave, valor_esperado, tolerancia=0.5):
        nonlocal testes_ok, testes_total
        testes_total += 1
        valor_atual = r[chave]
        diff = abs(valor_atual - valor_esperado)
        status = "PASSOU" if diff <= tolerancia else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}")
        print(f"         {chave}: {formatar_brl(valor_atual)} (esperado {formatar_brl(valor_esperado)})")
        if status == "FALHOU":
            print(f"         ⚠️  Diferença: {formatar_brl(diff)}")
    
    print("\n🧪 RODANDO TESTES DE GANHO DE CAPITAL EM VEÍCULO...")
    print(f"{'─'*65}")
    
    # Teste 1: Venda com lucro — uso pessoal (isenção)
    r = calcular_gcap_veiculo(80000, 50000, tipo_veiculo="particular")
    teste("Veículo particular com lucro (80k - 50k = 30k, isenção)",
          r, "imposto_devido", 0.0)
    
    # Teste 2: Venda com prejuízo — zero imposto
    r = calcular_gcap_veiculo(40000, 50000, tipo_veiculo="particular")
    teste("Veículo particular com prejuízo (40k - 50k = -10k)",
          r, "imposto_devido", 0.0)
    
    # Teste 3: Venda ao preço de custo — zero ganho
    r = calcular_gcap_veiculo(50000, 50000, tipo_veiculo="comercial")
    teste("Veículo comercial vendido ao custo (50k - 50k = 0)",
          r, "imposto_devido", 0.0)
    
    # Teste 4: Veículo comercial com lucro (alíquota 15%)
    r = calcular_gcap_veiculo(80000, 50000, tipo_veiculo="comercial")
    # Ganho 30k × 15% = 4.5k
    teste("Veículo comercial com lucro (80k - 50k = 30k × 15%)",
          r, "imposto_devido", 4500.0)
    
    # Teste 5: Veículo dependente — alerta
    r = calcular_gcap_veiculo(80000, 50000, tipo_veiculo="dependente")
    teste("Veículo de dependente (alerta, sem tributação automática)",
          r, "imposto_devido", 0.0)
    
    # Teste 6: Veículo comercial com ganho grande (progressiva)
    r = calcular_gcap_veiculo(6000000, 500000, tipo_veiculo="comercial")
    # Ganho 5.5M: (5M × 15%) + (0.5M × 17.5%) = 750k + 87.5k = 837.5k
    teste("Veículo comercial ganho > 5M (progressiva: 5M@15% + 0.5M@17.5%)",
          r, "ganho_bruto", 5500000.0)
    
    # Teste 7: Veículo particular com ganho grande (ainda isenção)
    r = calcular_gcap_veiculo(6000000, 500000, tipo_veiculo="particular")
    teste("Veículo particular com ganho grande (ainda isenção)",
          r, "imposto_devido", 0.0)
    
    # Teste 8: Tipo desconhecido — alerta
    r = calcular_gcap_veiculo(80000, 50000, tipo_veiculo="indefinido")
    teste("Tipo de veículo indefinido (alerta, sem tributação)",
          r, "imposto_devido", 0.0)
    
    # Teste 9: Veículo comercial ganho pequeno (15% sobre 20k = 3k)
    r = calcular_gcap_veiculo(70000, 50000, tipo_veiculo="comercial")
    teste("Veículo comercial ganho 20k (20k × 15%)",
          r, "imposto_devido", 3000.0)
    
    # Teste 10: Veículo comercial ganho 10M+ (alíquota progressiva 20%)
    r = calcular_gcap_veiculo(11000000, 500000, tipo_veiculo="comercial")
    # Ganho 10.5M: (5M × 15%) + (5M × 17.5%) + (0.5M × 20%) = 750k + 875k + 100k = 1.725M
    teste("Veículo comercial ganho 10M+ (progressiva: 5M@15% + 5M@17.5% + 0.5M@20%)",
          r, "ganho_bruto", 10500000.0)
    
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
    elif len(sys.argv) >= 3:
        try:
            valor_venda = float(sys.argv[1].replace(",", "."))
            custo_aquisicao = float(sys.argv[2].replace(",", "."))
            
            tipo_veiculo = "particular"
            if "--tipo" in sys.argv:
                idx = sys.argv.index("--tipo")
                tipo_veiculo = sys.argv[idx + 1]
            
            r = calcular_gcap_veiculo(valor_venda, custo_aquisicao, tipo_veiculo=tipo_veiculo)
            imprimir_resultado(r)
        except (ValueError, IndexError) as e:
            print(f"Erro: {e}")
            print("Uso: python3 calc_gcap_veiculo.py <venda> <custo> [--tipo <tipo>]")
            print("     python3 calc_gcap_veiculo.py --teste")
            print("\nTipos disponíveis: particular, comercial, dependente")
            sys.exit(1)
    else:
        print("Uso: python3 calc_gcap_veiculo.py <venda> <custo> [--tipo <tipo>]")
        print("     python3 calc_gcap_veiculo.py --teste")
        print("\nExemplo:")
        print("  python3 calc_gcap_veiculo.py 80000 50000")
        print("  python3 calc_gcap_veiculo.py 80000 50000 --tipo comercial")
        print("\nTipos: particular (padrão, isenção), comercial (tributável), dependente (alerta)")
