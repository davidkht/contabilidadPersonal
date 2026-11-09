// Mini helper para construir DOM sin innerHTML (evita XSS con datos del servidor).
export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "dataset") Object.assign(el.dataset, v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}

export function svg(tag, attrs = {}, ...children) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== undefined && v !== null) el.setAttribute(k, v);
  append(el, children);
  return el;
}

export function clear(el) {
  while (el.firstChild) el.firstChild.remove();
  return el;
}

let toastTimer;
export function toast(msg, kind = "info") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = `toast toast-${kind}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.className = "toast hidden"), 4500);
}

export function field(label, input, hint) {
  return h("label", { class: "field" }, h("span", { class: "field-label" }, label), input, hint && h("span", { class: "field-hint" }, hint));
}

export function stat(label, value, sub, tone) {
  return h(
    "div",
    { class: `stat${tone ? ` stat-${tone}` : ""}` },
    h("span", { class: "stat-label" }, label),
    h("span", { class: "stat-value" }, value),
    sub && h("span", { class: "stat-sub" }, sub),
  );
}

/** Diálogo modal. `build(close)` devuelve el contenido; resuelve con lo que se pase a close(). */
export function modal(title, build) {
  return new Promise((resolve) => {
    const dlg = h("dialog", { class: "modal" });
    const close = (value) => {
      dlg.close();
      dlg.remove();
      resolve(value);
    };
    dlg.append(
      h("div", { class: "modal-head" }, h("h2", {}, title), h("button", { class: "btn btn-ghost btn-icon", type: "button", "aria-label": "Cerrar", onclick: () => close(null) }, "✕")),
      build(close),
    );
    dlg.addEventListener("cancel", (e) => {
      e.preventDefault();
      close(null);
    });
    document.body.append(dlg);
    dlg.showModal();
  });
}

export function confirmDialog(title, message, confirmLabel = "Confirmar", danger = false) {
  return modal(title, (close) =>
    h(
      "div",
      { class: "modal-body" },
      h("p", {}, message),
      h(
        "div",
        { class: "form-actions" },
        h("button", { class: "btn", type: "button", onclick: () => close(false) }, "Cancelar"),
        h("button", { class: `btn ${danger ? "btn-danger" : "btn-primary"}`, type: "button", onclick: () => close(true) }, confirmLabel),
      ),
    ),
  );
}

export function showCredentials(cred, intro) {
  return modal("Credenciales", (close) => {
    const text = `Usuario: ${cred.username}\nContraseña temporal: ${cred.password_temporal}`;
    return h(
      "div",
      { class: "modal-body" },
      h("p", {}, intro || "Compártelas con la persona. Solo se muestran esta vez; se le pedirá cambiar la contraseña al ingresar."),
      h("pre", { class: "credentials" }, text),
      h(
        "div",
        { class: "form-actions" },
        h("button", {
          class: "btn",
          type: "button",
          onclick: async (e) => {
            try {
              await navigator.clipboard.writeText(text);
              e.target.textContent = "Copiado ✓";
            } catch {
              e.target.textContent = "Copia manualmente";
            }
          },
        }, "Copiar"),
        h("button", { class: "btn btn-primary", type: "button", onclick: () => close(true) }, "Listo"),
      ),
    );
  });
}
