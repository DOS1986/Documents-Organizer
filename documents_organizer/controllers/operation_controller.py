from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from documents_organizer.services.flattener import (
    FlattenResult,
    flatten_directory,
)
from documents_organizer.services.organizer import (
    OrganizationResult,
    organize_directory,
)
from documents_organizer.settings import (
    UI_QUEUE_POLL_INTERVAL_MS,
)


OperationName = Literal[
    "organize",
    "flatten",
]


class OperationController:
    """Coordinate background file operations."""

    def __init__(
        self,
        root: tk.Misc,
        *,
        on_started: Callable[
            [OperationName, Path],
            None,
        ],
        on_finished: Callable[
            [OperationName],
            None,
        ],
        on_cancel_requested: Callable[
            [],
            None,
        ],
        on_organization_result: Callable[
            [OrganizationResult],
            None,
        ],
        on_organization_error: Callable[
            [str],
            None,
        ],
        on_flatten_result: Callable[
            [FlattenResult],
            None,
        ],
        on_flatten_error: Callable[
            [str],
            None,
        ],
    ) -> None:
        self._root = root

        self._on_started = on_started
        self._on_finished = on_finished
        self._on_cancel_requested = (
            on_cancel_requested
        )

        self._on_organization_result = (
            on_organization_result
        )

        self._on_organization_error = (
            on_organization_error
        )

        self._on_flatten_result = (
            on_flatten_result
        )

        self._on_flatten_error = (
            on_flatten_error
        )

        self._current_operation: (
            OperationName | None
        ) = None

        self._flatten_cancel_event = (
            threading.Event()
        )

        self._queue: queue.Queue[
            tuple[str, object]
        ] = queue.Queue()

        self._closed = False
        self._after_id: str | None = None

        self._schedule_queue_processing()

    # -------------------------------------------------------------------------
    # State
    # -------------------------------------------------------------------------

    @property
    def current_operation(
        self,
    ) -> OperationName | None:
        """Return the currently running operation."""
        return self._current_operation

    @property
    def is_busy(self) -> bool:
        """Return whether a file operation is running."""
        return (
            self._current_operation
            is not None
        )

    @property
    def is_flattening(self) -> bool:
        """Return whether a flatten operation is running."""
        return (
            self._current_operation
            == "flatten"
        )

    @property
    def can_cancel(self) -> bool:
        """Return whether the active flatten operation can be canceled."""
        return (
            self.is_flattening
            and not self._flatten_cancel_event.is_set()
        )

    # -------------------------------------------------------------------------
    # Public operations
    # -------------------------------------------------------------------------

    def organize(
        self,
        folder: Path | str,
    ) -> bool:
        """Start an organize operation."""
        target = Path(
            folder
        ).resolve()

        if not self._begin_operation(
            "organize",
            target,
        ):
            return False

        try:
            worker = threading.Thread(
                target=self._run_organizer_worker,
                args=(
                    target,
                ),
                daemon=True,
                name="documents-organizer-organize",
            )

            worker.start()

        except Exception:
            self._finish_operation(
                "organize"
            )
            raise

        return True

    def flatten(
        self,
        folder: Path | str,
    ) -> bool:
        """Start a flatten operation."""
        target = Path(
            folder
        ).resolve()

        if not self._begin_operation(
            "flatten",
            target,
        ):
            return False

        try:
            worker = threading.Thread(
                target=self._run_flattener_worker,
                args=(
                    target,
                ),
                daemon=True,
                name="documents-organizer-flatten",
            )

            worker.start()

        except Exception:
            self._finish_operation(
                "flatten"
            )
            raise

        return True

    def cancel_flatten(self) -> bool:
        """Request cancellation of the active flatten operation."""
        if not self.can_cancel:
            return False

        self._flatten_cancel_event.set()

        self._on_cancel_requested()

        return True

    def shutdown(self) -> None:
        """Stop controller queue processing."""
        if self._closed:
            return

        self._closed = True

        if self._after_id is not None:
            try:
                self._root.after_cancel(
                    self._after_id
                )

            except tk.TclError:
                pass

            self._after_id = None

    # -------------------------------------------------------------------------
    # Operation lifecycle
    # -------------------------------------------------------------------------

    def _begin_operation(
            self,
            operation: OperationName,
            folder: Path,
    ) -> bool:
        """Mark an operation as active."""
        if self._current_operation is not None:
            return False

        if operation == "flatten":
            self._flatten_cancel_event.clear()

        self._current_operation = (
            operation
        )

        try:
            self._on_started(
                operation,
                folder,
            )

        except Exception:
            self._current_operation = None
            raise

        return True

    def _finish_operation(
        self,
        operation: OperationName,
    ) -> None:
        """Mark an operation as complete."""
        if (
            self._current_operation
            != operation
        ):
            return

        self._current_operation = None

        self._on_finished(
            operation
        )

    # -------------------------------------------------------------------------
    # Worker threads
    # -------------------------------------------------------------------------

    def _run_organizer_worker(
        self,
        folder: Path,
    ) -> None:
        """Run the organizer service on a worker thread."""
        try:
            result = organize_directory(
                folder
            )

        except (
            FileNotFoundError,
            NotADirectoryError,
            PermissionError,
            OSError,
        ) as exc:
            self._queue.put(
                (
                    "organization_error",
                    str(exc),
                )
            )
            return

        self._queue.put(
            (
                "organization_result",
                result,
            )
        )

    def _run_flattener_worker(
        self,
        folder: Path,
    ) -> None:
        """Run the flattener service on a worker thread."""
        try:
            result = flatten_directory(
                folder,
                cancel_event=(
                    self._flatten_cancel_event
                ),
            )

        except (
            FileNotFoundError,
            NotADirectoryError,
            PermissionError,
            OSError,
        ) as exc:
            self._queue.put(
                (
                    "flatten_error",
                    str(exc),
                )
            )
            return

        self._queue.put(
            (
                "flatten_result",
                result,
            )
        )

    # -------------------------------------------------------------------------
    # Worker → UI communication
    # -------------------------------------------------------------------------

    def _schedule_queue_processing(
        self,
    ) -> None:
        """Schedule worker queue processing on the Tkinter thread."""
        if self._closed:
            return

        self._after_id = self._root.after(
            UI_QUEUE_POLL_INTERVAL_MS,
            self._process_queue,
        )

    def _process_queue(self) -> None:
        """Process worker messages on the Tkinter main thread."""
        self._after_id = None

        try:
            while True:
                event_name, payload = (
                    self._queue.get_nowait()
                )

                self._dispatch_event(
                    event_name,
                    payload,
                )

        except queue.Empty:
            pass

        self._schedule_queue_processing()

    def _dispatch_event(
        self,
        event_name: str,
        payload: object,
    ) -> None:
        """Dispatch a worker result to the application."""
        if (
            event_name
            == "organization_result"
            and isinstance(
                payload,
                OrganizationResult,
            )
        ):
            try:
                self._on_organization_result(
                    payload
                )

            finally:
                self._finish_operation(
                    "organize"
                )

            return

        if (
            event_name
            == "organization_error"
        ):
            try:
                self._on_organization_error(
                    str(payload)
                )

            finally:
                self._finish_operation(
                    "organize"
                )

            return

        if (
            event_name
            == "flatten_result"
            and isinstance(
                payload,
                FlattenResult,
            )
        ):
            try:
                self._on_flatten_result(
                    payload
                )

            finally:
                self._finish_operation(
                    "flatten"
                )

            return

        if (
            event_name
            == "flatten_error"
        ):
            try:
                self._on_flatten_error(
                    str(payload)
                )

            finally:
                self._finish_operation(
                    "flatten"
                )