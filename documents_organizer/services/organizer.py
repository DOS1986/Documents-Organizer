from __future__ import annotations

import datetime
import os
from dataclasses import dataclass, field
from pathlib import Path

from documents_organizer.filesystem import (
    move_file_safely,
    should_ignore_file,
)


@dataclass(frozen=True)
class OrganizationFailure:
    """Represents a file or directory that could not be processed."""

    path: Path
    error: str


@dataclass
class OrganizationResult:
    """Summary of a completed organization operation."""

    moved: int = 0
    skipped: int = 0
    by_extension: dict[str, int] = field(default_factory=dict)
    failures: list[OrganizationFailure] = field(default_factory=list)

    @property
    def failed(self) -> int:
        """Return the number of failed files or directories."""
        return len(self.failures)


def organize_directory(folder: Path | str) -> OrganizationResult:
    """
    Organize all files beneath a directory by modified date and file type.

    Files from nested directories are centralized into the selected root.

    Example:

        Downloads/
            report.pdf
            project/
                notes.txt

    becomes:

        Downloads/
            2026-08-25/
                pdf/
                    report.pdf
                txt/
                    notes.txt
    """
    root = Path(folder).resolve()

    if not root.exists():
        raise FileNotFoundError(
            f"Folder does not exist: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Path is not a directory: {root}"
        )

    files, discovery_failures = _snapshot_files(root)

    result = OrganizationResult(
        failures=discovery_failures,
    )

    for source in files:
        _organize_file(
            root=root,
            source=source,
            result=result,
        )

    return result


def _snapshot_files(
    root: Path,
) -> tuple[list[Path], list[OrganizationFailure]]:
    """
    Capture the files that exist before organization begins.

    Taking a snapshot prevents directories created by the organizer from
    being discovered and processed during the same operation.
    """
    files: list[Path] = []
    failures: list[OrganizationFailure] = []

    def handle_walk_error(error: OSError) -> None:
        error_path = Path(
            error.filename
            if error.filename
            else root
        )

        failures.append(
            OrganizationFailure(
                path=error_path,
                error=str(error),
            )
        )

    for current_root, directories, filenames in os.walk(
        root,
        onerror=handle_walk_error,
        followlinks=False,
    ):
        current_path = Path(current_root)

        for filename in filenames:
            files.append(
                current_path / filename
            )

    return files, failures


def _organize_file(
    root: Path,
    source: Path,
    result: OrganizationResult,
) -> None:
    """Organize one file and update the operation result."""
    try:
        if not source.exists():
            raise FileNotFoundError(
                f"File no longer exists: {source}"
            )

        if not source.is_file():
            result.skipped += 1
            return

        if should_ignore_file(source):
            result.skipped += 1
            return

        if is_already_organized(
            source,
            root,
        ):
            result.skipped += 1
            return

        extension_name = get_extension_name(
            source
        )

        modified_date = get_modified_date(
            source
        )

        destination = (
            root
            / modified_date
            / extension_name
            / source.name
        )

        move_file_safely(
            source,
            destination,
        )

        result.moved += 1

        result.by_extension[extension_name] = (
            result.by_extension.get(
                extension_name,
                0,
            )
            + 1
        )

    except (
        FileNotFoundError,
        PermissionError,
        OSError,
        ValueError,
    ) as exc:
        result.failures.append(
            OrganizationFailure(
                path=source,
                error=str(exc),
            )
        )


def get_extension_name(path: Path) -> str:
    """
    Return the folder name used for a file type.

    Files without an extension are placed in the 'other' folder.
    """
    suffix = path.suffix.lower()

    if not suffix:
        return "other"

    return suffix.lstrip(".")


def get_modified_date(path: Path) -> str:
    """Return the file's modified date in YYYY-MM-DD format."""
    modified_timestamp = path.stat().st_mtime

    return datetime.datetime.fromtimestamp(
        modified_timestamp
    ).strftime("%Y-%m-%d")


def is_already_organized(
    path: Path,
    root: Path,
) -> bool:
    """
    Return True when a file is already in the organizer's date/type layout.

    Expected layout relative to the selected root:

        YYYY-MM-DD/
            extension/
                filename

    Example:

        2026-08-25/
            pdf/
                report.pdf
    """
    try:
        relative_path = path.resolve().relative_to(
            root.resolve()
        )
    except ValueError:
        return False

    parts = relative_path.parts

    if len(parts) != 3:
        return False

    date_directory = parts[0]
    extension_directory = parts[1]

    try:
        parsed_date = datetime.date.fromisoformat(
            date_directory
        )
    except ValueError:
        return False

    if parsed_date.isoformat() != date_directory:
        return False

    expected_extension = get_extension_name(
        path
    )

    return (
        extension_directory.lower()
        == expected_extension.lower()
    )