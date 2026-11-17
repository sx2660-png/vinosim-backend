import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AgentReply,
  SheetDraft,
  SheetLine,
  TastingPrompt,
  WineLabel,
  askSommelier,
  chatHistory,
  getPrompts,
  saveSheet,
  scanLabel,
} from "../api";
import { CellarWine, loadCellar, saveCellar } from "../cellar";
import { announceMedals } from "../medals";
import { MISSING_TEXT, SHEET_LINES } from "../words";

type Mode = "correction" | "roleplay";
type Turn = { role: "user" | "assistant"; text: string; note?: string };

const DRAFT_KEY = "vinosim_sheet_draft";
const EMPTY: SheetDraft = { wine_name: "", appearance: "", nose: "", palate: "", palate_because: "", liking: "" };

function replyText(reply: AgentReply) {
  return reply.answer || reply.reply || "";
}

function replyNote(reply: AgentReply) {
  const sources = reply.sources?.filter(Boolean) ?? [];
  if (sources.length) return `From ${sources.join(", ")}`;
  if (reply.emotion) return reply.emotion;
  return "";
}

function loadDraft(): SheetDraft {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? { ...EMPTY, ...(JSON.parse(raw) as SheetDraft) } : EMPTY;
  } catch {
    return EMPTY;
  }
}

function storeDraft(draft: SheetDraft) {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {
    /* the draft just won't survive a reload */
  }
}

export function TutorPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("correction");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [label, setLabel] = useState<WineLabel | null>(null);

  const [sheet, setSheet] = useState<SheetDraft>(loadDraft);
  const [step, setStep] = useState(0);
  const [showSheet, setShowSheet] = useState(true);
  const [missing, setMissing] = useState<string[] | null>(null);
  const [savedComplete, setSavedComplete] = useState(false);
  const [nosePrompt, setNosePrompt] = useState<TastingPrompt | null>(null);

  const line = SHEET_LINES[step];

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

  useEffect(() => {
    getPrompts("nose")
      .then((data) => {
        const list = data.prompts;
        if (list.length) setNosePrompt(list[Math.floor(Math.random() * list.length)]);
      })
      .catch(() => setNosePrompt(null));
  }, []);

  function updateSheet(patch: Partial<SheetDraft>) {
    const next = { ...sheet, ...patch };
    setSheet(next);
    storeDraft(next);
    setMissing(null);
    setSavedComplete(false);
  }

  async function send(text: string, sheetStep?: SheetLine) {
    const message = text.trim();
    if (!message || busy) return;
    setDraft("");
    setError("");
    setTurns((current) => [...current, { role: "user", text: message }]);
    setBusy(true);
    try {
      const reply = await askSommelier(mode, message, mode === "correction" ? sheetStep : undefined);
      setTurns((current) => [...current, { role: "assistant", text: replyText(reply), note: replyNote(reply) }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The tutor could not answer.");
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void send(draft, showSheet ? line.key : undefined);
  }

  function askAboutLine() {
    const written = sheet[line.key].trim();
    const text = written
      ? `For the ${line.title.toLowerCase()} line I wrote: "${written}". Can you help me put it into words?`
      : `I'm on the ${line.title.toLowerCase()} line and not sure what to write.`;
    void send(text, line.key);
  }

  async function onSave() {
    setBusy(true);
    setError("");
    try {
      const saved = await saveSheet(sheet);
      setMissing(saved.missing);
      setSavedComplete(saved.sheet.complete);
      const firstGap = saved.missing[0]?.startsWith("palate") ? "palate" : saved.missing[0];
      const gapStep = SHEET_LINES.findIndex((item) => item.key === firstGap);
      if (gapStep >= 0) setStep(gapStep);
      announceMedals(saved.new_medals);
      updateSheetId(saved.sheet.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the sheet.");
    } finally {
      setBusy(false);
    }
  }

  function updateSheetId(id: number) {
    const next = { ...sheet, id };
    setSheet(next);
    storeDraft(next);
  }

  function newSheet() {
    setSheet(EMPTY);
    storeDraft(EMPTY);
    setStep(0);
    setMissing(null);
    setSavedComplete(false);
  }

  async function onScan(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const read = await scanLabel(file);
      setLabel(read);
      if (!sheet.wine_name) updateSheet({ wine_name: read.wine_name || read.producer || "" });
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
    <main className={mode === "correction" && showSheet ? "screen chat-screen with-sheet" : "screen chat-screen"}>
      <p className="kicker">Tutor</p>
      <h1>{mode === "correction" ? "Let’s taste together." : "At the table."}</h1>
      <div className="tabs">
        <button className={mode === "correction" ? "tab active" : "tab"} onClick={() => setMode("correction")}>Tasting</button>
        <button className={mode === "roleplay" ? "tab active" : "tab"} onClick={() => setMode("roleplay")}>Roleplay</button>
      </div>
      {mode === "roleplay" && (
        <p className="quiet">Practise saying a sentence or two at dinner. Nothing here is graded.</p>
      )}
      <div className="thread">
        {turns.length === 0 && (
          <p className="quiet">
            {mode === "correction"
              ? "Take your time. Write what you notice on the sheet below, or ask “why does this red feel so drying?”"
              : "Try “this red feels a bit drying on my gums.”"}
          </p>
        )}
        {turns.map((turn, index) => (
          <div key={`${turn.role}-${index}`} className={turn.role === "user" ? "bubble user" : "bubble"}>
            <span className="who">{turn.role === "user" ? "You" : mode === "roleplay" ? "Guest" : "Tutor"}</span>
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

      {mode === "correction" && (
        <section className="card sheet">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <small className="meta">Your tasting sheet</small>
            <button className="back" onClick={() => setShowSheet(!showSheet)}>{showSheet ? "Hide" : "Show"}</button>
          </div>
          {showSheet && (
            <>
              <div className="steps">
                {SHEET_LINES.map((item, index) => (
                  <button
                    key={item.key}
                    className={index === step ? "step active" : sheet[item.key].trim() ? "step done" : "step"}
                    onClick={() => setStep(index)}
                  >
                    {sheet[item.key].trim() && index !== step ? "✓ " : ""}{item.step}
                  </button>
                ))}
              </div>
              {step === 0 && (
                <input
                  className="sheet-input"
                  value={sheet.wine_name}
                  placeholder="Which wine? (optional)"
                  onChange={(event) => updateSheet({ wine_name: event.target.value })}
                />
              )}
              <strong>{line.ask}</strong>
              {line.key === "nose" && nosePrompt && <p className="quiet">{nosePrompt.prompt}</p>}
              <textarea
                className="sheet-input"
                rows={2}
                value={sheet[line.key]}
                placeholder="What I sense, in my own words"
                onChange={(event) => updateSheet({ [line.key]: event.target.value })}
              />
              {line.key === "palate" && (
                <input
                  className="sheet-input"
                  value={sheet.palate_because}
                  placeholder="because… (optional)"
                  onChange={(event) => updateSheet({ palate_because: event.target.value })}
                />
              )}
              <p className="quiet">Common words people use: {line.common}</p>
              {missing && missing.length > 0 && (
                <div className="banner">
                  {missing.map((key) => <p key={key}>{MISSING_TEXT[key] ?? key}</p>)}
                </div>
              )}
              {savedComplete && <p className="banner ok">Sheet complete. It counts toward Level 1 and is kept in Cellar.</p>}
              <div className="row sheet-actions">
                <button className="btn secondary" onClick={askAboutLine} disabled={busy}>Ask about this line</button>
                {step < SHEET_LINES.length - 1 ? (
                  <button className="btn" onClick={() => setStep(step + 1)}>Next</button>
                ) : savedComplete ? (
                  <button className="btn" onClick={newSheet}>New sheet</button>
                ) : (
                  <button className="btn" onClick={() => void onSave()} disabled={busy}>Save sheet</button>
                )}
              </div>
            </>
          )}
        </section>
      )}

      {error && <p className="banner">{error}</p>}
      <form className="composer" onSubmit={onSubmit}>
        <input
          value={draft}
          placeholder={busy ? "Thinking…" : mode === "correction" ? "Ask the tutor" : "Say something"}
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
