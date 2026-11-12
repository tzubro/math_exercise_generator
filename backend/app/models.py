from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Difficulty = Literal["easy", "medium", "hard"]
ExerciseType = Literal["normal", "multiple_choice"]


class ExerciseFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1)
    topic: str = Field(min_length=1, max_length=100)
    age_min: int = Field(ge=10, le=15)
    age_max: int = Field(ge=10, le=15)
    exercise_type: ExerciseType = "normal"
    options: list[str] = Field(default_factory=list, max_length=26)
    correct_option: int | None = Field(default=None, ge=0)
    difficulty: Difficulty
    points: int = Field(ge=0)
    solution: str | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def age_range_is_ordered(self) -> "ExerciseFields":
        if self.age_min > self.age_max:
            raise ValueError("age_min must be less than or equal to age_max")
        if self.exercise_type == "normal":
            if self.options or self.correct_option is not None:
                raise ValueError("Normal exercises cannot have options or a correct option")
        else:
            if len(self.options) < 2 or any(not option for option in self.options):
                raise ValueError("Multiple-choice exercises need at least two non-empty options")
            if self.correct_option is None or self.correct_option >= len(self.options):
                raise ValueError("Select one correct option")
        return self


class Exercise(ExerciseFields):
    id: UUID
    image_id: UUID | None = None


class ExerciseCreate(ExerciseFields):
    pass


class ExerciseBulkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exercises: list[ExerciseCreate] = Field(min_length=1, max_length=100)


class ExerciseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    prompt: str | None = Field(default=None, min_length=1)
    topic: str | None = Field(default=None, min_length=1, max_length=100)
    age_min: int | None = Field(default=None, ge=10, le=15)
    age_max: int | None = Field(default=None, ge=10, le=15)
    exercise_type: ExerciseType | None = None
    options: list[str] | None = Field(default=None, max_length=26)
    correct_option: int | None = Field(default=None, ge=0)
    difficulty: Difficulty | None = None
    points: int | None = Field(default=None, ge=0)
    solution: str | None = None
    tags: list[str] | None = None


class TestExerciseSnapshot(ExerciseFields):
    source_exercise_id: UUID
    image_id: UUID | None = None


class Test(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str = Field(min_length=1, max_length=200)
    exercises: list[TestExerciseSnapshot] = Field(min_length=1)


class TestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    exercise_ids: list[UUID] = Field(min_length=1)

    @field_validator("exercise_ids")
    @classmethod
    def exercise_ids_are_unique(cls, exercise_ids: list[UUID]) -> list[UUID]:
        if len(exercise_ids) != len(set(exercise_ids)):
            raise ValueError("An exercise can only be added once to a test")
        return exercise_ids


class ImportParseResult(BaseModel):
    filename: str
    drafts: list[ExerciseCreate]
    warnings: list[str]


class ApiHealth(BaseModel):
    status: Literal["ok"]
