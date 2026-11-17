import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  ExamPaper,
  ExamResult,
  LabelQuiz,
  QuizQuestion,
  QuizResult,
  decodeLabel,
  getLabelTasks,
  getQuiz,
  startExam,
  submitExam,
  submitQuiz,
} from "../api";
import { announceMedals } from "../medals";

function letterOf(option: string) {
  const match = option.trim().match(/^([A-D])\b/i);
  return match ? match[1].toUpperCase() : option.trim();
}

function matches(option: string, correct: string) {
  const wanted = correct.trim();
  return option.trim().toLowerCase() === wanted.toLowerCase() || letterOf(option) === wanted.toUpperCase();
}

const TABS = [
  ["practice", "Practice"],
  ["exam", "Exam"],
  ["labels", "Labels"],
  ["photo", "Photo"],
] as const;
type Tab = (typeof TABS)[number][0];

export function QuizPage() {
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find(([key]) => key === params.get("tab"))?.[0] ?? "practice") as Tab;
  const level = params.get("level") === "2" ? 2 : 1;

  function go(next: Tab, nextLevel = level) {
    setParams({ tab: next, level: String(nextLevel) });
  }

  const titles: Record<Tab, string> = {
    practice: "One question",
    exam: `Level ${level} exam`,
    labels: "Read the label",
    photo: "From a photo",
  };

  return (
    <main className="screen">
      <p className="kicker">Quiz</p>
      <h1>{titles[tab]}</h1>
      <div className="tabs">
        {TABS.map(([key, label]) => (
          <button key={key} className={tab === key ? "tab active" : "tab"} onClick={() => go(key)}>
            {label}
          </button>
        ))}
      </div>
      {(tab === "practice" || tab === "exam") && (
        <div className="tabs small">
          {[1, 2].map((n) => (
            <button key={n} className={level === n ? "tab active" : "tab"} onClick={() => go(tab, n)}>
              Level {n}
            </button>
          ))}
        </div>
      )}
      {tab === "practice" && <Practice key={level} level={level} />}
      {tab === "exam" && <Exam key={level} level={level} />}
      {tab === "labels" && <LabelTasks />}
      {tab === "photo" && <LabelDecode />}
    </main>
  );
}

function QuestionCard({ question, onAnswered }: { question: QuizQuestion; onAnswered?: (result: QuizResult) => void }) {
  const [picked, setPicked] = useState<string | null>(null);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function confirm() {
    if (!picked) return;
    setBusy(true);
    setError("");
    try {
      const scored = await submitQuiz(question.id, letterOf(picked));
      setResult(scored);
      announceMedals(scored.new_medals);
      onAnswered?.(scored);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not score the answer.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      {error && <p className="banner">{error}</p>}
      {question.category && <p className="meta">{question.category}</p>}
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
        </div>
      )}
      {!result && (
        <button className="btn block" onClick={() => void confirm()} disabled={!picked || busy}>Check answer</button>
      )}
    </div>
  );
}

function Practice({ level }: { level: number }) {
  const [question, setQuestion] = useState<QuizQuestion | null>(null);
  const [answered, setAnswered] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    setAnswered(false);
    setQuestion(null);
    try {
      setQuestion(await getQuiz(level));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load a question.");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [level]);

  if (error) return <p className="banner">{error}</p>;
  if (!question) return <p className="quiet">Fetching a question…</p>;
  return (
    <div className="stack">
      <QuestionCard key={question.id} question={question} onAnswered={() => setAnswered(true)} />
      {answered && <button className="btn block" onClick={() => void load()}>Next question</button>}
    </div>
  );
}

function Exam({ level }: { level: number }) {
  const [paper, setPaper] = useState<ExamPaper | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ExamResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function begin() {
    setBusy(true);
    setError("");
    setResult(null);
    setAnswers({});
    try {
      setPaper(await startExam(level));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the exam.");
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    if (!paper) return;
    const left = paper.questions.length - Object.keys(answers).length;
    if (left > 0 && !window.confirm(`${left} question(s) are still blank and will count as wrong. Hand in anyway?`)) return;
    setBusy(true);
    setError("");
    try {
      const graded = await submitExam(paper.attempt_id, answers);
      setResult(graded);
      announceMedals(graded.new_medals);
      document.querySelector(".screen")?.scrollTo({ top: 0 });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not hand in the exam.");
    } finally {
      setBusy(false);
    }
  }

  if (result && paper) {
    const wrong = result.review.filter((item) => !item.correct);
    const byId = new Map(paper.questions.map((q) => [q.id, q]));
    return (
      <div className="stack">
        <div className={result.passed ? "banner ok" : "banner"}>
          <strong>{result.score}/{result.total} · {result.passed ? "Passed" : "Not passed yet"}</strong>
          <p>The pass mark is {result.pass_pct}%. {result.passed ? "" : "You can take it again whenever you like."}</p>
        </div>
        {wrong.length > 0 && <h2>Worth another look</h2>}
        {wrong.map((item) => (
          <div key={item.id} className="card">
            <strong>{byId.get(item.id)?.question}</strong>
            <p>Answer: {byId.get(item.id)?.options.find((o) => matches(o, item.correct_answer)) ?? item.correct_answer}</p>
            <p>{item.explanation}</p>
          </div>
        ))}
        <button className="btn block" onClick={() => void begin()} disabled={busy}>Take it again</button>
      </div>
    );
  }

  if (!paper) {
    return (
      <div className="stack">
        <p className="lede">
          {level === 1 ? "30 questions" : "50 questions"}, no time limit. The pass mark is {level === 1 ? "70%" : "55%"}, like
          the WSET Level {level} exam. You see the explanations when you hand in.
        </p>
        {error && <p className="banner">{error}</p>}
        <button className="btn block" onClick={() => void begin()} disabled={busy}>
          {busy ? "Preparing…" : "Start the exam"}
        </button>
      </div>
    );
  }

  const done = Object.keys(answers).length;
  return (
    <div className="stack">
      <p className="quiet">{done}/{paper.questions.length} answered</p>
      {paper.questions.map((question, index) => (
        <div key={question.id} className="card exam-q">
          <small className="meta">Question {index + 1}</small>
          {question.image && <img className="quiz-photo" src={question.image} alt="" />}
          <strong>{question.question}</strong>
          <div className="stack" style={{ marginTop: 10 }}>
            {question.options.map((option) => (
              <button
                key={option}
                className={answers[String(question.id)] === letterOf(option) ? "choice selected" : "choice"}
                onClick={() => setAnswers({ ...answers, [String(question.id)]: letterOf(option) })}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      ))}
      {error && <p className="banner">{error}</p>}
      <button className="btn block" onClick={() => void finish()} disabled={busy}>Hand in</button>
    </div>
  );
}

function LabelTasks() {
  const [data, setData] = useState<Awaited<ReturnType<typeof getLabelTasks>> | null>(null);
  const [open, setOpen] = useState<QuizQuestion | null>(null);
  const [error, setError] = useState("");

  function refresh() {
    getLabelTasks().then(setData).catch((err: Error) => setError(err.message));
  }

  useEffect(refresh, []);

  if (open) {
    return (
      <div className="stack">
        <button className="back" onClick={() => { setOpen(null); refresh(); }}>Back to label tasks</button>
        <QuestionCard question={open} />
      </div>
    );
  }

  return (
    <div className="stack">
      <p className="lede">Answer five different label questions correctly to complete the Level 2 label tasks.</p>
      {error && <p className="banner">{error}</p>}
      {data && (
        <>
          <p className="quiet">{Math.min(data.done, data.needed)}/{data.needed} done</p>
          {data.tasks.map((task) => (
            <button key={task.id} className={task.done ? "choice right" : "choice"} onClick={() => setOpen(task)}>
              {task.done ? "✓ " : ""}{task.question}
            </button>
          ))}
        </>
      )}
    </div>
  );
}

function LabelDecode() {
  const [quiz, setQuiz] = useState<LabelQuiz | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState("");

  async function onFile(file: File | undefined) {
    if (!file) return;
    setPreview((current) => {
      if (current) URL.revokeObjectURL(current);
      return URL.createObjectURL(file);
    });
    setBusy(true);
    setError("");
    setQuiz(null);
    setPicked(null);
    setChecked(false);
    try {
      setQuiz(await decodeLabel(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read that label.");
    } finally {
      setBusy(false);
    }
  }

  const correct = quiz && picked ? matches(picked, quiz.correct_answer) : false;

  return (
    <div className="stack">
      <p className="lede">Upload a label photo. The question is written from what is actually printed. Practice only: it does not count toward the label tasks.</p>
      <label className="btn secondary" style={{ textAlign: "center" }}>
        {busy ? "Reading…" : "Choose a photo"}
        <input hidden type="file" accept="image/*" onChange={(event) => void onFile(event.target.files?.[0])} />
      </label>
      {error && <p className="banner">{error}</p>}
      {preview && <img className="quiz-photo" src={preview} alt="The label you chose" />}
      {quiz && (
        <>
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
          {!checked && (
            <button className="btn block" disabled={!picked} onClick={() => setChecked(true)}>Check answer</button>
          )}
        </>
      )}
    </div>
  );
}
