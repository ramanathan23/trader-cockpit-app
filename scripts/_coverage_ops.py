from __future__ import annotations

import sys
from pathlib import Path

from _runner import run  # scripts/ is on sys.path when run as a script


def combine_and_report(root: Path, data_files: list[Path]) -> None:
    combined = root / ".coverage"
    if combined.exists():
        combined.unlink()

    rcfile = str(root / ".coveragerc")
    run([sys.executable, "-m", "coverage", "combine", *[str(p) for p in data_files]], root)
    run([sys.executable, "-m", "coverage", "report", "--rcfile", rcfile], root)
    run(
        [sys.executable, "-m", "coverage", "xml", "--rcfile", rcfile,
         "-o", str(root / "coverage.xml")],
        root,
    )
