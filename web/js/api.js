// Cliente HTTP: añade el JWT, desenvuelve el envelope {success, data, error, meta}.
import { session } from "./session.js";

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details || {};
  }
}

let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

async function request(method, path, { body, query, auth = true } = {}) {
  const url = new URL(`/api${path}`, window.location.origin);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
    }
  }
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = session.token();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "network", "No se pudo conectar con el servidor");
  }
  let payload = null;
  try {
    payload = await res.json();
  } catch {
    /* respuesta sin JSON */
  }
  if (!res.ok || (payload && payload.success === false)) {
    const err = payload?.error || {};
    if (res.status === 401 && auth) onUnauthorized();
    throw new ApiError(res.status, err.code || "http_error", humanize(res.status, err), err.details);
  }
  return { data: payload?.data, meta: payload?.meta || {} };
}

function humanize(status, err) {
  if (status === 422 && Array.isArray(err.details?.errors) && err.details.errors.length) {
    return err.details.errors
      .map((e) => `${(e.loc || []).filter((p) => p !== "body").join(".")}: ${e.msg}`)
      .join(" · ");
  }
  return err.message || `Error ${status}`;
}

export const api = {
  get: (path, query) => request("GET", path, { query }).then((r) => r.data),
  getPage: (path, query) => request("GET", path, { query }),
  post: (path, body) => request("POST", path, { body: body ?? {} }).then((r) => r.data),
  patch: (path, body) => request("PATCH", path, { body }).then((r) => r.data),
  del: (path) => request("DELETE", path).then((r) => r.data),
  login: (username, password) =>
    request("POST", "/auth/login", { body: { username, password }, auth: false }).then((r) => r.data),
};
