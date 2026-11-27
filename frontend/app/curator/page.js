"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Curator() {
  const [items, setItems] = useState([]);
  const [name, setName] = useState("");

  const [changes, setChanges] = useState(null);
  const [key, setKey] = useState(null);       // curator key, kept for this browser tab only
  const [keyInput, setKeyInput] = useState("");
  const [error, setError] = useState("");

  async function load(k = key) {
    if (!k) return;
    const res = await fetch(`${API}/api/curator/pending`, { headers: { "X-Curator-Key": k } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { setKey(null); sessionStorage.removeItem("scholarfit_curator_key"); return setError(data.detail || "Access refused"); }
    setError(""); setKey(k); sessionStorage.setItem("scholarfit_curator_key", k); setItems(data);
    fetch(`${API}/api/changes`).then(r => r.json()).then(setChanges).catch(() => {});
  }
  useEffect(() => { const k = sessionStorage.getItem("scholarfit_curator_key"); if (k) load(k); }, []);

  async function review(cid, approve) {
    await fetch(`${API}/api/curator/review/${cid}`, { method: "POST", headers: { "Content-Type": "application/json", "X-Curator-Key": key }, body: JSON.stringify({ reviewer: name || "curator", approve }) });
    load();
  }

  if (!key) return (
    <div className="card" style={{ maxWidth: 520 }}>
      <h1>Curator sign-in</h1>
      <p className="muted">This page is for the ScholarFit team, not for students. Curators check criteria the AI extracted from scholarship calls before students see them.</p>
      <form onSubmit={e => { e.preventDefault(); load(keyInput.trim()); }}>
        <label>Curator key</label>
        <input type="password" value={keyInput} onChange={e => setKeyInput(e.target.value)} autoFocus />
        <div style={{ marginTop: 12 }}><button type="submit" disabled={!keyInput.trim()}>Sign in</button></div>
      </form>
      {error && <p className="error">{error}</p>}
      <p className="muted small" style={{ marginTop: 16 }}><a href="/">Back to the student portal</a></p>
    </div>
  );

  const changed = changes?.changed || [];
  return (
    <>
    <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
      <span className="pill">Signed in as curator</span>
      <button className="secondary small" onClick={() => { sessionStorage.removeItem("scholarfit_curator_key"); setKey(null); setItems([]); }}>Sign out</button>
    </div>
    <div className="card">
      <h1>Programme pages that changed</h1>
      <p className="muted">From <code>python ingest/check_changes.py</code>{changes?.checked_at ? `, last run ${changes.checked_at.replace("T", " ")}` : ""}. Re-extract the criteria of these programmes and approve them below; until then students see a &quot;criteria under review&quot; badge.</p>
      {changed.length === 0 && (changes?.new || []).length === 0 && <p className="muted">No changed pages.</p>}
      {(changed.length > 0 || (changes?.new || []).length > 0) && (
        <table><tbody>
          {changed.map(c => (
            <tr key={c.programme_id}><td><strong>{c.programme_id}</strong></td>
              <td><span className="badge changed">Changed</span>{c.simulated && <span className="muted small"> (simulated for the demo)</span>}</td>
              <td className="muted">{c.old_snapshot ? `snapshot ${c.old_snapshot} → ${c.new_snapshot}` : `changed on ${c.new_snapshot || "unknown date"}`}</td>
              <td className="muted small">python scripts/build_catalogue.py, then review</td></tr>))}
          {(changes?.new || []).map(pid => (
            <tr key={"n" + pid}><td><strong>{pid}</strong></td><td><span className="badge eligible">New</span></td><td colSpan={2} className="muted">extract and review its criteria</td></tr>))}
        </tbody></table>
      )}
    </div>
    <div className="card">
      <h1>Criteria waiting for review</h1>
      <p className="muted">Criteria marked manual check, or whose quote could not be found in the call, are hidden from students until a person approves them.</p>
      <div style={{ maxWidth: 280, margin: "12px 0" }}><label>Your name</label><input value={name} onChange={e => setName(e.target.value)} /></div>
      {items.length === 0 && <p className="muted">Nothing to review.</p>}
      <table><tbody>{items.map(it => (
        <tr key={it.criterion_id}>
          <td><strong>{it.programme_id}</strong><div className="muted">{it.criterion.type} · {it.criterion.handling} · extracted by {it.model}</div></td>
          <td>{it.criterion.text}<div className="quote">“{it.criterion.source_quote}”</div></td>
          <td className="row"><button className="accent small" onClick={() => review(it.criterion_id, true)}>Approve</button>
            <button className="secondary small" onClick={() => review(it.criterion_id, false)}>Reject</button></td>
        </tr>))}</tbody></table>
    </div>
    </>
  );
}
