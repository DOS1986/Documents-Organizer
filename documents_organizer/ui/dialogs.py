from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from documents_organizer import __version__
from documents_organizer.settings import APP_NAME


def show_error(
    parent: tk.Misc,
    title: str,
    message: str,
) -> None:
    """Display an application error dialog."""
    messagebox.showerror(
        title,
        message,
        parent=parent,
    )


def show_warning(
    parent: tk.Misc,
    title: str,
    message: str,
) -> None:
    """Display an application warning dialog."""
    messagebox.showwarning(
        title,
        message,
        parent=parent,
    )


def ask_confirmation(
    parent: tk.Misc,
    title: str,
    message: str,
) -> bool:
    """Display a yes/no confirmation dialog."""
    return bool(
        messagebox.askyesno(
            title,
            message,
            parent=parent,
        )
    )


def show_about(
    parent: tk.Misc,
) -> None:
    """Display information about Documents Organizer."""
    messagebox.showinfo(
        f"About {APP_NAME}",
        (
            f"{APP_NAME}\n"
            f"Version: v{__version__}\n\n"
            "Created by David Southwood\n"
            "License: MIT License"
        ),
        parent=parent,
    )