import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Article, getArticles, getBonus, markBonusRead } from "../api";
import { announceMedals } from "../medals";
import { STRUCTURE_CARDS } from "../words";

const TABS = ["All", "Words", "Term", "Region", "New", "Bonus"] as const;
type Tab = (typeof TABS)[number];

export function StudyPage() {
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find((name) => name === params.get("tab")) ?? "All") as Tab;
  const [articles, setArticles] = useState<Article[]>([]);
  const [read, setRead] = useState<Set<number>>(new Set());
  const [bonusNote, setBonusNote] = useState("");
  const [open, setOpen] = useState<Article | null>(null);
  const [error, setError] = useState("");

  function setTab(name: Tab) {
    setParams({ tab: name });
  }

  useEffect(() => {
    setError("");
    if (tab === "Words") return;
    if (tab === "Bonus") {
      getBonus()
        .then((data) => {
          setBonusNote(data.status);
          setRead(new Set(data.articles.filter((a) => a.read).map((a) => a.id)));
          setArticles(data.articles.map((a) => ({ ...a, category: "Bonus" })));
        })
        .catch((err: Error) => setError(err.message));
      return;
    }
    const category = tab === "All" ? undefined : tab;
    getArticles(category)
      .then((data) => setArticles(data.articles.filter((a) => tab !== "All" || a.category !== "Bonus")))
      .catch((err: Error) => setError(err.message));
  }, [tab]);

  function openArticle(article: Article) {
    setOpen(article);
    if (article.category === "Bonus" && !read.has(article.id)) {
      markBonusRead(article.id)
        .then((result) => {
          setRead(new Set([...read, article.id]));
          announceMedals(result.new_medals);
        })
        .catch(() => undefined);
    }
  }

  if (open) {
    return (
      <main className="screen">
        <button className="back" onClick={() => setOpen(null)}>Back to reading</button>
        <p className="kicker">{open.category}</p>
        <h1>{open.title}</h1>
        {open.image && <img className="hero" src={open.image} alt="" />}
        {open.content.trim().split(/\n\n+/).filter(Boolean).map((paragraph) => (
          <p className="prose" key={paragraph.slice(0, 40)}>{paragraph}</p>
        ))}
      </main>
    );
  }

  return (
    <main className="screen">
      <p className="kicker">Study</p>
      <h1>Reading table</h1>
      <div className="tabs">
        {TABS.map((name) => (
          <button key={name} className={name === tab ? "tab active" : "tab"} onClick={() => setTab(name)}>
            {name}
          </button>
        ))}
      </div>
      {error && <p className="banner">{error}</p>}
      {tab === "Words" ? (
        <div className="stack">
          <p className="lede">What you feel, the word people use, and one reason it happens.</p>
          {STRUCTURE_CARDS.map((card) => (
            <div key={card.word} className="card word-card">
              <small className="meta">You feel</small>
              <p>{card.feel}</p>
              <small className="meta">People say</small>
              <strong>{card.word}</strong>
              <small className="meta">Because</small>
              <p>{card.why}</p>
            </div>
          ))}
        </div>
      ) : (
      <div className="stack">
        {tab === "Bonus" && <p className="lede">Optional reading toward the advanced levels. Not graded. {bonusNote}</p>}
        {articles.map((article) => (
          <button key={article.id} className="article" onClick={() => openArticle(article)}>
            {article.image && <img src={article.image} alt="" />}
            <small>{article.category}{article.category === "Bonus" && read.has(article.id) ? " · read" : ""}</small>
            <strong>{article.title}</strong>
            {article.match && article.match.length > 0 && (
              <p className="quiet">Because you asked about {article.match.slice(0, 3).join(", ")}</p>
            )}
            <p>{article.content.trim()}</p>
          </button>
        ))}
        {!error && articles.length === 0 && <p className="quiet">Nothing in this section yet.</p>}
      </div>
      )}
    </main>
  );
}
