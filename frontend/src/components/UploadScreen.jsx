import { useState } from "react";
import { ROLES } from "../constants";

export default function UploadScreen({ onStart, loading, error }) {
  const [role, setRole] = useState(ROLES[0].value);
  const [file, setFile] = useState(null);

  function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;
    onStart(role, file);
  }

  return (
    <div className="screen">
      <p className="eyebrow">AI-Powered Technical Screening</p>
      <h1>Start your mock interview</h1>
      <p className="lead">
        Upload your resume and pick a role. Questions are generated from your
        actual background and a role-specific knowledge base.
      </p>

      <form onSubmit={handleSubmit}>
        <label>
          Target role
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Resume (PDF or .txt)
          <input
            type="file"
            accept=".pdf,.txt"
            onChange={(e) => setFile(e.target.files[0])}
          />
        </label>

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={!file || loading}>
          {loading && <span className="spinner" />}
          {loading ? "Starting interview..." : "Start Interview"}
        </button>
        {loading && (
          <p className="loading-hint">
            Parsing your resume and generating your first question -- this calls the AI
            model twice, so it can take 5-15 seconds.
          </p>
        )}
      </form>
    </div>
  );
}
