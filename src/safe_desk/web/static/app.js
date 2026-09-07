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
    presets_title: "Demo presets",
    presets_hint: "One-click judge path. Dry-run only. No live orders.",
    presets_or: "Or run a demo preset:",
    preset_ideal: "Ideal setup (Approved path)",
    preset_risk: "Risk breach (Blocked by Policy)",
    preset_withdraw: "Withdraw attempt (Forbidden)",
    chart_title: "ATR levels (advisory)",
    chart_hint: "Chart shows ATR-based Entry / SL / TP1 / TP2. Levels refresh from the latest ATR when you re-analyze. Advisory only — not a live trailing order.",
    chart_entry: "Entry",
    chart_sl: "SL",
    chart_tp1: "TP1",
    chart_tp2: "TP2",
    chart_offline: "Lightweight Charts CDN unavailable — simple offline chart.",
    atr_used: "1% size uses the ATR stop distance.",
    atr_user_stop: "Sizing used your stop. ATR SL/TP1/TP2 below are still suggestions.",
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
    presets_title: "Демо-пресеты",
    presets_hint: "Один клик для судей. Только dry-run. Живых заявок нет.",
    presets_or: "Или запустите демо-пресет:",
    preset_ideal: "Идеальный сетап (путь к одобрению)",
    preset_risk: "Нарушение риска (политика BLOCKED)",
    preset_withdraw: "Попытка вывода (запрещено)",
    chart_title: "Уровни ATR (подсказка)",
    chart_hint: "График показывает вход, SL, TP1 и TP2 от ATR. Уровни обновляются по последнему ATR при новом разборе. Только подсказка — не биржевой трейлинг.",
    chart_entry: "Вход",
    chart_sl: "SL",
    chart_tp1: "TP1",
    chart_tp2: "TP2",
    chart_offline: "CDN Lightweight Charts недоступен — простой офлайн-график.",
    atr_used: "Размер на 1% риска считает дистанцию до ATR-стопа.",
    atr_user_stop: "Размер по вашему стопу. SL/TP1/TP2 от ATR ниже — всё ещё подсказки.",
  },
};

let lang = localStorage.getItem("safe-desk-lang") || "en";
let lastAnalyze = null;
let lastTicket = null;
let lastChart = null;
const chartHandles = {};
const LEVEL_COLORS = { entry: "#0f4c5c", sl: "#9b2226", tp1: "#2d6a4f", tp2: "#40916c" };

function t(key) {
  return (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key;
}

function applyLang() {
  $$("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  $$(".lang-toggle button").forEach((b) => b.classList.toggle("on", b.dataset.lang === lang));
  document.documentElement.lang = lang;
  if (lastChart) {
    drawChart("analyze-chart", "analyze-legend", lastChart);
    drawChart("ticket-chart", "ticket-legend", lastChart);
  }
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
    k_sl: numOrNull($("#f-k-sl").value),
    k_tp1: numOrNull($("#f-k-tp1").value),
    k_tp2: numOrNull($("#f-k-tp2").value),
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
        <div class="stat"><span class="k">Higher TF</span><span class="v">${s.htf_trend || "—"} ${s.mtf_state && s.mtf_state !== "UNKNOWN" ? `(${s.mtf_state})` : ""}</span></div>
        <div class="stat"><span class="k">Swings</span><span class="v">${s.vol_regime}</span></div>
        <div class="stat"><span class="k">RSI</span><span class="v">${s.rsi == null ? "—" : `${Number(s.rsi).toFixed(1)} ${s.rsi_state || ""}`}</span></div>
        <div class="stat"><span class="k">Volume</span><span class="v">${s.volume_ratio == null ? "—" : `${Number(s.volume_ratio).toFixed(2)}× ${s.volume_flag || ""}`}</span></div>
        <div class="stat"><span class="k">Risk</span><span class="v">${s.risk_score} / 100</span></div>
        <div class="stat"><span class="k">Signal</span><span class="v">${s.signal}</span></div>
        <div class="stat"><span class="k">Proof</span><span class="v">${data.proof ? data.proof.verdict : "—"}</span></div>
      </div>
      <div id="analyze-why"></div>
      ${data.size ? `<p class="hint">1% size: <strong>${qty(data.size.quantity)}</strong> · worth ${money(data.size.notional)} · risk ${money(data.size.risk_quote)}</p>` : ""}
      ${levelsHint(data)}
      <p class="hint">${data.offline ? "Offline path (sample / CSV). No MCP login used." : "Numbers from pasted MCP-shaped JSON. This app did not call Binance."}</p>
    `;
    renderWhy(data.why, $("#analyze-why"));
    applyAtrSuggestions(data);
    showChartFromAnalyze(data);
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
    take_profit_2: numOrNull($("#t-tp2").value),
    risk_pct: numOrNull($("#t-risk").value) || 1,
    k_sl: numOrNull($("#f-k-sl") && $("#f-k-sl").value),
    k_tp1: numOrNull($("#f-k-tp1") && $("#f-k-tp1").value),
    k_tp2: numOrNull($("#f-k-tp2") && $("#f-k-tp2").value),
    use_sample: true,
    lang,
  };
  if (!body.equity || !body.entry) {
    setErr(out, "Need entry and equity (or analyze the sample first). Stop can come from ATR.");
    return;
  }
  try {
    const { data } = await api("/api/ticket", { method: "POST", body: JSON.stringify(body) });
    paintTicket(data);
    if (data.chart) showChartFromAnalyze({ chart: data.chart, levels: data.levels });
    else if (lastAnalyze) showChartFromAnalyze(lastAnalyze);
    await loadStatus();
    await loadAlerts();
    showPanel("ticket");
  } catch (err) {
    setErr(out, err.message);
  }
}

function ticketStatusLabel(status) {
  return String(status || "").replace(/_/g, "_").toUpperCase();
}

function paintTicket(data) {
  const out = $("#ticket-out");
  lastTicket = data.ticket;
  const blocked = (data.blocked_reasons || []).length || data.ticket.status === "blocked";
  out.innerHTML = `
    <p>${badge(ticketStatusLabel(data.ticket.status), blocked ? "skip" : "wait")} ${badge("DRY-RUN", "dry")} ${badge("NOT AN ORDER", "paper")}</p>
    <p class="ticket-id">${data.ticket.id}</p>
    <p class="hint">${data.label}</p>
    <div id="ticket-why"></div>
    <p>Size ${qty(data.ticket.quantity)} · risk ${money(data.ticket.risk_quote)} · ${data.ticket.symbol} ${data.ticket.side}</p>
    ${data.ticket.take_profit_2 != null ? `<p class="hint">TP1 ${money(data.ticket.take_profit)} · TP2 ${money(data.ticket.take_profit_2)}</p>` : ""}
    ${blocked ? `<ul class="err">${(data.blocked_reasons || []).map((r) => `<li>${r}</li>`).join("")}</ul>` : ""}
  `;
  renderWhy(data.why, $("#ticket-why"));
  $("#ok-phrase").placeholder = data.ok_phrase;
  $("#ok-phrase").dataset.expected = blocked ? "" : data.ok_phrase;
  if (blocked) $("#ok-phrase").value = "";
  syncApproveButton();
}

function syncApproveButton() {
  const expected = $("#ok-phrase").dataset.expected || "";
  const typed = $("#ok-phrase").value.trim();
  const blocked = lastTicket && lastTicket.status === "blocked";
  $("#btn-approve").disabled = blocked || !expected || typed.toUpperCase() !== expected.toUpperCase();
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
  $("#f-stop").value = "";
  $("#f-equity").value = "1000";
  $("#f-risk").value = "1";
  $("#f-k-sl").value = "1.2";
  $("#f-k-tp1").value = "1.5";
  $("#f-k-tp2").value = "2.5";
  $("#t-symbol").value = "BTCUSDT";
  $("#t-side").value = "BUY";
  $("#t-entry").value = "102450";
  $("#t-stop").value = "";
  $("#t-equity").value = "1000";
  $("#t-tp").value = "";
  $("#t-tp2").value = "";
  $("#t-risk").value = "1";
}

function levelsHint(data) {
  const lv = data.levels;
  if (!lv) return "";
  const src = data.stop_source === "atr" ? t("atr_used") : t("atr_user_stop");
  return `<p class="hint">${src} SL ${money(lv.sl)} · TP1 ${money(lv.tp1)} · TP2 ${money(lv.tp2)} · k_sl ${lv.k_sl} · k_tp1 ${lv.k_tp1} · k_tp2 ${lv.k_tp2}</p>`;
}

function applyAtrSuggestions(data) {
  const lv = data && data.levels;
  if (!lv) return;
  $("#t-symbol").value = data.symbol || $("#t-symbol").value;
  if (data.side) $("#t-side").value = data.side;
  $("#t-entry").value = lv.entry;
  $("#t-stop").value = lv.sl;
  $("#t-tp").value = lv.tp1;
  $("#t-tp2").value = lv.tp2;
  if (data.size && data.size.equity) $("#t-equity").value = data.size.equity;
  if (!$("#f-stop").value) $("#f-stop").value = lv.sl;
}

function showChartFromAnalyze(data) {
  lastChart = data && data.chart ? data.chart : null;
  const has = lastChart && (lastChart.ohlcv || []).length;
  $("#analyze-chart-card").classList.toggle("hidden", !has);
  $("#ticket-chart-card").classList.toggle("hidden", !has);
  if (!has) return;
  drawChart("analyze-chart", "analyze-legend", lastChart);
  drawChart("ticket-chart", "ticket-legend", lastChart);
}

function drawChart(elId, legendId, payload) {
  const el = document.getElementById(elId);
  const legend = document.getElementById(legendId);
  if (!el || !payload) return;
  const bars = payload.ohlcv || [];
  const lv = payload.levels || {};
  if (legend) {
    legend.innerHTML = [
      ["entry", t("chart_entry"), lv.entry],
      ["sl", t("chart_sl"), lv.sl],
      ["tp1", t("chart_tp1"), lv.tp1],
      ["tp2", t("chart_tp2"), lv.tp2],
    ].map(([key, label, price]) =>
      `<span><i class="swatch" style="background:${LEVEL_COLORS[key]}"></i>${label} <span class="k">${money(price)}</span></span>`
    ).join("");
  }
  if (window.LightweightCharts && window.LightweightCharts.createChart) {
    drawLightweightChart(el, bars, lv);
  } else {
    drawFallbackChart(el, bars, lv);
  }
}

function destroyChart(el) {
  const id = el.id;
  if (chartHandles[id]) {
    try { chartHandles[id].remove(); } catch (err) { /* ignore */ }
    delete chartHandles[id];
  }
  el.innerHTML = "";
}

function drawLightweightChart(el, bars, lv) {
  destroyChart(el);
  const chart = LightweightCharts.createChart(el, {
    width: el.clientWidth || 640,
    height: 320,
    layout: { background: { color: "#fffdf8" }, textColor: "#1c2430" },
    grid: { vertLines: { color: "#eee6d6" }, horzLines: { color: "#eee6d6" } },
    rightPriceScale: { borderColor: "#d9d1c2" },
    timeScale: { borderColor: "#d9d1c2" },
  });
  const series = chart.addCandlestickSeries({
    upColor: "#2d6a4f",
    downColor: "#9b2226",
    borderVisible: false,
    wickUpColor: "#2d6a4f",
    wickDownColor: "#9b2226",
  });
  series.setData(bars.map((b) => ({
    time: b.time,
    open: b.open,
    high: b.high,
    low: b.low,
    close: b.close,
  })));
  const lines = [
    [lv.entry, LEVEL_COLORS.entry, t("chart_entry")],
    [lv.sl, LEVEL_COLORS.sl, t("chart_sl")],
    [lv.tp1, LEVEL_COLORS.tp1, t("chart_tp1")],
    [lv.tp2, LEVEL_COLORS.tp2, t("chart_tp2")],
  ];
  lines.forEach(([price, color, title]) => {
    if (price == null) return;
    series.createPriceLine({
      price,
      color,
      lineWidth: 2,
      lineStyle: LightweightCharts.LineStyle.Solid,
      axisLabelVisible: true,
      title,
    });
  });
  chart.timeScale().fitContent();
  chartHandles[el.id] = chart;
}

function drawFallbackChart(el, bars, lv) {
  destroyChart(el);
  if (!bars.length) return;
  const w = el.clientWidth || 640;
  const h = 320;
  const pad = { l: 12, r: 72, t: 16, b: 24 };
  const prices = bars.flatMap((b) => [b.high, b.low]);
  ["entry", "sl", "tp1", "tp2"].forEach((k) => {
    if (lv[k] != null) prices.push(lv[k]);
  });
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const span = max - min || 1;
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const x = (i) => pad.l + (innerW * i) / Math.max(bars.length - 1, 1);
  const y = (p) => pad.t + innerH * (1 - (p - min) / span);
  const path = bars.map((b, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(b.close).toFixed(1)}`).join(" ");
  const levelRows = [
    ["entry", t("chart_entry"), lv.entry],
    ["sl", t("chart_sl"), lv.sl],
    ["tp1", t("chart_tp1"), lv.tp1],
    ["tp2", t("chart_tp2"), lv.tp2],
  ].filter((row) => row[2] != null);
  const lines = levelRows.map(([key, label, price]) => {
    const yy = y(price).toFixed(1);
    return `<line x1="${pad.l}" x2="${w - pad.r}" y1="${yy}" y2="${yy}" stroke="${LEVEL_COLORS[key]}" stroke-width="1.6"/>
      <text x="${w - pad.r + 4}" y="${Number(yy) + 4}" fill="${LEVEL_COLORS[key]}" font-size="11">${label}</text>`;
  }).join("");
  el.innerHTML = `<svg viewBox="0 0 ${w} ${h}" width="100%" height="320" role="img" aria-label="${t("chart_title")}">
    <rect width="${w}" height="${h}" fill="#fffdf8"/>
    <path d="${path}" fill="none" stroke="#0f4c5c" stroke-width="1.6"/>
    ${lines}
  </svg>
  <p class="hint">${t("chart_offline")}</p>`;
}

function fillRiskBreachDefaults() {
  fillDemoDefaults();
  $("#f-risk").value = "2";
  $("#t-risk").value = "2";
}

async function runPreset(name) {
  const note = $("#preset-out");
  if (note) setErr(note, "");
  try {
    const { data } = await api("/api/demo/preset", {
      method: "POST",
      body: JSON.stringify({ name, lang }),
    });
    if (data.preset === "withdraw") {
      $("#alerts-extra").innerHTML = `<p class="err">${data.message}</p>`;
      if (note) note.innerHTML = `<p class="err">${data.title}: ${data.message}</p>`;
      await loadAlerts();
      await loadStatus();
      showPanel("alerts");
      return;
    }
    if (data.preset === "risk_breach") {
      fillRiskBreachDefaults();
    } else {
      fillDemoDefaults();
    }
    if (data.analyze) {
      lastAnalyze = data.analyze;
      applyAtrSuggestions(data.analyze);
      showChartFromAnalyze(data.analyze);
    }
    if (data.ticket) {
      paintTicket(data.ticket);
      if (data.ticket.chart) showChartFromAnalyze({ chart: data.ticket.chart, levels: data.ticket.levels });
    }
    if (note) {
      const cls = data.blocked ? "err" : "okmsg";
      note.innerHTML = `<p class="${cls}">${data.title}. ${data.message}</p>`;
    }
    await loadStatus();
    await loadAlerts();
    showPanel(data.panel || "ticket");
  } catch (err) {
    if (note) setErr(note, err.message);
  }
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
  $$(".preset-btn").forEach((b) => {
    b.addEventListener("click", () => runPreset(b.dataset.preset));
  });
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
