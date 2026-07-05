import { useState } from "react";

// Keeps candidates focused on a clear, interview-length response rather
// than an unbounded essay -- roughly 120-180 words, similar to what
// someone would actually say out loud in 60-90 seconds.
const MAX_ANSWER_LENGTH = 1200;

function ProgressRail({ current, total }) {
  const dots = Array.from({ length: total }, (_, i) => i + 1);
  return (
    <div className="progress-rail" aria-label={`Question ${current} of ${total}`}>
      {dots.map((n) => (
        <span
          key={n}
          className={
            "rail-dot " +
            (n < current ? "rail-dot--done" : n === current ? "rail-dot--current" : "")
          }
        />
      ))}
    </div>
  );
}

export default function InterviewScreen({
  totalQuestions,
  currentQuestion,
  questionNumber,
  onAnswer,
  loading,
  error,
}) {
  const [answer, setAnswer] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (!answer.trim()) return;
    onAnswer(answer);
    setAnswer("");
  }

  const charsLeft = MAX_ANSWER_LENGTH - answer.length;

  return (
    <div className="screen">
      <ProgressRail current={questionNumber} total={totalQuestions} />

      {currentQuestion.topic && <p className="topic-tag">{currentQuestion.topic}</p>}
      <h2>{currentQuestion.question}</h2>

      <form onSubmit={handleSubmit}>
        <textarea
          rows={7}
          value={answer}
          maxLength={MAX_ANSWER_LENGTH}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Type your answer here... (aim for a few focused sentences)"
        />
        <p className="char-count">{charsLeft} characters left</p>

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={!answer.trim() || loading}>
          {loading && <span className="spinner" />}
          {loading ? "Submitting..." : "Submit Answer"}
        </button>
        {loading && <p className="loading-hint">Generating your next question -- a few seconds.</p>}
      </form>
    </div>
  );
}
