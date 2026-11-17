"""Estado de la sesión: configuración, conexión, identidad e historial."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import uuid

from PySide6.QtCore import QObject, Signal

from core.paths import personal_root
from core.result import OpResult
from records.activity import ActivityLog, to_row
from remote.backend import RemoteBackend
from remote.ssh_backend import SSHBackend
from app.config import AppConfig, app_data_dir


def new_session_id() -> str:
    return f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"


@dataclass
class RemoteIdentity:
    computer_name: str = ""
    user: str = ""
    is_admin: bool = False
    os_caption: str = ""
    ps_version: str = ""


class Session(QObject):
    """Objeto compartido por toda la interfaz. Emite señales al cambiar."""

    connection_changed = Signal(bool)
    operation_recorded = Signal(object)  # OpResult
    config_changed = Signal()

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.session_id = new_session_id()
        self.backend: RemoteBackend = SSHBackend(app_data_dir() / "known_hosts")
        self.remote = RemoteIdentity()
        self.log = ActivityLog(config.local_path("Historial"))

    # -- estado --------------------------------------------------------------
    @property
    def connected(self) -> bool:
        return self.backend.is_connected()

    @property
    def personal_root(self) -> str:
        s = self.config.student
        return personal_root(self.config.lab.base_path, s.student_id)

    def set_config(self, config: AppConfig) -> None:
        self.config = config
        self.log = ActivityLog(config.local_path("Historial"))
        self.config_changed.emit()

    # -- historial -----------------------------------------------------------
    def record(self, op: OpResult) -> OpResult:
        if op.finished_at is None:
            op.finish()
        s = self.config.student
        host = self.remote.computer_name or self.config.connection.host_name
        self.log.append(to_row(op, self.session_id, s.student_id, s.full_name, host))
        self.operation_recorded.emit(op)
        return op
