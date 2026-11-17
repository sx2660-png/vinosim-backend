import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Progress, getProgress } from "../api";
import { announceMedals } from "../medals";

function useProgress() {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    getProgress()
      .then((data) => {
        setProgress(data);
        announceMedals(data.new_medals);
      })
      .catch((err: Error) => setError(err.message));
  }, []);
  return { progress, error };
}

function Bar({ value, max }: { value: number; max: number }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  return (
    <div className="bar" role="progressbar" aria-valuenow={value} aria-valuemax={max}>
      <i style={{ width: `${pct}%` }} />
    </div>
  );
}

function examLine(exam: Progress["level1"]["exam"]) {
  if (!exam) return "Exam: not taken yet";
  return `Exam: ${exam.score}/${exam.total}${exam.passed ? " · passed" : " · not passed yet"}`;
}

// Compact version for Home.
export function LevelsPanel() {
  const { progress } = useProgress();
  if (!progress) return null;
  const { level1, level2 } = progress;
  return (
    <Link className="card path-card" to="/levels">
      <small className="meta">Your path</small>
      <div className="path-row">
        <span className={level1.medal ? "medal on" : "medal"}>1</span>
        <div>
          <strong>Talk about the glass</strong>
          <p>{level1.sheets_complete}/{level1.sheets_needed} sheets · {level1.exam?.passed ? "exam passed" : "exam to do"}</p>
        </div>
      </div>
      <div className="path-row">
        <span className={level2.medal ? "medal on" : "medal"}>2</span>
        <div>
          <strong>Read the bottle</strong>
          <p>
            {level2.unlocked
              ? `${level2.labels_done}/${level2.labels_needed} labels · ${level2.exam?.passed ? "exam passed" : "exam to do"}`
              : "Opens after the Level 1 medal"}
          </p>
        </div>
      </div>
    </Link>
  );
}

export function LevelsPage() {
  const { progress, error } = useProgress();

  return (
    <main className="screen">
      <Link className="back" to="/">Back</Link>
      <p className="kicker">Your path</p>
      <h1>Two levels, two medals.</h1>
      <p className="lede">Each medal stands for something you can now do, not for time spent in the app.</p>
      {error && <p className="banner">{error}</p>}
      {!progress && !error && <p className="quiet">Loading your progress…</p>}
      {progress && (
        <div className="stack" style={{ marginTop: 18 }}>
          <section className="card level">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <small className="meta">Level 1</small>
              {progress.level1.medal && <span className="medal on">Medal</span>}
            </div>
            <h2>Talk about the glass</h2>
            <p>Describe a wine in your own words: how it looks, smells and feels, and whether you like it.</p>
            <p className="quiet">Tasting sheets: {progress.level1.sheets_complete}/{progress.level1.sheets_needed}</p>
            <Bar value={progress.level1.sheets_complete} max={progress.level1.sheets_needed} />
            <p className="quiet">{examLine(progress.level1.exam)}</p>
            <div className="row" style={{ marginTop: 10 }}>
              <Link className="btn" to="/tutor">Write a sheet</Link>
              <Link className="btn secondary" to="/quiz?tab=exam&level=1">Level 1 exam</Link>
            </div>
          </section>

          <section className={progress.level2.unlocked ? "card level" : "card level locked"}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <small className="meta">Level 2</small>
              {progress.level2.medal && <span className="medal on">Medal</span>}
            </div>
            <h2>Read the bottle</h2>
            <p>Labels, grapes and regions, sparkling and fortified wines, serving and food.</p>
            {progress.level2.unlocked ? (
              <>
                <p className="quiet">Label tasks: {progress.level2.labels_done}/{progress.level2.labels_needed}</p>
                <Bar value={progress.level2.labels_done} max={progress.level2.labels_needed} />
                <p className="quiet">{examLine(progress.level2.exam)}</p>
                <div className="row" style={{ marginTop: 10 }}>
                  <Link className="btn" to="/quiz?tab=labels">Label tasks</Link>
                  <Link className="btn secondary" to="/quiz?tab=exam&level=2">Level 2 exam</Link>
                </div>
              </>
            ) : (
              <p className="quiet">Opens after the Level 1 medal. You can already practise Level 2 questions in Quiz.</p>
            )}
          </section>

          {progress.course_complete && (
            <p className="banner ok">
              Both medals earned. If you would like a formal certificate, a WSET Level 1 course is a natural next step.
            </p>
          )}

          <section className="card level">
            <small className="meta">Bonus · not graded</small>
            <h2>Going further</h2>
            <p>{progress.bonus.status}</p>
            <div className="stack" style={{ marginTop: 10 }}>
              {progress.bonus.articles.map((article) => (
                <div key={article.id} className="row" style={{ justifyContent: "space-between" }}>
                  <span>{article.title}</span>
                  <span className={article.medal ? "medal on small" : "medal small"}>{article.medal ? "Read" : "New"}</span>
                </div>
              ))}
            </div>
            <Link className="btn secondary" style={{ marginTop: 12 }} to="/study?tab=Bonus">Open bonus reading</Link>
          </section>
        </div>
      )}
    </main>
  );
}
