import json
import zipfile
from pathlib import Path

from scripts.build_verification_bundle import build_bundle_from_report, main


def test_build_bundle_from_report_writes_commit_pinned_safe_manifest(
    tmp_path: Path,
    report_factory,
) -> None:
    report = report_factory()
    report_path = tmp_path / "report.json"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    output_path = tmp_path / "nested" / "verification.zip"

    build_bundle_from_report(report_path, output_path)

    with zipfile.ZipFile(output_path) as archive:
        manifest = json.loads(archive.read("mxready.yml"))
        assert manifest["scan_id"] == str(report.scan_id)
        assert manifest["repository_commit"] == report.repository.commit
        assert manifest["project_commands"] == []
        assert "mxready_runner/cli.py" in archive.namelist()
        assert "schemas/verification-result-v1.json" in archive.namelist()


def test_build_bundle_cli_reports_invalid_input_without_traceback(
    tmp_path: Path,
    capsys,
) -> None:
    report_path = tmp_path / "invalid.json"
    report_path.write_text("not-json", encoding="utf-8")

    exit_code = main(
        [
            str(report_path),
            "--output",
            str(tmp_path / "verification.zip"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "MXReady bundle error:" in captured.err
    assert "Traceback" not in captured.err
