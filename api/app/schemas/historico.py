from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RegistrarRequest(BaseModel):
    cnpj: str = Field(..., min_length=11, description="CNPJ (com ou sem máscara)")
    texto: str = Field(..., min_length=1, max_length=4000)
    classificacao: Optional[dict[str, Any]] = Field(
        None,
        description="Ex: {fluxo: 'Trabalhista', skill: 'rrt-group-contador', score: 0.95}",
    )
    resultado: Optional[dict[str, Any]] = Field(
        None,
        description="Resultado bruto da calc invocada (irá para o histórico)",
    )
    tags: list[str] = Field(default_factory=list, description="ex: ['rescisão','484-A']")
    origem: Literal["direto", "gestta", "whatsapp", "api"] = "direto"


class FeedbackRequest(BaseModel):
    interacao_id: str = Field(..., description="ID retornado por /registrar (CNPJ_NNNNNN)")
    avaliacao: Literal["aprovado", "rejeitado", "ajustado"]
    correcao: Optional[str] = Field(
        None, description="Texto da correção (obrigatório se avaliação='ajustado')",
    )


class BuscaTagRequest(BaseModel):
    tag: str = Field(..., min_length=1)
    cnpj: Optional[str] = Field(None, description="Restringe a um cliente (opcional)")
    limite: int = Field(50, ge=1, le=500)


class PadroesRequest(BaseModel):
    cnpj: Optional[str] = Field(
        None,
        description="None = análise global; senão, cliente específico",
    )


class SugestoesRequest(BaseModel):
    cnpj: Optional[str] = None
    regime: Optional[Literal[
        "simples", "presumido", "lucro_real", "mei",
    ]] = None
    data_referencia: Optional[str] = Field(None, description="YYYY-MM-DD")
    dias_antecedencia: int = Field(7, ge=0, le=60)