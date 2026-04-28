from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


# ─── Simples Nacional ──────────────────────────────────────────────

Anexo = Literal["I", "II", "III", "IV", "V"]
RegimeProlabore = Literal[
    "presumido", "lucro_real", "simples_iv",
    "simples_i", "simples_ii", "simples_iii", "simples_v", "simples_i_iii_v",
]


class SimplesDASRequest(BaseModel):
    anexo: Anexo
    rbt12: float = Field(..., gt=0, description="Receita bruta dos últimos 12 meses (R$)")
    receita_mes: float = Field(..., ge=0, description="Receita do mês de apuração (R$)")
    folha12: float = Field(0.0, ge=0, description="Folha 12 meses incl. pró-labore + encargos")


# ─── Pró-labore ───────────────────────────────────────────────────


class ProlaboreRequest(BaseModel):
    valor_bruto: float = Field(..., ge=0)
    regime: RegimeProlabore = "presumido"
    num_dependentes: int = Field(0, ge=0)
    pensao_alimenticia: float = Field(0.0, ge=0)


# ─── Comparativo de regimes ───────────────────────────────────────


class ComparativoRegimesRequest(BaseModel):
    receita_anual: float = Field(..., gt=0)
    atividade_presumido: str = Field(
        ...,
        description="ex: 'servicos', 'comercio', 'industria', 'transporte'",
    )
    anexo_simples: Anexo
    margem_lucro_pct: float = Field(20.0, ge=0, le=100)
    folha_anual: float = Field(0.0, ge=0)
    creditos_pis_cofins_pct: float = Field(0.0, ge=0, le=100)
    receitas_financeiras_anual: float = Field(0.0, ge=0)
    num_empregados: int = Field(0, ge=0)
    salario_medio: float = Field(0.0, ge=0)
    rat_pct: float = Field(2.0, ge=0)
    fap: float = Field(1.0, ge=0)
    prolabore_mensal: float = Field(0.0, ge=0)
    num_socios: int = Field(1, ge=1)
    lucro_mensal_distribuicao: float = Field(0.0, ge=0)
