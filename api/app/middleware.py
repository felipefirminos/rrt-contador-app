"""Auto-record middleware: grava interação no histórico para qualquer
chamada bem-sucedida em /calc/* quando header `X-Cliente-CNPJ` estiver presente.

Design:
- Opt-in: sem o header, nada acontece
- Apenas /calc/* (parsers e chat ficam de fora)
- Apenas status 2xx
- Best-effort: falha de gravação NUNCA quebra o request
- Tags derivadas do path (/calc/recuperacao/tema-69 → ['recuperacao', 'tema-69'])
- texto vem de `X-Cliente-Texto` (opcional) ou fallback `METHOD path`
"""
from __future__ import annotations

import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_MAX_BODY_BYTES = 64 * 1024  # 64KB cap no resultado armazenado
_PATH_PREFIX = "/calc/"


class AutoRecordMiddleware(BaseHTTPMiddleware):
    """Grava cada call de /calc/* no histórico se X-Cliente-CNPJ estiver presente."""

    async def dispatch(self, request: Request, call_next):
        cnpj = request.headers.get("x-cliente-cnpj")
        path = request.url.path

        # Filtro: só /calc/* com header presente. Tudo o mais passa direto.
        if not cnpj or not path.startswith(_PATH_PREFIX):
            return await call_next(request)

        response = await call_next(request)

        # Só grava em sucesso. Erros (422, 500) não poluem o histórico.
        if response.status_code < 200 or response.status_code >= 300:
            return response

        # BaseHTTPMiddleware exige consumir e re-emitir o body.
        body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            body_chunks.append(chunk)
        body = b"".join(body_chunks)

        new_response = Response(
            content=body,
            status_code=response.status_code,
            media_type=response.media_type,
        )
        # Preserva headers originais EXCETO content-length (recalculado)
        for k, v in response.headers.items():
            if k.lower() != "content-length":
                new_response.headers[k] = v

        # Best-effort recording — qualquer falha aqui não impacta a resposta.
        try:
            self._record(request, path, body, cnpj)
        except Exception:  # noqa: BLE001 — explicit best-effort
            pass

        return new_response

    @staticmethod
    def _record(request: Request, path: str, body: bytes, cnpj: str) -> None:
        # Import dentro do método para evitar circular imports na inicialização
        from app.services import db

        # Resultado: preferimos JSON parseado; senão, truncate textual
        try:
            resultado = json.loads(body[:_MAX_BODY_BYTES])
        except json.JSONDecodeError:
            resultado = {"raw": body[:500].decode("utf-8", errors="replace")}

        # Tags: segmentos do path após /calc/, sem '-' substituído por nada
        # Ex: /calc/recuperacao/tema-69 → ['recuperacao', 'tema-69']
        path_parts = [p for p in path.split("/") if p and p != "calc"]
        tags = [seg.lower() for seg in path_parts]

        texto = (
            request.headers.get("x-cliente-texto")
            or f"{request.method} {path}"
        )[:500]

        db.registrar(
            cnpj=cnpj,
            texto=texto,
            classificacao={"endpoint": path, "method": request.method},
            resultado=resultado,
            tags=tags,
            origem="api",
        )
