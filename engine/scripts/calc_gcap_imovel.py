#!/usr/bin/env python3
"""
Calculadora de Ganho de Capital em Imóvel (GCAP) — pessoa física
Base legal: Lei 11.196/2005 Art. 40 (fator redutor), Lei 7.713/88, IN RFB 599/2005

Cálculo:
  1. Ganho Bruto = Valor Venda - Custo Aquisição - Benfeitorias - Corretagem
  2. Aplicar Fator Redutor por Tempo de Posse (FRT) conforme data aquisição
  3. Ganho Tributável = Ganho Bruto × FRT
  4. Verificar isenções (único imóvel ≤ R$ 440k, ou uso para reinvestimento 180 dias)
  5. Aplicar alíquotas progressivas se ganho tributável > 0

Uso:
    python3 calc_gcap_imovel.py 500000 300000 2015-06-10
    python3 calc_gcap_imovel.py 500000 300000 2015-06-10 --benfeitorias 50000 --corretagem 10000
    python3 calc_gcap_imovel.py --teste
"""

import json
import sys
import os
from datetime import datetime, date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TABELA_PATH = os.path.join(SCRIPT_DIR, "tabelas", "gcap_rules.json")


def carregar_tabela(caminho=TABELA_PATH):
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def formatar_brl(valor):
    """Formata valor em R$ brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def obter_fator_redutor(data_aquisicao_str, data_venda_str=None):
    """
    Calcula o Fator de Redução por Tempo (FRT) conforme Lei 11.196/2005 Art. 40.
    
    Regras (IN SRF 84/2001 Art. 7; Lei 7.713/1988 Art. 18):
    - Antes de 1969: FRT = 0.0 (isenção integral — redução de 100%)
    - 1969-1988: Redução fixa de 5% por ano contado do ano de aquisição até 1988.
      Fórmula: reducao = (1988 - ano_aquisicao + 1) × 5%, limitada a 100%.
      FRT = 1.0 - reducao (quanto MENOR o FRT, MAIOR a redução).
    - Após 1988: FRT = 1.0 (sem redução por tempo — ganho integral tributável)

    NOTA: A redução depende APENAS do ano de aquisição, NÃO de anos de posse.

    Retorna: (frt: float, descricao: str)
    """
    try:
        data_aquisicao = datetime.fromisoformat(data_aquisicao_str).date()
    except (ValueError, TypeError):
        return 1.0, "Erro ao parsear data de aquisição"

    # data_venda não afeta o cálculo do FRT (depende apenas do ano de aquisição)
    # Mantida como parâmetro para compatibilidade da API

    # Antes de 1969: isenção completa
    if data_aquisicao.year < 1969:
        return 0.0, "Adquirido antes de 1969: isenção integral (IN SRF 84/2001)"

    # 1969-1988: redução fixa por ano de aquisição (IN SRF 84/2001 Art. 7)
    # Redução = (1988 - ano + 1) × 5%, cap 100%
    if 1969 <= data_aquisicao.year <= 1988:
        anos_ate_1988 = 1988 - data_aquisicao.year + 1
        reducao_pct = min(anos_ate_1988 * 0.05, 1.0)
        frt = 1.0 - reducao_pct

        return frt, (
            f"Adquirido {data_aquisicao.year}: redução {reducao_pct:.0%} "
            f"({anos_ate_1988} anos até 1988) → FRT = {frt:.2%} "
            f"(IN SRF 84/2001 Art. 7)"
        )

    # Após 1988: sem redução por tempo (FRT = 1.0, ganho integral tributável)
    if data_aquisicao.year >= 1989:
        return 1.0, "Adquirido após 1988: sem redução temporal"

    return 1.0, "Data indefinida"


def aplicar_aliquotas_progressivas(ganho_tributavel, tabela):
    """
    Aplica alíquotas progressivas em fatias de ganho.
    Exemplo: ganho de 7M = (5M × 15%) + (2M × 17,5%)
    
    Retorna: (imposto: float, aliquota_efetiva: float)
    """
    aliquotas = [a for a in tabela["ativos"][0]["aliquotas"]]
    
    imposto_total = 0.0
    ganho_restante = ganho_tributavel
    
    for aliq in aliquotas:
        if ganho_restante <= 0:
            break
        
        ganho_de = aliq["ganho_de"]
        ganho_ate = aliq["ganho_ate"]
        aliquota = aliq["aliquota"]
        
        # Calcular o valor nesta faixa
        if ganho_ate is None:
            # Última faixa: sem limite superior
            valor_faixa = ganho_restante
        else:
            valor_faixa = min(ganho_restante, ganho_ate - ganho_de)
        
        imposto_faixa = valor_faixa * aliquota
        imposto_total += imposto_faixa
        ganho_restante -= valor_faixa
    
    imposto_total = round(imposto_total, 2)
    aliquota_efetiva = (imposto_total / ganho_tributavel * 100) if ganho_tributavel > 0 else 0.0
    
    return imposto_total, round(aliquota_efetiva, 2)


def calcular_gcap_imovel(valor_venda, custo_aquisicao, data_aquisicao, 
                         benfeitorias=0, corretagem=0, 
                         unico_imovel=False, valor_ate_440k=False,
                         data_venda=None):
    """
    Calcula ganho de capital em imóvel de pessoa física.
    
    Args:
        valor_venda: valor de venda do imóvel
        custo_aquisicao: valor de custo (compra)
        data_aquisicao: data da aquisição (YYYY-MM-DD)
        benfeitorias: valor de benfeitorias realizadas
        corretagem: custos de corretagem/intermediação
        unico_imovel: se True, aplica isenção de único imóvel residencial
        valor_ate_440k: se True e valor_venda <= 440k, aplica isenção
        data_venda: data da venda (YYYY-MM-DD), default = hoje
    
    Retorna: dict com cálculo completo
    """
    tabela = carregar_tabela()
    
    # Cálculo do ganho bruto
    custo_total = custo_aquisicao + benfeitorias + corretagem
    ganho_bruto = valor_venda - custo_total
    
    # Se ganho é negativo (prejuízo), não há tributação
    if ganho_bruto <= 0:
        return {
            "valor_venda": valor_venda,
            "custo_aquisicao": custo_aquisicao,
            "benfeitorias": benfeitorias,
            "corretagem": corretagem,
            "custo_total": round(custo_total, 2),
            "ganho_bruto": round(ganho_bruto, 2),
            "fator_redutor": 1.0,
            "fator_redutor_descricao": "N/A",
            "ganho_tributavel": 0.0,
            "imposto_devido": 0.0,
            "aliquota_efetiva": 0.0,
            "isencoes_aplicadas": ["Prejuízo: nenhuma tributação devida"],
            "base_legal": "Lei 11.196/2005; Lei 7.713/88; IN RFB 599/2005",
            "disclaimer": "Prejuízo em alienação de imóvel por PF NÃO pode ser compensado com ganhos futuros (vedação Art. 11 IN RFB 599/2005). Diferente de PJ."
        }
    
    # Obter fator redutor
    frt, desc_frt = obter_fator_redutor(data_aquisicao, data_venda)
    
    # Ganho tributável antes de isenções
    ganho_tributavel = ganho_bruto * frt

    # Verificar isenções
    isencoes = []
    imposto_devido = 0.0
    aliquota_efetiva = 0.0

    # Isenção por tempo (pré-1969): FRT reduzido significa isenção
    try:
        data_acq = datetime.fromisoformat(data_aquisicao).date()
        if data_acq.year < 1969:
            isencoes.append("Adquirido antes de 1969: isenção integral (Lei 11.196/2005)")
            ganho_tributavel = 0.0
    except (ValueError, TypeError):
        pass

    # Isenção 1: único imóvel residencial com venda <= R$ 440k
    if not isencoes and unico_imovel and valor_venda <= 440000:
        isencoes.append(f"Único imóvel residencial com venda ≤ R$ 440.000 (Lei 11.196/2005 Art. 40 § 2º)")
        ganho_tributavel = 0.0
    # Isenção 2: reinvestimento em residência dentro de 180 dias
    elif not isencoes and unico_imovel and valor_ate_440k:
        isencoes.append("Reinvestimento em nova residência (180 dias) — orientação para comprovação")
        ganho_tributavel = 0.0

    # Se não há isenção, calcular imposto com alíquotas progressivas
    if ganho_tributavel > 0:
        imposto_devido, aliquota_efetiva = aplicar_aliquotas_progressivas(ganho_tributavel, tabela)
    elif not isencoes:
        isencoes.append("Ganho tributável zerado por isenções aplicáveis")
    
    return {
        "valor_venda": round(valor_venda, 2),
        "custo_aquisicao": round(custo_aquisicao, 2),
        "benfeitorias": round(benfeitorias, 2),
        "corretagem": round(corretagem, 2),
        "custo_total": round(custo_total, 2),
        "ganho_bruto": round(ganho_bruto, 2),
        "fator_redutor": round(frt, 4),
        "fator_redutor_descricao": desc_frt,
        "ganho_tributavel": round(ganho_tributavel, 2),
        "imposto_devido": round(imposto_devido, 2),
        "aliquota_efetiva": aliquota_efetiva,
        "isencoes_aplicadas": isencoes if isencoes else ["Nenhuma"],
        "base_legal": "Lei 11.196/2005 Art. 40; Lei 7.713/88; IN RFB 599/2005",
        "disclaimer": "Consulte parecer jurídico antes de aproveitar isenções. Validade sujeita a alterações legislativas."
    }


def imprimir_resultado(r):
    """Imprime resultado formatado para terminal."""
    print(f"\n{'='*65}")
    print(f"  CÁLCULO DE GANHO DE CAPITAL EM IMÓVEL")
    print(f"{'='*65}")
    print(f"  Valor de venda:       {formatar_brl(r['valor_venda'])}")
    print(f"  Custo de aquisição:   {formatar_brl(r['custo_aquisicao'])}")
    if r['benfeitorias'] > 0:
        print(f"  Benfeitorias:         {formatar_brl(r['benfeitorias'])}")
    if r['corretagem'] > 0:
        print(f"  Corretagem/custos:    {formatar_brl(r['corretagem'])}")
    print(f"  Custo total:          {formatar_brl(r['custo_total'])}")
    print(f"\n  Ganho bruto:          {formatar_brl(r['ganho_bruto'])}")
    print(f"  Fator redutor (FRT):  {r['fator_redutor']:.2%}")
    print(f"  ({r['fator_redutor_descricao']})")
    print(f"  Ganho tributável:     {formatar_brl(r['ganho_tributavel'])}")
    print(f"\n  Isenções aplicadas:")
    for isen in r['isencoes_aplicadas']:
        print(f"    • {isen}")
    print(f"\n  IMPOSTO DEVIDO:       {formatar_brl(r['imposto_devido'])}")
    print(f"  Alíquota efetiva:     {r['aliquota_efetiva']:.2f}%")
    print(f"\n  Base legal: {r['base_legal']}")
    print(f"  ⚠️  {r['disclaimer']}")
    print(f"{'='*65}\n")


# ─── TESTES INTEGRADOS ────────────────────────────────────────────

def rodar_testes():
    """
    Testes com valores conhecidos para validar o cálculo de GCAP imóvel.
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
    
    print("\n🧪 RODANDO TESTES DE GANHO DE CAPITAL EM IMÓVEL...")
    print(f"{'─'*65}")
    
    # Teste 1: Venda com lucro — imóvel pós-1988, alíquota 15%
    r = calcular_gcap_imovel(500000, 300000, "2010-01-01")
    teste("Venda com lucro pós-1988 (500k - 300k = 200k × 15%)",
          r, "imposto_devido", 30000.0)
    
    # Teste 2: Venda com prejuízo — zero imposto
    r = calcular_gcap_imovel(250000, 300000, "2015-01-01")
    teste("Venda com prejuízo (250k - 300k = -50k)",
          r, "imposto_devido", 0.0)
    
    # Teste 3: Aquisição pré-1969 — isenção 100%
    r = calcular_gcap_imovel(500000, 300000, "1968-06-15")
    teste("Imóvel adquirido antes de 1969 (isenção 100%)",
          r, "imposto_devido", 0.0)
    
    # Teste 4: Aquisição 1980 — redução fixa por ano de aquisição (IN SRF 84/2001)
    # 1988 - 1980 + 1 = 9 anos → redução 45% → FRT = 0.55
    # Ganho bruto: 200k × 0.55 = 110k (NÃO depende da data de venda)
    r = calcular_gcap_imovel(500000, 300000, "1980-01-01", data_venda="1990-01-01")
    teste("Imóvel adquirido 1980, vendido 1990 (FRT 55%)",
          r, "ganho_tributavel", 110000.0, tolerancia=1000)
    
    # Teste 5: Aquisição 1988 — redução mínima (IN SRF 84/2001)
    # 1988 - 1988 + 1 = 1 ano → redução 5% → FRT = 0.95
    r = calcular_gcap_imovel(500000, 300000, "1988-06-15", data_venda="1995-01-01")
    # Ganho bruto: 200k × 0.95 = 190k
    teste("Imóvel adquirido 1988, vendido 1995",
          r, "ganho_bruto", 200000.0)
    
    # Teste 6: Único imóvel ≤ R$ 440k — isenção
    r = calcular_gcap_imovel(400000, 300000, "2015-01-01", 
                             unico_imovel=True, valor_ate_440k=True)
    teste("Único imóvel residencial ≤ R$ 440k (isenção)",
          r, "imposto_devido", 0.0)
    
    # Teste 7: Com benfeitorias
    r = calcular_gcap_imovel(600000, 300000, "2012-01-01", benfeitorias=50000)
    # Custo total: 350k, ganho bruto: 250k, imposto ~37.5k
    teste("Venda com benfeitorias (600k - 300k - 50k = 250k)",
          r, "ganho_bruto", 250000.0)
    
    # Teste 8: Ganho > R$ 5M — alíquota progressiva
    r = calcular_gcap_imovel(6000000, 500000, "2010-01-01")
    # Ganho bruto: 5.5M, progressivo: (5M × 15%) + (0.5M × 17.5%) = 750k + 87.5k = 837.5k
    teste("Ganho > R$ 5M (progressiva: 5M@15% + 0.5M@17.5%)",
          r, "ganho_bruto", 5500000.0)
    
    # Teste 9: Com corretagem
    r = calcular_gcap_imovel(500000, 300000, "2014-01-01", corretagem=20000)
    # Custo total: 320k, ganho bruto: 180k, imposto: 27k
    teste("Venda com corretagem (500k - 300k - 20k = 180k)",
          r, "ganho_bruto", 180000.0)
    
    # Teste 10: Zero ganho (venda = custo)
    r = calcular_gcap_imovel(300000, 300000, "2018-01-01")
    teste("Venda ao preço de custo (zero ganho)",
          r, "imposto_devido", 0.0)
    
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
    elif len(sys.argv) >= 4:
        try:
            valor_venda = float(sys.argv[1].replace(",", "."))
            custo_aquisicao = float(sys.argv[2].replace(",", "."))
            data_aquisicao = sys.argv[3]
            
            benfeitorias = 0
            corretagem = 0
            unico_imovel = False
            valor_ate_440k = False
            
            # Parse flags
            if "--benfeitorias" in sys.argv:
                idx = sys.argv.index("--benfeitorias")
                benfeitorias = float(sys.argv[idx + 1].replace(",", "."))
            if "--corretagem" in sys.argv:
                idx = sys.argv.index("--corretagem")
                corretagem = float(sys.argv[idx + 1].replace(",", "."))
            if "--unico-imovel" in sys.argv:
                unico_imovel = True
            if "--ate-440k" in sys.argv:
                valor_ate_440k = True
            
            r = calcular_gcap_imovel(valor_venda, custo_aquisicao, data_aquisicao,
                                     benfeitorias=benfeitorias, corretagem=corretagem,
                                     unico_imovel=unico_imovel, valor_ate_440k=valor_ate_440k)
            imprimir_resultado(r)
        except (ValueError, IndexError) as e:
            print(f"Erro: {e}")
            print("Uso: python3 calc_gcap_imovel.py <venda> <custo> <data_aquisicao>")
            print("     [--benfeitorias <valor>] [--corretagem <valor>]")
            print("     [--unico-imovel] [--ate-440k]")
            print("     python3 calc_gcap_imovel.py --teste")
            sys.exit(1)
    else:
        print("Uso: python3 calc_gcap_imovel.py <venda> <custo> <data_aquisicao>")
        print("     [--benfeitorias <valor>] [--corretagem <valor>]")
        print("     [--unico-imovel] [--ate-440k]")
        print("     python3 calc_gcap_imovel.py --teste")
        print("\nExemplo:")
        print("  python3 calc_gcap_imovel.py 500000 300000 2015-06-10")
        print("  python3 calc_gcap_imovel.py 500000 300000 2015-06-10 --benfeitorias 50000")
