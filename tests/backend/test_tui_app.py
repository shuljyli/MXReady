import asyncio

from textual.widgets import Input, OptionList, RichLog

from mxready.tui.app import MXReadyApp
from mxready.tui.process import ToolResult


def test_keyboard_completion_history_and_narrow_layout(tmp_path):
    async def scenario():
        app = MXReadyApp(project_dir=tmp_path, output_dir=tmp_path / "reports")
        async with app.run_test(size=(110, 36)) as pilot:
            entry = app.query_one("#command", Input)
            assert app.focused is entry
            await pilot.press("/", "h")
            assert app.query_one("#suggestions", OptionList).display
            await pilot.press("tab")
            assert entry.value == "/help"
            await pilot.press("enter")
            await pilot.pause()
            assert "/help" in app.history
            await pilot.press("up")
            assert entry.value == "/help"
            await pilot.press("ctrl+p")
            assert app.screen.__class__.__name__ == "CommandPalette"
            await pilot.press("escape")
            await pilot.resize_terminal(55, 22)
            assert not app.query_one("#sidebar").display
            assert entry.region.width <= 55
            await pilot.press("ctrl+q")

    asyncio.run(scenario())


def test_local_scan_runs_in_background_and_preserves_artifacts(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    marker = tmp_path / "executed"
    (source / "setup.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
        "from torch.utils.cpp_extension import CUDAExtension\n",
        encoding="utf-8",
    )

    async def scenario():
        app = MXReadyApp(project_dir=tmp_path, output_dir=tmp_path / "reports")
        async with app.run_test(size=(100, 30)) as pilot:
            for _ in range(2):
                entry = app.query_one("#command", Input)
                entry.value = (
                    "/scan source --repo-url https://github.com/example/project --commit "
                    + "a" * 40
                )
                await pilot.press("enter")
                await app.workers.wait_for_complete()
                assert not app.busy
                assert app.last_report is not None
            assert len(list((tmp_path / "reports").glob("scan-*/*.json"))) == 2
            assert not marker.exists()
            entry.value = "/report"
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            assert app.current_report is not None
            await pilot.press("ctrl+q")

    asyncio.run(scenario())


def test_task_cancellation_and_duplicate_submission(tmp_path, monkeypatch):
    calls = []

    async def blocked(arguments, *, cwd, cancel, on_output):
        calls.append(arguments)
        await cancel.wait()
        return ToolResult(return_code=-1, cancelled=True)

    monkeypatch.setattr("mxready.tui.app.run_tool", blocked)

    async def scenario():
        app = MXReadyApp(project_dir=tmp_path, output_dir=tmp_path / "reports")
        async with app.run_test() as pilot:
            entry = app.query_one("#command", Input)
            entry.value = "/scan ."
            await pilot.press("enter")
            await pilot.pause()
            assert app.busy
            entry.value = "/scan ."
            await pilot.press("enter")
            assert len(calls) == 1
            await pilot.press("ctrl+c")
            await app.workers.wait_for_complete()
            assert not app.busy and app.last_report is None
            await pilot.press("ctrl+q")

    asyncio.run(scenario())


def test_quit_cleans_up_a_running_task(tmp_path, monkeypatch):
    stopped = []

    async def blocked(arguments, *, cwd, cancel, on_output):
        await cancel.wait()
        stopped.append(True)
        return ToolResult(return_code=-1, cancelled=True)

    monkeypatch.setattr("mxready.tui.app.run_tool", blocked)

    async def scenario():
        app = MXReadyApp(project_dir=tmp_path, output_dir=tmp_path / "reports")
        async with app.run_test() as pilot:
            app.query_one("#command", Input).value = "/scan ."
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("ctrl+q")
        assert stopped == [True]

    asyncio.run(scenario())


def test_existing_output_reflows_after_terminal_resize(tmp_path):
    async def scenario():
        app = MXReadyApp(project_dir=tmp_path, output_dir=tmp_path / "reports")
        async with app.run_test(size=(120, 40)) as pilot:
            app._write("source 中文内容 " * 40)
            await pilot.pause()
            await pilot.resize_terminal(55, 22)
            await pilot.pause()
            log = app.query_one("#transcript", RichLog)
            assert log.virtual_size.width <= log.scrollable_content_region.width

    asyncio.run(scenario())


def test_report_snapshot_and_bundle_workflow(tmp_path, report_factory):
    import zipfile

    report = report_factory(verification_status="verified")
    path = tmp_path / "legacy report.json"
    payload = report.model_dump_json(exclude={"coverage"})
    path.write_text(payload, encoding="utf-8-sig")

    async def scenario():
        app = MXReadyApp(project_dir=tmp_path, output_dir=tmp_path / "reports")
        async with app.run_test() as pilot:
            entry = app.query_one("#command", Input)
            entry.value = '/report "legacy report.json"'
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            assert app.current_report.scan_id == report.scan_id
            assert any("导出时快照" in str(item) for item in app._transcript)
            entry.value = "/bundle"
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            bundles = list((tmp_path / "reports").glob("bundle-*/verification.zip"))
            assert len(bundles) == 1
            with zipfile.ZipFile(bundles[0]) as bundle:
                assert "mxready.yml" in bundle.namelist()
            assert path.read_text(encoding="utf-8-sig") == payload

    asyncio.run(scenario())
