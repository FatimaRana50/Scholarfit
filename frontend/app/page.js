"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const LABEL_TEXT = { eligible: "Eligible", not_eligible: "Not eligible", insufficient_info: "Insufficient information", manual_check: "Manual check" };
const LEVELS = ["intermediate", "bachelor", "master", "phd"];
const SCALES = ["cgpa_4", "cgpa_5", "percentage", "uk_class", "german", "other"];

function Badge({ label }) {
  return <span className={`badge ${label}`}>{LABEL_TEXT[label] || label}</span>;
}

function num(v) { return v === "" || v === null || v === undefined ? null : Number(v); }

function ProfileEditor({ profile, setProfile }) {
  const set = (k, v) => setProfile({ ...profile, [k]: v });
  const setDeg = (i, k, v) => { const d = [...profile.degrees]; d[i] = { ...d[i], [k]: v }; set("degrees", d); };
  const setTest = (i, k, v) => { const t = [...profile.english_tests]; t[i] = { ...t[i], [k]: v }; set("english_tests", t); };
  return (
    <div>
      <div className="grid">
        <div><label>Date of birth</label><input type="date" value={profile.date_of_birth || ""} onChange={e => set("date_of_birth", e.target.value || null)} /></div>
        <div><label>Nationality</label><input value={profile.nationality || ""} onChange={e => set("nationality", e.target.value || null)} /></div>
        <div><label>Work experience (months)</label><input type="number" value={profile.work_experience_months ?? ""} onChange={e => set("work_experience_months", num(e.target.value))} /></div>
        <div><label>Bachelor taught in English</label>
          <select value={profile.english_medium_instruction === true ? "yes" : profile.english_medium_instruction === false ? "no" : ""}
            onChange={e => set("english_medium_instruction", e.target.value === "" ? null : e.target.value === "yes")}>
            <option value="">Not stated</option><option value="yes">Yes</option><option value="no">No</option>
          </select></div>
      </div>
      <h2 style={{ marginTop: 18 }}>Degrees</h2>
      {profile.degrees.map((d, i) => (
        <div className="deg" key={i}>
          <div className="grid">
            <div><label>Level</label><select value={d.level} onChange={e => setDeg(i, "level", e.target.value)}>{LEVELS.map(l => <option key={l}>{l}</option>)}</select></div>
            <div><label>Field</label><input value={d.field || ""} onChange={e => setDeg(i, "field", e.target.value || null)} /></div>
            <div><label>Duration (years)</label><input type="number" value={d.duration_years ?? ""} onChange={e => setDeg(i, "duration_years", num(e.target.value))} /></div>
            <div><label>Completed</label><select value={d.completed === true ? "yes" : d.completed === false ? "no" : ""} onChange={e => setDeg(i, "completed", e.target.value === "" ? null : e.target.value === "yes")}>
              <option value="">Unknown</option><option value="yes">Yes</option><option value="no">In progress</option></select></div>
            <div><label>Grade</label><input type="number" step="0.01" value={d.grade_value ?? ""} onChange={e => setDeg(i, "grade_value", num(e.target.value))} /></div>
            <div><label>Scale</label><select value={d.grade_scale || ""} onChange={e => setDeg(i, "grade_scale", e.target.value || null)}><option value="">Unknown</option>{SCALES.map(s => <option key={s}>{s}</option>)}</select></div>
            <div><label>Scale maximum</label><input type="number" value={d.grade_scale_max ?? ""} onChange={e => setDeg(i, "grade_scale_max", num(e.target.value))} /></div>
            <div><label>Minimum passing grade</label><input type="number" step="0.01" value={d.grade_scale_min_pass ?? ""} onChange={e => setDeg(i, "grade_scale_min_pass", num(e.target.value))} /></div>
          </div>
        </div>
      ))}
      <button className="secondary" onClick={() => set("degrees", [...profile.degrees, { level: "bachelor" }])}>Add degree</button>
      <h2 style={{ marginTop: 18 }}>English tests</h2>
      {profile.english_tests.map((t, i) => (
        <div className="grid3" key={i} style={{ marginBottom: 8 }}>
          <div><label>Test</label><select value={t.test} onChange={e => setTest(i, "test", e.target.value)}>{["IELTS", "TOEFL_iBT", "PTE", "Duolingo"].map(x => <option key={x}>{x}</option>)}</select></div>
          <div><label>Overall</label><input type="number" step="0.5" value={t.overall ?? ""} onChange={e => setTest(i, "overall", num(e.target.value))} /></div>
          <div><label>Lowest sub-score</label><input type="number" step="0.5" value={t.min_band ?? ""} onChange={e => setTest(i, "min_band", num(e.target.value))} /></div>
        </div>
      ))}
      <button className="secondary" onClick={() => set("english_tests", [...profile.english_tests, { test: "IELTS", overall: 6.5 }])}>Add test</button>
    </div>
  );
}

function ResultRow({ r, calendar }) {
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");
  async function addToCalendar() {
    setMsg("Adding...");
    const res = await fetch(`${API}/api/calendar/add`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ programme_id: r.programme_id }) });
    const data = await res.json();
    setMsg(res.ok ? "Added to Google Calendar" : (data.detail || "Failed"));
  }
  return (
    <>
      <tr>
        <td><strong>{r.name}</strong><div className="muted">{r.family} · snapshot {r.snapshot_date}</div></td>
        <td><Badge label={r.overall} /></td>
        <td>{r.deadline || <span className="muted">not found</span>}</td>
        <td className="row">
          <button className="secondary" onClick={() => setOpen(!open)}>{open ? "Hide" : "Why?"}</button>
          {r.deadline && calendar.connected && <button onClick={addToCalendar}>Add deadline</button>}
          {r.deadline && <a className="btn secondary" href={`${API}/api/programmes/${r.programme_id}/deadline.ics`}>.ics</a>}
          {msg && <span className="muted">{msg}</span>}
        </td>
      </tr>
      {open && (
        <tr><td colSpan={4}>
          <table>
            <thead><tr><th>Requirement</th><th>Verdict</th><th>Reason</th></tr></thead>
            <tbody>{r.criteria.map((c, i) => (
              <tr key={i}>
                <td>{c.type.replaceAll("_", " ")}</td>
                <td><Badge label={c.label} /></td>
                <td>{c.reason}{c.rule_used && <div className="muted">Rule: {c.rule_used}</div>}
                  {c.citation && <div className="quote">“{c.citation}”</div>}</td>
              </tr>))}
            </tbody>
          </table>
          {r.url && <p className="muted">Source: <a href={r.url} target="_blank">official call</a></p>}
        </td></tr>
      )}
    </>
  );
}

export default function Home() {
  const [file, setFile] = useState(null);
  const [profile, setProfile] = useState(null);
  const [results, setResults] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [calendar, setCalendar] = useState({ configured: false, connected: false });

  useEffect(() => { fetch(`${API}/api/calendar/status`).then(r => r.json()).then(setCalendar).catch(() => {}); }, []);

  async function extract() {
    setBusy("Reading your CV..."); setError("");
    const fd = new FormData(); fd.append("file", file);
    const res = await fetch(`${API}/api/profile/extract`, { method: "POST", body: fd });
    const data = await res.json();
    setBusy("");
    if (!res.ok) return setError(data.detail || "Extraction failed");
    setProfile({ degrees: [], english_tests: [], interests: [], ...data }); setResults(null);
  }

  async function check() {
    setBusy("Checking every programme..."); setError(""); setResults([]);
    let ids;
    try { ids = (await (await fetch(`${API}/api/programmes`)).json()).map(p => p.programme_id); }
    catch (e) { setBusy(""); return setError("Could not reach the server"); }
    const order = { eligible: 0, insufficient_info: 1, not_eligible: 2 };
    const sorted = rows => [...rows].sort((a, b) => (order[a.overall] ?? 3) - (order[b.overall] ?? 3) || a.name.localeCompare(b.name));
    let rows = [];
    // one programme per request: results appear as they arrive and the page shows progress
    for (let i = 0; i < ids.length; i++) {
      setBusy(`Checked ${i} of ${ids.length} programmes... (the first check of a new CV takes a few minutes)`);
      const res = await fetch(`${API}/api/check`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile, programme_ids: [ids[i]] }) });
      const data = await res.json();
      if (!res.ok) { setBusy(""); return setError(data.detail || "Check failed"); }
      rows = sorted([...rows, ...data]); setResults(rows);
    }
    setBusy("");
  }

  const counts = results ? results.reduce((a, r) => ({ ...a, [r.overall]: (a[r.overall] || 0) + 1 }), {}) : {};

  return (
    <div>
      <div className="card">
        <h1>Which scholarships can you apply to?</h1>
        <p className="muted">Upload your CV. ScholarFit reads it, lets you correct the profile, then checks every programme's criteria with each programme's own grade-conversion rule.</p>
        <div className="row">
          <input type="file" accept=".pdf,.docx,.txt" onChange={e => setFile(e.target.files[0])} style={{ maxWidth: 340 }} />
          <button disabled={!file || !!busy} onClick={extract}>Read CV</button>
          {calendar.configured && !calendar.connected && <a className="btn secondary" href={calendar.auth_url}>Connect Google Calendar</a>}
          {calendar.connected && <span className="muted">Google Calendar connected</span>}
        </div>
        {busy && <p className="muted">{busy}</p>}
        {error && <p className="error">{error}</p>}
      </div>

      {profile && (
        <div className="card">
          <h2>Your profile (check and correct before checking eligibility)</h2>
          <ProfileEditor profile={profile} setProfile={setProfile} />
          <div style={{ marginTop: 16 }}><button disabled={!!busy} onClick={check}>Check eligibility</button></div>
        </div>
      )}

      {results && (
        <div className="card">
          <h2>Results</h2>
          <p className="muted">{counts.eligible || 0} eligible · {counts.insufficient_info || 0} need more information · {counts.not_eligible || 0} not eligible</p>
          <table>
            <thead><tr><th>Programme</th><th>Overall</th><th>Deadline</th><th></th></tr></thead>
            <tbody>{results.map(r => <ResultRow key={r.programme_id} r={r} calendar={calendar} />)}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}
