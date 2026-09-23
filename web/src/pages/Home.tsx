import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Article, checkHealth, getArticles } from "../api";

export function HomePage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    checkHealth().then(() => setOffline(false)).catch(() => setOffline(true));
    getArticles().then((data) => setArticles(data.articles.slice(0, 3))).catch(() => setArticles([]));
  }, []);

  return (
    <main className="screen">
      <p className="kicker">VinoSim</p>
      <h1>A quieter way to learn wine.</h1>
      <p className="lede">Short lessons, one question at a time, and a sommelier who will stay with the glass in front of you.</p>
      {offline && <p className="banner">The local API is not responding.</p>}
      <div className="actions">
        <Link className="btn" to="/quiz">Take a question</Link>
        <Link className="btn secondary" to="/tutor">Ask the tutor</Link>
      </div>
      <div className="stack" style={{ marginTop: 28 }}>
        <h2>From the reading table</h2>
        {articles.map((article) => (
          <Link key={article.id} className="article" to="/study">
            <small>{article.category}</small>
            <strong>{article.title}</strong>
            <p>{article.content}</p>
          </Link>
        ))}
      </div>
    </main>
  );
}
