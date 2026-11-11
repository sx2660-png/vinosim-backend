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
      <h1>Wine is better when you get it.</h1>
      <p className="lede">A few minutes with the glass in front of you. One note, then one question.</p>
      {offline && <p className="banner">The API is not responding.</p>}
      <div className="actions">
        <Link className="btn" to="/quiz">Start exploring</Link>
        <Link className="btn secondary" to="/tutor">Taste together</Link>
      </div>
      <div className="stack" style={{ marginTop: 28 }}>
        {articles.map((article) => (
          <Link key={article.id} className="article" to="/study">
            {article.image && <img src={article.image} alt="" />}
            <small>{article.category}</small>
            <strong>{article.title}</strong>
            <p>{article.content.trim()}</p>
          </Link>
        ))}
      </div>
    </main>
  );
}
