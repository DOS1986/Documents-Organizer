from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk


class FolderSummary(ttk.LabelFrame):
    """Displays the selected root folder and current operation target."""

    def __init__(
        self,
        parent: tk.Misc,
    ) -> None:
        super().__init__(
            parent,
            text="Selected Location",
            style="Section.TLabelframe",
        )

        self._root_folder_var = tk.StringVar(
            value="No folder selected"
        )

        self._target_folder_var = tk.StringVar(
            value="No folder selected"
        )

        self.columnconfigure(
            1,
            weight=1,
        )

        ttk.Label(
            self,
            text="Root Folder:",
        ).grid(
            row=0,
            column=0,
            sticky="nw",
            padx=(
                0,
                10,
            ),
            pady=2,
        )

        ttk.Label(
            self,
            textvariable=self._root_folder_var,
            style="PathLabel.TLabel",
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=2,
        )

        ttk.Label(
            self,
            text="Operation Target:",
        ).grid(
            row=1,
            column=0,
            sticky="nw",
            padx=(
                0,
                10,
            ),
            pady=2,
        )

        ttk.Label(
            self,
            textvariable=self._target_folder_var,
            style="PathLabel.TLabel",
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=2,
        )

    def set_root(
        self,
        path: Path | str,
    ) -> None:
        """Set the selected root folder."""
        self._root_folder_var.set(
            str(path)
        )

    def set_target(
        self,
        path: Path | str,
    ) -> None:
        """Set the current operation target."""
        self._target_folder_var.set(
            str(path)
        )

    def clear_root(self) -> None:
        """Clear the selected root folder."""
        self._root_folder_var.set(
            "No folder selected"
        )

    def clear_target(self) -> None:
        """Clear the current operation target."""
        self._target_folder_var.set(
            "No folder selected"
        )

    def clear(self) -> None:
        """Clear both displayed folder paths."""
        self.clear_root()
        self.clear_target()