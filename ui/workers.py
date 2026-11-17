"""Ejecución en segundo plano: ninguna consulta remota bloquea el hilo de la UI.

Los resultados vuelven al hilo de la interfaz a través de `_Relay`, un QObject
creado en ese hilo. Así, los callbacks (incluidas las lambdas) se ejecutan
siempre en el hilo principal mediante una conexión en cola.
"""
from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class WorkerSignals(QObject):
    done = Signal(object)
    failed = Signal(object)    # Exception
    progress = Signal(object)


class Worker(QRunnable):
    def __init__(self, fn: Callable[..., Any], *args, **kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:  # se informa a la UI, nunca se pierde en silencio
            e.__coresync_tb__ = traceback.format_exc()  # type: ignore[attr-defined]
            self.signals.failed.emit(e)
        else:
            self.signals.done.emit(result)


class _Relay(QObject):
    """Vive en el hilo de la UI; recibe las señales del worker en cola."""

    def __init__(self, worker: Worker, on_done, on_fail, on_progress):
        super().__init__()
        self.worker, self.on_done, self.on_fail, self.on_progress = worker, on_done, on_fail, on_progress

    @Slot(object)
    def done(self, result: Any) -> None:
        _alive.discard(self)
        if self.on_done:
            self.on_done(result)

    @Slot(object)
    def failed(self, exc: Exception) -> None:
        _alive.discard(self)
        if self.on_fail:
            self.on_fail(exc)

    @Slot(object)
    def progress(self, value: Any) -> None:
        if self.on_progress:
            self.on_progress(value)


_alive: set[_Relay] = set()


def run_async(fn: Callable[..., Any], *args,
              on_done: Callable[[Any], None] | None = None,
              on_fail: Callable[[Exception], None] | None = None,
              on_progress: Callable[[Any], None] | None = None,
              **kwargs) -> Worker:
    """Ejecuta fn en el pool. Si fn acepta `progress`, recibe un emisor de avance."""
    w = Worker(fn, *args, **kwargs)
    relay = _Relay(w, on_done, on_fail, on_progress)
    _alive.add(relay)
    w.signals.done.connect(relay.done)
    w.signals.failed.connect(relay.failed)
    w.signals.progress.connect(relay.progress)
    w.setAutoDelete(False)
    QThreadPool.globalInstance().start(w)
    return w
