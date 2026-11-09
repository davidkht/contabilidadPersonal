import { api } from "../api.js";
import { barList, monthlyChart } from "../charts.js";
import { confirmDialog, h, stat, toast } from "../dom.js";
import { fmtDate, fmtMoney, fmtSigned, TIPO_LABEL } from "../format.js";

export async function dashboardView(root, { navigate, rerender }) {
  const d = await api.get("/admin/dashboard", { meses: 12, top: 6, recientes: 10 });
  const top = h("div");
  const months = h("div", { class: "chart-host" });

  const aplicar = async () => {
    const ok = await confirmDialog("Aplicar intereses",
      "Se cobrará el interés mensual a las personas con tasa > 0 y sin movimientos en los últimos 30 días. ¿Continuar?", "Aplicar");
    if (!ok) return;
    try {
      const r = await api.post("/admin/intereses/aplicar", {});
      toast(r.aplicados.length ? `Intereses aplicados a ${r.aplicados.length} persona(s)` : "No había intereses por aplicar", "success");
      rerender();
    } catch (err) {
      toast(err.message, "error");
    }
  };

  root.append(
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, "Resumen"), h("p", { class: "muted" }, "Estado general de las cuentas por cobrar.")),
      h("div", { class: "actions" },
        h("button", { class: "btn", type: "button", onclick: aplicar }, "Aplicar intereses"),
        h("a", { class: "btn btn-primary", href: "#/admin/personas" }, "Ver personas"))),
    h("div", { class: "stats" },
      stat("Por cobrar", fmtMoney(d.total_por_cobrar), `${d.personas_con_deuda} de ${d.personas_total} personas con deuda`, "warn"),
      stat("Cobrado (30 días)", fmtMoney(d.cobrado_ultimos_30d), null, "good"),
      stat("Prestado (30 días)", fmtMoney(d.prestado_ultimos_30d)),
      stat("Saldo a favor de otros", fmtMoney(d.total_a_favor_de_otros), "Lo que tú les debes")),
    h("div", { class: "grid-2" },
      h("section", { class: "card" }, h("h3", { class: "card-title" }, "Cargos y abonos por mes (todas las personas)"), months),
      h("section", { class: "card" }, h("h3", { class: "card-title" }, "Mayores saldos pendientes"), top)),
    h("section", { class: "card" }, h("h3", { class: "card-title" }, "Movimientos recientes"),
      d.recientes.length
        ? h("div", { class: "table-wrap" }, h("table", { class: "table" },
            h("thead", {}, h("tr", {}, h("th", {}, "Fecha"), h("th", {}, "Persona"), h("th", {}, "Descripción"), h("th", {}, "Tipo"), h("th", { class: "num" }, "Monto"))),
            h("tbody", {}, d.recientes.map((m) => h("tr", { class: "clickable", onclick: () => navigate(`#/admin/personas/${m.persona_id}`) },
              h("td", { class: "nowrap" }, fmtDate(m.fecha)), h("td", {}, m.persona_nombre), h("td", {}, m.descripcion || "—"),
              h("td", {}, h("span", { class: `tag tag-${m.tipo}` }, TIPO_LABEL[m.tipo])),
              h("td", { class: `num ${m.monto < 0 ? "pos" : ""}` }, fmtSigned(m.monto)))))))
        : h("p", { class: "empty" }, "Sin movimientos.")),
  );
  requestAnimationFrame(() => {
    monthlyChart(months, d.mensual);
    barList(top, d.top_deudores.map((p) => ({ label: p.nombre_completo, value: p.saldo, onClick: () => navigate(`#/admin/personas/${p.id}`) })));
  });
}
