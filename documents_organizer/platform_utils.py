from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_in_file_manager(path: Path | str) -> None:
    """Open a directory using the operating system's default file manager."""
    directory = Path(path).resolve()

    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")

    if sys.platform == "win32":
        os.startfile(str(directory))

    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(directory)])

    else:
        subprocess.Popen(["xdg-open", str(directory)])