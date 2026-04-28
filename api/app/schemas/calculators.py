from __future__ import annotations

from typing import Literal, Optional
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


# ─── Rescisão ─────────────────────────────────────────────────────

TipoRescisao = Literal["sem_justa_causa", "pedido_demissao", "justa_causa", "acordo_mutuo"]
AvisoPrevio = Literal["indenizado", "trabalhado", "dispensado"]


class RescisaoRequest(BaseModel):
    tipo: TipoRescisao
    salario: float = Field(..., gt=0, description="Último salário mensal (R$)")
    anos_servico: int = Field(0, ge=0, description="Anos completos (Lei 12.506: +3 dias/ano, max 90)")
    aviso_previo: AvisoPrevio = "indenizado"
    dias_trabalhados_mes: Optional[int] = Field(None, ge=0, le=31)
    meses_13_proporcional: Optional[int] = Field(
        None, ge=0, le=12,
        description="Avos de 13°. Se None, usa 6 (default da função).",
    )
    meses_ferias_proporcional: Optional[int] = Field(None, ge=0, le=12)
    tem_ferias_vencidas: bool = False
    periodos_ferias_vencidas: int = Field(1, ge=0, le=2, description="2 = férias dobradas")
    saldo_fgts: float = Field(0.0, ge=0, description="Saldo FGTS para multa")
    num_dependentes: int = Field(0, ge=0)
    media_adicionais: float = Field(0.0, ge=0, description="Média HE/noturno/insalubridade")


# ─── Folha em Lote ────────────────────────────────────────────────

RegimeFolha = Literal["presumido_real", "simples_i_iii_v", "simples_iv"]


class EmpregadoFolha(BaseModel):
    nome: str
    salario_base: float = Field(..., ge=0)
    he_normais: float = Field(0.0, ge=0, description="Horas extras 50%")
    he_feriado: float = Field(0.0, ge=0, description="Horas extras 100% (domingo/feriado)")
    horas_noturnas: float = Field(0.0, ge=0)
    adicional_noturno_pct: float = Field(0.0, ge=0, description="20% mínimo legal")
    insalubridade_pct: Literal[0, 10, 20, 40] = Field(
        0, description="CLT Art. 192: 10/20/40% sobre SM",
    )
    periculosidade_pct: float = Field(0.0, ge=0, le=30, description="30% sobre base (CLT 193)")
    adicional_funcao: float = Field(0.0, ge=0)
    comissoes: float = Field(0.0, ge=0)
    faltas_dias: int = Field(0, ge=0, le=31)
    num_dependentes: int = Field(0, ge=0)
    pensao_alimenticia: float = Field(0.0, ge=0)
    vt_base: float = Field(0.0, ge=0, description="Custo VT do mês (desconto 6% do salário)")
    outros_descontos: float = Field(0.0, ge=0)
    jornada_mensal: int = Field(220, gt=0, description="220h = 44h/sem; 180h = 36h/sem")


class FolhaBatchRequest(BaseModel):
    empregados: list[EmpregadoFolha] = Field(..., min_length=1)
    regime: RegimeFolha = "presumido_real"
    competencia: Optional[str] = Field(None, description="Ex: '04/2026' (informativo)")
    rat_pct: float = Field(2.0, ge=0)
    fap: float = Field(1.0, ge=0)


# ─── Distribuição de Lucros (Lei 15.270/2025) ────────────────────

RegimeDistribuicao = Literal["simples", "presumido", "lucro_real"]


class DistribuicaoLucrosRequest(BaseModel):
    valor_mensal: float = Field(..., ge=0, description="Valor TOTAL distribuído no mês (R$)")
    lucro_apurado_disponivel: Optional[float] = Field(
        None, ge=0,
        description="Lucro contábil disponível. Se informado, limita a distribuição.",
    )
    distribuicao_por_socio: Optional[list[float]] = Field(
        None, description="Para distribuição desigual; soma deve = valor_mensal",
    )
    tem_escrituracao_regular: bool = Field(
        True, description="Se False, alerta CRÍTICO de reclassificação como pró-labore",
    )
    lucro_aprovado_ate_2025: bool = Field(
        False,
        description=(
            "Lucros aprovados até 31/12/2025 + pagos até 31/12/2028 mantêm "
            "ISENÇÃO TOTAL (regra de transição Lei 15.270/2025)"
        ),
    )
    regime_tributario: Optional[RegimeDistribuicao] = Field(
        None,
        description=(
            "'simples' adiciona alerta da controvérsia LC 123 art. 14 × "
            "Lei 15.270/2025 (CF art. 146 III 'd')"
        ),
    )
