from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from documents_organizer import __version__


class StatusBar(ttk.Frame):
    """Displays application status, progress, and version information."""

    def __init__(
        self,
        parent: tk.Misc,
    ) -> None:
        super().__init__(
            parent
        )

        self._status_var = tk.StringVar(
            value="Ready"
        )

        self.columnconfigure(
            0,
            weight=1,
        )

        self._status_label = ttk.Label(
            self,
            textvariable=self._status_var,
            style="Status.TLabel",
        )

        self._status_label.grid(
            row=0,
            column=0,
            sticky="w",
        )

        self._progress_bar = ttk.Progressbar(
            self,
            mode="indeterminate",
            length=180,
        )

        self._progress_bar.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(
                10,
                16,
            ),
        )

        self._progress_bar.grid_remove()

        self._version_label = ttk.Label(
            self,
            text=f"v{__version__}",
            style="Version.TLabel",
        )

        self._version_label.grid(
            row=0,
            column=2,
            sticky="e",
        )

    def set_status(
        self,
        message: str,
    ) -> None:
        """Update the displayed application status."""
        self._status_var.set(
            message
        )

    def start_progress(self) -> None:
        """Show and start the indeterminate progress indicator."""
        self._progress_bar.grid()

        self._progress_bar.start(
            12
        )

    def stop_progress(self) -> None:
        """Stop and hide the progress indicator."""
        self._progress_bar.stop()

        self._progress_bar.grid_remove()