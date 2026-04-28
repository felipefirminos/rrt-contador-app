from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.calculators import (
    CBSIBSProjecaoRequest,
    CBSIBSRequest,
    ComparativoRegimesRequest,
    DecimoTerceiroRequest,
    DistribuicaoLucrosRequest,
    FeriasRequest,
    FolhaBatchRequest,
    HoraExtraRequest,
    IRPFRequest,
    ProlaboreRequest,
    RescisaoRequest,
    SimplesDASRequest,
    SugerirAnexoRequest,
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
