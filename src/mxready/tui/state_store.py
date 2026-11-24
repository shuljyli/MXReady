"""Independent, bounded TUI catalog. Short per-operation SQLite transactions."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar
from urllib.parse import urlsplit
from uuid import uuid4

from mxready.i18n import DEFAULT_LANGUAGE, normalize_language, tr
from mxready.tui.commands import Command, format_command, parse_command
from mxready.tui.report_catalog import (
    MAX_BATCH_ITEMS,
    BatchRead,
    LoadedReport,
    ReportMetadata,
    metadata,
)

MAX_HISTORY = 200
MAX_PROJECTS = 100
MAX_REPORTS = 2000
MAX_BATCHES = 200
SCHEMA_VERSION = 2
T = TypeVar("T")

_SCHEMA = (
    "CREATE TABLE projects (project_key TEXT PRIMARY KEY, last_access TEXT NOT NULL, "
    "output_dir TEXT, latest_id INTEGER REFERENCES report_entries(id) ON DELETE SET NULL)",
    "CREATE TABLE command_history (id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "project_key TEXT NOT NULL REFERENCES projects ON DELETE CASCADE, command TEXT NOT NULL)",
    "CREATE TABLE report_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "project_key TEXT NOT NULL REFERENCES projects ON DELETE CASCADE, "
    "canonical_path TEXT NOT NULL, "
    "metadata TEXT NOT NULL, last_access TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', "
    "UNIQUE(project_key, canonical_path))",
    "CREATE TABLE report_views (entry_id INTEGER PRIMARY KEY REFERENCES report_entries(id) "
    "ON DELETE CASCADE, scan_id TEXT NOT NULL, digest TEXT NOT NULL, filters TEXT NOT NULL, "
    "page INTEGER NOT NULL)",
    "CREATE TABLE batches (batch_id TEXT PRIMARY KEY, "
    "project_key TEXT NOT NULL REFERENCES projects "
    "ON DELETE CASCADE, output_dir TEXT NOT NULL, finished_at TEXT NOT NULL, return_code INTEGER, "
    "status TEXT NOT NULL, warning TEXT)",
    "CREATE TABLE batch_items (batch_id TEXT NOT NULL REFERENCES batches ON DELETE CASCADE, "
    "ordinal INTEGER NOT NULL, repository TEXT NOT NULL, ref TEXT NOT NULL, status TEXT NOT NULL, "
    "error TEXT NOT NULL, entry_id INTEGER REFERENCES report_entries(id) ON DELETE SET NULL, "
    "PRIMARY KEY(batch_id, ordinal))",
    "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
)


def project_key(path: Path) -> str:
    return os.path.normcase(str(path.expanduser().resolve()))


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


@dataclass(frozen=True)
class RestoredState:
    history: tuple[str, ...]
    output_dir: Path | None
    language: str | None = None
    workspace_mode: str | None = None


@dataclass(frozen=True)
class ReportEntry:
    id: int
    project_key: str
    metadata: ReportMetadata
    last_access: str
    error: str = ""


@dataclass(frozen=True)
class StoredBatchItem:
    ordinal: int
    repository: str
    ref: str
    status: str
    error: str
    entry_id: int | None


@dataclass(frozen=True)
class StoredBatch:
    batch_id: str
    output_dir: Path
    finished_at: str
    return_code: int | None
    status: str
    warning: str | None
    items: tuple[StoredBatchItem, ...]


class StateStore:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.persistent = path is not None
        self.warning: str | None = None
        self.language: str = DEFAULT_LANGUAGE
        self._ready = False
        self._lock = threading.RLock()
        self._uri = f"file:mxready-tui-{uuid4().hex}?mode=memory&cache=shared"
        self._keeper: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self.path) if self.persistent else self._uri, uri=not self.persistent, timeout=1
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _prepare(self) -> None:
        with self._lock:
            if self._ready:
                return
            if self.persistent and self.path is not None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.persistent:
                self._keeper = sqlite3.connect(self._uri, uri=True, check_same_thread=False)
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                if version > SCHEMA_VERSION:
                    raise sqlite3.DatabaseError(
                        tr(
                            self.language,
                            "状态库 schema 比当前实现更新",
                            "State database schema is newer than this implementation",
                        )
                    )
                if version == 0:
                    for statement in _SCHEMA:
                        conn.execute(statement)
                    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
                elif version < SCHEMA_VERSION:
                    # v1 -> v2: add settings without touching existing catalog tables.
                    conn.execute(
                        "CREATE TABLE IF NOT EXISTS settings "
                        "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                    )
                    conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
                conn.commit()
                self._ready = True
            finally:
                conn.close()

    def _run(self, operation: Callable[[sqlite3.Connection], T], *, write: bool = True) -> T:
        # Shared-memory SQLite returns SQLITE_LOCKED without honoring busy_timeout.
        # Serialize this session's short transactions, including startup recovery;
        # separate persistent instances still coordinate through SQLite's timeout.
        with self._lock:
            return self._transaction(operation, write=write)

    def _transaction(self, operation: Callable[[sqlite3.Connection], T], *, write: bool) -> T:
        was_persistent = self.persistent
        try:
            self._prepare()
            conn = self._connect()
            try:
                with conn:
                    conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                    return operation(conn)
            finally:
                conn.close()
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError) as error:
            with self._lock:
                if not was_persistent:
                    raise
                if self.persistent:
                    self.warning = tr(
                        self.language,
                        f"状态库不可用，已降级为本次会话内存模式: {str(error)[:500]}",
                        "State database unavailable; using in-memory state for this session: "
                        f"{str(error)[:500]}",
                    )
                    self.persistent = False
                    self._ready = False
            return self._run(operation, write=write)

    @staticmethod
    def _project(conn: sqlite3.Connection, key: str) -> None:
        conn.execute(
            "INSERT INTO projects(project_key,last_access) VALUES(?,?) "
            "ON CONFLICT(project_key) DO UPDATE SET last_access=excluded.last_access",
            (key, _now()),
        )

    @staticmethod
    def _prune(conn: sqlite3.Connection) -> None:
        for table, key, order, limit in (
            ("projects", "project_key", "last_access DESC, project_key", MAX_PROJECTS),
            ("report_entries", "id", "last_access DESC, id DESC", MAX_REPORTS),
            ("batches", "batch_id", "finished_at DESC, batch_id", MAX_BATCHES),
        ):
            conn.execute(
                f"DELETE FROM {table} WHERE {key} IN (SELECT {key} FROM {table} "
                f"ORDER BY {order} LIMIT -1 OFFSET ?)",
                (limit,),
            )

    def initialize(self, project: Path) -> RestoredState:
        key = project_key(project)

        def operation(conn: sqlite3.Connection) -> RestoredState:
            stored_language: str | None = None
            setting = conn.execute("SELECT value FROM settings WHERE key='language'").fetchone()
            if setting is not None:
                stored_language = normalize_language(setting[0])
                if stored_language is not None:
                    self.language = stored_language
            stored_mode: str | None = None
            mode_setting = conn.execute(
                "SELECT value FROM settings WHERE key='workspace_mode'"
            ).fetchone()
            if mode_setting is not None and mode_setting[0] in {"scan", "code"}:
                stored_mode = mode_setting[0]
            self._project(conn, key)
            self._prune(conn)
            row = conn.execute(
                "SELECT output_dir FROM projects WHERE project_key=?", (key,)
            ).fetchone()
            history = []
            for record in conn.execute(
                "SELECT command FROM command_history WHERE project_key=? ORDER BY id DESC LIMIT ?",
                (key, MAX_HISTORY),
            ).fetchall()[::-1]:
                try:
                    history.append(format_command(Command(**json.loads(record[0]))))
                except (ValueError, TypeError):
                    self.warning = tr(
                        self.language,
                        "部分历史命令无法无损恢复，已跳过。",
                        "Some history commands could not be restored losslessly and were skipped.",
                    )
            return RestoredState(
                tuple(history),
                Path(row[0]) if row[0] else None,
                stored_language,
                stored_mode,
            )

        return self._run(operation)

    def set_workspace_mode(self, mode: str) -> None:
        if mode not in {"scan", "code"}:
            raise ValueError(f"Unsupported workspace mode: {mode}")

        def operation(conn: sqlite3.Connection) -> None:
            conn.execute(
                "INSERT INTO settings(key,value) VALUES('workspace_mode',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (mode,),
            )

        self._run(operation)

    def set_language(self, language: str) -> None:
        normalized = normalize_language(language)
        if normalized is None:
            raise ValueError(f"Unsupported language: {language}")
        self.language = normalized

        def operation(conn: sqlite3.Connection) -> None:
            conn.execute(
                "INSERT INTO settings(key,value) VALUES('language',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (normalized,),
            )

        self._run(operation)

    def set_output(self, project: Path, output: Path) -> None:
        key = project_key(project)

        def operation(conn: sqlite3.Connection) -> None:
            self._project(conn, key)
            conn.execute(
                "UPDATE projects SET output_dir=? WHERE project_key=?",
                (str(output), key),
            )
            self._prune(conn)

        self._run(operation)

    def add_history(self, project: Path, command: Command) -> None:
        # Persist only typed, roundtrippable commands, never output or raw user input.
        try:
            parse_command(format_command(command))
            for value in asdict(command).values():
                if isinstance(value, str) and value.startswith(("https://", "http://")):
                    url = urlsplit(value)
                    if url.username or url.password or url.query or url.fragment:
                        return
        except ValueError:
            return
        payload = json.dumps(asdict(command), ensure_ascii=False, sort_keys=True)
        key = project_key(project)

        def operation(conn: sqlite3.Connection) -> None:
            self._project(conn, key)
            last = conn.execute(
                "SELECT command FROM command_history WHERE project_key=? ORDER BY id DESC LIMIT 1",
                (key,),
            ).fetchone()
            if last is None or last[0] != payload:
                conn.execute(
                    "INSERT INTO command_history(project_key,command) VALUES(?,?)", (key, payload)
                )
            conn.execute(
                "DELETE FROM command_history WHERE project_key=? AND id NOT IN "
                "(SELECT id FROM command_history WHERE project_key=? ORDER BY id DESC LIMIT ?)",
                (key, key, MAX_HISTORY),
            )
            self._prune(conn)

        self._run(operation)

    @staticmethod
    def _entry(row: sqlite3.Row) -> ReportEntry:
        values = json.loads(row["metadata"])
        values["path"] = Path(values["path"])
        return ReportEntry(
            row["id"],
            row["project_key"],
            ReportMetadata(**values),
            row["last_access"],
            row["error"],
        )

    def register(
        self,
        project: Path,
        loaded: LoadedReport,
        *,
        visited: bool = True,
        language: str = DEFAULT_LANGUAGE,
    ) -> ReportEntry:
        key, meta = project_key(project), metadata(loaded, language)
        canonical_path = project_key(meta.path)
        values = asdict(meta) | {"path": str(meta.path)}

        def operation(conn: sqlite3.Connection) -> ReportEntry:
            self._project(conn, key)
            conn.execute(
                "INSERT INTO report_entries(project_key,canonical_path,metadata,last_access) "
                "VALUES(?,?,?,?) ON CONFLICT(project_key,canonical_path) DO UPDATE SET "
                "metadata=excluded.metadata,last_access=excluded.last_access,error=''",
                (key, canonical_path, json.dumps(values, ensure_ascii=False), _now()),
            )
            row = conn.execute(
                "SELECT * FROM report_entries WHERE project_key=? AND canonical_path=?",
                (key, canonical_path),
            ).fetchone()
            entry = self._entry(row)
            conn.execute(
                "DELETE FROM report_views WHERE entry_id=? AND (digest!=? OR scan_id!=?)",
                (entry.id, meta.digest, meta.scan_id),
            )
            if visited:
                conn.execute("UPDATE projects SET latest_id=? WHERE project_key=?", (entry.id, key))
            self._prune(conn)
            return entry

        return self._run(operation)

    def mark_unavailable(self, project: Path, path: Path, error: str) -> None:
        key, canonical_path = project_key(project), project_key(path)

        def operation(conn: sqlite3.Connection) -> None:
            conn.execute(
                "UPDATE report_entries SET error=? WHERE project_key=? AND canonical_path=?",
                (error[:1000], key, canonical_path),
            )

        self._run(operation)

    def entries(
        self, project: Path, *, all_projects: bool = False, query: str = ""
    ) -> tuple[ReportEntry, ...]:
        key = project_key(project)

        def operation(conn: sqlite3.Connection) -> tuple[ReportEntry, ...]:
            rows = conn.execute(
                "SELECT * FROM report_entries "
                + ("" if all_projects else "WHERE project_key=? ")
                + "ORDER BY last_access DESC,id DESC",
                () if all_projects else (key,),
            ).fetchall()
            return tuple(
                self._entry(row) for row in rows if query.casefold() in row["metadata"].casefold()
            )

        return self._run(operation, write=False)

    def latest(self, project: Path) -> ReportEntry | None:
        key = project_key(project)

        def operation(conn: sqlite3.Connection) -> ReportEntry | None:
            row = conn.execute(
                "SELECT r.* FROM projects p JOIN report_entries r ON r.id=p.latest_id "
                "WHERE p.project_key=?",
                (key,),
            ).fetchone()
            return self._entry(row) if row else None

        return self._run(operation, write=False)

    def save_view(
        self, entry_id: int, scan_id: str, digest: str, filters: dict[str, object], page: int
    ) -> None:
        def operation(conn: sqlite3.Connection) -> None:
            if (
                conn.execute("SELECT 1 FROM report_entries WHERE id=?", (entry_id,)).fetchone()
                is None
            ):
                return
            conn.execute(
                "INSERT INTO report_views VALUES(?,?,?,?,?) ON CONFLICT(entry_id) DO UPDATE SET "
                "scan_id=excluded.scan_id,digest=excluded.digest,filters=excluded.filters,page=excluded.page",
                (entry_id, scan_id, digest, json.dumps(filters, ensure_ascii=False), page),
            )

        self._run(operation)

    def view(
        self, entry_id: int, scan_id: str, digest: str
    ) -> tuple[dict[str, object], int] | None:
        def operation(conn: sqlite3.Connection) -> tuple[dict[str, object], int] | None:
            row = conn.execute(
                "SELECT filters,page FROM report_views WHERE entry_id=? AND scan_id=? AND digest=?",
                (entry_id, scan_id, digest),
            ).fetchone()
            return (json.loads(row[0]), row[1]) if row else None

        return self._run(operation, write=False)

    def save_batch(
        self,
        project: Path,
        batch_id: str,
        output: Path,
        return_code: int | None,
        status: str,
        results: BatchRead,
    ) -> None:
        key = project_key(project)

        def operation(conn: sqlite3.Connection) -> None:
            self._project(conn, key)
            conn.execute(
                "INSERT INTO batches VALUES(?,?,?,?,?,?,?) ON CONFLICT(batch_id) DO UPDATE SET "
                "finished_at=excluded.finished_at,return_code=excluded.return_code,status=excluded.status,"
                "warning=excluded.warning",
                (
                    batch_id,
                    key,
                    str(output),
                    _now(),
                    return_code,
                    status,
                    results.warning,
                ),
            )
            for ordinal, item in enumerate(results.items[:MAX_BATCH_ITEMS]):
                entry_id = item.entry_id
                if (
                    entry_id is not None
                    and conn.execute(
                        "SELECT 1 FROM report_entries WHERE id=?", (entry_id,)
                    ).fetchone()
                    is None
                ):
                    entry_id = None
                conn.execute(
                    "INSERT INTO batch_items VALUES(?,?,?,?,?,?,?) "
                    "ON CONFLICT(batch_id,ordinal) DO NOTHING",
                    (
                        batch_id,
                        ordinal,
                        item.repository,
                        item.ref,
                        item.status,
                        item.error,
                        entry_id,
                    ),
                )
            self._prune(conn)

        self._run(operation)

    def batches(self, project: Path, *, all_projects: bool = False) -> tuple[StoredBatch, ...]:
        key = project_key(project)

        def operation(conn: sqlite3.Connection) -> tuple[StoredBatch, ...]:
            rows = conn.execute(
                "SELECT * FROM batches "
                + ("" if all_projects else "WHERE project_key=? ")
                + "ORDER BY finished_at DESC,batch_id",
                () if all_projects else (key,),
            ).fetchall()
            return tuple(
                StoredBatch(
                    row["batch_id"],
                    Path(row["output_dir"]),
                    row["finished_at"],
                    row["return_code"],
                    row["status"],
                    row["warning"],
                    tuple(
                        StoredBatchItem(
                            item["ordinal"],
                            item["repository"],
                            item["ref"],
                            item["status"],
                            item["error"],
                            item["entry_id"],
                        )
                        for item in conn.execute(
                            "SELECT * FROM batch_items WHERE batch_id=? ORDER BY ordinal",
                            (row["batch_id"],),
                        )
                    ),
                )
                for row in rows
            )

        return self._run(operation, write=False)

    def close(self) -> None:
        if self._keeper is not None:
            self._keeper.close()
            self._keeper = None
