"""Build a UI-enabled wheel/sdist and Windows, Linux and macOS installer ZIPs."""

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

PLATFORMS = ("windows", "linux", "macos")


def stage_source(root: Path, destination: Path) -> None:
    frontend = root / "frontend" / "dist"
    if not (frontend / "index.html").is_file() or not list(frontend.glob("assets/*.js")):
        raise ValueError("Missing built UI. Build frontend before assembling a release.")
    destination.mkdir(parents=True)
    for filename in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy2(root / filename, destination / filename)
    shutil.copytree(
        root / "src",
        destination / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
    )
    shutil.copytree(frontend, destination / "src" / "mxready" / "resources" / "frontend")


def build_archives(root: Path, wheel: Path, output: Path, version: str) -> list[Path]:
    artifacts = []
    for platform in PLATFORMS:
        name = f"mxready-{version}-{platform}"
        archive = output / f"{name}.zip"
        templates = root / "packaging" / ("windows" if platform == "windows" else "unix")
        files = {
            f"packages/{wheel.name}": wheel,
            "install.py": root / "packaging" / "install.py",
            "INSTALL.md": root / "docs" / "installation.md",
            "LICENSE": root / "LICENSE",
        }
        files.update({path.name: path for path in templates.iterdir() if path.is_file()})
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for relative, source in sorted(files.items()):
                info = zipfile.ZipInfo(f"{name}/{relative}")
                info.create_system = 3
                info.external_attr = (0o100755 if relative.endswith(".sh") else 0o100644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(info, source.read_bytes())
            bundle.writestr(
                f"{name}/WHEEL.sha256",
                hashlib.sha256(wheel.read_bytes()).hexdigest() + "\n",
            )
        artifacts.append(archive)
    return artifacts


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=root / "dist")
    parser.add_argument(
        "--skip-frontend-build",
        action="store_true",
        help="Reuse frontend/dist after a successful frontend build",
    )
    args = parser.parse_args(argv)
    if not args.skip_frontend_build:
        npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
        if npm is None:
            parser.error("Node.js 22+ and npm are required to build the release UI")
        for command in ([npm, "ci"], [npm, "run", "build"]):
            subprocess.run(command, cwd=root / "frontend", check=True, timeout=600)
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    with tempfile.TemporaryDirectory(prefix="mxready-release-") as temporary:
        staging = Path(temporary)
        source = staging / "source"
        stage_source(root, source)
        output = staging / "dist"
        subprocess.run(
            [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(output), str(source)],
            check=True,
            timeout=120,
        )
        wheels = list(output.glob("*.whl"))
        if len(wheels) != 1 or not wheels[0].name.endswith("-py3-none-any.whl"):
            raise ValueError("Expected one platform-independent MXReady wheel")
        with zipfile.ZipFile(wheels[0]) as wheel:
            for asset in (root / "frontend" / "dist").rglob("*"):
                if asset.is_file():
                    relative = asset.relative_to(root / "frontend" / "dist").as_posix()
                    if f"mxready/resources/frontend/{relative}" not in wheel.namelist():
                        raise ValueError(f"Frontend asset missing from wheel: {relative}")
        build_archives(root, wheels[0], output, version)
        checksums = "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            for path in sorted(output.iterdir())
            if path.is_file()
        )
        (output / "SHA256SUMS.txt").write_text(checksums, encoding="ascii")
        args.output.mkdir(parents=True, exist_ok=True)
        for artifact in sorted(output.iterdir()):
            shutil.copy2(artifact, args.output / artifact.name)
            print(args.output / artifact.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
