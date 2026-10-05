// Anupalan web client. Works against the FastAPI backend, or read-only from exported JSON (static demo).
const S = { live: true, meta: null, deptList: [] };
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => (s ?? "").toString().replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = (d) => (d ? new Date(d + "T00:00:00").toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "No fixed deadline");
const STATUS = { overdue: "Overdue", due_30d: "Due in 30 days", open: "Open", no_fixed_deadline: "No fixed deadline", complied: "Complied",
  rejected: "Rejected", under_appeal: "Under appeal", stayed: "Stayed" };
const badge = (s, label) => `<span class="badge b-${s}">${esc(label || STATUS[s] || s)}</span>`;
const DEPTS = ["School Education","Higher Education","Health & Family Welfare","Police / Home","Finance / Pensions","Revenue & Disaster Mgmt",
  "Power (PSPCL / Nigams)","Rural Development & Panchayats","Local Government / Urban","Irrigation / Water Resources","Transport",
  "Agriculture & Cooperation","Forests & Environment","Social Justice & Welfare","Defence (Union)","Recruitment Commissions (HPSC/HSSC/PPSC/PSSSB)","Personnel / General Admin","To be assigned"];

// ---------- data layer ----------
const local = () => { try { return JSON.parse(localStorage.getItem("anupalan-reviews") || "{}"); } catch { return {}; } };
const saveLocal = (v) => { try { localStorage.setItem("anupalan-reviews", JSON.stringify(v)); } catch {} };
async function get(path) {
  if (S.live) { const r = await fetch("/api" + path); if (!r.ok) throw new Error(r.status); return r.json(); }
  const map = { "/dashboard": "demo/dashboard.json", "/obligations": "demo/obligations.json", "/backtest": "demo/backtest.json" };
  let url = map[path.split("?")[0]] || (path.startsWith("/orders/") ? `demo/orders/${path.split("/")[2]}.json` : null);
  if (!url) return [];
  const data = await (await fetch(url)).json();
  const edits = local();
  const patch = (o) => (edits[o.id] ? { ...o, ...edits[o.id] } : o);
  if (Array.isArray(data)) return data.map(patch);
  if (data.obligations) data.obligations = data.obligations.map(patch);
  return data;
}
async function post(path, body) {
  if (S.live) { const r = await fetch("/api" + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); return r.json(); }
  const id = path.split("/")[2], edits = local(), e = edits[id] || {};
  if (body.action === "confirm") e.review_status = "confirmed";
  if (body.action === "reject") { e.review_status = "rejected"; e.status = "rejected"; }
  for (const k of ["due", "department", "obligor", "action_summary", "compliance_status"]) if (body[k]) e[k] = body[k];
  if (body.compliance_status === "complied") e.status = "complied";
  edits[id] = e; saveLocal(edits); return e;
}
function toast(m) { const t = $("#toast"); t.textContent = m; t.classList.remove("hidden"); setTimeout(() => t.classList.add("hidden"), 2200); }

// ---------- views ----------
const views = {
  async dashboard() {
    const d = await get("/dashboard");
    const bt = await get("/backtest").catch(() => ({}));
    S.deptList = d.departments;
    return `<h1>Compliance dashboard <span class="asof">as of ${fmt(d.as_of)}</span></h1>
    <p class="sub">${d.orders} real Punjab &amp; Haryana High Court orders read automatically; every court-ordered task is tracked to a named office and date.</p>
    <div class="kpis">
      <div class="kpi" onclick="go('register','overdue')"><b class="">${d.obligations}</b><span>Court-ordered obligations</span></div>
      <div class="kpi red" onclick="go('register','overdue')"><b>${d.counts.overdue}</b><span>Overdue (contempt risk)</span></div>
      <div class="kpi amber" onclick="go('register','due_30d')"><b>${d.counts.due_30d}</b><span>Due in next 30 days</span></div>
      <div class="kpi teal" onclick="go('review')"><b>${d.pending_review}</b><span>Awaiting legal-officer review</span></div>
      <div class="kpi" onclick="go('register','no_fixed_deadline')"><b>${d.counts.no_fixed_deadline}</b><span>No fixed deadline (30-day internal target)</span></div>
    </div>
    ${bt.cases ? `<div class="callout" onclick="go('backtest')"><b>${bt.median_lead_days} days</b><p><strong>Backtest on ${bt.cases} real contempt cases:</strong> Anupalan captured the court's direction in ${bt.captured_pct}% of the original orders, and the computed deadline had passed a median ${bt.median_lead_days} days before the citizen had to file contempt. That is the warning window departments never got.</p></div>` : ""}
    <div class="grid2"><div><h2>Departments by contempt risk</h2><div class="card"><table><tr><th>Government</th><th>Department</th><th>Tasks</th><th>Overdue</th><th>Due 30d</th></tr>
      ${d.departments.slice(0, 14).map((x) => `<tr class="click" onclick="go('register','', '${esc(x.department)}')"><td>${esc(x.government)}</td><td>${esc(x.department)}</td><td>${x.total}</td><td>${x.overdue ? badge("overdue", x.overdue) : "0"}</td><td>${x.due_30d ? badge("due_30d", x.due_30d) : "0"}</td></tr>`).join("")}
    </table></div></div>
    <div><h2>Next deadlines and overdue</h2><div class="card"><table>${d.upcoming.map((o) => `<tr class="click" onclick="openOb(${o.order_id}, ${o.id})"><td>${badge(o.status)}<div class="small">${fmt(o.due)}</div></td><td><b>${esc(o.case_no)}</b><div class="small">${esc(o.action_summary || o.action_type)}</div><div class="small">${esc(o.department)}</div></td></tr>`).join("")}</table></div></div></div>`;
  },
  async review() {
    const obs = (await get("/obligations")).filter((o) => o.review_status === "pending");
    const m = S.live ? await get("/metrics") : null;
    return `<h1>Review queue</h1><p class="sub">AI suggests, a legal officer decides. Each item links to the exact sentence in the court order. Lowest confidence first.</p>
    ${m && m.reviewed ? `<div class="card" style="margin-bottom:14px"><b>Review accuracy so far:</b> ${m.reviewed} reviewed · ${Math.round(m.precision_task_is_real * 100)}% were real court-ordered tasks · ${Math.round(m.exact_without_edits * 100)}% needed no edits · ${m.rejected} rejected</div>` : ""}
    <div class="card"><table><tr><th>Case</th><th>Direction (as extracted)</th><th>Deadline</th><th>Confidence</th></tr>
    ${obs.sort((a, b) => a.confidence - b.confidence).slice(0, 300).map((o) => `<tr class="click" onclick="openOb(${o.order_id}, ${o.id})"><td class="mono">${esc(o.case_no)}</td><td>${esc(o.action_summary || o.text.slice(0, 140))}<div class="small">${esc(o.department)} · ${esc(o.obligor || "")}</div></td><td>${fmt(o.due)}</td><td>${Math.round(o.confidence * 100)}%</td></tr>`).join("")}</table></div>`;
  },
  async register(status = "", dept = "") {
    const all = await get("/obligations");
    const depts = [...new Set(all.map((o) => o.department))].sort();
    const rows = all.filter((o) => (!status || o.status === status) && (!dept || o.department === dept));
    return `<h1>Obligation register</h1><p class="sub">One row per court-ordered task: what, who, by when, and its status.</p>
    <div class="filters"><select id="f-status" onchange="go('register', this.value, $('#f-dept').value)"><option value="">All statuses</option>${Object.entries(STATUS).map(([k, v]) => `<option value="${k}" ${k === status ? "selected" : ""}>${v}</option>`).join("")}</select>
    <select id="f-dept" onchange="go('register', $('#f-status').value, this.value)"><option value="">All departments</option>${depts.map((x) => `<option ${x === dept ? "selected" : ""}>${esc(x)}</option>`).join("")}</select>
    <span class="small" style="align-self:center">${rows.length} obligations</span></div>
    <div class="card"><table><tr><th>Status</th><th>Due</th><th>Case</th><th>What must be done</th><th>Responsible</th><th>Review</th></tr>
    ${rows.slice(0, 400).map((o) => `<tr class="click" onclick="openOb(${o.order_id}, ${o.id})"><td>${badge(o.status)}</td><td>${fmt(o.due)}</td><td class="mono">${esc(o.case_no)}<div class="small">order ${fmt(o.decision_date)}</div></td><td>${esc(o.action_summary || o.text.slice(0, 150))}</td><td>${esc(o.department)}<div class="small">${esc(o.government)}</div></td><td>${badge(o.review_status)}</td></tr>`).join("")}</table></div>`;
  },
  async backtest() {
    const b = await get("/backtest");
    if (!b.cases) return `<h1>Backtest</h1><p>No backtest results loaded.</p>`;
    const max = Math.max(...b.histogram.map((h) => h.count));
    return `<h1>Backtest: would Anupalan have prevented these contempt cases?</h1>
    <p class="sub">${b.method}</p>
    <div class="stat3"><div class="card"><b>${b.cases}</b>real contempt cases traced to their original order</div><div class="card"><b>${b.captured_pct}%</b>original orders where the direction was captured</div><div class="card"><b>${b.dated_pct}%</b>with a computed deadline</div><div class="card"><b>${b.median_lead_days} days</b>median warning before contempt was filed</div></div>
    <h2>How long after the deadline did citizens have to file contempt?</h2><div class="card"><div class="bars">${b.histogram.map((h) => `<div style="height:${(h.count / max) * 100}%"><span>${h.count}</span></div>`).join("")}</div><div class="barlbl">${b.histogram.map((h) => `<span>${h.label}</span>`).join("")}</div>
    <p class="small">Days between the deadline Anupalan computed from the original order and the date the contempt petition was registered (cases with a computed deadline).</p></div>
    <h2>Examples</h2><div class="card"><table><tr><th>Original order</th><th>Direction captured</th><th>Deadline</th><th>Contempt filed</th><th>Warning</th></tr>
    ${b.examples.map((e) => `<tr><td class="mono">${esc(e.orig_title)}<div class="small">order ${fmt(e.orig_order_date)}</div></td><td>${esc(e.summary)}<div class="small">${esc(e.obligor || "")}</div></td><td>${fmt(e.first_due)}</td><td>${fmt(e.cocp_filed)}</td><td><b>${e.lead_days} days</b></td></tr>`).join("")}</table></div>`;
  },
  async upload() {
    if (!S.live) return `<h1>Add a court order</h1><div class="card">The public demo is read-only. Run Anupalan locally (see README) to upload any High Court order PDF and watch it become tracked obligations in seconds.</div>`;
    return `<h1>Add a court order</h1><p class="sub">Drop any High Court order (PDF). Anupalan reads it, finds each direction, computes the deadline and routes it for review.</p>
    <label class="drop" id="drop"><input type="file" id="file" accept="application/pdf" hidden><b>Drop a PDF here or click to choose</b><div class="small">Scanned orders are read with OCR</div></label><div id="up-result"></div>`;
  },
  async about() {
    return `<h1>How Anupalan works</h1><p class="sub">Existing case trackers record hearings and next dates, typed in by officers. Anupalan reads the judgment itself and turns each direction into a tracked task.</p>
    <div class="card"><ol class="steps">
    <li><b>Read</b>: the order PDF (open High Court data, court website or upload); OCR for scanned copies; page stamps removed.</li>
    <li><b>Find</b>: a rule engine marks sentences where the court directs an authority; counsel's submissions, liberty clauses and Registry directions are excluded.</li>
    <li><b>Structure</b>: an LLM (Claude) returns who, what and conditions as JSON. Every quote is checked word-for-word against the order; anything not found is dropped.</li>
    <li><b>Date</b>: a deterministic deadline engine converts "within a fortnight", "four months from receipt of certified copy" and chained conditions into a date with a plain-English basis. The AI never computes dates.</li>
    <li><b>Link</b>: orders "disposed of in terms of CWP-X" are linked to the judgment that holds the actual direction.</li>
    <li><b>Confirm</b>: a legal officer confirms, edits or rejects in one click; every change is in the audit trail.</li>
    <li><b>Track &amp; warn</b>: alerts before the deadline, escalation when overdue, dashboards by department; export to LIMBS / state case trackers.</li></ol></div>`;
  },
};

// ---------- obligation drawer ----------
async function openOb(orderId, obId) {
  const o = await get(`/orders/${orderId}`);
  const ob = o.obligations.find((x) => x.id === obId) || o.obligations[0];
  let html = esc(o.text), shift = 0;
  const spans = o.obligations.filter((x) => x.start >= 0).sort((a, b) => a.start - b.start);
  // build highlighted text from original spans
  let out = "", pos = 0;
  for (const s of spans) { if (s.start < pos) continue; out += esc(o.text.slice(pos, s.start)) + `<mark id="m${s.id}" class="${s.id === ob.id ? "" : "other"}">` + esc(o.text.slice(s.start, s.end)) + "</mark>"; pos = s.end; }
  out += esc(o.text.slice(pos));
  const dl = ob.deadline || {};
  const today = S.meta?.as_of || new Date().toISOString().slice(0, 10);
  $("#drawer-inner").innerHTML = `<button class="x" onclick="closeDrawer()">✕</button>
  <div><h3>${esc(o.title || o.case_no)}</h3><div class="small">Order dated ${fmt(o.decision_date)} · ${esc(o.judge || "")} · read via ${esc(o.text_method || "text")}</div><p class="small">Highlighted: the sentence this task was extracted from.</p><div class="ordertext" id="otext">${out}</div></div>
  <div><h3>Court-ordered obligation ${badge(ob.status)} ${badge(ob.review_status)}</h3>
   <div class="field"><label>What must be done</label><input id="e-action" value="${esc(ob.action_summary || ob.action_type)}"></div>
   <div class="field"><label>Directed authority (as named in the order)</label><input id="e-obligor" value="${esc(ob.obligor || "")}"></div>
   <div class="field"><label>Responsible department <span class="small">(${esc(ob.department_evidence || "")})</span></label><select id="e-dept">${DEPTS.map((d) => `<option ${d === ob.department ? "selected" : ""}>${esc(d)}</option>`).join("")}</select></div>
   <div class="field"><label>Deadline</label><input type="date" id="e-due" value="${ob.due || ""}"></div>
   ${dl.basis ? `<div class="basis"><b>How the date was computed:</b> ${esc(dl.basis)}</div>` : `<div class="warn">${ob.ref_case ? `This order refers to <b>${esc(ob.ref_case)}</b>; its directions are fetched from that judgment for review.` : "No time limit stated by the court. Anupalan applies a 30-day internal target."}</div>`}
   ${(dl.assumptions || []).map((a) => `<div class="warn">Assumption: ${esc(a)}</div>`).join("")}
   <div class="small" style="margin-top:8px">Extraction: ${esc(ob.source)} · confidence ${Math.round((ob.confidence || 0) * 100)}%</div>
   <div class="btns"><button class="btn ok" onclick="act(${ob.id},'confirm',${orderId})">Confirm</button><button class="btn sec" onclick="act(${ob.id},'edit',${orderId})">Save edits &amp; confirm</button><button class="btn no" onclick="act(${ob.id},'reject',${orderId})">Reject</button></div>
   <div class="field"><label>Compliance status</label><select id="e-comp" onchange="act(${ob.id},'status',${orderId})">${["open","in_progress","complied","under_appeal","stayed"].map((s) => `<option ${s === ob.compliance_status ? "selected" : ""} value="${s}">${s.replace("_", " ")}</option>`).join("")}</select></div>
   <h3 style="margin-top:16px">Alert schedule</h3><ul class="timeline">${(ob.alerts || []).map((a) => `<li class="${a.on < today ? "past" : ""}"><b>${fmt(a.on)}</b>${esc(a.kind)}</li>`).join("")}</ul>
   <h3 style="margin-top:16px">Alert preview (to the nodal officer)</h3><div class="card small">Anupalan: Court-ordered task <b>${esc(o.case_no)}</b> (${esc(ob.department)}) is due on <b>${fmt(ob.due)}</b>: ${esc(ob.action_summary || "")}. Order dated ${fmt(o.decision_date)}. Mark compliance or record an appeal/stay to avoid contempt.</div>
  </div>`;
  $("#drawer").classList.remove("hidden");
  const m = document.getElementById("m" + ob.id); if (m) m.scrollIntoView({ block: "center" });
}
function closeDrawer() { $("#drawer").classList.add("hidden"); }
async function act(id, action, orderId) {
  const body = { action };
  if (action === "edit") Object.assign(body, { due: $("#e-due").value || null, department: $("#e-dept").value, obligor: $("#e-obligor").value, action_summary: $("#e-action").value });
  if (action === "status") Object.assign(body, { action: "status", compliance_status: $("#e-comp").value });
  await post(`/obligations/${id}/review`, body);
  toast({ confirm: "Confirmed and assigned", edit: "Saved and confirmed", reject: "Rejected (kept in audit trail)", status: "Compliance status updated" }[action]);
  await openOb(orderId, id); refreshBadge(); render(false);
}

// ---------- router ----------
let current = ["dashboard"];
async function go(view, ...args) { current = [view, ...args]; location.hash = view; await render(); }
async function render(scroll = true) {
  const [view, ...args] = current;
  document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("active", a.dataset.view === view));
  $("#main").innerHTML = await views[view](...args);
  if (scroll) window.scrollTo(0, 0);
  if (view === "upload" && S.live) bindUpload();
}
function bindUpload() {
  const drop = $("#drop"), file = $("#file");
  const send = async (f) => {
    $("#up-result").innerHTML = `<p class="small">Reading ${esc(f.name)}… (OCR + AI extraction can take ~10 s)</p>`;
    const fd = new FormData(); fd.append("file", f);
    const r = await fetch("/api/upload", { method: "POST", body: fd }); const o = await r.json();
    $("#up-result").innerHTML = `<h2>${o.obligations.length} obligation(s) found in ${esc(o.case_no || f.name)}</h2><div class="card"><table>${o.obligations.map((x) => `<tr class="click" onclick="openOb(${o.id}, ${x.id})"><td>${badge(x.status)}</td><td>${esc(x.action_summary || x.text.slice(0, 140))}</td><td>${fmt(x.due)}</td></tr>`).join("") || "<tr><td>No direction to government found in this order.</td></tr>"}</table></div>`;
    refreshBadge();
  };
  file.onchange = () => file.files[0] && send(file.files[0]);
  drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("on"); };
  drop.ondragleave = () => drop.classList.remove("on");
  drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("on"); e.dataTransfer.files[0] && send(e.dataTransfer.files[0]); };
}
async function refreshBadge() { const obs = await get("/obligations"); $("#nav-pending").textContent = obs.filter((o) => o.review_status === "pending").length || ""; }
document.querySelectorAll("nav a").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); go(a.dataset.view); }));
window.addEventListener("hashchange", () => { const v = location.hash.slice(1); closeDrawer(); if (views[v] && v !== current[0]) { current = [v]; render(); } });
$("#drawer").addEventListener("click", (e) => { if (e.target.id === "drawer") closeDrawer(); });
(async () => {
  try { S.meta = await (await fetch("/api/meta")).json(); S.live = true; } catch { S.live = false; S.meta = await (await fetch("demo/dashboard.json")).json(); }
  $("#mode").innerHTML = S.live ? "Live mode · connected to Anupalan API" : "Public demo (read-only). Reviews are saved only in this browser.<br>Data: Punjab &amp; Haryana High Court orders, open dataset (CC-BY-4.0).";
  const v = (location.hash || "#dashboard").slice(1); current = [views[v] ? v : "dashboard"]; await render(); refreshBadge();
})();
