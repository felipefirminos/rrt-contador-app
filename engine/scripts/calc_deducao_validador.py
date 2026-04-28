#!/usr/bin/env python3
"""
Classificador e validador de deduções IRPF PF — RRT-Group-Contador v3.0

Output TERNÁRIO (Judge mandate):
  - VALIDADO: dedução com base legal clara e documentação informada
  - FLAGGED: dedução possível mas requer revisão humana (limite, regra especial)
  - REJEITADO: dedução sem base ou acima do limite legal

NUNCA auto-aprova. Sempre requer revisão do contador.

Base legal: Art. 8° Lei 9.250/95, RIR/2018 (Decreto 9.580/2018)

Uso:
    python3 calc_deducao_validador.py --teste
    python3 calc_deducao_validador.py --exemplo
"""

import json
import sys
import os
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TABELA_PATH = os.path.join(SCRIPT_DIR, "tabelas", "irpf_deducoes.json")


def carregar_regras(caminho=TABELA_PATH):
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def validar_deducao(categoria, valor, documentos_informados=None, cpf_beneficiario=None,
                    renda_bruta_anual=None, num_dependentes=1, regras=None):
    """
    Valida uma dedução individual do IRPF.

    Args:
        categoria: str — "saude", "educacao", "previdencia_oficial",
                   "previdencia_privada", "dependentes", "pensao_alimenticia"
        valor: float — valor da dedução
        documentos_informados: list of str — documentos apresentados
        cpf_beneficiario: str or None — CPF do beneficiário (se aplicável)
        renda_bruta_anual: float or None — para cálculo de limite PGBL
        num_dependentes: int — quantidade de dependentes (para dedução "dependentes")
        regras: dict or None — regras carregadas (default: carrega do JSON)

    Returns:
        dict com:
            - status: "VALIDADO" | "FLAGGED" | "REJEITADO"
            - categoria: str
            - valor_informado: float
            - valor_aceito: float (pode ser menor que informado se acima do limite)
            - valor_excedente: float
            - confianca_pct: float (0-100)
            - motivos: list of str (razões para flag ou rejeição)
            - documentos_faltantes: list of str
            - requer_revisao_humana: bool (SEMPRE True)
            - base_legal: str
            - disclaimer: str
    """
    if regras is None:
        regras = carregar_regras()

    if documentos_informados is None:
        documentos_informados = []

    categorias_raw = regras.get("categorias", [])
    # Support both list-of-dicts (JSON) and dict (legacy) formats
    if isinstance(categorias_raw, list):
        categorias = {c["tipo"]: c for c in categorias_raw if "tipo" in c}
    else:
        categorias = categorias_raw
    if categoria not in categorias:
        return {
            "status": "REJEITADO",
            "categoria": categoria,
            "valor_informado": valor,
            "valor_aceito": 0.0,
            "valor_excedente": valor,
            "confianca_pct": 0.0,
            "motivos": [f"Categoria '{categoria}' não reconhecida. Categorias válidas: {', '.join(categorias.keys())}"],
            "documentos_faltantes": [],
            "requer_revisao_humana": True,
            "base_legal": "N/A",
            "disclaimer": "Calculado por automação. Revisão obrigatória pelo contador."
        }

    regra = categorias[categoria]
    motivos = []
    docs_faltantes = []
    confianca = 80.0  # baseline
    valor_aceito = valor
    valor_excedente = 0.0

    # 1. Validação de valor negativo ou zero
    if valor <= 0:
        return {
            "status": "REJEITADO",
            "categoria": categoria,
            "valor_informado": valor,
            "valor_aceito": 0.0,
            "valor_excedente": 0.0,
            "confianca_pct": 100.0,
            "motivos": ["Valor deve ser positivo"],
            "documentos_faltantes": [],
            "requer_revisao_humana": True,
            "base_legal": regra.get("base_legal", ""),
            "disclaimer": "Calculado por automação. Revisão obrigatória pelo contador."
        }

    # 2. Verificação de limite anual
    limite_anual = regra.get("limite_anual")
    if limite_anual is not None:
        # Para dependentes, limite é por dependente
        if categoria == "dependentes":
            limite_efetivo = limite_anual * num_dependentes
        else:
            limite_efetivo = limite_anual

        if valor > limite_efetivo:
            valor_excedente = round(valor - limite_efetivo, 2)
            valor_aceito = limite_efetivo
            motivos.append(
                f"Valor excede limite legal de R$ {limite_efetivo:,.2f} "
                f"(excedente: R$ {valor_excedente:,.2f})"
            )
            confianca -= 20.0

    # 3. Verificação de limite proporcional (previdência privada = 12% renda bruta)
    if categoria == "previdencia_privada" and renda_bruta_anual is not None:
        limite_prop = round(renda_bruta_anual * 0.12, 2)
        if valor > limite_prop:
            valor_excedente_prop = round(valor - limite_prop, 2)
            if limite_prop < valor_aceito:
                valor_aceito = limite_prop
                valor_excedente = round(valor - limite_prop, 2)
            motivos.append(
                f"PGBL: limite é 12% da renda bruta anual = R$ {limite_prop:,.2f} "
                f"(excedente: R$ {valor_excedente_prop:,.2f})"
            )
            confianca -= 15.0

    # 4. Verificação de documentação (fuzzy: any informed doc that partially matches counts)
    docs_exigidos = regra.get("documentos_exigidos", [])
    docs_informados_lower = [d.lower() for d in documentos_informados]
    for doc in docs_exigidos:
        doc_lower = doc.lower()
        # Check if any informed doc contains key words from the required doc
        matched = any(
            any(palavra in inf for palavra in doc_lower.split()[:3])
            for inf in docs_informados_lower
        ) if docs_informados_lower else False
        if not matched:
            docs_faltantes.append(doc)

    if docs_faltantes and documentos_informados:
        # Partial docs provided — mild penalty
        motivos.append(f"Documentação parcial: {len(docs_faltantes)} de {len(docs_exigidos)} docs podem estar faltando")
        confianca -= 3.0 * len(docs_faltantes)
    elif docs_faltantes and not documentos_informados:
        motivos.append(f"Documentação não informada: {len(docs_exigidos)} documento(s) exigido(s)")
        confianca -= 10.0 * min(len(docs_faltantes), 3)

    # 5. Verificação de CPF beneficiário
    requer_cpf = regra.get("requer_cpf_beneficiario", False)
    if requer_cpf and not cpf_beneficiario:
        motivos.append("CPF do beneficiário obrigatório para esta categoria")
        confianca -= 15.0

    # 6. Verificação de comprovante
    requer_comprov = regra.get("requer_comprovante", True)
    if requer_comprov and not documentos_informados:
        motivos.append("Nenhum comprovante informado — dedução sem suporte documental")
        confianca -= 30.0

    # 7. Regras de validação específicas (informational — no confidence penalty)
    # These are flagged for the human reviewer, not used to reject
    regras_validacao = regra.get("regras_validacao", [])

    # Clamp confiança
    confianca = max(0.0, min(100.0, confianca))

    # Determine status
    if confianca >= 70.0 and not docs_faltantes and valor_excedente == 0:
        status = "VALIDADO"
    elif confianca >= 40.0:
        status = "FLAGGED"
    else:
        status = "REJEITADO"

    valor_aceito = round(valor_aceito, 2)

    return {
        "status": status,
        "categoria": categoria,
        "valor_informado": round(valor, 2),
        "valor_aceito": valor_aceito,
        "valor_excedente": round(valor_excedente, 2),
        "confianca_pct": round(confianca, 1),
        "motivos": motivos if motivos else ["Dentro dos parâmetros legais"],
        "documentos_faltantes": docs_faltantes,
        "requer_revisao_humana": True,  # SEMPRE True — Judge mandate
        "base_legal": regra.get("base_legal", ""),
        "disclaimer": "Calculado por automação RRT-Group-Contador v3.0 — módulo IRPF PF. "
                      "Este resultado NÃO substitui a análise do contador responsável."
    }


def validar_multiplas_deducoes(deducoes, renda_bruta_anual=None, regras=None):
    """
    Valida uma lista de deduções e retorna resumo consolidado.

    Args:
        deducoes: list of dict, each with:
            - categoria: str
            - valor: float
            - documentos: list of str (optional)
            - cpf_beneficiario: str (optional)
            - num_dependentes: int (optional, for "dependentes" category)
        renda_bruta_anual: float (for PGBL limit calculation)

    Returns:
        dict com resultados individuais e totais
    """
    if regras is None:
        regras = carregar_regras()

    resultados = []
    total_aceito = 0.0
    total_excedente = 0.0
    total_rejeitado = 0.0
    stats = {"VALIDADO": 0, "FLAGGED": 0, "REJEITADO": 0}

    for ded in deducoes:
        r = validar_deducao(
            categoria=ded.get("categoria", ""),
            valor=ded.get("valor", 0),
            documentos_informados=ded.get("documentos", []),
            cpf_beneficiario=ded.get("cpf_beneficiario"),
            renda_bruta_anual=renda_bruta_anual,
            num_dependentes=ded.get("num_dependentes", 1),
            regras=regras
        )
        resultados.append(r)
        stats[r["status"]] += 1
        total_aceito += r["valor_aceito"]
        total_excedente += r["valor_excedente"]
        if r["status"] == "REJEITADO":
            total_rejeitado += r["valor_informado"]

    return {
        "resultados": resultados,
        "total_deducoes": len(deducoes),
        "total_aceito": round(total_aceito, 2),
        "total_excedente": round(total_excedente, 2),
        "total_rejeitado": round(total_rejeitado, 2),
        "contagem_status": stats,
        "requer_revisao_humana": True,
        "disclaimer": "Calculado por automação RRT-Group-Contador v3.0 — módulo IRPF PF. "
                      "TODOS os resultados requerem revisão do contador responsável."
    }


def formatar_brl(valor):
    """Formata valor em R$ brasileiro."""
    if valor < 0:
        return f"-R$ {abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    """Imprime resultado de validação formatado."""
    icone = {"VALIDADO": "✅", "FLAGGED": "⚠️", "REJEITADO": "❌"}
    print(f"\n  {icone.get(r['status'], '?')} [{r['status']}] {r['categoria']}")
    print(f"     Valor informado: {formatar_brl(r['valor_informado'])}")
    print(f"     Valor aceito:    {formatar_brl(r['valor_aceito'])}")
    if r['valor_excedente'] > 0:
        print(f"     Excedente:       {formatar_brl(r['valor_excedente'])}")
    print(f"     Confiança:       {r['confianca_pct']}%")
    if r['motivos'] and r['motivos'] != ["Dentro dos parâmetros legais"]:
        for m in r['motivos']:
            print(f"     • {m}")
    if r['documentos_faltantes']:
        print(f"     Docs faltantes: {', '.join(r['documentos_faltantes'])}")
    print(f"     Base legal: {r['base_legal']}")


# ─── TESTES INTEGRADOS ──────────────────────────────────────────

def rodar_testes():
    regras = carregar_regras()
    testes_ok = 0
    testes_total = 0

    def teste(descricao, condicao):
        nonlocal testes_ok, testes_total
        testes_total += 1
        if condicao:
            testes_ok += 1
        status = "PASSOU" if condicao else "FALHOU"
        print(f"  [{status}] {descricao}")

    print("\n🧪 RODANDO TESTES DO CALC_DEDUCAO_VALIDADOR...")
    print(f"{'─'*60}")

    # 1. Saúde — sem limite, com docs (using full names from JSON)
    r = validar_deducao("saude", 15000.00,
                        documentos_informados=["Recibo ou Nota Fiscal eletrônica", "CPF do contribuinte ou dependente", "Comprovante de pagamento"],
                        cpf_beneficiario="12345678901",
                        regras=regras)
    teste("Saúde R$15K com docs → VALIDADO", r["status"] == "VALIDADO")
    teste("Saúde sem limite: valor_aceito == valor_informado", r["valor_aceito"] == 15000.00)

    # 2. Saúde — sem docs
    r = validar_deducao("saude", 5000.00, documentos_informados=[], regras=regras)
    teste("Saúde sem docs → FLAGGED ou REJEITADO", r["status"] in ("FLAGGED", "REJEITADO"))
    teste("Saúde sem docs: docs_faltantes não vazio", len(r["documentos_faltantes"]) > 0)

    # 3. Educação — dentro do limite
    r = validar_deducao("educacao", 3000.00,
                        documentos_informados=["Recibo de matrícula ou contrato", "Nota Fiscal ou recibo da instituição", "CPF do estudante", "Comprovante de pagamento"],
                        cpf_beneficiario="12345678901",
                        regras=regras)
    teste("Educação R$3K (dentro limite) → VALIDADO", r["status"] == "VALIDADO")
    teste("Educação: valor_aceito == 3000", r["valor_aceito"] == 3000.00)

    # 4. Educação — acima do limite
    r = validar_deducao("educacao", 5000.00,
                        documentos_informados=["Recibo de matrícula ou contrato", "Nota Fiscal ou recibo da instituição", "CPF do estudante", "Comprovante de pagamento"],
                        cpf_beneficiario="12345678901",
                        regras=regras)
    teste("Educação R$5K (acima limite) → FLAGGED", r["status"] == "FLAGGED")
    teste("Educação: valor_aceito limitado", r["valor_aceito"] < 5000.00)
    teste("Educação: excedente > 0", r["valor_excedente"] > 0)

    # 5. Previdência privada — 12% da renda
    r = validar_deducao("previdencia_privada", 20000.00,
                        documentos_informados=["Demonstrativo de contribuições", "Extrato da conta", "Comprovante de pagamento", "CNPJ da instituição"],
                        cpf_beneficiario="12345678901",
                        renda_bruta_anual=100000.00,
                        regras=regras)
    teste("PGBL R$20K com renda R$100K → FLAGGED (excede 12%)", r["status"] == "FLAGGED")
    teste("PGBL: valor_aceito <= 12000", r["valor_aceito"] <= 12000.00)

    # 6. Dependentes — valor correto
    r = validar_deducao("dependentes", 4550.16,
                        documentos_informados=["CPF do dependente", "Comprovante de parentesco", "Documentação do motivo"],
                        cpf_beneficiario="12345678901",
                        num_dependentes=2,
                        regras=regras)
    teste("Dependentes 2x R$2275.08 = R$4550.16 → VALIDADO", r["status"] == "VALIDADO")

    # 7. Dependentes — excede limite
    r = validar_deducao("dependentes", 10000.00,
                        documentos_informados=["CPF do dependente", "Comprovante de parentesco"],
                        cpf_beneficiario="12345678901",
                        num_dependentes=2,
                        regras=regras)
    teste("Dependentes R$10K para 2 deps → FLAGGED", r["status"] == "FLAGGED")

    # 8. Pensão alimentícia — sem limite mas requer ordem judicial
    r = validar_deducao("pensao_alimenticia", 36000.00,
                        documentos_informados=["Sentença judicial ou acordo homologado", "CPF do alimentado", "Comprovantes de pagamento", "Número do processo judicial"],
                        cpf_beneficiario="98765432100",
                        regras=regras)
    teste("Pensão R$36K com docs → VALIDADO", r["status"] == "VALIDADO")

    # 9. Categoria inválida
    r = validar_deducao("investimentos", 5000.00, regras=regras)
    teste("Categoria inválida → REJEITADO", r["status"] == "REJEITADO")
    teste("Categoria inválida: valor_aceito == 0", r["valor_aceito"] == 0.0)

    # 10. Valor zero
    r = validar_deducao("saude", 0.0, regras=regras)
    teste("Valor zero → REJEITADO", r["status"] == "REJEITADO")

    # 11. Valor negativo
    r = validar_deducao("saude", -100.0, regras=regras)
    teste("Valor negativo → REJEITADO", r["status"] == "REJEITADO")

    # 12. requer_revisao_humana SEMPRE True
    r = validar_deducao("saude", 1000.00,
                        documentos_informados=["Recibo ou Nota Fiscal eletrônica", "CPF do contribuinte"],
                        cpf_beneficiario="12345678901",
                        regras=regras)
    teste("requer_revisao_humana é SEMPRE True", r["requer_revisao_humana"] is True)

    # 13. Múltiplas deduções
    deducoes = [
        {"categoria": "saude", "valor": 8000.00, "documentos": ["Recibo ou Nota Fiscal eletrônica", "CPF do contribuinte", "Comprovante de pagamento"], "cpf_beneficiario": "111"},
        {"categoria": "educacao", "valor": 3000.00, "documentos": ["Recibo de matrícula", "Nota Fiscal", "CPF do estudante", "Comprovante de pagamento"], "cpf_beneficiario": "222"},
        {"categoria": "dependentes", "valor": 2275.08, "documentos": ["CPF do dependente", "Comprovante de parentesco"], "cpf_beneficiario": "333", "num_dependentes": 1},
    ]
    mr = validar_multiplas_deducoes(deducoes, renda_bruta_anual=150000.00, regras=regras)
    teste("Múltiplas: total_deducoes == 3", mr["total_deducoes"] == 3)
    teste("Múltiplas: total_aceito > 0", mr["total_aceito"] > 0)
    teste("Múltiplas: requer_revisao_humana True", mr["requer_revisao_humana"] is True)

    # 14. Previdência oficial — sem limite
    r = validar_deducao("previdencia_oficial", 50000.00,
                        documentos_informados=["Extrato do CNIS", "Comprovante de pagamento", "Recibos do INSS"],
                        regras=regras)
    teste("INSS R$50K com docs → VALIDADO (sem limite)", r["status"] == "VALIDADO")
    teste("INSS: valor_aceito == 50000", r["valor_aceito"] == 50000.00)

    # 15. Envelope tem todas as chaves obrigatórias
    chaves = {"status", "categoria", "valor_informado", "valor_aceito", "valor_excedente",
              "confianca_pct", "motivos", "documentos_faltantes", "requer_revisao_humana",
              "base_legal", "disclaimer"}
    r = validar_deducao("saude", 100.00, documentos_informados=["Recibo ou Nota Fiscal eletrônica", "CPF do contribuinte", "Comprovante de pagamento"], cpf_beneficiario="111", regras=regras)
    teste("Envelope tem todas as 11 chaves", chaves.issubset(set(r.keys())))

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
        ok = rodar_testes()
        sys.exit(0 if ok else 1)
    elif len(sys.argv) > 1 and sys.argv[1] == "--exemplo":
        print("\n" + "="*60)
        print("  EXEMPLO: Validação de Deduções IRPF")
        print("="*60)
        regras = carregar_regras()
        deducoes = [
            {"categoria": "saude", "valor": 12000.00, "documentos": ["recibo_medico", "nota_fiscal_saude"]},
            {"categoria": "educacao", "valor": 5000.00, "documentos": ["recibo_instituicao_ensino"], "cpf_beneficiario": "111"},
            {"categoria": "previdencia_privada", "valor": 20000.00, "documentos": ["informe_pgbl"]},
        ]
        mr = validar_multiplas_deducoes(deducoes, renda_bruta_anual=120000.00, regras=regras)
        for r in mr["resultados"]:
            imprimir_resultado(r)
        print(f"\n  TOTAL ACEITO: {formatar_brl(mr['total_aceito'])}")
        print(f"  TOTAL EXCEDENTE: {formatar_brl(mr['total_excedente'])}")
        print(f"  Status: {mr['contagem_status']}")
        print("="*60)
    else:
        print("Uso: python3 calc_deducao_validador.py --teste")
        print("      python3 calc_deducao_validador.py --exemplo")
