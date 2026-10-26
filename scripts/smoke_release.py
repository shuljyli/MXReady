"""Install and start a release ZIP outside the checkout on the current OS."""

import argparse
import hashlib
import json
import os
import platform as host_platform
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path


def select_archive(dist: Path, platform: str) -> Path:
    archives = list(dist.glob(f"mxready-*-{platform}.zip"))
    if len(archives) != 1:
        raise ValueError(f"Expected one {platform} installer ZIP in {dist}")
    archive = archives[0]
    entries = [line.split() for line in (dist / "SHA256SUMS.txt").read_text().splitlines()]
    expected = [parts[0] for parts in entries if len(parts) == 2 and parts[1] == archive.name]
    if expected != [hashlib.sha256(archive.read_bytes()).hexdigest()]:
        raise ValueError(f"Installer checksum mismatch: {archive.name}")
    return archive


def profile_environment(work: Path, platform: str) -> tuple[dict[str, str], Path]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("PYTHON", "MXREADY_", "PIP_"))
        and k not in {"VIRTUAL_ENV", "XDG_DATA_HOME"}
    }
    home = work / "home"
    home.mkdir(exist_ok=True)
    env.update(
        HOME=str(home),
        USERPROFILE=str(home),
        PIP_CONFIG_FILE=os.devnull,
        PIP_NO_CACHE_DIR="1",
        PIP_DISABLE_PIP_VERSION_CHECK="1",
    )
    if platform == "windows":
        # py -3 otherwise may select a different preinstalled Python on CI runners.
        env["PY_PYTHON3"] = f"{sys.version_info.major}.{sys.version_info.minor}"
        env["LOCALAPPDATA"] = str(home / "AppData" / "Local")
        data = home / "AppData" / "Local" / "MXReady"
    elif platform == "macos":
        data = home / "Library" / "Application Support" / "MXReady"
    else:
        data = home / ".local" / "share" / "mxready"
    return env, data


class Evidence:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.commands: list[dict[str, object]] = []

    def run(
        self,
        name: str,
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        timeout: int,
        expect_failure: bool = False,
    ) -> None:
        record: dict[str, object] = {"name": name, "command": command, "cwd": str(cwd)}
        self.commands.append(record)
        with (self.directory / f"{name}.log").open("w", encoding="utf-8") as log:
            try:
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                record["error"] = str(error)
                raise
        record["returncode"] = result.returncode
        if expect_failure:
            if result.returncode == 0:
                raise AssertionError("Incomplete offline dependencies unexpectedly installed")
        elif result.returncode:
            raise subprocess.CalledProcessError(result.returncode, command)


RESOURCE_SMOKE = """
import io, json, zipfile
from pathlib import Path
from mxready.cli.scan_repository import main
from mxready.config import Settings
from mxready.models import ScanReport
from mxready.resources import verification_schema_bytes
from mxready.scanning.rule_loader import load_rule_catalog
from mxready.verification.bundle import build_verification_bundle
assert len(load_rule_catalog(Settings().rules_dir).rules) == 30
assert json.loads(verification_schema_bytes())['type'] == 'object'
Path('fixture').mkdir()
Path('fixture/setup.py').write_text('from torch.utils.cpp_extension import CUDAExtension')
assert main(['fixture', '--repo-url', 'https://github.com/example/project',
             '--commit', 'a'*40, '--output', 'reports']) in (0, 2)
report = ScanReport.model_validate_json(next(Path('reports').glob('*.json')).read_text())
payload = build_verification_bundle(report)
Path('verification.zip').write_bytes(payload)
with zipfile.ZipFile(io.BytesIO(payload)) as bundle:
    assert 'schemas/verification-result-v1.json' in bundle.namelist()
    bundle.extractall('bundle')
"""


def check_http(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=2) as response:
        assert response.status == 200
        return response.read()


def smoke(archive: Path, wheelhouse: Path | None, evidence: Evidence) -> None:
    platform = {"win32": "windows", "darwin": "macos", "linux": "linux"}[sys.platform]
    with tempfile.TemporaryDirectory(prefix="MXReady 安装 smoke ") as temporary:
        work = Path(temporary)
        env, data = profile_environment(work, platform)
        with zipfile.ZipFile(archive) as package:
            package.extractall(work)
        bundle = work / archive.stem
        if platform == "windows":
            shell = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
            install = [*shell, str(bundle / "install.ps1")]
            start = [*shell, str(bundle / "start.ps1")]
            python = bundle / ".venv" / "Scripts" / "python.exe"
        else:
            install = ["bash", str(bundle / "install.sh")]
            start = ["bash", str(bundle / "start.sh")]
            python = bundle / ".venv" / "bin" / "python"
            env["PYTHON"] = sys.executable
        if wheelhouse:
            install.append("-Offline" if platform == "windows" else "--offline")
            evidence.run(
                "missing-dependencies", install, cwd=work, env=env, timeout=660, expect_failure=True
            )
            # The real installation must start with a fresh virtual environment.
            shutil.rmtree(bundle / ".venv", ignore_errors=True)
            wheels = sorted(wheelhouse.glob("*.whl"))
            if not wheels:
                raise ValueError("Wheelhouse contains no wheels")
            for wheel in wheels:
                if not wheel.name.startswith("mxready-"):
                    shutil.copy2(wheel, bundle / "packages" / wheel.name)
        evidence.run("install", install, cwd=work, env=env, timeout=660)
        runtime = (
            "import platform,sys; print(sys.version); print(platform.platform()); "
            "print(platform.machine()); "
            "assert list(sys.version_info[:2]) == [int(v) for v in sys.argv[1:]]"
        )
        evidence.run(
            "installed-runtime",
            [
                str(python),
                "-I",
                "-c",
                runtime,
                str(sys.version_info.major),
                str(sys.version_info.minor),
            ],
            cwd=work,
            env=env,
            timeout=15,
        )
        evidence.run(
            "resources-scan-bundle",
            [str(python), "-I", "-c", RESOURCE_SMOKE],
            cwd=work,
            env=env,
            timeout=60,
        )
        evidence.run(
            "runner-help",
            [str(python), "-S", "-m", "mxready_runner", "--help"],
            cwd=work / "bundle",
            env=env,
            timeout=15,
        )
        evidence.run(
            "installed-packages",
            [str(python), "-m", "pip", "freeze"],
            cwd=work,
            env=env,
            timeout=30,
        )
        # Seed a completed local report before launching the background worker.
        seed = """
import sys
from pathlib import Path
from mxready.models import ScanReport, ScanStatus
from mxready.persistence.sqlite import SQLiteStore
store = SQLiteStore(Path(sys.argv[1]))
store.initialize()
report = ScanReport.model_validate_json(next(Path('reports').glob('*.json')).read_text())
job = store.create_job(report.repository.url, None)
report = report.model_copy(update={'scan_id': job.id})
store.save_report(report)
store.update_job(job.id, status=ScanStatus.COMPLETED, stage_message='Local smoke complete')
Path('scan-id.txt').write_text(str(job.id))
"""
        evidence.run(
            "seed-report",
            [str(python), "-I", "-c", seed, str(data / "mxready.db")],
            cwd=work,
            env=env,
            timeout=15,
        )
        scan_id = (work / "scan-id.txt").read_text()
        previous_report = None
        for attempt in range(2):
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            command = [*start, "--port", str(port)]
            record: dict[str, object] = {
                "name": f"server-{attempt}",
                "command": command,
                "cwd": str(work),
            }
            evidence.commands.append(record)
            with (evidence.directory / f"server-{attempt}.log").open("w+", encoding="utf-8") as log:
                process = subprocess.Popen(
                    command, cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT
                )
                try:
                    base = f"http://127.0.0.1:{port}"
                    deadline = time.monotonic() + 30
                    while True:
                        try:
                            assert b'"status":"ok"' in check_http(base + "/api/health")
                            break
                        except (OSError, urllib.error.URLError):
                            if process.poll() is not None or time.monotonic() > deadline:
                                raise RuntimeError(
                                    "Server failed; see retained server log"
                                ) from None
                            time.sleep(0.2)
                    html = check_http(base + "/").decode("utf-8")
                    assert '<div id="root">' in html
                    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
                    assert assets
                    for asset in assets:
                        assert check_http(base + asset)
                    try:
                        check_http(base + "/api/unknown")
                    except urllib.error.HTTPError as error:
                        assert error.code == 404
                    else:
                        raise AssertionError("Unknown API route must return 404")
                    job = json.loads(check_http(base + f"/api/scans/{scan_id}"))
                    assert job["status"] == "completed"
                    report = json.loads(check_http(base + f"/api/scans/{scan_id}/report"))
                    assert report["scan_id"] == scan_id
                    if previous_report is not None:
                        assert report == previous_report, "Report changed after restart"
                    previous_report = report
                    (evidence.directory / "report.json").write_text(
                        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    assert (data / "mxready.db").is_file()
                    log.flush()
                    log.seek(0)
                    assert f"http://127.0.0.1:{port}" in log.read()
                finally:
                    if platform == "windows":
                        subprocess.run(
                            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            check=False,
                            timeout=15,
                            capture_output=True,
                        )
                    else:
                        process.terminate()
                    try:
                        record["returncode"] = process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        record["returncode"] = process.wait(timeout=5)
        source = sqlite3.connect(data / "mxready.db")
        destination = sqlite3.connect(evidence.directory / "mxready.db")
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        shutil.copy2(work / "verification.zip", evidence.directory / "verification.zip")
        shutil.copytree(work / "reports", evidence.directory / "local-reports", dirs_exist_ok=True)
        shutil.copy2(
            work / "bundle/schemas/verification-result-v1.json",
            evidence.directory / "verification-result-v1.json",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--wheelhouse", type=Path, help="Use only local dependency wheels")
    parser.add_argument("--evidence-dir", type=Path, help="New directory for logs and result.json")
    parser.add_argument(
        "--candidate-commit", help="Declared source commit; bind to build log separately"
    )
    args = parser.parse_args(argv)
    platform = {"win32": "windows", "darwin": "macos", "linux": "linux"}[sys.platform]
    if args.evidence_dir and args.evidence_dir.exists():
        parser.error("Evidence directory already exists; use a new path to preserve prior runs")
    with tempfile.TemporaryDirectory(prefix="mxready-evidence-") as temporary:
        evidence = Evidence((args.evidence_dir or Path(temporary)).resolve())
        result: dict[str, object] = {
            "schema_version": 1,
            "kind": "release-installation-smoke",
            "started_at": datetime.now(UTC).isoformat(),
            "status": "failed",
            "os": host_platform.platform(),
            "architecture": host_platform.machine(),
            "python": sys.version,
            "candidate_commit": args.candidate_commit,
            "smoke_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "dependency_mode": "offline-pip-no-index" if args.wheelhouse else "online",
            "network_disconnected": False,
            "commands": evidence.commands,
            "not_validated": [
                "other OS/CPU/Python",
                "browser interaction",
                "process crash/leases",
                "historical database upgrade",
                "MetaX hardware",
            ],
        }
        if sys.platform != "win32":
            result["effective_uid"] = os.geteuid()
        try:
            shutil.copy2(Path(__file__), evidence.directory / "smoke_release.py")
            if args.wheelhouse:
                result["dependency_wheels_sha256"] = {
                    wheel.name: hashlib.sha256(wheel.read_bytes()).hexdigest()
                    for wheel in sorted(args.wheelhouse.glob("*.whl"))
                }
            archive = select_archive(args.dist.resolve(), platform)
            result.update(
                archive=archive.name,
                archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            )
            smoke(archive, args.wheelhouse.resolve() if args.wheelhouse else None, evidence)
            result["status"] = "passed"
        except Exception as error:
            result["error"] = f"{type(error).__name__}: {error}"
            raise
        finally:
            result["finished_at"] = datetime.now(UTC).isoformat()
            (evidence.directory / "result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    print(f"{platform} release install, resources, scan, runner help and restart smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
