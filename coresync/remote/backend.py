"""Interfaz del mecanismo remoto.

La interfaz y las operaciones dependen solo de esta clase. Así, si el docente
fija WinRM en lugar de SSH, basta con añadir otra implementación.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from .ps import PSResult

ProgressCallback = Callable[[int, int], None]  # (bytes_transferidos, bytes_totales)


@dataclass
class ConnectParams:
    address: str
    port: int
    username: str
    password: str
    timeout_s: float = 8.0


class RemoteError(Exception):
    """Fallo remoto con un mensaje que ayuda a resolverlo."""

    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.hint = hint


class UnknownHostKey(RemoteError):
    """Primera conexión a un equipo: el usuario debe confirmar la huella."""

    def __init__(self, address: str, key_type: str, fingerprint: str, key):
        super().__init__(
            f"Equipo no reconocido ({address}). Huella {key_type} SHA256:{fingerprint}",
            "Compara la huella con la de BOSGAME antes de confiar en ella.",
        )
        self.address = address
        self.key_type = key_type
        self.fingerprint = fingerprint
        self.key = key


class RemoteBackend(ABC):
    name: str = "abstracto"

    @abstractmethod
    def connect(self, params: ConnectParams) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def run_ps(self, body: str, timeout_s: float = 60.0) -> PSResult:
        """Ejecuta un cuerpo de script PowerShell (sin envolver) y devuelve el resultado parseado."""

    @abstractmethod
    def upload(self, local_path: str, remote_path: str, progress: ProgressCallback | None = None) -> None: ...

    @abstractmethod
    def download(self, remote_path: str, local_path: str, progress: ProgressCallback | None = None) -> None: ...

    @abstractmethod
    def rename(self, remote_src: str, remote_dst: str) -> None: ...
