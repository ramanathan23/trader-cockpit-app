from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _runner import run
from _coverage_ops import combine_and_report

ROOT = Path(__file__).resolve().parents[1]
SERVICES = (
    "DataSyncService",
    "LiveFeedService",
    "MomentumScorerService",
)


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

        run(
            [sys.executable, "-m", "coverage", "run",
             "--rcfile", str(ROOT / ".coveragerc"),
             f"--data-file={data_file}",
             "-m", "pytest", "-c", "pytest.ini"],
            service_dir,
        )
        data_files.append(data_file)

    if not args.no_report:
        combine_and_report(ROOT, data_files)


if __name__ == "__main__":
    main()