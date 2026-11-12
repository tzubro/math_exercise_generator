import sqlite3
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from ..db import get_connection


router = APIRouter(prefix="/api/images", tags=["images"])


def database_connection():
    with get_connection() as connection:
        yield connection


@router.get("/{image_id}")
def get_image(
    image_id: UUID,
    connection: sqlite3.Connection = Depends(database_connection),
) -> Response:
    row = connection.execute(
        "SELECT media_type, content FROM images WHERE id = ?", (str(image_id),)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return Response(
        content=row["content"],
        media_type=row["media_type"],
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )
