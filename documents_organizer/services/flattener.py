from __future__ import annotations

import datetime
import threading
from dataclasses import dataclass, field
from pathlib import Path

from documents_organizer.filesystem import move_file_safely
from documents_organizer.services.organizer import get_extension_name


@dataclass(frozen=True)
class FlattenFailure:
    """Represents a file or directory that could not be processed."""

    path: Path
    error: str


@dataclass
class FlattenResult:
    """Summary of a flatten operation."""

    moved: int = 0
    skipped: int = 0
    directories_removed: int = 0
    cancelled: bool = False
    by_extension: dict[str, int] = field(default_factory=dict)
    failures: list[FlattenFailure] = field(default_factory=list)

    @property
    def failed(self) -> int:
        """Return the number of failures."""
        return len(self.failures)


def flatten_directory(
    folder: Path | str,
    cancel_event: threading.Event | None = None,
) -> FlattenResult:
    """
    Flatten a Documents Organizer date/type directory structure.

    Expected structure:

        selected-folder/
            YYYY-MM-DD/
                extension/
                    filename

    Files are moved back into the selected root directory.

    Existing files are never silently overwritten. Duplicate names are
    resolved by move_file_safely().

    Only directories that match the organizer's expected structure are
    processed.
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

    if cancel_event is None:
        cancel_event = threading.Event()

    result = FlattenResult()

    try:
        root_items = list(root.iterdir())
    except OSError as exc:
        raise OSError(
            f"Unable to read folder: {root}"
        ) from exc

    date_directories = [
        item
        for item in root_items
        if item.is_dir()
        and is_date_directory(item)
    ]

    for date_directory in sorted(
        date_directories
    ):
        if cancel_event.is_set():
            result.cancelled = True
            return result

        _flatten_date_directory(
            root=root,
            date_directory=date_directory,
            cancel_event=cancel_event,
            result=result,
        )

        if cancel_event.is_set():
            result.cancelled = True
            return result

        _remove_if_empty(
            date_directory,
            result,
        )

    return result


def _flatten_date_directory(
    root: Path,
    date_directory: Path,
    cancel_event: threading.Event,
    result: FlattenResult,
) -> None:
    """Flatten the file-type directories inside one date directory."""
    try:
        items = list(
            date_directory.iterdir()
        )
    except OSError as exc:
        result.failures.append(
            FlattenFailure(
                path=date_directory,
                error=str(exc),
            )
        )
        return

    type_directories = [
        item
        for item in items
        if item.is_dir()
    ]

    for type_directory in sorted(
        type_directories
    ):
        if cancel_event.is_set():
            return

        _flatten_type_directory(
            root=root,
            type_directory=type_directory,
            cancel_event=cancel_event,
            result=result,
        )

        if cancel_event.is_set():
            return

        _remove_if_empty(
            type_directory,
            result,
        )


def _flatten_type_directory(
    root: Path,
    type_directory: Path,
    cancel_event: threading.Event,
    result: FlattenResult,
) -> None:
    """Move valid files from one file-type directory back to the root."""
    try:
        items = list(
            type_directory.iterdir()
        )
    except OSError as exc:
        result.failures.append(
            FlattenFailure(
                path=type_directory,
                error=str(exc),
            )
        )
        return

    for source in items:
        if cancel_event.is_set():
            return

        if not source.is_file():
            continue

        expected_type = get_extension_name(
            source
        )

        actual_type = (
            type_directory.name.lower()
        )

        if (
            actual_type
            != expected_type.lower()
        ):
            result.skipped += 1
            continue

        destination = (
            root
            / source.name
        )

        try:
            final_destination = (
                move_file_safely(
                    source,
                    destination,
                )
            )

            result.moved += 1

            result.by_extension[
                expected_type
            ] = (
                result.by_extension.get(
                    expected_type,
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
                FlattenFailure(
                    path=source,
                    error=str(exc),
                )
            )


def _remove_if_empty(
    directory: Path,
    result: FlattenResult,
) -> None:
    """
    Remove a directory only when it is completely empty.

    This deliberately uses rmdir() instead of recursive deletion so the
    flattener cannot accidentally delete unexpected contents.
    """
    try:
        if not directory.exists():
            return

        if not directory.is_dir():
            return

        if any(directory.iterdir()):
            return

        directory.rmdir()

        result.directories_removed += 1

    except OSError as exc:
        result.failures.append(
            FlattenFailure(
                path=directory,
                error=str(exc),
            )
        )


def is_date_directory(
    path: Path,
) -> bool:
    """Return True when a directory name is an ISO YYYY-MM-DD date."""
    if not path.is_dir():
        return False

    try:
        parsed_date = (
            datetime.date.fromisoformat(
                path.name
            )
        )
    except ValueError:
        return False

    return (
        parsed_date.isoformat()
        == path.name
    )