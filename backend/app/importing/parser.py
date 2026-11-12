import zipfile
from io import BytesIO

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from ..models import ExerciseCreate, ImportParseResult
from .numbering import DocxNumbering, NUMBERED_TASK
from .ollama_parser import OllamaParseError, parse_tasks_with_ollama


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_DOCX_EXPANDED_BYTES = 100 * 1024 * 1024
MAX_DOCX_ENTRIES = 10_000
MAX_PDF_PAGES = 100
MAX_IMPORTED_DRAFTS = 100

def extract_docx_text(content: bytes) -> list[str]:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            if len(archive.infolist()) > MAX_DOCX_ENTRIES:
                raise ValueError("The DOCX file contains too many internal entries.")
            if sum(item.file_size for item in archive.infolist()) > MAX_DOCX_EXPANDED_BYTES:
                raise ValueError("The DOCX file expands beyond the supported size.")
    except zipfile.BadZipFile as error:
        raise ValueError("The file is not a valid DOCX document.") from error

    try:
        document = Document(BytesIO(content))
    except (PackageNotFoundError, zipfile.BadZipFile) as error:
        raise ValueError("The file is not a valid DOCX document.") from error

    numbering = DocxNumbering(document)

    def paragraph_text(paragraph: Paragraph) -> str:
        text = paragraph.text.strip()
        if not text:
            return ""
        marker = numbering.marker_for(paragraph)
        if marker and not NUMBERED_TASK.match(text):
            return f"{marker}{text}"
        return text

    paragraphs: list[str] = []
    for block in document.iter_inner_content():
        if isinstance(block, Paragraph):
            text = paragraph_text(block)
            if text:
                paragraphs.append(text)
        elif isinstance(block, Table):
            for row in block.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        text = paragraph_text(paragraph)
                        if text:
                            paragraphs.append(text)
    return [paragraph for paragraph in paragraphs if paragraph]


def extract_pdf_text(content: bytes) -> tuple[list[str], list[str]]:
    try:
        reader = PdfReader(BytesIO(content), strict=False)
    except PdfReadError as error:
        raise ValueError("The file is not a readable PDF.") from error

    if reader.is_encrypted:
        raise ValueError("Password-protected PDFs are not supported.")
    if len(reader.pages) > MAX_PDF_PAGES:
        raise ValueError(f"PDFs are limited to {MAX_PDF_PAGES} pages.")

    paragraphs: list[str] = []
    pages_without_text = 0
    for page in reader.pages:
        page_text = page.extract_text() or ""
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        if not lines:
            pages_without_text += 1
        paragraphs.extend(lines)

    warnings = []
    if pages_without_text:
        warnings.append(
            f"{pages_without_text} page(s) had no extractable text; scanned pages need OCR."
        )
    return paragraphs, warnings


def split_tasks(paragraphs: list[str]) -> list[str]:
    tasks: list[list[str]] = []
    for paragraph in paragraphs:
        match = NUMBERED_TASK.match(paragraph)
        if match:
            question = paragraph[match.end():].strip()
            tasks.append([question] if question else [])
        elif tasks:
            tasks[-1].append(paragraph)
    return ["\n".join(lines).strip() for lines in tasks if "\n".join(lines).strip()]


def parse_upload(
    filename: str,
    content: bytes,
    extension: str,
    use_ollama: bool = True,
) -> ImportParseResult:
    warnings = [
        "Imported questions are drafts. Review text, numbering, diagrams, and math notation before saving."
    ]

    if extension == ".docx":
        paragraphs = extract_docx_text(content)
        warnings.append(
            "Embedded images and equation objects may not be represented in extracted text."
        )
    else:
        paragraphs, pdf_warnings = extract_pdf_text(content)
        warnings.extend(pdf_warnings)
        warnings.append(
            "Text-based PDF extraction may reorder columns or omit equation formatting and diagrams."
        )

    if use_ollama and any(NUMBERED_TASK.match(paragraph) for paragraph in paragraphs):
        try:
            task_texts, model = parse_tasks_with_ollama(paragraphs)
            warnings.append(
                f"Organized numbered question paragraphs with local Ollama model "
                f"'{model}'. Original text was preserved; review every draft before saving."
            )
        except OllamaParseError as error:
            task_texts = split_tasks(paragraphs)
            warnings.append(
                f"Local Ollama parsing could not be completed ({error}); "
                "used numbered-text parsing instead."
            )
    else:
        task_texts = split_tasks(paragraphs)
    if not task_texts:
        warnings.append(
            'No numbered questions were found. Only entries starting with a number '
            'such as "1." or "2)" are imported; unnumbered text is ignored.'
        )
    if len(task_texts) > MAX_IMPORTED_DRAFTS:
        task_texts = task_texts[:MAX_IMPORTED_DRAFTS]
        warnings.append(
            f"Only the first {MAX_IMPORTED_DRAFTS} candidate questions are shown."
        )

    drafts = [
        ExerciseCreate(
            title=f"Imported exercise {number}",
            prompt=task_text,
            topic="Uncategorized",
            age_min=10,
            age_max=15,
            difficulty="medium",
            points=1,
            solution=None,
            tags=["imported"],
        )
        for number, task_text in enumerate(task_texts, start=1)
    ]
    return ImportParseResult(filename=filename, drafts=drafts, warnings=warnings)
