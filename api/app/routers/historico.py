"""Histórico por cliente/CNPJ + análises e sugestões proativas.

Persistência via SQLite (services.db). Análises (detector_padroes,
sugestoes_proativas) ficam stateless e recebem listas de interações.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from app.schemas.historico import (
    BuscaTagRequest,
    FeedbackRequest,
    PadroesRequest,
    RegistrarRequest,
    SugestoesRequest,
)
from app.services import db, engine


router = APIRouter(prefix="/historico", tags=["historico"])


@router.post("/registrar")
def registrar(req: RegistrarRequest) -> dict:
    result = db.registrar(
        cnpj=req.cnpj, texto=req.texto,
        classificacao=req.classificacao,
        resultado=req.resultado,
        tags=req.tags, origem=req.origem,
    )
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result


@router.post("/feedback")
def feedback(req: FeedbackRequest) -> dict:
    result = db.registrar_feedback(
        interacao_id=req.interacao_id,
        avaliacao=req.avaliacao,
        correcao=req.correcao,
    )
    if "erro" in result:
        raise HTTPException(
            status_code=404 if "não encontrada" in result["erro"] else 422,
            detail=result["erro"],
        )
    return result


@router.get("/cliente/{cnpj}")
def listar_cliente(cnpj: str, limite: int = 100) -> dict:
    interacoes = db.listar_por_cliente(cnpj, limite=min(limite, 500))
    return {"cnpj": cnpj, "total": len(interacoes), "interacoes": interacoes}


@router.post("/buscar-tag")
def buscar_tag(req: BuscaTagRequest) -> dict:
    matches = db.buscar_por_tag(req.tag, cnpj=req.cnpj, limite=req.limite)
    return {
        "query": req.tag, "cnpj": req.cnpj,
        "total": len(matches), "interacoes": matches,
    }


@router.get("/estatisticas")
def estatisticas(cnpj: Optional[str] = None) -> dict:
    return db.estatisticas(cnpj)


@router.post("/padroes")
def padroes(req: PadroesRequest) -> dict:
    """Detecta sazonalidade, top temas, padrões de correção e clusters."""
    interacoes = db.todas_interacoes(req.cnpj)
    if not interacoes:
        return {"cnpj": req.cnpj, "total": 0, "mensagem": "Sem interações para analisar"}

    insights = engine._det_gerar_insights(interacoes)
    return {"cnpj": req.cnpj, "total": len(interacoes), **insights}


@router.post("/sugestoes")
def sugestoes(req: SugestoesRequest) -> dict:
    """Sugestões proativas: alertas de prazo + lembretes + antecipações."""
    interacoes = db.todas_interacoes(req.cnpj) if req.cnpj else []
    padroes_correcao = engine._det_padroes_correcao(interacoes) if interacoes else {}
    return engine._sug_consolidadas(
        interacoes_cliente=interacoes,
        padroes_correcao=padroes_correcao,
        regime=req.regime,
        data_referencia=req.data_referencia,
        dias_antecedencia=req.dias_antecedencia,
    )
