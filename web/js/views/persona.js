import { api } from "../api.js";
import { confirmDialog, field, h, modal, showCredentials, toast } from "../dom.js";
import { fmtMoney, todayISO } from "../format.js";
import { chartsSection, csvDownload, movimientosTable, summaryTiles } from "./debtPanel.js";
import { personaForm } from "./personaForm.js";

function movimientoForm(personaId, saldo, onSaved) {
  const tipo = h("select", {}, h("option", { value: "cargo" }, "Cargo — aumenta la deuda"), h("option", { value: "abono" }, "Abono — pago recibido"), h("option", { value: "ajuste" }, "Ajuste (con signo)"));
  const monto = h("input", { type: "number", min: "0", step: "0.01", required: true, inputmode: "decimal", placeholder: "0" });
  const fecha = h("input", { type: "date", value: todayISO(), max: todayISO(), required: true });
  const desc = h("input", { maxlength: 500, placeholder: "Ej. Pago Nequi, almuerzo…" });
  const preview = h("span", { class: "muted" });
  const error = h("p", { class: "form-error", role: "alert" });

  const signed = () => {
    const v = Number(monto.value || 0);
    return tipo.value === "abono" ? -Math.abs(v) : tipo.value === "cargo" ? Math.abs(v) : v;
  };
  const update = () => {
    monto.min = tipo.value === "ajuste" ? "" : "0";
    preview.textContent = `Saldo resultante: ${fmtMoney(saldo + signed())}`;
  };
  [tipo, monto].forEach((el) => el.addEventListener("input", update));
  update();

  const quick = (delta) => h("button", { class: "btn btn-sm", type: "button", onclick: () => { monto.value = String(Math.max(0, Number(monto.value || 0) + delta)); update(); } }, `${delta > 0 ? "+" : "−"}${Math.abs(delta) / 1000}k`);

  const form = h("form", { class: "card" },
    h("h3", { class: "card-title" }, "Registrar movimiento"),
    h("div", { class: "form-grid" },
      field("Tipo", tipo), field("Monto", monto),
      field("Fecha", fecha), field("Descripción", desc)),
    h("div", { class: "quick-row" }, quick(-10000), quick(10000), quick(50000), quick(100000), preview),
    error,
    h("div", { class: "form-actions" }, h("button", { class: "btn btn-primary", type: "submit" }, "Guardar movimiento")));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    error.textContent = "";
    const value = signed();
    if (!value) {
      error.textContent = "El monto no puede ser cero";
      return;
    }
    try {
      await api.post(`/admin/personas/${personaId}/movimientos`, { monto: value, descripcion: desc.value.trim(), fecha: fecha.value, tipo: tipo.value });
      toast("Movimiento registrado", "success");
      onSaved();
    } catch (err) {
      error.textContent = err.message;
    }
  });
  return form;
}

export async function personaView(root, { params, navigate, rerender }) {
  const id = Number(params.id);
  const [analitica, page, usuarios] = await Promise.all([
    api.get(`/admin/personas/${id}/analitica`, { meses: 12 }),
    api.getPage(`/admin/personas/${id}/movimientos`, { limit: 1000, orden: "desc" }),
    api.get("/admin/usuarios"),
  ]);
  const p = analitica.persona;
  const cuenta = usuarios.find((u) => u.persona_id === id);
  const items = page.data;

  const editar = async () => {
    const updated = await modal("Editar persona", (close) => personaForm(p, (body) => api.patch(`/admin/personas/${id}`, body), close));
    if (updated) {
      toast("Datos actualizados", "success");
      rerender();
    }
  };
  const borrar = async () => {
    const ok = await confirmDialog("Borrar persona", `Se eliminarán ${p.nombre_completo}, sus ${p.num_movimientos} movimientos y su cuenta de acceso. Esta acción no se puede deshacer.`, "Borrar definitivamente", true);
    if (!ok) return;
    try {
      await api.del(`/admin/personas/${id}`);
      toast("Persona eliminada", "success");
      navigate("#/admin/personas");
    } catch (err) {
      toast(err.message, "error");
    }
  };
  const borrarMov = async (m) => {
    const ok = await confirmDialog("Eliminar movimiento", `¿Eliminar "${m.descripcion || m.tipo}" por ${fmtMoney(m.monto)}?`, "Eliminar", true);
    if (!ok) return;
    try {
      await api.del(`/admin/personas/${id}/movimientos/${m.id}`);
      toast("Movimiento eliminado", "success");
      rerender();
    } catch (err) {
      toast(err.message, "error");
    }
  };
  const crearCuenta = async () => {
    try {
      const username = `${p.nombre}.${p.apellido}`.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, ".").replace(/[^a-zA-Z0-9.]/g, "").toLowerCase();
      const cred = await api.post("/admin/usuarios", { username, role: "usuario", persona_id: id });
      await showCredentials(cred);
      rerender();
    } catch (err) {
      toast(err.message, "error");
    }
  };
  const resetear = async () => {
    const ok = await confirmDialog("Restablecer contraseña", `Se generará una contraseña temporal nueva para @${cuenta.username} y se cerrarán sus sesiones.`, "Restablecer");
    if (!ok) return;
    try {
      await showCredentials(await api.post(`/admin/usuarios/${cuenta.id}/reset-password`));
    } catch (err) {
      toast(err.message, "error");
    }
  };

  const info = [
    p.documento && `Doc. ${p.documento}`, p.telefono, p.email,
    p.interes_mensual ? `Interés ${(p.interes_mensual * 100).toFixed(2)} % mensual` : null,
  ].filter(Boolean).join(" · ");

  root.append(
    h("a", { href: "#/admin/personas", class: "back" }, "← Personas"),
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, p.nombre_completo), h("p", { class: "muted" }, info || "Sin datos de contacto"),
        h("p", { class: "small" }, cuenta
          ? h("span", {}, `Cuenta: @${cuenta.username}${cuenta.activo ? "" : " (desactivada)"} · `, h("button", { class: "link", type: "button", onclick: resetear }, "restablecer contraseña"))
          : h("button", { class: "link", type: "button", onclick: crearCuenta }, "Crear cuenta de acceso"))),
      h("div", { class: "actions" },
        h("button", { class: "btn", type: "button", onclick: () => csvDownload(`${p.nombre}_${p.apellido}.csv`, items) }, "CSV"),
        h("button", { class: "btn", type: "button", onclick: editar }, "Editar"),
        h("button", { class: "btn btn-danger", type: "button", onclick: borrar }, "Borrar"))),
    summaryTiles(analitica.resumen),
    movimientoForm(id, analitica.resumen.saldo, rerender),
    chartsSection(analitica),
    h("section", { class: "card" }, h("h3", { class: "card-title" }, `Movimientos (${page.meta.page?.total ?? items.length})`), movimientosTable(items, { onDelete: borrarMov })),
  );
}
