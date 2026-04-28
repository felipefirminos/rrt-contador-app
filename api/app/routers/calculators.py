from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.calculators import (
    ComparativoRegimesRequest,
    ProlaboreRequest,
    SimplesDASRequest,
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
