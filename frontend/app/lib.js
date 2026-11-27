"use client";
// Shared by the check page and the dashboard. Display only: every verdict comes from the backend rule engine.
import { useEffect, useState } from "react";

export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const LABEL_TEXT = {
  eligible: "Eligible",
  conditional: "Conditionally eligible",
  insufficient_info: "Not enough information",
  not_eligible: "Not eligible",
  manual_check: "Checked by a person",
};

export const RESULT_CLASS = { eligible: "eligible", conditional: "conditional", insufficient_info: "insufficient_info", not_eligible: "not_eligible", manual_check: "manual_check" };

export const MISSING_TEXT = {
  not_met: "Not met",
  missing_info: "Missing information",
  condition: "Condition to meet",
  document: "Document to prepare",
  manual: "Checked by a person",
};

export const FAMILIES = {
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
export const fam = f => FAMILIES[f] || { name: f, flag: "", color: "#333" };

export function Badge({ label }) {
  return <span className={`badge ${RESULT_CLASS[label] || ""}`}>{LABEL_TEXT[label] || label}</span>;
}

export function NoticeBadges({ r }) {
  return (
    <>
      {r.outdated && <span className="badge outdated" title="The deadline in the stored call has passed">Deadline passed</span>}
      {r.call_changed && <span className="badge changed" title="The programme page changed; the curator is re-checking its criteria">
        Call changed on {r.call_changed.new_snapshot || "a recent date"}, criteria under review</span>}
    </>
  );
}

export const today = () => new Date().toISOString().slice(0, 10);
export const fmtTs = ts => ts ? new Date(ts * 1000).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "";

// One anonymous id per uploaded CV: links saved programmes and past checks to that profile without an account.
// Uploading another CV starts a new profile (newProfileId), so two CVs never share one dashboard.
const makeId = () => (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2));

export function getProfileId() {
  if (typeof window === "undefined") return null;
  let id = localStorage.getItem("scholarfit_profile_id");
  if (!id) { id = makeId(); localStorage.setItem("scholarfit_profile_id", id); }
  return id;
}

export function newProfileId() {
  const id = makeId();
  localStorage.setItem("scholarfit_profile_id", id);
  return id;
}

// Short description of the current profile, shown on the dashboard.
export function profileLabel(p) {
  if (!p) return null;
  const deg = (p.degrees || []).filter(d => ["bachelor", "master", "phd"].includes(d.level)).map(d => d.title || d.field || d.level);
  return [p.cv_name, deg.join(", ")].filter(Boolean).join(" · ") || "your profile";
}

// Ticked items of "What you still need", kept in the browser per profile (CV) and programme.
// An item is identified by its criterion, not its sentence: the sentence includes the reason,
// which changes when the profile changes, while the requirement stays the same.
const itemKey = m => m.criterion_id || `${m.type}|${m.evidence || m.action}`;

export function useTodoChecks(programmeId) {
  const [key, setKey] = useState(null);
  const [done, setDone] = useState({});
  useEffect(() => {
    const k = `scholarfit_todo_${getProfileId()}_${programmeId}`;
    setKey(k);
    try { setDone(JSON.parse(localStorage.getItem(k) || "{}")); } catch { setDone({}); }
  }, [programmeId]);
  const toggle = id => {
    setDone(d => {
      const next = { ...d, [id]: !d[id] };
      if (key) localStorage.setItem(key, JSON.stringify(next));
      return next;
    });
  };
  return [done, toggle];
}

export function MissingPanel({ programmeId, items, compact }) {
  const [done, toggle] = useTodoChecks(programmeId);
  if (!items || items.length === 0) return <p className="muted">Nothing left to do for this programme.</p>;
  return (
    <ul className={`todo ${compact ? "compact" : ""}`}>
      {items.map((m, i) => (
        <li key={itemKey(m) + i} className={done[itemKey(m)] ? "done" : ""}>
          <label className="todo-item">
            <input type="checkbox" checked={!!done[itemKey(m)]} onChange={() => toggle(itemKey(m))} />
            <span className={`kind ${m.kind}`}>{MISSING_TEXT[m.kind] || m.kind}</span>
            <span>{m.action}</span>
          </label>
          {!compact && m.evidence && <div className="quote">“{m.evidence}”</div>}
        </li>
      ))}
    </ul>
  );
}

export function CalendarButtons({ r, calendar }) {
  const [msg, setMsg] = useState("");
  if (!r.deadline) return null;
  async function add() {
    setMsg("Adding...");
    const res = await fetch(`${API}/api/calendar/add`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ programme_id: r.programme_id }) });
    const data = await res.json().catch(() => ({}));
    setMsg(res.ok ? "Added to Google Calendar" : (data.detail || "Failed"));
  }
  return (
    <>
      {calendar?.connected && !r.outdated && <button className="accent small" onClick={add}>Add deadline</button>}
      <a className="btn secondary small" href={`${API}/api/programmes/${r.programme_id}/deadline.ics`}>.ics</a>
      {msg && <span className="muted">{msg}</span>}
    </>
  );
}

export const DISCLAIMER = "ScholarFit checks the scholarship's stated eligibility conditions only. Meeting them means you may apply; it does not mean you are a competitive applicant or that you will be selected. Admission to the host university is decided separately by the university. The official programme page is always authoritative.";
