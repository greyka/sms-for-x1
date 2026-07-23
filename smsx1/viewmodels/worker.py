"""Универсальный воркер: выполняет функцию в пуле потоков и отдаёт результат
сигналами. Держит UI отзывчивым при работе с netsh/WinRT.
"""
from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot, QThreadPool


class _Signals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class Worker(QRunnable):
    """Оборачивает вызов ``fn(*args, **kwargs)`` в фоновый поток."""

    def __init__(self, fn: Callable[..., Any], *args, **kwargs) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self.signals = _Signals()

    @Slot()
    def run(self) -> None:
        try:
            value = self._fn(*self._args, **self._kwargs)
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self.signals.error.emit(str(exc))
        else:
            self.signals.result.emit(value)
        finally:
            self.signals.finished.emit()


def run_async(fn: Callable[..., Any], *args,
              on_result: Callable[[Any], None] | None = None,
              on_error: Callable[[str], None] | None = None,
              on_finished: Callable[[], None] | None = None,
              **kwargs) -> Worker:
    """Запустить ``fn`` в глобальном пуле потоков, подписав колбэки."""
    worker = Worker(fn, *args, **kwargs)
    if on_result:
        worker.signals.result.connect(on_result)
    if on_error:
        worker.signals.error.connect(on_error)
    if on_finished:
        worker.signals.finished.connect(on_finished)
    QThreadPool.globalInstance().start(worker)
    return worker
