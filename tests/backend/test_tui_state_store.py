import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from mxready.tui.commands import Command, format_command, parse_command
from mxready.tui.report_catalog import load_report
from mxready.tui.state_store import StateStore


def test_restart_upsert_output_and_digest_bound_views(tmp_path, report_factory):
    db = tmp_path / "state.db"
    path = tmp_path / "r.json"
    report = report_factory()
    path.write_text(report.model_dump_json(), encoding="utf-8")
    store = StateStore(db)
    store.initialize(tmp_path)
    loaded = load_report(path)
    entry = store.register(tmp_path, loaded)
    assert store.register(tmp_path, loaded).id == entry.id
    store.save_view(entry.id, str(report.scan_id), loaded.digest, {"text_query": "warp"}, 4)
    store.set_output(tmp_path, tmp_path / "custom")
    store.add_history(tmp_path, parse_command('/report "r.json"'))
    reopened = StateStore(db)
    restored = reopened.initialize(tmp_path)
    assert restored.output_dir == tmp_path / "custom"
    assert restored.history == ('/report "r.json"',)
    assert reopened.latest(tmp_path).id == entry.id
    assert reopened.view(entry.id, str(report.scan_id), loaded.digest)[1] == 4
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    updated = reopened.register(tmp_path, load_report(path))
    assert updated.id == entry.id
    assert reopened.view(entry.id, str(report.scan_id), load_report(path).digest) is None


def test_multiple_instances_short_transactions_and_history_privacy(tmp_path):
    db = tmp_path / "state.db"
    first, second = StateStore(db), StateStore(db)
    first.initialize(tmp_path)
    second.initialize(tmp_path)

    def add(i):
        (first if i % 2 else second).add_history(tmp_path, Command("report", f"{i}.json"))

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(add, range(30)))
    assert len(first.initialize(tmp_path).history) == 30
    first.add_history(tmp_path, Command("public", "https://user:secret@github.com/a/b?q=token#x"))
    assert len(first.initialize(tmp_path).history) == 30
    assert b"secret" not in db.read_bytes()


def test_future_corrupt_disabled_and_locked_state_degrade_without_overwrite(tmp_path):
    db = tmp_path / "state.db"
    with sqlite3.connect(db) as conn:
        conn.execute("PRAGMA user_version=999")
    original = db.read_bytes()
    store = StateStore(db)
    store.initialize(tmp_path)
    assert store.warning and not store.persistent
    assert db.read_bytes() == original
    disabled = StateStore(None)
    assert not disabled.initialize(tmp_path).history
    assert not disabled.persistent
    db.write_bytes(b"corrupt")
    corrupt = StateStore(db)
    corrupt.initialize(tmp_path)
    assert corrupt.warning and db.read_bytes() == b"corrupt"


def test_formatter_roundtrips_quotes_backslashes_unicode_and_empty_values():
    for value in ["C:\\a b\\尾部\\", "a\"b'c", "", "--leading", "组合e\u0301中文"]:
        command = Command("findings", query=value)
        assert parse_command(format_command(command)) == command


def test_locks_readonly_and_invalid_metadata_degrade_in_memory(
    tmp_path, monkeypatch, report_factory
):
    from mxready.tui import state_store as module

    db = tmp_path / "state.db"
    StateStore(db).initialize(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("BEGIN EXCLUSIVE")
        locked = StateStore(db)
        locked.initialize(tmp_path)
        assert not locked.persistent and "locked" in locked.warning
        locked.close()
    connect = module.sqlite3.connect

    def readonly(database, **kwargs):
        if str(database) == str(db):
            return connect(db.as_uri() + "?mode=ro", uri=True, timeout=1)
        return connect(database, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(module.sqlite3, "connect", readonly)
        store = StateStore(db)
        store.initialize(tmp_path)
        assert not store.persistent and "readonly" in store.warning
        store.close()
    path = tmp_path / "r.json"
    path.write_text(report_factory().model_dump_json(), encoding="utf-8")
    store = StateStore(db)
    store.register(tmp_path, load_report(path))
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE report_entries SET metadata='not-json'")
    assert not store.entries(tmp_path) and not store.persistent
    store.close()


def test_retention_never_deletes_reports_or_changes_success_status(
    tmp_path, monkeypatch, report_factory
):
    from mxready.tui import state_store as module
    from mxready.tui.report_catalog import BatchItem, BatchRead

    for constant in ("MAX_PROJECTS", "MAX_REPORTS", "MAX_BATCHES", "MAX_HISTORY"):
        monkeypatch.setattr(module, constant, 2)
    store = StateStore(tmp_path / "state.db")
    paths = []
    for i in range(4):
        path = tmp_path / f"{i}.json"
        paths.append(path)
        path.write_text(report_factory().model_dump_json(), encoding="utf-8")
        entry = store.register(tmp_path, load_report(path))
        store.add_history(tmp_path, Command("report", str(path)))
        store.save_batch(
            tmp_path,
            str(i),
            tmp_path,
            0,
            "completed",
            BatchRead((BatchItem("repo", "main", "passed", entry_id=entry.id),), None),
        )
    assert len(store.entries(tmp_path)) == 2 and len(store.batches(tmp_path)) == 2
    assert len(store.initialize(tmp_path).history) == 2
    for i in range(4, 6):
        path = tmp_path / f"{i}.json"
        path.write_text(report_factory().model_dump_json(), encoding="utf-8")
        store.register(tmp_path, load_report(path))
    assert all(batch.items[0].entry_id is None for batch in store.batches(tmp_path))
    assert all(batch.items[0].status == "passed" for batch in store.batches(tmp_path))
    assert all(path.exists() for path in paths)
    for i in range(3):
        project = tmp_path / str(i)
        project.mkdir()
        store.initialize(project)
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("SELECT count(*) FROM projects").fetchone()[0] == 2


def test_state_migration_is_transactional_and_unknown_history_is_skipped(tmp_path):
    db = tmp_path / "state.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE projects (wrong TEXT)")
    store = StateStore(db)
    store.initialize(tmp_path)
    assert not store.persistent
    with sqlite3.connect(db) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
        assert (
            conn.execute("SELECT name FROM sqlite_master WHERE name='command_history'").fetchone()
            is None
        )
    store.close()


@pytest.mark.parametrize(
    "target",
    [
        "https://github.com/a/b?q=x",
        "https://github.com/a/b#x",
        "https://name:secret@github.com/a/b",
    ],
)
def test_sensitive_url_commands_are_never_persisted(tmp_path, target):
    store = StateStore(tmp_path / "state.db")
    store.add_history(tmp_path, Command("public", target))
    assert not store.initialize(tmp_path).history
