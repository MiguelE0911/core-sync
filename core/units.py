"""Unidades consistentes.

Memoria y almacenamiento se muestran siempre en GiB (1 GiB = 1 073 741 824 bytes).
La memoria de procesos se muestra en MiB (1 MiB = 1 048 576 bytes).
"""
from __future__ import annotations

KIB = 1024
MIB = 1024 ** 2
GIB = 1024 ** 3


def gib(n: float | int | None, decimals: int = 2) -> str:
    return "No disponible" if n is None else f"{n / GIB:,.{decimals}f} GiB"


def mib(n: float | int | None, decimals: int = 1) -> str:
    return "No disponible" if n is None else f"{n / MIB:,.{decimals}f} MiB"


def pct(part: float | None, total: float | None, decimals: int = 1) -> float | None:
    if part is None or not total:
        return None
    return round(part * 100 / total, decimals)


def or_na(value) -> str:
    return "No disponible" if value in (None, "") else str(value)
