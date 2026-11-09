import { field, h } from "../dom.js";

/** Formulario de persona. `initial` = persona existente (edición) o null (alta). */
export function personaForm(initial, onSubmit, close) {
  const v = (k) => initial?.[k] ?? "";
  const inputs = {
    nombre: h("input", { value: v("nombre"), required: true, maxlength: 80 }),
    apellido: h("input", { value: v("apellido"), required: true, maxlength: 80 }),
    documento: h("input", { value: v("documento"), maxlength: 40 }),
    telefono: h("input", { value: v("telefono"), maxlength: 40, inputmode: "tel" }),
    email: h("input", { value: v("email"), maxlength: 120, type: "email" }),
    interes: h("input", { value: initial ? String(Math.round(initial.interes_mensual * 10000) / 100) : "0", type: "number", min: 0, max: 100, step: "0.01" }),
    descripcion: h("textarea", { rows: 2, maxlength: 500 }, v("descripcion")),
  };
  const extra = {};
  if (!initial) {
    extra.monto = h("input", { value: "0", type: "number", step: "0.01" });
    extra.crearUsuario = h("input", { type: "checkbox", checked: true });
    extra.username = h("input", { placeholder: "automático (nombre.apellido)", maxlength: 60 });
  }
  const error = h("p", { class: "form-error", role: "alert" });
  const form = h("form", { class: "modal-body form-grid" },
    field("Nombre", inputs.nombre), field("Apellido", inputs.apellido),
    field("Documento", inputs.documento), field("Teléfono", inputs.telefono),
    field("Email", inputs.email), field("Interés mensual (%)", inputs.interes, "0 = sin intereses"),
    h("div", { class: "full" }, field("Descripción", inputs.descripcion)),
    !initial && field("Deuda inicial", extra.monto, "Positivo: te debe. Negativo: le debes."),
    !initial && field("Usuario (opcional)", extra.username),
    !initial && h("label", { class: "check full" }, extra.crearUsuario, " Crear cuenta de acceso con contraseña temporal"),
    h("div", { class: "full" }, error),
    h("div", { class: "form-actions full" },
      h("button", { class: "btn", type: "button", onclick: () => close(null) }, "Cancelar"),
      h("button", { class: "btn btn-primary", type: "submit" }, initial ? "Guardar cambios" : "Crear persona")));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    error.textContent = "";
    const opt = (el) => (el.value.trim() === "" ? null : el.value.trim());
    const body = {
      nombre: inputs.nombre.value.trim(),
      apellido: inputs.apellido.value.trim(),
      documento: opt(inputs.documento),
      telefono: opt(inputs.telefono),
      email: opt(inputs.email),
      interes_mensual: Number(inputs.interes.value || 0) / 100,
      descripcion: opt(inputs.descripcion),
    };
    if (!initial) {
      body.monto_inicial = Number(extra.monto.value || 0);
      body.crear_usuario = extra.crearUsuario.checked;
      if (opt(extra.username)) body.username = opt(extra.username);
    }
    try {
      close(await onSubmit(body));
    } catch (err) {
      error.textContent = err.message;
    }
  });
  return form;
}
