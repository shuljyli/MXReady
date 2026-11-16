"""Run trusted regex searches in a disposable process with a wall-clock deadline."""

from __future__ import annotations

import multiprocessing
import re
import sys
import time
from itertools import islice
from multiprocessing.process import BaseProcess
from types import TracebackType
from typing import Any, Protocol

from mxready.errors import MxReadyError


class _MessagePipe(Protocol):
    def send(self, message: object) -> None: ...
    def recv(self) -> Any: ...
    def poll(self, timeout: float) -> bool: ...
    def close(self) -> None: ...


def _search_worker(connection: _MessagePipe) -> None:
    cached: dict[tuple[str, str], str] = {}
    cached_bytes = 0
    try:
        connection.send(None)  # Ready to receive; the parent must not block on startup.
        while True:
            expression, flags, key, text, limit = connection.recv()
            if text is None:
                text = cached[key]
            elif cached_bytes + sys.getsizeof(text) <= 16 * 1024 * 1024:
                cached[key] = text
                cached_bytes += sys.getsizeof(text)
            matches = re.finditer(expression, text, flags)
            connection.send(
                (key in cached, [(match.start(), match.end()) for match in islice(matches, limit)])
            )
    except (EOFError, BrokenPipeError):
        return
    finally:
        connection.close()


class RegexMatcher:
    """One lazy worker per rule evaluation; no scanned code is imported or executed."""

    def __init__(self, deadline: float, max_matches: int) -> None:
        self.deadline = deadline
        self.max_matches = max_matches
        self.connection: _MessagePipe | None = None
        self.process: BaseProcess | None = None
        self.cached: set[tuple[str, str]] = set()
        self.ready = False

    def __enter__(self) -> RegexMatcher:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.connection is not None:
            self.connection.close()
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=1)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=1)
            self.process.close()

    def search(
        self, expression: str, flags: int, text: str, key: tuple[str, str]
    ) -> list[tuple[int, int]]:
        if self.connection is None:
            context = multiprocessing.get_context("spawn")
            parent, child = context.Pipe()
            process = context.Process(target=_search_worker, args=(child,), daemon=True)
            try:
                process.start()
            except BaseException:
                parent.close()
                raise
            finally:
                child.close()
            self.connection, self.process = parent, process
        connection = self.connection
        assert connection is not None
        try:
            if not self.ready:
                self._receive(connection)
                self.ready = True
            connection.send(
                (expression, flags, key, None if key in self.cached else text, self.max_matches)
            )
            remembered, matches = self._receive(connection)
            if remembered:
                self.cached.add(key)
            return matches
        except (EOFError, BrokenPipeError, OSError) as error:
            raise MxReadyError(
                "SCAN_INTERNAL_ERROR", "规则匹配进程异常退出，请重新扫描。"
            ) from error

    def _receive(self, connection: _MessagePipe) -> Any:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0 or not connection.poll(remaining):
            raise MxReadyError("ANALYSIS_LIMIT_EXCEEDED", "规则评估超过时间预算，请缩小扫描范围。")
        return connection.recv()
