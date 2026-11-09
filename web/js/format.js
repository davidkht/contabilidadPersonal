const money = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});
const compact = new Intl.NumberFormat("es-CO", { notation: "compact", maximumFractionDigits: 1 });
const dateFmt = new Intl.DateTimeFormat("es-CO", { day: "2-digit", month: "short", year: "numeric" });
const monthFmt = new Intl.DateTimeFormat("es-CO", { month: "short", year: "2-digit" });

export const fmtMoney = (v) => (v === null || v === undefined ? "—" : money.format(v));
export const fmtCompact = (v) => compact.format(v);
export const fmtSigned = (v) => (v > 0 ? "+" : "") + money.format(v);

export function parseDate(iso) {
  // "YYYY-MM-DD" como fecha local (evita desfase por zona horaria)
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d || 1);
}
export const fmtDate = (iso) => (iso ? dateFmt.format(parseDate(iso)) : "—");
export const fmtMonth = (ym) => monthFmt.format(parseDate(`${ym}-01`));

export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export const TIPO_LABEL = { cargo: "Cargo", abono: "Abono", interes: "Interés", ajuste: "Ajuste" };
