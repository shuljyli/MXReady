import pytest

from mxready.tui.commands import make_scan_job, parse_command, read_report, safe_text


def test_scan_parser_preserves_spaces_backslashes_and_shell_characters():
    command = parse_command('/scan "C:\\source code\\ext;$(echo test)" --commit ' + "a" * 40)
    assert command.target == "C:\\source code\\ext;$(echo test)"
    assert command.commit == "a" * 40


@pytest.mark.parametrize(
    "value", ["/unknown", "/scan --shell", '/scan "unfinished', "/public", "/help\n/quit"]
)
def test_invalid_commands_have_actionable_errors(value):
    with pytest.raises(ValueError):
        parse_command(value)


def test_bare_url_and_directory_use_scan_shortcuts():
    assert parse_command("https://github.com/example/project").name == "public"
    assert parse_command(".").name == "scan"


def test_jobs_reserve_distinct_directories_and_pass_argument_arrays(tmp_path):
    source = tmp_path / "source with spaces"
    source.mkdir()
    command = parse_command(f'/scan "{source}" --repo-url https://github.com/example/project')
    first = make_scan_job(command, project_dir=tmp_path, output_dir=tmp_path / "reports")
    second = make_scan_job(command, project_dir=tmp_path, output_dir=tmp_path / "reports")
    assert first.output_dir != second.output_dir
    assert first.output_dir.is_dir() and second.output_dir.is_dir()
    assert first.arguments[-2:] == ("--", str(source))
    assert "mxready.cli.scan_repository" in first.arguments
    assert "--repo-url=https://github.com/example/project" in first.arguments


def test_public_url_validation_happens_before_creating_output(tmp_path):
    with pytest.raises(ValueError):
        make_scan_job(
            parse_command("/public https://internal.example/project"),
            project_dir=tmp_path,
            output_dir=tmp_path / "reports",
        )
    assert not (tmp_path / "reports").exists()


def test_report_reader_accepts_legacy_bom_json(tmp_path, report_factory):
    report = report_factory()
    path = tmp_path / "report.json"
    path.write_text(report.model_dump_json(exclude={"coverage"}), encoding="utf-8-sig")
    assert read_report(path).scan_id == report.scan_id


def test_report_reader_rejects_oversized_file(tmp_path):
    path = tmp_path / "large.json"
    path.write_bytes(b" " * (20 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="20 MiB"):
        read_report(path)


def test_terminal_controls_are_escaped_without_interpreting_rich_markup():
    value = safe_text("[bold]source\x1b[2J\x1b]52;c;secret\x07\u202e")
    assert "\x1b" not in value and "\x07" not in value and "\u202e" not in value
    assert "[bold]source" in value


@pytest.mark.parametrize(
    ("value", "module"),
    [
        ("/public https://github.com/example/project --ref release", "generate_public_report"),
        ('/batch "repo list.txt"', "scan_batch"),
    ],
)
def test_public_and_batch_jobs_delegate_to_existing_commands(tmp_path, value, module):
    (tmp_path / "repo list.txt").write_text("https://github.com/example/project\n")
    job = make_scan_job(parse_command(value), project_dir=tmp_path, output_dir=tmp_path / "reports")
    assert f"mxready.cli.{module}" in job.arguments
    assert job.arguments[-2] == "--"
    if module == "generate_public_report":
        assert "--ref=release" in job.arguments
    else:
        assert job.arguments[-1] == str(tmp_path / "repo list.txt")
