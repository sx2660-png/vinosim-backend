import { useEffect, useState } from "react";
import { QuizQuestion, QuizResult, StoredLabelQuiz, getLabelQuiz, getQuiz, submitQuiz } from "../api";

function letterOf(option: string) {
  const match = option.trim().match(/^([A-D])\b/i);
  return match ? match[1].toUpperCase() : option.trim();
}

function matches(option: string, correct: string) {
  const wanted = correct.trim();
  return option.trim().toLowerCase() === wanted.toLowerCase() || letterOf(option) === wanted.toUpperCase();
}

export function QuizPage() {
  const [mode, setMode] = useState<"bank" | "label">("label");
  return (
    <main className="screen">
      <p className="kicker">Quiz</p>
      <h1>Test your taste.</h1>
      <div className="tabs">
        <button className={mode === "label" ? "tab active" : "tab"} onClick={() => setMode("label")}>Label card</button>
        <button className={mode === "bank" ? "tab active" : "tab"} onClick={() => setMode("bank")}>Bank</button>
      </div>
      {mode === "bank" ? <BankQuiz /> : <LabelDecode />}
    </main>
  );
}

function BankQuiz() {
  const [question, setQuestion] = useState<QuizQuestion | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setError("");
    setPicked(null);
    setResult(null);
    try {
      setQuestion(await getQuiz());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load a question.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function confirm() {
    if (!question || !picked) return;
    setBusy(true);
    setError("");
    try {
      setResult(await submitQuiz(question.id, letterOf(picked)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not score the answer.");
    } finally {
      setBusy(false);
    }
  }

  if (!question && !error) return <p className="quiet">Fetching a question…</p>;

  return (
    <div className="stack">
      {error && <p className="banner">{error}</p>}
      {question && (
        <>
          <p className="meta">{question.category}</p>
          {question.image && <img className="quiz-photo" src={question.image} alt="" />}
          <h2>{question.question}</h2>
          {question.options.map((option) => {
            let tone = "choice";
            if (result && matches(option, result.correct_answer)) tone = "choice right";
            else if (result && picked === option) tone = "choice wrong";
            else if (picked === option) tone = "choice selected";
            return (
              <button key={option} className={tone} disabled={Boolean(result)} onClick={() => setPicked(option)}>
                {option}
              </button>
            );
          })}
          {result && (
            <div className={result.correct ? "banner ok" : "banner"}>
              <strong>{result.correct ? "Correct" : "Not quite"}</strong>
              <p>{result.explanation}</p>
              <p className="quiet">{result.score.correct} correct of {result.score.total}</p>
            </div>
          )}
          {result ? (
            <button className="btn block" onClick={() => void load()} disabled={busy}>Next question</button>
          ) : (
            <button className="btn block" onClick={() => void confirm()} disabled={!picked || busy}>Check answer</button>
          )}
        </>
      )}
    </div>
  );
}

function LabelDecode() {
  const [quiz, setQuiz] = useState<StoredLabelQuiz | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setError("");
    setQuiz(null);
    setPicked(null);
    setChecked(false);
    try {
      setQuiz(await getLabelQuiz());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load a label.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const correct = quiz && picked ? matches(picked, quiz.correct_answer) : false;

  if (!quiz && !error) return <p className="quiet">{busy ? "Reading the label…" : "Fetching a label…"}</p>;

  return (
    <div className="stack">
      <p className="lede">One label, one question. The photo is the one this card was written from.</p>
      {error && <p className="banner">{error}</p>}
      {quiz && (
        <>
          {quiz.image_url && <img className="quiz-photo" src={quiz.image_url} alt="" />}
          <h2>{quiz.question}</h2>
          {quiz.options.map((option) => {
            let tone = "choice";
            if (checked && matches(option, quiz.correct_answer)) tone = "choice right";
            else if (checked && picked === option) tone = "choice wrong";
            else if (picked === option) tone = "choice selected";
            return (
              <button key={option} className={tone} disabled={checked} onClick={() => setPicked(option)}>
                {option}
              </button>
            );
          })}
          {checked && (
            <div className={correct ? "banner ok" : "banner"}>
              <strong>{correct ? "Correct" : "Not quite"}</strong>
              <p>{quiz.explanation}</p>
            </div>
          )}
          {checked ? (
            <button className="btn block" onClick={() => void load()} disabled={busy}>Another label</button>
          ) : (
            <button className="btn block" disabled={!picked || busy} onClick={() => setChecked(true)}>Check answer</button>
          )}
        </>
      )}
    </div>
  );
}
