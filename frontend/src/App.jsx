import { useState } from "react";
import { createSession, submitAnswer, getSummary } from "./api";
import { MAX_QUESTIONS } from "./constants";
import UploadScreen from "./components/UploadScreen";
import InterviewScreen from "./components/InterviewScreen";
import SummaryScreen from "./components/SummaryScreen";
import "./App.css";

export default function App() {
  const [stage, setStage] = useState("upload"); // "upload" | "interview" | "summary"
  const [sessionId, setSessionId] = useState(null);
  const [role, setRole] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleStart(selectedRole, file) {
    setLoading(true);
    setError(null);
    try {
      const result = await createSession(selectedRole, file);
      setSessionId(result.session_id);
      setRole(result.role);
      setCurrentQuestion(result.first_question);
      setStage("interview");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAnswer(answerText) {
    setLoading(true);
    setError(null);
    try {
      const nextQuestion = await submitAnswer(sessionId, currentQuestion.question_id, answerText);

      if (nextQuestion.done) {
        const summaryData = await getSummary(sessionId);
        setSummary(summaryData);
        setStage("summary");
      } else {
        setCurrentQuestion(nextQuestion);
        setQuestionNumber((n) => n + 1);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      {stage === "upload" && (
        <UploadScreen onStart={handleStart} loading={loading} error={error} />
      )}

      {stage === "interview" && currentQuestion && (
        <InterviewScreen
          role={role}
          sessionId={sessionId}
          totalQuestions={MAX_QUESTIONS}
          currentQuestion={currentQuestion}
          questionNumber={questionNumber}
          onAnswer={handleAnswer}
          loading={loading}
          error={error}
        />
      )}

      {stage === "summary" && summary && <SummaryScreen summary={summary} />}
    </div>
  );
}
