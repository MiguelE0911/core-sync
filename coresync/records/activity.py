"""Historial de operaciones (registro mínimo del enunciado).

Cada operación se guarda localmente en actividad.csv con un op_id único.
Las filas aún no copiadas a BOSGAME quedan en pendientes.json. La
sincronización (fase 5) usa op_id para no duplicar filas.
"""
from __future__ import annotations

import csv
import json
import threading
from pathlib import Path

from ..core.result import OpResult

COLUMNS = [
    "op_id", "sesion", "estudiante_id", "estudiante", "equipo", "inicio", "fin", "zona_horaria",
    "accion", "nombre_accion", "parametros", "origen", "destino", "ejecutada", "verificada",
    "resultado", "mensaje", "error", "evidencia",
]


def to_row(op: OpResult, session_id: str, student_id: str, student_name: str, host: str) -> dict[str, str]:
    fin = op.finished_at or op.started_at
    return {
        "op_id": op.op_id,
        "sesion": session_id,
        "estudiante_id": student_id,
        "estudiante": student_name,
        "equipo": host,
        "inicio": op.started_at.isoformat(timespec="seconds"),
        "fin": fin.isoformat(timespec="seconds"),
        "zona_horaria": str(op.started_at.tzname() or ""),
        "accion": str(op.action),
        "nombre_accion": op.action_name,
        "parametros": json.dumps(op.params, ensure_ascii=False, default=str),
        "origen": op.source,
        "destino": op.destination,
        "ejecutada": "sí" if op.executed else "no",
        "verificada": "sí" if op.verified else "no",
        "resultado": op.status,
        "mensaje": op.message.replace("\n", " "),
        "error": op.error.replace("\n", " "),
        "evidencia": op.evidence,
    }


class ActivityLog:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.folder / "actividad.csv"
        self.pending_path = self.folder / "pendientes.json"
        self._lock = threading.Lock()

    def append(self, row: dict[str, str]) -> None:
        with self._lock:
            new = not self.csv_path.exists()
            # utf-8-sig para que Excel muestre bien las tildes
            with self.csv_path.open("a", newline="", encoding="utf-8-sig" if new else "utf-8") as f:
                w = csv.DictWriter(f, fieldnames=COLUMNS)
                if new:
                    w.writeheader()
                w.writerow(row)
            pending = self._read_pending()
            if row["op_id"] not in pending:
                pending.append(row["op_id"])
            self._write_pending(pending)

    def rows(self) -> list[dict[str, str]]:
        if not self.csv_path.exists():
            return []
        with self._lock, self.csv_path.open(newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def pending_ids(self) -> list[str]:
        with self._lock:
            return self._read_pending()

    def mark_synced(self, op_ids: list[str]) -> None:
        with self._lock:
            done = set(op_ids)
            self._write_pending([i for i in self._read_pending() if i not in done])

    def _read_pending(self) -> list[str]:
        if not self.pending_path.exists():
            return []
        try:
            return list(json.loads(self.pending_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, TypeError):
            return []

    def _write_pending(self, ids: list[str]) -> None:
        tmp = self.pending_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(ids), encoding="utf-8")
        tmp.replace(self.pending_path)
