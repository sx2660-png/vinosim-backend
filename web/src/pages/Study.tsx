import { useEffect, useState } from "react";
import { Article, getArticles } from "../api";

const TABS = ["All", "Term", "Region", "New"] as const;

export function StudyPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("All");
  const [articles, setArticles] = useState<Article[]>([]);
  const [open, setOpen] = useState<Article | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    const category = tab === "All" ? undefined : tab;
    getArticles(category)
      .then((data) => setArticles(data.articles))
      .catch((err: Error) => setError(err.message));
  }, [tab]);

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
      <div className="stack">
        {articles.map((article) => (
          <button key={article.id} className="article" onClick={() => setOpen(article)}>
            {article.image && <img src={article.image} alt="" />}
            <small>{article.category}</small>
            <strong>{article.title}</strong>
            {article.match && article.match.length > 0 && (
              <p className="quiet">Because you asked about {article.match.slice(0, 3).join(", ")}</p>
            )}
            <p>{article.content.trim()}</p>
          </button>
        ))}
        {!error && articles.length === 0 && <p className="quiet">Nothing in this section yet.</p>}
      </div>
    </main>
  );
}
