import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sheet, getSheets } from "../api";
import { CellarWine, loadCellar, saveCellar } from "../cellar";

const empty = { name: "", grape: "", region: "", year: "", notes: "", rating: 3 };

export function CellarPage() {
  const [wines, setWines] = useState<CellarWine[]>(() => loadCellar());
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState(empty);
  const [sheets, setSheets] = useState<Sheet[]>([]);

  useEffect(() => {
    getSheets().then((data) => setSheets(data.sheets)).catch(() => setSheets([]));
  }, []);

  function persist(next: CellarWine[]) {
    setWines(next);
    saveCellar(next);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!form.name.trim()) return;
    const wine: CellarWine = {
      id: Date.now().toString(),
      name: form.name.trim(),
      grape: form.grape.trim(),
      region: form.region.trim(),
      year: form.year.trim(),
      date: new Date().toISOString().slice(0, 10),
      notes: form.notes.trim(),
      rating: form.rating,
    };
    persist([wine, ...wines]);
    setForm(empty);
    setAdding(false);
  }

  if (adding) {
    return (
      <main className="screen">
        <button className="back" onClick={() => setAdding(false)}>Back</button>
        <h1>Add a bottle</h1>
        <form onSubmit={onSubmit}>
          {(["name", "grape", "region", "year", "notes"] as const).map((field) => (
            <label key={field} className="field">
              <span>{field}</span>
              {field === "notes" ? (
                <textarea rows={3} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
              ) : (
                <input value={form[field]} onChange={(event) => setForm({ ...form, [field]: event.target.value })} />
              )}
            </label>
          ))}
          <div className="field">
            <span>Rating</span>
            <div className="stars">
              {[1, 2, 3, 4, 5].map((score) => (
                <button key={score} type="button" className={score <= form.rating ? "on" : ""} onClick={() => setForm({ ...form, rating: score })}>
                  ★
                </button>
              ))}
            </div>
          </div>
          <button className="btn block" style={{ marginTop: 16 }} disabled={!form.name.trim()}>Save bottle</button>
        </form>
      </main>
    );
  }

  return (
    <main className="screen">
      <p className="kicker">Cellar</p>
      <h1>Your tastings.</h1>
      <p className="lede">Your tasting sheets, and the bottles you kept.</p>
      <h2 style={{ marginTop: 20 }}>Tasting sheets</h2>
      <div className="stack" style={{ marginTop: 10 }}>
        {sheets.length === 0 && (
          <p className="quiet">No sheets yet. <Link to="/tutor">Write one in Tutor.</Link></p>
        )}
        {sheets.map((sheet) => (
          <article key={sheet.id} className="wine">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <strong>{sheet.wine_name || "A glass of wine"}</strong>
              <span className={sheet.complete ? "medal on small" : "medal small"}>{sheet.complete ? "Complete" : "Draft"}</span>
            </div>
            {[["Looks", sheet.appearance], ["Smells", sheet.nose], ["Feels", [sheet.palate, sheet.palate_because && `because ${sheet.palate_because}`].filter(Boolean).join(", ")], ["Like it?", sheet.liking]]
              .filter(([, text]) => text)
              .map(([name, text]) => <p key={name}><b>{name.endsWith("?") ? name : `${name}:`}</b> {text}</p>)}
            <p className="quiet">{sheet.created_at.slice(0, 10)}</p>
          </article>
        ))}
      </div>
      <h2 style={{ marginTop: 24 }}>Bottles</h2>
      <p className="quiet">Stored on this device. Scanning a label can drop one in here.</p>
      <button className="btn" style={{ margin: "16px 0" }} onClick={() => setAdding(true)}>Add a bottle</button>
      <div className="stack">
        {wines.length === 0 && <p className="quiet">The cellar is empty.</p>}
        {wines.map((wine) => (
          <article key={wine.id} className="wine">
            <strong>{wine.name}</strong>
            <p>{[wine.year, wine.grape, wine.region].filter(Boolean).join(" · ")}</p>
            {wine.notes && <p>{wine.notes}</p>}
            <div className="row" style={{ justifyContent: "space-between", marginTop: 8 }}>
              <span className="quiet">{wine.rating ? `${wine.rating}/5` : wine.date}</span>
              <button className="back" onClick={() => persist(wines.filter((item) => item.id !== wine.id))}>Remove</button>
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
