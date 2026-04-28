from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.calculators import (
    CBSIBSProjecaoRequest,
    CBSIBSRequest,
    ComparativoRegimesRequest,
    DarfBuscaRequest,
    DarfRegimeRequest,
    DecimoTerceiroRequest,
    DIFALRequest,
    DistribuicaoLucrosRequest,
    FeriasRequest,
    FolhaBatchRequest,
    HoraExtraRequest,
    ICMSSTRequest,
    IRPFRequest,
    ISSRequest,
    LucroPresumidoRequest,
    LucroRealRequest,
    MEIResumoRequest,
    MunicipioBuscaRequest,
    PerDcompMinutaRequest,
    PrescricaoRequest,
    ProlaboreRequest,
    RescisaoRequest,
    SimplesDASRequest,
    SugerirAnexoRequest,
    Tema69Request,
    Tema779Request,
)
from app.services import engine


router = APIRouter(prefix="/calc", tags=["calculators"])


@router.post("/simples-das")
def simples_das(req: SimplesDASRequest) -> dict:
    result = engine.calc_simples_das(
        anexo=req.anexo,
        rbt12=req.rbt12,
        receita_mes=req.receita_mes,
        folha12=req.folha12,
    )
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/sugerir-anexo-engenharia")
def sugerir_anexo_engenharia(req: SugerirAnexoRequest) -> dict:
    """SKILL.md §5: enquadramento Anexo IV vs III/V para CNAEs ambíguos."""
    return engine.sugerir_anexo_engenharia(
        cnae=req.cnae,
        executa_obras=req.executa_obras,
        cessao_mao_obra=req.cessao_mao_obra,
    )


@router.post("/prolabore")
def prolabore(req: ProlaboreRequest) -> dict:
    result = engine.calc_prolabore(
        valor_bruto=req.valor_bruto,
        regime=req.regime,
        num_dependentes=req.num_dependentes,
        pensao_alimenticia=req.pensao_alimenticia,
    )
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/comparativo-regimes")
def comparativo_regimes(req: ComparativoRegimesRequest) -> dict:
    return engine.calc_comparativo(**req.model_dump())


@router.post("/rescisao")
def rescisao(req: RescisaoRequest) -> dict:
    result = engine.calc_rescisao(**req.model_dump())
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/decimo-terceiro")
def decimo_terceiro(req: DecimoTerceiroRequest) -> dict:
    return engine.calc_decimo_terceiro(**req.model_dump())


@router.post("/ferias")
def ferias(req: FeriasRequest) -> dict:
    return engine.calc_ferias(**req.model_dump())


@router.post("/hora-extra")
def hora_extra(req: HoraExtraRequest) -> dict:
    return engine.calc_hora_extra(**req.model_dump())


@router.post("/folha-batch")
def folha_batch(req: FolhaBatchRequest) -> dict:
    payload = req.model_dump()
    result = engine.calc_folha_batch(
        empregados=payload["empregados"],
        regime=payload["regime"],
        competencia=payload.get("competencia"),
    )
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/distribuicao-lucros")
def distribuicao_lucros(req: DistribuicaoLucrosRequest) -> dict:
    result = engine.calc_distribuicao_lucros(**req.model_dump())
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/irpf")
def irpf_integrado(req: IRPFRequest) -> dict:
    payload = req.model_dump()
    result = engine.calc_irpf_integrado(**payload)
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/mei/resumo")
def mei_resumo(req: MEIResumoRequest) -> dict:
    """MEI completo: DAS + faturamento + obrigações + alertas."""
    result = engine.resumo_mei(**req.model_dump())
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/darf/consultar")
def darf_consultar(req: DarfBuscaRequest) -> dict:
    return engine.darf_consultar(req.texto)


@router.post("/darf/buscar")
def darf_buscar(req: DarfBuscaRequest) -> dict:
    return engine.darf_buscar(req.texto)


@router.post("/darf/regime")
def darf_regime(req: DarfRegimeRequest) -> dict:
    return engine.darf_listar_regime(req.regime)


@router.post("/lucro-presumido")
def lucro_presumido(req: LucroPresumidoRequest) -> dict:
    """Lucro Presumido — apuração trimestral (IRPJ + CSLL + PIS + COFINS)."""
    result = engine.calc_lucro_presumido(**req.model_dump())
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/lucro-real")
def lucro_real(req: LucroRealRequest) -> dict:
    """Lucro Real — LALUR + compensação de prejuízo (30%) + PIS/COFINS não-cumulativo."""
    result = engine.calc_lucro_real(**req.model_dump())
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/icms/difal")
def difal(req: DIFALRequest) -> dict:
    """DIFAL ICMS — EC 87/2015 + LC 190/2022."""
    return engine.calc_difal(**req.model_dump())


@router.post("/icms/st")
def icms_st(req: ICMSSTRequest) -> dict:
    """ICMS-ST — Substituição Tributária."""
    result = engine.calc_icms_st(**req.model_dump())
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/iss")
def iss(req: ISSRequest) -> dict:
    """ISS sobre serviço — LC 116/2003."""
    result = engine.calc_iss(**req.model_dump())
    if "erro" in result and result.get("verificar_legislacao_municipal") is not True:
        # Município não encontrado retorna sugestões + erro mas é resposta útil
        # Apenas se não tiver indicador de "verificar" levantamos 422
        if "Município" not in result.get("erro", ""):
            raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/iss/buscar-municipio")
def buscar_municipio(req: MunicipioBuscaRequest) -> dict:
    return engine.buscar_municipio_iss(req.texto)


@router.post("/recuperacao/tema-69")
def tema_69(req: Tema69Request) -> dict:
    """STF Tema 69 — exclusão do ICMS da base PIS/COFINS."""
    payload = req.model_dump()
    result = engine.calc_tema_69(
        operacoes=payload["operacoes"],
        tem_acao_pre_15_03_2017=payload["tem_acao_pre_15_03_2017"],
    )
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/recuperacao/prescricao")
def prescricao(req: PrescricaoRequest) -> dict:
    """Prescrição quinquenal LC 118/2005."""
    result = engine.verificar_prescricao(
        data_pagamento=req.data_pagamento,
        data_referencia=req.data_referencia,
    )
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/recuperacao/tema-779")
def tema_779(req: Tema779Request) -> dict:
    """STJ Tema 779 — conceito amplo de insumo (PIS/COFINS Lucro Real)."""
    result = engine.calc_tema_779(insumos=[i.model_dump() for i in req.insumos])
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/recuperacao/perdcomp-minuta")
def perdcomp_minuta(req: PerDcompMinutaRequest) -> dict:
    """Gera minuta da memória de cálculo PER/DCOMP a partir do template RRT."""
    result = engine.gerar_minuta_perdcomp(**req.model_dump())
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/cbs-ibs")
def cbs_ibs(req: CBSIBSRequest) -> dict:
    """Reforma Tributária — operação isolada num ano específico (2026-2033)."""
    result = engine.calc_cbs_ibs(**req.model_dump())
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/cbs-ibs/projecao")
def cbs_ibs_projecao(req: CBSIBSProjecaoRequest) -> dict:
    """Reforma Tributária — projeção ano-a-ano 2026-2033."""
    projecao = engine.projecao_cbs_ibs(**req.model_dump())
    return {"projecao": projecao}
