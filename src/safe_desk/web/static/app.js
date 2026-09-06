const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

const I18N = {
  en: {
    paper_banner: "PAPER / SIMULATED — not live Binance profit or loss. Dry-run stays on. No API secrets.",
    tagline: "A simple desk for a normal exchange user. No terminal required.",
    nav_dash: "Dashboard",
    nav_analyze: "Analyze",
    nav_ticket: "Ticket",
    nav_paper: "Paper",
    nav_alerts: "Alerts",
    dash_title: "Desk status",
    analyze_title: "What is the setup?",
    ticket_title: "Ticket + human OK",
    paper_title: "Paper journal",
    alerts_title: "Alerts you should see now",
    use_sample: "Use sample BTC CSV",
    run_analyze: "Explain this setup",
    create_ticket: "Create ticket (still not an order)",
    approve: "Approve dry-run (PAPER)",
    cancel: "Cancel ticket",
    close_tp: "Close paper at take-profit",
    close_sl: "Close paper at stop",
    try_withdraw: "Try withdraw (must refuse)",
    must_type: "Type exactly OK plus the ticket id. A bare “ok” is rejected.",
    disclaimer: "Not financial advice. Crypto can go to zero. Official MCP only: https://agent.binance.com/mcp/agentic. Binance does not endorse this project.",
  },
  ru: {
    paper_banner: "PAPER / SIMULATED — не живой PnL Binance. Dry-run включён. Секретов нет.",
    tagline: "Простой стол для обычного пользователя биржи. Терминал не нужен.",
    nav_dash: "Статус",
    nav_analyze: "Разбор",
    nav_ticket: "Тикет",
    nav_paper: "Бумага",
    nav_alerts: "Сигналы",
    dash_title: "Статус стола",
    analyze_title: "Что за сетап?",
    ticket_title: "Тикет + OK человека",
    paper_title: "Бумажный журнал",
    alerts_title: "Какие сигналы видны сейчас",
    use_sample: "Взять пример BTC CSV",
    run_analyze: "Объяснить сетап",
    create_ticket: "Создать тикет (ещё не заявка)",
    approve: "Подтвердить dry-run (PAPER)",
    cancel: "Отменить тикет",
    close_tp: "Закрыть бумагу по тейку",
    close_sl: "Закрыть бумагу по стопу",
    try_withdraw: "Попробовать вывод (должен отказать)",
    must_type: "Наберите ровно OK и номер тикета. Голое «ok» не принимается.",
    disclaimer: "Не инвестсовет. Крипта может обнулиться. Только официальный MCP: https://agent.binance.com/mcp/agentic. Binance проект не поддерживает.",
  },
};

let lang = localStorage.getItem("safe-desk-lang") || "en";
let lastAnalyze = null;
let lastTicket = null;

function t(key) {
  return (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key;
}

function applyLang() {
  $$("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  $$(".lang-toggle button").forEach((b) => b.classList.toggle("on", b.dataset.lang === lang));
  document.documentElement.lang = lang;
}

function showPanel(name) {
  $$("nav button").forEach((b) => b.classList.toggle("on", b.dataset.panel === name));
  $$("section.panel").forEach((p) => p.classList.toggle("on", p.id === `panel-${name}`));
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok && data.detail) {
    throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  }
  return { res, data };
}

function money(n) {
  if (n == null || Number.isNaN(n)) return "—";
  const x = Number(n);
  return Math.abs(x) >= 1 ? x.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(x);
}

function qty(n) {
  if (n == null) return "—";
  return Number(n).toFixed(8).replace(/0+$/, "").replace(/\.$/, "");
}

function badge(text, cls) {
  return `<span class="badge ${cls}">${text}</span>`;
}

function setErr(el, msg) {
  el.innerHTML = msg ? `<p class="err">${msg}</p>` : "";
}

async function loadStatus() {
  const { data } = await api("/api/status");
  const proof = data.last_proof;
  const policy = data.last_policy;
  $("#dash-grid").innerHTML = `
    <div class="stat"><span class="k">Mode</span><span class="v">DRY-RUN</span></div>
    <div class="stat"><span class="k">MCP</span><span class="v mcp">${data.mcp_url}</span></div>
    <div class="stat"><span class="k">Emergency stop</span><span class="v">${data.emergency_stop ? "ON" : "off"}</span></div>
    <div class="stat"><span class="k">Proof</span><span class="v">${proof ? proof.verdict : "—"}</span></div>
    <div class="stat"><span class="k">Policy</span><span class="v">${policy ? (policy.ok ? "PASS" : "FAIL") : "—"}</span></div>
    <div class="stat"><span class="k">PAPER PnL</span><span class="v">${money(data.paper.running_pnl)}</span></div>
    <div class="stat"><span class="k">Open paper</span><span class="v">${data.paper.open_count}</span></div>
    <div class="stat"><span class="k">Alerts</span><span class="v">${data.alert_count}</span></div>
  `;
  $("#dash-notes").innerHTML = `
    <p class="hint">Live trading: <strong>off</strong>. Secrets stored: <strong>none</strong>. Policy file: ${data.policy_source || "hard rules"}.</p>
    ${data.last_why ? `<div class="why"><h3>${data.last_why.headline}</h3><ul>${data.last_why.sentences.map((s) => `<li>${s}</li>`).join("")}</ul></div>` : ""}
  `;
}

function renderWhy(why, target) {
  if (!why) {
    target.innerHTML = "";
    return;
  }
  const cls = why.action === "ENTER" ? "enter" : why.action === "SKIP" ? "skip" : "wait";
  target.innerHTML = `
    <p>${badge(why.action, cls)} ${why.risk_score != null ? `Risk ${why.risk_score}/100` : ""} ${why.signal ? `· ${why.signal} (setup only)` : ""}</p>
    <h3>${why.headline}</h3>
    <ul class="why">${why.sentences.map((s) => `<li>${s}</li>`).join("")}</ul>
  `;
}

async function runAnalyze(useSample) {
  const out = $("#analyze-out");
  setErr(out, "");
  const body = {
    symbol: $("#f-symbol").value || "BTCUSDT",
    side: $("#f-side").value,
    use_sample: !!useSample && !$("#f-csv").value,
    csv_text: $("#f-csv").value || null,
    stop: numOrNull($("#f-stop").value),
    equity: numOrNull($("#f-equity").value),
    risk_pct: numOrNull($("#f-risk").value) || 1,
    price_json: $("#f-price").value || null,
    balance_json: $("#f-balance").value || null,
    lang,
  };
  try {
    const { data } = await api("/api/analyze", { method: "POST", body: JSON.stringify(body) });
    lastAnalyze = data;
    const s = data.setup;
    out.innerHTML = `
      <div class="grid">
        <div class="stat"><span class="k">Last</span><span class="v">${money(data.last)}</span></div>
        <div class="stat"><span class="k">Trend</span><span class="v">${s.trend}</span></div>
        <div class="stat"><span class="k">Swings</span><span class="v">${s.vol_regime}</span></div>
        <div class="stat"><span class="k">Risk</span><span class="v">${s.risk_score} / 100</span></div>
        <div class="stat"><span class="k">Signal</span><span class="v">${s.signal}</span></div>
        <div class="stat"><span class="k">Proof</span><span class="v">${data.proof ? data.proof.verdict : "—"}</span></div>
      </div>
      <div id="analyze-why"></div>
      ${data.size ? `<p class="hint">1% size: <strong>${qty(data.size.quantity)}</strong> · worth ${money(data.size.notional)} · risk ${money(data.size.risk_quote)}</p>` : ""}
      <p class="hint">${data.offline ? "Offline path (sample / CSV). No MCP login used." : "Numbers from pasted MCP-shaped JSON. This app did not call Binance."}</p>
    `;
    renderWhy(data.why, $("#analyze-why"));
    if (data.last && !$("#t-entry").value) $("#t-entry").value = data.last;
    if (data.size && !$("#t-stop").value) $("#t-stop").value = data.size.stop;
    if (data.size && !$("#t-equity").value) $("#t-equity").value = data.size.equity;
    await loadStatus();
    await loadAlerts();
  } catch (err) {
    setErr(out, err.message);
  }
}

async function createTicket() {
  const out = $("#ticket-out");
  setErr(out, "");
  const body = {
    symbol: $("#t-symbol").value || $("#f-symbol").value || "BTCUSDT",
    side: $("#t-side").value,
    entry: numOrNull($("#t-entry").value),
    stop: numOrNull($("#t-stop").value),
    equity: numOrNull($("#t-equity").value),
    take_profit: numOrNull($("#t-tp").value),
    risk_pct: numOrNull($("#t-risk").value) || 1,
    use_sample: true,
    lang,
  };
  if (!body.stop || !body.equity || !body.entry) {
    setErr(out, "Need entry, stop, and equity (or analyze the sample first).");
    return;
  }
  try {
    const { data } = await api("/api/ticket", { method: "POST", body: JSON.stringify(body) });
    lastTicket = data.ticket;
    const blocked = (data.blocked_reasons || []).length;
    out.innerHTML = `
      <p>${badge(data.ticket.status, blocked ? "skip" : "wait")} ${badge("DRY-RUN", "dry")} ${badge("NOT AN ORDER", "paper")}</p>
      <p class="ticket-id">${data.ticket.id}</p>
      <p class="hint">${data.label}</p>
      <div id="ticket-why"></div>
      <p>Size ${qty(data.ticket.quantity)} · risk ${money(data.ticket.risk_quote)} · ${data.ticket.symbol} ${data.ticket.side}</p>
      ${blocked ? `<ul class="err">${data.blocked_reasons.map((r) => `<li>${r}</li>`).join("")}</ul>` : ""}
    `;
    renderWhy(data.why, $("#ticket-why"));
    $("#ok-phrase").placeholder = data.ok_phrase;
    $("#ok-phrase").dataset.expected = data.ok_phrase;
    syncApproveButton();
    await loadStatus();
    await loadAlerts();
    showPanel("ticket");
  } catch (err) {
    setErr(out, err.message);
  }
}

function syncApproveButton() {
  const expected = $("#ok-phrase").dataset.expected || "";
  const typed = $("#ok-phrase").value.trim();
  $("#btn-approve").disabled = !expected || typed.toUpperCase() !== expected.toUpperCase();
}

async function approveTicket() {
  const out = $("#approve-out");
  setErr(out, "");
  const phrase = $("#ok-phrase").value;
  const ticketId = lastTicket && lastTicket.id;
  const { res, data } = await api("/api/ticket/approve", {
    method: "POST",
    body: JSON.stringify({ phrase, ticket_id: ticketId }),
  });
  if (!res.ok) {
    setErr(out, data.message || "Rejected");
    await loadAlerts();
    return;
  }
  out.innerHTML = `
    <p class="okmsg">${badge("SIMULATED / PAPER", "paper")} Dry-run fill written to the paper journal. Not live PnL.</p>
    <pre class="payload">${JSON.stringify(data.simulated, null, 2)}</pre>
  `;
  await loadJournal();
  await loadStatus();
  showPanel("paper");
}

async function cancelTicket() {
  if (!lastTicket) return;
  await api("/api/ticket/cancel", {
    method: "POST",
    body: JSON.stringify({ ticket_id: lastTicket.id }),
  });
  $("#approve-out").innerHTML = `<p class="hint">Cancelled ${lastTicket.id}</p>`;
  await loadStatus();
}

async function loadJournal() {
  const { data } = await api("/api/journal");
  const rows = (data.events || []).slice().reverse();
  $("#paper-summary").innerHTML = `
    <div class="grid">
      <div class="stat"><span class="k">Label</span><span class="v">PAPER / SIMULATED</span></div>
      <div class="stat"><span class="k">Running PAPER PnL</span><span class="v">${money(data.running_pnl)}</span></div>
      <div class="stat"><span class="k">Open</span><span class="v">${data.open_count}</span></div>
      <div class="stat"><span class="k">Closed</span><span class="v">${data.closed_count}</span></div>
    </div>
    <p class="hint">${data.note}</p>
  `;
  $("#paper-table").innerHTML = rows.length
    ? `<table><thead><tr><th>When</th><th>Kind</th><th>Ticket</th><th>Qty @ price</th><th>PAPER PnL</th></tr></thead><tbody>
      ${rows.map((r) => `<tr>
        <td>${r.ts}</td>
        <td>${r.kind} ${badge(r.label, "paper")}</td>
        <td>${r.ticket_id}<br><span class="hint">${r.symbol} ${r.side}</span></td>
        <td>${qty(r.quantity)} @ ${money(r.price)}</td>
        <td>${r.pnl == null ? "—" : money(r.pnl)}<br><span class="hint">run ${money(r.running_pnl)}</span></td>
      </tr>`).join("")}
    </tbody></table>`
    : `<p class="hint">No paper fills yet. Analyze → ticket → type OK TKT-…</p>`;
  const open = (data.open_positions || [])[0];
  $("#btn-close-tp").disabled = !open;
  $("#btn-close-sl").disabled = !open;
  if (open) {
    $("#btn-close-tp").dataset.ticket = open.ticket_id;
    $("#btn-close-sl").dataset.ticket = open.ticket_id;
  }
}

async function closePaper(reason) {
  const btn = reason === "take_profit" ? $("#btn-close-tp") : $("#btn-close-sl");
  const ticketId = btn.dataset.ticket;
  if (!ticketId) return;
  try {
    await api("/api/journal/close", {
      method: "POST",
      body: JSON.stringify({ ticket_id: ticketId, reason }),
    });
    await loadJournal();
    await loadStatus();
  } catch (err) {
    $("#paper-table").insertAdjacentHTML("afterbegin", `<p class="err">${err.message}</p>`);
  }
}

async function loadAlerts() {
  const { data } = await api("/api/alerts");
  const rows = data.alerts || [];
  $("#alerts-list").innerHTML = rows.length
    ? `<table><thead><tr><th>When</th><th>Kind</th><th>Message</th></tr></thead><tbody>
      ${rows.map((a) => `<tr>
        <td>${a.ts}</td>
        <td>${badge(a.kind, a.severity === "block" ? "skip" : "wait")}</td>
        <td>${a.message}${a.ticket_id ? `<br><span class="hint">${a.ticket_id}</span>` : ""}</td>
      </tr>`).join("")}
    </tbody></table>`
    : `<p class="hint">No alerts yet. Proof REJECT, policy BLOCKED, withdraw attempts, and daily caps show up here.</p>`;
}

async function tryWithdraw() {
  const { data } = await api("/api/withdraw", {
    method: "POST",
    body: JSON.stringify({ note: "withdraw" }),
  });
  $("#alerts-extra").innerHTML = `<p class="err">${data.message}</p>`;
  await loadAlerts();
  await loadStatus();
  showPanel("alerts");
}

function numOrNull(v) {
  if (v == null || String(v).trim() === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function fillDemoDefaults() {
  $("#f-symbol").value = "BTCUSDT";
  $("#f-side").value = "BUY";
  $("#f-stop").value = "100200";
  $("#f-equity").value = "1000";
  $("#f-risk").value = "1";
  $("#t-symbol").value = "BTCUSDT";
  $("#t-side").value = "BUY";
  $("#t-entry").value = "102450";
  $("#t-stop").value = "100200";
  $("#t-equity").value = "1000";
  $("#t-tp").value = "106950";
  $("#t-risk").value = "1";
}

window.addEventListener("DOMContentLoaded", async () => {
  applyLang();
  fillDemoDefaults();
  $$(".lang-toggle button").forEach((b) => {
    b.addEventListener("click", () => {
      lang = b.dataset.lang;
      localStorage.setItem("safe-desk-lang", lang);
      applyLang();
    });
  });
  $$("nav button").forEach((b) => b.addEventListener("click", () => showPanel(b.dataset.panel)));
  $("#btn-sample").addEventListener("click", () => runAnalyze(true));
  $("#btn-analyze").addEventListener("click", () => runAnalyze(false));
  $("#btn-ticket").addEventListener("click", createTicket);
  $("#btn-approve").addEventListener("click", approveTicket);
  $("#btn-cancel").addEventListener("click", cancelTicket);
  $("#ok-phrase").addEventListener("input", syncApproveButton);
  $("#btn-close-tp").addEventListener("click", () => closePaper("take_profit"));
  $("#btn-close-sl").addEventListener("click", () => closePaper("stop"));
  $("#btn-withdraw").addEventListener("click", tryWithdraw);
  $("#f-file").addEventListener("change", async (ev) => {
    const file = ev.target.files && ev.target.files[0];
    if (!file) return;
    $("#f-csv").value = await file.text();
  });
  syncApproveButton();
  showPanel("dash");
  await loadStatus();
  await loadJournal();
  await loadAlerts();
});
