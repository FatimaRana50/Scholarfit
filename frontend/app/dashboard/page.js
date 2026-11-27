"use client";
import { useEffect, useState } from "react";
import { API, Badge, CalendarButtons, DISCLAIMER, LABEL_TEXT, MissingPanel, NoticeBadges, fam, fmtTs, getProfileId, profileLabel, today } from "../lib";

export default function Dashboard() {
  const [pid, setPid] = useState(null);
  const [saved, setSaved] = useState(null);
  const [history, setHistory] = useState([]);
  const [calendar, setCalendar] = useState({ connected: false });
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [changes, setChanges] = useState([]);

  async function load(id = pid) {
    if (!id) return;
    try {
      const [s, h] = await Promise.all([
        fetch(`${API}/api/saved?profile_id=${encodeURIComponent(id)}`).then(r => r.json()),
        fetch(`${API}/api/history?profile_id=${encodeURIComponent(id)}&limit=60`).then(r => r.json()),
      ]);
      setSaved(s); setHistory(h);
    } catch { setError("Could not reach the server"); setSaved([]); }
  }

  const [label, setLabel] = useState(null);

  useEffect(() => {
    const id = getProfileId(); setPid(id); load(id);
    try { setLabel(profileLabel(JSON.parse(localStorage.getItem("scholarfit_profile") || "null"))); } catch {}
    fetch(`${API}/api/calendar/status`).then(r => r.json()).then(setCalendar).catch(() => {});
  }, []);

  async function remove(programmeId) {
    await fetch(`${API}/api/saved/${programmeId}?profile_id=${encodeURIComponent(pid)}`, { method: "DELETE" });
    load();
  }

  // Re-check saved programmes with the last confirmed profile: verdict changes show as "Changed: A → B".
  async function recheck() {
    let profile;
    try { profile = JSON.parse(localStorage.getItem("scholarfit_profile") || "null"); } catch { profile = null; }
    if (!profile) return setError("No confirmed profile in this browser yet. Upload your CV on the Check eligibility page first.");
    setError(""); setChanges([]);
    const found = [];
    for (let i = 0; i < saved.length; i++) {
      setBusy(`Re-checking ${i + 1} of ${saved.length}...`);
      try {
        const res = await fetch(`${API}/api/check`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile: { ...profile, profile_id: pid }, programme_ids: [saved[i].programme_id] }) });
        const data = await res.json();
        if (!res.ok) { setError(data.detail || "Check failed"); break; }
        data.filter(r => r.status_change).forEach(r => found.push(r));
      } catch { setError("Could not reach the server"); break; }
    }
    setChanges(found); setBusy(""); load();
  }

  if (saved === null) return <div className="card"><p className="muted">Loading your dashboard...</p></div>;

  const row = s => s.last_row || {};
  const upcoming = saved.filter(s => s.deadline && !s.outdated).sort((a, b) => a.deadline.localeCompare(b.deadline));
  const withChange = saved.filter(s => s.prev_overall && s.prev_overall !== s.last_overall);
  const openItems = saved.filter(s => (row(s).missing || []).length > 0);
  const nOpen = openItems.reduce((a, s) => a + row(s).missing.length, 0);
  const nChanged = saved.filter(s => s.call_changed).length;

  return (
    <div>
      <div className="topbar">
        <div><h1 style={{ margin: 0 }}>My dashboard</h1>
          {label && <div className="muted small">For the CV you uploaded last: {label}. Uploading another CV starts a new dashboard.</div>}</div>
        <div className="row">
          {busy && <span className="muted">{busy}</span>}
          <button className="accent" disabled={!saved.length || !!busy} onClick={recheck}>Re-check saved programmes</button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="notice"><strong>Please note.</strong> {DISCLAIMER}</div>

      <div className="stats stats4">
        <div className="stat ok"><div className="ic">★</div><div><div className="n">{saved.length}</div><div className="t">Saved programmes</div></div></div>
        <div className="stat cond"><div className="ic">⏰</div><div><div className="n">{upcoming.length}</div><div className="t">Upcoming deadlines</div></div></div>
        <div className="stat warn"><div className="ic">☐</div><div><div className="n">{nOpen}</div><div className="t">Open items</div></div></div>
        <div className="stat bad"><div className="ic">↻</div><div><div className="n">{withChange.length + nChanged}</div><div className="t">Changes to review</div></div></div>
      </div>

      {saved.length === 0 && (
        <div className="card"><h2>Nothing saved yet</h2>
          <p className="muted">Check your eligibility, open a programme and press <strong>Save</strong>. Saved programmes, their deadlines and what you still need appear here.</p>
          <a className="btn accent" href="/">Check eligibility</a></div>
      )}

      {(changes.length > 0 || withChange.length > 0 || nChanged > 0) && (
        <div className="card">
          <h2>Status changes</h2>
          {changes.length > 0 && <p className="muted small">Found in the re-check just now:</p>}
          <ul className="changes">
            {withChange.map(s => (
              <li key={s.programme_id}><strong>{s.name}</strong>
                <span className="status-change inline">Changed: {LABEL_TEXT[s.prev_overall] || s.prev_overall} → {LABEL_TEXT[s.last_overall] || s.last_overall}</span>
                <span className="muted small">{fmtTs(s.changed_at)}</span></li>))}
            {saved.filter(s => s.call_changed).map(s => (
              <li key={"c" + s.programme_id}><strong>{s.name}</strong> <NoticeBadges r={{ call_changed: s.call_changed }} /></li>))}
          </ul>
        </div>
      )}

      {saved.length > 0 && (
        <div className="dash-grid">
          <div className="dark-card">
            <h3>Upcoming deadlines</h3>
            <div style={{ fontSize: 20, fontWeight: 700 }}>Saved programmes</div>
            {upcoming.length === 0 && <div className="empty">No open deadlines among your saved programmes.</div>}
            {upcoming.map(s => (
              <div className="dl" key={s.programme_id}>
                <span>{s.name.length > 40 ? s.name.slice(0, 40) + "…" : s.name}</span>
                <span className="row tight"><span className="d">{s.deadline}</span><CalendarButtons r={s} calendar={calendar} /></span>
              </div>))}
          </div>
          <div className="card" style={{ marginBottom: 0 }}>
            <h2>What you still need</h2>
            {openItems.length === 0 && <p className="muted">No open items.</p>}
            {openItems.map(s => (
              <div key={s.programme_id} className="todo-group">
                <div className="todo-head">{s.name}</div>
                <MissingPanel programmeId={s.programme_id} items={row(s).missing} compact />
              </div>))}
          </div>
        </div>
      )}

      {saved.length > 0 && (
        <div className="card">
          <h2>Saved programmes</h2>
          <table>
            <thead><tr><th>Programme</th><th>Verdict</th><th>Deadline</th><th>Saved</th><th>Last checked</th><th></th></tr></thead>
            <tbody>{saved.map(s => (
              <tr key={s.programme_id}>
                <td><strong>{s.name}</strong><div className="muted small">{fam(s.family).flag} {fam(s.family).name}</div>
                  <div className="row tight" style={{ marginTop: 4 }}><NoticeBadges r={s} /></div></td>
                <td>{s.last_overall ? <Badge label={s.last_overall} /> : <span className="muted">not checked</span>}
                  {s.prev_overall && s.prev_overall !== s.last_overall && <div className="status-change">Changed: {LABEL_TEXT[s.prev_overall]} → {LABEL_TEXT[s.last_overall]}</div>}</td>
                <td>{s.deadline || <span className="muted">not found</span>}</td>
                <td className="muted small">{fmtTs(s.saved_at)}</td>
                <td className="muted small">{fmtTs(s.last_checked)}</td>
                <td className="row">{s.url && <a className="btn secondary small" href={s.url} target="_blank" rel="noreferrer">Official call</a>}
                  <button className="secondary small" onClick={() => remove(s.programme_id)}>Remove</button></td>
              </tr>))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card">
        <h2>Past checks</h2>
        {history.length === 0 ? <p className="muted">No checks yet from this browser.</p> : (
          <table>
            <thead><tr><th>When</th><th>Programme</th><th>Verdict</th></tr></thead>
            <tbody>{history.map((h, i) => (
              <tr key={i}><td className="muted small">{fmtTs(h.ts)}</td><td>{h.name || h.programme_id}</td><td><Badge label={h.overall} /></td></tr>))}
            </tbody>
          </table>
        )}
      </div>
      <footer>Dashboard for this browser only (no account). Today is {today()}.</footer>
    </div>
  );
}
