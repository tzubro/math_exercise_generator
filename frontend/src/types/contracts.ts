export type Difficulty = "easy" | "medium" | "hard";
export type ExerciseType = "normal" | "multiple_choice";

export interface ExerciseFields {
  title: string;
  prompt: string;
  topic: string;
  age_min: number;
  age_max: number;
  exercise_type: ExerciseType;
  options: string[];
  correct_option: number | null;
  difficulty: Difficulty;
  points: number;
  solution: string | null;
  tags: string[];
}

export interface Exercise extends ExerciseFields {
  id: string;
  image_id: string | null;
}

export type ExerciseCreate = ExerciseFields;

export type ExerciseUpdate = Partial<ExerciseFields>;

export interface TestExerciseSnapshot extends ExerciseFields {
  source_exercise_id: string;
  image_id: string | null;
}

export interface Test {
  id: string;
  title: string;
  exercises: TestExerciseSnapshot[];
}

export interface TestCreate {
  title: string;
  exercise_ids: string[];
}

export interface ImportParseResult {
  filename: string;
  drafts: ExerciseCreate[];
  warnings: string[];
}

export interface ApiHealth {
  status: "ok";
}
