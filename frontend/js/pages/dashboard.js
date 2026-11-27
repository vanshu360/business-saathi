import { api } from "../api.js";
import { bindRowLinks, ordersTable } from "../components.js";
import { state } from "../format.js";

export async function renderDashboard(app) {
  const d = await api.get("/api/dashboard");
  const stat = (label, value, href) =>
    `<a class="stat card" href="${href}"><span class="value">${value.total}</span><span class="label">${label}</span></a>`;
  app.innerHTML = `
    <div class="page-head"><h1>Today at a glance</h1>
      <p>Speak an order, check it, save it.</p></div>
    <div class="cta-row">
      <a class="btn btn-big" href="#/voice" ${state.sarvamConfigured ? "" : 'aria-disabled="true"'}>New voice order</a>
      <a class="btn btn-secondary btn-big" href="#/orders/new">Type an order</a>
    </div>
    <div class="grid stats">
      ${stat("Orders today", d.orders_today, "#/orders")}
      ${stat("Open orders", d.pending, "#/orders?status=confirmed,pending,processing")}
      ${stat("Drafts", d.drafts, "#/orders?status=draft")}
      ${stat("Completed", d.completed, "#/orders?status=completed")}
    </div>
    <section class="card"><h2>Recent orders</h2><div id="recent">${ordersTable(d.recent_orders, "No orders yet. Record your first one!")}</div></section>`;
  bindRowLinks(app);
}
