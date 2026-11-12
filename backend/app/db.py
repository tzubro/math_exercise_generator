import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def get_data_dir() -> Path:
    configured_dir = os.environ.get("MATH_TEST_GENERATOR_DATA_DIR")
    if configured_dir:
        return Path(configured_dir).expanduser().resolve()

    if os.name == "nt":
        base_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base_dir / "MathTestGenerator"


def get_database_path() -> Path:
    return get_data_dir() / "math_test_generator.sqlite3"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        get_database_path(),
        timeout=10,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                id TEXT PRIMARY KEY,
                media_type TEXT NOT NULL,
                content BLOB NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS exercises (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                prompt TEXT NOT NULL,
                topic TEXT NOT NULL,
                age_min INTEGER NOT NULL CHECK (age_min BETWEEN 10 AND 15),
                age_max INTEGER NOT NULL CHECK (age_max BETWEEN age_min AND 15),
                exercise_type TEXT NOT NULL DEFAULT 'normal',
                options TEXT NOT NULL DEFAULT '[]',
                correct_option INTEGER,
                difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
                points INTEGER NOT NULL CHECK (points >= 0),
                solution TEXT,
                tags TEXT NOT NULL DEFAULT '[]',
                image_id TEXT REFERENCES images(id)
            )
            """
        )
        exercise_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(exercises)").fetchall()
        }
        if "image_id" not in exercise_columns:
            connection.execute(
                "ALTER TABLE exercises ADD COLUMN image_id TEXT REFERENCES images(id)"
            )
        if "exercise_type" not in exercise_columns:
            connection.execute(
                "ALTER TABLE exercises ADD COLUMN exercise_type TEXT NOT NULL DEFAULT 'normal'"
            )
        if "options" not in exercise_columns:
            connection.execute(
                "ALTER TABLE exercises ADD COLUMN options TEXT NOT NULL DEFAULT '[]'"
            )
        if "correct_option" not in exercise_columns:
            connection.execute("ALTER TABLE exercises ADD COLUMN correct_option INTEGER")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tests (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS test_exercises (
                test_id TEXT NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
                position INTEGER NOT NULL CHECK (position >= 0),
                source_exercise_id TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                PRIMARY KEY (test_id, position)
            )
            """
        )
