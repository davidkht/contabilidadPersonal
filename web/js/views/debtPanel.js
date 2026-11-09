// Panel reutilizable: resumen + gráficos + tabla de movimientos de una persona.
import { lineChart, monthlyChart } from "../charts.js";
import { h, stat } from "../dom.js";
import { fmtDate, fmtMoney, fmtSigned, TIPO_LABEL } from "../format.js";

export function saldoTone(saldo) {
  return saldo > 0 ? "warn" : saldo < 0 ? "good" : undefined;
}

export function summaryTiles(resumen, { perspective = "admin" } = {}) {
  const s = resumen.saldo;
  const saldoLabel =
    perspective === "self"
      ? s > 0 ? "Debes" : s < 0 ? "Saldo a tu favor" : "Estás al día"
      : s > 0 ? "Te debe" : s < 0 ? "Le debes" : "Al día";
  return h(
    "div",
    { class: "stats" },
    stat(saldoLabel, fmtMoney(Math.abs(s)), resumen.ultimo_movimiento ? `Último movimiento: ${fmtDate(resumen.ultimo_movimiento)}` : null, saldoTone(s)),
    stat("Total abonado", fmtMoney(resumen.total_abonos),
      resumen.ultimo_abono_fecha ? `Último: ${fmtMoney(resumen.ultimo_abono_monto)} · hace ${resumen.dias_desde_ultimo_abono} días` : "Sin abonos"),
    stat("Total cargado", fmtMoney(resumen.total_cargos),
      resumen.total_intereses ? `+ ${fmtMoney(resumen.total_intereses)} en intereses` : `${resumen.num_movimientos} movimientos`),
    stat("Abono promedio", resumen.promedio_abono == null ? "—" : fmtMoney(Math.round(resumen.promedio_abono)), resumen.primer_movimiento ? `Desde ${fmtDate(resumen.primer_movimiento)}` : null),
  );
}

export function chartsSection(analitica) {
  const line = h("div", { class: "chart-host" });
  const months = h("div", { class: "chart-host" });
  const section = h(
    "div",
    { class: "grid-2" },
    h("section", { class: "card" }, h("h3", { class: "card-title" }, "Evolución del saldo"), line),
    h("section", { class: "card" }, h("h3", { class: "card-title" }, "Cargos y abonos por mes"), months),
  );
  // dibujar cuando ya está en el DOM (para medir el ancho)
  requestAnimationFrame(() => {
    lineChart(line, analitica.serie_saldo);
    monthlyChart(months, analitica.mensual);
  });
  return section;
}

export function movimientosTable(items, { onDelete } = {}) {
  if (!items.length) return h("p", { class: "empty" }, "Sin movimientos.");
  return h(
    "div",
    { class: "table-wrap" },
    h(
      "table",
      { class: "table" },
      h("thead", {}, h("tr", {}, h("th", {}, "Fecha"), h("th", {}, "Descripción"), h("th", {}, "Tipo"),
        h("th", { class: "num" }, "Movimiento"), h("th", { class: "num" }, "Saldo"), onDelete && h("th", {}, ""))),
      h(
        "tbody",
        {},
        items.map((m) =>
          h("tr", {},
            h("td", { class: "nowrap" }, fmtDate(m.fecha)),
            h("td", {}, m.descripcion || h("span", { class: "muted" }, "—")),
            h("td", {}, h("span", { class: `tag tag-${m.tipo}` }, TIPO_LABEL[m.tipo] || m.tipo)),
            h("td", { class: `num ${m.monto < 0 ? "pos" : ""}` }, fmtSigned(m.monto)),
            h("td", { class: "num" }, fmtMoney(m.saldo)),
            onDelete && h("td", {}, h("button", { class: "btn btn-ghost btn-sm", type: "button", title: "Eliminar movimiento", onclick: () => onDelete(m) }, "Eliminar")),
          ),
        ),
      ),
    ),
  );
}

export function csvDownload(filename, items) {
  const rows = [["fecha", "descripcion", "tipo", "monto", "saldo"], ...items.map((m) => [m.fecha, m.descripcion, m.tipo, m.monto, m.saldo])];
  const csv = rows.map((r) => r.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
  const a = h("a", { href: url, download: filename });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
