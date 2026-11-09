import { api } from "../api.js";
import { confirmDialog, field, h, modal, showCredentials, toast } from "../dom.js";
import { fmtDate } from "../format.js";
import { session } from "../session.js";

export async function usuariosView(root, { rerender }) {
  const users = await api.get("/admin/usuarios");
  const me = session.user();

  const reset = async (u) => {
    if (!(await confirmDialog("Restablecer contraseña", `Nueva contraseña temporal para @${u.username}. Sus sesiones abiertas se cerrarán.`, "Restablecer"))) return;
    try {
      await showCredentials(await api.post(`/admin/usuarios/${u.id}/reset-password`));
      rerender();
    } catch (err) {
      toast(err.message, "error");
    }
  };
  const toggle = async (u) => {
    try {
      await api.patch(`/admin/usuarios/${u.id}`, { activo: !u.activo });
      toast(u.activo ? `@${u.username} desactivado` : `@${u.username} activado`, "success");
      rerender();
    } catch (err) {
      toast(err.message, "error");
    }
  };
  const nuevoAdmin = async () => {
    const cred = await modal("Nuevo administrador", (close) => {
      const username = h("input", { required: true, minlength: 3, maxlength: 60 });
      const error = h("p", { class: "form-error" });
      const form = h("form", { class: "modal-body" }, field("Usuario", username, "Minúsculas, números, '.', '_' o '-'"), error,
        h("div", { class: "form-actions" }, h("button", { class: "btn", type: "button", onclick: () => close(null) }, "Cancelar"), h("button", { class: "btn btn-primary", type: "submit" }, "Crear")));
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          close(await api.post("/admin/usuarios", { username: username.value.trim().toLowerCase(), role: "admin" }));
        } catch (err) {
          error.textContent = err.message;
        }
      });
      return form;
    });
    if (cred) {
      await showCredentials(cred);
      rerender();
    }
  };

  root.append(
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, "Cuentas de acceso"), h("p", { class: "muted" }, "Las cuentas de usuario se crean al crear una persona.")),
      h("button", { class: "btn", type: "button", onclick: nuevoAdmin }, "Nuevo administrador")),
    h("section", { class: "card flush" }, h("div", { class: "table-wrap" }, h("table", { class: "table" },
      h("thead", {}, h("tr", {}, h("th", {}, "Usuario"), h("th", {}, "Rol"), h("th", {}, "Persona"), h("th", {}, "Estado"), h("th", {}, "Último ingreso"), h("th", {}, ""))),
      h("tbody", {}, users.map((u) => h("tr", {},
        h("td", {}, h("strong", {}, `@${u.username}`)),
        h("td", {}, h("span", { class: `tag tag-${u.role}` }, u.role)),
        h("td", {}, u.persona_id ? h("a", { href: `#/admin/personas/${u.persona_id}` }, u.persona_nombre) : "—"),
        h("td", {}, !u.activo ? h("span", { class: "tag tag-off" }, "Desactivado") : u.bloqueado ? h("span", { class: "tag tag-warn" }, "Bloqueado") : u.debe_cambiar_password ? h("span", { class: "tag" }, "Clave temporal") : h("span", { class: "tag tag-ok" }, "Activo")),
        h("td", { class: "nowrap" }, u.ultimo_login ? fmtDate(u.ultimo_login) : "Nunca"),
        h("td", { class: "row-actions" },
          h("button", { class: "btn btn-sm", type: "button", onclick: () => reset(u) }, "Restablecer clave"),
          u.id !== me?.id && h("button", { class: "btn btn-sm btn-ghost", type: "button", onclick: () => toggle(u) }, u.activo ? "Desactivar" : "Activar")))))))),
  );
}
