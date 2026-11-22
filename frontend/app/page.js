"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const LABEL_TEXT = { eligible: "Eligible", not_eligible: "Not eligible", insufficient_info: "Insufficient information", manual_check: "Manual check" };
const LEVELS = ["intermediate", "bachelor", "master", "phd"];
const SCALES = ["cgpa_4", "cgpa_5", "percentage", "uk_class", "german", "other"];

const FAMILIES = {
  chevening: { name: "Chevening", flag: "UK", color: "#1d3557" },
  commonwealth: { name: "Commonwealth", flag: "UK", color: "#6a4c93" },
  csc_china: { name: "CSC China", flag: "CN", color: "#c1121f" },
  daad: { name: "DAAD Germany", flag: "DE", color: "#2b2d42" },
  erasmus_mundus: { name: "Erasmus Mundus", flag: "EU", color: "#0b3d91" },
  fulbright: { name: "Fulbright", flag: "US", color: "#3d5a80" },
  gks_korea: { name: "GKS Korea", flag: "KR", color: "#2a9d8f" },
  hec: { name: "HEC Pakistan", flag: "PK", color: "#1b6b3a" },
  mext: { name: "MEXT Japan", flag: "JP", color: "#9d0208" },
  open_doors: { name: "Open Doors Russia", flag: "RU", color: "#264653" },
  stipendium_hungaricum: { name: "Stipendium Hungaricum", flag: "HU", color: "#386641" },
  turkiye_burslari: { name: "Türkiye Burslari", flag: "TR", color: "#bb3e03" },
};
const FILTERS = [["all", "All"], ["eligible", "Eligible"], ["insufficient_info", "Need information"], ["not_eligible", "Not eligible"]];

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
        <td><strong>{r.name}</strong><div className="muted">{(FAMILIES[r.family] || {}).flag} {(FAMILIES[r.family] || {}).name || r.family} · snapshot {r.snapshot_date}</div></td>
        <td><Badge label={r.overall} /></td>
        <td>{r.deadline || <span className="muted">not found</span>}</td>
        <td className="row">
          <button className="secondary small" onClick={() => setOpen(!open)}>{open ? "Hide" : "Why?"}</button>
          {r.deadline && calendar.connected && <button className="accent small" onClick={addToCalendar}>Add deadline</button>}
          {r.deadline && <a className="btn secondary small" href={`${API}/api/programmes/${r.programme_id}/deadline.ics`}>.ics</a>}
          {msg && <span className="muted">{msg}</span>}
        </td>
      </tr>
      {open && (
        <tr><td colSpan={4}>
          <table className="nested">
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
  const [families, setFamilies] = useState([]);
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  const [prog, setProg] = useState(null);

  useEffect(() => { fetch(`${API}/api/programmes`).then(r => r.json()).then(ps => { const c = {}; ps.forEach(p => { c[p.family] = (c[p.family] || 0) + 1; }); setFamilies(Object.entries(c)); }).catch(() => {}); }, []);
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
      setBusy(`Checked ${i} of ${ids.length} programmes... (the first check of a new CV can take a minute)`); setProg({ i, n: ids.length });
      const res = await fetch(`${API}/api/check`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile, programme_ids: [ids[i]] }) });
      const data = await res.json();
      if (!res.ok) { setBusy(""); return setError(data.detail || "Check failed"); }
      rows = sorted([...rows, ...data]); setResults(rows);
    }
    setBusy(""); setProg(null);
  }

  const counts = results ? results.reduce((a, r) => ({ ...a, [r.overall]: (a[r.overall] || 0) + 1 }), {}) : {};
  const today = new Date().toISOString().slice(0, 10);
  const deadlines = results ? results.filter(r => r.deadline).sort((a, b) => a.deadline.localeCompare(b.deadline)).slice(0, 5) : [];
  const top = results ? results.filter(r => r.overall === "eligible").slice(0, 3) : [];
  const shown = results ? results.filter(r => (filter === "all" || r.overall === filter) && (!q || r.name.toLowerCase().includes(q.toLowerCase()))) : [];

  return (
    <div>
      <div className="topbar">
        <div className="search"><input placeholder="Search programmes in your results..." value={q} onChange={e => setQ(e.target.value)} /></div>
        <span className="pill"><span className="dot" style={{ background: calendar.connected ? "#22c55e" : "#bbb" }} />{calendar.connected ? "Google Calendar connected" : "Calendar not connected"}</span>
      </div>

      <div className="hero-grid">
        <div className="hero">
          <h1>Which scholarships can you apply to?</h1>
          <p>Upload your CV. ScholarFit reads it, lets you correct the profile, then checks every programme&apos;s criteria with its own grade-conversion rule.</p>
          <div className="dropzone">
            <input type="file" accept=".pdf,.docx,.txt" onChange={e => setFile(e.target.files[0])} />
            <button disabled={!file || !!busy} onClick={extract}>Read CV</button>
          </div>
          {calendar.configured && !calendar.connected && <p style={{ margin: "12px 0 0" }}><a className="btn secondary small" href={calendar.auth_url}>Connect Google Calendar</a></p>}
          {busy && <p style={{ margin: "12px 0 0", fontSize: 13 }}>{busy}</p>}
          {prog && <div className="progress"><div style={{ width: `${(prog.i / prog.n) * 100}%` }} /></div>}
          {error && <p className="error">{error}</p>}
          
        </div>
        <div className="dark-card">
          <h3>Upcoming deadlines</h3>
          <div style={{ fontSize: 20, fontWeight: 700 }}>From your results</div>
          {deadlines.length === 0 && <div className="empty">Check your eligibility to see programme deadlines here. You can add each one to Google Calendar.</div>}
          {deadlines.map(r => (
            <div className="dl" key={r.programme_id}>
              <span>{r.name.length > 46 ? r.name.slice(0, 46) + "…" : r.name}</span>
              <span className={`d ${r.deadline < today ? "past" : ""}`}>{r.deadline}{r.deadline < today ? " (passed)" : ""}</span>
            </div>))}
        </div>
      </div>

      {profile && (
        <div className="card">
          <h2>Your profile <span className="muted" style={{ fontWeight: 400 }}>(check and correct before checking eligibility)</span></h2>
          <ProfileEditor profile={profile} setProfile={setProfile} />
          <div style={{ marginTop: 18 }}><button className="accent" disabled={!!busy} onClick={check}>Check eligibility</button></div>
        </div>
      )}

      {results && (
        <>
          <div className="stats">
            <div className="stat ok"><div className="ic">✔</div><div><div className="n">{counts.eligible || 0}</div><div className="t">Eligible</div></div></div>
            <div className="stat warn"><div className="ic">❓</div><div><div className="n">{counts.insufficient_info || 0}</div><div className="t">Need more information</div></div></div>
            <div className="stat bad"><div className="ic">✖</div><div><div className="n">{counts.not_eligible || 0}</div><div className="t">Not eligible</div></div></div>
          </div>

          {top.length > 0 && (
            <>
              <div className="section-head"><h2>Your best matches</h2></div>
              <div className="cards3">
                {top.map(r => (
                  <div className="pcard" key={r.programme_id}>
                    <div className="name">{r.name}</div>
                    <div className="row"><Badge label={r.overall} />{r.deadline && <span className="muted">Deadline {r.deadline}</span>}</div>
                    <div className="meta"><span className="fam-ico">{(FAMILIES[r.family] || {}).flag || "🎓"}</span>{(FAMILIES[r.family] || {}).name || r.family}</div>
                  </div>))}
              </div>
            </>
          )}

          <div className="card">
            <h2>All programmes</h2>
            <div className="chips">
              {FILTERS.map(([k, t]) => <button key={k} className={`chip ${filter === k ? "on" : ""}`} onClick={() => setFilter(k)}>{t}{k !== "all" ? ` (${counts[k] || 0})` : ` (${results.length})`}</button>)}
            </div>
            <table>
              <thead><tr><th>Programme</th><th>Overall</th><th>Deadline</th><th></th></tr></thead>
              <tbody>{shown.map(r => <ResultRow key={r.programme_id} r={r} calendar={calendar} />)}</tbody>
            </table>
            {shown.length === 0 && <p className="muted">No programmes match.</p>}
          </div>
        </>
      )}

      <div className="section-head"><h2>Scholarship providers we check</h2><span className="muted">{families.reduce((a, [, n]) => a + n, 0)} programmes</span></div>
      <div className="tiles">
        {families.map(([f, n]) => {
          const fam = FAMILIES[f] || { name: f, flag: "🎓", color: "#333" };
          return <div className="tile" key={f} style={{ backgroundColor: fam.color, backgroundImage: `linear-gradient(180deg, rgba(0,0,0,.05) 25%, rgba(0,0,0,.78)), url(/destinations/${f}.jpg)` }}>
            <span className="flag">{fam.flag}</span><div><div className="tn">{fam.name}</div><div className="tc">{n} programme{n > 1 ? "s" : ""}</div></div></div>;
        })}
      </div>
      <footer>ScholarFit advises only. The official programme page is always authoritative.</footer>
    </div>
  );
}
