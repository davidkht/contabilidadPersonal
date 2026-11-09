import { api } from "../api.js";
import { h, modal, showCredentials, toast } from "../dom.js";
import { fmtDate, fmtMoney } from "../format.js";
import { personaForm } from "./personaForm.js";

export async function personasView(root, { navigate }) {
  let personas = await api.get("/admin/personas");
  const search = h("input", { type: "search", placeholder: "Buscar por nombre o documento…", class: "search" });
  const onlyDebt = h("input", { type: "checkbox" });
  const tbody = h("tbody");
  const counter = h("span", { class: "muted" });

  const render = () => {
    const q = search.value.trim().toLocaleLowerCase();
    const rows = personas.filter((p) =>
      (!q || p.nombre_completo.toLocaleLowerCase().includes(q) || (p.documento || "").includes(q)) && (!onlyDebt.checked || p.saldo !== 0));
    counter.textContent = `${rows.length} de ${personas.length}`;
    tbody.replaceChildren(...rows.map((p) =>
      h("tr", { class: "clickable", onclick: () => navigate(`#/admin/personas/${p.id}`) },
        h("td", {}, h("strong", {}, p.nombre_completo), p.username && h("div", { class: "muted small" }, `@${p.username}`)),
        h("td", {}, p.telefono || "—"),
        h("td", {}, p.ultimo_movimiento ? fmtDate(p.ultimo_movimiento) : "—"),
        h("td", { class: "num" }, String(p.num_movimientos)),
        h("td", { class: `num ${p.saldo > 0 ? "neg" : p.saldo < 0 ? "pos" : ""}` }, fmtMoney(p.saldo)))));
  };
  search.addEventListener("input", render);
  onlyDebt.addEventListener("change", render);

  const crear = async () => {
    const result = await modal("Nueva persona", (close) => personaForm(null, (body) => api.post("/admin/personas", body), close));
    if (!result) return;
    toast(`${result.persona.nombre_completo} creada`, "success");
    if (result.credenciales) await showCredentials(result.credenciales);
    personas = await api.get("/admin/personas");
    render();
  };

  root.append(
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, "Personas"), counter),
      h("button", { class: "btn btn-primary", type: "button", onclick: crear }, "Nueva persona")),
    h("div", { class: "toolbar" }, search, h("label", { class: "check" }, onlyDebt, " Solo con saldo")),
    h("section", { class: "card flush" }, h("div", { class: "table-wrap" }, h("table", { class: "table" },
      h("thead", {}, h("tr", {}, h("th", {}, "Persona"), h("th", {}, "Teléfono"), h("th", {}, "Último movimiento"), h("th", { class: "num" }, "Movs."), h("th", { class: "num" }, "Saldo"))),
      tbody))),
  );
  render();
}
