// Anupalan web client. Works against the FastAPI backend, or read-only from exported JSON (static demo).
const S = { live: true, meta: null };
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => (s ?? "").toString().replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = (d) => (d ? new Date(d + "T00:00:00").toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "No fixed deadline");
const asOf = () => S.meta?.as_of || new Date().toISOString().slice(0, 10);
const days = (d) => Math.round((new Date(d + "T00:00:00") - new Date(asOf() + "T00:00:00")) / 864e5);

// ---------- icons ----------
const P = {
  grid: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1z"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="3.5" cy="6" r="1"/><circle cx="3.5" cy="12" r="1"/><circle cx="3.5" cy="18" r="1"/>',
  chart: '<path d="M3 3v18h18"/><path d="M7 16v-4M12 16V8M17 16v-7"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5M12 3v12"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
  alert: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  user: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="m16 11 2 2 4-4"/>',
  cal: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  minus: '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
};
const icon = (n, st = "") => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"${st ? ` style="${st}"` : ""}>${P[n]}</svg>`;
const STATUS = {
  overdue: ["Overdue", "alert"], due_30d: ["Due ≤ 30 days", "clock"], open: ["Open", "cal"], no_fixed_deadline: ["No fixed deadline", "minus"],
  complied: ["Complied", "check"], rejected: ["Rejected", "x"], under_appeal: ["Under appeal", "file"], stayed: ["Stayed", "file"], in_progress: ["In progress", "clock"],
  pending: ["Awaiting review", "user"], confirmed: ["Confirmed", "check"], edited: ["Edited & confirmed", "edit"],
};
const badge = (s) => { const [l, i] = STATUS[s] || [s, "info"]; return `<span class="badge b-${s}">${icon(i)}${esc(l)}</span>`; };
const DEPTS = ["School Education","Higher Education","Health & Family Welfare","Police / Home","Finance / Pensions","Revenue & Disaster Mgmt",
  "Power (PSPCL / Nigams)","Rural Development & Panchayats","Local Government / Urban","Irrigation / Water Resources","Transport",
  "Agriculture & Cooperation","Forests & Environment","Social Justice & Welfare","Defence (Union)","Recruitment Commissions (HPSC/HSSC/PPSC/PSSSB)","Personnel / General Admin","To be assigned"];
const NAV = [["dashboard", "Dashboard", "grid"], ["review", "Review queue", "inbox"], ["register", "Obligation register", "list"], ["backtest", "Contempt backtest", "chart"], ["upload", "Add a court order", "upload"], ["about", "How it works", "info"]];

// ---------- data ----------
const local = () => { try { return JSON.parse(localStorage.getItem("anupalan-reviews") || "{}"); } catch { return {}; } };
const saveLocal = (v) => { try { localStorage.setItem("anupalan-reviews", JSON.stringify(v)); } catch {} };
async function get(path) {
  if (S.live) { const r = await fetch("/api" + path); if (!r.ok) throw new Error(r.status); return r.json(); }
  const map = { "/dashboard": "demo/dashboard.json", "/obligations": "demo/obligations.json", "/backtest": "demo/backtest.json" };
  const url = map[path.split("?")[0]] || (path.startsWith("/orders/") ? `demo/orders/${path.split("/")[2]}.json` : null);
  if (!url) return null;
  const data = await (await fetch(url)).json(), edits = local(), patch = (o) => (edits[o.id] ? { ...o, ...edits[o.id] } : o);
  if (Array.isArray(data)) return data.map(patch);
  if (Array.isArray(data.obligations)) data.obligations = data.obligations.map(patch);
  return data;
}
async function post(path, body) {
  if (S.live) return (await fetch("/api" + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })).json();
  const id = path.split("/")[2], edits = local(), e = edits[id] || {};
  if (body.action === "confirm") e.review_status = "confirmed";
  if (body.action === "edit") e.review_status = "edited";
  if (body.action === "reject") { e.review_status = "rejected"; e.status = "rejected"; }
  for (const k of ["due", "department", "obligor", "action_summary", "compliance_status"]) if (body[k]) e[k] = body[k];
  if (body.compliance_status === "complied") e.status = "complied";
  edits[id] = e; saveLocal(edits); return e;
}
const toast = (m) => { const t = $("#toast"); t.textContent = m; t.classList.remove("hidden"); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.add("hidden"), 2200); };
const tip = { show(e, html) { const t = $("#tip"); t.innerHTML = html; t.style.opacity = 1; t.style.left = Math.min(e.clientX + 14, innerWidth - 260) + "px"; t.style.top = e.clientY + 14 + "px"; }, hide() { $("#tip").style.opacity = 0; } };
const pageHead = (title, sub, right = "") => `<div class="top"><div><h1>${title}</h1>${sub ? `<p>${sub}</p>` : ""}</div>${right}</div>`;
const asofChip = () => `<span class="chip">${icon("cal")}Replay as of ${fmt(asOf())}</span>`;
function countdown(o) {
  if (!o.due) return `<div class="when" style="background:#F2F3F7;color:#69708A">—<small>no date</small></div>`;
  const d = days(o.due);
  if (d === 0) return `<div class="when w">Today<small>due</small></div>`;
  return d < 0 ? `<div class="when c">${-d}d<small>overdue</small></div>` : `<div class="when w">${d}d<small>left</small></div>`;
}

// ---------- charts ----------
function statusBar(counts) {
  const order = ["overdue", "due_30d", "open", "no_fixed_deadline", "complied"], total = order.reduce((a, k) => a + (counts[k] || 0), 0) || 1;
  const segs = order.filter((k) => counts[k]).map((k) => `<div class="s-${k}" style="flex:${counts[k]}" data-k="${k}" data-v="${counts[k]}"></div>`).join("");
  const leg = order.map((k) => `<span><i class="s-${k}"></i>${STATUS[k][0]} <b>${counts[k] || 0}</b> <span class="muted">(${Math.round(((counts[k] || 0) / total) * 100)}%)</span></span>`).join("");
  return `<div class="sbar" id="sbar">${segs}</div><div class="legend">${leg}</div>`;
}
function monthChart(obs) {
  const now = asOf().slice(0, 7), by = {};
  obs.filter((o) => o.due && o.status !== "rejected").forEach((o) => { const m = o.due.slice(0, 7); by[m] = (by[m] || 0) + 1; });
  const months = Object.keys(by).sort();
  if (!months.length) return "";
  const W = 640, H = 190, pad = { l: 28, r: 8, t: 16, b: 26 }, iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
  const max = Math.max(...Object.values(by)), step = Math.max(5, Math.ceil(max / 4 / 5) * 5), top_ = step * 4;
  const bw = iw / months.length, gap = Math.max(2, bw * 0.28), every = Math.ceil(months.length / 9);
  const lbl = (m) => new Date(m + "-01T00:00:00").toLocaleDateString("en-IN", { month: "short" }) + (m.endsWith("-01") || m === months[0] ? " '" + m.slice(2, 4) : "");
  let g = "";
  for (let i = 0; i <= 4; i++) { const y = pad.t + ih - (ih * i) / 4; g += `<line x1="${pad.l}" x2="${W - pad.r}" y1="${y}" y2="${y}"/><text class="ax" x="${pad.l - 6}" y="${y + 3.5}" text-anchor="end">${step * i}</text>`; }
  const bars = months.map((m, i) => {
    const v = by[m], h = Math.max(2, (v / top_) * ih), x = pad.l + i * bw + gap / 2, w = bw - gap, y = pad.t + ih - h, past = m < now, r = Math.min(4, w / 2, h);
    const col = past ? "var(--critical)" : m === now ? "var(--warning-mark)" : "var(--navy-2)";
    return `<g class="bar" data-m="${m}" data-v="${v}" data-p="${past ? 1 : 0}"><rect x="${pad.l + i * bw}" y="${pad.t}" width="${bw}" height="${ih}" fill="transparent"/>
      <path d="M${x},${pad.t + ih} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${pad.t + ih} Z" fill="${col}"/>
      ${i % every === 0 ? `<text class="ax" x="${x + w / 2}" y="${H - 8}" text-anchor="middle">${lbl(m)}</text>` : ""}</g>`;
  }).join("");
  const ni = months.findIndex((m) => m >= now), nx = pad.l + (ni < 0 ? months.length : ni) * bw;
  return `<div class="chart" id="mchart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Court-ordered deadlines per month"><g class="grid">${g}</g>${bars}
    <line x1="${nx}" x2="${nx}" y1="${pad.t - 8}" y2="${pad.t + ih}" stroke="var(--ink)" stroke-dasharray="3 3" stroke-width="1.2"/><text x="${nx + 5}" y="${pad.t - 2}" font-size="11" font-weight="700" fill="var(--ink)">Today</text></svg>
    <div class="legend" style="margin-top:6px"><span><i class="s-overdue"></i>Deadline passed</span><span><i class="s-due_30d"></i>This month</span><span><i style="background:var(--navy-2)"></i>Upcoming</span></div></div>`;
}
function histogram(h) {
  const W = 640, H = 210, pad = { l: 28, r: 8, t: 22, b: 30 }, iw = W - pad.l - pad.r, ih = H - pad.t - pad.b, max = Math.max(...h.map((x) => x.count));
  const top_ = Math.ceil(max / 10) * 10, bw = iw / h.length, gap = bw * 0.26;
  let g = ""; for (let i = 0; i <= 4; i++) { const y = pad.t + ih - (ih * i) / 4; g += `<line x1="${pad.l}" x2="${W - pad.r}" y1="${y}" y2="${y}"/><text class="ax" x="${pad.l - 6}" y="${y + 3.5}" text-anchor="end">${(top_ * i) / 4}</text>`; }
  const bars = h.map((x, i) => { const bh = Math.max(2, (x.count / top_) * ih), X = pad.l + i * bw + gap / 2, Y = pad.t + ih - bh, w = bw - gap, r = Math.min(4, bh);
    return `<g class="bar" data-l="${x.label === "before deadline" ? "Filed before the deadline" : x.label + " days after the deadline"}" data-v="${x.count}"><rect x="${pad.l + i * bw}" y="${pad.t}" width="${bw}" height="${ih}" fill="transparent"/>
    <path d="M${X},${pad.t + ih} V${Y + r} Q${X},${Y} ${X + r},${Y} H${X + w - r} Q${X + w},${Y} ${X + w},${Y + r} V${pad.t + ih} Z" fill="${i === 0 ? "var(--none)" : "var(--navy-2)"}"/>
    <text x="${X + w / 2}" y="${Y - 6}" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--ink)">${x.count}</text>
    <text class="ax" x="${X + w / 2}" y="${H - 10}" text-anchor="middle">${x.label === "before deadline" ? "before" : x.label}</text></g>`; }).join("");
  return `<div class="chart" id="hchart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Days between deadline and contempt filing"><g class="grid">${g}</g>${bars}</svg><div class="small" style="margin-top:4px">Days after the computed deadline</div></div>`;
}
function bindCharts() {
  document.querySelectorAll("#sbar div").forEach((d) => { d.onmousemove = (e) => tip.show(e, `<b>${STATUS[d.dataset.k][0]}</b><br>${d.dataset.v} court-ordered tasks`); d.onmouseleave = tip.hide; });
  document.querySelectorAll("#mchart .bar, #hchart .bar").forEach((b) => {
    b.onmousemove = (e) => tip.show(e, b.dataset.m ? `<b>${new Date(b.dataset.m + "-01T00:00:00").toLocaleDateString("en-IN", { month: "long", year: "numeric" })}</b><br>${b.dataset.v} deadlines${b.dataset.p === "1" ? " (already passed)" : ""}` : `<b>${b.dataset.l}</b><br>${b.dataset.v} contempt cases`);
    b.onmouseleave = tip.hide;
  });
}

// ---------- views ----------
const views = {
  async dashboard() {
    const [d, obs, bt] = await Promise.all([get("/dashboard"), get("/obligations"), get("/backtest").catch(() => ({}))]);
    const live = obs.filter((o) => o.review_status !== "rejected");
    const counts = { overdue: 0, due_30d: 0, open: 0, no_fixed_deadline: 0, complied: 0 };
    live.forEach((o) => { if (counts[o.status] !== undefined) counts[o.status]++; });
    const pend = live.filter((o) => o.review_status === "pending").length, pct = (n) => Math.round((n / (live.length || 1)) * 100);
    const deps = d.departments.filter((x) => x.department !== "To be assigned").slice(0, 8), maxO = Math.max(1, ...deps.map((x) => x.overdue));
    const soon = live.filter((o) => o.status === "due_30d").sort((a, b) => a.due.localeCompare(b.due));
    const late = live.filter((o) => o.status === "overdue").sort((a, b) => b.due.localeCompare(a.due));
    const next = [...soon, ...late].slice(0, 7);
    return pageHead("Compliance dashboard", `${d.orders} real Punjab &amp; Haryana High Court orders, read automatically. Every court-ordered task is tracked to a named office and a date.`, asofChip()) + `
    <div class="grid g-kpi">
      <div class="card kpi" onclick="go('register')"><div class="ic n">${icon("file")}</div><div><b>${live.length}</b><span>Court-ordered tasks</span><em>from ${d.orders} orders</em></div></div>
      <div class="card kpi" onclick="go('register','overdue')"><div class="ic c">${icon("alert")}</div><div><b style="color:var(--critical)">${counts.overdue}</b><span>Overdue · contempt risk</span><em>${pct(counts.overdue)}% of tasks</em></div></div>
      <div class="card kpi" onclick="go('register','due_30d')"><div class="ic w">${icon("clock")}</div><div><b style="color:#B07500">${counts.due_30d}</b><span>Due in next 30 days</span><em>act now to avoid contempt</em></div></div>
      <div class="card kpi" onclick="go('review')"><div class="ic t">${icon("user")}</div><div><b>${pend}</b><span>Awaiting legal-officer review</span><em>AI suggests, officers decide</em></div></div>
    </div>
    <div class="grid g-main">
      <div class="card"><h2>Where every court-ordered task stands</h2><p class="hint">Status of all ${live.length} tasks · hover for counts</p>${statusBar(counts)}
        <div style="margin-top:22px"><h2>Deadlines by month</h2><p class="hint">Bars left of “Today” are deadlines that have already passed</p>${monthChart(live)}</div></div>
      <div style="display:flex;flex-direction:column;gap:18px">${bt && bt.cases ? `<div class="card hero" onclick="go('backtest')"><h2>Backtest on real contempt cases</h2><div class="big">${bt.median_lead_days} days</div>
        <p>median warning Anupalan would have given <b style="color:#fff">before</b> citizens had to file contempt, across ${bt.cases} real cases traced back to the original order.</p>
        <div class="row"><div><b>${bt.captured_pct}%</b><span>directions captured</span></div><div><b>${bt.deadline_before_contempt_pct}%</b><span>deadline passed before contempt</span></div><div><b>${bt.median_order_to_contempt_days}d</b><span>order → contempt</span></div></div>
        <span class="go">See the evidence ${icon("arrow", "width:15px;height:15px")}</span></div>` : ""}
      <div class="card" style="flex:1"><h2>Why now</h2><p class="hint">The mandate exists; the tool does not</p><ul class="why">
        <li><b>Supreme Court, 2026</b>Directions must be “monitored, tracked, and complied with within the time prescribed” (2026 INSC 642).</li>
        <li><b>Dept. of Justice, Jan 2025</b>Every ministry to “establish a Compliance Mechanism” for court orders.</li>
        <li><b>~1.5 lakh</b>contempt cases pending in Indian courts (Law Ministry, Lok Sabha, Mar 2025).</li></ul></div></div>
    </div>
    <div class="grid g-bottom">
      <div class="card"><h2>Departments by contempt risk</h2><p class="hint">Overdue court-ordered tasks per department</p>
        <table><tr><th>Department</th><th>Govt</th><th style="width:34%">Overdue</th><th>Due ≤30d</th><th>Tasks</th></tr>
        ${deps.map((x) => `<tr class="click" onclick="go('register','','${esc(x.department)}')"><td><b>${esc(x.department)}</b></td><td class="muted">${esc(x.government)}</td>
          <td><span class="count ${x.overdue ? "c" : "z"}">${x.overdue}</span><div class="rbar"><i style="width:${(x.overdue / maxO) * 100}%"></i></div></td>
          <td><span class="count ${x.due_30d ? "w" : "z"}">${x.due_30d}</span></td><td>${x.total}</td></tr>`).join("")}</table></div>
      <div class="card"><h2>Act next</h2><p class="hint">Due soonest, then most recently missed</p><ul class="dl">
        ${next.map((o) => `<li onclick="openOb(${o.order_id}, ${o.id})">${countdown(o)}<div><b class="mono">${esc(o.case_no)}</b> ${badge(o.status)}<div class="what">${esc(o.action_summary || o.action_type)}</div><div class="small">${esc(o.department)} · due ${fmt(o.due)}</div></div></li>`).join("")}</ul></div>
    </div>`;
  },
  async review() {
    const obs = (await get("/obligations")).filter((o) => o.review_status === "pending").sort((a, b) => a.confidence - b.confidence);
    const m = S.live ? await get("/metrics") : null;
    const ring = (c) => { const p = Math.round(c * 100), col = p >= 85 ? "var(--good-mark)" : p >= 65 ? "var(--warning-mark)" : "var(--critical)";
      return `<div class="conf" title="AI confidence" style="background:conic-gradient(${col} ${p * 3.6}deg,var(--line-2) 0)"><span style="position:absolute;inset:5px;border-radius:50%;background:#fff;display:grid;place-items:center">${p}%</span></div>`; };
    return pageHead("Review queue", "AI suggests, a legal officer decides. Lowest confidence first; each task opens beside the exact sentence in the order.",
      m && m.reviewed ? `<span class="chip">${icon("check")}${m.reviewed} reviewed · ${Math.round(m.precision_task_is_real * 100)}% real tasks · ${Math.round(m.exact_without_edits * 100)}% no edits</span>` : `<span class="chip">${icon("inbox")}${obs.length} awaiting review</span>`) +
    `<div class="rq">${obs.slice(0, 120).map((o) => `<div class="card rqi" onclick="openOb(${o.order_id}, ${o.id})">${ring(o.confidence)}
      <div><b>${esc(o.action_summary || o.action_type)}</b><div class="small"><span class="mono">${esc(o.case_no)}</span> · ${esc(o.department)} · ${esc(o.obligor || "")}</div><div class="q">“${esc(o.text.slice(0, 220))}”</div></div>
      <div style="text-align:right">${badge(o.status)}${o.due ? `<div class="small" style="margin-top:6px">Due ${fmt(o.due)}</div>` : ""}</div></div>`).join("")}</div>`;
  },
  async register(status = "", dept = "") {
    const all = await get("/obligations"), depts = [...new Set(all.map((o) => o.department))].sort();
    const rows = all.filter((o) => (!status || o.status === status) && (!dept || o.department === dept));
    const segs = [["", "All"], ["overdue", "Overdue"], ["due_30d", "Due ≤30d"], ["open", "Open"], ["no_fixed_deadline", "No date"], ["complied", "Complied"]];
    return pageHead("Obligation register", "One row per court-ordered task: what, who, by when, and where it stands.", asofChip()) +
    `<div class="filters"><div class="seg">${segs.map(([k, l]) => `<button class="${k === status ? "on" : ""}" onclick="go('register','${k}',$('#f-dept').value)">${l}</button>`).join("")}</div>
      <select id="f-dept" onchange="go('register','${status}',this.value)"><option value="">All departments</option>${depts.map((x) => `<option ${x === dept ? "selected" : ""}>${esc(x)}</option>`).join("")}</select>
      <span class="small">${rows.length} tasks</span></div>
    <div class="tbl"><table><tr><th>Status</th><th>Deadline</th><th>Case</th><th>What must be done</th><th>Responsible office</th><th>Review</th></tr>
    ${rows.slice(0, 400).map((o) => `<tr class="click" onclick="openOb(${o.order_id}, ${o.id})"><td>${badge(o.status)}</td><td><b>${o.due ? fmt(o.due) : "—"}</b><div class="small">${o.due ? (days(o.due) < 0 ? -days(o.due) + " days ago" : "in " + days(o.due) + " days") : "internal target"}</div></td>
      <td class="mono">${esc(o.case_no)}<div class="small">order ${fmt(o.decision_date)}</div></td><td>${esc(o.action_summary || o.text.slice(0, 150))}</td><td><b>${esc(o.department)}</b><div class="small">${esc(o.government)}</div></td><td>${badge(o.review_status)}</td></tr>`).join("")}</table></div>`;
  },
  async backtest() {
    const b = await get("/backtest");
    if (!b || !b.cases) return pageHead("Contempt backtest", "No backtest results loaded.");
    return pageHead("Would Anupalan have prevented these contempt cases?", b.method) +
    `<div class="stat"><div class="card"><b>${b.cases}</b><span>real contempt cases traced to the original order</span></div><div class="card"><b>${b.captured_pct}%</b><span>original orders where the direction was captured</span></div>
      <div class="card"><b>${b.deadline_before_contempt_pct}%</b><span>of dated cases: deadline passed before contempt was filed</span></div><div class="card" style="background:var(--navy);border:0"><b style="color:#FFC983">${b.median_lead_days} days</b><span style="color:#C7CFF2">median early warning departments never got</span></div></div>
    <div class="grid g-main"><div class="card"><h2>How long after the deadline did citizens file contempt?</h2><p class="hint">Contempt cases by days between the deadline Anupalan computed from the original order and the contempt filing · ${b.dated} cases with a deadline</p>${histogram(b.histogram)}</div>
      <div class="card"><h2>Reading the result</h2><p class="hint">What this shows, and what it does not</p><ul style="margin:0;padding-left:18px;line-height:1.7">
        <li>The obligation that later became a contempt case was <b>captured in ${b.captured_pct}%</b> of original orders (direct ${b.direct_pct}%, plus orders that only point to another judgment).</li>
        <li>${b.dated_pct}% had a computable deadline; the rest say “in accordance with law” and get a 30-day internal target.</li>
        <li>Median <b>${b.median_order_to_contempt_days} days</b> from order to contempt: the window in which a reminder could act.</li>
        <li class="muted">It shows a dated warning would have existed, not that contempt would certainly have been avoided.</li></ul></div></div>
    <div class="card" style="margin-top:18px"><h2>Examples from the backtest</h2><p class="hint">Real Punjab &amp; Haryana High Court cases</p>
    <table><tr><th>Original order</th><th>Direction captured</th><th>Deadline</th><th>Contempt filed</th><th style="width:130px">Warning</th></tr>
    ${b.examples.map((e) => `<tr><td class="mono">${esc(e.orig_title)}<div class="small">order ${fmt(e.orig_order_date)}</div></td><td>${esc(e.summary)}<div class="small">${esc(e.obligor || "")}</div></td><td>${fmt(e.first_due)}</td><td>${fmt(e.cocp_filed)}</td><td><b>${e.lead_days} days</b><div class="rbar"><i style="background:var(--navy-2);width:${Math.min(100, (e.lead_days / 400) * 100)}%"></i></div></td></tr>`).join("")}</table></div>`;
  },
  async upload() {
    if (!S.live) return pageHead("Add a court order", "") + `<div class="card">The public demo is read-only. Run Anupalan locally (see the README) to drop in any High Court order PDF and watch it become tracked tasks in seconds.</div>`;
    return pageHead("Add a court order", "Drop any High Court order (PDF). Anupalan reads it, finds each direction, computes the deadline and routes it to a legal officer.") +
      `<label class="drop" id="drop"><input type="file" id="file" accept="application/pdf" hidden>${icon("upload")}<b>Drop a PDF here or click to choose</b><div class="small">Digital or scanned orders · OCR is applied automatically</div></label><div id="up-result" style="margin-top:18px"></div>`;
  },
  async about() {
    const st = [["Read", "The order PDF from open High Court data, a court website or a department upload. OCR for scanned copies; signature stamps and page headers removed."],
      ["Find", "A rule engine marks sentences where the court directs an authority, and skips counsel’s submissions, liberty clauses and Registry directions."],
      ["Structure", "Claude returns who, what and conditions as JSON. Every quote must match the order word for word, or it is dropped."],
      ["Date", "A deterministic engine converts “within a fortnight” or “four months from receipt of certified copy” into a date, with its reasoning. The AI never computes dates."],
      ["Link", "Orders “disposed of in terms of CWP-X” are linked to the judgment that holds the actual direction."],
      ["Confirm", "A legal officer confirms, edits or rejects in one click. Every change is in the audit trail."],
      ["Track & warn", "Alerts before the deadline and escalation when it is missed; dashboards by department."],
      ["Plug in", "Exports to LIMBS and state case trackers. Anupalan adds the obligation layer they lack instead of replacing them."]];
    return pageHead("How Anupalan works", "Existing case trackers record hearings and next dates, typed in by officers. Anupalan reads the judgment itself and turns each direction into a tracked task.") +
      `<ol class="steps">${st.map(([a, b]) => `<li><b>${a}</b>${b}</li>`).join("")}</ol>`;
  },
};

// ---------- obligation drawer ----------
async function openOb(orderId, obId) {
  const o = await get(`/orders/${orderId}`);
  const ob = o.obligations.find((x) => x.id === obId) || o.obligations[0], dl = ob.deadline || {};
  let out = "", pos = 0;
  for (const s of o.obligations.filter((x) => x.start >= 0).sort((a, b) => a.start - b.start)) {
    if (s.start < pos) continue;
    out += esc(o.text.slice(pos, s.start)) + `<mark id="m${s.id}" class="${s.id === ob.id ? "" : "other"}">${esc(o.text.slice(s.start, s.end))}</mark>`; pos = s.end;
  }
  out += esc(o.text.slice(pos));
  const ev = S.live ? await get(`/obligations/${ob.id}/events`).catch(() => []) : [];
  const d = ob.due ? days(ob.due) : null;
  $("#drawer-inner").innerHTML = `<div class="dhead"><div><h3>${esc(o.title || o.case_no)}</h3><div class="meta">Order dated ${fmt(o.decision_date)} · ${esc(o.judge || "")} · read via ${esc(o.text_method || "text")}</div></div>
    <div style="display:flex;gap:6px;align-items:center;margin-left:auto">${badge(ob.status)}${badge(ob.review_status)}</div><button class="x" onclick="closeDrawer()" aria-label="Close">✕</button></div>
  <div class="dbody"><div><p class="label">Court order · highlighted sentence = source of this task</p><div class="ordertext" id="otext">${out}</div></div>
  <div>
    <p class="label">Deadline</p>
    <div class="due"><div style="width:42px;height:42px;border-radius:12px;display:grid;place-items:center;flex:none" class="ic ${d === null ? "n" : d < 0 ? "c" : "w"}">${icon(d === null ? "minus" : d < 0 ? "alert" : "clock", "width:21px;height:21px")}</div>
      <div><div class="d">${ob.due ? fmt(ob.due) : "No fixed deadline"}</div><div class="small">${d === null ? "30-day internal target applied" : d < 0 ? `${-d} days overdue on ${fmt(asOf())}` : `${d} days left on ${fmt(asOf())}`}</div></div>
      <input type="date" id="e-due" value="${ob.due || ""}" class="cd" style="padding:8px 10px;border:1px solid var(--line);border-radius:10px" aria-label="Edit deadline"></div>
    ${dl.basis ? `<div class="basis"><b>How the date was computed:</b> ${esc(dl.basis)}</div>` : `<div class="warn">${ob.ref_case ? `This order points to <b>${esc(ob.ref_case)}</b>; its directions are fetched from that judgment for review.` : "The court gave no time limit. A 30-day internal target is applied and flagged."}</div>`}
    ${(dl.assumptions || []).map((a) => `<div class="warn">Assumption: ${esc(a)}</div>`).join("")}
    <div class="field" style="margin-top:14px"><p class="label">What must be done</p><input id="e-action" value="${esc(ob.action_summary || ob.action_type)}"></div>
    <div class="field"><p class="label">Directed authority (as named in the order)</p><input id="e-obligor" value="${esc(ob.obligor || "")}"></div>
    <div class="field"><p class="label">Responsible department <span style="text-transform:none;letter-spacing:0;font-weight:500">· ${esc(ob.department_evidence || "")}</span></p><select id="e-dept">${DEPTS.map((x) => `<option ${x === ob.department ? "selected" : ""}>${esc(x)}</option>`).join("")}</select></div>
    <div class="small">Extracted by ${esc(ob.source)} · confidence ${Math.round((ob.confidence || 0) * 100)}%</div>
    <div class="btns"><button class="btn ok" onclick="act(${ob.id},'confirm',${orderId})">${icon("check")}Confirm</button><button class="btn sec" onclick="act(${ob.id},'edit',${orderId})">${icon("edit")}Save edits &amp; confirm</button><button class="btn no" onclick="act(${ob.id},'reject',${orderId})">${icon("x")}Reject</button></div>
    <div class="field"><p class="label">Compliance status</p><select id="e-comp" onchange="act(${ob.id},'status',${orderId})">${["open","in_progress","complied","under_appeal","stayed"].map((s) => `<option ${s === ob.compliance_status ? "selected" : ""} value="${s}">${s.replace("_", " ")}</option>`).join("")}</select></div>
    <div class="section"><p class="label">Alert schedule</p><ul class="timeline">${(ob.alerts || []).map((a) => `<li class="${a.on < asOf() ? "past" : ""}"><b>${fmt(a.on)}</b>${esc(a.kind)}</li>`).join("")}</ul></div>
    <div class="section"><p class="label">Alert preview · to the nodal officer</p><div class="preview"><div class="from"><img src="brand/logo-mark.svg" alt="">Anupalan</div>Court-ordered task <b>${esc(o.case_no)}</b> (${esc(ob.department)}) is due on <b>${fmt(ob.due)}</b>: ${esc(ob.action_summary || "")}. Order dated ${fmt(o.decision_date)}. Mark compliance, or record an appeal or stay, to avoid contempt.</div></div>
    ${ev && ev.length ? `<div class="section"><p class="label">Audit trail</p><ul class="timeline">${ev.map((e) => `<li><b>${esc(e.ts.slice(0, 16).replace("T", " "))}</b>${esc(e.actor)} · ${esc(e.action)}${e.detail ? " · " + esc(e.detail) : ""}</li>`).join("")}</ul></div>` : ""}
  </div></div>`;
  $("#drawer").classList.remove("hidden");
  const m = document.getElementById("m" + ob.id), ot = $("#otext");
  if (m && ot) ot.scrollTop = m.offsetTop - ot.offsetTop - ot.clientHeight / 3;
  $("#drawer-inner").scrollTop = 0;
}
function closeDrawer() { $("#drawer").classList.add("hidden"); }
async function act(id, action, orderId) {
  const body = { action };
  if (action === "edit") Object.assign(body, { due: $("#e-due").value || null, department: $("#e-dept").value, obligor: $("#e-obligor").value, action_summary: $("#e-action").value });
  if (action === "status") Object.assign(body, { compliance_status: $("#e-comp").value });
  await post(`/obligations/${id}/review`, body);
  toast({ confirm: "Confirmed and assigned", edit: "Saved and confirmed", reject: "Rejected (kept in the audit trail)", status: "Compliance status updated" }[action]);
  await openOb(orderId, id); render(false);
}

// ---------- router ----------
let current = ["dashboard"];
async function go(view, ...args) { current = [view, ...args]; if (location.hash !== "#" + view) history.replaceState(null, "", "#" + view); await render(); }
async function render(scroll = true) {
  const [view, ...args] = current;
  $("#nav").innerHTML = NAV.map(([k, l, i]) => `<a href="#${k}" data-view="${k}" class="${k === view ? "active" : ""}">${icon(i)}${l}${k === "review" ? '<span id="nav-pending" class="pill"></span>' : ""}</a>`).join("");
  document.querySelectorAll("nav a").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); go(a.dataset.view); }));
  $("#main").innerHTML = await views[view](...args);
  bindCharts(); refreshBadge();
  if (scroll) window.scrollTo(0, 0);
  if (view === "upload" && S.live) bindUpload();
}
function bindUpload() {
  const drop = $("#drop"), file = $("#file");
  const send = async (f) => {
    $("#up-result").innerHTML = `<div class="card"><span class="spin"></span>Reading <b>${esc(f.name)}</b> · OCR, rule engine and AI extraction…</div>`;
    const fd = new FormData(); fd.append("file", f);
    const o = await (await fetch("/api/upload", { method: "POST", body: fd })).json();
    $("#up-result").innerHTML = `<div class="card"><h2>${o.obligations.length} court-ordered task${o.obligations.length === 1 ? "" : "s"} found in ${esc(o.case_no || f.name)}</h2><p class="hint">Order dated ${fmt(o.decision_date)} · click a task to review it against the order</p>
      <table>${o.obligations.map((x) => `<tr class="click" onclick="openOb(${o.id}, ${x.id})"><td>${badge(x.status)}</td><td><b>${esc(x.action_summary || x.text.slice(0, 140))}</b><div class="small">${esc(x.obligor || "")} · ${esc(x.department)}</div></td><td><b>${fmt(x.due)}</b></td></tr>`).join("") || "<tr><td>No direction to a government authority found in this order.</td></tr>"}</table></div>`;
    refreshBadge();
  };
  file.onchange = () => file.files[0] && send(file.files[0]);
  drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("on"); };
  drop.ondragleave = () => drop.classList.remove("on");
  drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("on"); e.dataTransfer.files[0] && send(e.dataTransfer.files[0]); };
}
async function refreshBadge() { const obs = await get("/obligations"); const el = $("#nav-pending"); if (el) el.textContent = obs.filter((o) => o.review_status === "pending").length || ""; }
window.addEventListener("hashchange", () => { const v = location.hash.slice(1); closeDrawer(); if (views[v] && v !== current[0]) { current = [v]; render(); } });
$("#drawer").addEventListener("click", (e) => { if (e.target.id === "drawer") closeDrawer(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });
(async () => {
  try { const r = await fetch("/api/meta"); if (!r.ok) throw 0; S.meta = await r.json(); S.live = true; } catch { S.live = false; S.meta = await (await fetch("demo/dashboard.json")).json(); }
  $("#mode").innerHTML = S.live ? `<span class="dot"></span><b>Live</b> · connected to the Anupalan API<br>Data: P&amp;H High Court orders, open dataset (CC-BY-4.0)`
    : `<b>Public demo</b> · read-only. Reviews are saved only in this browser.<br>Data: P&amp;H High Court orders, open dataset (CC-BY-4.0)`;
  const v = (location.hash || "#dashboard").slice(1); current = [views[v] ? v : "dashboard"]; await render();
})();
