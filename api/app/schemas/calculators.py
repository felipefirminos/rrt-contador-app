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


class SugerirAnexoRequest(BaseModel):
    cnae: Optional[str] = Field(
        None,
        description="CNAE com ou sem máscara, ex: '71.12-0-00' ou '7112000'",
    )
    executa_obras: bool = Field(
        False,
        description="A empresa executa fisicamente obras/serviços de campo? (não é só projetar)",
    )
    cessao_mao_obra: bool = Field(
        False,
        description="Há cessão de mão de obra (pessoal subordinado ao tomador)?",
    )


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


# ─── IRPF Integrado (Pessoa Física) ──────────────────────────────

TipoDeducao = Literal["saude", "educacao", "previdencia_privada", "pensao_alimenticia",
                       "dependentes", "livro_caixa"]
TipoGCap = Literal["imovel", "veiculo"]
Moeda = Literal["USD", "EUR", "GBP"]


class DeducaoIRPF(BaseModel):
    tipo: TipoDeducao
    valor: float = Field(..., ge=0)
    documentos: list[str] = Field(default_factory=list)


class RendimentoExterior(BaseModel):
    valor: float = Field(..., ge=0, description="Valor em moeda estrangeira")
    moeda: Moeda
    mes: int = Field(..., ge=1, le=12)


class GanhoCapitalIRPF(BaseModel):
    tipo: TipoGCap
    valor_venda: float = Field(..., gt=0)
    custo_aquisicao: float = Field(..., ge=0)
    data_aquisicao: Optional[str] = Field(None, description="YYYY-MM-DD")
    data_venda: Optional[str] = Field(None, description="YYYY-MM-DD")
    finalidade_unico_imovel: Optional[bool] = Field(
        None, description="Imóvel único < R$440K isento (Art. 23 Lei 9.250/95)",
    )


class IRPFRequest(BaseModel):
    salarios_mensais: list[float] = Field(
        default_factory=list,
        description="12 valores mensais (R$). Lista vazia = sem renda CLT.",
    )
    num_dependentes: int = Field(0, ge=0, le=20)
    pensao_alimenticia_mensal: float = Field(0.0, ge=0)
    deducoes_anuais: list[DeducaoIRPF] = Field(default_factory=list)
    rendimentos_exterior: list[RendimentoExterior] = Field(default_factory=list)
    ganhos_capital: list[GanhoCapitalIRPF] = Field(default_factory=list)
    irrf_ja_retido_anual: float = Field(
        0.0, ge=0,
        description="IRRF retido por outros fontes (auto, 3º) já recolhido",
    )


# ─── CBS / IBS — Reforma Tributária ──────────────────────────────

RegimeReforma = Literal["simples", "lucro_presumido", "lucro_real"]
TipoOperacao = Literal["mercadoria", "servico", "misto"]
SetorEspecifico = Literal["combustiveis", "financeiro", "imobiliario", "saude", "educacao"]


class CBSIBSRequest(BaseModel):
    valor_operacao: float = Field(..., gt=0)
    ano: int = Field(..., ge=2026, le=2099, description="Ano da operação (2026-2033 transição)")
    regime: RegimeReforma = "lucro_presumido"
    aliquota_icms: float = Field(0.0, ge=0, le=30, description="ICMS atual (% da operação)")
    aliquota_iss: float = Field(0.0, ge=0, le=10, description="ISS atual (% — máximo 5% LC 116)")
    tipo_operacao: TipoOperacao = "mercadoria"
    setor_especifico: Optional[SetorEspecifico] = None


class CBSIBSProjecaoRequest(BaseModel):
    valor_operacao: float = Field(..., gt=0)
    regime: RegimeReforma = "lucro_presumido"
    aliquota_icms: float = Field(0.0, ge=0, le=30)
    aliquota_iss: float = Field(0.0, ge=0, le=10)


# ─── Trabalhista — 13º, Férias, Hora Extra (Fluxo 3 SKILL.md) ────


class DecimoTerceiroRequest(BaseModel):
    salario_bruto: float = Field(..., gt=0)
    meses_trabalhados: int = Field(12, ge=1, le=12, description="Avos (proporcional)")
    num_dependentes: int = Field(0, ge=0)
    pensao_alimenticia: float = Field(0.0, ge=0)


class FeriasRequest(BaseModel):
    salario: float = Field(..., gt=0)
    dias_ferias: int = Field(
        30, ge=0, le=30,
        description="Dias gozados (mínimo 20 se há abono pecuniário, CLT 143)",
    )
    dias_abono: int = Field(
        0, ge=0, le=10,
        description="Abono pecuniário — 'venda' de até 10 dias (CLT 143)",
    )
    num_dependentes: int = Field(0, ge=0)
    media_adicionais: float = Field(0.0, ge=0)


class HoraExtraRequest(BaseModel):
    salario: float = Field(..., gt=0)
    horas_normais: float = Field(..., ge=0, description="HE em dias normais")
    horas_feriado: float = Field(0.0, ge=0, description="HE em domingos/feriados")
    adicional_normal: float = Field(50.0, ge=50, description="% mínimo legal 50% (CLT 59)")
    adicional_feriado: float = Field(100.0, ge=100, description="% mínimo legal 100% (CLT 70)")
    jornada_mensal: int = Field(220, gt=0, description="220h = 44h/sem; 180h = 36h/sem")
    comissoes: float = Field(0.0, ge=0)
    # Para cálculo do DSR opcional
    dias_uteis: Optional[int] = Field(None, ge=0, le=31, description="Para DSR")
    domingos_feriados: Optional[int] = Field(None, ge=0, le=15, description="Para DSR")


# ─── MEI (LC 188/2021) ────────────────────────────────────────────

AtividadeMEI = Literal["comercio", "servicos", "comercio_servicos", "caminhoneiro"]


class MEIResumoRequest(BaseModel):
    atividade: AtividadeMEI = Field(
        "comercio",
        description=(
            "'caminhoneiro' aplica LC 188/2021: INSS 12% SM, limite anual R$251,6K"
        ),
    )
    receita_bruta_anual: float = Field(0.0, ge=0)
    meses_atividade: int = Field(12, ge=1, le=12,
                                  description="Proporcionaliza limite se < 12")


# ─── DARF / GPS / DAS — códigos de receita ───────────────────────

RegimeDarf = Literal["simples", "presumido", "lucro_real", "mei", "dp"]


class DarfBuscaRequest(BaseModel):
    texto: str = Field(..., min_length=2, description="Tributo, descrição ou código")


class DarfRegimeRequest(BaseModel):
    regime: RegimeDarf


# ─── Recuperação Tributária (Tema 69 + prescrição) ────────────────

RegimeTema69 = Literal["LUCRO_REAL", "LUCRO_PRESUMIDO"]


class OperacaoTema69(BaseModel):
    competencia: str = Field(..., description="YYYY-MM-DD ou YYYY-MM (1º dia)")
    receita_bruta: float = Field(..., gt=0)
    icms_destacado: float = Field(..., ge=0)
    regime: RegimeTema69


class Tema69Request(BaseModel):
    operacoes: list[OperacaoTema69] = Field(..., min_length=1)
    tem_acao_pre_15_03_2017: bool = Field(
        False,
        description="Se a empresa tinha ação ajuizada antes de 15/03/2017 (libera modulação)",
    )


class PrescricaoRequest(BaseModel):
    data_pagamento: str = Field(..., description="YYYY-MM-DD")
    data_referencia: Optional[str] = Field(
        None, description="Data do protocolo (default: hoje)",
    )


# ─── DIFAL ICMS (EC 87/2015) + ICMS-ST + ISS ─────────────────────


class DIFALRequest(BaseModel):
    valor_operacao: float = Field(..., gt=0)
    aliquota_destino: float = Field(..., ge=0, le=30,
                                     description="Alíquota interna do estado de destino (%)")
    aliquota_interestadual: float = Field(..., ge=0, le=30,
                                           description="Alíquota interestadual (4/7/12%)")
    frete: float = Field(0.0, ge=0)
    seguro: float = Field(0.0, ge=0)
    outras_despesas: float = Field(0.0, ge=0)


class ICMSSTRequest(BaseModel):
    valor_operacao: float = Field(..., gt=0)
    mva: float = Field(..., ge=0, le=300, description="Margem de Valor Agregado (%)")
    aliquota_interna: float = Field(..., ge=0, le=30,
                                     description="Alíquota interna do estado de DESTINO (%)")
    aliquota_origem: float = Field(..., ge=0, le=30,
                                    description="Alíquota interna do estado de ORIGEM (%)")
    frete: float = Field(0.0, ge=0)
    seguro: float = Field(0.0, ge=0)
    outras_despesas: float = Field(0.0, ge=0)


class ISSRequest(BaseModel):
    valor_servico: float = Field(..., ge=0)
    municipio: str = Field(..., min_length=2,
                            description="ex: 'São Paulo-SP', 'Campinas-SP'")
    item_lc116: Optional[int] = Field(
        None, ge=1, le=40,
        description="Item da LC 116/2003 (1=TI, 7=eng, 8=educ, 14=saúde, 17=consultoria)",
    )
    simples_nacional: bool = Field(
        False,
        description="Se True, alerta que ISS pode estar incluído no DAS",
    )


class MunicipioBuscaRequest(BaseModel):
    texto: str = Field(..., min_length=2)


# ─── Tema 779 STJ + PER/DCOMP Minuta ──────────────────────────────

CategoriaInsumo = Literal[
    "MATERIA_PRIMA_DIRETA",
    "EMBALAGEM_PRIMARIA",
    "ENERGIA_ELETRICA_PRODUTIVA",
    "COMBUSTIVEL_MAQUINA_PRODUTIVA",
    "EPI_OBRIGATORIO_NR",
    "SERVICOS_MANUTENCAO_MAQUINARIO",
    "FRETE_INTERNO_ENTRE_ESTABELECIMENTOS",
    "PRODUTOS_LIMPEZA_AREA_PRODUTIVA",
    "ANALISES_LABORATORIAIS_QUALIDADE",
    "MATERIAL_ESCRITORIO",
    "DESPESAS_ADMINISTRATIVAS",
    "MARKETING_PUBLICIDADE",
    "ALIMENTACAO_FUNCIONARIOS",
    "MAO_DE_OBRA_PF",
    "TRIBUTOS_RECUPERAVEIS",
]


class InsumoTema779(BaseModel):
    descricao: str = Field(..., min_length=2)
    categoria: CategoriaInsumo
    valor_total_competencia: float = Field(..., gt=0)
    competencia: str = Field(..., description="MM/AAAA")
    justificativa_tecnica: str = ""
    tem_laudo_tecnico: bool = False


class Tema779Request(BaseModel):
    insumos: list[InsumoTema779] = Field(..., min_length=1)


class LucroPresumidoRequest(BaseModel):
    atividade: Literal[
        "comercio", "industria", "servicos", "transporte_cargas",
        "transporte_passageiros", "combustiveis", "servicos_hospitalares",
        "construcao_civil",
    ] = Field(..., description="Chave da atividade na tabela do Lucro Presumido")
    receita_trimestre: float = Field(..., gt=0, description="Receita bruta trimestral (R$)")
    receitas_financeiras: float = Field(0.0, ge=0)
    outras_receitas: float = Field(0.0, ge=0)


PeriodoLR = Literal["trimestral", "mensal"]


class LucroRealRequest(BaseModel):
    lucro_contabil: float = Field(..., description="Pode ser negativo (prejuízo contábil)")
    adicoes: float = Field(0.0, ge=0, description="Total de adições ao LALUR")
    exclusoes: float = Field(0.0, ge=0, description="Total de exclusões do LALUR")
    prejuizo_fiscal_acumulado: float = Field(
        0.0, ge=0,
        description="Saldo de prejuízo fiscal de períodos anteriores (compensação limitada a 30%)",
    )
    base_negativa_csll_acumulada: float = Field(0.0, ge=0)
    receita_bruta: float = Field(0.0, ge=0, description="Para PIS/COFINS não-cumulativo")
    receitas_financeiras: float = Field(0.0, ge=0)
    outras_receitas: float = Field(0.0, ge=0)
    creditos_pis: float = Field(0.0, ge=0)
    creditos_cofins: float = Field(0.0, ge=0)
    periodo: PeriodoLR = "trimestral"
    csll_adicoes: Optional[float] = Field(None, ge=0,
        description="Adições específicas CSLL (default = adicoes do IRPJ)")
    csll_exclusoes: Optional[float] = Field(None, ge=0)


class PerDcompMinutaRequest(BaseModel):
    """Gera memória de cálculo PER/DCOMP a partir do template RRT."""
    cliente_razao_social: str = Field(..., min_length=2)
    cliente_cnpj: str = Field(..., min_length=14)
    regime_tributario: Literal["LUCRO_REAL", "LUCRO_PRESUMIDO"]
    tese: str = Field(
        "Tema 69 STF — Exclusão do ICMS da base de PIS/COFINS",
        description="Identificação da tese invocada",
    )
    leading_case: str = Field("RE 574.706/PR")
    competencia_inicial: str = Field(..., description="MM/AAAA")
    competencia_final: str = Field(..., description="MM/AAAA")
    num_competencias: int = Field(..., gt=0)
    total_principal: float = Field(..., ge=0, description="Total recuperável (R$)")
    total_atualizado: Optional[float] = Field(
        None, description="Total atualizado pela SELIC, opcional",
    )
    contador_nome: str = Field(..., min_length=2)
    contador_crc: str = Field(...)
    advogado_nome: Optional[str] = Field(None, min_length=2)
    advogado_oab: Optional[str] = None
    forma_recuperacao: Literal["DCOMP", "PER", "RESSARCIMENTO"] = "DCOMP"
    ultimo_dia_pleito: Optional[str] = Field(None, description="DD/MM/AAAA")
    sem_prescricao: bool = Field(True, description="Confirmar prescrição verificada")
