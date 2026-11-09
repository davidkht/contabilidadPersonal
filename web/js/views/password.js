import { api } from "../api.js";
import { field, h, toast } from "../dom.js";
import { session } from "../session.js";

export function passwordView(root, { navigate }) {
  const forced = session.user()?.debe_cambiar_password;
  const current = h("input", { type: "password", autocomplete: "current-password", required: true });
  const next = h("input", { type: "password", autocomplete: "new-password", required: true, minlength: 10 });
  const repeat = h("input", { type: "password", autocomplete: "new-password", required: true });
  const error = h("p", { class: "form-error", role: "alert" });
  const form = h("form", { class: "card narrow" },
    h("h2", { class: "card-title" }, "Cambiar contraseña"),
    forced && h("p", { class: "notice" }, "Estás usando una contraseña temporal. Elige una nueva para continuar."),
    field("Contraseña actual", current),
    field("Nueva contraseña", next, "Mínimo 10 caracteres, combinando letras y números o símbolos."),
    field("Repite la nueva contraseña", repeat),
    error,
    h("div", { class: "form-actions" },
      !forced && h("button", { class: "btn", type: "button", onclick: () => history.back() }, "Cancelar"),
      h("button", { class: "btn btn-primary", type: "submit" }, "Guardar")));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    error.textContent = "";
    if (next.value !== repeat.value) {
      error.textContent = "Las contraseñas nuevas no coinciden";
      return;
    }
    try {
      const result = await api.post("/auth/change-password", { current_password: current.value, new_password: next.value });
      session.save(result);
      toast("Contraseña actualizada", "success");
      navigate("#/");
    } catch (err) {
      error.textContent = err.message;
    }
  });
  root.append(form);
}
