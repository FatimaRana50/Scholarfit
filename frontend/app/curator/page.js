"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Curator() {
  const [items, setItems] = useState([]);
  const [name, setName] = useState("");

  const load = () => fetch(`${API}/api/curator/pending`).then(r => r.json()).then(setItems);
  useEffect(() => { load(); }, []);

  async function review(cid, approve) {
    await fetch(`${API}/api/curator/review/${cid}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reviewer: name || "curator", approve }) });
    load();
  }

  return (
    <div className="card">
      <h1>Criteria waiting for review</h1>
      <p className="muted">Criteria marked manual check, or whose quote could not be found in the call, are hidden from students until a person approves them.</p>
      <div style={{ maxWidth: 280, margin: "12px 0" }}><label>Your name</label><input value={name} onChange={e => setName(e.target.value)} /></div>
      {items.length === 0 && <p className="muted">Nothing to review.</p>}
      <table><tbody>{items.map(it => (
        <tr key={it.criterion_id}>
          <td><strong>{it.programme_id}</strong><div className="muted">{it.criterion.type} · {it.criterion.handling} · extracted by {it.model}</div></td>
          <td>{it.criterion.text}<div className="quote">“{it.criterion.source_quote}”</div></td>
          <td className="row"><button onClick={() => review(it.criterion_id, true)}>Approve</button>
            <button className="secondary" onClick={() => review(it.criterion_id, false)}>Reject</button></td>
        </tr>))}</tbody></table>
    </div>
  );
}
