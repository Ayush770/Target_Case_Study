let claimData;
let activeView = "overview";
const content = document.getElementById("content");

const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#039;", '"': "&quot;",
}[char]));

function sourceLink(file, locator) {
  return `<a href="/evidence/${encodeURIComponent(file)}" target="_blank" rel="noreferrer">${escapeHtml(file)}</a><span class="anchor">${escapeHtml(locator)}</span>`;
}

function findingCard(finding) {
  return `<div class="finding ${finding.severity}"><h3>${escapeHtml(finding.title)}</h3><p>${escapeHtml(finding.detail)}</p><strong>Next action:</strong> <span>${escapeHtml(finding.action)}</span></div>`;
}

function renderOverview() {
  const c = claimData.claim;
  return `<div class="grid metrics">
    <div class="metric"><span>Shipper demand</span><strong>${c.demand}</strong><small>Initial demand; not an adjudicated amount</small></div>
    <div class="metric"><span>Carrier offer</span><strong class="positive">${c.offer}</strong><small>Current negotiation position</small></div>
    <div class="metric"><span>Supported direct cargo</span><strong>${c.direct_cargo}</strong><small>Before packaging / mitigation review</small></div>
    <div class="metric"><span>Direct cargo gap</span><strong class="warning">${c.gap_to_direct_cargo}</strong><small>Five disputed unsellable units</small></div>
  </div><div class="grid two-col" style="margin-top: 16px">
    <article class="card"><div class="section-header"><div><h3>Evidence findings</h3><p class="muted">Open issues are shown, not hidden by a summary.</p></div></div>${claimData.findings.map(findingCard).join("")}</article>
    <article class="card"><div class="section-header"><div><h3>Claim timeline</h3><p class="muted">Operational, delivery, and negotiation events.</p></div></div><div class="timeline">${claimData.timeline.map(event => `<div class="timeline-item"><span class="timeline-date">${event.date}</span><strong>${escapeHtml(event.event)}</strong><p>${escapeHtml(event.detail)}</p></div>`).join("")}</div></article>
  </div>`;
}

function renderEvidence() {
  return `<div class="section-header"><div><p class="eyebrow">Evidence ledger</p><h2>Facts retain their sources</h2><p class="muted">A fact has a value, status, and one or more auditable evidence anchors.</p></div></div>
  <article class="card"><table><thead><tr><th>Fact</th><th>Value</th><th>Status</th><th>Evidence anchor</th></tr></thead><tbody>${claimData.facts.map(fact => `<tr><td><strong>${escapeHtml(fact.label)}</strong><span class="anchor">${escapeHtml(fact.id)}</span></td><td>${escapeHtml(fact.value)}</td><td><span class="fact-status">${escapeHtml(fact.status)}</span></td><td>${fact.anchors.map(a => sourceLink(a.file, a.locator)).join("<br>")}</td></tr>`).join("")}</tbody></table></article>
  <div class="grid two-col" style="margin-top: 16px"><article class="card"><h3>Why signed POD leads on receipt</h3><p class="muted">The EDI event is retained as carrier operational evidence. The signed POD is a consignee receiving record, so it is preferred for what arrived—not treated as universally superior evidence.</p></article><article class="card"><h3>Scanned inspection handling</h3><p class="muted">The inspection fact is a reviewed OCR extraction. A production worker would retain OCR confidence and route low-confidence amounts, quantities, and identifiers to human review.</p></article></div>`;
}

function renderPosition() {
  const order = ["direct_cargo", "cargo_cap", "inspection", "repack", "delay_markdown", "freight_refund"];
  const labels = {direct_cargo: "Direct cargo position", cargo_cap: "Cargo liability cap", inspection: "Inspection expense", repack: "Repack labor", delay_markdown: "Promotion markdown", freight_refund: "Freight refund"};
  return `<div class="section-header"><div><p class="eyebrow">Versioned policy output</p><h2>Contract position</h2><p class="muted">Rules produce the position. The model may explain it, but cannot change it.</p></div></div><article class="card">${order.map(key => { const item = claimData.position[key]; return `<div class="position-row"><div class="position-top"><strong>${labels[key]}</strong><strong>${item.amount}</strong></div><p>${escapeHtml(item.status)}</p>${item.formula ? `<div class="formula">${escapeHtml(item.formula)}</div>` : ""}${item.clause ? `<span class="tag">${escapeHtml(item.clause)}</span>` : ""}</div>`; }).join("")}</article>`;
}

function renderHistory() {
  return `<div class="section-header"><div><p class="eyebrow">Retrieval, not prediction</p><h2>Similar historical claims</h2><p class="muted">Filtered to BlueLine + Standard LTL, then ranked with an explainable feature score.</p></div></div><article class="card"><table><thead><tr><th>Claim</th><th>Similarity</th><th>Outcome</th><th>Why it matches</th><th>Context</th></tr></thead><tbody>${claimData.comparators.map(item => `<tr><td><strong>${item.claim_id}</strong><span class="anchor">${item.issue_type}</span></td><td><span class="score">${Math.round(item.score * 100)}%</span></td><td><strong>${item.settled}</strong><span class="anchor">${item.settlement_pct} of ${item.claimed}</span></td><td>${item.reasons.map(reason => `<span class="tag">${escapeHtml(reason)}</span>`).join("")}</td><td>${escapeHtml(item.summary)}<span class="anchor">${escapeHtml(item.notes)}</span></td></tr>`).join("")}</tbody></table></article><div class="notice">Historical settlement percentages are negotiation context only. This data set has 30 cases and must not be presented as a predictive settlement model or contractual entitlement.</div>`;
}

async function renderDraft() {
  content.innerHTML = `<div class="loading">Generating a source-linked, approval-required draft…</div>`;
  const response = await fetch("/api/draft", {method: "POST"});
  const draft = await response.json();
  content.innerHTML = `<div class="section-header"><div><p class="eyebrow">Human approval gate</p><h2>Negotiation draft</h2><p class="muted">Generated only from vetted facts and contract outputs. It cannot send automatically.</p></div><button class="button" id="regenerate">Regenerate draft</button></div><article class="card"><p class="eyebrow">${escapeHtml(draft.subject)}</p><div class="draft-body">${escapeHtml(draft.body)}</div><div class="validation">✓ Citation coverage: ${draft.validation.citation_coverage} &nbsp; · &nbsp; ✓ Numeric consistency: ${draft.validation.numeric_consistency} &nbsp; · &nbsp; Approval required: ${draft.validation.approval_required ? "yes" : "no"}</div></article><article class="card" style="margin-top:16px"><h3>Grounding references</h3>${draft.citations.map(citation => `<p><strong>${escapeHtml(citation.claim)}</strong><span class="anchor">${citation.fact_ids ? citation.fact_ids.join(", ") : citation.rule}</span></p>`).join("")}</article>`;
  document.getElementById("regenerate").addEventListener("click", renderDraft);
}

function render(view) {
  activeView = view;
  document.querySelectorAll(".tab").forEach(tab => tab.classList.toggle("active", tab.dataset.view === view));
  if (view === "overview") content.innerHTML = renderOverview();
  if (view === "evidence") content.innerHTML = renderEvidence();
  if (view === "position") content.innerHTML = renderPosition();
  if (view === "history") content.innerHTML = renderHistory();
  if (view === "draft") renderDraft();
}

async function init() {
  content.innerHTML = document.getElementById("empty").innerHTML;
  const response = await fetch("/api/claim");
  claimData = await response.json();
  document.getElementById("claim-title").textContent = claimData.claim.id;
  document.getElementById("claim-meta").textContent = `${claimData.claim.carrier} · Owner: ${claimData.claim.owner}`;
  document.getElementById("claim-status").textContent = claimData.claim.status;
  document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => render(tab.dataset.view)));
  render(activeView);
}

init().catch(error => { content.innerHTML = `<div class="notice">Could not load the claim workspace: ${escapeHtml(error.message)}</div>`; });
