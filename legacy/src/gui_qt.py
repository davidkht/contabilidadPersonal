"""
Interfaz de escritorio con PySide6 (Qt): alternativa visual a gui.py (Tkinter).
Misma lógica de negocio en main.py.
Ejecutar desde la carpeta src:  python gui_qt.py
"""
from __future__ import annotations

import os
import sys

import main
from main import script_directory

import matplotlib.ticker as mticker
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QApplication,
)


def _money_fmt(v: float) -> str:
    return f"${float(v):,.2f}"


def _field_label(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("fieldLabel")
    return lab


def _apply_data_table(t: QTableWidget) -> None:
    t.setShowGrid(False)
    t.setFrameShape(QFrame.Shape.NoFrame)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(30)


def _persona_movements_col_width(col: str) -> int:
    """Anchos por columna de tablas de movimientos (tabla por persona)."""
    return {
        "id": 56,
        "deuda_total": 144,
        "transaccion": 144,
        "fecha": 128,
        "descripcion": 400,
    }.get(col, 140)


def _apply_persona_table_layout(table: QTableWidget, cols: list[str]) -> None:
    """Descripción ocupa el espacio sobrante; el resto respeta anchos mínimos amplios."""
    hdr = table.horizontalHeader()
    hdr.setMinimumSectionSize(48)
    for i, col in enumerate(cols):
        table.setColumnWidth(i, _persona_movements_col_width(col))
        if col == "descripcion":
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        else:
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)


def _parse_monto_display(s) -> float:
    if s is None:
        return 0.0
    t = str(s).replace("$", "").replace(",", "").strip()
    if not t:
        return 0.0
    return float(t)


def _load_modern_theme() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "modern_theme.qss")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


class RegistroDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo registro")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        g = QGridLayout()
        self._nombre = QLineEdit()
        self._apellido = QLineEdit()
        self._documento = QLineEdit()
        self._tel = QLineEdit()
        self._email = QLineEdit()
        self._monto = QLineEdit()
        self._interes = QLineEdit()
        self._desc = QTextEdit()
        self._desc.setMaximumHeight(120)
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(8)
        r = 0
        g.addWidget(_field_label("Nombre:"), r, 0)
        g.addWidget(self._nombre, r, 1)
        g.addWidget(_field_label("Apellido:"), r, 2)
        g.addWidget(self._apellido, r, 3)
        r += 1
        g.addWidget(_field_label("Documento ID:"), r, 0)
        g.addWidget(self._documento, r, 1)
        g.addWidget(_field_label("Teléfono:"), r, 2)
        g.addWidget(self._tel, r, 3)
        r += 1
        g.addWidget(_field_label("Email:"), r, 0)
        g.addWidget(self._email, r, 1, 1, 3)
        r += 1
        g.addWidget(_field_label("Monto adeudado:"), r, 0)
        g.addWidget(self._monto, r, 1)
        g.addWidget(_field_label("Tasa de interés:"), r, 2)
        g.addWidget(self._interes, r, 3)
        r += 1
        g.addWidget(_field_label("Descripción:"), r, 0, alignment=Qt.AlignTop)
        g.addWidget(self._desc, r, 1, 1, 3)
        layout.addLayout(g)
        bb = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        bb.accepted.connect(self._guardar)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _guardar(self):
        if (
            not self._nombre.text().strip()
            or not self._apellido.text().strip()
            or not self._tel.text().strip()
            or not self._email.text().strip()
        ):
            QMessageBox.warning(
                self,
                "Error",
                "Por favor llene todos los campos requeridos (Nombre, Apellido, Teléfono, Email).",
            )
            return
        desc = self._desc.toPlainText()
        doc = self._documento.text().strip()
        try:
            m = float(self._monto.text())
            i = float(self._interes.text())
        except ValueError:
            r = QMessageBox.question(
                self,
                "Sin valor",
                "No ingresó valores en monto y/o interés. Se utilizará 0.0 por "
                "defecto, ¿Está de acuerdo?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if r != QMessageBox.Yes:
                return
            m, i = 0.0, 0.0
        try:
            main.registrar_persona(
                self._nombre.text().strip(),
                self._apellido.text().strip(),
                self._tel.text().strip(),
                self._email.text().strip(),
                m,
                i,
                desc,
                doc,
            )
        except PermissionError:
            QMessageBox.critical(
                self,
                "Error fatal",
                "No pueden haber registros con el mismo nombre y apellido.",
            )
            return
        QMessageBox.information(self, "Éxito", "Registro guardado exitosamente.")
        self.accept()


class EditarDialog(QDialog):
    def __init__(self, values, parent=None):
        super().__init__(parent)
        self._nombre = values[1]
        self._apellido = values[2]
        self.setWindowTitle("Editar información")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(f"<b>{self._nombre} {self._apellido}</b>"),
            alignment=Qt.AlignCenter,
        )
        form = QFormLayout()
        form.setVerticalSpacing(8)
        form.setHorizontalSpacing(12)
        self._doc = QLineEdit(str(values[3]) if values[3] is not None else "")
        self._tel = QLineEdit(str(values[4]) if values[4] is not None else "")
        self._email = QLineEdit(str(values[5]) if values[5] is not None else "")
        form.addRow(_field_label("Documento ID:"), self._doc)
        form.addRow(_field_label("Teléfono:"), self._tel)
        form.addRow(_field_label("Email:"), self._email)
        layout.addLayout(form)
        bb = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _save(self):
        main.editar_registro(
            self._nombre,
            self._apellido,
            self._tel.text().strip(),
            self._email.text().strip(),
            self._doc.text().strip(),
        )
        QMessageBox.information(self, "Éxito", "Cambios guardados exitosamente.")
        self.accept()


class HomePage(QWidget):
    """Solo la tabla principal; acciones y navegación viven en MainWindow."""

    def __init__(self, window: "MainWindow"):
        super().__init__()
        self._win = window
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        hint = QLabel(
            "Seleccione una fila para habilitar Movimientos y Detalles en la barra lateral."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #9b8cb8; font-size: 9pt;")

        box_list = QGroupBox("Todas las deudas")
        vl = QVBoxLayout(box_list)
        self._table = QTableWidget()
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setAlternatingRowColors(True)
        _apply_data_table(self._table)
        vl.addWidget(self._table)

        root.addWidget(hint)
        root.addWidget(box_list, 1)
        self._table.itemSelectionChanged.connect(self._win.on_home_selection_changed)

    def refresh_table(self):
        df = main.consultar_deudas()
        cols = list(df.columns)
        self._table.clear()
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels([c.upper() for c in cols])
        self._table.setRowCount(len(df))
        widths = {
            "id": 40,
            "nombre": 90,
            "apellido": 90,
            "documento": 100,
            "telefono": 90,
            "email": 180,
            "monto": 110,
            "interes": 70,
            "fecha": 95,
        }
        for i, col in enumerate(cols):
            self._table.setColumnWidth(i, widths.get(col, 100))
        for ri, (_, row) in enumerate(df.iterrows()):
            for ci, col in enumerate(cols):
                val = row[col]
                if col == "monto":
                    disp = _money_fmt(val)
                else:
                    disp = "" if pd.isna(val) else str(val)
                item = QTableWidgetItem(disp)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self._table.setItem(ri, ci, item)

    def selected_values(self):
        r = self._table.currentRow()
        if r < 0:
            return None
        out = []
        for c in range(self._table.columnCount()):
            it = self._table.item(r, c)
            out.append(it.text() if it else "")
        return out


class MovimientoPage(QWidget):
    def __init__(self, window: "MainWindow"):
        super().__init__()
        self._win = window
        self._nombre = ""
        self._apellido = ""
        self._deuda_actual = 0.0

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)
        split = QSplitter(Qt.Horizontal)

        self._hist_box = QGroupBox("Historial de movimientos")
        box_t = self._hist_box
        vt = QVBoxLayout(box_t)
        self._table = QTableWidget()
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        _apply_data_table(self._table)
        vt.addWidget(self._table)

        box_f = QGroupBox("Nuevo movimiento")
        vf = QGridLayout(box_f)
        vf.setHorizontalSpacing(12)
        vf.setVerticalSpacing(6)
        vf.setContentsMargins(10, 14, 10, 12)
        f = QLineEdit()
        f.setReadOnly(True)
        self._deuda_in = f
        self._mov_in = QLineEdit()
        self._mov_in.textChanged.connect(self._update_preview)
        self._nueva_in = QLineEdit()
        self._nueva_in.setReadOnly(True)
        self._desc = QTextEdit()
        self._desc.setMaximumHeight(100)
        vf.addWidget(_field_label("Deuda actual:"), 0, 0)
        vf.addWidget(self._deuda_in, 0, 1)
        vf.addWidget(_field_label("Movimiento:"), 1, 0)
        vf.addWidget(self._mov_in, 1, 1)
        row_quick = QHBoxLayout()
        row_quick.addWidget(self._mk_quick(False))
        row_quick.addStretch()
        row_quick.addWidget(self._mk_quick(True))
        vf.addLayout(row_quick, 2, 1)
        vf.addWidget(_field_label("Deuda actualizada:"), 3, 0)
        vf.addWidget(self._nueva_in, 3, 1)
        vf.addWidget(_field_label("Descripción:"), 4, 0, alignment=Qt.AlignTop)
        vf.addWidget(self._desc, 4, 1)
        save = QPushButton("Guardar movimiento")
        save.setObjectName("btnPrimary")
        save.clicked.connect(self._save)
        clr = QPushButton("Limpiar campos")
        clr.setObjectName("btnSecondary")
        clr.clicked.connect(self._limpiar)
        vf.addWidget(clr, 5, 0)
        vf.addWidget(save, 5, 1)

        split.addWidget(box_t)
        split.addWidget(box_f)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 1)
        lay.addWidget(split)

    def _mk_quick(self, mas: bool):
        b = QPushButton("+ 10k" if mas else "− 10k")
        b.setObjectName("btnSecondary")
        b.setFixedWidth(72)
        b.clicked.connect(lambda: self._suma(mas))
        return b

    def _suma(self, mas: bool):
        try:
            cur = float(self._mov_in.text()) if self._mov_in.text().strip() else 0.0
        except ValueError:
            cur = 0.0
        cur += 10000.0 if mas else -10000.0
        self._mov_in.setText(str(cur))
        self._update_preview()

    def _update_preview(self):
        try:
            mov_txt = self._mov_in.text().strip()
            mov = float(mov_txt) if mov_txt else 0.0
        except ValueError:
            self._nueva_in.setText(_money_fmt(self._deuda_actual))
            return
        self._nueva_in.setText(_money_fmt(self._deuda_actual + mov))

    def populate(self, values):
        self._nombre = values[1]
        self._apellido = values[2]
        self._deuda_actual = _parse_monto_display(values[6])
        self._deuda_in.setText(_money_fmt(self._deuda_actual))
        self._mov_in.clear()
        self._nueva_in.setText(_money_fmt(self._deuda_actual))
        self._desc.clear()
        self._fill_movements_table()

    def _fill_movements_table(self):
        df = main.consultar_tabla_persona(self._nombre, self._apellido)
        cols = list(df.columns)
        self._table.clear()
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setRowCount(len(df))
        for ri, (_, row) in enumerate(df.iterrows()):
            for ci, col in enumerate(cols):
                val = row[col]
                if col in ("deuda_total", "transaccion"):
                    disp = _money_fmt(val)
                else:
                    disp = "" if pd.isna(val) else str(val)
                item = QTableWidgetItem(disp)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self._table.setItem(ri, ci, item)
        _apply_persona_table_layout(self._table, cols)

    def _limpiar(self):
        self._mov_in.clear()
        self._nueva_in.setText(_money_fmt(self._deuda_actual))
        self._desc.clear()

    def _save(self):
        try:
            mov_txt = self._mov_in.text().strip()
            mov = float(mov_txt) if mov_txt else 0.0
        except ValueError:
            QMessageBox.warning(self, "Error", "No hay movimiento para registrar.")
            return
        if mov == 0.0:
            QMessageBox.warning(self, "Error", "No hay movimiento para registrar.")
            return
        nueva = self._deuda_actual + mov
        main.actualizar_deuda(
            self._nombre,
            self._apellido,
            nueva,
            mov,
            self._desc.toPlainText(),
        )
        self._deuda_actual = nueva
        self._deuda_in.setText(_money_fmt(nueva))
        self._limpiar()
        self._fill_movements_table()


class DetallesPage(QWidget):
    def __init__(self, window: "MainWindow"):
        super().__init__()
        self._win = window
        self._nombre = ""
        self._apellido = ""
        self._mail_addr = ""
        self._telefono = ""

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        outer = QSplitter(Qt.Vertical)
        outer.setChildrenCollapsible(False)

        self._box_g = QGroupBox("Evolución de la deuda")
        box_g = self._box_g
        vg = QVBoxLayout(box_g)
        self._figure = Figure(figsize=(7, 3.2), layout="tight")
        self._figure.patch.set_facecolor("#141023")
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.setMinimumHeight(220)
        vg.addWidget(self._canvas)

        inner = QSplitter(Qt.Horizontal)
        inner.setChildrenCollapsible(False)

        self._gb_tabla = QGroupBox("Movimientos")
        box_t = self._gb_tabla
        vt = QVBoxLayout(box_t)
        self._table = QTableWidget()
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        _apply_data_table(self._table)
        vt.addWidget(self._table)

        act = QGroupBox("Contacto y exportación")
        va = QVBoxLayout(act)
        va.setSpacing(6)
        row_tel = QHBoxLayout()
        row_tel.setSpacing(10)
        lab_tel = _field_label("Teléfono:")
        lab_tel.setFixedWidth(82)
        row_tel.addWidget(lab_tel)
        self._lbl_tel = QLabel()
        self._lbl_tel.setObjectName("metaValue")
        self._lbl_tel.setWordWrap(True)
        row_tel.addWidget(self._lbl_tel, 1)
        va.addLayout(row_tel)
        row_mail = QHBoxLayout()
        row_mail.setSpacing(10)
        lab_mail = _field_label("Email:")
        lab_mail.setFixedWidth(82)
        row_mail.addWidget(lab_mail)
        self._lbl_mail = QLabel()
        self._lbl_mail.setObjectName("metaValue")
        self._lbl_mail.setWordWrap(True)
        row_mail.addWidget(self._lbl_mail, 1)
        va.addLayout(row_mail)
        va.addSpacing(4)
        exp = QPushButton("Exportar CSV")
        exp.setObjectName("btnPrimary")
        exp.clicked.connect(self._exportar)
        mail = QPushButton("Enviar E-mail")
        mail.setObjectName("btnSecondary")
        mail.clicked.connect(self._enviar_email)
        va.addWidget(exp)
        va.addWidget(mail)
        va.addStretch()

        inner.addWidget(self._gb_tabla)
        inner.addWidget(act)
        inner.setStretchFactor(0, 3)
        inner.setStretchFactor(1, 1)

        outer.addWidget(self._box_g)
        outer.addWidget(inner)
        outer.setStretchFactor(0, 1)
        outer.setStretchFactor(1, 2)

        lay.addWidget(outer)

    def populate(self, values):
        self._nombre = values[1]
        self._apellido = values[2]
        self._telefono = values[4] or ""
        self._mail_addr = values[5] or ""
        tel = str(self._telefono)
        if len(tel) >= 9:
            tel_fmt = f"{tel[:3]}-{tel[3:6]}-{tel[6:]}"
        else:
            tel_fmt = tel or "N/A"
        self._lbl_tel.setText(tel_fmt)
        self._lbl_mail.setText(self._mail_addr or "N/A")

        self._fill_table()
        self._draw_chart()

    def _fill_table(self):
        df = main.consultar_tabla_persona(self._nombre, self._apellido)
        cols = list(df.columns)
        self._table.clear()
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setRowCount(len(df))
        for ri, (_, row) in enumerate(df.iterrows()):
            for ci, col in enumerate(cols):
                val = row[col]
                if col in ("deuda_total", "transaccion"):
                    disp = _money_fmt(val)
                else:
                    disp = "" if pd.isna(val) else str(val)
                item = QTableWidgetItem(disp)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self._table.setItem(ri, ci, item)
        _apply_persona_table_layout(self._table, cols)

    def _draw_chart(self):
        df = main.consultar_tabla_persona(self._nombre, self._apellido)
        df = df.sort_values(by="id") if len(df) else df
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        if len(df) > 0:
            ax.plot(
                df["id"],
                df["deuda_total"],
                marker="s",
                linestyle="-",
                color="#a78bfa",
                linewidth=1.2,
                markersize=1.5,
                markerfacecolor="#c4b5fd",
                markeredgecolor="#6d28d9",
                markeredgewidth=0.2,
            )
        else:
            ax.text(
                0.5,
                0.5,
                "Sin movimientos",
                ha="center",
                va="center",
                transform=ax.transAxes,
                color="#9b8cb8",
                fontsize=12,
            )
        ax.set_facecolor("#1a1428")
        ax.set_xlabel("Nº transacción", color="#c9bddc")
        ax.set_ylabel("Deuda total", color="#c9bddc")
        ax.set_title("Historial de deuda", color="#ebe4f5")
        ax.tick_params(colors="#b8a8d8")
        for spine in ax.spines.values():
            spine.set_color("#352d4a")
        ax.axhline(0, color="#352d4a", linestyle="-", linewidth=0.5)
        ax.axvline(0, color="#352d4a", linestyle="-", linewidth=0.5)
        formatter = mticker.FuncFormatter(lambda x, p: f"${x:,.0f}")
        ax.yaxis.set_major_formatter(formatter)
        self._figure.patch.set_facecolor("#141023")
        self._figure.tight_layout()
        self._canvas.draw()

    def _exportar(self):
        nombre_archivo = f"{self._nombre}_{self._apellido}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar archivo como",
            nombre_archivo,
            "CSV (*.csv)",
        )
        if path:
            main.exportar_datos_a_csv("Usuario", self._nombre, self._apellido, path)
            QMessageBox.information(self, "Exportación", f"Datos exportados a:\n{path}")

    def _enviar_email(self):
        import email_sender

        nombre_archivo = f"{self._nombre}_{self._apellido}.csv"
        subject = "Resumen de Movimientos a fecha"
        body = f"""
            Buen día estimado {self._nombre} {self._apellido},
            Adjunto excel con un resumen de los movimientos y transacciones
            de nuestros asuntos de dinero.

            Saludos.
            """
        try:
            main.exportar_datos_a_csv(
                "Usuario", self._nombre, self._apellido, nombre_archivo
            )
            email_sender.send_email(subject, body, self._mail_addr, nombre_archivo)
            QMessageBox.information(
                self, "Éxito", f"Correo enviado exitosamente a {self._mail_addr}"
            )
            os.remove(nombre_archivo)
        except ConnectionAbortedError as e:
            QMessageBox.critical(self, "Error", f"Error al enviar el correo: {e}")
        except ConnectionError as e:
            QMessageBox.critical(self, "Error", f"Ocurrió un error: {e}")
        except OSError as e:
            QMessageBox.critical(self, "Error", str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Contabilidad")
        self.resize(1180, 640)
        self._set_icon()

        self._breadcrumb = QLabel("Lista de deudas")
        self._breadcrumb.setObjectName("breadcrumb")

        self._stack = QStackedWidget()
        self._stack.setObjectName("stackedPages")
        self._home = HomePage(self)
        self._mov = MovimientoPage(self)
        self._det = DetallesPage(self)
        self._stack.addWidget(self._home)
        self._stack.addWidget(self._mov)
        self._stack.addWidget(self._det)

        self._sidebar = self._build_sidebar()

        shell = QWidget()
        shell.setObjectName("contentShell")
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        shell_layout.addWidget(self._sidebar)

        center_host = QWidget()
        center_host.setObjectName("contentHost")
        cv = QVBoxLayout(center_host)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)

        cv.addWidget(self._breadcrumb)
        cv.addWidget(self._stack, 1)

        shell_layout.addWidget(center_host, 1)
        self.setCentralWidget(shell)

        self.on_home_selection_changed()

    def _build_sidebar(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("sideRail")
        rail.setFixedWidth(280)
        v = QVBoxLayout(rail)
        v.setContentsMargins(14, 16, 14, 16)
        v.setSpacing(3)

        bt = QLabel("Contabilidad")
        bt.setObjectName("brandTitle")
        bs = QLabel("Deudas personales")
        bs.setObjectName("brandSub")
        v.addWidget(bt)
        v.addWidget(bs)
        v.addSpacing(10)

        nav_lab = QLabel("Navegación")
        nav_lab.setObjectName("sectionLabel")
        v.addWidget(nav_lab)

        self._btn_nav_lista = QPushButton("Lista de deudas")
        self._btn_nav_mov = QPushButton("Movimientos")
        self._btn_nav_det = QPushButton("Detalles")
        self._btn_nav_lista.clicked.connect(self.show_home)
        self._btn_nav_mov.clicked.connect(self._nav_to_mov)
        self._btn_nav_det.clicked.connect(self._nav_to_det)
        v.addWidget(self._btn_nav_lista)
        v.addWidget(self._btn_nav_mov)
        v.addWidget(self._btn_nav_det)

        sel_lab = QLabel("Selección")
        sel_lab.setObjectName("sectionLabel")
        v.addWidget(sel_lab)
        self._lbl_sel = QLabel("Nadie seleccionado")
        self._lbl_sel.setObjectName("selectionBadge")
        self._lbl_sel.setProperty("isPlaceholder", True)
        self._lbl_sel.setWordWrap(True)
        v.addWidget(self._lbl_sel)

        reg_lab = QLabel("Registros")
        reg_lab.setObjectName("sectionLabel")
        v.addWidget(reg_lab)
        self._btn_nuevo = QPushButton("Nuevo registro")
        self._btn_nuevo.setObjectName("btnRegAdd")
        self._btn_nuevo.clicked.connect(self._action_nuevo)
        self._btn_editar = QPushButton("Editar persona")
        self._btn_editar.setObjectName("btnRegEdit")
        self._btn_editar.clicked.connect(self._action_editar)
        self._btn_borrar = QPushButton("Borrar registro")
        self._btn_borrar.setObjectName("btnRegDel")
        self._btn_borrar.clicked.connect(self._action_borrar)
        v.addWidget(self._btn_nuevo)
        v.addWidget(self._btn_editar)
        v.addWidget(self._btn_borrar)

        dat_lab = QLabel("Datos")
        dat_lab.setObjectName("sectionLabel")
        v.addWidget(dat_lab)
        self._btn_export = QPushButton("Exportar tabla (CSV)")
        self._btn_export.setObjectName("btnSecondary")
        self._btn_export.clicked.connect(self._action_export_all)
        v.addWidget(self._btn_export)
        v.addStretch()

        self._highlight_nav("lista")
        return rail

    def _highlight_nav(self, which: str) -> None:
        mapping = [
            ("lista", self._btn_nav_lista),
            ("mov", self._btn_nav_mov),
            ("det", self._btn_nav_det),
        ]
        for key, btn in mapping:
            btn.setObjectName("navBtnActive" if key == which else "navBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def on_home_selection_changed(self) -> None:
        vals = self._home.selected_values()
        if vals:
            self._lbl_sel.setText(f"{vals[1]} {vals[2]}")
            self._lbl_sel.setProperty("isPlaceholder", False)
            self._btn_nav_mov.setEnabled(True)
            self._btn_nav_det.setEnabled(True)
            self._btn_editar.setEnabled(True)
            self._btn_borrar.setEnabled(True)
        else:
            self._lbl_sel.setText("Nadie seleccionado")
            self._lbl_sel.setProperty("isPlaceholder", True)
            self._btn_nav_mov.setEnabled(False)
            self._btn_nav_det.setEnabled(False)
            self._btn_editar.setEnabled(False)
            self._btn_borrar.setEnabled(False)
        self._lbl_sel.style().unpolish(self._lbl_sel)
        self._lbl_sel.style().polish(self._lbl_sel)

    def _nav_to_mov(self) -> None:
        vals = self._home.selected_values()
        if not vals:
            QMessageBox.warning(
                self,
                "Selección",
                "Seleccione una persona en la lista.",
            )
            return
        self.show_movimiento(vals)

    def _nav_to_det(self) -> None:
        vals = self._home.selected_values()
        if not vals:
            QMessageBox.warning(
                self,
                "Selección",
                "Seleccione una persona en la lista.",
            )
            return
        self.show_detalles(vals)

    def _action_nuevo(self) -> None:
        dlg = RegistroDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._home.refresh_table()
            self.on_home_selection_changed()

    def _action_editar(self) -> None:
        vals = self._home.selected_values()
        if not vals:
            QMessageBox.warning(self, "Error", "No hay selección.")
            return
        dlg = EditarDialog(vals, self)
        if dlg.exec() == QDialog.Accepted:
            self._home.refresh_table()
            self.on_home_selection_changed()

    def _action_borrar(self) -> None:
        vals = self._home.selected_values()
        if not vals:
            QMessageBox.warning(self, "Error", "No hay selección.")
            return
        if (
            QMessageBox.question(
                self,
                "Borrar registro",
                "¿Está seguro de borrar el registro?",
            )
            != QMessageBox.Yes
        ):
            return
        main.borrar_usuario(vals[1], vals[2])
        self._home.refresh_table()
        self.on_home_selection_changed()

    def _action_export_all(self) -> None:
        exports_dir = os.path.join(script_directory, "..", "..", "exports")
        os.makedirs(exports_dir, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar archivo como",
            os.path.join(exports_dir, "deudas_exportadas.csv"),
            "CSV (*.csv)",
        )
        if path:
            main.exportar_datos_a_csv("Deudas", filename=path)
            QMessageBox.information(
                self, "Exportación", f"Datos exportados a:\n{path}"
            )

    def _set_icon(self):
        icon_path = os.path.join(script_directory, "..", "docs", "icono.svg")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def show_home(self):
        self._breadcrumb.setText("Lista de deudas")
        self._stack.setCurrentWidget(self._home)
        self._home.refresh_table()
        self.on_home_selection_changed()
        self._highlight_nav("lista")

    def show_movimiento(self, values):
        nom, ape = values[1], values[2]
        self._breadcrumb.setText(f"Lista › {nom} {ape} › Movimientos")
        self._mov.populate(values)
        self._stack.setCurrentWidget(self._mov)
        self._highlight_nav("mov")

    def show_detalles(self, values):
        nom, ape = values[1], values[2]
        self._breadcrumb.setText(f"Lista › {nom} {ape} › Detalles")
        self._det.populate(values)
        self._stack.setCurrentWidget(self._det)
        self._highlight_nav("det")

    def closeEvent(self, event):
        r = QMessageBox.question(
            self,
            "Salir",
            "¿Seguro que quieres salir?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if r == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


def main_qt():
    main.verificar_y_calcular_intereses()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(_load_modern_theme())
    w = MainWindow()
    w.show_home()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main_qt()
