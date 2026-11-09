// Arranque, layout y enrutador por hash.
import { api, setUnauthorizedHandler } from "./api.js";
import { clear, h, toast } from "./dom.js";
import { session } from "./session.js";
import { dashboardView } from "./views/dashboard.js";
import { loginView } from "./views/login.js";
import { myDebtView } from "./views/myDebt.js";
import { passwordView } from "./views/password.js";
import { personaView } from "./views/persona.js";
import { personasView } from "./views/personas.js";
import { usuariosView } from "./views/usuarios.js";

const routes = [
  { path: /^#\/login$/, view: loginView, public: true },
  { path: /^#\/cambiar-clave$/, view: passwordView },
  { path: /^#\/mi-deuda$/, view: myDebtView, role: "usuario" },
  { path: /^#\/admin$/, view: dashboardView, role: "admin" },
  { path: /^#\/admin\/personas$/, view: personasView, role: "admin" },
  { path: /^#\/admin\/personas\/(?<id>\d+)$/, view: personaView, role: "admin" },
  { path: /^#\/admin\/usuarios$/, view: usuariosView, role: "admin" },
];

const app = document.getElementById("app");
const navigate = (hash) => {
  if (location.hash === hash) render();
  else location.hash = hash;
};

function logout(message) {
  session.clear();
  if (message) toast(message, "info");
  navigate("#/login");
}
setUnauthorizedHandler(() => logout("Tu sesión expiró. Ingresa de nuevo."));

function home(user) {
  return user.role === "admin" ? "#/admin" : "#/mi-deuda";
}

function navbar(user) {
  const link = (href, label) => h("a", { href, class: location.hash.startsWith(href) && (href !== "#/admin" || location.hash === "#/admin") ? "active" : "" }, label);
  return h("header", { class: "topbar" },
    h("a", { class: "brand", href: "#/" }, h("img", { src: "/icon.svg", alt: "" }), h("span", {}, "Contabilidad")),
    h("nav", { class: "nav" },
      user.role === "admin"
        ? [link("#/admin", "Resumen"), link("#/admin/personas", "Personas"), link("#/admin/usuarios", "Cuentas")]
        : [link("#/mi-deuda", "Mi deuda")]),
    h("div", { class: "user-menu" },
      h("span", { class: "muted small" }, `@${user.username}`),
      h("a", { class: "btn btn-ghost btn-sm", href: "#/cambiar-clave" }, "Contraseña"),
      h("button", { class: "btn btn-ghost btn-sm", type: "button", onclick: () => logout() }, "Salir")));
}

let renderSeq = 0;
async function render() {
  const seq = ++renderSeq;
  const hash = location.hash || "#/";
  const user = session.user();

  if (!user && hash !== "#/login") return navigate("#/login");
  if (user && (hash === "#/" || hash === "#/login")) return navigate(user.debe_cambiar_password ? "#/cambiar-clave" : home(user));
  if (user?.debe_cambiar_password && hash !== "#/cambiar-clave") return navigate("#/cambiar-clave");

  const route = routes.find((r) => r.path.test(hash));
  if (!route || (route.role && user?.role !== route.role)) return navigate(user ? home(user) : "#/login");

  clear(app);
  const main = h("main", { class: route.public ? "main main-auth" : "main" });
  if (!route.public) app.append(navbar(user));
  app.append(main);
  main.append(h("div", { class: "loading" }, "Cargando…"));
  const content = h("div", { class: "page" });
  try {
    await route.view(content, { params: hash.match(route.path).groups || {}, navigate, rerender: render });
    if (seq !== renderSeq) return; // otra navegación empezó mientras cargaba
    main.replaceChildren(content);
  } catch (err) {
    if (seq !== renderSeq) return;
    if (err.status === 401) return;
    main.replaceChildren(h("div", { class: "card narrow" }, h("h2", {}, "No se pudo cargar"), h("p", {}, err.message),
      h("button", { class: "btn", type: "button", onclick: render }, "Reintentar")));
  }
}

window.addEventListener("hashchange", render);

// Revalidar la sesión guardada al abrir la página (p. ej. si el admin cerró la sesión).
(async () => {
  if (session.token()) {
    try {
      session.updateUser(await api.get("/auth/me"));
    } catch {
      /* el handler de 401 ya redirige */
    }
  }
  render();
})();
