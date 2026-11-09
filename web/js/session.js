// Sesión en sessionStorage: se borra al cerrar la pestaña.
const KEY = "contabilidad.session";

function read() {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    const s = JSON.parse(raw);
    if (!s.expires_at || new Date(s.expires_at) <= new Date()) return null;
    return s;
  } catch {
    return null;
  }
}

export const session = {
  get: read,
  token: () => read()?.access_token || null,
  user: () => read()?.user || null,
  save(loginResult) {
    try {
      sessionStorage.setItem(KEY, JSON.stringify(loginResult));
    } catch {
      /* almacenamiento bloqueado: la sesión dura lo que la página */
    }
  },
  updateUser(user) {
    const s = read();
    if (s) this.save({ ...s, user });
  },
  clear() {
    try {
      sessionStorage.removeItem(KEY);
    } catch {
      /* noop */
    }
  },
};
