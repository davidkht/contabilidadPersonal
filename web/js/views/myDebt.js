import { api } from "../api.js";
import { h } from "../dom.js";
import { chartsSection, csvDownload, movimientosTable, summaryTiles } from "./debtPanel.js";

export async function myDebtView(root) {
  const [analitica, page] = await Promise.all([
    api.get("/me/analitica", { meses: 12 }),
    api.getPage("/me/movimientos", { limit: 1000, orden: "desc" }),
  ]);
  const items = page.data;
  root.append(
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, `Hola, ${analitica.persona.nombre}`), h("p", { class: "muted" }, "Este es tu estado de cuenta.")),
      h("button", { class: "btn", type: "button", onclick: () => csvDownload("mis_movimientos.csv", items) }, "Descargar CSV")),
    summaryTiles(analitica.resumen, { perspective: "self" }),
    chartsSection(analitica),
    h("section", { class: "card" }, h("h3", { class: "card-title" }, `Movimientos (${page.meta.page?.total ?? items.length})`), movimientosTable(items)),
  );
}
