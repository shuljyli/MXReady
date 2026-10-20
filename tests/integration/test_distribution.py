import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from runpy import run_path


def test_release_archives_contain_ui_and_platform_installers(tmp_path):
    root = Path(__file__).resolve().parents[2]
    build = run_path(str(root / "scripts" / "build_release.py"))
    source = tmp_path / "checkout"
    shutil.copytree(root / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__"))
    for filename in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy2(root / filename, source / filename)
    for folder in ("packaging", "docs"):
        shutil.copytree(root / folder, source / folder)
    frontend = source / "frontend" / "dist"
    (frontend / "assets").mkdir(parents=True)
    (frontend / "index.html").write_text('<script src="/assets/test.js"></script>')
    (frontend / "assets" / "test.js").write_text('console.log("release-ui");')
    staging = tmp_path / "staged"
    build["stage_source"](source, staging)
    output = tmp_path / "release"
    result = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(output), str(staging)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    wheel_path = next(output.glob("*.whl"))
    archives = build["build_archives"](source, wheel_path, output, "0.1.0")
    assert len(archives) == 3
    for archive in archives:
        prefix = archive.stem + "/"
        with zipfile.ZipFile(archive) as bundle:
            names = {name.removeprefix(prefix) for name in bundle.namelist()}
            assert {"install.py", "INSTALL.md", "LICENSE", "WHEEL.sha256"} <= names
            extension = "ps1" if "windows" in archive.stem else "sh"
            assert {f"install.{extension}", f"start.{extension}"} <= names
            assert not any(".venv" in name or "mxready.db" in name for name in names)
    installed = tmp_path / "installed-release"
    with zipfile.ZipFile(wheel_path) as wheel:
        wheel.extractall(installed)
    smoke = """
import sys
sys.path.insert(0, sys.argv[1])
from mxready.config import Settings
from mxready.app import create_app
from fastapi.testclient import TestClient
settings = Settings.from_env()
assert settings.frontend_dist.is_absolute()
with TestClient(create_app(settings, start_worker=False)) as client:
    assert '/assets/test.js' in client.get('/').text
    assert client.get('/assets/test.js').text == 'console.log("release-ui");'
    assert client.get('/api/missing').status_code == 404
"""
    result = subprocess.run(
        [sys.executable, "-I", "-c", smoke, str(installed)],
        cwd=tmp_path,
        env={k: v for k, v in os.environ.items() if not k.startswith("MXREADY_")},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_wheel_runs_outside_checkout_with_rules_schema_and_runner(tmp_path, report_factory):
    root = Path(__file__).resolve().parents[2]
    source = tmp_path / "source"
    source.mkdir()
    for filename in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy2(root / filename, source / filename)
    shutil.copytree(root / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__"))
    result = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(tmp_path / "dist")],
        cwd=source,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    installed = tmp_path / "installed"
    with zipfile.ZipFile(next((tmp_path / "dist").glob("*.whl"))) as wheel:
        wheel.extractall(installed)
    report_path = tmp_path / "report.json"
    report_path.write_text(report_factory().model_dump_json(), encoding="utf-8")
    smoke = """
import io, sys, zipfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from mxready.app import create_app
from mxready.config import Settings
from mxready.models import ScanReport
from mxready.scanning.rule_loader import load_rule_catalog
from mxready.verification.bundle import build_verification_bundle
from mxready.cli.scan_repository import main
from fastapi.testclient import TestClient
assert len(load_rule_catalog(Settings().rules_dir).rules) == 30
with TestClient(create_app()) as client:
    assert client.get('/api/health').status_code == 200
report = ScanReport.model_validate_json(Path(sys.argv[2]).read_text())
with zipfile.ZipFile(io.BytesIO(build_verification_bundle(report))) as bundle:
    assert 'schemas/verification-result-v1.json' in bundle.namelist()
    bundle.extractall('bundle')
Path('fixture').mkdir()
Path('fixture/setup.py').write_text('from torch.utils.cpp_extension import CUDAExtension')
assert main(['fixture','--repo-url','https://github.com/example/project',
             '--commit','a'*40,'--output','reports']) in (0,2)
"""
    clean_env = {
        k: v for k, v in os.environ.items() if k != "PYTHONPATH" and not k.startswith("MXREADY_")
    }
    result = subprocess.run(
        [sys.executable, "-I", "-c", smoke, str(installed), str(report_path)],
        cwd=tmp_path,
        env=clean_env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    runner = subprocess.run(
        [sys.executable, "-S", "-m", "mxready_runner", "--help"],
        cwd=tmp_path / "bundle",
        env=clean_env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert runner.returncode == 0, runner.stderr
