from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from documents_organizer.settings import APP_NAME


class Header(ttk.Frame):
    """Application title and description header."""

    def __init__(
        self,
        parent: tk.Misc,
    ) -> None:
        super().__init__(parent)

        self.columnconfigure(
            0,
            weight=1,
        )

        title = ttk.Label(
            self,
            text=APP_NAME,
            style="AppTitle.TLabel",
        )

        title.grid(
            row=0,
            column=0,
            sticky="w",
        )

        subtitle = ttk.Label(
            self,
            text=(
                "Organize files by modified date "
                "and file type."
            ),
            style="AppSubtitle.TLabel",
        )

        subtitle.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(
                2,
                0,
            ),
        )