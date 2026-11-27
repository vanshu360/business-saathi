// Editable order review form, shared by voice orders, typed orders and editing a saved order.
import { html } from "./components.js";
import { UNITS } from "./format.js";

function unitOptions(selected) {
  const blank = `<option value="" ${selected ? "" : "selected"}>Choose unit</option>`;
  return blank + UNITS.map(([v, label]) =>
    `<option value="${v}" ${v === selected ? "selected" : ""}>${label}</option>`).join("");
}

function itemRow(item = {}) {
  const review = item.needs_review ? " review" : "";
  const spoken = item.product_name_spoken
    ? `<small class="muted">Heard: “${html(item.product_name_spoken)}”</small>` : "";
  const suggestion = item.suggestion
    ? ` <button type="button" class="btn btn-small btn-secondary" data-use="${html(item.suggestion)}">Use “${html(item.suggestion)}”</button>` : "";
  const note = item.needs_review
    ? `<p class="review-note"><span class="badge badge-review">Check</span> ${html(item.review_reason || "Please check")}${suggestion}</p>` : "";
  return `<div class="item-row${review}" data-item data-product-id="${item.product_id ?? ""}"
      data-spoken="${html(item.product_name_spoken || "")}">
    <div class="field"><label>Product</label>
      <input name="product_name" required maxlength="120" value="${html(item.product_name || "")}" placeholder="e.g. Rice">${spoken}</div>
    <div class="field"><label>Quantity</label>
      <input name="quantity" type="number" inputmode="decimal" min="0.001" step="any" value="${item.quantity ?? ""}"></div>
    <div class="field"><label>Unit</label><select name="unit">${unitOptions(item.unit)}</select></div>
    <button type="button" class="btn btn-secondary btn-small" data-remove aria-label="Remove item">Remove</button>
    ${note}
  </div>`;
}

function fieldNote(uncertain, key) {
  return uncertain[key] ? `<small class="error-text"><span class="badge badge-review">Check</span> ${html(uncertain[key])}</small>` : "";
}

// draft: {customer_name, customer_phone, delivery_date, delivery_time, delivery_time_text,
//         special_instructions, items, uncertain_fields, unmatched_text}
export function renderOrderForm(draft, submitLabel) {
  const u = draft.uncertain_fields || {};
  const items = draft.items && draft.items.length ? draft.items : [{}];
  const unmatched = (draft.unmatched_text || []).length
    ? `<p class="notice warn">Words not understood: “${html(draft.unmatched_text.join("”, “"))}”. Add them as items or instructions if needed.</p>` : "";
  const itemsNote = u.items ? `<p class="notice warn">${html(u.items)}</p>` : "";
  return `<form id="order-form" class="card" novalidate>
    <h2>Customer</h2>
    <div class="form-grid">
      <div class="field"><label for="f-name">Customer name</label>
        <input id="f-name" name="customer_name" maxlength="80" value="${html(draft.customer_name || "")}" placeholder="Optional">${fieldNote(u, "customer_name")}</div>
      <div class="field"><label for="f-phone">Phone</label>
        <input id="f-phone" name="customer_phone" inputmode="tel" value="${html(draft.customer_phone || "")}" placeholder="10-digit mobile, optional">${fieldNote(u, "customer_phone")}</div>
    </div>
    <h2>Items</h2>${itemsNote}
    <div class="items" id="items">${items.map(itemRow).join("")}</div>
    <button type="button" class="btn btn-secondary" id="add-item">+ Add item</button>
    ${unmatched}
    <h2>Delivery</h2>
    <div class="form-grid">
      <div class="field"><label for="f-date">Date</label>
        <input id="f-date" type="date" name="delivery_date" value="${html(draft.delivery_date || "")}">${fieldNote(u, "delivery_date")}</div>
      <div class="field"><label for="f-time">Time</label>
        <input id="f-time" type="time" name="delivery_time" value="${html(draft.delivery_time || "")}">${fieldNote(u, "delivery_time")}</div>
      <div class="field"><label for="f-when">As spoken</label>
        <input id="f-when" name="delivery_time_text" maxlength="80" value="${html(draft.delivery_time_text || "")}" placeholder="e.g. tomorrow evening"></div>
    </div>
    <div class="field"><label for="f-notes">Special instructions</label>
      <textarea id="f-notes" name="special_instructions" maxlength="1000">${html(draft.special_instructions || "")}</textarea></div>
    <p class="error-text" id="form-error" role="alert"></p>
    <div class="actions"><button type="submit" class="btn" id="save-order">${html(submitLabel)}</button></div>
  </form>`;
}

export function bindOrderForm(form, onSubmit) {
  const items = form.querySelector("#items");
  form.querySelector("#add-item").addEventListener("click", () => {
    items.insertAdjacentHTML("beforeend", itemRow());
    items.lastElementChild.querySelector("input").focus();
  });
  items.addEventListener("click", (e) => {
    const row = e.target.closest("[data-item]");
    if (e.target.matches("[data-remove]")) {
      row.remove();
      if (!items.children.length) items.insertAdjacentHTML("beforeend", itemRow());
    } else if (e.target.dataset.use) {
      row.querySelector("[name=product_name]").value = e.target.dataset.use;
      row.dataset.productId = "";
      e.target.remove();
    }
  });
  items.addEventListener("input", (e) => {
    const row = e.target.closest("[data-item]");
    if (e.target.name === "product_name") row.dataset.productId = "";
    row.classList.remove("review");
  });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const error = form.querySelector("#form-error");
    const { data, problem } = collect(form);
    error.textContent = problem || "";
    if (!problem) await onSubmit(data, form.querySelector("#save-order"), error);
  });
}

function collect(form) {
  const v = (name) => form.elements[name].value.trim();
  const rows = [...form.querySelectorAll("[data-item]")];
  const items = rows.map((row) => {
    const get = (n) => row.querySelector(`[name=${n}]`).value.trim();
    return {
      product_id: row.dataset.productId ? Number(row.dataset.productId) : null,
      product_name_spoken: row.dataset.spoken || "",
      product_name: get("product_name"),
      quantity: get("quantity") === "" ? null : Number(get("quantity")),
      unit: get("unit") || null,
    };
  }).filter((i) => i.product_name || i.quantity !== null);
  let problem = "";
  if (!items.length) problem = "Add at least one item.";
  else if (items.some((i) => !i.product_name)) problem = "Every item needs a product name.";
  else if (items.some((i) => !(i.quantity > 0))) problem = "Every item needs a quantity above 0.";
  else if (items.some((i) => !i.unit)) problem = "Every item needs a unit.";
  const phone = v("customer_phone");
  if (!problem && phone && phone.replace(/\D/g, "").replace(/^91(?=\d{10}$)/, "").length !== 10) {
    problem = "Phone number should have 10 digits.";
  }
  return {
    problem,
    data: {
      customer_name: v("customer_name") || null,
      customer_phone: phone || null,
      delivery_date: v("delivery_date") || null,
      delivery_time: v("delivery_time") || null,
      delivery_time_text: v("delivery_time_text"),
      special_instructions: v("special_instructions"),
      items,
    },
  };
}
