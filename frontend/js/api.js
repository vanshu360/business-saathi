// All calls to the backend go through this file.
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function describeValidationError(detail) {
  if (!Array.isArray(detail)) return String(detail);
  return detail
    .map((d) => {
      const field = (d.loc || []).filter((p) => p !== "body").join(" → ");
      return field ? `${field}: ${d.msg}` : d.msg;
    })
    .join("; ");
}

export async function request(method, path, body) {
  const options = { method, headers: {} };
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(path, options);
  } catch {
    throw new ApiError("Cannot reach the server. Check your connection and try again.", 0);
  }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const message = data && data.detail ? describeValidationError(data.detail) : `Request failed (${res.status})`;
    throw new ApiError(message, res.status);
  }
  return data;
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body ?? {}),
  put: (path, body) => request("PUT", path, body),
  patch: (path, body) => request("PATCH", path, body),
  del: (path) => request("DELETE", path),
};

export function query(params) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.set(k, v);
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

// crypto.randomUUID needs HTTPS; getRandomValues works on plain http too (e.g. phone on local Wi-Fi).
export function newIdempotencyKey() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
