"use client";
import { useEffect, useState } from "react";
import { API, Badge, CalendarButtons, DISCLAIMER, LABEL_TEXT, MissingPanel, NoticeBadges, fam, getProfileId, newProfileId, today } from "./lib";

// Results are kept in the browser while they arrive, so leaving the page never loses them.
function storeResults(data) {
  try { localStorage.setItem("scholarfit_results", JSON.stringify(data)); } catch { /* storage full: keep in memory only */ }
}
function loadResults() {
  try { return JSON.parse(localStorage.getItem("scholarfit_results") || "null"); } catch { return null; }
}

const LEVELS = ["intermediate", "bachelor", "master", "phd"];
const SCALES = ["cgpa_4", "cgpa_5", "percentage", "uk_class", "german", "other"];
const VERDICT_ORDER = { eligible: 0, conditional: 1, insufficient_info: 2, not_eligible: 3 };
const GROUPS = [
  ["eligible", "Eligible"],
  ["conditional", "Conditionally eligible"],
  ["insufficient_info", "Not enough information"],
  ["not_eligible", "Not eligible"],
  ["outdated", "Deadline passed"],
];
const MISSING_HINT = "Not found in your CV, add it if you have it";

// Same order as backend ranking.sort_key: not outdated first, then verdict, then ranking score.
const sortKey = (a, b) => (a.outdated - b.outdated) || ((VERDICT_ORDER[a.overall] ?? 4) - (VERDICT_ORDER[b.overall] ?? 4))
  || ((b.ranking?.score || 0) - (a.ranking?.score || 0)) || a.name.localeCompare(b.name);
const groupOf = r => r.outdated ? "outdated" : r.overall;

function num(v) { return v === "" || v === null || v === undefined ? null : Number(v); }
const empty = v => v === null || v === undefined || v === "";

function Field({ label, missing, children, wide }) {
  return (
    <div className={`${missing ? "field-missing" : ""} ${wide ? "wide" : ""}`}>
      <label>{label}</label>
      {children}
      {missing && <div className="hint">{MISSING_HINT}</div>}
    </div>
  );
}

function ProfileEditor({ profile, setProfile }) {
  const set = (k, v) => setProfile({ ...profile, [k]: v });
  const setDeg = (i, k, v) => { const d = [...profile.degrees]; d[i] = { ...d[i], [k]: v }; set("degrees", d); };
  const setTest = (i, k, v) => { const t = [...profile.english_tests]; t[i] = { ...t[i], [k]: v }; set("english_tests", t); };
  const tertiary = d => ["bachelor", "master", "phd"].includes(d.level);
  return (
    <div>
      <div className="grid">
        <Field label="Degree I am applying for">
          <select value={profile.target_level || ""} onChange={e => set("target_level", e.target.value || null)}>
            <option value="">Not chosen (next degree up)</option><option value="master">Master&apos;s</option><option value="phd">PhD</option>
          </select>
        </Field>
        <Field label="Date of birth" missing={empty(profile.date_of_birth)}><input type="date" value={profile.date_of_birth || ""} onChange={e => set("date_of_birth", e.target.value || null)} /></Field>
        <Field label="Nationality" missing={empty(profile.nationality)}><input value={profile.nationality || ""} onChange={e => set("nationality", e.target.value || null)} /></Field>
        <Field label="Work experience (months)" missing={empty(profile.work_experience_months)}><input type="number" value={profile.work_experience_months ?? ""} onChange={e => set("work_experience_months", num(e.target.value))} /></Field>
        <Field label="Bachelor taught in English">
          <select value={profile.english_medium_instruction === true ? "yes" : profile.english_medium_instruction === false ? "no" : ""}
            onChange={e => set("english_medium_instruction", e.target.value === "" ? null : e.target.value === "yes")}>
            <option value="">Not stated</option><option value="yes">Yes</option><option value="no">No</option>
          </select>
        </Field>
        <Field label="Interests (comma separated, used to rank programmes)" wide>
          <input value={(profile.interests || []).join(", ")} onChange={e => set("interests", e.target.value.split(",").map(s => s.trim()).filter(Boolean))} />
        </Field>
      </div>
      <h2 style={{ marginTop: 18 }}>Degrees</h2>
      {profile.degrees.map((d, i) => (
        <div className="deg" key={i}>
          <div className="grid">
            <Field label="Level"><select value={d.level} onChange={e => setDeg(i, "level", e.target.value)}>{LEVELS.map(l => <option key={l}>{l}</option>)}</select></Field>
            <Field label="Field"><input value={d.field || ""} onChange={e => setDeg(i, "field", e.target.value || null)} /></Field>
            <Field label="Duration (years)"><input type="number" value={d.duration_years ?? ""} onChange={e => setDeg(i, "duration_years", num(e.target.value))} /></Field>
            <Field label="Completed"><select value={d.completed === true ? "yes" : d.completed === false ? "no" : ""} onChange={e => setDeg(i, "completed", e.target.value === "" ? null : e.target.value === "yes")}>
              <option value="">Unknown</option><option value="yes">Yes</option><option value="no">In progress</option></select></Field>
            <Field label="Grade" missing={tertiary(d) && empty(d.grade_value)}><input type="number" step="0.01" value={d.grade_value ?? ""} onChange={e => setDeg(i, "grade_value", num(e.target.value))} /></Field>
            <Field label="Scale"><select value={d.grade_scale || ""} onChange={e => setDeg(i, "grade_scale", e.target.value || null)}><option value="">Unknown</option>{SCALES.map(s => <option key={s}>{s}</option>)}</select></Field>
            <Field label="Scale maximum"><input type="number" value={d.grade_scale_max ?? ""} onChange={e => setDeg(i, "grade_scale_max", num(e.target.value))} /></Field>
            <Field label="Minimum passing grade" missing={tertiary(d) && empty(d.grade_scale_min_pass)}><input type="number" step="0.01" value={d.grade_scale_min_pass ?? ""} onChange={e => setDeg(i, "grade_scale_min_pass", num(e.target.value))} /></Field>
          </div>
          <button className="secondary small" style={{ marginTop: 10 }} onClick={() => set("degrees", profile.degrees.filter((_, j) => j !== i))}>Remove degree</button>
        </div>
      ))}
      <button className="secondary" onClick={() => set("degrees", [...profile.degrees, { level: "bachelor" }])}>Add degree</button>
      <h2 style={{ marginTop: 18 }}>English tests</h2>
      {profile.english_tests.length === 0 && <div className="field-missing box"><div className="hint">No English test found. {MISSING_HINT}.</div></div>}
      {profile.english_tests.map((t, i) => (
        <div className="grid" key={i} style={{ marginBottom: 8 }}>
          <Field label="Test"><select value={t.test} onChange={e => setTest(i, "test", e.target.value)}>{["IELTS", "TOEFL_iBT", "PTE", "Duolingo"].map(x => <option key={x}>{x}</option>)}</select></Field>
          <Field label="Overall"><input type="number" step="0.5" value={t.overall ?? ""} onChange={e => setTest(i, "overall", num(e.target.value))} /></Field>
          <Field label="Lowest sub-score"><input type="number" step="0.5" value={t.min_band ?? ""} onChange={e => setTest(i, "min_band", num(e.target.value))} /></Field>
          <div style={{ alignSelf: "end" }}><button className="secondary small" onClick={() => set("english_tests", profile.english_tests.filter((_, j) => j !== i))}>Remove</button></div>
        </div>
      ))}
      <button className="secondary" onClick={() => set("english_tests", [...profile.english_tests, { test: "IELTS", overall: 6.5 }])}>Add test</button>
    </div>
  );
}

function rankHints(k) {
  if (!k) return [];
  const out = [];
  if (k.relevance >= 0.15) out.push("Close to your field");
  if (k.funding_kind === "full") out.push("Full scholarship");
  else if (k.funding_kind === "partial") out.push("Partial funding");
  else if (k.funding_kind === "tuition") out.push("Tuition only");
  if (k.urgency === 1) out.push("Deadline within 30 days");
  else if (k.urgency === 0.5) out.push("Deadline within 90 days");
  return out;
}

function Breakdown({ r }) {
  return (
    <table className="nested breakdown">
      <thead><tr><th style={{ width: "26%" }}>Requirement</th><th style={{ width: "22%" }}>Your profile</th><th style={{ width: "22%" }}>Result</th><th>Evidence</th></tr></thead>
      <tbody>{r.criteria.map((c, i) => (
        <tr key={i}>
          <td>{c.requirement}<div className="muted small">{c.type.replaceAll("_", " ")}{c.alternative_group ? " · one of several alternatives" : ""}</div></td>
          <td>{c.your_profile}</td>
          <td><span className={`badge ${c.label}`}>{c.result}</span><div className="reason">{c.reason}</div>
            {c.rule_used && <div className="muted small">Rule: {c.rule_used}</div>}</td>
          <td>{c.citation
            ? <div className="quote">“{c.citation}”</div>
            : <div className="muted small">No quote stored for this requirement. Check the official call before relying on this result.</div>}
            {r.url && <div className="muted small" style={{ marginTop: 6 }}><a href={r.url} target="_blank" rel="noreferrer">Official call</a>{r.snapshot_date && `, snapshot ${r.snapshot_date}`}</div>}
          </td>
        </tr>))}
      </tbody>
    </table>
  );
}

function ResultCard({ r, rank, calendar, onSave }) {
  const [open, setOpen] = useState(false);
  const f = fam(r.family);
  return (
    <div className={`rcard ${r.outdated ? "is-outdated" : ""}`}>
      <div className="rhead">
        <div className="rank">{rank ? `#${rank}` : ""}</div>
        <div className="rmain">
          <div className="name">{r.name}</div>
          <div className="muted small">{f.flag} {f.name} · snapshot {r.snapshot_date || "unknown"} · deadline {r.deadline || "not found"}</div>
          <div className="row tight" style={{ marginTop: 6 }}>
            <Badge label={r.overall} /><NoticeBadges r={r} />
            {rankHints(r.ranking).map(h => <span key={h} className="hintchip">{h}</span>)}
          </div>
          {r.status_change && <div className="status-change">Changed: {LABEL_TEXT[r.status_change.from] || r.status_change.from} → {LABEL_TEXT[r.status_change.to] || r.status_change.to}</div>}
        </div>
        <div className="row ractions">
          <button className="secondary small" onClick={() => setOpen(!open)}>{open ? "Hide details" : "Why? Show breakdown"}</button>
          <button className={`small ${r.saved ? "" : "accent"}`} onClick={() => onSave(r)}>{r.saved ? "Saved ✓" : "Save"}</button>
          <CalendarButtons r={r} calendar={calendar} />
        </div>
      </div>
      {open && (
        <div className="rbody">
          {r.criteria.length === 0
            ? <p className="muted">No approved criteria for this programme yet (they are waiting for curator review), so it cannot be checked. Read the <a href={r.url} target="_blank" rel="noreferrer">official call</a>.</p>
            : <>
              <h3>Requirement breakdown</h3>
              <Breakdown r={r} />
              <h3>What you still need</h3>
              <MissingPanel programmeId={r.programme_id} items={r.missing} />
            </>}
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [file, setFile] = useState(null);
  const [profile, setProfile] = useState(null);
  const [reviewed, setReviewed] = useState(false);
  const [results, setResults] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [calendar, setCalendar] = useState({ configured: false, connected: false });
  const [families, setFamilies] = useState([]);
  const [showNotEligible, setShowNotEligible] = useState(false);
  const [q, setQ] = useState("");
  const [prog, setProg] = useState(null);

  useEffect(() => { fetch(`${API}/api/programmes`).then(r => r.json()).then(ps => { const c = {}; ps.forEach(p => { c[p.family] = (c[p.family] || 0) + 1; }); setFamilies(Object.entries(c)); }).catch(() => {}); }, []);
  useEffect(() => { fetch(`${API}/api/calendar/status`).then(r => r.json()).then(setCalendar).catch(() => {}); }, []);
  const [meta, setMeta] = useState(null);   // {checked_at, total, complete, stale} of the stored results

  // Restore the last profile and results, so leaving the page (e.g. to the dashboard) loses nothing.
  useEffect(() => {
    try {
      const p = JSON.parse(localStorage.getItem("scholarfit_profile") || "null");
      if (p) setProfile(p);
      const last = loadResults();
      if (last?.rows?.length && (!p || last.profile_id === p.profile_id)) {
        const { rows, ...m } = last;
        setResults(rows); setMeta(m); setReviewed(!m.stale);
        // saved flags may have changed on the dashboard
        fetch(`${API}/api/saved?profile_id=${encodeURIComponent(getProfileId())}`).then(r => r.json()).then(s => {
          const ids = new Set(s.map(x => x.programme_id));
          setResults(rs => rs && rs.map(r => ({ ...r, saved: ids.has(r.programme_id) })));
        }).catch(() => {});
      }
    } catch {}
  }, []);

  function updateMeta(change) {
    setMeta(m => {
      const next = { ...(m || {}), ...change };
      const last = loadResults();
      if (last) storeResults({ ...last, ...change });
      return next;
    });
  }

  function editProfile(p) {
    setProfile(p); setReviewed(false);
    localStorage.setItem("scholarfit_profile", JSON.stringify(p));
    if (results?.length) updateMeta({ stale: true });
  }

  async function extract() {
    setBusy("Reading your CV..."); setError("");
    try {
      const fd = new FormData(); fd.append("file", file);
      const res = await fetch(`${API}/api/profile/extract`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) return setError(data.detail || "Extraction failed");
      // a new CV is a new profile: its own saved programmes, dashboard and past checks
      const p = { degrees: [], english_tests: [], interests: [], ...data, profile_id: newProfileId(), cv_name: file.name };
      setProfile(p); localStorage.setItem("scholarfit_profile", JSON.stringify(p));
      setReviewed(false); setResults(null); setMeta(null); localStorage.removeItem("scholarfit_results");
    } catch { setError("Could not reach the server"); }
    finally { setBusy(""); }
  }

  function confirmReview() {
    const p = { ...profile, profile_id: profile.profile_id || getProfileId() };
    setProfile(p); setReviewed(true);
    localStorage.setItem("scholarfit_profile", JSON.stringify(p));
  }

  async function check() {
    setBusy("Checking every programme..."); setError(""); setResults([]);
    let ids;
    try { ids = (await (await fetch(`${API}/api/programmes`)).json()).map(p => p.programme_id); }
    catch (e) { setBusy(""); return setError("Could not reach the server"); }
    let rows = [];
    const m = { profile_id: profile.profile_id, checked_at: new Date().toLocaleString(), total: ids.length, complete: false, stale: false };
    setMeta(m);
    // one programme per request: results appear as they arrive and the page shows progress
    for (let i = 0; i < ids.length; i++) {
      setBusy(`Checked ${i} of ${ids.length} programmes... (the first check of a new CV can take a minute)`); setProg({ i, n: ids.length });
      try {
        const res = await fetch(`${API}/api/check`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile, programme_ids: [ids[i]] }) });
        const data = await res.json();
        if (!res.ok) { setBusy(""); setProg(null); return setError(data.detail || "Check failed"); }
        rows = [...rows, ...data].sort(sortKey); setResults(rows);
        storeResults({ ...m, rows });   // stored as they arrive: leaving the page keeps what was checked so far
      } catch { setBusy(""); setProg(null); return setError("Could not reach the server"); }
    }
    const done = { ...m, complete: true };
    setMeta(done); storeResults({ ...done, rows });
    setBusy(""); setProg(null);
  }

  async function toggleSave(r) {
    const pid = getProfileId();
    const res = r.saved
      ? await fetch(`${API}/api/saved/${r.programme_id}?profile_id=${encodeURIComponent(pid)}`, { method: "DELETE" })
      : await fetch(`${API}/api/saved`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ profile_id: pid, programme_id: r.programme_id, overall: r.overall, row: r }) });
    if (!res.ok) return setError("Could not save the programme");
    setResults(rs => {
      const next = rs.map(x => x.programme_id === r.programme_id ? { ...x, saved: !r.saved } : x);
      const last = loadResults();
      if (last) storeResults({ ...last, rows: next });
      return next;
    });
  }

  const current = results ? results.filter(r => !r.outdated) : [];
  const counts = current.reduce((a, r) => ({ ...a, [r.overall]: (a[r.overall] || 0) + 1 }), {});
  const nOutdated = results ? results.length - current.length : 0;
  const deadlines = results ? results.filter(r => r.deadline && !r.outdated).sort((a, b) => a.deadline.localeCompare(b.deadline)).slice(0, 5) : [];
  const top = current.filter(r => r.overall === "eligible" || r.overall === "conditional").slice(0, 3);
  const match = r => !q || r.name.toLowerCase().includes(q.toLowerCase());
  let rank = 0;
  const ranks = {};
  (results || []).forEach(r => { if (!r.outdated && r.overall !== "not_eligible") ranks[r.programme_id] = ++rank; });

  return (
    <div>
      <div className="topbar">
        <div className="search"><input placeholder="Search programmes in your results..." value={q} onChange={e => setQ(e.target.value)} /></div>
        <span className="pill"><span className="dot" style={{ background: calendar.connected ? "#22c55e" : "#bbb" }} />{calendar.connected ? "Google Calendar connected" : "Calendar not connected"}</span>
      </div>

      <div className="hero-grid">
        <div className="hero">
          <h1>Which scholarships can you apply to?</h1>
          <p>Upload your CV. ScholarFit reads it, you check and correct the profile, then every programme&apos;s criteria are checked with its own grade-conversion rule.</p>
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
          {deadlines.length === 0 && <div className="empty">Check your eligibility to see open programme deadlines here. You can add each one to Google Calendar.</div>}
          {deadlines.map(r => (
            <div className="dl" key={r.programme_id}>
              <span>{r.name.length > 46 ? r.name.slice(0, 46) + "…" : r.name}</span>
              <span className="d">{r.deadline}</span>
            </div>))}
        </div>
      </div>

      {profile && (
        <div className="card">
          <h2>Step 1: Check your profile</h2>
          <p className="muted" style={{ marginTop: -6 }}>This is what we read from your CV. Correct anything that is wrong and fill in the fields marked in amber before checking eligibility. Your CV file itself is not stored.</p>
          <ProfileEditor profile={profile} setProfile={editProfile} />
          <div className="gate">
            {!reviewed
              ? <button onClick={confirmReview}>I have checked my profile</button>
              : <span className="ok-text">✓ Profile checked</span>}
            <button className="accent" disabled={!reviewed || !!busy} onClick={check}
              title={reviewed ? "" : "Confirm your profile first"}>Step 2: Check eligibility</button>
            {!reviewed && <span className="muted small">The check is enabled after you confirm your profile.</span>}
          </div>
        </div>
      )}

      {results && results.length > 0 && (
        <>
          <div className="notice"><strong>Please note.</strong> {DISCLAIMER}</div>
          {!busy && meta?.checked_at && <p className="muted small" style={{ marginTop: -10 }}>Results of your check on {meta.checked_at}{profile?.cv_name ? ` for ${profile.cv_name}` : ""}.</p>}
          {!busy && meta && !meta.complete && <div className="notice warn-notice">This check stopped after {results.length} of {meta.total} programmes (the page was left or the server stopped). Press <strong>Check eligibility</strong> again for the full results.</div>}
          {!busy && meta?.stale && <div className="notice warn-notice">You changed your profile after this check. Confirm your profile and press <strong>Check eligibility</strong> again to update these results.</div>}

          <div className="stats stats4">
            <div className="stat ok"><div className="ic">✔</div><div><div className="n">{counts.eligible || 0}</div><div className="t">Eligible</div></div></div>
            <div className="stat cond"><div className="ic">◐</div><div><div className="n">{counts.conditional || 0}</div><div className="t">Conditionally eligible</div></div></div>
            <div className="stat warn"><div className="ic">?</div><div><div className="n">{counts.insufficient_info || 0}</div><div className="t">Need more information</div></div></div>
            <div className="stat bad"><div className="ic">✖</div><div><div className="n">{counts.not_eligible || 0}</div><div className="t">Not eligible{nOutdated ? ` · ${nOutdated} past deadline` : ""}</div></div></div>
          </div>

          {top.length > 0 && (
            <>
              <div className="section-head"><h2>Your best matches</h2></div>
              <div className="cards3">
                {top.map(r => (
                  <div className="pcard" key={r.programme_id}>
                    <div className="name">#{ranks[r.programme_id]} {r.name}</div>
                    <div className="row"><Badge label={r.overall} />{r.deadline && <span className="muted">Deadline {r.deadline}</span>}</div>
                    <div className="row tight">{rankHints(r.ranking).map(h => <span key={h} className="hintchip">{h}</span>)}</div>
                    <div className="meta"><span className="fam-ico">{fam(r.family).flag || "🎓"}</span>{fam(r.family).name}</div>
                  </div>))}
              </div>
            </>
          )}

          <div className="card">
            <div className="section-head">
              <h2>All programmes, ranked</h2>
              <label className="toggle"><input type="checkbox" checked={showNotEligible} onChange={e => setShowNotEligible(e.target.checked)} /> Show programmes I don&apos;t qualify for</label>
            </div>
            <p className="muted small" style={{ marginTop: -4 }}>
              Order: open programmes before those past their deadline; then eligible, conditionally eligible and not enough information.
              Within each group, programmes are ordered by how close they are to your field and interests (60%), how much funding they give (25%)
              and how soon the deadline is (15%). The order never changes a verdict.
            </p>
            {GROUPS.filter(([g]) => g !== "not_eligible" || showNotEligible).map(([g, title]) => {
              const rows = results.filter(r => groupOf(r) === g && match(r));
              if (rows.length === 0) return null;
              return (
                <div key={g} className="group">
                  <h3 className={`group-title g-${g}`}>{title} <span className="muted">({rows.length})</span></h3>
                  {g === "outdated" && <p className="muted small">The deadline in the stored call has passed. These are never listed as eligible; check the official page for the next round.</p>}
                  {rows.map(r => <ResultCard key={r.programme_id} r={r} rank={ranks[r.programme_id]} calendar={calendar} onSave={toggleSave} />)}
                </div>
              );
            })}
            {!showNotEligible && (counts.not_eligible || 0) > 0 && <p className="muted small">{counts.not_eligible} programme(s) you don&apos;t qualify for are hidden.</p>}
          </div>
        </>
      )}

      <div className="section-head"><h2>Scholarship providers we check</h2><span className="muted">{families.reduce((a, [, n]) => a + n, 0)} programmes</span></div>
      <div className="tiles">
        {families.map(([f, n]) => {
          const fm = fam(f);
          return <div className="tile" key={f} style={{ backgroundColor: fm.color, backgroundImage: `linear-gradient(180deg, rgba(0,0,0,.05) 25%, rgba(0,0,0,.78)), url(/destinations/${f}.jpg)` }}>
            <span className="flag">{fm.flag || "🎓"}</span><div><div className="tn">{fm.name}</div><div className="tc">{n} programme{n > 1 ? "s" : ""}</div></div></div>;
        })}
      </div>
      <footer>ScholarFit advises only. The official programme page is always authoritative. Checked {today()}.</footer>
    </div>
  );
}
