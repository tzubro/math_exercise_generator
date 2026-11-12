import type {
  ApiHealth,
  Difficulty,
  Exercise,
  ExerciseCreate,
  ExerciseUpdate,
  ImportParseResult,
  Test,
  TestCreate,
} from "../types/contracts";

export interface ExerciseFilters {
  q?: string;
  topic?: string;
  age?: number;
  difficulty?: Difficulty;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const response = await fetch(url, {
    ...init,
    headers: {
      ...(init?.body && !isFormData ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item: { msg?: string }) => item.msg ?? "Invalid value").join("; ")
      : typeof detail === "string"
        ? detail
        : `Request failed (${response.status})`;
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export async function getApiHealth(): Promise<ApiHealth> {
  return request<ApiHealth>("/api/health");
}

export async function getExercises(
  filters: ExerciseFilters = {},
  signal?: AbortSignal,
): Promise<Exercise[]> {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.topic) params.set("topic", filters.topic);
  if (filters.age !== undefined) params.set("age", String(filters.age));
  if (filters.difficulty) params.set("difficulty", filters.difficulty);
  const query = params.size > 0 ? `?${params.toString()}` : "";
  return request<Exercise[]>(`/api/exercises${query}`, { signal });
}

export async function createExercise(input: ExerciseCreate): Promise<Exercise> {
  return request<Exercise>("/api/exercises", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function createExercises(
  exercises: ExerciseCreate[],
): Promise<Exercise[]> {
  return request<Exercise[]>("/api/exercises/bulk", {
    method: "POST",
    body: JSON.stringify({ exercises }),
  });
}

export async function updateExercise(
  id: string,
  input: ExerciseUpdate,
): Promise<Exercise> {
  return request<Exercise>(`/api/exercises/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export async function deleteExercise(id: string): Promise<void> {
  return request<void>(`/api/exercises/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export async function uploadExerciseImage(
  id: string,
  file: File,
): Promise<Exercise> {
  const formData = new FormData();
  formData.append("file", file);
  return request<Exercise>(`/api/exercises/${encodeURIComponent(id)}/image`, {
    method: "PUT",
    body: formData,
  });
}

export async function removeExerciseImage(id: string): Promise<void> {
  return request<void>(`/api/exercises/${encodeURIComponent(id)}/image`, {
    method: "DELETE",
  });
}

export function exerciseImageUrl(imageId: string): string {
  return `/api/images/${encodeURIComponent(imageId)}`;
}

export async function createTest(input: TestCreate): Promise<Test> {
  return request<Test>("/api/tests", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function exportTest(
  testId: string,
  format: "docx" | "pdf",
  includeSolutions: boolean,
): Promise<void> {
  const params = new URLSearchParams({
    format,
    include_solutions: String(includeSolutions),
  });
  const response = await fetch(
    `/api/tests/${encodeURIComponent(testId)}/export?${params.toString()}`,
    { method: "POST" },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(
      typeof detail === "string" ? detail : `Export failed (${response.status})`,
    );
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? `math-test.${format}`;
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

export async function parseExerciseUpload(
  file: File,
  useOllama = true,
): Promise<ImportParseResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("use_ollama", String(useOllama));
  return request<ImportParseResult>("/api/imports/parse", {
    method: "POST",
    body: formData,
  });
}
