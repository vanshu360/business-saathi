import { api, newIdempotencyKey, query } from "../api.js";
import { bindRowLinks, confirmDialog, demoBadge, html, ordersTable, statusBadge, toast, withBusy } from "../components.js";
import { formatDelivery, formatQuantity, formatTimestamp, STATUS_LABELS } from "../format.js";
import { bindOrderForm, renderOrderForm } from "../review.js";

function summary(data) {
  const who = data.customer_name || "no customer name";
  return `${data.items.length} item(s) for ${who}: ` +
    data.items.map((i) => `${i.product_name} ${formatQuantity(i)}`).join(", ");
}

// Shared "Confirm and save" step: explicit confirmation, one idempotency key per form.
export function bindSaveOrder(form, extra) {
  const key = newIdempotencyKey();
  bindOrderForm(form, async (data, button, error) => {
    const ok = await confirmDialog("Save this order?", summary(data), "Yes, confirm and save");
    if (!ok) return;
    await withBusy(button, "Saving…", async () => {
      try {
        const order = await api.post("/api/orders", { ...data, ...extra(), status: "confirmed", idempotency_key: key });
        location.hash = `#/orders/${order.id}?saved=1`;
      } catch (err) {
        error.textContent = err.message;
      }
    });
  });
}

export async function renderTypedOrder(app) {
  app.innerHTML = `
    <div class="page-head"><h1>Type an order</h1>
      <p>Works without Sarvam. Type the order as one sentence and let the app fill the form, or fill it yourself.</p></div>
    <section class="card">
      <label for="typed">Order sentence (optional)</label>
      <textarea id="typed" placeholder="e.g. Ramesh ji ko 2 kilo chawal aur 1 litre doodh kal shaam 5 baje"></textarea>
      <div class="actions"><button class="btn btn-secondary" id="read-typed">Read this order</button></div>
    </section>
    <div id="form-slot">${renderOrderForm({}, "Confirm and save order")}</div>`;
  const mount = (draft) => {
    app.querySelector("#form-slot").innerHTML = renderOrderForm(draft, "Confirm and save order");
    bindSaveOrder(app.querySelector("#order-form"), () => ({ source: "manual" }));
  };
  mount({});
  app.querySelector("#read-typed").addEventListener("click", (e) => withBusy(e.target, "Reading…", async () => {
    const typedText = app.querySelector("#typed").value.trim();
    if (!typedText) { toast("Type the order first.", true); return; }
    try {
      mount(await api.post("/api/extract", { original: typedText }));
      toast("Form filled. Please check the highlighted fields.");
    } catch (err) { toast(err.message, true); }
  }));
}

export async function renderOrdersList(app, params) {
  const q = params.get("q") || "";
  const status = params.get("status") || "";
  const orders = await api.get(`/api/orders${query({ q, status })}`);
  const options = [["", "All statuses"], ["confirmed,pending,processing", "Open"], ...Object.entries(STATUS_LABELS)]
    .map(([v, l]) => `<option value="${v}" ${v === status ? "selected" : ""}>${l}</option>`).join("");
  app.innerHTML = `
    <div class="page-head"><h1>Saved orders</h1><p>Every confirmed order is stored in the SQLite database.</p></div>
    <form class="row card" id="filters">
      <input name="q" type="search" value="${html(q)}" placeholder="Name, phone, product or order number" aria-label="Search">
      <select name="status" aria-label="Status">${options}</select>
      <button class="btn btn-secondary">Filter</button>
    </form>
    <section class="card">${ordersTable(orders, q || status ? "No orders match." : "No orders yet.")}</section>`;
  bindRowLinks(app);
  app.querySelector("#filters").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    location.hash = `#/orders${query({ q: f.get("q").trim(), status: f.get("status") })}`;
  });
}

function transcriptBlock(t) {
  if (!t) return "";
  const card = (title, text, status) => `<div class="transcript"><h3>${title}</h3>
    <p>${text ? html(text) : `<span class="muted">${status === "failed" ? "Failed" : "Not available"}</span>`}</p></div>`;
  return `<section class="card"><h2>What the customer said</h2>
    <p class="muted">Language: ${html(t.language_detected || t.language_requested)}. The original transcript is the source of truth.</p>
    <div class="transcripts">${card("Original", t.original_text, t.original_status)}
      ${card("Roman", t.roman_text, t.roman_status)}${card("English", t.english_text, t.english_status)}</div></section>`;
}

export async function renderOrderDetail(app, id, params) {
  const o = await api.get(`/api/orders/${id}`);
  const saved = params && params.get("saved")
    ? `<p class="notice success" role="status">Order saved to the database. Reload this page or open <a href="#/orders">Saved orders</a> to see it is still there.</p>` : "";
  const items = o.items.map((i) => `<tr><td>${html(i.product_name)}${i.product_name_spoken && i.product_name_spoken !== i.product_name
    ? `<br><small class="muted">Heard: “${html(i.product_name_spoken)}”</small>` : ""}</td><td>${html(formatQuantity(i))}</td></tr>`).join("");
  const moves = o.allowed_next_statuses.map((s) =>
    `<button class="btn ${s === "cancelled" ? "btn-danger" : "btn-secondary"} btn-small" data-status="${s}">Mark ${STATUS_LABELS[s]}</button>`).join("");
  const history = (o.history || []).map((h) =>
    `<li><strong>${html(h.field)}</strong>: ${html(h.old_value ?? "—")} → ${html(h.new_value ?? "—")}
      <br><small class="muted">${html(formatTimestamp(h.changed_at))}</small></li>`).join("");
  app.innerHTML = `${saved}
    <div class="page-head"><h1>${html(o.order_number)} ${statusBadge(o.status)}${demoBadge(o.is_demo)}</h1>
      <p>${o.source === "voice" ? "Voice order" : "Typed order"} · created ${html(formatTimestamp(o.created_at))}</p></div>
    <div class="two-col">
      <section class="card"><h2>Order</h2>
        <dl class="details"><dt>Customer</dt><dd>${html(o.customer_name || "Not given")}</dd>
          <dt>Phone</dt><dd>${html(o.customer_phone || "Not given")}</dd>
          <dt>Delivery</dt><dd>${html(formatDelivery(o))}</dd>
          <dt>Instructions</dt><dd>${html(o.special_instructions || "None")}</dd></dl>
        <div class="table-wrap"><table><thead><tr><th>Product</th><th>Quantity</th></tr></thead><tbody>${items}</tbody></table></div>
        <div class="actions">${o.can_edit ? `<a class="btn btn-secondary btn-small" href="#/orders/${o.id}/edit">Edit</a>` : ""}${moves}</div>
      </section>
      <section class="card"><h2>History</h2><ul class="history-list">${history || "<li>No changes yet.</li>"}</ul></section>
    </div>${transcriptBlock(o.transcription)}`;
  app.querySelectorAll("[data-status]").forEach((b) => b.addEventListener("click", async () => {
    const s = b.dataset.status;
    if (s === "cancelled" && !(await confirmDialog("Cancel this order?", "This cannot be undone.", "Cancel order", true))) return;
    await withBusy(b, "Saving…", async () => {
      try {
        await api.patch(`/api/orders/${id}/status`, { status: s });
        toast(`Order marked ${STATUS_LABELS[s]}.`);
        renderOrderDetail(app, id);
      } catch (err) { toast(err.message, true); }
    });
  }));
}

export async function renderOrderEdit(app, id) {
  const o = await api.get(`/api/orders/${id}`);
  app.innerHTML = `<div class="page-head"><h1>Edit ${html(o.order_number)}</h1></div>${renderOrderForm(o, "Save changes")}`;
  bindOrderForm(app.querySelector("#order-form"), (data, button, error) => withBusy(button, "Saving…", async () => {
    try {
      await api.put(`/api/orders/${id}`, data);
      toast("Changes saved.");
      location.hash = `#/orders/${id}`;
    } catch (err) { error.textContent = err.message; }
  }));
}
