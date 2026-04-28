"""
calcular_tema_69.py — Memória de cálculo da exclusão do ICMS da base de
PIS/COFINS (Tema 69 STF, RE 574.706).

Regra pós-julgamento dos embargos (maio/2021):
- ICMS a excluir = ICMS DESTACADO na nota fiscal.
- Aplicável aos regimes cumulativo (Lei 9.718/98) e não cumulativo
  (Leis 10.637/2002 e 10.833/2003).
- NÃO aplicável ao Simples Nacional (PIS/COFINS embutidos no DAS).
- Modulação: efeitos a partir de 15/03/2017 (exceto quem tinha ação
  ajuizada antes, que recupera os 5 anos anteriores à propositura).

Base legal:
- CF/88, art. 195, I, b
- Lei 9.718/98, art. 3º (cumulativo)
- Lei 10.637/2002, art. 1º (PIS não cumulativo)
- Lei 10.833/2003, art. 1º (COFINS não cumulativa)
- RE 574.706/PR (Tema 69 STF)
- Embargos de declaração julgados em 13/05/2021

Autor: RRT Group — 22/04/2026
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Literal


def _brl(valor) -> str:
    """Formata Decimal/float/int em padrão pt-BR: R$ 1.234,56."""
    try:
        v = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        v = Decimal("0.00")
    sinal = "-" if v < 0 else ""
    inteiro, _, decimais = f"{abs(v):.2f}".partition(".")
    # separador de milhar com ponto
    partes = []
    while len(inteiro) > 3:
        partes.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    partes.insert(0, inteiro)
    inteiro_fmt = ".".join(partes)
    return f"{sinal}R$ {inteiro_fmt},{decimais}"


REGIMES_APLICAVEIS = ("LUCRO_REAL", "LUCRO_PRESUMIDO")

ALIQUOTAS = {
    "LUCRO_REAL": {  # não-cumulativo
        "PIS": Decimal("0.0165"),
        "COFINS": Decimal("0.076"),
    },
    "LUCRO_PRESUMIDO": {  # cumulativo
        "PIS": Decimal("0.0065"),
        "COFINS": Decimal("0.03"),
    },
}

MARCO_MODULACAO = date(2017, 3, 15)


@dataclass
class OperacaoMensal:
    """Representa uma competência mensal para cálculo."""
    competencia: date  # primeiro dia do mês
    receita_bruta: Decimal
    icms_destacado: Decimal  # ICMS destacado nas NFs de saída da competência
    regime: Literal["LUCRO_REAL", "LUCRO_PRESUMIDO"]


@dataclass
class ResultadoMensal:
    competencia: date
    regime: str
    receita_bruta: Decimal
    icms_destacado: Decimal
    pis_pago_indevido: Decimal
    cofins_pago_indevido: Decimal
    total_recuperavel: Decimal
    dentro_modulacao: bool
    observacao: str


def calcular_credito_mensal(
    op: OperacaoMensal,
    tem_acao_pre_15_03_2017: bool = False,
) -> ResultadoMensal:
    """
    Calcula crédito mensal de PIS/COFINS indevidamente recolhidos sobre
    ICMS destacado.

    Args:
        op: dados da competência.
        tem_acao_pre_15_03_2017: se a empresa tinha ação ajuizada antes da
            modulação (permite recuperar períodos pré-15/03/2017).

    Returns:
        ResultadoMensal com valores a recuperar.
    """
    if op.regime not in REGIMES_APLICAVEIS:
        raise ValueError(
            f"Regime {op.regime} não aplicável ao Tema 69. "
            "Simples Nacional e MEI ficam fora."
        )

    # Verifica se a competência cai dentro ou fora da modulação
    dentro_modulacao = op.competencia >= MARCO_MODULACAO
    elegivel = dentro_modulacao or tem_acao_pre_15_03_2017

    if not elegivel:
        return ResultadoMensal(
            competencia=op.competencia,
            regime=op.regime,
            receita_bruta=op.receita_bruta,
            icms_destacado=op.icms_destacado,
            pis_pago_indevido=Decimal("0"),
            cofins_pago_indevido=Decimal("0"),
            total_recuperavel=Decimal("0"),
            dentro_modulacao=False,
            observacao=(
                "❌ Fora da modulação. Competência anterior a 15/03/2017 "
                "e sem ação judicial anterior — crédito não elegível."
            ),
        )

    aliquotas = ALIQUOTAS[op.regime]

    # Valor indevido = ICMS × alíquota
    pis_indevido = (op.icms_destacado * aliquotas["PIS"]).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    cofins_indevido = (op.icms_destacado * aliquotas["COFINS"]).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    total = pis_indevido + cofins_indevido

    obs_base = f"✅ Dentro da modulação. ICMS destacado: {_brl(op.icms_destacado)}"
    if not dentro_modulacao and tem_acao_pre_15_03_2017:
        obs_base = f"✅ Pré-15/03/2017 mas com ação ajuizada. {obs_base}"

    return ResultadoMensal(
        competencia=op.competencia,
        regime=op.regime,
        receita_bruta=op.receita_bruta,
        icms_destacado=op.icms_destacado,
        pis_pago_indevido=pis_indevido,
        cofins_pago_indevido=cofins_indevido,
        total_recuperavel=total,
        dentro_modulacao=dentro_modulacao,
        observacao=obs_base,
    )


def calcular_total(
    operacoes: list[OperacaoMensal],
    tem_acao_pre_15_03_2017: bool = False,
) -> dict:
    """Calcula total recuperável em múltiplas competências."""
    resultados = [
        calcular_credito_mensal(op, tem_acao_pre_15_03_2017)
        for op in operacoes
    ]

    total_pis = sum((r.pis_pago_indevido for r in resultados), Decimal("0"))
    total_cofins = sum((r.cofins_pago_indevido for r in resultados), Decimal("0"))
    total = total_pis + total_cofins

    return {
        "resultados_mensais": resultados,
        "total_pis_recuperavel": total_pis,
        "total_cofins_recuperavel": total_cofins,
        "total_geral": total,
        "competencias_elegiveis": sum(1 for r in resultados if r.total_recuperavel > 0),
        "competencias_bloqueadas": sum(1 for r in resultados if r.total_recuperavel == 0),
    }


# ---------------------------------------------------------------------------
# IMPORTANTE — atualização monetária
# ---------------------------------------------------------------------------
# O valor a recuperar deve ser atualizado pela SELIC a partir do pagamento
# indevido até a data da compensação/restituição (art. 39, §4º Lei 9.250/95).
# Esta função calcula apenas o principal. Para atualização, use o módulo
# de correção SELIC (rrt-group-contador/scripts/atualizacao_selic.py ou
# similar) ou o simulador do e-CAC.


# ---------------------------------------------------------------------------
# Exemplo de uso
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Cliente Lucro Real, competência abril/2025
    op = OperacaoMensal(
        competencia=date(2025, 4, 1),
        receita_bruta=Decimal("500000.00"),
        icms_destacado=Decimal("72000.00"),
        regime="LUCRO_REAL",
    )

    r = calcular_credito_mensal(op)
    print(f"Competência: {r.competencia.strftime('%m/%Y')}")
    print(f"Regime: {r.regime}")
    print(f"ICMS destacado: {_brl(r.icms_destacado)}")
    print(f"PIS indevido: {_brl(r.pis_pago_indevido)}")
    print(f"COFINS indevido: {_brl(r.cofins_pago_indevido)}")
    print(f"Total principal: {_brl(r.total_recuperavel)}")
    print(f"\n{r.observacao}")
    print("\n⚠️ Valor NÃO atualizado pela SELIC — aplicar correção antes do pedido.")
