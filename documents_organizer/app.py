import tkinter as tk

from documents_organizer.ui.main_window import MainWindow


def run() -> None:
    """Start Documents Organizer."""
    root = tk.Tk()

    app = MainWindow(
        root
    )

    root.mainloop()