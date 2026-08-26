import tkinter as tk

from documents_organizer.ui.main_window import MainWindow


def run() -> None:
    root = tk.Tk()

    MainWindow(root)

    root.mainloop()