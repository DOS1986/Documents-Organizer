from __future__ import annotations

import sys
from pathlib import Path


def get_resource_path(*parts: str) -> Path:
    """
    Return the absolute path to an application resource.

    During normal development, resources are resolved relative to the
    repository root.

    When packaged with PyInstaller, resources are resolved relative to
    PyInstaller's temporary extraction directory.
    """
    if getattr(sys, "frozen", False):
        base_path = Path(
            getattr(
                sys,
                "_MEIPASS",
                Path(sys.executable).parent,
            )
        )
    else:
        base_path = (
            Path(__file__)
            .resolve()
            .parent
            .parent
        )

    return base_path.joinpath(
        *parts
    )


def get_image_path(
    filename: str,
) -> Path:
    """Return the absolute path to an image resource."""
    return get_resource_path(
        "images",
        filename,
    )