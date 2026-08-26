from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def configure_styles(root: tk.Misc) -> None:
    """Configure ttk styles used by Documents Organizer."""
    style = ttk.Style(root)

    style.configure(
        "AppTitle.TLabel",
        font=(
            "Segoe UI",
            18,
            "bold",
        ),
    )

    style.configure(
        "AppSubtitle.TLabel",
        font=(
            "Segoe UI",
            10,
        ),
    )

    style.configure(
        "Version.TLabel",
        font=(
            "Segoe UI",
            9,
        ),
    )

    style.configure(
        "Toolbar.TButton",
        padding=(
            10,
            7,
        ),
    )

    style.configure(
        "Primary.TButton",
        padding=(
            12,
            7,
        ),
    )

    style.configure(
        "Section.TLabelframe",
        padding=10,
    )

    style.configure(
        "Section.TLabelframe.Label",
        font=(
            "Segoe UI",
            10,
            "bold",
        ),
    )

    style.configure(
        "PathLabel.TLabel",
        font=(
            "Segoe UI",
            9,
        ),
    )

    style.configure(
        "Status.TLabel",
        padding=(
            4,
            2,
        ),
    )

    style.configure(
        "Treeview",
        rowheight=26,
        font=(
            "Segoe UI",
            10,
        ),
    )