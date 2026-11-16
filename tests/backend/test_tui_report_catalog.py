import csv

import pytest

from mxready.tui.report_catalog import read_batch


def summary(path, rows):
    with (path / "batch-summary.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["repository", "ref", "commit", "status", "report", "error"])
        writer.writerows(rows)


def test_batch_mixed_results_are_separate_from_process_status(tmp_path, report_factory):
    report = report_factory(static_status="blocked")
    (tmp_path / "r.json").write_text(report.model_dump_json(), encoding="utf-8")
    summary(
        tmp_path,
        [
            [report.repository.url, "main", report.repository.commit, "blocked", "r.md", ""],
            ["example/bad", "", "", "failed", "", "bad\x1b[2J"],
        ],
    )
    batch = read_batch(tmp_path)
    assert batch.warning is None and len(batch.items) == 2
    assert batch.items[0].loaded.static_status == "blocked"
    assert batch.items[1].status == "failed" and "\x1b" not in batch.items[1].error


@pytest.mark.parametrize("path", ["../r.md", "/r.md", "C:r.md", "sub/r.md", "sub\\r.md"])
def test_batch_paths_cannot_leave_new_output_directory(tmp_path, report_factory, path):
    report = report_factory()
    summary(tmp_path, [[report.repository.url, "", report.repository.commit, "passed", path, ""]])
    item = read_batch(tmp_path).items[0]
    assert item.loaded is None and item.error


def test_missing_summary_and_metadata_mismatch_are_explicit(tmp_path, report_factory):
    report = report_factory()
    (tmp_path / "r.json").write_text(report.model_dump_json(), encoding="utf-8")
    assert read_batch(tmp_path).warning
    summary(tmp_path, [[report.repository.url, "", "b" * 40, "passed", "r.md", ""]])
    result = read_batch(tmp_path)
    assert result.items[0].loaded is None and "不一致" in result.items[0].error


def test_symlink_escape_is_rejected_even_when_json_is_valid(tmp_path, report_factory):
    outside = tmp_path / "outside.json"
    outside.write_text(report_factory().model_dump_json(), encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    try:
        (output / "r.json").symlink_to(outside)
    except OSError:
        pytest.skip("Creating symlinks requires Windows developer mode or elevated rights")
    summary(output, [["https://github.com/example/project", "", "a" * 40, "passed", "r.md", ""]])
    assert read_batch(output).items[0].loaded is None


def test_csv_bounds_truncation_and_between_file_cancellation(tmp_path, report_factory, monkeypatch):
    from mxready.tui import report_catalog as module

    monkeypatch.setattr(module, "MAX_CSV_BYTES", 100)
    (tmp_path / "batch-summary.csv").write_bytes(b"x" * 101)
    assert "2 MiB" in read_batch(tmp_path).warning
    monkeypatch.setattr(module, "MAX_BATCH_ITEMS", 1)
    for i in range(2):
        (tmp_path / f"{i}.json").write_text(report_factory().model_dump_json(), encoding="utf-8")
    assert len(read_batch(tmp_path).items) == 1
    assert not read_batch(tmp_path, cancelled=lambda: True).items
