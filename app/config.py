"""Configuración persistente (acción 1).

- Parámetros no sensibles en %APPDATA%\\CoreSync\\config.json (editable).
- La contraseña se guarda solo en el Administrador de credenciales de Windows
  mediante `keyring`; nunca en el JSON ni en el código.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
from pathlib import Path

import keyring
import keyring.errors
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from core.paths import validate_base_path, validate_student_id

KEYRING_SERVICE = "CoreSync"
_HOSTNAME_RE = re.compile(r"^(?=.{1,253}$)[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$")


def app_data_dir() -> Path:
    base = os.environ.get("CORESYNC_HOME") or os.path.join(os.environ.get("APPDATA", str(Path.home())), "CoreSync")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


class ConnectionConfig(BaseModel):
    host_name: str = Field("BOSGAME", description="Nombre esperado del equipo remoto")
    address: str = ""
    port: int = 22
    username: str = ""
    timeout_s: float = 8.0

    @field_validator("address")
    @classmethod
    def _addr(cls, v: str) -> str:
        v = v.strip()
        if not v:
            return v
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            # "192.168.1.300" no es IP válida y tampoco debe pasar como nombre DNS.
            if _HOSTNAME_RE.fullmatch(v) and not re.fullmatch(r"[\d.]+", v):
                return v
        raise ValueError("Dirección no válida: usa una IP (p. ej. 192.168.1.50) o un nombre de equipo.")

    @field_validator("port")
    @classmethod
    def _port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError("El puerto debe estar entre 1 y 65535.")
        return v

    @field_validator("username")
    @classmethod
    def _user(cls, v: str) -> str:
        v = v.strip()
        if any(c in v for c in '"/[]:;|=,+*?<>'):
            raise ValueError("El usuario contiene caracteres no permitidos.")
        return v

    @field_validator("timeout_s")
    @classmethod
    def _timeout(cls, v: float) -> float:
        if not 1 <= v <= 120:
            raise ValueError("El tiempo de espera debe estar entre 1 y 120 s.")
        return v


class LabConfig(BaseModel):
    base_path: str = r"C:\Laboratorio"
    tcp_range_start: int = 8000
    tcp_range_end: int = 8010
    practice_service: str = ""
    practice_port: int | None = None
    services_to_query: list[str] = Field(default_factory=list)
    cpu_interval_s: float = 1.0

    @field_validator("base_path")
    @classmethod
    def _base(cls, v: str) -> str:
        return validate_base_path(v)

    @field_validator("practice_service")
    @classmethod
    def _svc(cls, v: str) -> str:
        v = v.strip()
        if v and not re.fullmatch(r"[A-Za-z0-9_.\-]{1,80}", v):
            raise ValueError("Nombre de servicio no válido (usa el nombre corto del servicio).")
        return v

    @field_validator("services_to_query")
    @classmethod
    def _svcs(cls, v: list[str]) -> list[str]:
        out = [s.strip() for s in v if s.strip()]
        for s in out:
            if not re.fullmatch(r"[A-Za-z0-9_.\-]{1,80}", s):
                raise ValueError(f"Nombre de servicio no válido: {s!r}")
        return out

    @model_validator(mode="after")
    def _range(self) -> "LabConfig":
        for p in (self.tcp_range_start, self.tcp_range_end):
            if not 1 <= p <= 65535:
                raise ValueError("Los puertos del rango deben estar entre 1 y 65535.")
        if self.tcp_range_start > self.tcp_range_end:
            raise ValueError("El inicio del rango TCP no puede ser mayor que el final.")
        if self.tcp_range_end - self.tcp_range_start > 1024:
            raise ValueError("El rango TCP autorizado no debe superar 1025 puertos.")
        if self.practice_port is not None and not 1 <= self.practice_port <= 65535:
            raise ValueError("El puerto de práctica debe estar entre 1 y 65535.")
        if not 0.2 <= self.cpu_interval_s <= 10:
            raise ValueError("El intervalo de CPU debe estar entre 0.2 y 10 s.")
        return self


class StudentConfig(BaseModel):
    full_name: str = ""
    group: str = ""
    student_id: str = ""

    @field_validator("full_name", "group")
    @classmethod
    def _text(cls, v: str) -> str:
        v = " ".join(v.split())
        if any(ord(c) < 32 for c in v) or len(v) > 100:
            raise ValueError("Texto no válido o demasiado largo.")
        return v

    @field_validator("student_id")
    @classmethod
    def _sid(cls, v: str) -> str:
        return validate_student_id(v) if v.strip() else ""

    @property
    def complete(self) -> bool:
        return bool(self.full_name and self.group and self.student_id)


class AppConfig(BaseModel):
    connection: ConnectionConfig = Field(default_factory=ConnectionConfig)
    lab: LabConfig = Field(default_factory=LabConfig)
    student: StudentConfig = Field(default_factory=StudentConfig)
    local_dir: str = Field(default_factory=lambda: str(Path.home() / "Documents" / "CoreSync"))

    # -- persistencia ---------------------------------------------------------
    @staticmethod
    def path() -> Path:
        return app_data_dir() / "config.json"

    @classmethod
    def load(cls) -> "AppConfig":
        p = cls.path()
        if not p.exists():
            return cls()
        try:
            return cls.model_validate(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, ValidationError) as e:
            raise ConfigError(f"El archivo de configuración {p} no es válido:\n{e}") from e

    def save(self) -> Path:
        p = self.path()
        tmp = p.with_suffix(".tmp")
        tmp.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(p)
        return p

    def local_path(self, *parts: str) -> Path:
        p = Path(self.local_dir).joinpath(*parts)
        p.mkdir(parents=True, exist_ok=True)
        return p


class ConfigError(Exception):
    pass


# -- credenciales --------------------------------------------------------------
def _cred_key(cfg: ConnectionConfig) -> str:
    return f"{cfg.username}@{cfg.address}:{cfg.port}"


def save_password(cfg: ConnectionConfig, password: str) -> None:
    keyring.set_password(KEYRING_SERVICE, _cred_key(cfg), password)


def load_password(cfg: ConnectionConfig) -> str | None:
    try:
        return keyring.get_password(KEYRING_SERVICE, _cred_key(cfg))
    except keyring.errors.KeyringError:
        return None


def delete_password(cfg: ConnectionConfig) -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, _cred_key(cfg))
    except keyring.errors.PasswordDeleteError:
        pass
