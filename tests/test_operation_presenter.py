from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from documents_organizer.presenters.operation_presenter import (
    present_flatten_error,
    present_flatten_result,
    present_organization_error,
    present_organization_result,
)


def test_present_organization_result() -> None:
    result = SimpleNamespace(
        moved=4,
        skipped=1,
        failed=1,
        by_extension={
            "pdf": 3,
            "txt": 1,
        },
        failures=[
            SimpleNamespace(
                path=Path("broken.pdf"),
                error="Access denied",
            )
        ],
    )

    presentation = present_organization_result(
        result
    )

    assert presentation.log_messages == (
        "Organized 3 pdf files.",
        "Organized 1 txt file.",
        "Skipped 1 file.",
        "Encountered 1 failure.",
        "  broken.pdf: Access denied",
        "Organization complete. 4 files moved.",
    )

    assert presentation.status == (
        "Organization complete — "
        "4 files moved."
    )


def test_present_organization_error() -> None:
    presentation = present_organization_error(
        "Access denied"
    )

    assert presentation.log_messages == (
        "Organization failed: Access denied",
    )

    assert presentation.status == (
        "Organization failed."
    )


def test_present_flatten_result() -> None:
    result = SimpleNamespace(
        moved=5,
        skipped=2,
        failed=0,
        directories_removed=3,
        cancelled=False,
        by_extension={
            "jpg": 2,
            "pdf": 3,
        },
        failures=[],
    )

    presentation = present_flatten_result(
        result
    )

    assert presentation.log_messages == (
        "Flattened 2 jpg files.",
        "Flattened 3 pdf files.",
        (
            "Skipped 2 files that did not match "
            "their file-type folder."
        ),
        (
            "Flattening complete. "
            "5 files moved and "
            "3 empty folders removed."
        ),
    )

    assert presentation.status == (
        "Flattening complete — "
        "5 files moved."
    )


def test_present_cancelled_flatten_result() -> None:
    result = SimpleNamespace(
        moved=2,
        skipped=0,
        failed=0,
        directories_removed=1,
        cancelled=True,
        by_extension={
            "pdf": 2,
        },
        failures=[],
    )

    presentation = present_flatten_result(
        result
    )

    assert presentation.log_messages == (
        "Flattened 2 pdf files.",
        "Flattening canceled.",
    )

    assert presentation.status == (
        "Flattening canceled."
    )


def test_present_flatten_error() -> None:
    presentation = present_flatten_error(
        "Unable to move file"
    )

    assert presentation.log_messages == (
        "Flattening failed: Unable to move file",
    )

    assert presentation.status == (
        "Flattening failed."
    )