import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


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
