import { ReactNode, useState } from "react";

const KEY = "vinosim_age_ok";

function readOk() {
  try {
    return localStorage.getItem(KEY) === "yes";
  } catch {
    return false;
  }
}

export function AgeGate({ children }: { children: ReactNode }) {
  const [ok, setOk] = useState(readOk);
  const [under, setUnder] = useState(false);

  if (ok) return <>{children}</>;

  function confirm() {
    try {
      localStorage.setItem(KEY, "yes");
    } catch {
      /* still let them in for this visit */
    }
    setOk(true);
  }

  return (
    <div className="app">
      <main className="screen gate">
        <p className="kicker">VinoSim</p>
        {under ? (
          <>
            <h1>Come back later.</h1>
            <p className="lede">VinoSim is about tasting wine, so it is only for adults of legal drinking age.</p>
          </>
        ) : (
          <>
            <h1>Before we pour.</h1>
            <p className="lede">
              VinoSim is for adults of legal drinking age where you live (21 or older in the US).
            </p>
            <p className="card gate-note">
              Tasting is about small sips. Spitting is completely fine, and so is learning without drinking at all.
            </p>
            <div className="actions">
              <button className="btn" onClick={confirm}>I’m of legal age</button>
              <button className="btn secondary" onClick={() => setUnder(true)}>I’m not</button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
