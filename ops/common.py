"""Utilidades compartidas por las operaciones."""
from __future__ import annotations

from app.session import Session
from core.result import OpResult
from remote.backend import RemoteError


def run_body(session: Session, op: OpResult, body: str, timeout_s: float = 60) -> bool:
    """Ejecuta el script en BOSGAME y vuelca el resultado en `op`. Devuelve True si se ejecutó."""
    op.command = op.command or body.strip()
    try:
        res = session.backend.run_ps(body, timeout_s=timeout_s)
    except RemoteError as e:
        op.error = str(e) + (f" {e.hint}" if e.hint else "")
        return False
    if res.ok:
        op.executed = True
        op.data = res.data
        return True
    op.error = res.error
    return False
