"""Validación de identificadores, nombres y rutas remotas (Windows).

Toda ruta que la app construye para BOSGAME pasa por aquí. Reglas:
- El identificador del estudiante no admite separadores ni secuencias que
  permitan salir de la carpeta asignada.
- Cualquier ruta efectiva debe quedar dentro de la carpeta personal
  (se comprueba también en el lado remoto con [IO.Path]::GetFullPath).
"""
from __future__ import annotations

import ntpath
import re

_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_INVALID_NAME_CHARS = set('<>:"/\\|?*')
_STUDENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,40}$")


class PathValidationError(ValueError):
    """Entrada rechazada por violar las reglas de rutas."""


def validate_student_id(value: str) -> str:
    value = (value or "").strip()
    if not _STUDENT_ID_RE.fullmatch(value):
        raise PathValidationError(
            "El identificador debe tener de 3 a 40 caracteres: letras sin tilde, "
            "números, guion o guion bajo (sin espacios, puntos ni separadores)."
        )
    if value.upper() in _RESERVED:
        raise PathValidationError(f"'{value}' es un nombre reservado de Windows.")
    return value


def validate_name(value: str, what: str = "nombre") -> str:
    """Valida un nombre de archivo o carpeta (un solo componente)."""
    if value is None or value.strip() == "":
        raise PathValidationError(f"El {what} no puede estar vacío.")
    if value != value.strip() or value.endswith("."):
        raise PathValidationError(f"El {what} no puede empezar/terminar con espacios ni terminar en punto.")
    if value in (".", ".."):
        raise PathValidationError(f"El {what} no puede ser '.' ni '..'.")
    if len(value) > 120:
        raise PathValidationError(f"El {what} supera 120 caracteres.")
    bad = sorted({c for c in value if c in _INVALID_NAME_CHARS or ord(c) < 32})
    if bad:
        shown = " ".join(repr(c) for c in bad)
        raise PathValidationError(f"El {what} contiene caracteres no permitidos: {shown}")
    stem = value.split(".")[0].upper()
    if stem in _RESERVED:
        raise PathValidationError(f"'{value}' usa un nombre reservado de Windows.")
    return value


def validate_base_path(value: str) -> str:
    """Valida la carpeta base del laboratorio (p. ej. C:\\Laboratorio)."""
    value = (value or "").strip()
    if not re.fullmatch(r"[A-Za-z]:\\.*", value):
        raise PathValidationError("La carpeta base debe ser una ruta absoluta de Windows, p. ej. C:\\Laboratorio")
    if ".." in re.split(r"[\\/]", value):
        raise PathValidationError("La carpeta base no puede contener '..'.")
    norm = ntpath.normpath(value)
    return norm.rstrip("\\") if len(norm) > 3 else norm


def personal_root(base_path: str, student_id: str) -> str:
    return ntpath.join(validate_base_path(base_path), validate_student_id(student_id))


def is_within(root: str, candidate: str) -> bool:
    """True si `candidate` (normalizada) es `root` o está dentro de ella."""
    r = ntpath.normcase(ntpath.normpath(root)).rstrip("\\")
    c = ntpath.normcase(ntpath.normpath(candidate))
    return c == r or c.startswith(r + "\\")


def join_inside(root: str, *parts: str) -> str:
    """Une componentes relativos a `root` y garantiza que el resultado no salga de ella."""
    for p in parts:
        if ntpath.isabs(p) or p.startswith("\\\\") or ":" in p:
            raise PathValidationError(f"Se esperaba una ruta relativa: {p!r}")
    path = ntpath.normpath(ntpath.join(root, *parts))
    if not is_within(root, path):
        raise PathValidationError("La ruta resultante sale de la carpeta personal.")
    return path
