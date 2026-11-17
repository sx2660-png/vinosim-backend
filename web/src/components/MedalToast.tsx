import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { medalName } from "../medals";

export function MedalToast() {
  const [ids, setIds] = useState<string[]>([]);

  useEffect(() => {
    function onMedals(event: Event) {
      setIds((event as CustomEvent<string[]>).detail);
    }
    window.addEventListener("vinosim:medals", onMedals);
    return () => window.removeEventListener("vinosim:medals", onMedals);
  }, []);

  if (ids.length === 0) return null;

  return (
    <div className="toast" role="status">
      <strong>{ids.length === 1 ? "New medal" : "New medals"}</strong>
      {ids.map((id) => (
        <p key={id}>{medalName(id)}</p>
      ))}
      <div className="row" style={{ marginTop: 8 }}>
        <Link className="btn" to="/levels" onClick={() => setIds([])}>See your path</Link>
        <button className="btn secondary" onClick={() => setIds([])}>Close</button>
      </div>
    </div>
  );
}
