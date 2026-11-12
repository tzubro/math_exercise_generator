import { useEffect, useMemo, useState } from "react";
import {
  createTest,
  exportTest,
  exerciseImageUrl,
  getExercises,
} from "../../lib/api";
import type { Exercise, Test } from "../../types/contracts";

type ExportFormat = "docx" | "pdf";

function messageFrom(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}

export default function TestBuilder() {
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [search, setSearch] = useState("");
  const [title, setTitle] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [savedTest, setSavedTest] = useState<Test | null>(null);
  const [includeSolutions, setIncludeSolutions] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState<ExportFormat | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getExercises({}, controller.signal)
      .then(setExercises)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setLoadError(messageFrom(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const filteredExercises = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    if (!query) return exercises;
    return exercises.filter((exercise) =>
      [
        exercise.title,
        exercise.prompt,
        exercise.topic,
        ...exercise.tags,
        ...exercise.options,
      ]
        .join(" ")
        .toLocaleLowerCase()
        .includes(query),
    );
  }, [exercises, search]);

  const selectedExercises = useMemo(() => {
    const byId = new Map(exercises.map((exercise) => [exercise.id, exercise]));
    return selectedIds.flatMap((id) => {
      const exercise = byId.get(id);
      return exercise ? [exercise] : [];
    });
  }, [exercises, selectedIds]);
  const totalPoints = selectedExercises.reduce(
    (total, exercise) => total + exercise.points,
    0,
  );

  const toggleExercise = (id: string) => {
    setSelectedIds((current) =>
      current.includes(id)
        ? current.filter((selectedId) => selectedId !== id)
        : [...current, id],
    );
    setSavedTest(null);
    setError("");
  };

  const moveExercise = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= selectedIds.length) return;
    setSelectedIds((current) => {
      const reordered = [...current];
      [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
      return reordered;
    });
    setSavedTest(null);
  };

  const saveTest = async () => {
    setSaving(true);
    setError("");
    try {
      const test = await createTest({
        title: title.trim(),
        exercise_ids: selectedIds,
      });
      setSavedTest(test);
    } catch (reason) {
      setError(messageFrom(reason));
    } finally {
      setSaving(false);
    }
  };

  const download = async (format: ExportFormat) => {
    if (!savedTest) return;
    setExporting(format);
    setError("");
    try {
      await exportTest(savedTest.id, format, includeSolutions);
    } catch (reason) {
      setError(messageFrom(reason));
    } finally {
      setExporting(null);
    }
  };

  return (
    <section className="test-builder">
      <div className="page-heading">
        <div>
          <p className="eyebrow">TEST WORKSPACE</p>
          <h1>Create a test</h1>
          <p className="page-description">
            Choose exercises, arrange their order, and save a printable test.
          </p>
        </div>
      </div>

      <div className="test-title-panel">
        <label className="form-field">
          Test title
          <input
            maxLength={200}
            onChange={(event) => {
              setTitle(event.target.value);
              setSavedTest(null);
            }}
            placeholder="e.g. Fractions practice"
            value={title}
          />
        </label>
      </div>

      {error && <div className="alert" role="alert">{error}</div>}
      {loadError && <div className="alert" role="alert">{loadError}</div>}

      {savedTest && (
        <div className="saved-test-panel">
          <div>
            <strong>Test saved.</strong>
            <span> Export a student copy or include the answer key.</span>
          </div>
          <label className="solution-toggle">
            <input
              checked={includeSolutions}
              onChange={(event) => setIncludeSolutions(event.target.checked)}
              type="checkbox"
            />
            Include answer key
          </label>
          <div className="export-actions">
            <button
              className="secondary-button"
              disabled={exporting !== null}
              onClick={() => void download("docx")}
              type="button"
            >
              {exporting === "docx" ? "Preparing…" : "Download DOCX"}
            </button>
            <button
              className="primary-button"
              disabled={exporting !== null}
              onClick={() => void download("pdf")}
              type="button"
            >
              {exporting === "pdf" ? "Preparing…" : "Download PDF"}
            </button>
          </div>
        </div>
      )}

      <div className="test-workspace">
        <section className="exercise-picker">
          <div className="section-heading">
            <div>
              <h2>Exercise bank</h2>
              <p>{filteredExercises.length} available</p>
            </div>
            <label className="picker-search">
              <span className="visually-hidden">Search available exercises</span>
              <input
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search"
                type="search"
                value={search}
              />
            </label>
          </div>
          {loading && <p className="subtle-message">Loading exercises…</p>}
          {!loading && !loadError && exercises.length === 0 && (
            <p className="subtle-message">Add exercises to the bank before creating a test.</p>
          )}
          {!loading && exercises.length > 0 && filteredExercises.length === 0 && (
            <p className="subtle-message">No exercises match your search.</p>
          )}
          <div className="picker-list">
            {filteredExercises.map((exercise) => {
              const checked = selectedIds.includes(exercise.id);
              return (
                <label className={`picker-card${checked ? " picker-card-selected" : ""}`} key={exercise.id}>
                  <input
                    checked={checked}
                    onChange={() => toggleExercise(exercise.id)}
                    type="checkbox"
                  />
                  <span className="picker-card-content">
                    <strong>{exercise.title}</strong>
                    <span>{exercise.topic} · Ages {exercise.age_min}–{exercise.age_max}</span>
                    {exercise.exercise_type === "multiple_choice" && (
                      <span>Multiple choice · {exercise.options.length} options</span>
                    )}
                    <span className="picker-prompt">{exercise.prompt}</span>
                  </span>
                  {exercise.image_id && (
                    <img
                      alt=""
                      className="picker-image"
                      loading="lazy"
                      src={exerciseImageUrl(exercise.image_id)}
                    />
                  )}
                  <span className="picker-points">{exercise.points} pt</span>
                </label>
              );
            })}
          </div>
        </section>

        <aside className="test-preview">
          <div className="section-heading">
            <div>
              <h2>Test order</h2>
              <p>{selectedExercises.length} selected · {totalPoints} points</p>
            </div>
          </div>
          {selectedExercises.length === 0 ? (
            <div className="selection-empty">
              <span aria-hidden="true">☷</span>
              <p>Select exercises to build your test.</p>
            </div>
          ) : (
            <ol className="selected-list">
              {selectedExercises.map((exercise, index) => (
                <li className="selected-item" key={exercise.id}>
                  <span className="selected-number">{index + 1}</span>
                  <span className="selected-title">{exercise.title}</span>
                  <span className="reorder-actions">
                    <button
                      aria-label={`Move ${exercise.title} up`}
                      disabled={index === 0}
                      onClick={() => moveExercise(index, -1)}
                      type="button"
                    >↑</button>
                    <button
                      aria-label={`Move ${exercise.title} down`}
                      disabled={index === selectedExercises.length - 1}
                      onClick={() => moveExercise(index, 1)}
                      type="button"
                    >↓</button>
                  </span>
                  <button
                    aria-label={`Remove ${exercise.title}`}
                    className="remove-selected"
                    onClick={() => toggleExercise(exercise.id)}
                    type="button"
                  >×</button>
                </li>
              ))}
            </ol>
          )}
          <button
            className="primary-button save-test-button"
            disabled={saving || !title.trim() || selectedIds.length === 0}
            onClick={() => void saveTest()}
            type="button"
          >
            {saving ? "Saving test…" : savedTest ? "Save updated test" : "Save test"}
          </button>
        </aside>
      </div>
    </section>
  );
}
