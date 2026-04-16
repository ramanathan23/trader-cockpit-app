from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICES = (
    "DataSyncService",
    "LiveFeedService",
    "MomentumScorerService",
)


def run(command: list[str], cwd: Path) -> None:
    completed = subprocess.run(command, cwd=cwd)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run isolated pytest suites for each Python service and combine coverage."
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Run tests only, skipping coverage combine/report output.",
    )
    args = parser.parse_args()

    data_files: list[Path] = []

    for service in SERVICES:
        service_dir = ROOT / service
        data_file = ROOT / f".coverage.{service.lower()}"
        if data_file.exists():
            data_file.unlink()

        command = [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--rcfile",
            str(ROOT / ".coveragerc"),
            f"--data-file={data_file}",
            "-m",
            "pytest",
            "-c",
            "pytest.ini",
        ]
        run(command, service_dir)
        data_files.append(data_file)

    if args.no_report:
        return

    combined_file = ROOT / ".coverage"
    if combined_file.exists():
        combined_file.unlink()

    run(
        [
            sys.executable,
            "-m",
            "coverage",
            "combine",
            *[str(path) for path in data_files],
        ],
        ROOT,
    )
    run(
        [
            sys.executable,
            "-m",
            "coverage",
            "report",
            "--rcfile",
            str(ROOT / ".coveragerc"),
        ],
        ROOT,
    )
    run(
        [
            sys.executable,
            "-m",
            "coverage",
            "xml",
            "--rcfile",
            str(ROOT / ".coveragerc"),
            "-o",
            str(ROOT / "coverage.xml"),
        ],
        ROOT,
    )


if __name__ == "__main__":
    main()