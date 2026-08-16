/* ── State ───────────────────────────────────────────────── */
let claimData = null;
let activeView = "overview";
const content = document.getElementById("content");

/* ── Page titles per view ────────────────────────────────── */
const PAGE_META = {
  upload:   { title: "Upload Documents",      sub: "Upload claim evidence to S3 and trigger analysis" },
  overview: { title: "Overview",              sub: "Claim metrics, open findings, and operational timeline" },
  evidence: { title: "Evidence & Findings",   sub: "Source-linked fact ledger with evidence anchors" },
  position: { title: "Contract Position",     sub: "Deterministic contract rule outputs" },
  history:  { title: "Similar Claims",        sub: "Ranked historical comparators with match reasoning" },
  draft:    { title: "Negotiation Draft",     sub: "Approval-required draft with citation grounding" },
};

/* ── Utilities ───────────────────────────────────────────── */
const esc = (v) => String(v ?? "").replace(/[&<>'"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#039;",'"':"&quot;"}[c]));

function scoreClass(score) {
  const s = parseFloat(score);
  if (s >= 0.6) return "score-high";
  if (s >= 0.4) return "score-medium";
  return "score-low";
}

function sourceLink(file, locator) {
  return `<a class="anchor-link" href="/evidence/${encodeURIComponent(file)}" target="_blank" rel="noreferrer">${esc(file)}</a><span class="anchor-loc">${esc(locator)}</span>`;
}

function findingCard(f) {
  return `
    <div class="finding ${esc(f.severity)}">
      <div class="finding-header">
        <h3>${esc(f.title)}</h3>
        <span class="severity-badge ${esc(f.severity)}">${esc(f.severity)}</span>
      </div>
      <p>${esc(f.detail)}</p>
      ${f.action ? `<div class="finding-action"><strong>Next action:</strong> ${esc(f.action)}</div>` : ""}
    </div>`;
}

/* ── Upload view ─────────────────────────────────────────── */
const DEFAULT_CLAIM_ID = claimData?.claim?.id || "FCL-2026-0147";

function renderUpload() {
  return `
    <div class="info-callout">
      Upload claim documents to AWS S3. After uploading, run <strong>Analyze</strong> to process evidence
      through the full pipeline. AWS credentials must be configured for upload to succeed.
    </div>
    <div class="upload-grid">
      <div>
        <div class="upload-zone" id="upload-zone">
          <div class="upload-zone-icon">📄</div>
          <h3>Drop files here</h3>
          <p>PDF, JSON, CSV, PNG, JPG — any claim supporting document</p>
          <label class="btn btn-ghost" style="cursor:pointer">
            Choose files
            <input type="file" class="upload-input" id="file-input" multiple accept=".pdf,.json,.csv,.png,.jpg,.jpeg,.eml,.xlsx" />
          </label>
        </div>
        <div style="margin-top:12px">
          <label style="font-size:12px;font-weight:600;color:var(--muted-2);display:block;margin-bottom:4px">Claim ID</label>
          <input id="upload-claim-id" type="text" value="${esc(claimData?.claim?.id || "FCL-2026-0147")}"
            style="width:100%;padding:8px 12px;border:1px solid var(--line);border-radius:var(--radius-sm);font:inherit;font-size:13px;color:var(--ink)" />
        </div>
        <button class="analyze-btn" id="analyze-btn" disabled>
          Run Claim Analysis
        </button>
        <div id="analyze-output"></div>
      </div>
      <div>
        <div style="font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:10px">Upload queue</div>
        <div id="upload-list" class="upload-list">
          <div style="font-size:13px;color:var(--muted-2);padding:12px 0">No files selected yet.</div>
        </div>
      </div>
    </div>`;
}

function bindUploadHandlers() {
  const zone      = document.getElementById("upload-zone");
  const input     = document.getElementById("file-input");
  const list      = document.getElementById("upload-list");
  const analyzeBtn= document.getElementById("analyze-btn");
  const output    = document.getElementById("analyze-output");

  if (!zone || !input) return;

  let uploadedKeys = [];

  function claimId() {
    return (document.getElementById("upload-claim-id")?.value || "FCL-2026-0147").trim();
  }

  function renderList(files) {
    if (!files.length) { list.innerHTML = `<div style="font-size:13px;color:var(--muted-2);padding:12px 0">No files selected yet.</div>`; return; }
    list.innerHTML = [...files].map(f => `
      <div class="upload-item" id="item-${esc(f.name)}">
        <span class="upload-item-icon">📎</span>
        <span class="upload-item-name" title="${esc(f.name)}">${esc(f.name)}</span>
        <span class="upload-item-status uploading" id="status-${esc(f.name)}">Pending</span>
      </div>`).join("");
  }

  async function uploadFiles(files) {
    uploadedKeys = [];
    analyzeBtn.disabled = true;
    for (const file of files) {
      const statusEl = document.getElementById(`status-${file.name}`);
      if (statusEl) { statusEl.textContent = "Uploading…"; statusEl.className = "upload-item-status uploading"; }
      try {
        const form = new FormData();
        form.append("file", file);
        const res  = await fetch(`/claims/${encodeURIComponent(claimId())}/documents`, { method: "POST", body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || res.statusText);
        uploadedKeys.push(data.s3_key);
        if (statusEl) { statusEl.textContent = "Uploaded ✓"; statusEl.className = "upload-item-status success"; }
      } catch (err) {
        if (statusEl) { statusEl.textContent = "Failed"; statusEl.className = "upload-item-status error"; }
        // Show the real error from the API in the console and in the UI
        console.warn("Upload error:", err.message);
        output.innerHTML = `<div class="analyze-error"><strong>Upload failed:</strong> ${esc(err.message)}</div>`;
      }
    }
    analyzeBtn.disabled = false;
  }

  function handleFiles(files) {
    if (!files.length) return;
    renderList(files);
    uploadFiles(files);
  }

  input.addEventListener("change", () => handleFiles(input.files));

  zone.addEventListener("dragover",  (e) => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", ()  => zone.classList.remove("drag-over"));
  zone.addEventListener("drop",      (e) => { e.preventDefault(); zone.classList.remove("drag-over"); handleFiles(e.dataTransfer.files); });

  analyzeBtn.addEventListener("click", async () => {
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing…";
    output.innerHTML = "";
    try {
      const cid  = claimId();
      const res  = await fetch(`/claims/${encodeURIComponent(cid)}/analyze`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      const factCount = data?.evidence?.facts?.length ?? 0;
      output.innerHTML = `<div class="analyze-result">
        ✓ Analysis complete — ${factCount} evidence facts extracted,
        ${data?.contract_position?.length ?? 0} contract positions evaluated,
        ${data?.historical_comparables?.length ?? 0} historical comparables found.
        <br><br>Loading results…
      </div>`;

      // Reload claim workspace from the pipeline result for this claim_id
      const claimRes  = await fetch(`/api/claim/${encodeURIComponent(cid)}`);
      const claimJson = await claimRes.json();
      if (claimRes.ok) {
        claimData = claimJson;
        const titleEl  = document.getElementById("claim-title");
        const metaEl   = document.getElementById("claim-meta");
        const statusEl = document.getElementById("claim-status");
        if (titleEl)  titleEl.textContent  = claimData.claim?.id     || cid;
        if (metaEl)   metaEl.textContent   = `${claimData.claim?.carrier || ""} · ${claimData.claim?.owner || ""}`;
        if (statusEl) statusEl.textContent = claimData.claim?.status || "ANALYZED";
        render("overview");
      }
    } catch (err) {
      output.innerHTML = `<div class="analyze-error">Analysis failed: ${esc(err.message)}</div>`;
    }
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Run Claim Analysis";
  });
}

/* ── Overview view ───────────────────────────────────────── */
function renderOverview() {
  const c = claimData.claim;
  const findings  = (claimData.findings  || []).map(findingCard).join("");
  const timeline  = (claimData.timeline  || []).map(e => `
    <div class="timeline-item">
      <div class="timeline-dot"></div>
      <div class="timeline-date">${esc(e.date)}</div>
      <div class="timeline-event">${esc(e.event)}</div>
      <div class="timeline-detail">${esc(e.detail)}</div>
    </div>`).join("");

  return `
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-label">Shipper demand</div>
        <div class="metric-value neutral">${esc(c.demand)}</div>
        <div class="metric-hint">Initial demand; not adjudicated</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Carrier offer</div>
        <div class="metric-value positive">${esc(c.offer)}</div>
        <div class="metric-hint">Current negotiation position</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Supported direct cargo</div>
        <div class="metric-value neutral">${esc(c.direct_cargo)}</div>
        <div class="metric-hint">Before packaging / mitigation review</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Direct cargo gap</div>
        <div class="metric-value warning">${esc(c.gap_to_direct_cargo)}</div>
        <div class="metric-hint">Carrier offer vs. supported cargo</div>
      </div>
    </div>
    <div class="two-col">
      <div class="card">
        <div class="section-header">
          <div class="eyebrow">Open issues</div>
          <h2>Evidence findings</h2>
          <p>Issues are surfaced, not hidden by a summary.</p>
        </div>
        ${findings || `<p style="color:var(--muted);font-size:13px">No findings.</p>`}
      </div>
      <div class="card">
        <div class="section-header">
          <div class="eyebrow">Operational events</div>
          <h2>Claim timeline</h2>
          <p>Delivery and negotiation chronology.</p>
        </div>
        <div class="timeline">${timeline || `<p style="color:var(--muted);font-size:13px">No timeline events.</p>`}</div>
      </div>
    </div>`;
}

/* ── Evidence view ───────────────────────────────────────── */
function renderEvidence() {
  const rows = (claimData.facts || []).map(f => `
    <tr>
      <td><strong>${esc(f.label)}</strong><div class="fact-id">${esc(f.id)}</div></td>
      <td>${esc(f.value)}</td>
      <td><span class="fact-status ${esc(f.status)}">${esc(f.status)}</span></td>
      <td>${(f.anchors || []).map(a => sourceLink(a.file, a.locator)).join("")}</td>
    </tr>`).join("");

  return `
    <div class="section-header">
      <div class="eyebrow">Evidence ledger</div>
      <h2>Facts retain their sources</h2>
      <p>Every fact carries a value, status, and one or more auditable evidence anchors.</p>
    </div>
    <div class="card table-wrap">
      <table>
        <thead><tr><th>Fact</th><th>Value</th><th>Status</th><th>Evidence anchor</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="4" style="color:var(--muted);text-align:center;padding:24px">No facts extracted.</td></tr>`}</tbody>
      </table>
    </div>
    <div class="two-col" style="margin-top:16px">
      <div class="card">
        <h3 style="margin-bottom:8px">Why signed POD leads on receipt</h3>
        <p style="font-size:13px;color:var(--muted)">The EDI event is retained as carrier operational evidence. The signed POD is the consignee receiving record and is preferred for what arrived — not treated as universally superior.</p>
      </div>
      <div class="card">
        <h3 style="margin-bottom:8px">Scanned inspection handling</h3>
        <p style="font-size:13px;color:var(--muted)">The inspection fact is a reviewed OCR extraction via AWS Textract. In production, low-confidence consequential fields are routed to human review.</p>
      </div>
    </div>`;
}

/* ── Contract position view ──────────────────────────────── */
function renderPosition() {
  const ORDER  = ["direct_cargo","cargo_cap","inspection","repack","delay_markdown","freight_refund"];
  const LABELS = {
    direct_cargo:   "Direct cargo position",
    cargo_cap:      "Cargo liability cap",
    inspection:     "Inspection expense",
    repack:         "Repack labor",
    delay_markdown: "Promotion markdown",
    freight_refund: "Freight refund",
  };
  const pos = claimData.position || {};
  const rows = ORDER.map(key => {
    const item = pos[key] || {};
    return `
      <div class="position-row">
        <div class="position-top">
          <span class="position-name">${LABELS[key]}</span>
          <span class="position-amount">${esc(item.amount ?? "—")}</span>
        </div>
        <div class="position-status">${esc(item.status ?? "")}</div>
        ${item.formula   ? `<div class="position-formula">${esc(item.formula)}</div>` : ""}
        ${item.rationale ? `<div class="position-status" style="font-size:12px">${esc(item.rationale)}</div>` : ""}
        ${item.clause    ? `<span class="clause-tag">${esc(item.clause)}</span>` : ""}
      </div>`;
  }).join("");

  return `
    <div class="section-header">
      <div class="eyebrow">Versioned policy output</div>
      <h2>Contract position</h2>
      <p>Rules produce the position. The model may explain it, but cannot change it.</p>
    </div>
    <div class="card">${rows}</div>`;
}

/* ── Historical comparators view ─────────────────────────── */
function renderHistory() {
  const rows = (claimData.comparators || []).map(item => {
    const pct = parseFloat(item.score ?? 0);
    const cls = scoreClass(pct);
    const reasons = (item.reasons || []).map(r => `<span class="reason-tag">${esc(r)}</span>`).join("");
    return `
      <tr>
        <td><strong>${esc(item.claim_id)}</strong><div class="fact-id">${esc(item.issue_type)}</div></td>
        <td><span class="score-pill ${cls}">${Math.round(pct * 100)}%</span></td>
        <td><strong>${esc(item.settled)}</strong><div class="fact-id">${esc(item.settlement_pct)} of ${esc(item.claimed)}</div></td>
        <td>${reasons}</td>
        <td>${esc(item.summary)}<div class="fact-id">${esc(item.notes)}</div></td>
      </tr>`;
  }).join("");

  return `
    <div class="section-header">
      <div class="eyebrow">Retrieval, not prediction</div>
      <h2>Similar historical claims</h2>
      <p>Filtered to same carrier + service level, then ranked with an explainable feature score.</p>
    </div>
    <div class="card table-wrap">
      <table>
        <thead><tr><th>Claim</th><th>Similarity</th><th>Outcome</th><th>Why it matches</th><th>Context</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:24px">No comparables found.</td></tr>`}</tbody>
      </table>
    </div>
    <div class="notice">Historical settlement percentages are negotiation context only. This dataset has 30 cases and must not be treated as a predictive settlement model or contractual entitlement.</div>`;
}

/* ── Draft view ──────────────────────────────────────────── */
async function renderDraft() {
  content.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Generating source-linked draft…</p></div>`;
  try {
    const res   = await fetch("/api/draft", { method: "POST" });
    const draft = await res.json();
    if (!res.ok) throw new Error(draft.detail || res.statusText);

    const citations = (draft.citations || []).map(c => `
      <div class="citation-item">
        <span class="citation-claim">${esc(c.claim)}</span>
        <span class="citation-ref">${c.fact_ids ? c.fact_ids.join(", ") : (c.rule || "")}</span>
      </div>`).join("");

    content.innerHTML = `
      <div class="section-header-row">
        <div class="section-header" style="margin-bottom:0">
          <div class="eyebrow">Human approval gate</div>
          <h2>Negotiation draft</h2>
          <p>Generated from vetted facts and contract outputs only. Cannot be sent automatically.</p>
        </div>
        <button class="btn btn-ghost" id="regenerate">↻ Regenerate</button>
      </div>
      <div class="card">
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;font-weight:700;color:var(--muted);margin-bottom:10px">${esc(draft.subject)}</div>
        <div class="draft-body">${esc(draft.body)}</div>
        <div class="validation-bar">
          <span>✓ Citation coverage: ${esc(draft.validation?.citation_coverage)}</span>
          <span>✓ Numeric consistency: ${esc(draft.validation?.numeric_consistency)}</span>
        </div>
      </div>
      <div class="card" style="margin-top:16px">
        <h3 style="margin-bottom:14px">Grounding references</h3>
        ${citations || `<p style="font-size:13px;color:var(--muted)">No citations.</p>`}
      </div>
      <div class="approval-gate">
        ⚠ Approval required — a specialist must review before any communication is sent.
      </div>`;

    document.getElementById("regenerate")?.addEventListener("click", renderDraft);
  } catch (err) {
    content.innerHTML = `<div class="notice">Draft generation failed: ${esc(err.message)}</div>`;
  }
}

/* ── Render dispatcher ───────────────────────────────────── */
function render(view) {
  activeView = view;

  // Update sidebar active state
  document.querySelectorAll(".nav-item").forEach(el => el.classList.toggle("active", el.dataset.view === view));

  // Update topbar
  const meta = PAGE_META[view] || {};
  const titleEl = document.getElementById("page-title");
  const subEl   = document.getElementById("page-sub");
  if (titleEl) titleEl.textContent = meta.title || "";
  if (subEl)   subEl.textContent   = meta.sub   || "";

  if (view === "upload")   { content.innerHTML = renderUpload();   bindUploadHandlers(); return; }
  if (view === "overview") { content.innerHTML = renderOverview(); return; }
  if (view === "evidence") { content.innerHTML = renderEvidence(); return; }
  if (view === "position") { content.innerHTML = renderPosition(); return; }
  if (view === "history")  { content.innerHTML = renderHistory();  return; }
  if (view === "draft")    { renderDraft();                        return; }
}

/* ── Health check ────────────────────────────────────────── */
async function checkHealth() {
  try {
    const res = await fetch("/health");
    const dot = document.getElementById("health-dot");
    if (dot) dot.style.background = res.ok ? "var(--green)" : "var(--red)";
  } catch {
    const dot = document.getElementById("health-dot");
    if (dot) dot.style.background = "var(--red)";
  }
}

/* ── Init ────────────────────────────────────────────────── */
async function init() {
  checkHealth();

  try {
    const res = await fetch("/api/claim");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    claimData = await res.json();

    const titleEl  = document.getElementById("claim-title");
    const metaEl   = document.getElementById("claim-meta");
    const statusEl = document.getElementById("claim-status");
    if (titleEl)  titleEl.textContent  = claimData.claim?.id     || "";
    if (metaEl)   metaEl.textContent   = `${claimData.claim?.carrier || ""} · ${claimData.claim?.owner || ""}`;
    if (statusEl) statusEl.textContent = claimData.claim?.status || "";

    document.querySelectorAll(".nav-item").forEach(el =>
      el.addEventListener("click", () => render(el.dataset.view))
    );

    render("overview");
  } catch (err) {
    content.innerHTML = `<div class="notice">Could not load claim workspace: ${esc(err.message)}</div>`;
  }
}

init();
