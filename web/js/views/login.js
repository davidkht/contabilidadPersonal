import { api } from "../api.js";
import { field, h } from "../dom.js";
import { session } from "../session.js";

export function loginView(root, { navigate }) {
  const user = h("input", { name: "username", autocomplete: "username", required: true, autofocus: true });
  const pass = h("input", { name: "password", type: "password", autocomplete: "current-password", required: true });
  const error = h("p", { class: "form-error", role: "alert" });
  const submit = h("button", { class: "btn btn-primary btn-block", type: "submit" }, "Ingresar");
  const form = h("form", { class: "auth-card card" },
    h("img", { src: "/icon.svg", alt: "", class: "auth-logo" }),
    h("h1", {}, "Contabilidad personal"),
    h("p", { class: "muted" }, "Ingresa con tu usuario para ver tu estado de cuenta."),
    field("Usuario", user), field("Contraseña", pass), error, submit);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    error.textContent = "";
    submit.disabled = true;
    try {
      const result = await api.login(user.value.trim(), pass.value);
      session.save(result);
      navigate(result.user.debe_cambiar_password ? "#/cambiar-clave" : "#/");
    } catch (err) {
      error.textContent = err.message;
      pass.value = "";
      pass.focus();
    } finally {
      submit.disabled = false;
    }
  });
  root.append(h("div", { class: "auth-wrap" }, form));
}
