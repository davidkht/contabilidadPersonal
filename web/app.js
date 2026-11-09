/**
 * Contabilidad web — replica de la lógica de src/main.py + flujos de gui.py
 * Requiere sql.js (SQLite en WASM) y Chart.js (gráfico).
 */

(function () {
  "use strict";

  /** @type {import("sql.js").Database | null} */
  let db = null;
  let SQL = null;

  /** Fila seleccionada en Deudas (objeto con claves de columnas) */
  let selected = null;

  /** Contexto vista movimiento / detalles */
  let ctxNombre = "";
  let ctxApellido = "";

  /** @type {import("chart.js").Chart | null} */
  let chartInstance = null;

  const $ = (id) => document.getElementById(id);

  function toast(msg, type = "info") {
    const el = $("toast");
    el.textContent = msg;
    el.classList.remove("hidden", "success", "error");
    if (type === "success") el.classList.add("success");
    if (type === "error") el.classList.add("error");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.add("hidden"), 4200);
  }

  function todayISO() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  /** Nombre de tabla por persona: mismo criterio que Python */
  function personTableRaw(nombre, apellido) {
    return `${nombre}_${apellido}`.replace(/ /g, "_");
  }

  /** Identificador SQL citado para tablas dinámicas */
  function quoteIdent(name) {
    return '"' + String(name).replace(/"/g, '""') + '"';
  }

  function personTableQuoted(nombre, apellido) {
    return quoteIdent(personTableRaw(nombre, apellido));
  }

  function queryAll(sql, params = []) {
    const stmt = db.prepare(sql);
    if (params && params.length) stmt.bind(params);
    const rows = [];
    while (stmt.step()) {
      rows.push(stmt.getAsObject());
    }
    stmt.free();
    return rows;
  }

  function run(sql, params) {
    if (params && params.length) db.run(sql, params);
    else db.run(sql);
  }

  function ensureMainSchema() {
    run(`
      CREATE TABLE IF NOT EXISTS Deudas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL COLLATE NOCASE,
        apellido TEXT NOT NULL COLLATE NOCASE,
        documento TEXT,
        telefono TEXT,
        email TEXT,
        monto REAL NOT NULL,
        interes REAL DEFAULT 0,
        fecha DATE NOT NULL,
        descripcion TEXT,
        UNIQUE(nombre, apellido)
      )
    `);
  }

  function crearTablaPersona(nombre, apellido) {
    const q = personTableQuoted(nombre, apellido);
    run(`
      CREATE TABLE IF NOT EXISTS ${q} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deuda_total REAL NOT NULL,
        transaccion REAL NOT NULL,
        fecha DATE NOT NULL,
        descripcion TEXT
      )
    `);
  }

  function consultarDeudas() {
    return queryAll(`
      SELECT id, nombre, apellido, documento, telefono, email, monto, interes, fecha
      FROM Deudas
      ORDER BY id
    `);
  }

  function consultarTablaPersona(nombre, apellido) {
    const q = personTableQuoted(nombre, apellido);
    return queryAll(`SELECT * FROM ${q} ORDER BY id`);
  }

  function registrarPersona(
    nombre,
    apellido,
    telefono,
    email,
    monto,
    interes,
    descripcion,
    documento
  ) {
    const fecha = todayISO();
    run(
      `
      INSERT INTO Deudas (nombre, apellido, documento, telefono, email, monto, interes, fecha, descripcion)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `,
      [nombre, apellido, documento || null, telefono, email, monto, interes, fecha, descripcion || ""]
    );
    crearTablaPersona(nombre, apellido);
    const q = personTableQuoted(nombre, apellido);
    run(
      `
      INSERT INTO ${q} (deuda_total, transaccion, fecha, descripcion)
      VALUES (?, ?, ?, ?)
    `,
      [monto, monto, fecha, descripcion || ""]
    );
  }

  function actualizarDeuda(nombre, apellido, deudaTotal, transaccion, descripcion) {
    const fecha = todayISO();
    run(
      `
      UPDATE Deudas SET monto = monto + ? WHERE nombre = ? AND apellido = ?
    `,
      [transaccion, nombre, apellido]
    );
    const q = personTableQuoted(nombre, apellido);
    run(
      `
      INSERT INTO ${q} (deuda_total, transaccion, fecha, descripcion)
      VALUES (?, ?, ?, ?)
    `,
      [deudaTotal, transaccion, fecha, descripcion || ""]
    );
  }

  function editarRegistro(nombre, apellido, telefono, email, documento) {
    run(
      `
      UPDATE Deudas SET telefono = ?, email = ?, documento = ? WHERE nombre = ? AND apellido = ?
    `,
      [telefono, email, documento || "", nombre, apellido]
    );
  }

  function borrarUsuario(nombre, apellido) {
    run(`DELETE FROM Deudas WHERE nombre = ? AND apellido = ?`, [nombre, apellido]);
    const q = personTableQuoted(nombre, apellido);
    run(`DROP TABLE IF EXISTS ${q}`);
  }

  /**
   * Replica verificar_y_calcular_intereses() de main.py
   */
  function verificarYCalcularIntereses() {
    const rows = queryAll(
      `SELECT nombre, apellido, monto, interes FROM Deudas WHERE interes > 0`
    );
    const now = new Date();
    for (const r of rows) {
      const nombre = r.nombre;
      const apellido = r.apellido;
      const interes = Number(r.interes);
      const qtbl = personTableQuoted(nombre, apellido);
      const ult = queryAll(
        `SELECT fecha, deuda_total FROM ${qtbl} ORDER BY fecha DESC LIMIT 1`
      );
      if (!ult.length) continue;
      let fechaUlt = ult[0].fecha;
      const deudaTotal = Number(ult[0].deuda_total);
      const fechaUltimoMovimiento = new Date(fechaUlt + "T12:00:00");
      const diffDays = Math.floor((now - fechaUltimoMovimiento) / 86400000);
      if (diffDays < 30) continue;
      const meses =
        (now.getFullYear() - fechaUltimoMovimiento.getFullYear()) * 12 +
        (now.getMonth() - fechaUltimoMovimiento.getMonth());
      if (meses > 0) {
        const interesCalculado = deudaTotal * interes * meses;
        actualizarDeuda(
          nombre,
          apellido,
          deudaTotal + interesCalculado,
          interesCalculado,
          "Interés acumulado"
        );
      }
    }
  }

  function formatMoney(n) {
    const x = Number(n);
    if (Number.isNaN(x)) return n;
    return (
      "$" +
      x.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    );
  }

  function parseMoneyDisplay(s) {
    if (s == null || s === "") return 0;
    if (typeof s === "number") return s;
    const t = String(s).replace(/[$,\s]/g, "");
    const v = parseFloat(t);
    return Number.isNaN(v) ? 0 : v;
  }

  function parseDecimalInput(s) {
    if (s == null || String(s).trim() === "") return null;
    const v = parseFloat(String(s).replace(",", "."));
    return Number.isNaN(v) ? null : v;
  }

  /** CSV escape */
  function csvEscape(field) {
    const s = field == null ? "" : String(field);
    if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  }

  function rowsToCsv(objects) {
    if (!objects.length) return "";
    const cols = Object.keys(objects[0]);
    const lines = [cols.join(",")];
    for (const o of objects) {
      lines.push(cols.map((c) => csvEscape(o[c])).join(","));
    }
    return lines.join("\r\n");
  }

  function downloadText(filename, text, mime) {
    const blob = new Blob([text], { type: mime || "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function downloadBuffer(filename, u8) {
    const blob = new Blob([u8], { type: "application/x-sqlite3" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function renderDeudasTable() {
    const tbody = $("tbody-deudas");
    tbody.innerHTML = "";
    const keepId = selected ? selected.id : null;
    const rows = consultarDeudas();
    for (const r of rows) {
      const tr = document.createElement("tr");
      tr.dataset.id = String(r.id);
      const vals = [
        r.id,
        r.nombre,
        r.apellido,
        r.documento ?? "",
        r.telefono ?? "",
        r.email ?? "",
        formatMoney(r.monto),
        r.interes ?? 0,
        r.fecha ?? "",
      ];
      vals.forEach((cell) => {
        const td = document.createElement("td");
        td.textContent = cell === null || cell === undefined ? "" : String(cell);
        tr.appendChild(td);
      });
      tr.addEventListener("click", () => {
        tbody.querySelectorAll("tr").forEach((x) => x.classList.remove("selected"));
        tr.classList.add("selected");
        selected = { ...r };
      });
      if (keepId != null && Number(r.id) === Number(keepId)) {
        tr.classList.add("selected");
        selected = { ...r };
      }
      tbody.appendChild(tr);
    }
    if (keepId != null && !rows.some((r) => Number(r.id) === Number(keepId))) {
      selected = null;
    }
  }

  function renderMovTable(nombre, apellido) {
    const tbody = $("tbody-mov");
    tbody.innerHTML = "";
    const rows = consultarTablaPersona(nombre, apellido);
    for (const r of rows) {
      const tr = document.createElement("tr");
      const vals = [
        r.id,
        formatMoney(r.deuda_total),
        formatMoney(r.transaccion),
        r.fecha,
        (r.descripcion || "").replace(/\s+$/g, ""),
      ];
      vals.forEach((c) => {
        const td = document.createElement("td");
        td.textContent = c;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    }
  }

  function renderDetTable(nombre, apellido) {
    const tbody = $("tbody-det");
    tbody.innerHTML = "";
    const rows = consultarTablaPersona(nombre, apellido);
    for (const r of rows) {
      const tr = document.createElement("tr");
      [
        r.id,
        formatMoney(r.deuda_total),
        formatMoney(r.transaccion),
        r.fecha,
        (r.descripcion || "").replace(/\s+$/g, ""),
      ].forEach((c) => {
        const td = document.createElement("td");
        td.textContent = c;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    }
  }

  function destroyChart() {
    if (chartInstance) {
      chartInstance.destroy();
      chartInstance = null;
    }
  }

  function buildDebtChart(nombre, apellido) {
    destroyChart();
    if (typeof Chart === "undefined") {
      toast("Chart.js no está disponible; no se puede dibujar el gráfico.", "error");
      return;
    }
    const rows = consultarTablaPersona(nombre, apellido).sort((a, b) => a.id - b.id);
    const labels = rows.map((r) => String(r.id));
    const data = rows.map((r) => Number(r.deuda_total));
    const canvas = $("chart-deuda");
    const ctx = canvas.getContext("2d");
    chartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Total Debt",
            data,
            borderColor: "red",
            backgroundColor: "rgba(255,0,0,0.2)",
            pointStyle: "rect",
            pointRadius: 2,
            borderWidth: 1,
            tension: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          title: { display: true, text: "Debt History" },
        },
        scales: {
          x: {
            title: { display: true, text: "Transaction Number" },
            ticks: { maxTicksLimit: 12 },
          },
          y: {
            title: { display: true, text: "Total Debt" },
            ticks: {
              callback: (v) =>
                "$" + Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 }),
            },
          },
        },
      },
    });
  }

  function showView(name) {
    document.querySelectorAll(".view").forEach((v) => {
      v.classList.toggle("view-active", v.id === "view-" + name);
    });
  }

  function openOverlay(id, open) {
    const el = $(id);
    el.classList.toggle("hidden", !open);
    el.setAttribute("aria-hidden", open ? "false" : "true");
  }

  function confirmDialog(message) {
    return new Promise((resolve) => {
      const dlg = $("dialog-confirm");
      $("dialog-confirm-msg").textContent = message;
      dlg.returnValue = "";
      function onClose() {
        dlg.removeEventListener("close", onClose);
        resolve(dlg.returnValue === "yes");
      }
      dlg.addEventListener("close", onClose);
      dlg.showModal();
    });
  }

  function initEmptyDatabase() {
    db = new SQL.Database();
    ensureMainSchema();
    verificarYCalcularIntereses();
    renderDeudasTable();
    toast("Base nueva en memoria. Use «Guardar .db» para descargarla.", "success");
  }

  async function loadSqlJs() {
    if (typeof initSqlJs !== "function") {
      throw new Error("sql.js no cargó (initSqlJs). Revise la red o el CDN.");
    }
    SQL = await initSqlJs({
      locateFile: (file) =>
        `https://cdn.jsdelivr.net/npm/sql.js@1.10.3/dist/${file}`,
    });
  }

  function attachDbHandlers() {
    $("file-db").addEventListener("change", (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const u8 = new Uint8Array(reader.result);
          if (db) {
            try {
              db.close();
            } catch (_) {}
          }
          db = new SQL.Database(u8);
          ensureMainSchema();
          verificarYCalcularIntereses();
          selected = null;
          renderDeudasTable();
          showView("home");
          toast("Base de datos cargada.", "success");
        } catch (err) {
          console.error(err);
          toast("No se pudo abrir el archivo SQLite.", "error");
        }
        e.target.value = "";
      };
      reader.readAsArrayBuffer(f);
    });

    $("btn-save-db").addEventListener("click", () => {
      if (!db) return toast("No hay base cargada.", "error");
      const data = db.export();
      downloadBuffer("deudas.db", data);
      toast("Archivo deudas.db descargado.", "success");
    });
  }

  function attachHomeHandlers() {
    $("btn-home").addEventListener("click", () => {
      showView("home");
      destroyChart();
    });

    $("btn-nuevo").addEventListener("click", () => {
      $("form-nuevo").reset();
      openOverlay("overlay-nuevo", true);
    });

    $("btn-borrar").addEventListener("click", async () => {
      if (!selected) return toast("Seleccione un registro.", "error");
      const ok = await confirmDialog("¿Está seguro de borrar el registro?");
      if (!ok) return;
      borrarUsuario(selected.nombre, selected.apellido);
      selected = null;
      renderDeudasTable();
      toast("Registro eliminado.", "success");
    });

    $("btn-editar").addEventListener("click", () => {
      if (!selected) return toast("Seleccione un registro.", "error");
      $("editar-nombre-display").textContent = `${selected.nombre} ${selected.apellido}`;
      $("editar-documento").value = selected.documento ?? "";
      $("editar-tel").value = selected.telefono ?? "";
      $("editar-email").value = selected.email ?? "";
      openOverlay("overlay-editar", true);
    });

    $("btn-movimiento").addEventListener("click", () => {
      if (!selected) return toast("Seleccione un registro.", "error");
      ctxNombre = selected.nombre;
      ctxApellido = selected.apellido;
      $("mov-person-title").textContent = `${ctxNombre} ${ctxApellido}`.toUpperCase();
      const monto = parseMoneyDisplay(selected.monto);
      $("mov-deuda-actual").value = formatMoney(monto);
      $("mov-importe").value = "";
      $("mov-deuda-nueva").value = formatMoney(monto);
      $("mov-desc").value = "";
      renderMovTable(ctxNombre, ctxApellido);
      showView("mov");
    });

    $("btn-detalles").addEventListener("click", () => {
      if (!selected) return toast("Seleccione un registro.", "error");
      ctxNombre = selected.nombre;
      ctxApellido = selected.apellido;
      $("det-person-title").textContent = `${ctxNombre} ${ctxApellido}`.toUpperCase();
      const tel = selected.telefono ? String(selected.telefono) : "";
      const telFmt =
        tel.length >= 9
          ? `${tel.slice(0, 3)}-${tel.slice(3, 6)}-${tel.slice(6)}`
          : tel || "N/A";
      $("det-telefono").textContent = "Teléfono: " + telFmt;
      $("det-email").textContent = "Email: " + (selected.email || "N/A");
      renderDetTable(ctxNombre, ctxApellido);
      buildDebtChart(ctxNombre, ctxApellido);
      showView("detalles");
    });

    $("btn-exportar-deudas").addEventListener("click", () => {
      const rows = consultarDeudas();
      const csv = rowsToCsv(rows);
      downloadText("deudas_exportadas.csv", csv, "text/csv;charset=utf-8");
      toast("CSV exportado.", "success");
    });
  }

  function attachMovHandlers() {
    const inp = $("mov-importe");
    const roDeuda = () => parseMoneyDisplay($("mov-deuda-actual").value);
    const updateNueva = () => {
      const mov = parseDecimalInput(inp.value);
      const base = roDeuda();
      if (mov === null) {
        $("mov-deuda-nueva").value = formatMoney(base);
        return;
      }
      $("mov-deuda-nueva").value = formatMoney(base + mov);
    };
    inp.addEventListener("input", updateNueva);

    $("mov-minus-10k").addEventListener("click", () => {
      const cur = parseDecimalInput(inp.value);
      const v = (cur === null ? 0 : cur) - 10000;
      inp.value = String(v);
      updateNueva();
    });
    $("mov-plus-10k").addEventListener("click", () => {
      const cur = parseDecimalInput(inp.value);
      const v = (cur === null ? 0 : cur) + 10000;
      inp.value = String(v);
      updateNueva();
    });

    $("mov-limpiar").addEventListener("click", () => {
      inp.value = "";
      $("mov-deuda-nueva").value = $("mov-deuda-actual").value;
      $("mov-desc").value = "";
    });

    $("form-mov").addEventListener("submit", (e) => {
      e.preventDefault();
      const mov = parseDecimalInput($("mov-importe").value);
      if (mov === null || mov === 0) {
        toast("No hay movimiento para registrar.", "error");
        return;
      }
      const deuda = roDeuda();
      const nueva = deuda + mov;
      actualizarDeuda(
        ctxNombre,
        ctxApellido,
        nueva,
        mov,
        $("mov-desc").value
      );
      $("mov-deuda-actual").value = formatMoney(nueva);
      inp.value = "";
      $("mov-deuda-nueva").value = formatMoney(nueva);
      $("mov-desc").value = "";
      renderMovTable(ctxNombre, ctxApellido);
      const rows = consultarDeudas();
      const upd = rows.find(
        (r) => r.nombre === ctxNombre && r.apellido === ctxApellido
      );
      if (upd) selected = { ...upd };
      renderDeudasTable();
      toast("Movimiento guardado.", "success");
    });
  }

  function attachDetHandlers() {
    $("det-exportar-csv").addEventListener("click", () => {
      const rows = consultarTablaPersona(ctxNombre, ctxApellido);
      const csv = rowsToCsv(rows);
      const fn = `${personTableRaw(ctxNombre, ctxApellido)}.csv`;
      downloadText(fn, csv, "text/csv;charset=utf-8");
      toast("CSV exportado.", "success");
    });

    $("det-mailto").addEventListener("click", () => {
      const rows = consultarTablaPersona(ctxNombre, ctxApellido);
      const email = selected && selected.email ? selected.email : "";
      if (!email) {
        toast("No hay email en el registro.", "error");
        return;
      }
      const sub = encodeURIComponent("Resumen de Movimientos a fecha");
      const body = encodeURIComponent(
        `Buen día estimado ${ctxNombre} ${ctxApellido},\n\n` +
          "Adjunte usted el CSV exportado desde la aplicación.\n\n" +
          "Saludos."
      );
      window.location.href = `mailto:${encodeURIComponent(email)}?subject=${sub}&body=${body}`;
    });
  }

  function attachOverlayHandlers() {
    document.querySelectorAll("[data-close-overlay]").forEach((el) => {
      el.addEventListener("click", () => {
        openOverlay("overlay-nuevo", false);
        openOverlay("overlay-editar", false);
      });
    });

    $("form-nuevo").addEventListener("submit", (e) => {
      e.preventDefault();
      const nombre = $("nuevo-nombre").value.trim();
      const apellido = $("nuevo-apellido").value.trim();
      const tel = $("nuevo-tel").value.trim();
      const email = $("nuevo-email").value.trim();
      if (!nombre || !apellido || !tel || !email) {
        toast(
          "Complete Nombre, Apellido, Teléfono y Email.",
          "error"
        );
        return;
      }
      let monto = parseDecimalInput($("nuevo-monto").value);
      let interes = parseDecimalInput($("nuevo-interes").value);
      const desc = $("nuevo-desc").value;
      const doc = $("nuevo-documento").value.trim();

      const apply = () => {
        try {
          registrarPersona(
            nombre,
            apellido,
            tel,
            email,
            monto,
            interes,
            desc,
            doc
          );
          openOverlay("overlay-nuevo", false);
          verificarYCalcularIntereses();
          renderDeudasTable();
          toast("Registro guardado.", "success");
        } catch (err) {
          const msg = err && err.message ? err.message : String(err);
          if (msg.includes("UNIQUE")) {
            toast("No pueden haber registros con el mismo nombre y apellido.", "error");
          } else {
            console.error(err);
            toast("Error al guardar.", "error");
          }
        }
      };

      if (monto === null || interes === null) {
        if (
          !confirm(
            "No ingresó valores en monto y/o interés. Se usará 0.0. ¿Continuar?"
          )
        ) {
          return;
        }
        monto = monto === null ? 0 : monto;
        interes = interes === null ? 0 : interes;
      }
      if (monto === null) monto = 0;
      if (interes === null) interes = 0;
      apply();
    });

    $("form-editar").addEventListener("submit", (e) => {
      e.preventDefault();
      if (!selected) return;
      editarRegistro(
        selected.nombre,
        selected.apellido,
        $("editar-tel").value.trim(),
        $("editar-email").value.trim(),
        $("editar-documento").value.trim()
      );
      openOverlay("overlay-editar", false);
      renderDeudasTable();
      const rows = consultarDeudas();
      const r = rows.find(
        (x) => x.nombre === selected.nombre && x.apellido === selected.apellido
      );
      if (r) selected = { ...r };
      toast("Cambios guardados.", "success");
    });
  }

  async function boot() {
    try {
      await loadSqlJs();
    } catch (e) {
      console.error(e);
      toast("No se pudo inicializar SQLite en el navegador.", "error");
      return;
    }
    initEmptyDatabase();
    attachDbHandlers();
    attachHomeHandlers();
    attachMovHandlers();
    attachDetHandlers();
    attachOverlayHandlers();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
