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

# Recuperação tributária (Tema 69, Tema 779, prescrição) — módulos separados
from app.config import ENGINE_DIR  # noqa: E402

REC_TRIB_DIR = ENGINE_DIR / "recuperacao_tributaria" / "scripts"
if REC_TRIB_DIR.exists() and str(REC_TRIB_DIR) not in sys.path:
    sys.path.insert(0, str(REC_TRIB_DIR))


from calc_simples import calcular_das as _calc_das  # noqa: E402
from calc_simples import sugerir_anexo_engenharia as _sugerir_anexo  # noqa: E402
from calc_prolabore import calcular_prolabore as _calc_prolabore  # noqa: E402
from calc_comparativo_regimes import comparar_regimes as _comparar_regimes  # noqa: E402
from calc_rescisao import calcular_rescisao as _calc_rescisao  # noqa: E402
from calc_folha_batch import processar_folha_batch as _processar_folha_batch  # noqa: E402
from calc_distribuicao_lucros import calcular_distribuicao as _calc_distribuicao  # noqa: E402
from calc_irpf_integrado import calcular_irpf_integrado as _calc_irpf  # noqa: E402
from calc_cbs_ibs import calcular_cbs_ibs as _calc_cbs_ibs  # noqa: E402
from calc_cbs_ibs import projecao_transicao as _proj_transicao  # noqa: E402
from calc_13o import calcular_13o as _calc_13o  # noqa: E402
from calc_ferias import calcular_ferias as _calc_ferias  # noqa: E402
from calc_hora_extra import calcular_hora_extra as _calc_he  # noqa: E402
from calc_hora_extra import calcular_dsr as _calc_dsr  # noqa: E402
from calc_mei import resumo_mei as _resumo_mei  # noqa: E402
from calc_darf_codes import consultar_darf as _consultar_darf  # noqa: E402
from calc_darf_codes import listar_por_regime as _darf_regime  # noqa: E402
from calc_darf_codes import buscar as _darf_buscar  # noqa: E402
from calc_difal import calcular_difal as _calc_difal  # noqa: E402
from calc_icms_st import calcular_icms_st as _calc_icms_st  # noqa: E402
from calc_iss import calcular_iss as _calc_iss  # noqa: E402
from calc_iss import buscar_municipio as _buscar_municipio  # noqa: E402
from calc_iss import consultar_municipio as _consultar_municipio  # noqa: E402
from calc_presumido import calcular_presumido as _calc_presumido  # noqa: E402
from calc_lucro_real import calcular_lucro_real as _calc_lucro_real  # noqa: E402
from calc_custo_empregado import calcular_custo_empregado as _calc_custo_emp  # noqa: E402
from calc_retencoes_pj import calcular_retencoes_pj as _calc_retencoes  # noqa: E402
from calc_gcap_imovel import calcular_gcap_imovel as _calc_gcap_imovel  # noqa: E402
from calc_gcap_veiculo import calcular_gcap_veiculo as _calc_gcap_veiculo  # noqa: E402
from calc_gcap_crypto import gerar_checklist_crypto as _gcap_crypto_checklist  # noqa: E402
from calc_gcap_etf_exterior import gerar_checklist_etf_exterior as _gcap_etf_checklist  # noqa: E402
from calc_carne_leao import calcular_carne_leao as _calc_carne_leao  # noqa: E402
from gerar_dossie_irpf import gerar_dossie as _gerar_dossie_irpf  # noqa: E402
from validar_consistencia_irpf import validar_dossie as _validar_dossie_irpf  # noqa: E402
from detector_padroes import (  # noqa: E402
    detectar_sazonalidade as _det_sazonalidade,
    detectar_padroes_cliente as _det_padroes_cliente,
    detectar_padroes_correcao as _det_padroes_correcao,
    detectar_clusters as _det_clusters,
    gerar_insights as _det_gerar_insights,
)
from sugestoes_proativas import (  # noqa: E402
    gerar_alertas_prazo as _sug_alertas_prazo,
    gerar_lembretes_recorrentes as _sug_lembretes,
    gerar_validacoes_reforcadas as _sug_validacoes,
    gerar_antecipacoes as _sug_antecipacoes,
    gerar_sugestoes_consolidadas as _sug_consolidadas,
)

# Recuperação tributária — só importa se a pasta existe
try:
    from calcular_tema_69 import (  # noqa: E402
        OperacaoMensal as _OperacaoTema69,
        calcular_credito_mensal as _calc_tema_69_mensal,
        calcular_total as _calc_tema_69_total,
    )
    from verificar_prescricao import (  # noqa: E402
        verificar_prescricao as _verificar_prescricao,
        calcular_periodo_recuperavel as _periodo_recuperavel,
    )
    from calcular_tema_779 import (  # noqa: E402
        Insumo as _Insumo779,
        consolidar_analise as _consolidar_779,
    )
    REC_TRIB_DISPONIVEL = True
except ImportError:
    REC_TRIB_DISPONIVEL = False


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


def calc_irpf_integrado(
    salarios_mensais: list[float] | None = None,
    num_dependentes: int = 0,
    pensao_alimenticia_mensal: float = 0.0,
    deducoes_anuais: list[dict[str, Any]] | None = None,
    rendimentos_exterior: list[dict[str, Any]] | None = None,
    ganhos_capital: list[dict[str, Any]] | None = None,
    irrf_ja_retido_anual: float = 0.0,
) -> dict[str, Any]:
    return _calc_irpf(
        salarios_mensais=salarios_mensais or [],
        num_dependentes=num_dependentes,
        pensao_alimenticia_mensal=pensao_alimenticia_mensal,
        deducoes_anuais=deducoes_anuais or [],
        rendimentos_exterior=rendimentos_exterior or [],
        ganhos_capital=ganhos_capital or [],
        irrf_ja_retido_anual=irrf_ja_retido_anual,
    )


def calc_cbs_ibs(
    valor_operacao: float,
    ano: int,
    regime: str = "lucro_presumido",
    aliquota_icms: float = 0.0,
    aliquota_iss: float = 0.0,
    tipo_operacao: str = "mercadoria",
    setor_especifico: str | None = None,
) -> dict[str, Any]:
    return _calc_cbs_ibs(
        valor_operacao=valor_operacao, ano=ano, regime=regime,
        aliquota_icms=aliquota_icms, aliquota_iss=aliquota_iss,
        tipo_operacao=tipo_operacao, setor_especifico=setor_especifico,
    )


def projecao_cbs_ibs(
    valor_operacao: float,
    regime: str = "lucro_presumido",
    aliquota_icms: float = 0.0,
    aliquota_iss: float = 0.0,
) -> dict[str, Any]:
    return _proj_transicao(
        valor_operacao=valor_operacao, regime=regime,
        aliquota_icms=aliquota_icms, aliquota_iss=aliquota_iss,
    )


def calc_decimo_terceiro(
    salario_bruto: float,
    meses_trabalhados: int = 12,
    num_dependentes: int = 0,
    pensao_alimenticia: float = 0.0,
) -> dict[str, Any]:
    return _calc_13o(
        salario_bruto=salario_bruto,
        meses_trabalhados=meses_trabalhados,
        num_dependentes=num_dependentes,
        pensao_alimenticia=pensao_alimenticia,
    )


def calc_ferias(
    salario: float,
    dias_ferias: int = 30,
    dias_abono: int = 0,
    num_dependentes: int = 0,
    media_adicionais: float = 0.0,
) -> dict[str, Any]:
    return _calc_ferias(
        salario=salario,
        dias_ferias=dias_ferias,
        dias_abono=dias_abono,
        num_dependentes=num_dependentes,
        media_adicionais=media_adicionais,
    )


def calc_hora_extra(
    salario: float,
    horas_normais: float,
    horas_feriado: float = 0.0,
    adicional_normal: float = 50.0,
    adicional_feriado: float = 100.0,
    jornada_mensal: int = 220,
    comissoes: float = 0.0,
    dias_uteis: int | None = None,
    domingos_feriados: int | None = None,
) -> dict[str, Any]:
    result = _calc_he(
        salario=salario,
        horas_normais=horas_normais,
        horas_feriado=horas_feriado,
        adicional_normal=adicional_normal,
        adicional_feriado=adicional_feriado,
        jornada_mensal=jornada_mensal,
        comissoes=comissoes,
    )
    if dias_uteis is not None and domingos_feriados is not None:
        result["dsr"] = _calc_dsr(
            total_variaveis=result["total_variaveis"],
            dias_uteis=dias_uteis,
            domingos_feriados=domingos_feriados,
        )
        result["dias_uteis"] = dias_uteis
        result["domingos_feriados"] = domingos_feriados
        result["base_legal_dsr"] = "Lei 605/49 + Súmula 172 TST"
    return result


def resumo_mei(
    atividade: str = "comercio",
    receita_bruta_anual: float = 0.0,
    meses_atividade: int = 12,
) -> dict[str, Any]:
    return _resumo_mei(
        atividade=atividade,
        receita_bruta_anual=receita_bruta_anual,
        meses_atividade=meses_atividade,
    )


def calc_tema_779(insumos: list[dict[str, Any]]) -> dict[str, Any]:
    """STJ Tema 779 — insumo gerador de crédito de PIS/COFINS."""
    if not REC_TRIB_DISPONIVEL:
        return {"erro": "Módulo de recuperação tributária não disponível"}

    from decimal import Decimal as _Dec

    insumos_engine = []
    for it in insumos:
        insumos_engine.append(_Insumo779(
            descricao=it["descricao"],
            categoria=it["categoria"],
            valor_total_competencia=_Dec(str(it["valor_total_competencia"])),
            competencia=it["competencia"],
            justificativa_tecnica=it.get("justificativa_tecnica", ""),
            tem_laudo_tecnico=it.get("tem_laudo_tecnico", False),
        ))

    try:
        raw = _consolidar_779(insumos_engine)
    except ValueError as exc:
        return {"erro": str(exc)}

    def _ser(a):
        return {
            "descricao": a.insumo.descricao,
            "categoria": a.insumo.categoria,
            "valor_competencia": float(a.insumo.valor_total_competencia),
            "competencia": a.insumo.competencia,
            "tem_laudo_tecnico": a.insumo.tem_laudo_tecnico,
            "forca_tese": a.forca_tese,
            "credito_pis": float(a.credito_pis),
            "credito_cofins": float(a.credito_cofins),
            "credito_total": float(a.credito_total),
            "recomendacao": a.recomendacao,
            "riscos": a.riscos,
        }

    return {
        "analises": [_ser(a) for a in raw["analises"]],
        "credito_alta_confianca": float(raw["credito_alta_confianca"]),
        "credito_media_confianca": float(raw["credito_media_confianca"]),
        "credito_baixa_confianca": float(raw["credito_baixa_confianca"]),
        "credito_total_bruto": float(raw["credito_total_bruto"]),
        "aliquota_pis_pct": 1.65,
        "aliquota_cofins_pct": 7.6,
        "aliquota_total_pct": 9.25,
        "aviso_selic": (
            "⚠️ Valor é PRINCIPAL apenas. Aplicar SELIC e consultar advogado "
            "tributarista (cláusula CRC + OAB) antes do PER/DCOMP."
        ),
        "base_legal": (
            "STJ Tema 779 — REsp 1.221.170/PR (recursos repetitivos, conceito "
            "amplo de insumo: essencialidade + relevância)"
        ),
    }


def gerar_minuta_perdcomp(
    cliente_razao_social: str,
    cliente_cnpj: str,
    regime_tributario: str,
    tese: str,
    leading_case: str,
    competencia_inicial: str,
    competencia_final: str,
    num_competencias: int,
    total_principal: float,
    contador_nome: str,
    contador_crc: str,
    total_atualizado: float | None = None,
    advogado_nome: str | None = None,
    advogado_oab: str | None = None,
    forma_recuperacao: str = "DCOMP",
    ultimo_dia_pleito: str | None = None,
    sem_prescricao: bool = True,
) -> dict[str, Any]:
    """Gera minuta da memória de cálculo PER/DCOMP a partir do template RRT.

    Lê o template em engine/recuperacao_tributaria/templates/template_perdcomp.md
    e substitui os placeholders pelas informações fornecidas.
    """
    template_path = ENGINE_DIR / "recuperacao_tributaria" / "templates" / "template_perdcomp.md"
    if not template_path.exists():
        return {"erro": f"Template não encontrado: {template_path}"}

    template = template_path.read_text(encoding="utf-8")

    from datetime import date as _date
    hoje = _date.today().strftime("%d/%m/%Y")

    # Aliquotas conforme regime
    if regime_tributario == "LUCRO_REAL":
        aliq_pis, aliq_cofins, aliq_total = "1,65%", "7,6%", "9,25%"
    else:
        aliq_pis, aliq_cofins, aliq_total = "0,65%", "3%", "3,65%"

    # Mapa de substituições (placeholder → valor)
    formato_brl = lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    sub = {
        "<RAZÃO SOCIAL>": cliente_razao_social,
        "<00.000.000/0001-00>": cliente_cnpj,
        "<LUCRO_REAL / LUCRO_PRESUMIDO>": regime_tributario,
        "<ex.: Tema 69 STF — Exclusão do ICMS da base de PIS/COFINS>": tese,
        "<ex.: RE 574.706/PR>": leading_case,
        "<DD/MM/AAAA>": hoje,
        "<Nome CRC>": f"{contador_nome} (CRC {contador_crc})",
        "<Nome OAB>": (
            f"{advogado_nome} (OAB {advogado_oab})" if advogado_nome and advogado_oab
            else "[a definir]"
        ),
    }

    # Substitui placeholders inline
    for placeholder, valor in sub.items():
        template = template.replace(placeholder, valor)

    # Adiciona seção pré-preenchida com o resumo do cálculo no início
    resumo = f"""
> 📊 **Resumo executivo gerado automaticamente em {hoje}:**
>
> - Cliente: **{cliente_razao_social}** (CNPJ {cliente_cnpj}) — regime {regime_tributario}
> - Tese: {tese} ({leading_case})
> - Período: **{competencia_inicial}** a **{competencia_final}** ({num_competencias} competências)
> - Alíquotas aplicadas: PIS {aliq_pis} + COFINS {aliq_cofins} = **{aliq_total}**
> - **Total principal:** {formato_brl(total_principal)}
"""
    if total_atualizado is not None:
        resumo += f"> - **Total atualizado pela SELIC:** {formato_brl(total_atualizado)}\n"
    resumo += f"> - Forma de recuperação: **{forma_recuperacao}**\n"
    if ultimo_dia_pleito:
        resumo += f"> - ⏰ Último dia para pleito: **{ultimo_dia_pleito}**\n"
    if not sem_prescricao:
        resumo += (
            "> - 🚨 **PRESCRIÇÃO NÃO VERIFICADA** — bloquear processo até checagem.\n"
        )
    resumo += "\n---\n"

    minuta_md = template.replace("\n---\n\n## 1. Identificação", resumo + "\n## 1. Identificação")

    return {
        "minuta_markdown": minuta_md,
        "tamanho_chars": len(minuta_md),
        "cliente": cliente_razao_social,
        "cnpj": cliente_cnpj,
        "tese": tese,
        "principal": total_principal,
        "atualizado": total_atualizado,
        "data_geracao": hoje,
        "aviso": (
            "⚠️ Esta é uma MINUTA. Antes de protocolar: (1) preencher tabelas "
            "competência-a-competência da seção 4.1 com a memória detalhada, "
            "(2) anexar EFD-Contribuições retificadoras e demais documentos da "
            "seção 6, (3) revisão por contador CRC + advogado OAB."
        ),
    }


def calc_difal(
    valor_operacao: float,
    aliquota_destino: float,
    aliquota_interestadual: float,
    frete: float = 0.0,
    seguro: float = 0.0,
    outras_despesas: float = 0.0,
) -> dict[str, Any]:
    return _calc_difal(
        valor_operacao=valor_operacao,
        aliquota_destino=aliquota_destino,
        aliquota_interestadual=aliquota_interestadual,
        frete=frete, seguro=seguro, outras_despesas=outras_despesas,
    )


def calc_icms_st(
    valor_operacao: float,
    mva: float,
    aliquota_interna: float,
    aliquota_origem: float,
    frete: float = 0.0,
    seguro: float = 0.0,
    outras_despesas: float = 0.0,
) -> dict[str, Any]:
    return _calc_icms_st(
        valor_operacao=valor_operacao, mva=mva,
        aliquota_interna=aliquota_interna, aliquota_origem=aliquota_origem,
        frete=frete, seguro=seguro, outras_despesas=outras_despesas,
    )


def calc_iss(
    valor_servico: float,
    municipio: str,
    item_lc116: int | None = None,
    simples_nacional: bool = False,
) -> dict[str, Any]:
    return _calc_iss(
        valor_servico=valor_servico, municipio=municipio,
        item_lc116=item_lc116, simples_nacional=simples_nacional,
    )


def buscar_municipio_iss(texto: str) -> dict[str, Any]:
    matches = _buscar_municipio(texto)
    return {
        "query": texto,
        "resultados": [
            {"municipio": m[0], "score": m[1]} for m in matches[:10]
        ],
    }


def calc_gcap_imovel(
    valor_venda: float,
    custo_aquisicao: float,
    data_aquisicao: str,
    benfeitorias: float = 0.0,
    corretagem: float = 0.0,
    unico_imovel: bool = False,
    valor_ate_440k: bool = False,
    data_venda: str | None = None,
) -> dict[str, Any]:
    return _calc_gcap_imovel(
        valor_venda=valor_venda, custo_aquisicao=custo_aquisicao,
        data_aquisicao=data_aquisicao, benfeitorias=benfeitorias,
        corretagem=corretagem, unico_imovel=unico_imovel,
        valor_ate_440k=valor_ate_440k, data_venda=data_venda,
    )


def calc_gcap_veiculo(
    valor_venda: float,
    custo_aquisicao: float,
    tipo_veiculo: str = "particular",
) -> dict[str, Any]:
    return _calc_gcap_veiculo(
        valor_venda=valor_venda, custo_aquisicao=custo_aquisicao,
        tipo_veiculo=tipo_veiculo,
    )


def gcap_crypto_checklist(
    operacoes: list[dict] | None = None,
    saldo_31dez: float | None = None,
) -> dict[str, Any]:
    return _gcap_crypto_checklist(operacoes=operacoes, saldo_31dez=saldo_31dez)


def gcap_etf_exterior_checklist(
    pais_origem: str = "EUA",
    ativos: list[dict] | None = None,
) -> dict[str, Any]:
    return _gcap_etf_checklist(ativos=ativos, pais_origem=pais_origem)


def gerar_dossie_irpf(
    dados_contribuinte: dict[str, Any],
    fontes_tributaveis: list[dict] | None = None,
    rendimentos_exclusivos: list[dict] | None = None,
    rendimentos_isentos: list[dict] | None = None,
    rendimentos_isentos_classificados: list[dict] | None = None,
    bens_direitos: list[dict] | None = None,
    salarios_mensais: list[float] | None = None,
    deducoes_anuais: list[dict] | None = None,
    rendimentos_exterior: list[dict] | None = None,
    ganhos_capital: list[dict] | None = None,
    irrf_ja_retido_anual: float | None = None,
) -> dict[str, Any]:
    return _gerar_dossie_irpf(
        dados_contribuinte=dados_contribuinte,
        fontes_tributaveis=fontes_tributaveis,
        rendimentos_exclusivos=rendimentos_exclusivos,
        rendimentos_isentos=rendimentos_isentos,
        rendimentos_isentos_classificados=rendimentos_isentos_classificados,
        bens_direitos=bens_direitos,
        salarios_mensais=salarios_mensais,
        deducoes_anuais=deducoes_anuais,
        rendimentos_exterior=rendimentos_exterior,
        ganhos_capital=ganhos_capital,
        irrf_ja_retido_anual=irrf_ja_retido_anual,
    )


def validar_dossie_irpf(
    dossie: dict[str, Any],
    regras_excluidas: list[str] | None = None,
) -> dict[str, Any]:
    return _validar_dossie_irpf(
        dossie=dossie,
        regras_excluidas=regras_excluidas,
    )


def calc_carne_leao(
    renda_exterior_moeda: float,
    moeda_origem: str,
    mes_referencia: str,
    dependentes_irrf: int = 0,
    deducoes_mes: float = 0.0,
) -> dict[str, Any]:
    return _calc_carne_leao(
        renda_exterior_moeda=renda_exterior_moeda,
        moeda_origem=moeda_origem,
        mes_referencia=mes_referencia,
        dependentes_irrf=dependentes_irrf,
        deducoes_mes=deducoes_mes,
    )


def calc_custo_empregado(
    salario_bruto: float,
    regime: str = "presumido_real",
    rat_pct: float = 2.0,
    fap: float = 1.0,
    terceiros_pct: float = 5.8,
    vale_transporte: float = 0.0,
    vale_refeicao: float = 0.0,
    plano_saude: float = 0.0,
    outros_beneficios: float = 0.0,
) -> dict[str, Any]:
    return _calc_custo_emp(
        salario_bruto=salario_bruto, regime=regime,
        rat_pct=rat_pct, fap=fap, terceiros_pct=terceiros_pct,
        vale_transporte=vale_transporte, vale_refeicao=vale_refeicao,
        plano_saude=plano_saude, outros_beneficios=outros_beneficios,
    )


def calc_retencoes_pj(
    valor_nota: float,
    tipo_servico: str = "profissional",
    prestador_simples: bool = False,
    reter_inss: bool = False,
    reter_iss: bool = False,
    aliquota_iss: float = 0.0,
) -> dict[str, Any]:
    return _calc_retencoes(
        valor_nota=valor_nota, tipo_servico=tipo_servico,
        prestador_simples=prestador_simples,
        reter_inss=reter_inss, reter_iss=reter_iss,
        aliquota_iss=aliquota_iss,
    )


def calc_lucro_presumido(
    atividade: str,
    receita_trimestre: float,
    receitas_financeiras: float = 0.0,
    outras_receitas: float = 0.0,
) -> dict[str, Any]:
    return _calc_presumido(
        atividade=atividade,
        receita_trimestre=receita_trimestre,
        receitas_financeiras=receitas_financeiras,
        outras_receitas=outras_receitas,
    )


def calc_lucro_real(
    lucro_contabil: float,
    adicoes: float = 0.0,
    exclusoes: float = 0.0,
    prejuizo_fiscal_acumulado: float = 0.0,
    base_negativa_csll_acumulada: float = 0.0,
    receita_bruta: float = 0.0,
    receitas_financeiras: float = 0.0,
    outras_receitas: float = 0.0,
    creditos_pis: float = 0.0,
    creditos_cofins: float = 0.0,
    periodo: str = "trimestral",
    csll_adicoes: float | None = None,
    csll_exclusoes: float | None = None,
) -> dict[str, Any]:
    return _calc_lucro_real(
        lucro_contabil=lucro_contabil,
        adicoes=adicoes, exclusoes=exclusoes,
        prejuizo_fiscal_acumulado=prejuizo_fiscal_acumulado,
        base_negativa_csll_acumulada=base_negativa_csll_acumulada,
        receita_bruta=receita_bruta,
        receitas_financeiras=receitas_financeiras,
        outras_receitas=outras_receitas,
        creditos_pis=creditos_pis, creditos_cofins=creditos_cofins,
        periodo=periodo,
        csll_adicoes=csll_adicoes, csll_exclusoes=csll_exclusoes,
    )


def calc_tema_69(
    operacoes: list[dict[str, Any]],
    tem_acao_pre_15_03_2017: bool = False,
) -> dict[str, Any]:
    """Tema 69 STF — exclusão do ICMS da base de PIS/COFINS.

    Cada operação recebe: competencia (YYYY-MM-DD ou YYYY-MM), receita_bruta,
    icms_destacado, regime ('LUCRO_REAL' ou 'LUCRO_PRESUMIDO').
    """
    if not REC_TRIB_DISPONIVEL:
        return {"erro": "Módulo de recuperação tributária não disponível"}

    from datetime import date as _date
    from decimal import Decimal as _Dec

    ops_engine = []
    for op in operacoes:
        comp_raw = op["competencia"]
        # Aceita "YYYY-MM-DD" ou "YYYY-MM"
        if isinstance(comp_raw, str):
            parts = comp_raw.split("-")
            comp = _date(int(parts[0]), int(parts[1]), 1)
        else:
            comp = comp_raw
        ops_engine.append(_OperacaoTema69(
            competencia=comp,
            receita_bruta=_Dec(str(op["receita_bruta"])),
            icms_destacado=_Dec(str(op["icms_destacado"])),
            regime=op["regime"].upper(),
        ))

    raw = _calc_tema_69_total(ops_engine, tem_acao_pre_15_03_2017=tem_acao_pre_15_03_2017)

    # Serializa Decimals → float, dataclasses → dict
    def _ser_resultado(r):
        return {
            "competencia": r.competencia.isoformat(),
            "regime": r.regime,
            "receita_bruta": float(r.receita_bruta),
            "icms_destacado": float(r.icms_destacado),
            "pis_pago_indevido": float(r.pis_pago_indevido),
            "cofins_pago_indevido": float(r.cofins_pago_indevido),
            "total_recuperavel": float(r.total_recuperavel),
            "dentro_modulacao": r.dentro_modulacao,
            "observacao": r.observacao,
        }

    return {
        "resultados_mensais": [_ser_resultado(r) for r in raw["resultados_mensais"]],
        "total_pis_recuperavel": float(raw["total_pis_recuperavel"]),
        "total_cofins_recuperavel": float(raw["total_cofins_recuperavel"]),
        "total_geral": float(raw["total_geral"]),
        "competencias_elegiveis": raw["competencias_elegiveis"],
        "competencias_bloqueadas": raw["competencias_bloqueadas"],
        "marco_modulacao": "2017-03-15",
        "tem_acao_pre_15_03_2017": tem_acao_pre_15_03_2017,
        "aviso_selic": (
            "⚠️ Valor é PRINCIPAL apenas. Aplicar atualização pela SELIC "
            "(art. 39, §4º Lei 9.250/95) antes do pedido de restituição/compensação."
        ),
        "base_legal": (
            "STF Tema 69 — RE 574.706 (transitado 2017, modulação 13/05/2021); "
            "LC 118/2005 art. 3º (prescrição 5 anos); Lei 9.430/96 (PER/DCOMP)"
        ),
    }


def verificar_prescricao(
    data_pagamento: str,
    data_referencia: str | None = None,
) -> dict[str, Any]:
    """Verifica prescrição quinquenal (LC 118/2005)."""
    if not REC_TRIB_DISPONIVEL:
        return {"erro": "Módulo não disponível"}
    from datetime import date as _date
    parts_pag = data_pagamento.split("-")
    pag = _date(int(parts_pag[0]), int(parts_pag[1]), int(parts_pag[2]))
    ref = None
    if data_referencia:
        parts_ref = data_referencia.split("-")
        ref = _date(int(parts_ref[0]), int(parts_ref[1]), int(parts_ref[2]))
    try:
        r = _verificar_prescricao(data_pagamento=pag, data_referencia=ref)
    except ValueError as exc:
        return {"erro": str(exc)}
    inicio, fim = _periodo_recuperavel(ref)
    return {
        "data_pagamento": r.data_pagamento.isoformat(),
        "data_corte": r.data_corte.isoformat(),
        "data_limite_pleito": r.data_limite_pleito.isoformat(),
        "dias_restantes": r.dias_restantes,
        "prescrito": r.prescrito,
        "observacao": r.observacao,
        "periodo_recuperavel_inicio": inicio.isoformat(),
        "periodo_recuperavel_fim": fim.isoformat(),
        "base_legal": "LC 118/2005, art. 3º; CTN art. 168 I",
    }


def darf_consultar(tributo: str) -> dict[str, Any]:
    return _consultar_darf(tributo)


def darf_listar_regime(regime: str) -> dict[str, Any]:
    return {"regime": regime, "codigos": _darf_regime(regime)}


def darf_buscar(texto: str) -> dict[str, Any]:
    # _darf_buscar já retorna dict com {busca, total_encontrado, resultados[]}
    return _darf_buscar(texto)


def calc_distribuicao_lucros(
    valor_mensal: float,
    lucro_apurado_disponivel: float | None = None,
    distribuicao_por_socio: list[float] | None = None,
    tem_escrituracao_regular: bool = True,
    lucro_aprovado_ate_2025: bool = False,
    regime_tributario: str | None = None,
) -> dict[str, Any]:
    return _calc_distribuicao(
        valor_mensal=valor_mensal,
        lucro_apurado_disponivel=lucro_apurado_disponivel,
        distribuicao_por_socio=distribuicao_por_socio,
        tem_escrituracao_regular=tem_escrituracao_regular,
        lucro_aprovado_ate_2025=lucro_aprovado_ate_2025,
        regime_tributario=regime_tributario,
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
        "name": "sugerir_anexo_engenharia",
        "description": (
            "SKILL.md §5: sugere Anexo correto (III/V vs IV) para CNAEs ambíguos de "
            "engenharia/arquitetura/construção (71.12-0-00, 71.11-1-00, 43.29-1-99…). "
            "Quando há execução de obras OU cessão de mão de obra → Anexo IV (CPP separada). "
            "Quando é apenas consultoria/projetos/laudos → Anexo III/V c/ Fator R. "
            "Use ANTES de calcular DAS quando o usuário menciona engenharia/arquitetura."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cnae": {"type": "string", "description": "CNAE com ou sem máscara"},
                "executa_obras": {"type": "boolean", "default": False},
                "cessao_mao_obra": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "calc_decimo_terceiro",
        "description": (
            "Calcula 13° salário (Lei 4.090/62) com proporcionalidade (avos/12) e ambas "
            "as parcelas: 1ª (50% sem deduções, paga até 30/nov) e 2ª (saldo após INSS+IRRF, "
            "até 20/dez). FGTS de 8% incide sobre as duas parcelas. INSS é progressivo "
            "sobre o 13° BRUTO completo, não sobre cada parcela isoladamente."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "salario_bruto": {"type": "number"},
                "meses_trabalhados": {"type": "integer", "default": 12,
                                      "description": "Avos no exercício (1-12)"},
                "num_dependentes": {"type": "integer", "default": 0},
                "pensao_alimenticia": {"type": "number", "default": 0},
            },
            "required": ["salario_bruto"],
        },
    },
    {
        "name": "calc_ferias",
        "description": (
            "Calcula férias (CLT Arts. 129-153 + CF Art. 7° XVII) com 1/3 constitucional. "
            "REGRA CRÍTICA (CLT 144 + Súmula 386 TST): abono pecuniário (até 10 dias) + "
            "1/3 sobre abono são ISENTOS de INSS e IRRF. Apenas férias gozadas + 1/3 "
            "constitucional sobre elas é tributável. Erro recorrente: incluir abono na "
            "base do INSS — gera autuação."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "salario": {"type": "number"},
                "dias_ferias": {"type": "integer", "default": 30,
                                "description": "20-30 (mín 20 quando há abono)"},
                "dias_abono": {"type": "integer", "default": 0,
                               "description": "0-10 (CLT 143)"},
                "num_dependentes": {"type": "integer", "default": 0},
                "media_adicionais": {"type": "number", "default": 0},
            },
            "required": ["salario"],
        },
    },
    {
        "name": "calc_hora_extra",
        "description": (
            "Calcula horas extras (CLT Arts. 59 e 70). Adicional mínimo: 50% em dias "
            "normais e 100% em domingos/feriados (CCT pode ser maior). Inclui DSR opcional "
            "(Lei 605/49 + Súmula 172 TST) sobre verbas variáveis (HE + comissões) — "
            "informe dias_uteis e domingos_feriados para calcular DSR junto."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "salario": {"type": "number"},
                "horas_normais": {"type": "number", "description": "HE 50%"},
                "horas_feriado": {"type": "number", "default": 0, "description": "HE 100%"},
                "adicional_normal": {"type": "number", "default": 50,
                                     "description": "% adicional 50% mínimo"},
                "adicional_feriado": {"type": "number", "default": 100,
                                      "description": "% adicional 100% mínimo"},
                "jornada_mensal": {"type": "integer", "default": 220,
                                   "description": "220h=44h/sem; 180h=36h/sem"},
                "comissoes": {"type": "number", "default": 0},
                "dias_uteis": {"type": "integer", "description": "Para DSR (opcional)"},
                "domingos_feriados": {"type": "integer", "description": "Para DSR (opcional)"},
            },
            "required": ["salario", "horas_normais"],
        },
    },
    {
        "name": "resumo_mei",
        "description": (
            "Resumo completo do MEI (LC 123/2006 + LC 188/2021): DAS mensal por atividade "
            "(comércio R$82, serviços R$82, comércio+serviços R$83, caminhoneiro R$195), "
            "verificação do limite anual (R$81K geral / R$251,6K caminhoneiro — proporcional "
            "por meses_atividade), situação de enquadramento (OK / EXCESSO_ATE_20PCT → "
            "desenquadramento prospectivo / EXCESSO_ACIMA_20PCT → retroativo + multa), "
            "obrigações (DAS-MEI dia 20, DASN-SIMEI até 31/maio, max 1 empregado). "
            "ATENÇÃO: PLP 108/21 (R$130K) NÃO está em vigor."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "atividade": {"type": "string",
                              "enum": ["comercio", "servicos", "comercio_servicos", "caminhoneiro"]},
                "receita_bruta_anual": {"type": "number", "default": 0},
                "meses_atividade": {"type": "integer", "default": 12},
            },
        },
    },
    {
        "name": "darf_consultar",
        "description": (
            "Consulta códigos DARF/GPS/DAS por tributo (IRPJ, CSLL, PIS, COFINS, IRRF, "
            "CSRF, INSS, FGTS, DAS, DAS-MEI, ICMS, ISS, CBS, IBS, DIFAL). Retorna lista "
            "com código, descrição, regime, periodicidade, vencimento, observações. "
            "Use SEMPRE que o usuário pedir 'qual o código DARF de X' ou 'como pagar Y'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"tributo": {"type": "string"}},
            "required": ["tributo"],
        },
    },
    {
        "name": "darf_buscar",
        "description": (
            "Busca livre nos códigos DARF: por número (ex: '0561'), descrição parcial "
            "(ex: 'rendimentos do trabalho'), ou tributo. Retorna todos os matches."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"texto": {"type": "string"}},
            "required": ["texto"],
        },
    },
    {
        "name": "calc_tema_69",
        "description": (
            "STF Tema 69 (RE 574.706) — exclusão do ICMS da base de PIS/COFINS. "
            "Calcula crédito recuperável de PIS/COFINS pagos indevidamente sobre o "
            "ICMS destacado. Modulação STF 13/05/2021: créditos a partir de 15/03/2017 "
            "são automáticos; pré-modulação só com ação ajuizada antes daquela data. "
            "Regimes: LUCRO_REAL (não-cumulativo: PIS 1,65%, COFINS 7,6%) e LUCRO_PRESUMIDO "
            "(cumulativo: PIS 0,65%, COFINS 3%). Simples e MEI ficam de fora. Retorna "
            "PRINCIPAL — atualização SELIC é separada (art. 39 §4 Lei 9.250/95)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "operacoes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "competencia": {"type": "string", "description": "YYYY-MM-DD ou YYYY-MM"},
                            "receita_bruta": {"type": "number"},
                            "icms_destacado": {"type": "number"},
                            "regime": {"type": "string", "enum": ["LUCRO_REAL", "LUCRO_PRESUMIDO"]},
                        },
                        "required": ["competencia", "receita_bruta", "icms_destacado", "regime"],
                    },
                },
                "tem_acao_pre_15_03_2017": {"type": "boolean", "default": False,
                    "description": "Se True, libera períodos pré-modulação"},
            },
            "required": ["operacoes"],
        },
    },
    {
        "name": "verificar_prescricao",
        "description": (
            "Verifica prescrição quinquenal (LC 118/2005 art. 3º) para pleitos de "
            "restituição/compensação de tributos pagos indevidamente. Retorna se está "
            "prescrito, dias restantes, data limite. Use ANTES de qualquer estudo de "
            "recuperação tributária — pagamento prescrito não recupera."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "data_pagamento": {"type": "string", "description": "YYYY-MM-DD"},
                "data_referencia": {"type": "string",
                    "description": "Data do protocolo (default: hoje)"},
            },
            "required": ["data_pagamento"],
        },
    },
    {
        "name": "calc_tema_779",
        "description": (
            "STJ Tema 779 (REsp 1.221.170/PR) — conceito amplo de insumo gerador de "
            "crédito de PIS/COFINS no regime não-cumulativo (Lucro Real). Aplica "
            "essencialidade + relevância. Categorias: FORTE (matéria-prima, embalagem, "
            "energia/combustível produtivo), MEDIA (EPI obrigatório, manutenção, "
            "frete interno, limpeza área produtiva — exige laudo), FRACA (mat. escritório, "
            "marketing — alto risco de glosa), NAO_APLICAVEL (mão-de-obra PF, tributos "
            "recuperáveis — vedação legal). Alíquota total 9,25%."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "insumos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "descricao": {"type": "string"},
                            "categoria": {"type": "string"},
                            "valor_total_competencia": {"type": "number"},
                            "competencia": {"type": "string", "description": "MM/AAAA"},
                            "justificativa_tecnica": {"type": "string"},
                            "tem_laudo_tecnico": {"type": "boolean"},
                        },
                        "required": ["descricao", "categoria",
                                     "valor_total_competencia", "competencia"],
                    },
                },
            },
            "required": ["insumos"],
        },
    },
    {
        "name": "gerar_minuta_perdcomp",
        "description": (
            "Gera MINUTA de memória de cálculo PER/DCOMP a partir do template RRT "
            "(IN RFB 2.055/2021 + Lei 9.430/96 art. 74 + CTN 165-170). Substitui "
            "placeholders pelos dados do cliente, cláusula CRC+OAB, alíquotas conforme "
            "regime, resumo executivo. Retorna markdown pronto para revisão humana — "
            "NÃO é o documento final, exige preenchimento das tabelas competência-a-"
            "competência e revisão jurídica antes do protocolo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_razao_social": {"type": "string"},
                "cliente_cnpj": {"type": "string"},
                "regime_tributario": {"type": "string", "enum": ["LUCRO_REAL", "LUCRO_PRESUMIDO"]},
                "tese": {"type": "string"},
                "leading_case": {"type": "string"},
                "competencia_inicial": {"type": "string"},
                "competencia_final": {"type": "string"},
                "num_competencias": {"type": "integer"},
                "total_principal": {"type": "number"},
                "total_atualizado": {"type": "number"},
                "contador_nome": {"type": "string"},
                "contador_crc": {"type": "string"},
                "advogado_nome": {"type": "string"},
                "advogado_oab": {"type": "string"},
                "forma_recuperacao": {"type": "string", "enum": ["DCOMP", "PER", "RESSARCIMENTO"]},
                "ultimo_dia_pleito": {"type": "string"},
                "sem_prescricao": {"type": "boolean"},
            },
            "required": ["cliente_razao_social", "cliente_cnpj", "regime_tributario",
                         "tese", "leading_case", "competencia_inicial", "competencia_final",
                         "num_competencias", "total_principal", "contador_nome", "contador_crc"],
        },
    },
    {
        "name": "calc_gcap_imovel",
        "description": (
            "Calcula ganho de capital em alienação de imóvel PF (Lei 11.196/2005, Lei "
            "7.713/88, IN RFB 599/2005). Aplica fator redutor por tempo de posse, "
            "alíquotas progressivas (15%/17,5%/20%/22,5% conforme faixas), e ISENÇÕES: "
            "(1) único imóvel residencial com venda ≤ R$440K; (2) reinvestimento em "
            "residência em 180 dias; (3) imóvel adquirido pré-1969. Prejuízo NÃO "
            "compensa ganhos futuros para PF (vedação Art. 11 IN RFB 599/2005)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "valor_venda": {"type": "number"},
                "custo_aquisicao": {"type": "number"},
                "data_aquisicao": {"type": "string", "description": "YYYY-MM-DD"},
                "benfeitorias": {"type": "number", "default": 0},
                "corretagem": {"type": "number", "default": 0},
                "unico_imovel": {"type": "boolean", "default": False},
                "valor_ate_440k": {"type": "boolean", "default": False},
                "data_venda": {"type": "string", "description": "default: hoje"},
            },
            "required": ["valor_venda", "custo_aquisicao", "data_aquisicao"],
        },
    },
    {
        "name": "calc_gcap_veiculo",
        "description": (
            "Calcula ganho de capital em veículo PF (RIR/2018 + IN RFB 599/2005). "
            "Veículo PARTICULAR de uso pessoal: ISENTO de tributação (mas reportar "
            "na IRPF). Veículo COMERCIAL (revenda/aluguel): tributável com alíquotas "
            "progressivas. Veículo de DEPENDENTE: alerta especial — exige parecer "
            "jurídico para definir tributação no titular ou dependente."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "valor_venda": {"type": "number"},
                "custo_aquisicao": {"type": "number"},
                "tipo_veiculo": {"type": "string",
                    "enum": ["particular", "comercial", "dependente"]},
            },
            "required": ["valor_venda", "custo_aquisicao"],
        },
    },
    {
        "name": "gcap_crypto_checklist",
        "description": (
            "Modo GUIDANCE — gera checklist de 12+ itens + alertas para tributação "
            "de criptoativos PF (IN RFB 1.888/2019, Lei 14.754/2023). NÃO calcula "
            "imposto: a complexidade do FIFO + isenção mensal R$35K + obrigação de "
            "declarar saldo >R$5K em 31/12 exige revisão manual do contador. "
            "Alíquotas: 15-22,5% sobre ganho mensal acima da isenção. "
            "Detecta padrões de risco (>30 trades/ano = escrutínio RFB)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "operacoes": {"type": "array", "items": {"type": "object"},
                    "description": "Lista {tipo, data, valor_brl, quantidade, exchange}"},
                "saldo_31dez": {"type": "number"},
            },
        },
    },
    {
        "name": "gcap_etf_exterior_checklist",
        "description": (
            "Modo GUIDANCE — checklist + tratado de bitributação para ETFs no exterior "
            "(Lei 14.754/2023 — come-cotas anual 15%, regime offshore opcional). Verifica "
            "tratados Brasil-país de origem (EUA, IRLANDA, LUXEMBURGO, etc.) "
            "para evitar dupla tributação. Não calcula valores — exige confirmação manual."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pais_origem": {"type": "string", "description": "ex: EUA, IRLANDA"},
                "ativos": {"type": "array", "items": {"type": "object"},
                           "description": "Opcional: lista de operações"},
            },
        },
    },
    {
        "name": "calc_carne_leao",
        "description": (
            "Carnê-leão isolado para um mês: renda no exterior em moeda → BRL via "
            "PTAX de fechamento → IRRF mensal devido (tabela Lei 15.270/2025). "
            "Suporta dependentes (R$189,59/mês cada) e deduções (pensão judicial, "
            "previdência). Sinaliza desvio de PTAX se PTAX usado >10% diferente "
            "do esperado. Para PF residente que recebe do exterior."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "renda_exterior_moeda": {"type": "number"},
                "moeda_origem": {"type": "string",
                    "enum": ["USD", "EUR", "GBP", "JPY", "CHF"]},
                "mes_referencia": {"type": "string", "description": "YYYY-MM"},
                "dependentes_irrf": {"type": "integer", "default": 0},
                "deducoes_mes": {"type": "number", "default": 0},
            },
            "required": ["renda_exterior_moeda", "moeda_origem", "mes_referencia"],
        },
    },
    {
        "name": "gerar_dossie_irpf",
        "description": (
            "Gera dossiê IRPF completo de pessoa física com 12 seções: enquadramento, "
            "dados, rendimentos tributáveis, exclusivos, isentos, deduções, bens, "
            "ganhos de capital, exterior, comparativo completa×simplificada, e validação "
            "cruzada. Orquestra calcular_irpf_integrado + validar_consistencia_irpf "
            "(17 regras). Retorna dossiê estruturado pronto para entregar ao cliente."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dados_contribuinte": {"type": "object",
                    "description": "{cpf, nome, dependentes[], pensao_alimenticia_mensal}"},
                "fontes_tributaveis": {"type": "array", "items": {"type": "object"}},
                "rendimentos_exclusivos": {"type": "array", "items": {"type": "object"}},
                "rendimentos_isentos": {"type": "array", "items": {"type": "object"}},
                "bens_direitos": {"type": "array", "items": {"type": "object"}},
                "deducoes_anuais": {"type": "array", "items": {"type": "object"}},
                "ganhos_capital": {"type": "array", "items": {"type": "object"}},
                "rendimentos_exterior": {"type": "array", "items": {"type": "object"}},
                "salarios_mensais": {"type": "array", "items": {"type": "number"}},
                "irrf_ja_retido_anual": {"type": "number"},
            },
            "required": ["dados_contribuinte"],
        },
    },
    {
        "name": "validar_dossie_irpf",
        "description": (
            "Valida dossiê IRPF contra 17 regras de consistência cruzada (R01-R17). "
            "Detecta: IRRF total cruzado entre seções, limites de educação/PGBL/PGBL "
            "com regime obrigatório, crypto sem custódia, exterior sem PTAX, "
            "tratado Brasil-EUA inexistente, completa vs simplificada obrigatória, "
            "saldo de imposto coerente, dependentes com CPF, bens exterior convertidos, "
            "código aluguel não-dedutível, exercício vs ano-calendário, dividendos "
            "acima de isenção. Retorna inconsistências por severidade + status final."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dossie": {"type": "object", "description": "Dossiê completo"},
                "regras_excluidas": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Códigos a pular (ex: ['R10', 'R16'])",
                },
            },
            "required": ["dossie"],
        },
    },
    {
        "name": "calc_custo_empregado",
        "description": (
            "Calcula custo TOTAL mensal/anual de empregado CLT (Lei 8.212/91 + LC "
            "123/2006). Encargos variam por regime: presumido_real (INSS patronal "
            "20% + RAT×FAP + Terceiros 5,8% + FGTS 8%); simples_i_iii_v (CPP no DAS, "
            "apenas FGTS); simples_iv (INSS 20% + RAT×FAP + FGTS, Terceiros dispensado "
            "para todo Simples). Provisões mensais: 13° (1/12) + férias+1/3 (1/9). "
            "Benefícios opcionais: VT, VR/VA, plano de saúde, outros CCT."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "salario_bruto": {"type": "number"},
                "regime": {"type": "string",
                           "enum": ["presumido_real", "simples_i_iii_v", "simples_iv"]},
                "rat_pct": {"type": "number", "default": 2,
                            "description": "1/2/3 (leve/médio/grave)"},
                "fap": {"type": "number", "default": 1.0,
                        "description": "Fator Acidentário 0,5-2,0"},
                "terceiros_pct": {"type": "number", "default": 5.8},
                "vale_transporte": {"type": "number", "default": 0},
                "vale_refeicao": {"type": "number", "default": 0},
                "plano_saude": {"type": "number", "default": 0},
                "outros_beneficios": {"type": "number", "default": 0},
            },
            "required": ["salario_bruto"],
        },
    },
    {
        "name": "calc_retencoes_pj",
        "description": (
            "Calcula retenções sobre nota PJ→PJ (IN RFB 1.234/2012 + Art. 30 Lei "
            "10.833/2003 + Art. 31 Lei 8.212/91). Tipos: profissional (IRRF 1,5% + "
            "CSRF 4,65%), limpeza/vigilância/conservação (IRRF 1% + CSRF), cessao_mao_obra "
            "(IRRF 1% + CSRF + INSS 11% retido), publicidade (IRRF 1,5% — RETÉM mesmo "
            "Simples), comissao (IRRF 1,5%). REGRAS: Simples NÃO retém IRRF (exceto "
            "publicidade) NEM CSRF. CSRF DISPENSADA se valor_nota ≤ R$215,05."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "valor_nota": {"type": "number"},
                "tipo_servico": {"type": "string",
                    "enum": ["profissional", "limpeza", "vigilancia", "conservacao",
                             "cessao_mao_obra", "publicidade", "comissao"]},
                "prestador_simples": {"type": "boolean", "default": False},
                "reter_inss": {"type": "boolean", "default": False,
                               "description": "Apenas cessao_mao_obra"},
                "reter_iss": {"type": "boolean", "default": False},
                "aliquota_iss": {"type": "number", "default": 0,
                                  "description": "Em % (ex: 5 para 5%)"},
            },
            "required": ["valor_nota"],
        },
    },
    {
        "name": "calc_lucro_presumido",
        "description": (
            "Calcula IRPJ + CSLL + PIS + COFINS no Lucro Presumido (Lei 9.249/95 + "
            "Lei 9.718/98). Período TRIMESTRAL. Presunção varia por atividade (8% comércio/"
            "indústria, 32% serviços, 16% transporte cargas, etc.). IRPJ 15% sobre presunção "
            "+ adicional 10% sobre o que excede R$ 60K/trimestre. CSLL 9%. PIS 0,65% + "
            "COFINS 3% (cumulativo, sem créditos). Receitas financeiras e outras entram "
            "100% na base. IRPJ+CSLL parceláveis em até 3x se ≥ R$2.000."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "atividade": {"type": "string",
                    "enum": ["comercio", "industria", "servicos", "transporte_cargas",
                             "transporte_passageiros", "combustiveis",
                             "servicos_hospitalares", "construcao_civil"]},
                "receita_trimestre": {"type": "number"},
                "receitas_financeiras": {"type": "number", "default": 0},
                "outras_receitas": {"type": "number", "default": 0},
            },
            "required": ["atividade", "receita_trimestre"],
        },
    },
    {
        "name": "calc_lucro_real",
        "description": (
            "Apuração completa Lucro Real via LALUR: lucro contábil + adições - exclusões "
            "= lucro ajustado. Compensa prejuízo fiscal anterior limitado a 30% do lucro "
            "ajustado. IRPJ 15% + adicional 10% acima R$60K/trim ou R$20K/mês. CSLL 9% "
            "com base independente. PIS/COFINS NÃO-CUMULATIVO (1,65% + 7,6%) com créditos. "
            "Receitas financeiras: PIS 0,65% + COFINS 4% (Decreto 8.426/2015). Retorna "
            "saldos atualizados de prejuízo fiscal e base negativa CSLL para próximo período."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lucro_contabil": {"type": "number", "description": "Pode ser negativo"},
                "adicoes": {"type": "number", "default": 0},
                "exclusoes": {"type": "number", "default": 0},
                "prejuizo_fiscal_acumulado": {"type": "number", "default": 0},
                "base_negativa_csll_acumulada": {"type": "number", "default": 0},
                "receita_bruta": {"type": "number", "default": 0},
                "receitas_financeiras": {"type": "number", "default": 0},
                "outras_receitas": {"type": "number", "default": 0},
                "creditos_pis": {"type": "number", "default": 0},
                "creditos_cofins": {"type": "number", "default": 0},
                "periodo": {"type": "string", "enum": ["trimestral", "mensal"]},
                "csll_adicoes": {"type": "number"},
                "csll_exclusoes": {"type": "number"},
            },
            "required": ["lucro_contabil"],
        },
    },
    {
        "name": "calc_difal",
        "description": (
            "Calcula DIFAL (Diferencial de Alíquota ICMS) — EC 87/2015, LC 190/2022. "
            "Operação interestadual destinada a consumidor final não-contribuinte: "
            "DIFAL = base × (alíquota_interna_destino - alíquota_interestadual). "
            "Desde 2022, 100% vai para o estado de DESTINO. Base = valor_operação + "
            "frete + seguro + outras despesas. Alíquotas interestaduais comuns: "
            "4% (importados), 7% (Norte/Nordeste/CO + ES), 12% (Sul + SE)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "valor_operacao": {"type": "number"},
                "aliquota_destino": {"type": "number", "description": "Interna do destino (%)"},
                "aliquota_interestadual": {"type": "number", "description": "4/7/12%"},
                "frete": {"type": "number", "default": 0},
                "seguro": {"type": "number", "default": 0},
                "outras_despesas": {"type": "number", "default": 0},
            },
            "required": ["valor_operacao", "aliquota_destino", "aliquota_interestadual"],
        },
    },
    {
        "name": "calc_icms_st",
        "description": (
            "Calcula ICMS-ST (Substituição Tributária) — antecipação do imposto sobre toda "
            "a cadeia. Base: BC-ST = (valor + despesas) × (1 + MVA/100); ICMS-ST = "
            "BC-ST × alíq_interna_destino - ICMS_próprio (valor × alíq_origem). "
            "Se ICMS-ST < 0 → não há ST a recolher; tem_restituicao indica direito a ressarcir."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "valor_operacao": {"type": "number"},
                "mva": {"type": "number", "description": "Margem de Valor Agregado (%)"},
                "aliquota_interna": {"type": "number", "description": "Interna do destino (%)"},
                "aliquota_origem": {"type": "number", "description": "Interna do origem (%)"},
                "frete": {"type": "number", "default": 0},
                "seguro": {"type": "number", "default": 0},
                "outras_despesas": {"type": "number", "default": 0},
            },
            "required": ["valor_operacao", "mva", "aliquota_interna", "aliquota_origem"],
        },
    },
    {
        "name": "calc_iss",
        "description": (
            "Calcula ISS sobre serviço prestado (LC 116/2003, alíquota máxima 5%). "
            "Base de municípios brasileiros (incl. CCTs Campinas). Item LC 116 pode "
            "alterar alíquota (1=TI, 7=engenharia, 8=educação, 14=saúde, 17=consultoria). "
            "Para Simples Nacional, ISS pode estar incluído no DAS (retorna iss_valor=0 "
            "+ iss_valor_base para referência). Município não-mapeado → alíquota máxima "
            "5% como conservadora + sugestões de busca."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "valor_servico": {"type": "number"},
                "municipio": {"type": "string", "description": "ex: 'São Paulo-SP'"},
                "item_lc116": {"type": "integer", "description": "1-40 (opcional)"},
                "simples_nacional": {"type": "boolean", "default": False},
            },
            "required": ["valor_servico", "municipio"],
        },
    },
    {
        "name": "buscar_municipio_iss",
        "description": (
            "Busca fuzzy de município brasileiro na base do ISS (≥5K municípios). "
            "Retorna até 10 matches ranqueados. Use quando o usuário não souber a "
            "grafia exata do município."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"texto": {"type": "string"}},
            "required": ["texto"],
        },
    },
    {
        "name": "darf_listar_regime",
        "description": (
            "Lista todos os códigos DARF aplicáveis a um regime tributário "
            "(simples, presumido, lucro_real, mei, dp). Útil para checklist mensal."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "regime": {"type": "string",
                           "enum": ["simples", "presumido", "lucro_real", "mei", "dp"]},
            },
            "required": ["regime"],
        },
    },
    {
        "name": "calc_distribuicao_lucros",
        "description": (
            "Calcula tributação sobre distribuição de lucros (Lei 15.270/2025). "
            "Regras críticas conforme SKILL.md: (1) IRRF 10% incide sobre VALOR INTEGRAL "
            "se mensal > R$ 50K/sócio (efeito-salto: R$ 50.001 produz líquido MENOR que "
            "R$ 50.000); (2) regime_tributario='simples' adiciona alerta da controvérsia "
            "LC 123 art. 14 vs Lei 15.270/2025 (CF art. 146 III 'd'); (3) "
            "tem_escrituracao_regular=False → alerta CRÍTICO (RFB pode reclassificar como "
            "pró-labore: 27,5% IRPF + 11% INSS + retroativos); (4) lucro_aprovado_ate_2025=True "
            "+ pago até 31/12/2028 → ISENÇÃO TOTAL mantida (regra de transição)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "valor_mensal": {"type": "number", "description": "Valor TOTAL distribuído no mês (R$)"},
                "lucro_apurado_disponivel": {"type": "number"},
                "distribuicao_por_socio": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Distribuição desigual; soma deve = valor_mensal",
                },
                "tem_escrituracao_regular": {"type": "boolean", "default": True},
                "lucro_aprovado_ate_2025": {"type": "boolean", "default": False},
                "regime_tributario": {
                    "type": "string", "enum": ["simples", "presumido", "lucro_real"],
                },
            },
            "required": ["valor_mensal"],
        },
    },
    {
        "name": "calc_cbs_ibs",
        "description": (
            "Calcula CBS + IBS sobre uma operação fiscal específica em um ano da "
            "transição (2026-2033) — EC 132/2023 + LC 214/2025. 2026 = ano-teste "
            "(CBS 0,9% + IBS 0,1%); fases progressivas até regime definitivo em 2033 "
            "(CBS ~8,8% + IBS ~17,7%). Retorna comparativo carga antiga vs nova e "
            "compensação CBS×PIS/COFINS quando aplicável (2026). Setores específicos: "
            "combustíveis (monofásico), financeiro/imobiliário/saúde (regimes diferenciados)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "valor_operacao": {"type": "number"},
                "ano": {"type": "integer", "description": "2026-2033 transição"},
                "regime": {"type": "string", "enum": ["simples", "lucro_presumido", "lucro_real"]},
                "aliquota_icms": {"type": "number", "default": 0},
                "aliquota_iss": {"type": "number", "default": 0},
                "tipo_operacao": {"type": "string", "enum": ["mercadoria", "servico", "misto"]},
                "setor_especifico": {
                    "type": "string",
                    "enum": ["combustiveis", "financeiro", "imobiliario", "saude", "educacao"],
                },
            },
            "required": ["valor_operacao", "ano"],
        },
    },
    {
        "name": "projecao_cbs_ibs",
        "description": (
            "Gera projeção da carga tributária ano-a-ano de 2026 a 2033 para a "
            "mesma operação. Útil para planejamento de transição: mostra quando a "
            "carga ultrapassa o regime atual e pode forçar re-precificação."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "valor_operacao": {"type": "number"},
                "regime": {"type": "string", "enum": ["simples", "lucro_presumido", "lucro_real"]},
                "aliquota_icms": {"type": "number", "default": 0},
                "aliquota_iss": {"type": "number", "default": 0},
            },
            "required": ["valor_operacao"],
        },
    },
    {
        "name": "calc_irpf_integrado",
        "description": (
            "Calcula a posição anual de IRPF para Pessoa Física (Exercício 2026, "
            "ano-calendário 2025). Integra: rendimentos CLT mensais, deduções legais "
            "(saúde, educação, previdência privada — com validação de limites), "
            "carnê-leão (rendimentos no exterior), ganhos de capital (imóvel, veículo). "
            "Compara com desconto simplificado (20% até R$16.754,34) e retorna situação "
            "fiscal: ZERADO, RESTITUIR ou PAGAR. Base: Lei 9.250/95, Lei 15.270/2025, "
            "RIR/2018, IN RFB 1.500/2014."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "salarios_mensais": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "12 valores mensais; vazio = sem renda CLT",
                },
                "num_dependentes": {"type": "integer", "default": 0},
                "pensao_alimenticia_mensal": {"type": "number", "default": 0},
                "deducoes_anuais": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tipo": {"type": "string", "enum": ["saude", "educacao",
                                "previdencia_privada", "pensao_alimenticia",
                                "dependentes", "livro_caixa"]},
                            "valor": {"type": "number"},
                        },
                        "required": ["tipo", "valor"],
                    },
                },
                "rendimentos_exterior": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "valor": {"type": "number"},
                            "moeda": {"type": "string", "enum": ["USD", "EUR", "GBP"]},
                            "mes": {"type": "integer"},
                        },
                        "required": ["valor", "moeda", "mes"],
                    },
                },
                "ganhos_capital": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tipo": {"type": "string", "enum": ["imovel", "veiculo"]},
                            "valor_venda": {"type": "number"},
                            "custo_aquisicao": {"type": "number"},
                        },
                        "required": ["tipo", "valor_venda", "custo_aquisicao"],
                    },
                },
                "irrf_ja_retido_anual": {"type": "number", "default": 0},
            },
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
    "sugerir_anexo_engenharia": sugerir_anexo_engenharia,
    "calc_prolabore": calc_prolabore,
    "calc_comparativo": calc_comparativo,
    "calc_rescisao": calc_rescisao,
    "calc_folha_batch": calc_folha_batch,
    "calc_decimo_terceiro": calc_decimo_terceiro,
    "calc_ferias": calc_ferias,
    "calc_hora_extra": calc_hora_extra,
    "resumo_mei": resumo_mei,
    "darf_consultar": darf_consultar,
    "darf_listar_regime": darf_listar_regime,
    "darf_buscar": darf_buscar,
    "calc_tema_69": calc_tema_69,
    "verificar_prescricao": verificar_prescricao,
    "calc_tema_779": calc_tema_779,
    "gerar_minuta_perdcomp": gerar_minuta_perdcomp,
    "calc_difal": calc_difal,
    "calc_icms_st": calc_icms_st,
    "calc_iss": calc_iss,
    "buscar_municipio_iss": buscar_municipio_iss,
    "calc_lucro_presumido": calc_lucro_presumido,
    "calc_lucro_real": calc_lucro_real,
    "calc_custo_empregado": calc_custo_empregado,
    "calc_retencoes_pj": calc_retencoes_pj,
    "calc_gcap_imovel": calc_gcap_imovel,
    "calc_gcap_veiculo": calc_gcap_veiculo,
    "gcap_crypto_checklist": gcap_crypto_checklist,
    "gcap_etf_exterior_checklist": gcap_etf_exterior_checklist,
    "calc_carne_leao": calc_carne_leao,
    "gerar_dossie_irpf": gerar_dossie_irpf,
    "validar_dossie_irpf": validar_dossie_irpf,
    "calc_distribuicao_lucros": calc_distribuicao_lucros,
    "calc_irpf_integrado": calc_irpf_integrado,
    "calc_cbs_ibs": calc_cbs_ibs,
    "projecao_cbs_ibs": projecao_cbs_ibs,
}
