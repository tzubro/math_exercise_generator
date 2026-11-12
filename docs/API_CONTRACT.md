# MVP API and data contract

This document is the shared contract for the MVP. JSON field names use
`snake_case`. The local React app and FastAPI server use the same origin; API
routes are under `/api`.

## Data models

### Exercise

An exercise-bank record has these fields:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID string | Assigned by the server |
| `title` | string | Required |
| `prompt` | string | Required exercise text |
| `topic` | string | Required, for example fractions |
| `age_min` | integer | Inclusive; from 10 through 15 |
| `age_max` | integer | Inclusive; from 10 through 15 and not less than `age_min` |
| `exercise_type` | `"normal" \| "multiple_choice"` | Defaults to `normal` |
| `options` | array of strings | Multiple choice requires 2–26 non-empty options |
| `correct_option` | integer or `null` | Zero-based index; required for multiple choice |
| `difficulty` | `"easy" \| "medium" \| "hard"` | Initial MVP scale |
| `points` | integer | Zero or greater |
| `solution` | string or `null` | Optional answer/solution |
| `tags` | array of strings | Empty by default |
| `image_id` | UUID string or `null` | Optional JPEG/PNG image stored by the app |

`ExerciseCreate` contains the exercise content fields; `id` and `image_id` are
server-managed. `exercise_type` defaults to `normal`, `options` to an empty
array, and `correct_option` and `solution` to `null`; `tags` also defaults to an
empty array. A normal exercise must have no options; a multiple-choice exercise
has one required correct option. The UI displays choices with alphabetic labels
(`a)`, `b)`, `c)`, ...). An exercise update is a partial object containing
only fields to change.

### Test

A saved test has `id` (UUID string), `title` (string), and `exercises` (an
ordered array of snapshots). Each `TestExerciseSnapshot` contains all
`Exercise` fields except `id`, plus `source_exercise_id` (the source exercise's
UUID). The array order is the printed test order.

Creating a test sends the title and ordered exercise IDs. The server copies the
current exercise content into snapshots; later edits to the exercise bank must
not alter a saved test.

## MVP endpoints

All successful responses are JSON except document exports.

| Method and path | Request | Response |
| --- | --- | --- |
| `GET /api/health` | None | `{"status":"ok"}` |
| `GET /api/exercises` | Optional `q`, `topic`, `age`, `difficulty` query parameters | Array of `Exercise` (implemented) |
| `POST /api/exercises` | `ExerciseCreate` JSON | Created `Exercise` (implemented) |
| `POST /api/exercises/bulk` | `{"exercises":[ExerciseCreate,...]}` (1–100 items) | Created exercises (implemented) |
| `GET /api/exercises/{id}` | None | `Exercise` (implemented) |
| `PATCH /api/exercises/{id}` | Partial exercise JSON | Updated `Exercise` (implemented) |
| `DELETE /api/exercises/{id}` | None | `204 No Content` (implemented) |
| `PUT /api/exercises/{id}/image` | Multipart `file` field with JPEG/PNG image, max 5 MB | Updated `Exercise` (implemented) |
| `DELETE /api/exercises/{id}/image` | None | `204 No Content` (implemented) |
| `GET /api/images/{image_id}` | None | Image bytes (implemented) |
| `POST /api/tests` | `TestCreate` JSON | Created `Test` with ordered snapshots (implemented) |
| `GET /api/tests/{id}` | None | `Test` (implemented) |
| `POST /api/tests/{id}/export?format=docx\|pdf&include_solutions=false` | None | Downloadable document (implemented) |
| `POST /api/imports/parse` | Multipart `file` field containing DOCX or PDF; optional `use_ollama` boolean (defaults to `true`) | `ImportParseResult` with drafts and warnings (implemented) |

`TestCreate` is:

```json
{
  "title": "Fractions practice",
  "exercise_ids": ["00000000-0000-0000-0000-000000000001"]
}
```

The order of `exercise_ids` determines the order of the snapshots. A missing
resource returns `404`; invalid request data returns FastAPI's standard `422`
validation response. PDF export requires LibreOffice. Imported drafts are not
stored until the teacher selects them and adds them to the bank. Extraction is
text-only; scanned pages need OCR and equation/diagram fidelity is not
guaranteed.
Text entries beginning with a numeric marker such as `1.` or `2)` and
automatically numbered decimal lists in DOCX files are treated as exercise
candidates. Unnumbered headings and text before the first numbered entry are
ignored. Continuation paragraphs after a numbered entry are included in that
candidate until the next numbered entry.
When `use_ollama` is enabled, the server sends extracted paragraph text only to
the local Ollama service at `127.0.0.1:11434`, using
`MATH_TEST_GENERATOR_OLLAMA_MODEL` or `qwen3.5:4b` by default. The model may
organize numbered question paragraphs, but the server validates every returned
paragraph reference against the original text and preserves that text rather
than accepting model-generated exercise content. If Ollama is unavailable,
times out, or returns invalid references, the API reports a warning and uses
the numbered-text parser. The teacher must review all drafts before saving.

Exercise images are kept in SQLite. Replacing or removing an exercise's image
does not remove old image bytes, because saved test snapshots may still refer
to them.

The import response contains `filename`, `drafts` (ExerciseCreate-shaped
objects with placeholder topic/age/difficulty/points), and `warnings`. The UI
requires the teacher to select drafts before saving them into the exercise
bank. At most 100 candidates are returned per upload.

## Module boundaries

- `backend/app/models.py`: canonical backend validation models.
- `backend/app/main.py`: FastAPI application, health endpoint, exercise route
  registration, and serving the compiled frontend.
- `backend/app/db.py`: SQLite connection, schema initialization, and
  user-writable data directory selection.
- `backend/app/routes/exercises.py`: exercise-bank CRUD and filtering endpoints.
- `backend/app/routes/tests.py`: saved test snapshots and document export.
- `backend/app/routes/imports.py`: upload validation and parsing API.
- `backend/app/importing/parser.py`: document text extraction and draft parsing.
- `backend/app/importing/numbering.py`: shared numbered marker and DOCX automatic-list numbering.
- `backend/app/importing/ollama_parser.py`: optional local Ollama paragraph grouping and response validation.
- `frontend/src/types/contracts.ts`: matching TypeScript data shapes.
- `frontend/src/lib/api.ts`: shared browser API client.
- `frontend/src/features/exercises/`: exercise-bank interface.
- `frontend/src/features/tests/`: test composition and export controls.
- `backend/tests/`: focused API and persistence tests.

Keep the database and generated documents in a user-writable data directory,
not inside the installed application. The location and installer behavior can
be decided during the packaging phase.
