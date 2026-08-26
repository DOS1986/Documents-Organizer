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
    Organize files beneath a directory by extension and modification date.

    Files are first discovered before any files are moved. This prevents
    directories created by the organization process from being discovered
    and processed again during the same operation.

    Example:

        Downloads/
            report.pdf

    becomes:

        Downloads/
            pdf/
                2026-08-25/
                    report.pdf
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
            source,
            result,
        )

    return result


def _snapshot_files(
    root: Path,
) -> tuple[list[Path], list[OrganizationFailure]]:
    """
    Capture the files that exist before organization begins.

    Taking a snapshot prevents newly-created extension/date directories
    from being traversed by the current organization operation.
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

        if is_already_organized(source):
            result.skipped += 1
            return

        extension_name = get_extension_name(source)

        modified_date = get_modified_date(
            source
        )

        destination = (
            source.parent
            / extension_name
            / modified_date
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
    Return the directory name used for a file extension.

    Files without an extension are placed in the 'other' directory.
    """
    suffix = path.suffix.lower()

    if not suffix:
        return "other"

    return suffix.lstrip(".")


def get_modified_date(path: Path) -> str:
    """Return the file modification date in YYYY-MM-DD format."""
    modified_timestamp = path.stat().st_mtime

    return datetime.datetime.fromtimestamp(
        modified_timestamp
    ).strftime("%Y-%m-%d")


def is_already_organized(path: Path) -> bool:
    """
    Return True when a file already appears to be in an organized location.

    Expected structure:

        <extension>/<YYYY-MM-DD>/<filename>

    Example:

        pdf/2026-08-25/report.pdf
    """
    date_directory = path.parent

    extension_directory = date_directory.parent

    expected_extension = get_extension_name(
        path
    )

    if (
        extension_directory.name.lower()
        != expected_extension.lower()
    ):
        return False

    try:
        parsed_date = datetime.date.fromisoformat(
            date_directory.name
        )
    except ValueError:
        return False

    return (
        parsed_date.isoformat()
        == date_directory.name
    )