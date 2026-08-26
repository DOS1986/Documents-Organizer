from __future__ import annotations

import tkinter as tk
import tkinter.scrolledtext as scrolledtext
from datetime import datetime
from tkinter import ttk


class ActivityLog(ttk.LabelFrame):
    """Activity log panel for displaying application messages."""

    def __init__(
        self,
        parent: tk.Misc,
    ) -> None:
        super().__init__(
            parent,
            text="Activity Log",
            style="Section.TLabelframe",
        )

        self.rowconfigure(
            0,
            weight=1,
        )

        self.columnconfigure(
            0,
            weight=1,
        )

        self._text = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=(
                "Consolas",
                10,
            ),
            padx=10,
            pady=10,
            relief=tk.SOLID,
            borderwidth=1,
        )

        self._text.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

    def write(
        self,
        message: str,
    ) -> None:
        """Append a timestamped message to the activity log."""
        timestamp = datetime.now().strftime(
            "%H:%M:%S"
        )

        self._text.configure(
            state=tk.NORMAL
        )

        self._text.insert(
            tk.END,
            f"[{timestamp}] {message}\n",
        )

        self._text.configure(
            state=tk.DISABLED
        )

        self._text.see(
            tk.END
        )

    def clear(self) -> None:
        """Remove all messages from the activity log."""
        self._text.configure(
            state=tk.NORMAL
        )

        self._text.delete(
            "1.0",
            tk.END,
        )

        self._text.configure(
            state=tk.DISABLED
        )