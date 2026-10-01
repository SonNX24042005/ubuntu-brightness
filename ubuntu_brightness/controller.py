"""Xử lý thiết bị tuần tự ngoài luồng giao diện và gộp các lần kéo thanh trượt."""

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Callable

from .models import Brightness, Discovery, Display


class Controller:
    def __init__(self, backend, dispatch: Callable[..., None]) -> None:
        self.backend = backend
        self.dispatch = dispatch
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="brightness")
        self.lock = Lock()
        self.pending = OrderedDict()
        self.running = False
        self.closed = False

    @property
    def busy(self) -> bool:
        with self.lock:
            return self.running or bool(self.pending)

    def discover(self, callback: Callable[[Discovery | None, Exception | None], None]) -> None:
        def work() -> None:
            try:
                result = self.backend.discover()
            except Exception as exc:
                self.dispatch(callback, None, exc)
            else:
                self.dispatch(callback, result, None)

        with self.lock:
            if not self.closed:
                self.executor.submit(work)

    def set(self, display: Display, percent: int, callback: Callable) -> None:
        with self.lock:
            if self.closed:
                return
            self.pending[display.identifier] = (display, percent, callback)
            if not self.running:
                self.running = True
                self.executor.submit(self._drain)

    def _drain(self) -> None:
        while True:
            with self.lock:
                if not self.pending:
                    self.running = False
                    return
                _, (display, percent, callback) = self.pending.popitem(last=False)
            brightness: Brightness | None = None
            error = None
            try:
                brightness = self.backend.set(display, percent)
            except Exception as exc:
                error = exc
            self.dispatch(callback, display.identifier, percent, brightness, error)

    def close(self) -> None:
        with self.lock:
            self.closed = True
        self.executor.shutdown(wait=False)
