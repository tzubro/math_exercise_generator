import json
import sqlite3
from uuid import UUID, uuid4
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from PIL import Image, UnidentifiedImageError

from ..db import get_connection
from ..models import (
    Difficulty,
    Exercise,
    ExerciseBulkCreate,
    ExerciseCreate,
    ExerciseFields,
    ExerciseUpdate,
)


router = APIRouter(prefix="/api/exercises", tags=["exercises"])
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
IMAGE_MEDIA_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png"}


def database_connection():
    with get_connection() as connection:
        yield connection


def row_to_exercise(row: sqlite3.Row) -> Exercise:
    return Exercise(
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


def insert_exercise(connection: sqlite3.Connection, exercise: Exercise) -> None:
    connection.execute(
        """
        INSERT INTO exercises (
            id, title, prompt, topic, age_min, age_max,
            exercise_type, options, correct_option, difficulty, points,
            solution, tags, image_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(exercise.id),
            exercise.title,
            exercise.prompt,
            exercise.topic,
            exercise.age_min,
            exercise.age_max,
            exercise.exercise_type,
            json.dumps(exercise.options, ensure_ascii=False),
            exercise.correct_option,
            exercise.difficulty,
            exercise.points,
            exercise.solution,
            json.dumps(exercise.tags, ensure_ascii=False),
            str(exercise.image_id) if exercise.image_id else None,
        ),
    )


@router.get("", response_model=list[Exercise])
def list_exercises(
    q: str | None = Query(default=None, max_length=200),
    topic: str | None = Query(default=None, max_length=100),
    age: int | None = Query(default=None, ge=10, le=15),
    difficulty: Difficulty | None = None,
    connection: sqlite3.Connection = Depends(database_connection),
) -> list[Exercise]:
    filters: list[str] = []
    parameters: list[object] = []
    if q and q.strip():
        search = f"%{q.strip()}%"
        filters.append(
            "(title LIKE ? COLLATE NOCASE OR prompt LIKE ? COLLATE NOCASE "
            "OR topic LIKE ? COLLATE NOCASE OR tags LIKE ? COLLATE NOCASE "
            "OR options LIKE ? COLLATE NOCASE)"
        )
        parameters.extend([search] * 5)
    if topic and topic.strip():
        filters.append("topic = ? COLLATE NOCASE")
        parameters.append(topic.strip())
    if age is not None:
        filters.append("age_min <= ? AND age_max >= ?")
        parameters.extend([age, age])
    if difficulty is not None:
        filters.append("difficulty = ?")
        parameters.append(difficulty)

    where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""
    rows = connection.execute(
        f"SELECT * FROM exercises{where_clause} ORDER BY title COLLATE NOCASE, id",
        parameters,
    ).fetchall()
    return [row_to_exercise(row) for row in rows]


@router.post("", response_model=Exercise, status_code=status.HTTP_201_CREATED)
def create_exercise(
    exercise_input: ExerciseCreate,
    connection: sqlite3.Connection = Depends(database_connection),
) -> Exercise:
    exercise = Exercise(id=uuid4(), **exercise_input.model_dump())
    insert_exercise(connection, exercise)
    return exercise


@router.post("/bulk", response_model=list[Exercise], status_code=status.HTTP_201_CREATED)
def create_exercises(
    exercise_input: ExerciseBulkCreate,
    connection: sqlite3.Connection = Depends(database_connection),
) -> list[Exercise]:
    exercises = [
        Exercise(id=uuid4(), **item.model_dump())
        for item in exercise_input.exercises
    ]
    for exercise in exercises:
        insert_exercise(connection, exercise)
    return exercises


@router.get("/{exercise_id}", response_model=Exercise)
def get_exercise(
    exercise_id: UUID,
    connection: sqlite3.Connection = Depends(database_connection),
) -> Exercise:
    row = connection.execute(
        "SELECT * FROM exercises WHERE id = ?", (str(exercise_id),)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return row_to_exercise(row)


@router.patch("/{exercise_id}", response_model=Exercise)
def update_exercise(
    exercise_id: UUID,
    exercise_update: ExerciseUpdate,
    connection: sqlite3.Connection = Depends(database_connection),
) -> Exercise:
    row = connection.execute(
        "SELECT * FROM exercises WHERE id = ?", (str(exercise_id),)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    current = row_to_exercise(row)
    updated_fields = current.model_dump(exclude={"id", "image_id"})
    updated_fields.update(exercise_update.model_dump(exclude_unset=True))
    validated_fields = ExerciseFields.model_validate(updated_fields)
    exercise = Exercise(
        id=exercise_id,
        image_id=current.image_id,
        **validated_fields.model_dump(),
    )
    connection.execute(
        """
        UPDATE exercises SET
            title = ?, prompt = ?, topic = ?, age_min = ?, age_max = ?,
            exercise_type = ?, options = ?, correct_option = ?,
            difficulty = ?, points = ?, solution = ?, tags = ?
        WHERE id = ?
        """,
        (
            exercise.title,
            exercise.prompt,
            exercise.topic,
            exercise.age_min,
            exercise.age_max,
            exercise.exercise_type,
            json.dumps(exercise.options, ensure_ascii=False),
            exercise.correct_option,
            exercise.difficulty,
            exercise.points,
            exercise.solution,
            json.dumps(exercise.tags, ensure_ascii=False),
            str(exercise.id),
        ),
    )
    return exercise


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(
    exercise_id: UUID,
    connection: sqlite3.Connection = Depends(database_connection),
) -> Response:
    cursor = connection.execute("DELETE FROM exercises WHERE id = ?", (str(exercise_id),))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{exercise_id}/image", response_model=Exercise)
async def upload_exercise_image(
    exercise_id: UUID,
    file: UploadFile = File(...),
    connection: sqlite3.Connection = Depends(database_connection),
) -> Exercise:
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Images are limited to 5 MB.",
        )
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The image is empty.")

    try:
        with Image.open(BytesIO(content)) as image:
            image_format = image.format
            width, height = image.size
            if width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Image dimensions are too large.",
                )
            if image_format not in IMAGE_MEDIA_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Use a JPEG or PNG image.",
                )
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid image.",
        ) from error

    row = connection.execute(
        "SELECT * FROM exercises WHERE id = ?", (str(exercise_id),)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    image_id = uuid4()
    connection.execute(
        "INSERT INTO images (id, media_type, content) VALUES (?, ?, ?)",
        (str(image_id), IMAGE_MEDIA_TYPES[image_format], content),
    )
    connection.execute(
        "UPDATE exercises SET image_id = ? WHERE id = ?",
        (str(image_id), str(exercise_id)),
    )
    updated = connection.execute(
        "SELECT * FROM exercises WHERE id = ?", (str(exercise_id),)
    ).fetchone()
    return row_to_exercise(updated)


@router.delete("/{exercise_id}/image", status_code=status.HTTP_204_NO_CONTENT)
def remove_exercise_image(
    exercise_id: UUID,
    connection: sqlite3.Connection = Depends(database_connection),
) -> Response:
    cursor = connection.execute(
        "UPDATE exercises SET image_id = NULL WHERE id = ?", (str(exercise_id),)
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
