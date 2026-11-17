"""Sección 'Monitoreo': acciones 5 (sistema), 6 (CPU), 7 (RAM), 8 (almacenamiento) y 9 (procesos)."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QProgressBar, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from app.session import Session
from core.result import OpResult
from core.units import gib, mib, or_na, pct
from ops import monitor
from ui.theme import PALETTE, StatusBadge
from ui.workers import run_async

AUTO_CPU_MS = 5000


class NumItem(QTableWidgetItem):
    """Celda que ordena por valor numérico y muestra texto formateado."""

    def __init__(self, value, text: str | None = None):
        super().__init__(text if text is not None else or_na(value))
        self.value = value if value is not None else float("-inf")
        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __lt__(self, other):
        return self.value < other.value if isinstance(other, NumItem) else super().__lt__(other)


def make_table(headers: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.horizontalHeader().setStretchLastSection(True)
    return t


def hms(iso: str | None) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%H:%M:%S")  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "?"


class ConnectedSection(QWidget):
    """Base: deshabilita los botones remotos sin conexión y muestra el estado de cada consulta."""

    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.remote_buttons: list[QPushButton] = []
        self.status = StatusBadge()
        session.connection_changed.connect(self._on_connection)

    def _on_connection(self, *_args) -> None:
        connected = self.session.connected
        for b in self.remote_buttons:
            b.setEnabled(connected)
            b.setToolTip("" if connected else "Requiere conexión activa con BOSGAME.")
        if not connected:
            self.status.set_status("desconectado", "Sin conexión")

    def launch(self, fn, *args, on_done, busy_text: str = "Consultando…") -> None:
        self.status.set_status("conectando", busy_text)
        for b in self.remote_buttons:
            b.setEnabled(False)
        run_async(fn, self.session, *args, on_done=lambda op: self._finish(op, on_done), on_fail=self._fail)

    def _finish(self, op: OpResult, on_done) -> None:
        self._on_connection()
        self.status.set_status(op.status, f"{op.status.capitalize()} · {op.finished_at:%H:%M:%S}"
                               + (f" · {op.error}" if op.error else ""))
        if not op.error:
            on_done(op)

    def _fail(self, e: Exception) -> None:
        self._on_connection()
        self.status.set_status("error", f"Error: {e}")


# -- Acción 5 -------------------------------------------------------------------
class SystemTab(ConnectedSection):
    def __init__(self, session: Session):
        super().__init__(session)
        btn = QPushButton("Consultar sistema"); btn.clicked.connect(lambda: self.launch(monitor.system_info, on_done=self.show))
        self.remote_buttons.append(btn)
        self.table = make_table(["Dato", "Valor", "Fuente"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        top = QHBoxLayout(); top.addWidget(btn); top.addWidget(self.status, 1)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(self.table, 1)
        self._on_connection()

    def show(self, op: OpResult) -> None:
        d = op.data
        self.table.setRowCount(len(monitor.SYSTEM_FIELDS))
        for r, (key, label, source) in enumerate(monitor.SYSTEM_FIELDS):
            v = d.get(key)
            if key in ("memoria_instalada", "memoria_visible") and v is not None:
                text = gib(v)
            elif key == "arranque" and v:
                text = datetime.fromisoformat(v).strftime("%Y-%m-%d %H:%M:%S %z")
            else:
                text = or_na(v)
            item = QTableWidgetItem(text)
            if v in (None, ""):
                item.setForeground(QColor(PALETTE["warn"]))
            self.table.setItem(r, 0, QTableWidgetItem(label))
            self.table.setItem(r, 1, item)
            self.table.setItem(r, 2, QTableWidgetItem(source))
        self.table.resizeColumnToContents(0)


# -- Acciones 6 y 7 -----------------------------------------------------------
class CpuRamTab(ConnectedSection):
    def __init__(self, session: Session):
        super().__init__(session)
        # CPU
        self.cpu_value = QLabel("—"); self.cpu_value.setObjectName("bigValue")
        self.cpu_info = QLabel("Sin mediciones."); self.cpu_info.setObjectName("muted"); self.cpu_info.setWordWrap(True)
        self.btn_cpu = QPushButton("Medir CPU"); self.btn_cpu.clicked.connect(self.measure_cpu)
        self.auto = QCheckBox(f"Medición automática cada {AUTO_CPU_MS // 1000} s (no se registra en el historial)")
        self.auto.toggled.connect(self._toggle_auto)
        self.load_secs = QSpinBox(); self.load_secs.setRange(5, 120); self.load_secs.setValue(20); self.load_secs.setSuffix(" s")
        self.btn_load = QPushButton("Generar carga de prueba"); self.btn_load.clicked.connect(self.start_load)
        self.load_status = StatusBadge(); self.load_status.set_status("no ejecutado", "Sin carga activa")
        self.history = make_table(["Hora (BOSGAME)", "CPU %", "Intervalo", "Tipo"])
        self.history.setMaximumHeight(220)
        g_cpu = QGroupBox("Uso de CPU · fuente: Win32_PerfRawData_PerfOS_Processor (_Total), dos muestras")
        cl = QVBoxLayout(g_cpu)
        row = QHBoxLayout(); row.addWidget(self.cpu_value); row.addWidget(self.cpu_info, 1); cl.addLayout(row)
        row2 = QHBoxLayout(); row2.addWidget(self.btn_cpu); row2.addWidget(self.auto); row2.addStretch(); cl.addLayout(row2)
        row3 = QHBoxLayout(); row3.addWidget(QLabel("Duración")); row3.addWidget(self.load_secs); row3.addWidget(self.btn_load)
        row3.addWidget(self.load_status, 1); cl.addLayout(row3)
        cl.addWidget(self.history)
        # RAM
        self.ram_bar = QProgressBar(); self.ram_bar.setRange(0, 1000); self.ram_bar.setFormat("—")
        self.l_total, self.l_used, self.l_free, self.l_when = (QLabel("—") for _ in range(4))
        self.btn_ram = QPushButton("Consultar RAM"); self.btn_ram.clicked.connect(
            lambda: self.launch(monitor.ram_usage, on_done=self.show_ram))
        g_ram = QGroupBox("Memoria RAM · unidades en GiB (1 GiB = 1 073 741 824 bytes)")
        f = QFormLayout(g_ram); f.setVerticalSpacing(8)
        f.addRow(self.ram_bar)
        f.addRow("Total", self.l_total); f.addRow("Utilizada", self.l_used); f.addRow("Disponible", self.l_free)
        f.addRow("Instante", self.l_when)
        f.addRow("Fuente", QLabel(monitor.RAM_SOURCE))
        ram_row = QHBoxLayout(); ram_row.addWidget(self.btn_ram); ram_row.addStretch(); f.addRow(ram_row)

        self.remote_buttons += [self.btn_cpu, self.btn_load, self.btn_ram]
        top = QHBoxLayout(); top.addWidget(QLabel("Última consulta:")); top.addWidget(self.status, 1)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(g_cpu, 3); lay.addWidget(g_ram, 2)

        self._auto_timer = QTimer(self); self._auto_timer.setInterval(AUTO_CPU_MS)
        self._auto_timer.timeout.connect(self._auto_tick)
        self._auto_busy = False
        self._load_running = False
        self._on_connection()

    def _on_connection(self, *_args) -> None:
        super()._on_connection()
        if not self.session.connected:
            self.auto.setChecked(False)
        if self._load_running:
            self.btn_load.setEnabled(False)

    # CPU manual (registrada)
    def measure_cpu(self) -> None:
        self.launch(monitor.cpu_usage, on_done=lambda op: self.show_cpu(op, "manual"),
                    busy_text=f"Midiendo durante {self.session.config.lab.cpu_interval_s:g} s…")

    # CPU automática (no se registra para no inundar el historial)
    def _toggle_auto(self, on: bool) -> None:
        if on:
            self._auto_timer.start(); self._auto_tick()
        else:
            self._auto_timer.stop()

    def _auto_tick(self) -> None:
        if self._auto_busy or not self.session.connected:
            return
        self._auto_busy = True
        run_async(monitor.cpu_usage, self.session, record=False,
                  on_done=self._auto_done, on_fail=self._auto_fail)

    def _auto_done(self, op: OpResult) -> None:
        self._auto_busy = False
        if not op.error:
            self.show_cpu(op, "automática")

    def _auto_fail(self, e: Exception) -> None:
        self._auto_busy = False
        self.auto.setChecked(False)
        self.status.set_status("error", f"Medición automática detenida: {e}")

    def show_cpu(self, op: OpResult, kind: str) -> None:
        d = op.data
        v = d.get("porcentaje")
        self.cpu_value.setText(f"{v:.1f} %" if v is not None else "No disponible")
        self.cpu_info.setText(f"Medido en BOSGAME entre {hms(d.get('inicio'))} y {hms(d.get('fin'))} "
                              f"(intervalo {d.get('intervalo_ms')} ms, real {d.get('medido_ms')} ms). "
                              f"{d.get('logicos')} procesadores lógicos.")
        self.history.insertRow(0)
        self.history.setItem(0, 0, QTableWidgetItem(hms(d.get("fin"))))
        self.history.setItem(0, 1, NumItem(v, f"{v:.1f}" if v is not None else None))
        self.history.setItem(0, 2, QTableWidgetItem(f"{d.get('intervalo_ms')} ms"))
        self.history.setItem(0, 3, QTableWidgetItem(kind + (" · con carga" if self._load_running else "")))
        if self.history.rowCount() > 200:
            self.history.removeRow(200)
        self.history.resizeColumnsToContents()

    def start_load(self) -> None:
        secs = self.load_secs.value()
        self._load_running = True
        self.btn_load.setEnabled(False)
        self.load_status.set_status("ejecutado", f"Carga activa en BOSGAME durante {secs} s…")
        # Medición automática para ver la variación mientras dura la carga.
        self.auto.setChecked(True)
        run_async(monitor.generate_cpu_load, self.session, secs, on_done=self._load_done, on_fail=self._load_fail)

    def _load_done(self, op: OpResult) -> None:
        self._load_running = False
        self.btn_load.setEnabled(self.session.connected)
        if op.error:
            self.load_status.set_status("error", f"Carga fallida: {op.error}")
        else:
            self.load_status.set_status(op.status, op.message)

    def _load_fail(self, e: Exception) -> None:
        self._load_running = False
        self.btn_load.setEnabled(self.session.connected)
        self.load_status.set_status("error", f"Carga fallida: {e}")

    def show_ram(self, op: OpResult) -> None:
        d = op.data
        total, used, free = d["total"], d["usada"], d["disponible"]
        p = pct(used, total)
        self.ram_bar.setValue(int((p or 0) * 10)); self.ram_bar.setFormat(f"{p} % utilizada")
        self.l_total.setText(gib(total)); self.l_used.setText(gib(used)); self.l_free.setText(gib(free))
        self.l_when.setText(hms(d.get("instante")))


# -- Acción 8 -------------------------------------------------------------------
class StorageTab(ConnectedSection):
    HEAD = ["Unidad", "Etiqueta", "Sistema", "Capacidad", "Utilizado", "Libre", "Uso", "Libre según Get-Volume", "Contraste"]

    def __init__(self, session: Session):
        super().__init__(session)
        btn = QPushButton("Consultar almacenamiento")
        btn.clicked.connect(lambda: self.launch(monitor.storage, on_done=self.show))
        self.remote_buttons.append(btn)
        self.table = make_table(self.HEAD)
        note = QLabel("Fuente: Win32_LogicalDisk (unidades fijas). Contraste: Get-Volume en el mismo equipo. "
                      "Unidades en GiB.")
        note.setObjectName("muted")
        top = QHBoxLayout(); top.addWidget(btn); top.addWidget(self.status, 1)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(note); lay.addWidget(self.table, 1)
        self._on_connection()

    def show(self, op: OpResult) -> None:
        self.table.setRowCount(len(op.data))
        for r, d in enumerate(op.data):
            bar = QProgressBar(); bar.setRange(0, 1000)
            p = pct(d.get("usado"), d.get("total"))
            bar.setValue(int((p or 0) * 10)); bar.setFormat(f"{p} %" if p is not None else "—")
            match = {True: ("✔ Coincide", PALETTE["ok"]), False: ("✖ Difiere", PALETTE["error"]),
                     None: ("– Sin contraste", PALETTE["muted"])}[d.get("coincide")]
            cells = [
                QTableWidgetItem(d.get("unidad", "")), QTableWidgetItem(or_na(d.get("etiqueta"))),
                QTableWidgetItem(or_na(d.get("sistema"))),
                NumItem(d.get("total"), gib(d.get("total"))), NumItem(d.get("usado"), gib(d.get("usado"))),
                NumItem(d.get("libre"), gib(d.get("libre"))), None,
                NumItem(d.get("contraste_libre"), gib(d.get("contraste_libre"))), QTableWidgetItem(match[0]),
            ]
            cells[8].setForeground(QColor(match[1]))
            for c, item in enumerate(cells):
                if item is not None:
                    self.table.setItem(r, c, item)
            self.table.setCellWidget(r, 6, bar)
        self.table.resizeColumnsToContents()


# -- Acción 9 -------------------------------------------------------------------
class ProcessesTab(ConnectedSection):
    HEAD = ["PID", "Nombre", "CPU %", "CPU acumulada (s)", "Memoria (MiB)", "Sesión", "Prueba"]

    def __init__(self, session: Session):
        super().__init__(session)
        self._procs: list[dict] = []
        btn = QPushButton("Consultar procesos")
        btn.clicked.connect(lambda: self.launch(monitor.processes, on_done=self.show,
                                                busy_text="Midiendo consumo por proceso…"))
        self.remote_buttons.append(btn)
        self.filter = QLineEdit(); self.filter.setPlaceholderText("Filtrar por nombre o PID")
        self.filter.textChanged.connect(self.apply_filter)
        self.only_test = QCheckBox("Solo procesos de prueba")
        self.only_test.toggled.connect(self.apply_filter)
        self.summary = QLabel(); self.summary.setObjectName("muted")
        self.table = make_table(self.HEAD)
        self.table.setSortingEnabled(True)
        top = QHBoxLayout(); top.addWidget(btn); top.addWidget(self.filter, 1); top.addWidget(self.only_test)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(self.status); lay.addWidget(self.summary)
        lay.addWidget(self.table, 1)
        self._on_connection()

    def show(self, op: OpResult) -> None:
        self._procs = op.data
        self.summary.setText(op.message + " CPU % = uso medio durante el intervalo, normalizado al total de "
                             "procesadores lógicos. Los procesos de prueba se generan en CPU y RAM → "
                             "'Generar carga de prueba'.")
        self.apply_filter()

    def apply_filter(self, *_args) -> None:
        text = self.filter.text().strip().lower()
        rows = [p for p in self._procs
                if (not self.only_test.isChecked() or p.get("prueba"))
                and (not text or text in str(p.get("nombre", "")).lower() or text == str(p.get("pid")))]
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, p in enumerate(rows):
            cells = [
                NumItem(p.get("pid")), QTableWidgetItem(p.get("nombre", "")),
                NumItem(p.get("cpu_pct")), NumItem(p.get("cpu_s")),
                NumItem(p.get("memoria"), mib(p.get("memoria")).replace(" MiB", "")),
                NumItem(p.get("sesion")), QTableWidgetItem("● Sí" if p.get("prueba") else ""),
            ]
            if p.get("prueba"):
                for item in cells:
                    item.setBackground(QColor("#CCFBF1"))
            for c, item in enumerate(cells):
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()


class MonitorPage(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        tabs = QTabWidget()
        tabs.addTab(SystemTab(session), "Sistema")
        tabs.addTab(CpuRamTab(session), "CPU y RAM")
        tabs.addTab(StorageTab(session), "Almacenamiento")
        tabs.addTab(ProcessesTab(session), "Procesos")
        QVBoxLayout(self).addWidget(tabs)
