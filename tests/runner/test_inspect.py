from __future__ import annotations

from subprocess import CompletedProcess

from mxready_runner.inspect import DEFAULT_CHECKS, collect_environment


def test_environment_inspection_uses_fixed_commands_in_order(
    recording_runner,
) -> None:
    results = collect_environment(recording_runner)

    assert [call[0] for call in recording_runner.calls] == [
        check.command for check in DEFAULT_CHECKS
    ]
    assert [result.id for result in results] == [
        "uname",
        "python-version",
        "mx-smi-version",
        "mx-smi",
        "pytorch-device",
    ]
    assert all(result.status == "passed" for result in results)
    assert all("secret123" not in result.stdout for result in results)


def test_missing_environment_tools_are_unavailable_without_aborting() -> None:
    def missing_runner(command, *, timeout):
        raise FileNotFoundError(command[0])

    results = collect_environment(missing_runner)

    assert len(results) == len(DEFAULT_CHECKS)
    assert all(result.status == "unavailable" for result in results)


def test_uname_output_does_not_retain_hostname() -> None:
    def uname_runner(command, *, timeout):
        return CompletedProcess(
            command,
            0,
            stdout="Linux private-host 6.8.0 x86_64 GNU/Linux\n",
            stderr="",
        )

    result = collect_environment(uname_runner, [DEFAULT_CHECKS[0]])[0]

    assert "private-host" not in result.stdout
    assert "[HOST]" in result.stdout
