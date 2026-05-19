"""CV upload endpoint — accepts PDF or DOCX, extracts text, saves as cv.txt."""
import io
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from ..config import settings

router = APIRouter(prefix="/api/cv", tags=["cv"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_CV_BYTES = 10 * 1024 * 1024  # 10 MB


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise HTTPException(500, "pypdf not installed")
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError:
        raise HTTPException(500, "python-docx not installed")
    doc = Document(io.BytesIO(data))
    parts = []
    for element in doc.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag
        if tag == "p":
            text = "".join(t.text or "" for t in element.iter() if t.tag.endswith("}t"))
            if text.strip():
                parts.append(text)
        elif tag == "tbl":
            for row in element.iter():
                if not row.tag.endswith("}tr"):
                    continue
                cells = []
                for cell in row.iter():
                    if not cell.tag.endswith("}tc"):
                        continue
                    cell_text = "".join(t.text or "" for t in cell.iter() if t.tag.endswith("}t"))
                    if cell_text.strip():
                        cells.append(cell_text.strip())
                if cells:
                    parts.append("  ".join(cells))
    return "\n".join(parts).strip()


def _cv_path() -> Path:
    p = Path(settings.cv_path)
    if not p.is_absolute():
        p = Path(__file__).parent.parent.parent / settings.cv_path
    return p


@router.post("/upload")
async def upload_cv(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Only .pdf and .docx files are supported")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_CV_BYTES:
        raise HTTPException(413, "File too large — maximum size is 10 MB")

    if suffix == ".pdf":
        text = _extract_pdf(data)
    else:
        text = _extract_docx(data)

    if not text:
        raise HTTPException(
            422,
            "No text could be extracted — make sure the file contains readable text (not a scanned image)",
        )

    _cv_path().write_text(text, encoding="utf-8")

    return {
        "filename": file.filename,
        "chars": len(text),
        "words": len(text.split()),
    }


@router.get("/status")
def cv_status():
    text = settings.get_cv_text()
    return {
        "loaded": bool(text),
        "chars": len(text),
        "words": len(text.split()) if text else 0,
    }
