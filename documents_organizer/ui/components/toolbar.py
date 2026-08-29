from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class Toolbar(ttk.Frame):
    """Primary application action toolbar."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_select_folder: Callable[[], None],
        on_organize: Callable[[], None],
        on_flatten: Callable[[], None],
        on_cancel: Callable[[], None],
        on_open_selected: Callable[[], None],
        on_refresh: Callable[[], None],
        on_clear_log: Callable[[], None],
    ) -> None:
        super().__init__(
            parent
        )

        self.columnconfigure(
            5,
            weight=1,
        )

        self._select_folder_button = ttk.Button(
            self,
            text="Select Folder",
            command=on_select_folder,
            style="Primary.TButton",
        )

        self._select_folder_button.grid(
            row=0,
            column=0,
            padx=(
                0,
                6,
            ),
        )

        first_separator = ttk.Separator(
            self,
            orient=tk.VERTICAL,
        )

        first_separator.grid(
            row=0,
            column=1,
            sticky="ns",
            padx=8,
        )

        self._organize_button = ttk.Button(
            self,
            text="Organize",
            command=on_organize,
            style="Toolbar.TButton",
        )

        self._organize_button.grid(
            row=0,
            column=2,
            padx=6,
        )

        self._flatten_button = ttk.Button(
            self,
            text="Flatten",
            command=on_flatten,
            style="Toolbar.TButton",
        )

        self._flatten_button.grid(
            row=0,
            column=3,
            padx=6,
        )

        self._cancel_button = ttk.Button(
            self,
            text="Cancel",
            command=on_cancel,
            style="Toolbar.TButton",
        )

        self._cancel_button.grid(
            row=0,
            column=4,
            padx=6,
        )

        second_separator = ttk.Separator(
            self,
            orient=tk.VERTICAL,
        )

        second_separator.grid(
            row=0,
            column=6,
            sticky="ns",
            padx=8,
        )

        self._open_selected_button = ttk.Button(
            self,
            text="Open Selected",
            command=on_open_selected,
            style="Toolbar.TButton",
        )

        self._open_selected_button.grid(
            row=0,
            column=7,
            padx=6,
        )

        self._refresh_button = ttk.Button(
            self,
            text="Refresh",
            command=on_refresh,
            style="Toolbar.TButton",
        )

        self._refresh_button.grid(
            row=0,
            column=8,
            padx=6,
        )

        self._clear_log_button = ttk.Button(
            self,
            text="Clear Log",
            command=on_clear_log,
            style="Toolbar.TButton",
        )

        self._clear_log_button.grid(
            row=0,
            column=9,
            padx=(
                6,
                0,
            ),
        )

    def set_states(
        self,
        *,
        select_enabled: bool,
        operations_enabled: bool,
        cancel_enabled: bool,
        utilities_enabled: bool,
    ) -> None:
        """Update toolbar button states."""
        self._select_folder_button.configure(
            state=self._state(
                select_enabled
            )
        )

        self._organize_button.configure(
            state=self._state(
                operations_enabled
            )
        )

        self._flatten_button.configure(
            state=self._state(
                operations_enabled
            )
        )

        self._cancel_button.configure(
            state=self._state(
                cancel_enabled
            )
        )

        self._open_selected_button.configure(
            state=self._state(
                utilities_enabled
            )
        )

        self._refresh_button.configure(
            state=self._state(
                utilities_enabled
            )
        )

        # Clearing the activity log is always safe.
        self._clear_log_button.configure(
            state=tk.NORMAL
        )

    @staticmethod
    def _state(
        enabled: bool,
    ) -> str:
        """Convert a boolean to a Tkinter widget state."""
        return (
            tk.NORMAL
            if enabled
            else tk.DISABLED
        )