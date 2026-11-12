from fastapi.testclient import TestClient

from backend.app.main import app


def exercise_data(**overrides):
    data = {
        "title": "Add fractions",
        "prompt": "Calculate 1/2 + 1/4.",
        "topic": "Fractions",
        "age_min": 10,
        "age_max": 12,
        "difficulty": "easy",
        "points": 2,
        "solution": "3/4",
        "tags": ["addition"],
    }
    data.update(overrides)
    return data


def test_exercise_crud_search_and_filters(tmp_path, monkeypatch):
    monkeypatch.setenv("MATH_TEST_GENERATOR_DATA_DIR", str(tmp_path))

    with TestClient(app) as client:
        created_response = client.post("/api/exercises", json=exercise_data())
        assert created_response.status_code == 201
        created = created_response.json()
        assert created["id"]
        assert created["tags"] == ["addition"]

        assert client.get("/api/exercises", params={"q": "fractions"}).json() == [created]
        assert client.get("/api/exercises", params={"age": 11}).json() == [created]
        assert client.get("/api/exercises", params={"age": 14}).json() == []
        assert client.get(
            "/api/exercises", params={"topic": "fractions", "difficulty": "easy"}
        ).json() == [created]

        updated_response = client.patch(
            f"/api/exercises/{created['id']}",
            json={"points": 3, "solution": None, "tags": ["fractions", "practice"]},
        )
        assert updated_response.status_code == 200
        updated = updated_response.json()
        assert updated["points"] == 3
        assert updated["solution"] is None
        assert updated["tags"] == ["fractions", "practice"]

        assert client.get(f"/api/exercises/{created['id']}").json() == updated
        assert client.delete(f"/api/exercises/{created['id']}").status_code == 204
        assert client.get(f"/api/exercises/{created['id']}").status_code == 404
        assert client.delete(f"/api/exercises/{created['id']}").status_code == 404


def test_exercise_validation_rejects_invalid_age_range(tmp_path, monkeypatch):
    monkeypatch.setenv("MATH_TEST_GENERATOR_DATA_DIR", str(tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/api/exercises",
            json=exercise_data(age_min=14, age_max=11),
        )
        assert response.status_code == 422


def test_exercises_persist_between_app_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("MATH_TEST_GENERATOR_DATA_DIR", str(tmp_path))

    with TestClient(app) as first_run:
        created = first_run.post("/api/exercises", json=exercise_data()).json()

    with TestClient(app) as second_run:
        response = second_run.get(f"/api/exercises/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created
