"""Ventana principal: cabecera de contexto, navegación lateral y secciones."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import APP_NAME, APP_VERSION
from ..app.session import Session
from ..core.result import OpResult
from .connection_page import ConnectionPage
from .theme import StatusBadge

RESOURCES = Path(__file__).resolve().parent.parent / "resources"


def app_icon() -> QIcon:
    return QIcon(str(RESOURCES / "icon.svg"))


class Header(QWidget):
    """Muestra estudiante, equipo, IP y conexión antes de cualquier operación."""

    def __init__(self, session: Session):
        super().__init__()
        self.setObjectName("header")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.session = session
        self.title = QLabel(); self.title.setObjectName("title")
        self.ctx = QLabel(); self.ctx.setObjectName("muted")
        self.badge = StatusBadge()
        left = QVBoxLayout(); left.addWidget(self.title); left.addWidget(self.ctx)
        lay = QHBoxLayout(self); lay.setContentsMargins(18, 10, 18, 10)
        lay.addLayout(left, 1); lay.addWidget(self.badge)
        session.connection_changed.connect(self.refresh)
        session.config_changed.connect(self.refresh)
        self.refresh()

    def set_title(self, text: str) -> None:
        self.title.setText(text)

    def refresh(self, *_args) -> None:
        s, c = self.session.config.student, self.session.config.connection
        student = f"{s.full_name} ({s.student_id})" if s.complete else "Estudiante sin registrar"
        host = self.session.remote.computer_name or c.host_name or "—"
        self.ctx.setText(f"{student}   ·   Equipo: {host}   ·   IP: {c.address or '—'}:{c.port}   ·   Sesión: {self.session.session_id}")
        if self.session.connected:
            self.badge.set_status("conectado", f"Conectado como {self.session.remote.user}")
        else:
            self.badge.set_status("desconectado", "Desconectado")


class DashboardPage(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.g = QGroupBox("BOSGAME")
        f = QFormLayout(self.g)
        self.l_host, self.l_ip, self.l_user, self.l_os, self.l_ps = (QLabel("—") for _ in range(5))
        self.badge = StatusBadge()
        f.addRow("Estado", self.badge)
        f.addRow("Equipo", self.l_host)
        f.addRow("Dirección", self.l_ip)
        f.addRow("Usuario remoto", self.l_user)
        f.addRow("Sistema", self.l_os)
        f.addRow("PowerShell", self.l_ps)
        self.recent = QTableWidget(0, 4)
        self.recent.setHorizontalHeaderLabels(["Hora", "Acción", "Resultado", "Detalle"])
        self.recent.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.recent.verticalHeader().setVisible(False)
        self.recent.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        g2 = QGroupBox("Operaciones de esta sesión")
        QVBoxLayout(g2).addWidget(self.recent)
        lay = QVBoxLayout(self); lay.addWidget(self.g); lay.addWidget(g2, 1)
        session.connection_changed.connect(self.refresh)
        session.operation_recorded.connect(self.add_op)
        self.refresh()

    def refresh(self, *_args) -> None:
        r, c = self.session.remote, self.session.config.connection
        if self.session.connected:
            self.badge.set_status("conectado", "Conectado")
        else:
            self.badge.set_status("desconectado", "Desconectado")
        self.l_host.setText(r.computer_name or f"{c.host_name} (esperado)")
        self.l_ip.setText(f"{c.address or '—'}:{c.port}")
        self.l_user.setText(f"{r.user} ({'administrador' if r.is_admin else 'estándar'})" if r.user else "—")
        self.l_os.setText(r.os_caption or "—")
        self.l_ps.setText(r.ps_version or "—")

    def add_op(self, op: OpResult) -> None:
        self.recent.insertRow(0)
        for col, val in enumerate([f"{op.started_at:%H:%M:%S}", f"{op.action} · {op.action_name}",
                                   op.status, op.error or op.message]):
            self.recent.setItem(0, col, QTableWidgetItem(val))
        self.recent.resizeColumnsToContents()


class HistoryPage(QWidget):
    COLS = ["inicio", "accion", "nombre_accion", "resultado", "ejecutada", "verificada", "destino", "mensaje", "error"]

    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(["Inicio", "Acción", "Nombre", "Resultado", "Ejecutada",
                                              "Verificada", "Destino", "Mensaje", "Error"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.info = QLabel(); self.info.setObjectName("muted")
        btn_open = QPushButton("Abrir carpeta local del historial")
        btn_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.session.log.folder))))
        top = QHBoxLayout(); top.addWidget(self.info, 1); top.addWidget(btn_open)
        lay = QVBoxLayout(self); lay.addLayout(top); lay.addWidget(self.table, 1)
        session.operation_recorded.connect(self.reload)
        session.config_changed.connect(self.reload)
        self.reload()

    def reload(self, *_args) -> None:
        rows = self.session.log.rows()
        self.table.setRowCount(len(rows))
        for r, row in enumerate(reversed(rows)):
            for c, key in enumerate(self.COLS):
                self.table.setItem(r, c, QTableWidgetItem(row.get(key, "")))
        self.table.resizeColumnsToContents()
        pend = len(self.session.log.pending_ids())
        self.info.setText(f"{len(rows)} operaciones registradas en {self.session.log.csv_path} · "
                          f"{pend} pendientes de sincronizar con BOSGAME")


class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        logo = QLabel(); logo.setPixmap(app_icon().pixmap(QSize(96, 96)))
        name = QLabel(f"{APP_NAME} {APP_VERSION}"); name.setObjectName("title")
        text = QLabel(
            "<p><b>Propósito:</b> monitorear, administrar y mantener de forma remota el mini PC BOSGAME "
            "por la red local, dejando evidencias verificables de cada operación.</p>"
            "<p><b>Compatibilidad:</b> cliente Windows 10/11 (64 bits). Equipo remoto: Windows con OpenSSH Server.</p>"
            "<p><b>Mecanismo remoto:</b> SSH + PowerShell para comandos, SFTP para transferencias.</p>"
            "<p><b>Créditos y licencias de terceros:</b><br>"
            "Qt for Python / PySide6 — LGPL v3<br>paramiko — LGPL v2.1<br>keyring — MIT<br>pydantic — MIT</p>"
        )
        text.setWordWrap(True)
        text.setTextFormat(Qt.TextFormat.RichText)
        lay = QVBoxLayout(self)
        head = QHBoxLayout(); head.addWidget(logo); head.addWidget(name, 1)
        lay.addLayout(head); lay.addWidget(text); lay.addStretch()


class MainWindow(QMainWindow):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self.setWindowTitle(f"{APP_NAME} — administración remota de BOSGAME")
        self.setWindowIcon(app_icon())
        self.resize(1180, 780)

        self.header = Header(session)
        self.nav = QListWidget(); self.nav.setObjectName("nav"); self.nav.setFixedWidth(230)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.stack = QStackedWidget()
        pages = [
            ("Panel principal", DashboardPage(session)),
            ("Conexión y estudiante", ConnectionPage(session)),
            ("Historial e informes", HistoryPage(session)),
            ("Acerca de", AboutPage()),
        ]
        for title, page in pages:
            self.nav.addItem(QListWidgetItem(title))
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self._go)

        content = QWidget(); content.setObjectName("content")
        cl = QVBoxLayout(content); cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(0)
        cl.addWidget(self.header)
        inner = QWidget(); il = QVBoxLayout(inner); il.setContentsMargins(16, 12, 16, 16); il.addWidget(self.stack)
        cl.addWidget(inner, 1)

        central = QWidget()
        h = QHBoxLayout(central); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        h.addWidget(self.nav); h.addWidget(content, 1)
        self.setCentralWidget(central)
        # Sin conexión configurada, se abre directamente en Conexión.
        self.nav.setCurrentRow(0 if session.config.connection.address else 1)

    def _go(self, row: int) -> None:
        self.stack.setCurrentIndex(row)
        self.header.set_title(self.nav.item(row).text())

    def closeEvent(self, event) -> None:
        # Cerrar la sesión remota libera transporte y canales SFTP.
        self.session.backend.close()
        super().closeEvent(event)
