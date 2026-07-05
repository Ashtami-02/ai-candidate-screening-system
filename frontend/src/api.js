// All communication with the FastAPI backend lives here. Keeping every
// fetch() call in one file means if the backend URL or response shape
// ever changes, you edit exactly one place instead of hunting through
// every component.

const API_BASE = "http://127.0.0.1:8000";

export async function createSession(role, resumeFile) {
  const formData = new FormData();
  formData.append("role", role);
  formData.append("resume", resumeFile);

  const response = await fetch(`${API_BASE}/interview/sessions`, {
    method: "POST",
    body: formData, // NOTE: no Content-Type header here on purpose --
    // the browser sets the correct multipart boundary automatically.
    // Setting it manually is a classic bug that breaks file uploads.
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || "Failed to create session");
  }
  return response.json();
}

export async function submitAnswer(sessionId, questionId, answerText) {
  const response = await fetch(`${API_BASE}/interview/sessions/${sessionId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: questionId, answer_text: answerText }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || "Failed to submit answer");
  }
  return response.json();
}

export async function getSummary(sessionId) {
  const response = await fetch(`${API_BASE}/interview/sessions/${sessionId}/summary`);

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || "Failed to load summary");
  }
  return response.json();
}
