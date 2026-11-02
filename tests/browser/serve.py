"""Isolated browser-test service; only copies controlled source fixtures."""

import argparse
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import uvicorn

import mxready.app as app_module
from mxready.config import Settings
from mxready.models import ScanStatus, summarize_findings
from mxready.persistence.sqlite import SQLiteStore
from mxready.scanning.analyzer import ScanAnalyzer
from mxready.scanning.rule_loader import load_rule_catalog

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/repositories/cuda_extension"
SCAN_ID = UUID("00000000-0000-0000-0000-000000000099")


class FixtureGit:
    def clone(self, identity, ref, destination):
        shutil.copytree(FIXTURE, destination)
        return "a" * 40


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8173)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="mxready-browser-") as directory:
        root = Path(directory)
        settings = Settings(
            data_dir=root / "data", temp_dir=root / "tmp", frontend_dist=ROOT / "frontend/dist"
        )
        store = SQLiteStore(settings.data_dir / "mxready.db")
        store.initialize()
        job = store.create_job("https://github.com/example/large-fixture", None)
        with store._connect() as connection:
            connection.execute(
                "UPDATE scan_jobs SET id = ? WHERE id = ?", (str(SCAN_ID), str(job.id))
            )
        report = ScanAnalyzer(load_rule_catalog(settings.rules_dir)).analyze(
            FIXTURE,
            repository_url=job.repo_url,
            commit="a" * 40,
            scan_id=SCAN_ID,
            stage_callback=lambda _: None,
        )
        findings = [
            report.findings[0].model_copy(update={"relative_path": f"csrc/fixture-{i}.cu"})
            for i in range(1000)
        ]
        report = report.model_copy(
            update={"findings": findings, "summary": summarize_findings(findings)}
        )
        store.save_report(report)
        store.update_job(SCAN_ID, status=ScanStatus.COMPLETED, stage_message="fixture complete")
        app_module.GitClient = FixtureGit
        uvicorn.run(
            app_module.create_app(settings), host="127.0.0.1", port=args.port, log_level="warning"
        )


if __name__ == "__main__":
    main()
