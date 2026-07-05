import { roleLabel } from "../constants";

export default function SummaryScreen({ summary }) {
  return (
    <div className="screen">
      <p className="eyebrow">{roleLabel(summary.role)}</p>
      <h1>Interview Summary</h1>
      <p className="lead">
        Answered {summary.answered_questions} of {summary.total_questions} questions
      </p>

      <div className="insights-card">
        <p className="insights-label">Session Analysis</p>
        <p className="insights-text">{summary.insights}</p>
      </div>

      {summary.qa_pairs.map((qa, index) => (
        <div className="qa-card" key={index}>
          <p className="topic-tag">{qa.topic}</p>
          <p className="question-text">
            <strong>Q{index + 1}:</strong> {qa.question}
          </p>
          <p className="answer-text">
            <strong>Your answer:</strong> {qa.answer || <em>(not answered)</em>}
          </p>
        </div>
      ))}
    </div>
  );
}
