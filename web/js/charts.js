// Gráficos SVG ligeros (sin dependencias). Colores vía variables CSS --series-1/--series-2.
import { h, svg } from "./dom.js";
import { fmtCompact, fmtDate, fmtMoney, fmtMonth, parseDate } from "./format.js";

const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function niceTicks(min, max, count = 5) {
  if (min === max) {
    max = min + 1;
  }
  const span = max - min;
  const step0 = span / count;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= step0) || step0;
  const lo = Math.floor(min / step) * step;
  const hi = Math.ceil(max / step) * step;
  const ticks = [];
  for (let v = lo; v <= hi + step / 2; v += step) ticks.push(Math.round(v * 100) / 100);
  return ticks;
}

function axisLabel(v) {
  return Math.abs(v) >= 10000 ? fmtCompact(v) : v.toLocaleString("es-CO");
}

function frame(container, { height = 260 } = {}) {
  const width = Math.max(container.clientWidth || 600, 280);
  const m = { top: 12, right: 16, bottom: 28, left: 56 };
  const root = h("div", { class: "chart" });
  const tip = h("div", { class: "chart-tip hidden", role: "status" });
  const el = svg("svg", { viewBox: `0 0 ${width} ${height}`, width: "100%", height, role: "img" });
  root.append(el, tip);
  container.append(root);
  return { root, el, tip, width, height, m, iw: width - m.left - m.right, ih: height - m.top - m.bottom };
}

function yAxis(f, ticks, y) {
  const g = svg("g", { class: "axis" });
  for (const t of ticks) {
    const yy = y(t);
    g.append(
      svg("line", { x1: f.m.left, x2: f.width - f.m.right, y1: yy, y2: yy, class: t === 0 ? "zero" : "grid" }),
      svg("text", { x: f.m.left - 8, y: yy + 4, "text-anchor": "end" }, axisLabel(t)),
    );
  }
  f.el.append(g);
}

function showTip(f, x, y, lines) {
  f.tip.replaceChildren(...lines.map((l) => (l instanceof Node ? l : h("div", {}, l))));
  f.tip.classList.remove("hidden");
  const tw = f.tip.offsetWidth;
  const scale = f.root.clientWidth / f.width;
  let left = x * scale + 12;
  if (left + tw > f.root.clientWidth) left = x * scale - tw - 12;
  f.tip.style.left = `${Math.max(0, left)}px`;
  f.tip.style.top = `${Math.max(0, y * scale - 10)}px`;
}
const hideTip = (f) => f.tip.classList.add("hidden");

function keyed(color, label, value) {
  return h("div", { class: "tip-row" }, h("span", { class: `key key-${color}` }), h("span", {}, label), h("strong", {}, value));
}

/** Línea de saldo en el tiempo (escalonada: el saldo se mantiene hasta el siguiente movimiento). */
export function lineChart(container, points, { label = "Saldo" } = {}) {
  if (!points.length) {
    container.append(h("p", { class: "empty" }, "Sin movimientos todavía."));
    return;
  }
  const f = frame(container);
  const xs = points.map((p) => parseDate(p.fecha).getTime());
  const now = Date.now();
  const x0 = Math.min(...xs);
  const x1 = Math.max(now, ...xs);
  const vals = points.map((p) => p.saldo);
  const ticks = niceTicks(Math.min(0, ...vals), Math.max(0, ...vals));
  const ymin = ticks[0];
  const ymax = ticks.at(-1);
  const x = (t) => f.m.left + (x1 === x0 ? f.iw / 2 : ((t - x0) / (x1 - x0)) * f.iw);
  const y = (v) => f.m.top + f.ih - ((v - ymin) / (ymax - ymin)) * f.ih;
  yAxis(f, ticks, y);

  // eje X: ~5 fechas
  const gx = svg("g", { class: "axis" });
  for (let i = 0; i <= 4; i++) {
    const t = x0 + ((x1 - x0) * i) / 4;
    const d = new Date(t);
    gx.append(svg("text", { x: x(t), y: f.height - 8, "text-anchor": i === 0 ? "start" : i === 4 ? "end" : "middle" },
      d.toLocaleDateString("es-CO", { month: "short", year: "2-digit" })));
  }
  f.el.append(gx);

  let d = "";
  points.forEach((p, i) => {
    const px = x(xs[i]);
    const py = y(p.saldo);
    d += i === 0 ? `M${px},${py}` : `H${px}V${py}`;
  });
  d += `H${x(x1)}`;
  const base = y(Math.max(ymin, Math.min(0, ymax)));
  f.el.append(
    svg("path", { d: `${d}V${base}H${x(xs[0])}Z`, class: "area s1" }),
    svg("path", { d, class: "line s1" }),
    svg("circle", { cx: x(x1), cy: y(vals.at(-1)), r: 4, class: "dot s1" }),
  );

  // hover: crosshair
  const cross = svg("line", { class: "crosshair hidden", y1: f.m.top, y2: f.m.top + f.ih });
  const hoverDot = svg("circle", { r: 5, class: "dot s1 hidden" });
  const hit = svg("rect", { x: f.m.left, y: f.m.top, width: f.iw, height: f.ih, class: "hit" });
  f.el.append(cross, hoverDot, hit);
  const move = (evt) => {
    const rect = f.el.getBoundingClientRect();
    const mx = ((evt.clientX - rect.left) / rect.width) * f.width;
    const t = x0 + ((mx - f.m.left) / f.iw) * (x1 - x0);
    let idx = 0;
    for (let i = 0; i < xs.length; i++) if (xs[i] <= t) idx = i;
    const p = points[idx];
    cross.setAttribute("x1", mx);
    cross.setAttribute("x2", mx);
    hoverDot.setAttribute("cx", x(xs[idx]));
    hoverDot.setAttribute("cy", y(p.saldo));
    cross.classList.remove("hidden");
    hoverDot.classList.remove("hidden");
    showTip(f, mx, y(p.saldo), [h("div", { class: "tip-title" }, fmtDate(p.fecha)), keyed("s1", label, fmtMoney(p.saldo))]);
  };
  hit.addEventListener("pointermove", move);
  hit.addEventListener("pointerleave", () => {
    cross.classList.add("hidden");
    hoverDot.classList.add("hidden");
    hideTip(f);
  });
}

/** Columnas agrupadas por mes: cargos (s1) vs abonos (s2). */
export function monthlyChart(container, months) {
  const legend = h("div", { class: "legend" },
    h("span", {}, h("span", { class: "key key-s1" }), "Cargos (aumenta deuda)"),
    h("span", {}, h("span", { class: "key key-s2" }), "Abonos (pagos)"));
  container.append(legend);
  const f = frame(container, { height: 240 });
  f.m.bottom = 34;
  f.ih = f.height - f.m.top - f.m.bottom;
  const maxV = Math.max(1, ...months.flatMap((m) => [m.cargos, m.abonos]));
  const ticks = niceTicks(0, maxV, 4);
  const ymax = ticks.at(-1);
  const y = (v) => f.m.top + f.ih - (v / ymax) * f.ih;
  yAxis(f, ticks, y);
  const band = f.iw / months.length;
  const bw = Math.min(16, (band - 8) / 2);
  const g = svg("g");
  months.forEach((m, i) => {
    const cx = f.m.left + band * i + band / 2;
    for (const [key, v, dx] of [["s1", m.cargos, -bw - 1], ["s2", m.abonos, 1]]) {
      if (v <= 0) continue;
      const top = y(v);
      const hgt = f.m.top + f.ih - top;
      const r = Math.min(4, hgt, bw / 2);
      const x0 = cx + dx;
      // esquina redondeada solo en el extremo de datos
      g.append(svg("path", {
        class: `bar ${key}`,
        d: `M${x0},${top + hgt}V${top + r}Q${x0},${top} ${x0 + r},${top}H${x0 + bw - r}Q${x0 + bw},${top} ${x0 + bw},${top + r}V${top + hgt}Z`,
      }));
    }
    // Mes abreviado; el año solo en el primer mes y en enero (evita etiquetas largas solapadas)
    const [yy, mm] = m.mes.split("-");
    const label = svg("text", { class: "axis-x", x: cx, y: f.height - 16, "text-anchor": "middle" }, MONTHS[Number(mm) - 1]);
    if (i === 0 || mm === "01") label.append(svg("tspan", { x: cx, dy: 12 }, yy));
    if (band >= 26 || i % 2 === 0) g.append(label);
    const hit = svg("rect", { class: "hit", x: cx - band / 2, y: f.m.top, width: band, height: f.ih });
    hit.addEventListener("pointermove", () =>
      showTip(f, cx, f.m.top + 20, [
        h("div", { class: "tip-title" }, fmtMonth(m.mes)),
        keyed("s1", "Cargos", fmtMoney(m.cargos)),
        keyed("s2", "Abonos", fmtMoney(m.abonos)),
        h("div", { class: "tip-row muted" }, `Saldo al cierre: ${fmtMoney(m.saldo_fin)}`),
      ]));
    hit.addEventListener("pointerleave", () => hideTip(f));
    g.append(hit);
  });
  f.el.append(g);
}

/** Barras horizontales (ranking). items: [{label, value, onClick}] */
export function barList(container, items) {
  if (!items.length) {
    container.append(h("p", { class: "empty" }, "Nadie tiene deuda pendiente. 🎉"));
    return;
  }
  const max = Math.max(...items.map((i) => i.value));
  const list = h("ol", { class: "barlist" });
  for (const it of items) {
    const fill = h("span", { class: "barlist-fill" });
    fill.style.width = `${Math.max(2, (it.value / max) * 100)}%`;
    list.append(
      h("li", {},
        h(it.onClick ? "button" : "span", { class: "barlist-label", type: it.onClick ? "button" : undefined, onclick: it.onClick }, it.label),
        h("span", { class: "barlist-track" }, fill),
        h("span", { class: "barlist-value" }, fmtMoney(it.value))),
    );
  }
  container.append(list);
}
