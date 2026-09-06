const cards = document.getElementById("cards");
const flash = document.getElementById("flash");
const phrase = document.getElementById("phrase");
let lastTicketId = null;

function mark(step) {
  const el = document.querySelector(`[data-step="${step}"]`);
  if (el) el.classList.add("on");
}

function num(v, d = 2) {
  if (v == null) return "—";
  return Number(v).toLocaleString("en-US", { maximumFractionDigits: d });
}

function card(title, bodyHtml) {
  const wrap = document.createElement("section");
  wrap.className = "card";
  wrap.innerHTML = `<h3>${title}</h3>${bodyHtml}`;
  cards.prepend(wrap);
}

async function post(path, body = {}) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function setFlash(text, cls) {
  flash.className = `flash ${cls || ""}`;
  flash.textContent = text;
}

document.getElementById("btn-analyze").onclick = async () => {
  const a = await post("/api/analyze");
  mark("read");
  mark("analyze");
  card(
    `Analyze ${a.symbol} · ${a.signal}`,
    `<div class="kv">
      <span>Path</span><div>${a.path} (synthetic CSV)</div>
      <span>Last</span><div>${num(a.last)}</div>
      <span>SMA20 / 50</span><div>${num(a.sma20)} / ${num(a.sma50)}</div>
      <span>ATR</span><div>${num(a.atr, 4)} (${num(a.atr_pct, 2)}%)</div>
      <span>Trend / vol</span><div>${a.trend} · ${a.vol_regime}</div>
      <span>Risk score</span><div>${a.risk_score} / 100</div>
      <span>Signal</span><div>${a.signal} — setup only, not an order</div>
    </div>`
  );
  setFlash("Analyze complete. BUY is a setup label.", "pass");
};

document.getElementById("btn-proof").onclick = async () => {
  const p = await post("/api/proof");
  mark("proof");
  const cls = p.verdict === "REJECT" ? "fail" : p.verdict === "WAIT" ? "warn" : "pass";
  card(
    `Proof ${p.verdict}`,
    `<div class="kv">
      <span>Verdict</span><div class="${cls}">${p.verdict}</div>
      <span>Analogs</span><div>${p.n_analogs} · k=${p.k} · window=${p.window} · horizon=${p.horizon}</div>
      <span>Median fwd</span><div>${p.median_forward_return == null ? "—" : (p.median_forward_return * 100).toFixed(2) + "%"}</div>
      <span>Hit rate</span><div>${p.hit_rate == null ? "—" : Math.round(p.hit_rate * 100) + "%"}</div>
      <span>Receipt</span><div class="mono">${p.receipt_hash}</div>
    </div>
    <p>${p.rationale || p.note}</p>`
  );
  setFlash(`Proof ${p.verdict}. Not a live win rate.`, cls);
};

document.getElementById("btn-policy").onclick = async () => {
  const p = await post("/api/policy", { intent: "ticket" });
  mark("policy");
  const cls = p.ok ? "pass" : "fail";
  const viol = (p.violations || []).map((v) => `${v.code}: ${v.message}`).join("<br />") || "none";
  card(
    `Policy ${p.ok ? "PASS" : "FAIL"}`,
    `<div class="kv">
      <span>Intent</span><div>${p.intent}</div>
      <span>Result</span><div class="${cls}">${p.ok ? "PASS" : "FAIL"}</div>
      <span>Emergency</span><div>${p.emergency_stop}</div>
      <span>Violations</span><div>${viol}</div>
    </div>
    <p>Withdrawals and transfer-out always fail this engine.</p>`
  );
  setFlash(p.ok ? "Policy PASS — ticket may be drafted." : "Policy FAIL — no AWAITING_APPROVAL.", cls);
};

document.getElementById("btn-ticket").onclick = async () => {
  const t = await post("/api/ticket");
  const ticket = t.ticket;
  lastTicketId = ticket.id;
  mark("proof");
  mark("policy");
  mark("ticket");
  const cls = ticket.status === "blocked" ? "fail" : "warn";
  card(
    `Ticket ${ticket.id}`,
    `<div class="kv">
      <span>Status</span><div class="${cls}">${ticket.status.toUpperCase()}</div>
      <span>Mode</span><div>${ticket.mode.toUpperCase()}</div>
      <span>Symbol / side</span><div>${ticket.symbol} ${ticket.side}</div>
      <span>Entry / stop / TP</span><div>${num(ticket.entry)} / ${num(ticket.stop_loss)} / ${num(ticket.take_profit)}</div>
      <span>Risk</span><div>${ticket.risk_pct}% (${num(ticket.risk_quote)} quote)</div>
      <span>Qty / notional</span><div>${ticket.quantity} / ${num(ticket.notional)}</div>
      <span>MCP action</span><div>${ticket.mcp_action}</div>
    </div>
    <p>Waiting. A bare “ok” is rejected. Reply <code>OK ${ticket.id}</code>.</p>`
  );
  phrase.value = "";
  phrase.placeholder = `OK ${ticket.id}`;
  setFlash(`Ticket ${ticket.id} ${ticket.status}. No order sent.`, cls);
};

async function sendPhrase(text) {
  const r = await post("/api/command", { phrase: text });
  if (r.kind === "bare_ok") {
    card("Bare ok rejected", `<p class="fail">${r.message}</p>`);
    setFlash(r.message, "fail");
    return;
  }
  if (r.kind === "withdraw_refused") {
    card("Withdrawal refused", `<p class="fail">${r.message}</p>`);
    setFlash(r.message, "fail");
    return;
  }
  if (r.kind === "simulated") {
    mark("ok");
    card(
      `DRY-RUN ${r.payload.status}`,
      `<p class="pass">${r.message}</p>
       <pre>${JSON.stringify(r.payload, null, 2)}</pre>`
    );
    setFlash(r.message, "pass");
    return;
  }
  card("Desk reply", `<p>${r.message}</p>`);
  setFlash(r.message, r.ok ? "pass" : "fail");
}

document.getElementById("btn-ok").onclick = () => sendPhrase(phrase.value);
document.getElementById("btn-bare").onclick = () => sendPhrase("ok");
document.getElementById("btn-withdraw").onclick = () =>
  sendPhrase("withdraw 50 USDT to my wallet 0x1111111111111111111111111111111111111111");
phrase.addEventListener("keydown", (ev) => {
  if (ev.key === "Enter") sendPhrase(phrase.value);
});

fetch("/api/health")
  .then((r) => r.json())
  .then((h) => {
    mark("read");
    setFlash(`Desk ready · ${h.mode} · ${h.csv}`, "pass");
  })
  .catch(() => setFlash("Desk UI loaded, health check failed.", "fail"));
