from __future__ import annotations

import shutil
from pathlib import Path


SYSTEM_FILES = {
    ".DS_Store",
    "Thumbs.db",
}


def get_unique_destination(destination: Path) -> Path:
    """
    Return a destination path that does not overwrite an existing file.

    Example:
        report.pdf
        report (1).pdf
        report (2).pdf
    """
    if not destination.exists():
        return destination

    parent = destination.parent
    stem = destination.stem
    suffix = destination.suffix

    counter = 1

    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"

        if not candidate.exists():
            return candidate

        counter += 1


def move_file_safely(source: Path, destination: Path) -> Path:
    """
    Move a file without silently overwriting an existing file.

    The destination directory is created automatically when necessary.

    Returns the final destination path.
    """
    source = Path(source)
    destination = Path(destination)

    if not source.exists():
        raise FileNotFoundError(f"Source file does not exist: {source}")

    if not source.is_file():
        raise ValueError(f"Source path is not a file: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)

    final_destination = get_unique_destination(destination)

    shutil.move(str(source), str(final_destination))

    return final_destination


def should_ignore_file(path: Path) -> bool:
    """Return True when a file should be ignored by organizer operations."""
    return path.name in SYSTEM_FILES