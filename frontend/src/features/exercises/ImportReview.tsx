import { useState } from "react";
import { parseExerciseUpload } from "../../lib/api";
import type { ExerciseCreate } from "../../types/contracts";

interface ImportReviewProps {
  onClose: () => void;
  onAddSelected: (drafts: ExerciseCreate[]) => Promise<void>;
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Could not read this file.";
}

export default function ImportReview({ onClose, onAddSelected }: ImportReviewProps) {
  const [drafts, setDrafts] = useState<ExerciseCreate[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fileName, setFileName] = useState("");
  const [useOllama, setUseOllama] = useState(true);

  const readFile = async (file?: File) => {
    if (!file) return;
    setLoading(true);
    setError("");
    setDrafts([]);
    setWarnings([]);
    setSelected(new Set());
    setFileName(file.name);
    try {
      const result = await parseExerciseUpload(file, useOllama);
      setDrafts(result.drafts);
      setWarnings(result.warnings);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setLoading(false);
    }
  };

  const toggle = (index: number) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const saveSelected = async () => {
    setSaving(true);
    setError("");
    try {
      await onAddSelected([...selected].sort((a, b) => a - b).map((index) => drafts[index]));
      onClose();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="dialog-backdrop">
      <section aria-labelledby="import-title" aria-modal="true" className="exercise-dialog import-dialog" role="dialog">
        <div className="dialog-heading">
          <div>
            <p className="eyebrow">IMPORT QUESTIONS</p>
            <h2 id="import-title">Review extracted exercises</h2>
          </div>
          <button aria-label="Close dialog" className="icon-button" onClick={onClose} type="button">×</button>
        </div>

        <label className="form-field upload-field">
          Choose a DOCX or PDF file
          <input
            accept=".docx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={(event) => void readFile(event.target.files?.[0])}
            type="file"
          />
        </label>
        <label className="import-ai-toggle">
          <input
            checked={useOllama}
            disabled={loading}
            onChange={(event) => setUseOllama(event.target.checked)}
            type="checkbox"
          />
          <span>
            <strong>Use local Ollama AI parsing</strong>
            <span>Uses the configured local model (default: qwen3.5:4b). If unavailable, numbered-text parsing is used instead.</span>
          </span>
        </label>
        <p className="subtle-message">
          Only numbered entries (such as “1.” or “2)”) are treated as exercises. Automatic numbered lists in DOCX are supported; unnumbered text is ignored.
        </p>
        {fileName && <p className="subtle-message">{fileName}</p>}
        {loading && (
          <p className="subtle-message">
            {useOllama ? "Extracting text and organizing questions with local Ollama…" : "Extracting text…"}
          </p>
        )}
        {warnings.length > 0 && (
          <ul className="import-warnings">
            {warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        )}
        {drafts.length > 0 && (
          <>
            <div className="import-review-heading">
              <span>{drafts.length} draft exercises found</span>
              <button
                className="text-button"
                onClick={() =>
                  setSelected(selected.size === drafts.length
                    ? new Set()
                    : new Set(drafts.map((_, index) => index)))
                }
                type="button"
              >
                {selected.size === drafts.length ? "Clear selection" : "Select all"}
              </button>
            </div>
            <p className="subtle-message">
              Imported items use default age, topic, difficulty, and point values. Edit those in the bank after saving.
            </p>
            <div className="draft-list">
              {drafts.map((draft, index) => (
                <label className={`draft-item${selected.has(index) ? " draft-item-selected" : ""}`} key={`${index}-${draft.title}`}>
                  <input
                    checked={selected.has(index)}
                    onChange={() => toggle(index)}
                    type="checkbox"
                  />
                  <span>
                    <strong>{draft.title}</strong>
                    <span>{draft.prompt}</span>
                  </span>
                </label>
              ))}
            </div>
          </>
        )}
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="dialog-actions">
          <button className="secondary-button" disabled={saving} onClick={onClose} type="button">Cancel</button>
          <button
            className="primary-button"
            disabled={saving || loading || selected.size === 0}
            onClick={() => void saveSelected()}
            type="button"
          >
            {saving ? "Adding…" : `Add ${selected.size} selected`}
          </button>
        </div>
      </section>
    </div>
  );
}
