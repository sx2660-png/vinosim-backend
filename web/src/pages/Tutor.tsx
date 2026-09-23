import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AgentReply, WineLabel, askSommelier, chatHistory, scanLabel } from "../api";
import { CellarWine, loadCellar, saveCellar } from "../cellar";

type Mode = "correction" | "roleplay";
type Turn = { role: "user" | "assistant"; text: string; note?: string };

function replyText(reply: AgentReply) {
  return reply.answer || reply.reply || "";
}

function replyNote(reply: AgentReply) {
  const sources = reply.sources?.filter(Boolean) ?? [];
  if (sources.length) return `From ${sources.join(", ")}`;
  if (reply.emotion) return reply.emotion;
  return "";
}

export function TutorPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("correction");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [label, setLabel] = useState<WineLabel | null>(null);

  useEffect(() => {
    setError("");
    setLabel(null);
    chatHistory(mode)
      .then((data) => {
        setTurns(data.messages.map((message) => ({
          role: message.role === "assistant" ? "assistant" : "user",
          text: message.content,
        })));
      })
      .catch((err: Error) => setError(err.message));
  }, [mode]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    setDraft("");
    setError("");
    setTurns((current) => [...current, { role: "user", text: message }]);
    setBusy(true);
    try {
      const reply = await askSommelier(mode, message);
      setTurns((current) => [...current, { role: "assistant", text: replyText(reply), note: replyNote(reply) }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The tutor could not answer.");
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void send(draft);
  }

  async function onScan(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      setLabel(await scanLabel(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read that label.");
    } finally {
      setBusy(false);
    }
  }

  function keepLabel() {
    if (!label) return;
    const wine: CellarWine = {
      id: Date.now().toString(),
      name: label.wine_name || label.producer || "Untitled bottle",
      grape: label.grape_varieties.join(", "),
      region: label.region,
      year: label.vintage,
      date: new Date().toISOString().slice(0, 10),
      notes: label.notes,
      rating: 0,
    };
    saveCellar([wine, ...loadCellar()]);
    navigate("/cellar");
  }

  const labelLine = label
    ? [label.wine_name || label.producer, label.vintage, label.region, label.grape_varieties.join(", ")]
        .filter(Boolean)
        .join(" · ")
    : "";

  return (
    <main className="screen chat-screen">
      <p className="kicker">Tutor</p>
      <h1>{mode === "correction" ? "Ask plainly." : "At the bar."}</h1>
      <div className="tabs">
        <button className={mode === "correction" ? "tab active" : "tab"} onClick={() => setMode("correction")}>Correction</button>
        <button className={mode === "roleplay" ? "tab active" : "tab"} onClick={() => setMode("roleplay")}>Roleplay</button>
      </div>
      <div className="thread">
        {turns.length === 0 && <p className="quiet">Try “why does this red wine feel so drying?”</p>}
        {turns.map((turn, index) => (
          <div key={`${turn.role}-${index}`} className={turn.role === "user" ? "bubble user" : "bubble"}>
            <span className="who">{turn.role === "user" ? "You" : mode === "roleplay" ? "Sommelier" : "Tutor"}</span>
            {turn.text}
            {turn.note && <p className="quiet">{turn.note}</p>}
          </div>
        ))}
      </div>
      {label && (
        <div className="card label-card">
          <strong>{label.wine_name || label.producer || "Label"}</strong>
          <p>{labelLine}</p>
          <div className="row" style={{ marginTop: 12 }}>
            <button className="btn" onClick={() => void send(`Tell me about this bottle: ${labelLine}`)}>Ask about it</button>
            <button className="btn secondary" onClick={keepLabel}>Save</button>
          </div>
        </div>
      )}
      {error && <p className="banner">{error}</p>}
      <form className="composer" onSubmit={onSubmit}>
        <input
          value={draft}
          placeholder={busy ? "Thinking…" : "Ask something"}
          onChange={(event) => setDraft(event.target.value)}
        />
        <button className="btn" disabled={busy || !draft.trim()}>Send</button>
      </form>
      <label className="btn secondary block" style={{ display: "block", textAlign: "center", marginTop: 10 }}>
        Scan a label
        <input hidden type="file" accept="image/*" onChange={(event) => void onScan(event.target.files?.[0])} />
      </label>
    </main>
  );
}
