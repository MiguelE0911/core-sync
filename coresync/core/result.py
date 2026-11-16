"""Resultado uniforme de cada operación (base del historial y las evidencias)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def now_local() -> datetime:
    """Fecha y hora local con zona horaria explícita."""
    return datetime.now().astimezone()


@dataclass
class OpResult:
    action: int
    action_name: str
    params: dict[str, Any] = field(default_factory=dict)  # nunca contraseñas
    command: str = ""            # instrucción real mostrada al usuario
    source: str = ""
    destination: str = ""
    executed: bool = False       # la operación se ejecutó en BOSGAME
    verified: bool = False       # se comprobó el estado real posterior
    message: str = ""
    error: str = ""
    data: Any = None
    evidence: str = ""
    op_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: datetime = field(default_factory=now_local)
    finished_at: datetime | None = None

    def finish(self) -> "OpResult":
        self.finished_at = now_local()
        return self

    @property
    def status(self) -> str:
        if self.error:
            return "error"
        if self.executed and self.verified:
            return "verificado"
        if self.executed:
            return "ejecutado"
        return "no ejecutado"
