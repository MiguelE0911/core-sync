"""Plantillas PowerShell seguras.

- Los parámetros se insertan como literales de comilla simple escapados
  (`ps_str`), nunca concatenando texto del usuario sin escapar.
- El script completo se envía con -EncodedCommand (UTF-16LE + base64): evita
  problemas de comillas con cmd.exe, que es el shell por defecto de OpenSSH
  en Windows.
- El script se envuelve para devolver siempre JSON: {ok, data} o {ok, error}.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

# PowerShell también trata como comilla simple estas variantes tipográficas.
_SINGLE_QUOTES = ("'", "‘", "’", "‚", "‛")


def ps_str(value: str) -> str:
    """Convierte un texto en literal PowerShell de comilla simple."""
    if "\x00" in value:
        raise ValueError("El valor contiene un carácter nulo.")
    out = value
    for q in _SINGLE_QUOTES:
        out = out.replace(q, q + q)
    return f"'{out}'"


def ps_int(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("Se esperaba un entero.")
    return str(value)


def ps_str_array(values: list[str]) -> str:
    return "@(" + ",".join(ps_str(v) for v in values) + ")"


_WRAPPER = """$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try {{
    $__data = & {{
{body}
    }}
    [pscustomobject]@{{ ok = $true; data = $__data }} | ConvertTo-Json -Depth 8 -Compress
}} catch {{
    [pscustomobject]@{{
        ok = $false
        error = $_.Exception.Message
        category = [string]$_.CategoryInfo.Category
        exception = $_.Exception.GetType().FullName
    }} | ConvertTo-Json -Compress
    exit 1
}}"""


def wrap(body: str) -> str:
    indented = "\n".join("        " + line for line in body.strip("\n").splitlines())
    return _WRAPPER.format(body=indented)


def encode_command(script: str) -> str:
    """Línea de comando completa para ejecutar `script` en el equipo remoto."""
    b64 = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return (
        "powershell.exe -NoLogo -NoProfile -NonInteractive "
        "-ExecutionPolicy Bypass -EncodedCommand " + b64
    )


@dataclass
class PSResult:
    script: str          # cuerpo legible (lo que se muestra al usuario)
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    ok: bool = False
    data: Any = None
    error: str = ""

    @classmethod
    def parse(cls, script: str, exit_code: int, stdout: str, stderr: str, duration_s: float) -> "PSResult":
        res = cls(script, exit_code, stdout, stderr, duration_s)
        payload = _last_json_line(stdout)
        if payload is None:
            res.error = _clean_stderr(stderr) or f"Respuesta no reconocida (código {exit_code})."
            return res
        res.ok = bool(payload.get("ok")) and exit_code == 0
        res.data = payload.get("data")
        if not res.ok:
            res.error = payload.get("error") or _clean_stderr(stderr) or f"Falló con código {exit_code}."
        return res


def _last_json_line(stdout: str) -> dict | None:
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip().lstrip("﻿")
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                return None
    return None


def _clean_stderr(stderr: str) -> str:
    # PowerShell puede emitir registros CLIXML; se descartan para mostrar algo legible.
    lines = [l for l in stderr.splitlines() if l.strip() and not l.startswith("#< CLIXML") and not l.startswith("<Objs")]
    return "\n".join(lines).strip()


def as_list(value: Any) -> list:
    """ConvertTo-Json desenvuelve arreglos de un elemento; esto lo normaliza."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]
