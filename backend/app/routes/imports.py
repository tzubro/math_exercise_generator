import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from ..importing.parser import MAX_UPLOAD_BYTES, parse_upload
from ..models import ImportParseResult


router = APIRouter(prefix="/api/imports", tags=["imports"])
SUPPORTED_EXTENSIONS = {".docx", ".pdf"}


@router.post("/parse", response_model=ImportParseResult)
async def parse_uploaded_test(
    file: UploadFile = File(...),
    use_ollama: bool = Form(True),
) -> ImportParseResult:
    filename = file.filename or ""
    extension = filename.lower().rsplit(".", maxsplit=1)
    extension = f".{extension[-1]}" if len(extension) > 1 else ""
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a DOCX or PDF file.",
        )

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Files are limited to {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
    if extension == ".pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The file is not a valid PDF.")
    if extension == ".docx" and not content.startswith(b"PK"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The file is not a valid DOCX.")

    try:
        return await asyncio.to_thread(
            parse_upload, filename, content, extension, use_ollama
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
