from __future__ import annotations

from dataclasses import dataclass

from documents_organizer.services.flattener import FlattenResult
from documents_organizer.services.organizer import OrganizationResult


@dataclass(frozen=True, slots=True)
class OperationPresentation:
    """User-facing messages produced from an operation result."""

    log_messages: tuple[str, ...]
    status: str


def present_organization_result(
    result: OrganizationResult,
) -> OperationPresentation:
    """Create user-facing messages for an organization result."""
    messages: list[str] = []

    for extension, count in sorted(
        result.by_extension.items()
    ):
        messages.append(
            (
                f"Organized {count} "
                f"{extension} {_pluralize('file', count)}."
            )
        )

    if result.skipped:
        messages.append(
            (
                f"Skipped {result.skipped} "
                f"{_pluralize('file', result.skipped)}."
            )
        )

    if result.failed:
        messages.append(
            (
                f"Encountered {result.failed} "
                f"{_pluralize('failure', result.failed)}."
            )
        )

        for failure in result.failures:
            messages.append(
                f"  {failure.path}: {failure.error}"
            )

    messages.append(
        (
            "Organization complete. "
            f"{result.moved} files moved."
        )
    )

    return OperationPresentation(
        log_messages=tuple(messages),
        status=(
            "Organization complete — "
            f"{result.moved} files moved."
        ),
    )


def present_organization_error(
    message: str,
) -> OperationPresentation:
    """Create user-facing messages for a fatal organization error."""
    return OperationPresentation(
        log_messages=(
            f"Organization failed: {message}",
        ),
        status="Organization failed.",
    )


def present_flatten_result(
    result: FlattenResult,
) -> OperationPresentation:
    """Create user-facing messages for a flatten result."""
    messages: list[str] = []

    for extension, count in sorted(
        result.by_extension.items()
    ):
        messages.append(
            (
                f"Flattened {count} "
                f"{extension} {_pluralize('file', count)}."
            )
        )

    if result.skipped:
        messages.append(
            (
                f"Skipped {result.skipped} "
                f"{_pluralize('file', result.skipped)} "
                "that did not match their "
                "file-type folder."
            )
        )

    if result.failed:
        messages.append(
            (
                f"Encountered {result.failed} "
                f"{_pluralize('failure', result.failed)}."
            )
        )

        for failure in result.failures:
            messages.append(
                f"  {failure.path}: {failure.error}"
            )

    if result.cancelled:
        messages.append(
            "Flattening canceled."
        )

        status = "Flattening canceled."

    else:
        messages.append(
            (
                "Flattening complete. "
                f"{result.moved} files moved and "
                f"{result.directories_removed} "
                "empty folders removed."
            )
        )

        status = (
            "Flattening complete — "
            f"{result.moved} files moved."
        )

    return OperationPresentation(
        log_messages=tuple(messages),
        status=status,
    )


def present_flatten_error(
    message: str,
) -> OperationPresentation:
    """Create user-facing messages for a fatal flatten error."""
    return OperationPresentation(
        log_messages=(
            f"Flattening failed: {message}",
        ),
        status="Flattening failed.",
    )


def _pluralize(
    singular: str,
    count: int,
) -> str:
    """Return a simple singular or plural word."""
    if count == 1:
        return singular

    if singular == "failure":
        return "failures"

    return f"{singular}s"