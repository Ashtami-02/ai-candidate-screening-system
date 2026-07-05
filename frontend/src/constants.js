export const ROLES = [
  { value: "ai_ml_engineer", label: "AI/ML Engineer" },
  { value: "data_scientist", label: "Data Scientist / Applied ML" },
  // Add more roles here as you build out more knowledge bases --
  // each just needs: (1) a build_kb.py run under that role name,
  // (2) an entry here. No backend code changes needed.
];

// Must match MAX_QUESTIONS in backend/app/services/session_service.py.
// Kept as a separate constant here (rather than fetched from the API)
// to keep the frontend simple -- a natural extension would be exposing
// this via the /health endpoint so the two can never drift apart.
export const MAX_QUESTIONS = 5;

export function roleLabel(value) {
  return ROLES.find((r) => r.value === value)?.label || value;
}
