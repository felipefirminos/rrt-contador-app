"""Bridge between FastAPI and the RRT calc engine.

The engine lives at `<repo>/engine/scripts/` as plain Python modules with pure
functions. We add that directory to sys.path once, then expose typed wrappers
that map directly to the underlying calc functions. Adding a new calculator
to the API is two steps:

1. import the calc function here
2. add a Pydantic schema + a router endpoint (see app/routers/calculators.py)
"""

from __future__ import annotations

import sys
from typing import Any

from app.config import SCRIPTS_DIR


if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


from calc_simples import calcular_das as _calc_das  # noqa: E402
from calc_simples import sugerir_anexo_engenharia as _sugerir_anexo  # noqa: E402
from calc_prolabore import calcular_prolabore as _calc_prolabore  # noqa: E402
from calc_comparativo_regimes import comparar_regimes as _comparar_regimes  # noqa: E402
from calc_rescisao import calcular_rescisao as _calc_rescisao  # noqa: E402
from calc_folha_batch import processar_folha_batch as _processar_folha_batch  # noqa: E402


def calc_simples_das(
    anexo: str,
    rbt12: float,
    receita_mes: float,
    folha12: float = 0.0,
) -> dict[str, Any]:
    return _calc_das(anexo, rbt12, receita_mes, folha12=folha12)


def sugerir_anexo_engenharia(
    cnae: str | None = None,
    executa_obras: bool = False,
    cessao_mao_obra: bool = False,
) -> dict[str, Any]:
    return _sugerir_anexo(
        cnae=cnae,
        executa_obras=executa_obras,
        cessao_mao_obra=cessao_mao_obra,
    )


def calc_prolabore(
    valor_bruto: float,
    regime: str = "presumido",
    num_dependentes: int = 0,
    pensao_alimenticia: float = 0.0,
) -> dict[str, Any]:
    return _calc_prolabore(
        valor_bruto=valor_bruto,
        regime=regime,
        num_dependentes=num_dependentes,
        pensao_alimenticia=pensao_alimenticia,
    )


def calc_rescisao(
    tipo: str,
    salario: float,
    anos_servico: int = 0,
    aviso_previo: str = "indenizado",
    dias_trabalhados_mes: int | None = None,
    meses_13_proporcional: int | None = None,
    meses_ferias_proporcional: int | None = None,
    tem_ferias_vencidas: bool = False,
    periodos_ferias_vencidas: int = 1,
    saldo_fgts: float = 0.0,
    num_dependentes: int = 0,
    media_adicionais: float = 0.0,
) -> dict[str, Any]:
    return _calc_rescisao(
        tipo=tipo,
        salario=salario,
        anos_servico=anos_servico,
        aviso_previo=aviso_previo,
        dias_trabalhados_mes=dias_trabalhados_mes,
        meses_13_proporcional=meses_13_proporcional,
        meses_ferias_proporcional=meses_ferias_proporcional,
        tem_ferias_vencidas=tem_ferias_vencidas,
        periodos_ferias_vencidas=periodos_ferias_vencidas,
        saldo_fgts=saldo_fgts,
        num_dependentes=num_dependentes,
        media_adicionais=media_adicionais,
    )


def calc_folha_batch(
    empregados: list[dict[str, Any]],
    regime: str = "presumido_real",
    competencia: str | None = None,
) -> dict[str, Any]:
    return _processar_folha_batch(
        empregados=empregados,
        regime=regime,
        competencia=competencia,
    )


def calc_comparativo(
    receita_anual: float,
    atividade_presumido: str,
    anexo_simples: str,
    margem_lucro_pct: float = 20.0,
    folha_anual: float = 0.0,
    creditos_pis_cofins_pct: float = 0.0,
    receitas_financeiras_anual: float = 0.0,
    num_empregados: int = 0,
    salario_medio: float = 0.0,
    rat_pct: float = 2.0,
    fap: float = 1.0,
    prolabore_mensal: float = 0.0,
    num_socios: int = 1,
    lucro_mensal_distribuicao: float = 0.0,
) -> dict[str, Any]:
    return _comparar_regimes(
        receita_anual=receita_anual,
        atividade_presumido=atividade_presumido,
        anexo_simples=anexo_simples,
        margem_lucro_pct=margem_lucro_pct,
        folha_anual=folha_anual,
        creditos_pis_cofins_pct=creditos_pis_cofins_pct,
        receitas_financeiras_anual=receitas_financeiras_anual,
        num_empregados=num_empregados,
        salario_medio=salario_medio,
        rat_pct=rat_pct,
        fap=fap,
        prolabore_mensal=prolabore_mensal,
        num_socios=num_socios,
        lucro_mensal_distribuicao=lucro_mensal_distribuicao,
    )


CALCULATOR_TOOLS = [
    {
        "name": "calc_simples_das",
        "description": (
            "Calcula o DAS mensal do Simples Nacional (LC 123/2006). "
            "Anexo I (comércio), II (indústria), III (serviços com Fator R), "
            "IV (construção/limpeza/vigilância — CPP separada), V (serviços sem Fator R)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "anexo": {"type": "string", "enum": ["I", "II", "III", "IV", "V"]},
                "rbt12": {"type": "number", "description": "Receita bruta dos últimos 12 meses (R$)"},
                "receita_mes": {"type": "number", "description": "Receita do mês de apuração (R$)"},
                "folha12": {"type": "number", "description": "Folha 12 meses incl. pró-labore + encargos (Fator R)", "default": 0},
            },
            "required": ["anexo", "rbt12", "receita_mes"],
        },
    },
    {
        "name": "calc_prolabore",
        "description": (
            "Calcula INSS sócio (11% até teto), CPP patronal (20% se regime aplicável), "
            "IRRF (Lei 15.270/2025) e custo total empresa para um pró-labore mensal."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "valor_bruto": {"type": "number"},
                "regime": {
                    "type": "string",
                    "enum": [
                        "presumido", "lucro_real", "simples_iv",
                        "simples_i", "simples_ii", "simples_iii", "simples_v",
                        "simples_i_iii_v",
                    ],
                },
                "num_dependentes": {"type": "integer", "default": 0},
                "pensao_alimenticia": {"type": "number", "default": 0},
            },
            "required": ["valor_bruto", "regime"],
        },
    },
    {
        "name": "calc_comparativo",
        "description": (
            "Compara carga tributária anual entre Simples Nacional, Lucro Presumido e "
            "Lucro Real, incluindo custo de sócios (pró-labore + distribuição de lucros)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "receita_anual": {"type": "number"},
                "atividade_presumido": {"type": "string", "description": "ex: 'servicos', 'comercio', 'industria'"},
                "anexo_simples": {"type": "string", "enum": ["I", "II", "III", "IV", "V"]},
                "margem_lucro_pct": {"type": "number", "default": 20.0},
                "folha_anual": {"type": "number", "default": 0},
                "creditos_pis_cofins_pct": {"type": "number", "default": 0},
                "num_empregados": {"type": "integer", "default": 0},
                "salario_medio": {"type": "number", "default": 0},
                "prolabore_mensal": {"type": "number", "default": 0},
                "num_socios": {"type": "integer", "default": 1},
                "lucro_mensal_distribuicao": {"type": "number", "default": 0},
            },
            "required": ["receita_anual", "atividade_presumido", "anexo_simples"],
        },
    },
    {
        "name": "calc_folha_batch",
        "description": (
            "Processa folha de pagamento de N empregados de uma vez (CLT + Lei 8.212 + 8.036). "
            "Retorna resultado individual por empregado, totais consolidados (bruto, líquido, "
            "INSS empregado/patronal, IRRF, FGTS, custo empresa) e guias prontas: "
            "GPS (vence dia 20), FGTS Digital (vence dia 7), DARF 0561 (IRRF, vence dia 20). "
            "Trata erros individualmente — um empregado com erro não interrompe o lote."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "empregados": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nome": {"type": "string"},
                            "salario_base": {"type": "number"},
                            "he_normais": {"type": "number", "default": 0},
                            "he_feriado": {"type": "number", "default": 0},
                            "horas_noturnas": {"type": "number", "default": 0},
                            "adicional_noturno_pct": {"type": "number", "default": 0},
                            "insalubridade_pct": {"type": "number", "enum": [0, 10, 20, 40]},
                            "periculosidade_pct": {"type": "number", "default": 0},
                            "faltas_dias": {"type": "integer", "default": 0},
                            "num_dependentes": {"type": "integer", "default": 0},
                            "pensao_alimenticia": {"type": "number", "default": 0},
                            "vt_base": {"type": "number", "default": 0},
                            "outros_descontos": {"type": "number", "default": 0},
                            "jornada_mensal": {"type": "integer", "default": 220},
                        },
                        "required": ["nome", "salario_base"],
                    },
                },
                "regime": {
                    "type": "string",
                    "enum": ["presumido_real", "simples_i_iii_v", "simples_iv"],
                    "default": "presumido_real",
                },
                "competencia": {"type": "string", "description": "ex: '04/2026'"},
            },
            "required": ["empregados"],
        },
    },
    {
        "name": "calc_rescisao",
        "description": (
            "Calcula rescisão trabalhista (CLT Arts. 477-484-A, Lei 12.506/2011). "
            "4 tipos: sem_justa_causa (FGTS+40%, seguro-desemprego), pedido_demissao "
            "(sem multa, sem FGTS), justa_causa (apenas férias vencidas), acordo_mutuo "
            "(484-A: aviso 50%, FGTS multa 20%, saque 80%, sem seguro-desemprego). "
            "Aplica regras de incidência: férias indenizadas+1/3 e aviso indenizado "
            "são ISENTOS de INSS/IRRF; 13° tem cálculo separado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {
                    "type": "string",
                    "enum": ["sem_justa_causa", "pedido_demissao", "justa_causa", "acordo_mutuo"],
                },
                "salario": {"type": "number", "description": "Último salário mensal (R$)"},
                "anos_servico": {"type": "integer", "default": 0},
                "aviso_previo": {
                    "type": "string",
                    "enum": ["indenizado", "trabalhado", "dispensado"],
                    "default": "indenizado",
                },
                "meses_13_proporcional": {"type": "integer", "description": "Avos de 13°"},
                "meses_ferias_proporcional": {"type": "integer"},
                "tem_ferias_vencidas": {"type": "boolean", "default": False},
                "periodos_ferias_vencidas": {"type": "integer", "default": 1},
                "saldo_fgts": {"type": "number", "default": 0},
                "num_dependentes": {"type": "integer", "default": 0},
                "media_adicionais": {"type": "number", "default": 0},
            },
            "required": ["tipo", "salario"],
        },
    },
]


TOOL_DISPATCH = {
    "calc_simples_das": calc_simples_das,
    "calc_prolabore": calc_prolabore,
    "calc_comparativo": calc_comparativo,
    "calc_rescisao": calc_rescisao,
    "calc_folha_batch": calc_folha_batch,
}
