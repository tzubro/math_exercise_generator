import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  createExercise,
  createExercises,
  deleteExercise,
  exerciseImageUrl,
  getExercises,
  removeExerciseImage,
  type ExerciseFilters,
  uploadExerciseImage,
  updateExercise,
} from "../../lib/api";
import type {
  Difficulty,
  Exercise,
  ExerciseFields,
  ExerciseType,
} from "../../types/contracts";
import ImportReview from "./ImportReview";

interface ExerciseFormValues {
  title: string;
  prompt: string;
  topic: string;
  age_min: string;
  age_max: string;
  exercise_type: ExerciseType;
  options: string[];
  correct_option: number | null;
  difficulty: Difficulty;
  points: string;
  solution: string;
  tags: string;
}

const emptyForm: ExerciseFormValues = {
  title: "",
  prompt: "",
  topic: "",
  age_min: "10",
  age_max: "15",
  exercise_type: "normal",
  options: ["", ""],
  correct_option: null,
  difficulty: "medium",
  points: "1",
  solution: "",
  tags: "",
};

function toFormValues(exercise: Exercise): ExerciseFormValues {
  return {
    title: exercise.title,
    prompt: exercise.prompt,
    topic: exercise.topic,
    age_min: String(exercise.age_min),
    age_max: String(exercise.age_max),
    exercise_type: exercise.exercise_type,
    options: exercise.exercise_type === "multiple_choice"
      ? [...exercise.options]
      : ["", ""],
    correct_option: exercise.correct_option,
    difficulty: exercise.difficulty,
    points: String(exercise.points),
    solution: exercise.solution ?? "",
    tags: exercise.tags.join(", "),
  };
}

function toExerciseFields(values: ExerciseFormValues): ExerciseFields {
  return {
    title: values.title.trim(),
    prompt: values.prompt.trim(),
    topic: values.topic.trim(),
    age_min: Number(values.age_min),
    age_max: Number(values.age_max),
    exercise_type: values.exercise_type,
    options: values.exercise_type === "multiple_choice"
      ? values.options.map((option) => option.trim())
      : [],
    correct_option: values.exercise_type === "multiple_choice"
      ? values.correct_option
      : null,
    difficulty: values.difficulty,
    points: Number(values.points),
    solution: values.solution.trim() || null,
    tags: values.tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean),
  };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}

export default function ExerciseBank() {
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [filters, setFilters] = useState<ExerciseFilters>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<Exercise | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [removeCurrentImage, setRemoveCurrentImage] = useState(false);
  const [localImageUrl, setLocalImageUrl] = useState<string | null>(null);
  const [values, setValues] = useState(emptyForm);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => setRefreshKey((key) => key + 1), []);

  useEffect(() => {
    if (!imageFile) {
      setLocalImageUrl(null);
      return;
    }
    const url = URL.createObjectURL(imageFile);
    setLocalImageUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [imageFile]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setLoadError("");

    getExercises(filters, controller.signal)
      .then(setExercises)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setLoadError(errorMessage(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [filters, refreshKey]);

  const updateFilter = <K extends keyof ExerciseFilters>(
    key: K,
    value: ExerciseFilters[K] | undefined,
  ) => {
    setFilters((current) => {
      const next = { ...current };
      if (value === undefined || value === "") delete next[key];
      else next[key] = value;
      return next;
    });
  };

  const availableTopics = useMemo(
    () => [...new Set(exercises.map((exercise) => exercise.topic))].sort(),
    [exercises],
  );

  const openNewForm = () => {
    setEditing(null);
    setValues(emptyForm);
    setImageFile(null);
    setRemoveCurrentImage(false);
    setFormError("");
    setFormOpen(true);
  };

  const openEditForm = (exercise: Exercise) => {
    setEditing(exercise);
    setValues(toFormValues(exercise));
    setImageFile(null);
    setRemoveCurrentImage(false);
    setFormError("");
    setFormOpen(true);
  };

  const closeForm = () => {
    if (saving) return;
    setFormOpen(false);
    setFormError("");
  };

  const submitForm = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setFormError("");

    try {
      const input = toExerciseFields(values);
      let savedExercise: Exercise;
      if (editing) {
        savedExercise = await updateExercise(editing.id, input);
      } else {
        savedExercise = await createExercise(input);
      }

      if (imageFile) {
        try {
          await uploadExerciseImage(savedExercise.id, imageFile);
        } catch (error) {
          if (!editing) {
            setEditing(savedExercise);
            setFilters({});
            refresh();
          }
          throw new Error(`Exercise saved, but image upload failed: ${errorMessage(error)}`);
        }
      } else if (editing && removeCurrentImage) {
        await removeExerciseImage(editing.id);
      }

      setFormOpen(false);
      setEditing(null);
      setImageFile(null);
      setRemoveCurrentImage(false);
      setFilters({});
      refresh();
    } catch (error) {
      setFormError(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const removeExercise = async (exercise: Exercise) => {
    if (!window.confirm(`Delete “${exercise.title}”? This cannot be undone.`)) return;
    setLoadError("");
    try {
      await deleteExercise(exercise.id);
      refresh();
    } catch (error) {
      setLoadError(errorMessage(error));
    }
  };

  return (
    <section className="exercise-bank">
      <div className="page-heading">
        <div>
          <p className="eyebrow">YOUR LIBRARY</p>
          <h1>Exercise bank</h1>
          <p className="page-description">
            Save and organize exercises to reuse in your tests.
          </p>
        </div>
        <div className="page-heading-actions">
          <button className="secondary-button" onClick={() => setImportOpen(true)} type="button">
            Import file
          </button>
          <button className="primary-button" onClick={openNewForm} type="button">
            <span aria-hidden="true">＋</span> Add exercise
          </button>
        </div>
      </div>

      <div className="filter-bar" aria-label="Filter exercises">
        <label className="search-field">
          <span className="visually-hidden">Search exercises</span>
          <span className="search-icon" aria-hidden="true">⌕</span>
          <input
            onChange={(event) => updateFilter("q", event.target.value || undefined)}
            placeholder="Search title, question, topic or tag"
            type="search"
            value={filters.q ?? ""}
          />
        </label>
        <label>
          <span className="visually-hidden">Filter by topic</span>
          <input
            list="exercise-topics"
            onChange={(event) =>
              updateFilter("topic", event.target.value || undefined)
            }
            placeholder="All topics"
            value={filters.topic ?? ""}
          />
          <datalist id="exercise-topics">
            {availableTopics.map((topic) => <option key={topic} value={topic} />)}
          </datalist>
        </label>
        <label>
          <span className="visually-hidden">Filter by student age</span>
          <select
            onChange={(event) =>
              updateFilter("age", event.target.value ? Number(event.target.value) : undefined)
            }
            value={filters.age ?? ""}
          >
            <option value="">All ages</option>
            {[10, 11, 12, 13, 14, 15].map((age) => (
              <option key={age} value={age}>Age {age}</option>
            ))}
          </select>
        </label>
        <label>
          <span className="visually-hidden">Filter by difficulty</span>
          <select
            onChange={(event) =>
              updateFilter(
                "difficulty",
                (event.target.value || undefined) as Difficulty | undefined,
              )
            }
            value={filters.difficulty ?? ""}
          >
            <option value="">All levels</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </label>
      </div>

      {loadError && (
        <div className="alert" role="alert">
          <span>{loadError}</span>
          <button onClick={refresh} type="button">Retry</button>
        </div>
      )}

      <div className="bank-summary">
        <span>{loading ? "Loading exercises…" : `${exercises.length} exercises`}</span>
      </div>

      {!loading && !loadError && exercises.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon" aria-hidden="true">∑</div>
          <h2>{Object.keys(filters).length ? "No matches found" : "Your bank is empty"}</h2>
          <p>
            {Object.keys(filters).length
              ? "Try changing or clearing the filters."
              : "Add your first exercise to start building your reusable library."}
          </p>
          {Object.keys(filters).length ? (
            <button className="secondary-button" onClick={() => setFilters({})} type="button">
              Clear filters
            </button>
          ) : (
            <button className="primary-button" onClick={openNewForm} type="button">
              Add your first exercise
            </button>
          )}
        </div>
      )}

      <div className="exercise-grid">
        {exercises.map((exercise) => (
          <article className="exercise-card" key={exercise.id}>
            <div className="exercise-card-top">
              <span className="topic-badge">{exercise.topic}</span>
              <span className={`difficulty-badge difficulty-${exercise.difficulty}`}>
                {exercise.difficulty}
              </span>
            </div>
            <h2>{exercise.title}</h2>
            {exercise.exercise_type === "multiple_choice" && (
              <span className="exercise-type-badge">Multiple choice</span>
            )}
            <p className="exercise-prompt">{exercise.prompt}</p>
            {exercise.exercise_type === "multiple_choice" && (
              <ul className="exercise-options">
                {exercise.options.map((option, index) => (
                  <li key={`${index}-${option}`}>
                    <span>{String.fromCharCode(97 + index)})</span> {option}
                  </li>
                ))}
              </ul>
            )}
            <div className="exercise-meta">
              <span>Ages {exercise.age_min}–{exercise.age_max}</span>
              <span>{exercise.points} {exercise.points === 1 ? "point" : "points"}</span>
            </div>
            {exercise.tags.length > 0 && (
              <div className="tag-list">
                {exercise.tags.map((tag) => <span className="tag" key={tag}>{tag}</span>)}
              </div>
            )}
            {exercise.image_id && (
              <img
                alt=""
                className="exercise-thumbnail"
                loading="lazy"
                src={exerciseImageUrl(exercise.image_id)}
              />
            )}
            <div className="exercise-actions">
              <button onClick={() => openEditForm(exercise)} type="button">Edit</button>
              <button
                className="delete-action"
                onClick={() => void removeExercise(exercise)}
                type="button"
              >
                Delete
              </button>
            </div>
          </article>
        ))}
      </div>

      {formOpen && (
        <div className="dialog-backdrop">
          <section aria-labelledby="exercise-form-title" aria-modal="true" className="exercise-dialog" role="dialog">
            <div className="dialog-heading">
              <div>
                <p className="eyebrow">{editing ? "EDIT LIBRARY ITEM" : "NEW LIBRARY ITEM"}</p>
                <h2 id="exercise-form-title">{editing ? "Edit exercise" : "Add exercise"}</h2>
              </div>
              <button
                aria-label="Close dialog"
                className="icon-button"
                disabled={saving}
                onClick={closeForm}
                type="button"
              >
                ×
              </button>
            </div>
            <form onSubmit={submitForm}>
              <label className="form-field">
                Title
                <input
                  autoFocus
                  maxLength={200}
                  onChange={(event) => setValues({ ...values, title: event.target.value })}
                  required
                  value={values.title}
                />
              </label>
              <label className="form-field">
                Exercise
                <textarea
                  onChange={(event) => setValues({ ...values, prompt: event.target.value })}
                  required
                  rows={4}
                  value={values.prompt}
                />
              </label>
              <div className="image-upload-panel">
                <label className="form-field">
                  Question image
                  <span className="optional-label">Optional · JPEG or PNG, up to 5 MB</span>
                  <input
                    accept="image/jpeg,image/png,.jpg,.jpeg,.png"
                    onChange={(event) => {
                      setImageFile(event.target.files?.[0] ?? null);
                      setRemoveCurrentImage(false);
                    }}
                    type="file"
                  />
                </label>
                {(localImageUrl || (editing?.image_id && !removeCurrentImage)) && (
                  <img
                    alt="Exercise preview"
                    className="exercise-image-preview"
                    src={
                      localImageUrl ??
                      (editing?.image_id ? exerciseImageUrl(editing.image_id) : "")
                    }
                  />
                )}
                {imageFile && (
                  <button
                    className="text-button image-action"
                    onClick={() => setImageFile(null)}
                    type="button"
                  >
                    Clear selected image
                  </button>
                )}
                {editing?.image_id && !imageFile && (
                  <label className="remove-image-control">
                    <input
                      checked={removeCurrentImage}
                      onChange={(event) => setRemoveCurrentImage(event.target.checked)}
                      type="checkbox"
                    />
                    Remove current image when saving
                  </label>
                )}
              </div>
              <label className="form-field exercise-type-field">
                Exercise type
                <select
                  onChange={(event) => {
                    const exerciseType = event.target.value as ExerciseType;
                    setValues({
                      ...values,
                      exercise_type: exerciseType,
                      options: exerciseType === "multiple_choice"
                        ? values.options.length >= 2 ? values.options : ["", ""]
                        : [],
                      correct_option: exerciseType === "multiple_choice"
                        ? values.correct_option
                        : null,
                    });
                  }}
                  value={values.exercise_type}
                >
                  <option value="normal">Normal exercise</option>
                  <option value="multiple_choice">Multiple choice</option>
                </select>
              </label>
              {values.exercise_type === "multiple_choice" && (
                <fieldset className="options-editor">
                  <legend>Answer options</legend>
                  <p className="options-help">Add at least two options and mark the correct answer.</p>
                  {values.options.map((option, index) => (
                    <div className="option-editor-row" key={index}>
                      <span className="option-editor-label">{String.fromCharCode(97 + index)})</span>
                      <input
                        aria-label={`Option ${String.fromCharCode(97 + index)}`}
                        maxLength={500}
                        onChange={(event) => {
                          const options = [...values.options];
                          options[index] = event.target.value;
                          setValues({ ...values, options });
                        }}
                        placeholder={`Enter option ${String.fromCharCode(97 + index)}`}
                        required
                        value={option}
                      />
                      <label className="correct-option-control">
                        <input
                          checked={values.correct_option === index}
                          name="correct-option"
                          onChange={() => setValues({ ...values, correct_option: index })}
                          required={values.correct_option === null}
                          type="radio"
                        />
                        Correct
                      </label>
                      <button
                        aria-label={`Remove option ${String.fromCharCode(97 + index)}`}
                        className="remove-option-button"
                        disabled={values.options.length <= 2}
                        onClick={() => {
                          const options = values.options.filter((_, optionIndex) => optionIndex !== index);
                          const correctOption = values.correct_option === index
                            ? null
                            : values.correct_option !== null && values.correct_option > index
                              ? values.correct_option - 1
                              : values.correct_option;
                          setValues({ ...values, options, correct_option: correctOption });
                        }}
                        type="button"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                  {values.options.length < 26 && (
                    <button
                      className="text-button add-option-button"
                      onClick={() =>
                        setValues({ ...values, options: [...values.options, ""] })
                      }
                      type="button"
                    >
                      + Add option
                    </button>
                  )}
                </fieldset>
              )}
              <div className="form-row">
                <label className="form-field">
                  Topic
                  <input
                    maxLength={100}
                    onChange={(event) => setValues({ ...values, topic: event.target.value })}
                    placeholder="e.g. Fractions"
                    required
                    value={values.topic}
                  />
                </label>
                <label className="form-field">
                  Difficulty
                  <select
                    onChange={(event) =>
                      setValues({ ...values, difficulty: event.target.value as Difficulty })
                    }
                    value={values.difficulty}
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </label>
              </div>
              <div className="form-row form-row-three">
                <label className="form-field">
                  Ages from
                  <select
                    onChange={(event) => setValues({ ...values, age_min: event.target.value })}
                    value={values.age_min}
                  >
                    {[10, 11, 12, 13, 14, 15].map((age) => (
                      <option key={age} value={age}>{age}</option>
                    ))}
                  </select>
                </label>
                <label className="form-field">
                  Ages to
                  <select
                    onChange={(event) => setValues({ ...values, age_max: event.target.value })}
                    value={values.age_max}
                  >
                    {[10, 11, 12, 13, 14, 15].map((age) => (
                      <option key={age} value={age}>{age}</option>
                    ))}
                  </select>
                </label>
                <label className="form-field">
                  Points
                  <input
                    min="0"
                    onChange={(event) => setValues({ ...values, points: event.target.value })}
                    required
                    type="number"
                    value={values.points}
                  />
                </label>
              </div>
              <label className="form-field">
                Solution <span className="optional-label">Optional</span>
                <textarea
                  onChange={(event) => setValues({ ...values, solution: event.target.value })}
                  rows={2}
                  value={values.solution}
                />
              </label>
              <label className="form-field">
                Tags <span className="optional-label">Separate with commas</span>
                <input
                  onChange={(event) => setValues({ ...values, tags: event.target.value })}
                  placeholder="e.g. addition, fractions"
                  value={values.tags}
                />
              </label>
              {formError && <p className="form-error" role="alert">{formError}</p>}
              <div className="dialog-actions">
                <button className="secondary-button" disabled={saving} onClick={closeForm} type="button">
                  Cancel
                </button>
                <button className="primary-button" disabled={saving} type="submit">
                  {saving ? "Saving…" : editing ? "Save changes" : "Add exercise"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
      {importOpen && (
        <ImportReview
          onAddSelected={async (drafts) => {
            await createExercises(drafts);
            setFilters({});
            refresh();
          }}
          onClose={() => setImportOpen(false)}
        />
      )}
    </section>
  );
}
