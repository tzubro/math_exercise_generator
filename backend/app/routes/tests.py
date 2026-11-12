import json
import os
import re
import sqlite3
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..db import get_connection
from ..models import Exercise, Test, TestCreate, TestExerciseSnapshot


router = APIRouter(prefix="/api/tests", tags=["tests"])


def database_connection():
    with get_connection() as connection:
        yield connection


def row_to_test(connection: sqlite3.Connection, test_row: sqlite3.Row) -> Test:
    rows = connection.execute(
        """
        SELECT snapshot_json FROM test_exercises
        WHERE test_id = ? ORDER BY position
        """,
        (test_row["id"],),
    ).fetchall()
    return Test(
        id=UUID(test_row["id"]),
        title=test_row["title"],
        exercises=[
            TestExerciseSnapshot.model_validate(json.loads(row["snapshot_json"]))
            for row in rows
        ],
    )


@router.post("", response_model=Test, status_code=status.HTTP_201_CREATED)
def create_test(
    test_input: TestCreate,
    connection: sqlite3.Connection = Depends(database_connection),
) -> Test:
    snapshots: list[TestExerciseSnapshot] = []
    for exercise_id in test_input.exercise_ids:
        row = connection.execute(
            "SELECT * FROM exercises WHERE id = ?", (str(exercise_id),)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exercise {exercise_id} not found",
            )
        source = Exercise(
            id=UUID(row["id"]),
            title=row["title"],
            prompt=row["prompt"],
            topic=row["topic"],
            age_min=row["age_min"],
            age_max=row["age_max"],
            exercise_type=row["exercise_type"],
            options=json.loads(row["options"]),
            correct_option=row["correct_option"],
            difficulty=row["difficulty"],
            points=row["points"],
            solution=row["solution"],
            tags=json.loads(row["tags"]),
            image_id=UUID(row["image_id"]) if row["image_id"] else None,
        )
        snapshots.append(
            TestExerciseSnapshot(
                source_exercise_id=source.id,
                **source.model_dump(exclude={"id"}),
            )
        )

    test_id = uuid4()
    connection.execute(
        "INSERT INTO tests (id, title) VALUES (?, ?)",
        (str(test_id), test_input.title),
    )
    connection.executemany(
        """
        INSERT INTO test_exercises (test_id, position, source_exercise_id, snapshot_json)
        VALUES (?, ?, ?, ?)
        """,
        [
            (
                str(test_id),
                position,
                str(snapshot.source_exercise_id),
                snapshot.model_dump_json(),
            )
            for position, snapshot in enumerate(snapshots)
        ],
    )
    return Test(id=test_id, title=test_input.title, exercises=snapshots)


@router.get("/{test_id}", response_model=Test)
def get_test(
    test_id: UUID,
    connection: sqlite3.Connection = Depends(database_connection),
) -> Test:
    row = connection.execute(
        "SELECT id, title FROM tests WHERE id = ?", (str(test_id),)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    return row_to_test(connection, row)


def build_test_document(
    test: Test,
    include_solutions: bool,
    connection: sqlite3.Connection,
) -> bytes:
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    normal_style = document.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(12)

    heading = document.add_heading(test.title, level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in heading.runs:
        run.font.size = Pt(14)
    header = document.add_table(rows=1, cols=3)
    header.autofit = False
    available_width = (
        section.page_width - section.left_margin - section.right_margin
    )
    column_widths = [
        int(available_width * 0.58),
        int(available_width * 0.18),
        int(available_width * 0.24),
    ]
    table_width = header._tbl.tblPr.find(qn("w:tblW"))
    if table_width is None:
        table_width = OxmlElement("w:tblW")
        header._tbl.tblPr.insert(0, table_width)
    table_width.set(qn("w:w"), str(int(available_width / 635)))
    table_width.set(qn("w:type"), "dxa")
    for column, width in zip(header.columns, column_widths):
        column.width = width
    for cell, label, width in zip(
        header.rows[0].cells,
        ("Meno a priezvisko:", "Dátum:", "Hodnotenie:"),
        column_widths,
    ):
        cell.width = width
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(12)
        paragraph.add_run(label).font.size = Pt(10)

    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), "nil")
        borders.append(border)
    header._tbl.tblPr.append(borders)

    for number, exercise in enumerate(test.exercises, start=1):
        question = document.add_paragraph()
        number_run = question.add_run(f"{number}. ")
        number_run.bold = True
        number_run.font.size = Pt(12)
        prompt_run = question.add_run(exercise.prompt)
        prompt_run.font.size = Pt(12)
        if exercise.exercise_type == "multiple_choice":
            for index, option in enumerate(exercise.options):
                option_paragraph = document.add_paragraph(
                    f"{chr(ord('a') + index)}) {option}"
                )
                for run in option_paragraph.runs:
                    run.font.size = Pt(12)
        if exercise.image_id:
            image_row = connection.execute(
                "SELECT content FROM images WHERE id = ?", (str(exercise.image_id),)
            ).fetchone()
            if image_row is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="A saved test image is missing from the image store.",
                )
            document.add_picture(BytesIO(image_row["content"]), width=Inches(5.8))
        document.add_paragraph("")

    if include_solutions:
        document.add_page_break()
        document.add_heading("Answer key", level=0)
        for number, exercise in enumerate(test.exercises, start=1):
            answer = document.add_paragraph()
            number_run = answer.add_run(f"{number}. ")
            number_run.bold = True
            number_run.font.size = Pt(12)
            if exercise.exercise_type == "multiple_choice":
                correct_text = (
                    f"{chr(ord('a') + exercise.correct_option)}) "
                    f"{exercise.options[exercise.correct_option]}"
                )
                answer.add_run(f"Correct answer: {correct_text}")
                if exercise.solution:
                    document.add_paragraph(f"Explanation: {exercise.solution}")
            else:
                answer.add_run(exercise.solution or "No solution was provided.")

    output = BytesIO()
    document.save(output)
    return output.getvalue()


def find_libreoffice() -> str | None:
    for command in ("soffice", "soffice.com", "libreoffice"):
        executable = shutil.which(command)
        if executable:
            return executable
    if os.name == "nt":
        for program_dir in (
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        ):
            for executable_name in ("soffice.com", "soffice.exe"):
                candidate = program_dir / "LibreOffice" / "program" / executable_name
                if candidate.is_file():
                    return str(candidate)
    return None


def convert_docx_to_pdf(docx_bytes: bytes) -> bytes:
    libreoffice = find_libreoffice()
    if libreoffice is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF export requires LibreOffice. Install LibreOffice and restart the app.",
        )

    with tempfile.TemporaryDirectory(prefix="math-test-") as temp_dir:
        directory = Path(temp_dir)
        input_path = directory / "test.docx"
        output_path = directory / "test.pdf"
        input_path.write_bytes(docx_bytes)
        try:
            completed = subprocess.run(
                [
                    libreoffice,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(directory),
                    str(input_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LibreOffice timed out while creating the PDF.",
            ) from error
        if completed.returncode != 0 or not output_path.is_file():
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LibreOffice could not create the PDF. {detail}".strip(),
            )
        return output_path.read_bytes()


def safe_filename(title: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()
    return normalized or "math-test"


@router.post("/{test_id}/export")
def export_test(
    test_id: UUID,
    format: str = Query(pattern="^(docx|pdf)$"),
    include_solutions: bool = False,
    connection: sqlite3.Connection = Depends(database_connection),
) -> Response:
    row = connection.execute(
        "SELECT id, title FROM tests WHERE id = ?", (str(test_id),)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    test = row_to_test(connection, row)
    document_bytes = build_test_document(test, include_solutions, connection)
    if format == "pdf":
        content = convert_docx_to_pdf(document_bytes)
        media_type = "application/pdf"
        extension = "pdf"
    else:
        content = document_bytes
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        extension = "docx"
    filename = f"{safe_filename(test.title)}.{extension}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
