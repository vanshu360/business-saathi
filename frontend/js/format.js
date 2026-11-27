// Display helpers: Indian date format (DD-MM-YYYY), Asia/Kolkata time, units and statuses.
export const state = { timeFormat: "12h", timezone: "Asia/Kolkata", sarvamConfigured: false };

export const UNITS = [
  ["kg", "kg"], ["g", "grams"], ["l", "litres"], ["ml", "ml"], ["piece", "pieces"], ["packet", "packets"],
];
export const STATUS_LABELS = {
  draft: "Draft", confirmed: "Confirmed", pending: "Pending",
  processing: "Processing", completed: "Completed", cancelled: "Cancelled",
};

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function parts(date, options) {
  const out = {};
  new Intl.DateTimeFormat("en-IN", { timeZone: state.timezone, ...options })
    .formatToParts(date).forEach((p) => { out[p.type] = p.value; });
  return out;
}

export function formatDate(isoDate) {
  if (!isoDate) return "";
  const [y, m, d] = isoDate.slice(0, 10).split("-");
  return `${d}-${m}-${y}`;
}

export function formatClock(hhmm) {
  if (!hhmm) return "";
  if (state.timeFormat === "24h") return hhmm;
  const [h, m] = hhmm.split(":").map(Number);
  const suffix = h >= 12 ? "PM" : "AM";
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${suffix}`;
}

export function formatTimestamp(iso) {
  if (!iso) return "";
  const p = parts(new Date(iso), {
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  });
  return `${p.day}-${p.month}-${p.year} ${formatClock(`${p.hour}:${p.minute}`)}`;
}

export function formatDelivery(order) {
  const bits = [formatDate(order.delivery_date), formatClock(order.delivery_time), order.delivery_time_text];
  return bits.filter(Boolean).join(", ") || "Not specified";
}

export function formatQuantity(item) {
  if (item.quantity === null || item.quantity === undefined) return "—";
  const unit = (UNITS.find(([v]) => v === item.unit) || [null, item.unit || ""])[1];
  return `${Number(item.quantity).toLocaleString("en-IN")} ${unit}`.trim();
}

// Shows only the last 3 digits in lists, to protect customer numbers on a shared screen.
export function maskPhone(phone) {
  if (!phone) return "";
  return `•••••••${phone.slice(-3)}`;
}
