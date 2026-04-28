"""Parser endpoints — DAS PDF + NF-e/NFS-e XML.

PDFs são processados in-memory via pdfplumber (já em requirements.txt).
XMLs são lidos como string e despachados pelo `processar_xml` que detecta
NF-e / NFC-e / NFS-e automaticamente.
"""
from __future__ import annotations

import sys

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import SCRIPTS_DIR


if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


from parser_das_pdf import extrair_dados_das, processar_lote_das  # noqa: E402
from parser_xml_nfe import processar_xml  # noqa: E402


router = APIRouter(prefix="/parser", tags=["parsers"])


def _extract_pdf_text(content: bytes) -> str:
    """Tenta extrair texto via pdfplumber; falha se PDF não tiver texto."""
    try:
        import pdfplumber  # type: ignore
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="pdfplumber não instalado. Rode: pip install pdfplumber",
        ) from exc

    import io
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages_text = []
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t.strip():
                    pages_text.append(t)
            return "\n".join(pages_text)
    except Exception as exc:  # pdfplumber raises various exceptions
        raise HTTPException(
            status_code=400,
            detail=f"Falha ao extrair texto do PDF: {exc}",
        ) from exc


@router.post("/das-pdf")
async def parse_das_pdf(file: UploadFile = File(..., description="Guia DAS em PDF")) -> dict:
    """Extrai dados estruturados de uma guia DAS (Simples ou MEI)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos .pdf")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF acima de 10MB")

    texto = _extract_pdf_text(content)
    if not texto.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "PDF sem texto extraível (provavelmente imagem/escaneado). "
                "Use um PDF nativo gerado pela RFB."
            ),
        )
    return extrair_dados_das(texto)


@router.post("/das-pdf-batch")
async def parse_das_pdf_batch(
    files: list[UploadFile] = File(..., description="Múltiplas guias DAS"),
) -> dict:
    """Lote de DAS — útil para apuração mensal de carteira de clientes."""
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Máximo 50 arquivos por lote")

    textos: list[str] = []
    nomes: list[str] = []
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            continue
        content = await f.read()
        if not content:
            continue
        textos.append(_extract_pdf_text(content))
        nomes.append(f.filename)

    if not textos:
        raise HTTPException(status_code=400, detail="Nenhum PDF válido no lote")

    result = processar_lote_das(textos)
    # Anexa nomes dos arquivos aos resultados individuais para rastreamento
    for i, r in enumerate(result.get("resultados", [])):
        if i < len(nomes):
            r["arquivo"] = nomes[i]
    return result


@router.post("/xml-fiscal")
async def parse_xml_fiscal(
    file: UploadFile = File(..., description="NF-e, NFC-e ou NFS-e em XML"),
) -> dict:
    """Detecta tipo (NF-e/NFC-e/NFS-e) e extrai estrutura completa."""
    if not file.filename or not file.filename.lower().endswith((".xml", ".nfe", ".nfse")):
        raise HTTPException(status_code=400, detail="Apenas .xml/.nfe/.nfse")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="XML acima de 5MB")

    try:
        xml_string = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            xml_string = content.decode("latin-1")
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail=f"Encoding não suportado: {exc}",
            ) from exc

    return processar_xml(xml_string)
