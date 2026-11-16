import asyncio
import threading

from test_tui_app import _after_refresh, _after_resize
from test_tui_report_browser import finding
from textual.widgets import Input, OptionList

from mxready.tui.app import MXReadyApp
from mxready.tui.commands import Command
from mxready.tui.process import ToolResult
from mxready.tui.screens import ComparisonScreen, ReportInformationScreen, ReportPicker


async def submit(app, pilot, command):
    app.query_one("#command", Input).value = command
    await pilot.press("enter")
    await app.workers.wait_for_complete()
    await _after_refresh(app)


def test_quit_command_with_memory_state_closes_cleanly(tmp_path):
    async def scenario():
        app = MXReadyApp(project_dir=tmp_path)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            app.query_one("#command", Input).value = "/quit"
            await pilot.press("enter")
        assert not (tmp_path / "tui").exists()

    asyncio.run(scenario())


def test_restart_is_lazy_restores_output_history_and_content_bound_filters(
    tmp_path, report_factory
):
    path = tmp_path / "report.json"
    report = report_factory(findings=[finding(relative_path=f"{i}.cu") for i in range(12)])
    path.write_text(report.model_dump_json(), encoding="utf-8")
    database = tmp_path / "data" / "tui" / "state.db"

    async def scenario():
        first = MXReadyApp(project_dir=tmp_path, state_path=database)
        async with first.run_test() as pilot:
            await submit(first, pilot, '/report "report.json"')
            await submit(first, pilot, "/findings 2 --query Straße")
            await submit(first, pilot, "/output custom")
            await submit(first, pilot, "/not-a-command secret")
            assert first.finding_page == 2
        second = MXReadyApp(project_dir=tmp_path, state_path=database)
        async with second.run_test() as pilot:
            await second.workers.wait_for_complete()
            assert second.current_report is None and second.last_report is None
            assert second.output_dir == tmp_path / "custom" and not second.output_dir.exists()
            assert not any("secret" in command for command in second.history)
            await submit(second, pilot, "/report")
            assert second.finding_page == 2 and second.filters.text_query == "Straße"
            await submit(second, pilot, "/findings 999 --query absent")
            assert second.finding_page == 2 and second.filters.text_query == "Straße"
            path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
            await submit(second, pilot, "/report report.json")
            assert second.finding_page == 1 and not second.filters.text_query

    asyncio.run(scenario())


def test_report_picker_compare_escape_focus_resize_and_main_state(tmp_path, report_factory):
    before = report_factory(findings=[finding()])
    after = report_factory(findings=[finding(count=3)])
    for name, report in (("before", before), ("after", after)):
        (tmp_path / f"{name}.json").write_text(report.model_dump_json(), encoding="utf-8")

    async def scenario():
        app = MXReadyApp(project_dir=tmp_path)
        async with app.run_test(size=(110, 36)) as pilot:
            await submit(app, pilot, "/report before.json")
            await submit(app, pilot, "/report after.json")
            await submit(app, pilot, "/findings --severity blocker")
            main = app.screen
            await submit(app, pilot, "/reports --query before")
            assert isinstance(app.screen, ReportPicker) and not app.busy
            await pilot.resize_terminal(55, 22)
            await _after_resize(app, 55, 22)
            await pilot.press("i")
            await _after_refresh(app)
            assert isinstance(app.screen, ReportInformationScreen)
            await pilot.press("pagedown", "escape")
            await _after_refresh(app)
            assert isinstance(app.screen, ReportPicker)
            await pilot.press("escape")
            await _after_refresh(app)
            assert app.screen is main and app.focused is app.query_one("#command", Input)
            await submit(app, pilot, "/compare")
            assert isinstance(app.screen, ReportPicker)
            choices = app.screen.query_one("#report-choices", OptionList)
            assert choices.option_count == 1
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            await _after_refresh(app)
            assert isinstance(app.screen, ComparisonScreen)
            await pilot.press("right", "right", "right", "right")
            assert app.screen.group == 4
            await pilot.resize_terminal(55, 22)
            await _after_resize(app, 55, 22)
            assert app.screen.query_one("#difference").region.width <= 55
            await pilot.press("escape")
            await _after_refresh(app)
            assert app.screen is main and app.current_report.scan_id == after.scan_id
            assert app.filters.severity == "blocker" and app.finding_page == 1
            assert app.focused is app.query_one("#command", Input)

    asyncio.run(scenario())


def test_batch_results_require_selection_and_keep_failures(tmp_path, report_factory, monkeypatch):
    report = report_factory(static_status="blocked")
    (tmp_path / "list.txt").write_text("https://github.com/example/project")

    async def batch(arguments, **kwargs):
        from pathlib import Path

        from test_tui_report_catalog import summary

        output = Path(
            next(a.removeprefix("--output=") for a in arguments if a.startswith("--output="))
        )
        (output / "r.json").write_text(report.model_dump_json(), encoding="utf-8")
        summary(
            output,
            [
                [report.repository.url, "main", report.repository.commit, "blocked", "r.md", ""],
                ["example/bad", "", "", "failed", "", "failure"],
            ],
        )
        return ToolResult(1, False)

    monkeypatch.setattr("mxready.tui.app.run_tool", batch)

    async def scenario():
        app = MXReadyApp(project_dir=tmp_path)
        async with app.run_test() as pilot:
            await submit(app, pilot, "/batch list.txt")
            assert isinstance(app.screen, ReportPicker) and app.current_report is None
            assert app.screen.query_one("#report-choices", OptionList).option_count == 2
            batches = app.store.batches(tmp_path)
            assert batches[0].status == "failed"
            assert batches[0].items[0].status == "blocked"
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            assert app.current_report.scan_id == report.scan_id

    asyncio.run(scenario())


def test_late_reads_and_filter_results_cannot_replace_current_view(
    tmp_path, report_factory, monkeypatch
):
    from mxready.tui import app as module

    report = report_factory(findings=[finding()])
    path = tmp_path / "r.json"
    path.write_text(report.model_dump_json(), encoding="utf-8")
    started, release = threading.Event(), threading.Event()
    original = module.browse

    def blocked(*args, **kwargs):
        started.set()
        assert release.wait(5)
        return original(*args, **kwargs)

    async def scenario():
        app = MXReadyApp(project_dir=tmp_path)
        async with app.run_test() as pilot:
            await app._open_report(path)
            monkeypatch.setattr(module, "browse", blocked)
            worker = app.run_worker(app._apply_filters(Command("findings", query="absent")))
            assert await asyncio.to_thread(started.wait, 2)
            app.query_one("#command", Input).value = "responsive"
            await pilot.press("ctrl+c")
            assert app.query_one("#command", Input).value == ""
            release.set()
            await worker.wait()
            assert app.filters.text_query == "" and app.current_report.scan_id == report.scan_id
            started.clear()
            release.clear()
            worker = app.run_worker(app._open_report(path))
            assert await asyncio.to_thread(started.wait, 2)
            app.view_generation += 1
            old = app.current_report
            release.set()
            await worker.wait()
            assert app.current_report is old

    asyncio.run(scenario())
