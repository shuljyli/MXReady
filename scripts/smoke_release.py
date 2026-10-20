"""Install and start a release ZIP outside the checkout on the current OS."""

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

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
with zipfile.ZipFile(io.BytesIO(build_verification_bundle(report))) as bundle:
    assert 'schemas/verification-result-v1.json' in bundle.namelist()
    bundle.extractall('bundle')
"""


def check_http(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=2) as response:
        assert response.status == 200
        return response.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument(
        "--wheelhouse", type=Path, help="Use offline dependency wheels from this directory"
    )
    args = parser.parse_args(argv)
    platform = {"win32": "windows", "darwin": "macos", "linux": "linux"}[sys.platform]
    archives = list(args.dist.glob(f"mxready-*-{platform}.zip"))
    if len(archives) != 1:
        parser.error(f"Expected one {platform} installer ZIP in {args.dist}")
    env = {
        k: v for k, v in os.environ.items() if k != "PYTHONPATH" and not k.startswith("MXREADY_")
    }
    # Include non-ASCII characters and spaces to cover installation path quoting.
    with tempfile.TemporaryDirectory(prefix="MXReady 安装 smoke ") as temporary:
        work = Path(temporary)
        with zipfile.ZipFile(archives[0]) as archive:
            archive.extractall(work)
        bundle = work / archives[0].stem
        if args.wheelhouse:
            for wheel in args.wheelhouse.glob("*.whl"):
                if not wheel.name.startswith("mxready-"):
                    shutil.copy2(wheel, bundle / "packages" / wheel.name)
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
        if args.wheelhouse:
            install.append("-Offline" if platform == "windows" else "--offline")
        subprocess.run(install, cwd=work, env=env, check=True, timeout=660)
        subprocess.run(
            [str(python), "-I", "-c", RESOURCE_SMOKE], cwd=work, env=env, check=True, timeout=60
        )
        subprocess.run(
            [str(python), "-S", "-m", "mxready_runner", "--help"],
            cwd=work / "bundle",
            env=env,
            check=True,
            timeout=15,
        )
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        env["MXREADY_DATA_DIR"] = str(work / "data")
        env["MXREADY_TEMP_DIR"] = str(work / "data" / "tmp")
        with (work / "server.log").open("w+", encoding="utf-8") as log:
            process = subprocess.Popen(
                [*start, "--port", str(port)],
                cwd=work,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
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
                            log.seek(0)
                            raise RuntimeError(log.read()) from None
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
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        assert (work / "data" / "mxready.db").is_file()
    print(f"{platform} release installation, UI, API, scanning and runner smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
