"""
verificar_prescricao.py — Check de prescrição quinquenal para recuperação
tributária (art. 168 CTN; art. 74 Lei 9.430/96 para compensação).

Regra geral:
- Prazo de 5 anos para pedir restituição/compensação de tributos federais
  pagos indevidamente (art. 168, I CTN c/c art. 3º LC 118/2005 para
  tributos por lançamento por homologação).
- Início do prazo: data do pagamento indevido (para homologação) ou data
  do ato que declarou a inconstitucionalidade da norma (em casos de
  repetição de indébito específicos — sempre validar jurisprudencialmente).

Base legal:
- CTN, art. 165, 168, 169
- LC 118/2005, art. 3º
- Lei 9.430/96, art. 74
- IN RFB 2.055/2021 (com alterações posteriores — verificar vigência
  antes de protocolar: a IN foi emendada diversas vezes desde a publicação)

Autor: RRT Group — 22/04/2026
"""

from datetime import date, datetime, timedelta
from dataclasses import dataclass
from typing import Optional


@dataclass
class ResultadoPrescricao:
    """Resultado da análise de prescrição para um pagamento indevido."""
    data_pagamento: date
    data_corte: date              # data a partir da qual já prescreveu
    data_limite_pleito: date      # último dia para pleitear restituição
    dias_restantes: int
    prescrito: bool
    observacao: str


def verificar_prescricao(
    data_pagamento: date,
    data_referencia: Optional[date] = None,
) -> ResultadoPrescricao:
    """
    Verifica se pagamento indevido ainda está no prazo de 5 anos para
    pleitear restituição/compensação.

    Args:
        data_pagamento: data do recolhimento indevido (fato gerador do
            direito de repetir).
        data_referencia: data do protocolo do pedido/ação (default: hoje).

    Returns:
        ResultadoPrescricao com análise estruturada.

    Raises:
        ValueError: se data_pagamento for no futuro.

    Nota:
        - Para tributos federais por homologação (PIS, COFINS, IRPJ, CSLL,
          IRRF), a regra vigente é 5 anos do pagamento (LC 118/2005, art. 3º).
        - Casos específicos (decisão judicial transitada em julgado, lei
          declarada inconstitucional pelo STF) podem ter início de prazo
          diferente — validar individualmente.
    """
    if data_pagamento > date.today():
        raise ValueError(f"Data de pagamento não pode ser futura: {data_pagamento}")

    data_ref = data_referencia or date.today()

    # Limite: 5 anos do pagamento
    try:
        data_limite = data_pagamento.replace(year=data_pagamento.year + 5)
    except ValueError:
        # 29/02 em ano não bissexto → 28/02
        data_limite = data_pagamento.replace(
            year=data_pagamento.year + 5, day=28
        )

    dias_restantes = (data_limite - data_ref).days
    prescrito = dias_restantes < 0

    def _pluralizar_dias(n: int) -> str:
        return "1 dia" if abs(n) == 1 else f"{abs(n)} dias"

    def _restante(n: int) -> str:
        return "restante" if abs(n) == 1 else "restantes"

    if prescrito:
        obs = (
            f"❌ PRESCRITO há {_pluralizar_dias(dias_restantes)}. "
            f"Último dia para pleito era {data_limite.strftime('%d/%m/%Y')}. "
            f"Não é mais possível recuperar este pagamento administrativamente."
        )
    elif dias_restantes < 90:
        obs = (
            f"🟠 URGENTE: apenas {_pluralizar_dias(dias_restantes)} "
            f"{_restante(dias_restantes)}. "
            f"Protocolar pedido ATÉ {data_limite.strftime('%d/%m/%Y')}."
        )
    elif dias_restantes < 365:
        obs = (
            f"🟡 ATENÇÃO: {_pluralizar_dias(dias_restantes)} "
            f"{_restante(dias_restantes)} "
            f"(menos de 1 ano). Priorizar."
        )
    else:
        obs = (
            f"✅ Prazo OK — {_pluralizar_dias(dias_restantes)} "
            f"{_restante(dias_restantes)}. "
            f"Pleitear até {data_limite.strftime('%d/%m/%Y')}."
        )

    return ResultadoPrescricao(
        data_pagamento=data_pagamento,
        data_corte=data_ref,
        data_limite_pleito=data_limite,
        dias_restantes=dias_restantes,
        prescrito=prescrito,
        observacao=obs,
    )


def calcular_periodo_recuperavel(data_pleito: Optional[date] = None) -> tuple[date, date]:
    """
    Calcula o período de 5 anos recuperáveis contado a partir da data
    do pleito.

    Returns:
        (data_inicio_periodo, data_fim_periodo)
        — pagamentos feitos dentro desta janela são recuperáveis.
    """
    data_fim = data_pleito or date.today()
    try:
        data_inicio = data_fim.replace(year=data_fim.year - 5)
    except ValueError:
        data_inicio = data_fim.replace(year=data_fim.year - 5, day=28)

    return data_inicio, data_fim


# ---------------------------------------------------------------------------
# Exemplo de uso
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Caso 1: pagamento há 3 anos
    r1 = verificar_prescricao(date(2023, 4, 22))
    print(f"Pagamento 22/04/2023 → {r1.observacao}")

    # Caso 2: pagamento há 6 anos (prescrito)
    r2 = verificar_prescricao(date(2020, 3, 15))
    print(f"Pagamento 15/03/2020 → {r2.observacao}")

    # Caso 3: pagamento urgente (4 anos e 11 meses)
    r3 = verificar_prescricao(date(2021, 5, 22))
    print(f"Pagamento 22/05/2021 → {r3.observacao}")

    # Período recuperável agora
    ini, fim = calcular_periodo_recuperavel()
    print(f"\nPeríodo recuperável hoje: {ini.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}")
