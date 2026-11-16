"""Sección 'Conexión y estudiante': acciones 1, 2, 3 y 4."""
from __future__ import annotations

from pydantic import ValidationError
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from ..app.config import (
    AppConfig, ConnectionConfig, LabConfig, StudentConfig, delete_password, load_password, save_password,
)
from ..app.session import Session
from ..core.paths import PathValidationError, personal_root
from ..core.result import OpResult
from ..ops import workspace
from ..remote.backend import UnknownHostKey
from .workers import run_async


def format_op(op: OpResult) -> str:
    lines = [f"[{op.started_at:%H:%M:%S}] Acción {op.action} · {op.action_name} → {op.status.upper()}"]
    if op.command:
        lines.append("  Instrucción:\n" + "\n".join("    " + l for l in op.command.splitlines()))
    if op.message:
        lines.append("  " + op.message)
    if op.error:
        lines.append("  Error: " + op.error)
    return "\n".join(lines) + "\n"


class ConnectionPage(QWidget):
    def __init__(self, session: Session):
        super().__init__()
        self.session = session
        self._busy = False

        # -- Equipo remoto (acción 1) --
        self.host_name = QLineEdit()
        self.address = QLineEdit()
        self.address.setPlaceholderText("p. ej. 192.168.1.50")
        self.port = QSpinBox(); self.port.setRange(1, 65535)
        self.username = QLineEdit()
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Se toma del Administrador de credenciales si está guardada")
        self.remember = QCheckBox("Guardar contraseña en el Administrador de credenciales de Windows")
        self.timeout = QDoubleSpinBox(); self.timeout.setRange(1, 120); self.timeout.setSuffix(" s")
        g1 = QGroupBox("Equipo remoto (BOSGAME)")
        f1 = QFormLayout(g1)
        f1.addRow("Nombre esperado", self.host_name)
        f1.addRow("IP o nombre DNS", self.address)
        f1.addRow("Puerto SSH", self.port)
        f1.addRow("Usuario", self.username)
        f1.addRow("Contraseña", self.password)
        f1.addRow("", self.remember)
        f1.addRow("Tiempo de espera", self.timeout)

        # -- Parámetros del laboratorio --
        self.base_path = QLineEdit()
        self.range_start = QSpinBox(); self.range_start.setRange(1, 65535)
        self.range_end = QSpinBox(); self.range_end.setRange(1, 65535)
        self.practice_service = QLineEdit()
        self.practice_port = QSpinBox(); self.practice_port.setRange(0, 65535); self.practice_port.setSpecialValueText("(sin definir)")
        self.services = QLineEdit(); self.services.setPlaceholderText("Nombres separados por coma, p. ej. sshd, W3SVC")
        self.cpu_interval = QDoubleSpinBox(); self.cpu_interval.setRange(0.2, 10); self.cpu_interval.setSingleStep(0.5); self.cpu_interval.setSuffix(" s")
        g2 = QGroupBox("Parámetros del laboratorio (los entrega el docente)")
        f2 = QFormLayout(g2)
        f2.addRow("Carpeta base", self.base_path)
        rng = QHBoxLayout(); rng.addWidget(self.range_start); rng.addWidget(QLabel("a")); rng.addWidget(self.range_end)
        f2.addRow("Rango TCP autorizado", rng)
        f2.addRow("Servicio de práctica", self.practice_service)
        f2.addRow("Puerto de práctica", self.practice_port)
        f2.addRow("Servicios a consultar", self.services)
        f2.addRow("Intervalo de CPU", self.cpu_interval)

        # -- Estudiante (acción 2) --
        self.full_name = QLineEdit()
        self.group = QLineEdit()
        self.student_id = QLineEdit(); self.student_id.setPlaceholderText("p. ej. AMartinez")
        self.root_preview = QLabel(); self.root_preview.setObjectName("muted")
        g3 = QGroupBox("Estudiante")
        f3 = QFormLayout(g3)
        f3.addRow("Nombre completo", self.full_name)
        f3.addRow("Grupo", self.group)
        f3.addRow("Identificador", self.student_id)
        f3.addRow("Carpeta personal", self.root_preview)
        for w in (self.base_path, self.student_id):
            w.textChanged.connect(self._update_preview)

        # -- Botones --
        self.btn_save = QPushButton("Guardar configuración")
        self.btn_connect = QPushButton("Conectar")
        self.btn_prepare = QPushButton("Preparar carpeta personal")
        self.btn_identify = QPushButton("Registrar identificación")
        self.btn_save.clicked.connect(self.on_save)
        self.btn_connect.clicked.connect(self.on_connect_toggle)
        self.btn_prepare.clicked.connect(self.on_prepare)
        self.btn_identify.clicked.connect(self.on_identify)
        buttons = QHBoxLayout()
        for b in (self.btn_save, self.btn_connect, self.btn_prepare, self.btn_identify):
            buttons.addWidget(b)
        buttons.addStretch()

        self.console = QPlainTextEdit(); self.console.setObjectName("console"); self.console.setReadOnly(True)
        self.console.setMinimumHeight(160)

        grid = QGridLayout()
        grid.addWidget(g1, 0, 0)
        grid.addWidget(g2, 0, 1)
        grid.addWidget(g3, 1, 0, 1, 2)
        root = QVBoxLayout(self)
        root.addLayout(grid)
        root.addLayout(buttons)
        root.addWidget(QLabel("Resultado de las operaciones"))
        root.addWidget(self.console, 1)

        self.load_from(session.config)
        session.connection_changed.connect(self._on_connection_changed)
        session.config_changed.connect(self._refresh_buttons)
        self._refresh_buttons()

    # -- formulario <-> configuración ------------------------------------------
    def load_from(self, cfg: AppConfig) -> None:
        c, l, s = cfg.connection, cfg.lab, cfg.student
        self.host_name.setText(c.host_name); self.address.setText(c.address); self.port.setValue(c.port)
        self.username.setText(c.username); self.timeout.setValue(c.timeout_s)
        self.base_path.setText(l.base_path); self.range_start.setValue(l.tcp_range_start); self.range_end.setValue(l.tcp_range_end)
        self.practice_service.setText(l.practice_service); self.practice_port.setValue(l.practice_port or 0)
        self.services.setText(", ".join(l.services_to_query)); self.cpu_interval.setValue(l.cpu_interval_s)
        self.full_name.setText(s.full_name); self.group.setText(s.group); self.student_id.setText(s.student_id)
        self.remember.setChecked(bool(c.address and c.username and load_password(c)))
        self._update_preview()

    def build_config(self) -> AppConfig:
        """Construye y valida la configuración. Lanza ValidationError si algo es inválido."""
        return AppConfig(
            connection=ConnectionConfig(
                host_name=self.host_name.text().strip(), address=self.address.text(), port=self.port.value(),
                username=self.username.text(), timeout_s=self.timeout.value()),
            lab=LabConfig(
                base_path=self.base_path.text(), tcp_range_start=self.range_start.value(),
                tcp_range_end=self.range_end.value(), practice_service=self.practice_service.text(),
                practice_port=self.practice_port.value() or None,
                services_to_query=self.services.text().split(","), cpu_interval_s=self.cpu_interval.value()),
            student=StudentConfig(full_name=self.full_name.text(), group=self.group.text(),
                                  student_id=self.student_id.text()),
            local_dir=self.session.config.local_dir,
        )

    def _update_preview(self) -> None:
        try:
            self.root_preview.setText(personal_root(self.base_path.text(), self.student_id.text()))
            self.student_id.setProperty("invalid", False)
        except PathValidationError as e:
            self.root_preview.setText(f"⚠ {e}")
            self.student_id.setProperty("invalid", bool(self.student_id.text()))
        self.student_id.style().unpolish(self.student_id); self.student_id.style().polish(self.student_id)

    def _apply_form(self) -> bool:
        try:
            cfg = self.build_config()
        except ValidationError as e:
            msgs = [f"• {'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()]
            QMessageBox.warning(self, "Configuración no válida", "Corrige estos campos:\n\n" + "\n".join(msgs))
            return False
        if self.session.connected and (cfg.connection != self.session.config.connection):
            QMessageBox.information(self, "Conexión activa",
                                    "Desconecta antes de cambiar los parámetros de acceso.")
            return False
        cfg.save()
        pwd = self.password.text()
        if self.remember.isChecked() and pwd:
            save_password(cfg.connection, pwd)
        elif not self.remember.isChecked():
            delete_password(cfg.connection)
        self.session.set_config(cfg)
        return True

    # -- acciones ----------------------------------------------------------------
    def on_save(self) -> None:
        if self._apply_form():
            self.log(f"Configuración guardada en {AppConfig.path()} (sin contraseñas).\n")

    def on_connect_toggle(self) -> None:
        if self.session.connected:
            self._start(workspace.disconnect, self.session)
            return
        if not self._apply_form():
            return
        c = self.session.config.connection
        if not c.address or not c.username:
            QMessageBox.warning(self, "Faltan datos", "Indica la IP o el nombre del equipo y el usuario.")
            return
        pwd = self.password.text() or load_password(c)
        if not pwd:
            QMessageBox.warning(self, "Falta la contraseña",
                                "Escribe la contraseña (o guárdala en el Administrador de credenciales).")
            return
        self.log(f"Conectando a {c.address}:{c.port} como {c.username}…\n")
        self._start(workspace.connect, self.session, pwd, on_fail=lambda e: self._connect_failed(e, pwd))

    def _connect_failed(self, e: Exception, pwd: str) -> None:
        self._set_busy(False)
        if isinstance(e, UnknownHostKey):
            answer = QMessageBox.question(
                self, "Confirmar identidad del equipo",
                f"Es la primera conexión a {e.address}.\n\nHuella {e.key_type}:\nSHA256:{e.fingerprint}\n\n"
                "Compárala con la de BOSGAME. En BOSGAME ejecuta:\n"
                "ssh-keygen -lf C:\\ProgramData\\ssh\\ssh_host_ed25519_key.pub\n\n¿Confías en este equipo?")
            if answer == QMessageBox.StandardButton.Yes:
                c = self.session.config.connection
                self.session.backend.trust_host_key(c.address, c.port, e.key)  # type: ignore[attr-defined]
                self.log("Huella guardada. Reintentando…\n")
                self._start(workspace.connect, self.session, pwd)
            return
        self._show_error(e)

    def on_prepare(self) -> None:
        if self._apply_form():
            self._start(workspace.prepare_workspace, self.session)

    def on_identify(self) -> None:
        if self._apply_form():
            self._start(workspace.write_identification, self.session)

    # -- utilidades -------------------------------------------------------------
    def _start(self, fn, *args, on_fail=None) -> None:
        self._set_busy(True)
        run_async(fn, *args, on_done=self._done, on_fail=on_fail or self._show_error)

    def _done(self, op: OpResult) -> None:
        self._set_busy(False)
        self.log(format_op(op))
        if op.action == 4 and isinstance(op.data, list):
            for item in op.data:
                state = "creado" if item["existe"] and not item["existia"] else ("conservado" if item["existe"] else "FALTA")
                self.log(f"    {item['tipo']:<8} {state:<10} {item['ruta']}\n")

    def _show_error(self, e: Exception) -> None:
        self._set_busy(False)
        hint = getattr(e, "hint", "")
        self.log(f"Error: {e} {hint}\n")
        QMessageBox.critical(self, "Operación fallida", f"{e}\n\n{hint}".strip())

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._refresh_buttons()

    def _on_connection_changed(self, _connected: bool) -> None:
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        connected = self.session.connected
        ready = connected and self.session.config.student.complete and not self._busy
        self.btn_connect.setText("Desconectar" if connected else ("Conectando…" if self._busy else "Conectar"))
        self.btn_connect.setEnabled(not self._busy)
        self.btn_save.setEnabled(not self._busy)
        self.btn_prepare.setEnabled(ready)
        self.btn_identify.setEnabled(ready)
        tip = "" if ready else "Requiere conexión activa y datos completos del estudiante (guardados)."
        self.btn_prepare.setToolTip(tip); self.btn_identify.setToolTip(tip)

    def log(self, text: str) -> None:
        self.console.appendPlainText(text.rstrip("\n"))
