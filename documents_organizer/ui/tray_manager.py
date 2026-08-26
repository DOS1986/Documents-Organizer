from __future__ import annotations

import threading
from collections.abc import Callable

import pystray
from PIL import Image
from pystray import MenuItem as TrayMenuItem

from documents_organizer.resources import get_image_path
from documents_organizer.settings import (
    APP_NAME,
    TRAY_ICON_FILE,
    TRAY_ICON_NAME,
)


class TrayManager:
    """Manage the application's system tray icon."""

    def __init__(
        self,
        *,
        on_show_requested: Callable[[], None],
        on_exit_requested: Callable[[], None],
    ) -> None:
        self._on_show_requested = (
            on_show_requested
        )

        self._on_exit_requested = (
            on_exit_requested
        )

        self._icon: pystray.Icon | None = None

    @property
    def is_running(self) -> bool:
        """Return whether the tray icon is active."""
        return self._icon is not None

    def start(self) -> None:
        """Create and start the system tray icon."""
        if self._icon is not None:
            return

        with Image.open(
            get_image_path(
                TRAY_ICON_FILE
            )
        ) as source_image:
            image = source_image.copy()

        tray_menu = (
            TrayMenuItem(
                "Show",
                self._handle_show,
            ),
            TrayMenuItem(
                "Quit",
                self._handle_exit,
            ),
        )

        self._icon = pystray.Icon(
            TRAY_ICON_NAME,
            image,
            APP_NAME,
            tray_menu,
        )

        threading.Thread(
            target=self._icon.run,
            daemon=True,
            name="documents-organizer-tray",
        ).start()

    def stop(self) -> None:
        """Stop and remove the tray icon."""
        icon = self._icon

        if icon is None:
            return

        self._icon = None

        icon.stop()

    def _handle_show(
        self,
        icon: pystray.Icon,
        menu_item: object,
    ) -> None:
        """Handle a tray Show request."""
        self.stop()

        self._on_show_requested()

    def _handle_exit(
        self,
        icon: pystray.Icon,
        menu_item: object,
    ) -> None:
        """Handle a tray Quit request."""
        self.stop()

        self._on_exit_requested()