import asyncio

import pytest
from textual.geometry import Size
from textual.widgets import Input, OptionList, RichLog

from mxready.tui.app import MXReadyApp, TranscriptLog
from mxready.tui.approval import ApprovalScreen
from mxready.tui.commands import parse_code_command
from mxready.tui.process import ToolResult


async def _after_refresh(app: MXReadyApp) -> None:
    refreshed = asyncio.Event()
    assert app.call_after_refresh(refreshed.set)
    await asyncio.wait_for(refreshed.wait(), timeout=5)


async def _after_resize(app: MXReadyApp, width: int, height: int) -> None:
    # App resize events are debounced: a refresh may finish before screen resize.
    async with asyncio.timeout(5):
        while app.screen.region.size != Size(width, height):
            await _after_refresh(app)
        await _after_refresh(app)


@pytest.mark.parametrize("resize_delay", [0, 0.1])
def test_keyboard_completion_history_and_narrow_layout(tmp_path, monkeypatch, resize_delay):
    async def scenario():
        app = MXReadyApp(project_dir=tmp_path, output_dir=tmp_path / "reports")
        async with app.run_test(size=(110, 36)) as pilot:
            await _after_refresh(app)
            entry = app.query_one("#command", Input)
            workspace = app.screen
            assert app.focused is entry
            await pilot.press("/", "h")
            await _after_refresh(app)
            assert app.query_one("#suggestions", OptionList).display
            await pilot.press("tab")
            await _after_refresh(app)
            assert entry.value == "/help"
            await pilot.press("enter")
            await _after_refresh(app)
            assert "/help" in app.history
            await pilot.press("up")
            await _after_refresh(app)
            assert entry.value == "/help"
            await pilot.press("ctrl+p")
            await _after_refresh(app)
            assert app.screen.__class__.__name__ == "CommandPalette"
            await pilot.press("escape")
            assert app.screen is workspace
            if resize_delay:
                check_resize = app._check_resize
                monkeypatch.setattr(
                    app, "_check_resize", lambda: app.set_timer(resize_delay, check_resize)
                )
            await pilot.resize_terminal(55, 22)
            await _after_resize(app, 55, 22)
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
            await _after_resize(app, 55, 22)
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


def test_queued_resize_after_transcript_removal_does_not_crash(tmp_path):
    async def scenario():
        app = MXReadyApp(project_dir=tmp_path, output_dir=tmp_path / "reports")
        async with app.run_test() as pilot:
            log = app.query_one("#transcript", TranscriptLog)
            await log.remove()
            app.post_message(TranscriptLog.Resized())
            await pilot.pause()

    asyncio.run(scenario())


async def _submit_command(app: MXReadyApp, pilot, value: str) -> None:
    entry = app.query_one("#command", Input)
    entry.focus()
    entry.value = value
    await _after_refresh(app)
    await pilot.press("enter")
    await _after_refresh(app)
    await app.workers.wait_for_complete()


def test_language_command_switches_interface_and_back(tmp_path):
    async def scenario():
        app = MXReadyApp(project_dir=tmp_path, output_dir=tmp_path / "reports")
        async with app.run_test() as pilot:
            await app._state_ready.wait()
            await _after_refresh(app)
            assert app.language == "zh"
            assert "迁移检查" in str(app.query_one("#mode").render())

            await _submit_command(app, pilot, "/lang en")
            assert app.language == "en"
            assert str(app.query_one("#mode").render()) == (
                "Migration check  ·  read-only static analysis"
            )
            assert "project path" in app.query_one("#command", Input).placeholder
            assert str(app.query_one("#projects-heading").render()) == "PROJECT"
            assert all("迁移检查" not in str(item) for item in app._transcript)

            await _submit_command(app, pilot, "/lang")
            assert app.language == "zh"
            assert "迁移检查" in str(app.query_one("#mode").render())

    asyncio.run(scenario())


def test_invalid_language_keeps_current_language_and_explains_support(tmp_path):
    async def scenario():
        app = MXReadyApp(project_dir=tmp_path, output_dir=tmp_path / "reports")
        async with app.run_test() as pilot:
            await app._state_ready.wait()
            await _submit_command(app, pilot, "/lang fr")
            assert app.language == "zh"
            error = str(app._transcript[-1])
            assert "zh" in error and "en" in error

    asyncio.run(scenario())


def test_language_choice_restores_from_state_database(tmp_path):
    state_path = tmp_path / "state.db"
    project = tmp_path / "project"
    project.mkdir()

    async def first():
        app = MXReadyApp(project_dir=project, output_dir=project / "reports", state_path=state_path)
        async with app.run_test() as pilot:
            await app._state_ready.wait()
            await _submit_command(app, pilot, "/lang en")
            assert app.language == "en"

    async def second():
        app = MXReadyApp(project_dir=project, output_dir=project / "reports", state_path=state_path)
        async with app.run_test():
            await app._state_ready.wait()
            await _after_refresh(app)
            assert app.language == "en"
            assert str(app.query_one("#mode").render()) == (
                "Migration check  ·  read-only static analysis"
            )

    asyncio.run(first())
    asyncio.run(second())


def test_code_workspace_switches_help_elevates_and_returns(tmp_path):
    state_path = tmp_path / "state.db"

    async def scenario():
        app = MXReadyApp(
            project_dir=tmp_path,
            output_dir=tmp_path / "reports",
            state_path=state_path,
            agent_dir=tmp_path / "agent",
        )
        async with app.run_test(size=(110, 36)) as pilot:
            await app._state_ready.wait()
            await _after_refresh(app)
            await _submit_command(app, pilot, "/code")
            assert app.workspace_mode == "code"
            assert app.query_one("#sidebar-code").display
            assert not app.query_one("#sidebar-scan").display
            assert "CODE" in str(app.query_one("#mode").render())
            transcript = "".join(str(item) for item in app._transcript)
            assert "/provider add" in transcript

            await _submit_command(app, pilot, "/help")
            transcript = "".join(str(item) for item in app._transcript)
            assert "/elevate" in transcript and "/scan" in transcript

            # Opening a modal from an Enter press would make Pilot.press wait for a
            # screen update that never settles, so start the command directly.
            task = asyncio.create_task(
                app._execute_code_command(parse_code_command("/elevate"))
            )
            await _after_refresh(app)
            assert isinstance(app.screen, ApprovalScreen)
            await pilot.press("y")
            await _after_refresh(app)
            await asyncio.wait_for(task, timeout=5)
            assert app.agent_elevated

            await _submit_command(app, pilot, "/restrict")
            assert not app.agent_elevated

            await _submit_command(app, pilot, "/scan")
            assert app.workspace_mode == "scan"
            assert app.query_one("#sidebar-scan").display
            assert not app.query_one("#sidebar-code").display

    asyncio.run(scenario())

    async def restored():
        app = MXReadyApp(
            project_dir=tmp_path,
            output_dir=tmp_path / "reports",
            state_path=state_path,
            agent_dir=tmp_path / "agent",
        )
        async with app.run_test(size=(110, 36)):
            await app._state_ready.wait()
            await _after_refresh(app)
            assert app.workspace_mode == "scan"

    asyncio.run(restored())


def test_start_flag_opens_code_even_with_stale_state(tmp_path):
    state_path = tmp_path / "state.db"

    async def scenario():
        app = MXReadyApp(
            project_dir=tmp_path,
            output_dir=tmp_path / "reports",
            state_path=state_path,
            agent_dir=tmp_path / "agent",
            workspace_mode="code",
        )
        async with app.run_test(size=(110, 36)):
            await app._state_ready.wait()
            await _after_refresh(app)
            assert app.workspace_mode == "code"
            assert app.query_one("#sidebar-code").display
            assert not app.query_one("#sidebar-scan").display

    asyncio.run(scenario())
