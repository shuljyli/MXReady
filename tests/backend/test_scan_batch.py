from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from mxready.cli.scan_batch import (
    BatchEntry,
    format_progress_line,
    load_batch_entries,
    main,
    render_batch_csv,
    render_batch_markdown,
    scan_batch,
)
from mxready.errors import MxReadyError
from mxready.models import (
    Finding,
    RepositorySnapshot,
    ScanReport,
    ScanSummary,
    Severity,
    SourceReference,
    StaticStatus,
    VerificationStatus,
)


def _stub_report(
    repository_name: str = "project",
    commit: str = "a" * 40,
    static_status: StaticStatus = StaticStatus.PASSED,
    rule_ids: list[tuple[str, Severity]] | None = None,
) -> ScanReport:
    findings = [
        Finding(
            rule_id=rule_id,
            rule_version=1,
            severity=severity,
            category="test",
            title=f"规则 {rule_id}",
            relative_path="setup.py",
            line_start=1,
            line_end=1,
            evidence="evidence",
            message="message",
            recommendation="recommendation",
            references=[SourceReference(title="doc", url="https://example.com/doc")],
        )
        for rule_id, severity in (rule_ids or [])
    ]
    blockers = sum(1 for _, severity in (rule_ids or []) if severity is Severity.BLOCKER)
    warnings = sum(1 for _, severity in (rule_ids or []) if severity is Severity.WARNING)
    infos = sum(1 for _, severity in (rule_ids or []) if severity is Severity.INFO)
    return ScanReport(
        scan_id=uuid4(),
        repository=RepositorySnapshot(
            provider="github",
            owner="example",
            name=repository_name,
            url=f"https://github.com/example/{repository_name}",
            commit=commit,
        ),
        tool_version="0.1.0",
        ruleset_version="1",
        ruleset_digest="sha256:" + "0" * 64,
        scanned_at=datetime(2026, 7, 29, tzinfo=UTC),
        summary=ScanSummary(
            total_count=len(findings),
            blocker_count=blockers,
            warning_count=warnings,
            info_count=infos,
        ),
        findings=findings,
        migration_checklist=[],
        analysis_warnings=[],
        static_status=static_status,
        verification_status=VerificationStatus.NOT_RUN,
    )


def _fake_scan_one(
    reports_by_name: dict[str, ScanReport],
    failures: set[str] | None = None,
):
    failures = failures or set()

    def scan_one(
        repository_url: str,
        *,
        label: str,
        output_dir: Path,
        work_dir: Path,
        requested_ref: str | None,
    ):
        name = repository_url.rsplit("/", 1)[-1]
        if name in failures:
            raise MxReadyError(
                "REPOSITORY_NOT_FOUND", "未找到仓库或指定分支、标签、提交，请检查输入。"
            )
        return reports_by_name.get(name) or _stub_report(repository_name=name)

    return scan_one


def test_load_batch_entries_parses_files_with_refs_and_comments(tmp_path: Path) -> None:
    listing = tmp_path / "repos.txt"
    listing.write_text(
        "\n".join(
            [
                "# 优先迁移的核心仓库",
                "https://github.com/example/alpha main",
                "",
                "https://github.com/example/beta"
                "  1c325b202ae5e11de3cefb9a65be28f47949edd4  # 固定提交",
                "https://github.com/example/alpha main",
                "https://gitee.com/example/gamma",
            ]
        ),
        encoding="utf-8",
    )

    entries = load_batch_entries(str(listing))

    assert [(entry.repository_url, entry.requested_ref) for entry in entries] == [
        ("https://github.com/example/alpha", "main"),
        ("https://github.com/example/beta", "1c325b202ae5e11de3cefb9a65be28f47949edd4"),
        ("https://gitee.com/example/gamma", None),
    ]


def test_load_batch_entries_accepts_a_single_url() -> None:
    entries = load_batch_entries("https://github.com/example/alpha")

    assert len(entries) == 1
    assert entries[0].requested_ref is None


def test_load_batch_entries_rejects_bad_lines(tmp_path: Path) -> None:
    listing = tmp_path / "repos.txt"
    listing.write_text("https://ftp.example.com/repo\n", encoding="utf-8")

    with pytest.raises(ValueError) as error:
        load_batch_entries(str(listing))
    assert "第 1 行" in str(error.value)

    with pytest.raises(ValueError):
        load_batch_entries(str(tmp_path / "missing.txt"))


def test_scan_batch_collects_reports_and_failures(tmp_path: Path) -> None:
    blocked = _stub_report(
        repository_name="blocked-repo",
        static_status=StaticStatus.BLOCKED,
        rule_ids=[
            ("MXR-TOOLCHAIN-001", Severity.BLOCKER),
            ("MXR-PATH-001", Severity.WARNING),
            ("MXR-DEPENDENCY-001", Severity.WARNING),
            ("MXR-TOOL-001", Severity.WARNING),
        ],
    )
    entries = [
        BatchEntry("https://github.com/example/clean-repo", None, 1),
        BatchEntry("https://github.com/example/blocked-repo", "main", 2),
        BatchEntry("https://github.com/example/missing-repo", None, 3),
    ]
    scan_one = _fake_scan_one({"blocked-repo": blocked}, failures={"missing-repo"})
    seen: list[str] = []

    outcomes = scan_batch(
        entries,
        output_dir=tmp_path / "out",
        work_dir=tmp_path / "work",
        scan_one=scan_one,
        progress=lambda outcome: seen.append(outcome.display),
    )

    assert [outcome.report is not None for outcome in outcomes] == [True, True, False]
    assert outcomes[0].label == "example-clean-repo-aaaaaaaaaaaa"
    assert outcomes[2].error is not None and "REPOSITORY_NOT_FOUND" in outcomes[2].error
    assert seen == ["example/clean-repo", "example/blocked-repo", "example/missing-repo"]


def test_batch_csv_and_markdown_summarize_status_and_top_rules(tmp_path: Path) -> None:
    blocked = _stub_report(
        repository_name="blocked-repo",
        static_status=StaticStatus.BLOCKED,
        rule_ids=[
            ("MXR-TOOLCHAIN-001", Severity.BLOCKER),
            ("MXR-PATH-001", Severity.WARNING),
        ],
    )
    entries = [
        BatchEntry("https://github.com/example/clean-repo", None, 1),
        BatchEntry("https://github.com/example/blocked-repo", "main", 2),
        BatchEntry("https://github.com/example/missing-repo", None, 3),
    ]
    outcomes = scan_batch(
        entries,
        output_dir=tmp_path,
        work_dir=tmp_path,
        scan_one=_fake_scan_one({"blocked-repo": blocked}, failures={"missing-repo"}),
    )

    rows = list(csv.DictReader(io.StringIO(render_batch_csv(outcomes))))
    assert rows[0]["status"] == "passed" and rows[0]["total"] == "0"
    assert rows[1]["status"] == "blocked" and rows[1]["top_rules"].startswith("MXR-TOOLCHAIN-001; ")
    assert rows[2]["status"] == "failed" and "REPOSITORY_NOT_FOUND" in rows[2]["error"]

    markdown = render_batch_markdown(
        outcomes,
        ruleset_version="1",
        ruleset_digest="sha256:" + "0" * 64,
    )
    assert "# MXReady 批量迁移体检汇总" in markdown
    assert "成功 2 · 失败 1 · 其中阻塞 1" in markdown
    assert "[example/blocked-repo](https://github.com/example/blocked-repo)" in markdown
    assert "失败（REPOSITORY_NOT_FOUND" in markdown


def test_progress_line_is_compact_and_gbk_encodable(tmp_path: Path) -> None:
    report = _stub_report(repository_name="alpha", static_status=StaticStatus.WARNINGS)
    outcome = next(
        iter(
            scan_batch(
                [BatchEntry("https://github.com/example/alpha", None, 1)],
                output_dir=tmp_path,
                work_dir=tmp_path,
                scan_one=_fake_scan_one({"alpha": report}),
            )
        )
    )

    line = format_progress_line(1, 1, outcome)

    assert line.startswith("[1/1] example/alpha → warnings")
    line.encode("gbk")


def test_cli_exit_codes_and_summary_files(tmp_path: Path, monkeypatch, capsys) -> None:
    blocked = _stub_report(
        repository_name="blocked-repo",
        static_status=StaticStatus.BLOCKED,
        rule_ids=[("MXR-TOOLCHAIN-001", Severity.BLOCKER)],
    )
    listing = tmp_path / "repos.txt"
    listing.write_text(
        "https://github.com/example/clean-repo\nhttps://github.com/example/blocked-repo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "mxready.cli.scan_batch.generate_public_report",
        _fake_scan_one({"blocked-repo": blocked}),
    )

    exit_code = main(
        [str(listing), "--output", str(tmp_path / "out"), "--work-dir", str(tmp_path / "work")]
    )

    assert exit_code == 2
    stdout = capsys.readouterr().out
    assert "汇总: 成功 2 · 失败 0（其中阻塞 1）" in stdout
    assert (tmp_path / "out" / "batch-summary.csv").is_file()
    assert (tmp_path / "out" / "batch-summary.md").is_file()


def test_cli_reports_empty_or_invalid_sources_without_traceback(tmp_path: Path, capsys) -> None:
    empty = tmp_path / "empty.txt"
    empty.write_text("# 只有注释\n", encoding="utf-8")

    assert main([str(empty)]) == 1
    assert main([str(tmp_path / "missing.txt")]) == 1

    captured = capsys.readouterr()
    assert "MXReady batch error" in captured.err
    assert "Traceback" not in captured.err
