// Small reusable pieces of interface.
import { escapeHtml, formatDelivery, formatTimestamp, maskPhone, STATUS_LABELS } from "./format.js";

export const html = escapeHtml;

export function statusBadge(status) {
  return `<span class="badge badge-${status}">${STATUS_LABELS[status] || status}</span>`;
}

export function demoBadge(isDemo) {
  return isDemo ? ' <span class="badge badge-demo" title="Sample data, not a real customer">DEMO</span>' : "";
}

export function emptyState(message, actionHref, actionLabel) {
  const action = actionHref ? `<a class="btn" href="${actionHref}">${html(actionLabel)}</a>` : "";
  return `<div class="empty"><p>${html(message)}</p>${action}</div>`;
}

export function ordersTable(orders, emptyMessage = "No orders yet.") {
  if (!orders.length) return emptyState(emptyMessage, "#/orders/new", "Create an order");
  const rows = orders.map((o) => `
    <tr class="clickable" data-href="#/orders/${o.id}" tabindex="0">
      <td><a href="#/orders/${o.id}">${html(o.order_number)}</a>${demoBadge(o.is_demo)}</td>
      <td>${html(o.customer_name || "No customer")}<br><small class="muted">${html(maskPhone(o.customer_phone))}</small></td>
      <td class="hide-mobile">${o.item_count}</td>
      <td class="hide-mobile">${html(formatDelivery(o))}</td>
      <td>${statusBadge(o.status)}</td>
      <td class="hide-mobile">${html(formatTimestamp(o.created_at))}</td>
    </tr>`).join("");
  return `<div class="table-wrap"><table>
    <thead><tr><th>Order</th><th>Customer</th><th class="hide-mobile">Items</th>
    <th class="hide-mobile">Delivery</th><th>Status</th><th class="hide-mobile">Created</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

export function bindRowLinks(root) {
  root.querySelectorAll("tr[data-href]").forEach((tr) => {
    const go = () => { location.hash = tr.dataset.href; };
    tr.addEventListener("click", (e) => { if (e.target.tagName !== "A") go(); });
    tr.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
  });
}

let toastTimer;
export function toast(message, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = `toast show${isError ? " error" : ""}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = "toast"; }, isError ? 6000 : 3000);
}

// Opens a modal; resolves with true/false (confirm) or closes when the content's form submits.
export function openModal(innerHtml, onMount) {
  const root = document.getElementById("modal-root");
  root.innerHTML = `<div class="modal-backdrop"><div class="modal" role="dialog" aria-modal="true">${innerHtml}</div></div>`;
  const close = () => { root.innerHTML = ""; };
  root.querySelector(".modal-backdrop").addEventListener("click", (e) => {
    if (e.target.classList.contains("modal-backdrop")) close();
  });
  root.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", close));
  const first = root.querySelector("input, select, textarea, button");
  if (first) first.focus();
  if (onMount) onMount(root.querySelector(".modal"), close);
  return close;
}

export function confirmDialog(title, message, confirmLabel = "Yes", danger = false) {
  return new Promise((resolve) => {
    openModal(`
      <h2>${html(title)}</h2><p>${html(message)}</p>
      <div class="actions">
        <button class="btn ${danger ? "btn-danger" : ""}" data-yes>${html(confirmLabel)}</button>
        <button class="btn btn-secondary" data-no>Go back</button>
      </div>`, (modal, close) => {
      modal.querySelector("[data-yes]").addEventListener("click", () => { close(); resolve(true); });
      modal.querySelector("[data-no]").addEventListener("click", () => { close(); resolve(false); });
    });
  });
}

// Disables a button while an async action runs, so it cannot be pressed twice.
export async function withBusy(button, busyLabel, action) {
  const label = button.textContent;
  button.disabled = true;
  button.textContent = busyLabel;
  try {
    return await action();
  } finally {
    button.disabled = false;
    button.textContent = label;
  }
}
