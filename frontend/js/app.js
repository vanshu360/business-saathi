// Starts the app: loads server status, shows notices and switches pages based on the URL hash.
import { api } from "./api.js";
import { html, toast } from "./components.js";
import { state } from "./format.js";
import { renderDashboard } from "./pages/dashboard.js";
import { renderOrderDetail, renderOrderEdit, renderOrdersList, renderTypedOrder } from "./pages/orders.js";
import { renderVoice, stopVoice } from "./pages/voice.js";

const app = document.getElementById("app");

const ROUTES = [
  [/^dashboard$/, "dashboard", () => renderDashboard(app)],
  [/^voice$/, "voice", () => renderVoice(app)],
  [/^orders\/new$/, "orders/new", () => renderTypedOrder(app)],
  [/^orders$/, "orders", (m, params) => renderOrdersList(app, params)],
  [/^orders\/(\d+)$/, "orders", (m, params) => renderOrderDetail(app, Number(m[1]), params)],
  [/^orders\/(\d+)\/edit$/, "orders", (m) => renderOrderEdit(app, Number(m[1]))],
];

async function route() {
  stopVoice();
  const [path, search = ""] = location.hash.replace(/^#\/?/, "").split("?");
  const params = new URLSearchParams(search);
  const match = ROUTES.map(([re, nav, fn]) => [path.match(re), nav, fn]).find(([m]) => m);
  if (!match) { location.hash = "#/dashboard"; return; }
  const [m, nav, render] = match;
  document.querySelectorAll(".sidebar nav a").forEach((a) =>
    a.classList.toggle("active", a.dataset.route === nav));
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("menu-toggle").setAttribute("aria-expanded", "false");
  app.innerHTML = '<p class="muted">Loading…</p>';
  try {
    await render(m, params);
  } catch (err) {
    app.innerHTML = `<div class="card"><h1>Something went wrong</h1><p class="error-text">${html(err.message)}</p>
      <a class="btn" href="#/dashboard">Back to dashboard</a></div>`;
  }
  app.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}

async function init() {
  const notices = document.getElementById("notices");
  try {
    const status = await api.get("/api/system/status");
    state.sarvamConfigured = status.sarvam_configured;
    state.retentionHours = status.audio_retention_hours;
    state.timezone = status.timezone;
    notices.innerHTML = `<p class="notice info">Local demo · single shop · no login. Do not put this on the internet with real customer data.</p>` +
      (status.sarvam_configured ? "" : `<p class="notice warn">${html(status.sarvam_message)} <a href="#/orders/new">Type an order instead</a>.</p>`);
    const settings = await api.get("/api/settings");
    document.getElementById("shop-name").textContent = settings.shop_name || "My Shop";
    state.timeFormat = settings.time_format || "12h";
  } catch (err) {
    toast(err.message, true);
  }
  document.getElementById("menu-toggle").addEventListener("click", (e) => {
    const open = document.getElementById("sidebar").classList.toggle("open");
    e.currentTarget.setAttribute("aria-expanded", String(open));
  });
  document.getElementById("global-search").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = document.getElementById("global-search-input").value.trim();
    location.hash = `#/orders${q ? `?q=${encodeURIComponent(q)}` : ""}`;
  });
  window.addEventListener("hashchange", route);
  route();
}

init();
