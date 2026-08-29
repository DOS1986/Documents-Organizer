from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pytest

from documents_organizer.controllers import (
    operation_controller as operation_controller_module,
)
from documents_organizer.controllers.operation_controller import (
    OperationController,
)


class FakeRoot:
    """Minimal Tkinter root replacement for controller tests."""

    def __init__(self) -> None:
        self._counter = 0
        self.callbacks: dict[
            str,
            Callable[[], None],
        ] = {}

        self.cancelled_callbacks: list[str] = []

    def after(
        self,
        delay_ms: int,
        callback: Callable[[], None],
    ) -> str:
        """Record an after callback without requiring Tkinter."""
        self._counter += 1

        callback_id = (
            f"after-{self._counter}"
        )

        self.callbacks[
            callback_id
        ] = callback

        return callback_id

    def after_cancel(
        self,
        callback_id: str,
    ) -> None:
        """Cancel a scheduled callback."""
        self.cancelled_callbacks.append(
            callback_id
        )

        self.callbacks.pop(
            callback_id,
            None,
        )

    def run_next_callback(
        self,
    ) -> None:
        """Execute the next scheduled callback."""
        if not self.callbacks:
            raise AssertionError(
                "No scheduled callback is available."
            )

        callback_id = next(
            iter(self.callbacks)
        )

        callback = self.callbacks.pop(
            callback_id
        )

        callback()


class ImmediateThread:
    """Thread replacement that executes its target synchronously."""

    def __init__(
        self,
        *,
        target: Callable[..., None],
        args: tuple[object, ...] = (),
        daemon: bool | None = None,
        name: str | None = None,
    ) -> None:
        self.target = target
        self.args = args
        self.daemon = daemon
        self.name = name

    def start(self) -> None:
        """Execute the thread target immediately."""
        self.target(
            *self.args
        )


class FakeOrganizationResult:
    """Test replacement for OrganizationResult."""


class FakeFlattenResult:
    """Test replacement for FlattenResult."""


@dataclass
class CallbackRecorder:
    """Records OperationController callback activity."""

    started: list[
        tuple[str, Path]
    ] = field(
        default_factory=list
    )

    finished: list[str] = field(
        default_factory=list
    )

    cancel_requests: int = 0

    organization_results: list[
        object
    ] = field(
        default_factory=list
    )

    organization_errors: list[
        str
    ] = field(
        default_factory=list
    )

    flatten_results: list[
        object
    ] = field(
        default_factory=list
    )

    flatten_errors: list[
        str
    ] = field(
        default_factory=list
    )

    def record_started(
        self,
        operation: str,
        folder: Path,
    ) -> None:
        self.started.append(
            (
                operation,
                folder,
            )
        )

    def record_finished(
        self,
        operation: str,
    ) -> None:
        self.finished.append(
            operation
        )

    def record_cancel_request(
        self,
    ) -> None:
        self.cancel_requests += 1


def create_controller(
    root: FakeRoot,
    callbacks: CallbackRecorder,
) -> OperationController:
    """Create an OperationController using test callbacks."""
    return OperationController(
        root,
        on_started=(
            callbacks.record_started
        ),
        on_finished=(
            callbacks.record_finished
        ),
        on_cancel_requested=(
            callbacks.record_cancel_request
        ),
        on_organization_result=(
            callbacks.organization_results.append
        ),
        on_organization_error=(
            callbacks.organization_errors.append
        ),
        on_flatten_result=(
            callbacks.flatten_results.append
        ),
        on_flatten_error=(
            callbacks.flatten_errors.append
        ),
    )


@pytest.fixture
def controller_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    FakeRoot,
    CallbackRecorder,
    OperationController,
]:
    """Create a controller with GUI/thread dependencies replaced."""
    monkeypatch.setattr(
        operation_controller_module.threading,
        "Thread",
        ImmediateThread,
    )

    monkeypatch.setattr(
        operation_controller_module,
        "OrganizationResult",
        FakeOrganizationResult,
    )

    monkeypatch.setattr(
        operation_controller_module,
        "FlattenResult",
        FakeFlattenResult,
    )

    root = FakeRoot()

    callbacks = CallbackRecorder()

    controller = create_controller(
        root,
        callbacks,
    )

    return (
        root,
        callbacks,
        controller,
    )


def test_controller_starts_idle(
    controller_environment,
) -> None:
    """Controller should start without an active operation."""
    (
        root,
        callbacks,
        controller,
    ) = controller_environment

    assert controller.current_operation is None
    assert controller.is_busy is False
    assert controller.is_flattening is False
    assert controller.can_cancel is False

    assert callbacks.started == []
    assert callbacks.finished == []

    # Queue polling should have been scheduled.
    assert len(root.callbacks) == 1


def test_organize_success(
    controller_environment,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Successful organization should dispatch its result."""
    (
        root,
        callbacks,
        controller,
    ) = controller_environment

    result = FakeOrganizationResult()

    received_folders: list[Path] = []

    def fake_organize(
        folder: Path,
    ) -> FakeOrganizationResult:
        received_folders.append(
            folder
        )

        return result

    monkeypatch.setattr(
        operation_controller_module,
        "organize_directory",
        fake_organize,
    )

    started = controller.organize(
        tmp_path
    )

    assert started is True

    assert controller.current_operation == "organize"
    assert controller.is_busy is True
    assert controller.is_flattening is False
    assert controller.can_cancel is False

    assert received_folders == [
        tmp_path.resolve()
    ]

    assert callbacks.started == [
        (
            "organize",
            tmp_path.resolve(),
        )
    ]

    # Worker result has been queued but not dispatched yet.
    assert callbacks.organization_results == []
    assert callbacks.finished == []

    root.run_next_callback()

    assert callbacks.organization_results == [
        result
    ]

    assert callbacks.finished == [
        "organize"
    ]

    assert controller.current_operation is None
    assert controller.is_busy is False


def test_organize_error(
    controller_environment,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Organizer errors should be dispatched and finish the operation."""
    (
        root,
        callbacks,
        controller,
    ) = controller_environment

    def fake_organize(
        folder: Path,
    ) -> FakeOrganizationResult:
        raise PermissionError(
            "Access denied"
        )

    monkeypatch.setattr(
        operation_controller_module,
        "organize_directory",
        fake_organize,
    )

    assert controller.organize(
        tmp_path
    )

    assert controller.is_busy is True

    root.run_next_callback()

    assert callbacks.organization_errors == [
        "Access denied"
    ]

    assert callbacks.finished == [
        "organize"
    ]

    assert controller.is_busy is False


def test_second_operation_is_rejected_while_busy(
    controller_environment,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A second file operation should not start while one is active."""
    (
        root,
        callbacks,
        controller,
    ) = controller_environment

    result = FakeOrganizationResult()

    monkeypatch.setattr(
        operation_controller_module,
        "organize_directory",
        lambda folder: result,
    )

    assert controller.organize(
        tmp_path
    )

    assert controller.is_busy is True

    second_started = controller.flatten(
        tmp_path
    )

    assert second_started is False

    assert callbacks.started == [
        (
            "organize",
            tmp_path.resolve(),
        )
    ]

    root.run_next_callback()

    assert controller.is_busy is False


def test_flatten_success(
    controller_environment,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Successful flattening should dispatch its result."""
    (
        root,
        callbacks,
        controller,
    ) = controller_environment

    result = FakeFlattenResult()

    received_folder: Path | None = None
    received_cancel_event = None

    def fake_flatten(
        folder: Path,
        *,
        cancel_event,
    ) -> FakeFlattenResult:
        nonlocal received_folder
        nonlocal received_cancel_event

        received_folder = folder
        received_cancel_event = (
            cancel_event
        )

        return result

    monkeypatch.setattr(
        operation_controller_module,
        "flatten_directory",
        fake_flatten,
    )

    assert controller.flatten(
        tmp_path
    )

    assert controller.current_operation == "flatten"
    assert controller.is_busy is True
    assert controller.is_flattening is True
    assert controller.can_cancel is True

    assert received_folder == (
        tmp_path.resolve()
    )

    assert received_cancel_event is not None

    root.run_next_callback()

    assert callbacks.flatten_results == [
        result
    ]

    assert callbacks.finished == [
        "flatten"
    ]

    assert controller.is_busy is False
    assert controller.can_cancel is False


def test_flatten_error(
    controller_environment,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Flattener errors should be dispatched and finish the operation."""
    (
        root,
        callbacks,
        controller,
    ) = controller_environment

    def fake_flatten(
        folder: Path,
        *,
        cancel_event,
    ) -> FakeFlattenResult:
        raise OSError(
            "Flatten failed"
        )

    monkeypatch.setattr(
        operation_controller_module,
        "flatten_directory",
        fake_flatten,
    )

    assert controller.flatten(
        tmp_path
    )

    root.run_next_callback()

    assert callbacks.flatten_errors == [
        "Flatten failed"
    ]

    assert callbacks.finished == [
        "flatten"
    ]

    assert controller.is_busy is False


def test_flatten_can_be_cancelled(
    controller_environment,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Cancel should set the event and notify the application once."""
    (
        root,
        callbacks,
        controller,
    ) = controller_environment

    result = FakeFlattenResult()

    received_cancel_event = None

    def fake_flatten(
        folder: Path,
        *,
        cancel_event,
    ) -> FakeFlattenResult:
        nonlocal received_cancel_event

        received_cancel_event = (
            cancel_event
        )

        return result

    monkeypatch.setattr(
        operation_controller_module,
        "flatten_directory",
        fake_flatten,
    )

    assert controller.flatten(
        tmp_path
    )

    assert controller.can_cancel is True

    assert controller.cancel_flatten() is True

    assert callbacks.cancel_requests == 1

    assert received_cancel_event is not None
    assert received_cancel_event.is_set()

    assert controller.can_cancel is False

    # Repeated cancellation requests should be ignored.
    assert controller.cancel_flatten() is False
    assert callbacks.cancel_requests == 1

    root.run_next_callback()

    assert controller.is_busy is False


def test_cancel_is_rejected_when_not_flattening(
    controller_environment,
) -> None:
    """Cancellation should only be available for active flattening."""
    (
        root,
        callbacks,
        controller,
    ) = controller_environment

    assert controller.cancel_flatten() is False

    assert callbacks.cancel_requests == 0


def test_rejected_flatten_does_not_clear_cancel_request(
    controller_environment,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Rejecting another flatten operation must not reset
    the current operation's cancellation event.
    """
    (
        root,
        callbacks,
        controller,
    ) = controller_environment

    result = FakeFlattenResult()

    received_cancel_event = None

    def fake_flatten(
        folder: Path,
        *,
        cancel_event,
    ) -> FakeFlattenResult:
        nonlocal received_cancel_event

        received_cancel_event = (
            cancel_event
        )

        return result

    monkeypatch.setattr(
        operation_controller_module,
        "flatten_directory",
        fake_flatten,
    )

    assert controller.flatten(
        tmp_path
    )

    assert controller.cancel_flatten() is True

    assert received_cancel_event is not None
    assert received_cancel_event.is_set()

    # This must be rejected without touching the active cancellation event.
    assert controller.flatten(
        tmp_path
    ) is False

    assert received_cancel_event.is_set()

    root.run_next_callback()


def test_thread_start_failure_restores_idle_state(
    controller_environment,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Failure to start a worker thread should roll back operation state."""
    (
        root,
        callbacks,
        controller,
    ) = controller_environment

    class FailingThread:
        def __init__(
            self,
            **kwargs,
        ) -> None:
            pass

        def start(
            self,
        ) -> None:
            raise RuntimeError(
                "Unable to start thread"
            )

    monkeypatch.setattr(
        operation_controller_module.threading,
        "Thread",
        FailingThread,
    )

    with pytest.raises(
        RuntimeError,
        match="Unable to start thread",
    ):
        controller.organize(
            tmp_path
        )

    assert controller.is_busy is False
    assert controller.current_operation is None

    assert callbacks.started == [
        (
            "organize",
            tmp_path.resolve(),
        )
    ]

    assert callbacks.finished == [
        "organize"
    ]


def test_shutdown_cancels_queue_processing(
    controller_environment,
) -> None:
    """Shutdown should cancel scheduled queue polling."""
    (
        root,
        callbacks,
        controller,
    ) = controller_environment

    assert len(root.callbacks) == 1

    scheduled_id = next(
        iter(root.callbacks)
    )

    controller.shutdown()

    assert scheduled_id in (
        root.cancelled_callbacks
    )

    assert root.callbacks == {}

    # Shutdown should also be safe to call more than once.
    controller.shutdown()

    assert root.cancelled_callbacks == [
        scheduled_id
    ]