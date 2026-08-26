from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


class MenuBar:
    """Application menu bar and menu state management."""

    def __init__(
        self,
        root: tk.Tk,
        *,
        on_select_folder: Callable[[], None],
        on_minimize_to_tray: Callable[[], None],
        on_exit: Callable[[], None],
        on_organize: Callable[[], None],
        on_flatten: Callable[[], None],
        on_cancel: Callable[[], None],
        on_clear_log: Callable[[], None],
        on_refresh: Callable[[], None],
        on_about: Callable[[], None],
    ) -> None:
        self._root = root

        self._menu_bar = tk.Menu(
            root
        )

        self._root.config(
            menu=self._menu_bar
        )

        self._create_file_menu(
            on_select_folder=on_select_folder,
            on_minimize_to_tray=on_minimize_to_tray,
            on_exit=on_exit,
        )

        self._create_action_menu(
            on_organize=on_organize,
            on_flatten=on_flatten,
            on_cancel=on_cancel,
            on_clear_log=on_clear_log,
            on_refresh=on_refresh,
        )

        self._create_help_menu(
            on_about=on_about,
        )

    # -------------------------------------------------------------------------
    # Menu construction
    # -------------------------------------------------------------------------

    def _create_file_menu(
        self,
        *,
        on_select_folder: Callable[[], None],
        on_minimize_to_tray: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        """Create the File menu."""
        self._file_menu = tk.Menu(
            self._menu_bar,
            tearoff=0,
        )

        self._file_menu.add_command(
            label="Select Folder",
            command=on_select_folder,
        )

        self._file_menu.add_separator()

        self._file_menu.add_command(
            label="Minimize to Tray",
            command=on_minimize_to_tray,
        )

        self._file_menu.add_separator()

        self._file_menu.add_command(
            label="Exit",
            command=on_exit,
        )

        self._menu_bar.add_cascade(
            label="File",
            menu=self._file_menu,
        )

    def _create_action_menu(
        self,
        *,
        on_organize: Callable[[], None],
        on_flatten: Callable[[], None],
        on_cancel: Callable[[], None],
        on_clear_log: Callable[[], None],
        on_refresh: Callable[[], None],
    ) -> None:
        """Create the Action menu."""
        action_menu = tk.Menu(
            self._menu_bar,
            tearoff=0,
        )

        self._organize_menu = tk.Menu(
            action_menu,
            tearoff=0,
        )

        self._organize_menu.add_command(
            label="Organize Files",
            command=on_organize,
        )

        self._organize_menu.add_command(
            label="Flatten Files",
            command=on_flatten,
        )

        self._organize_menu.add_separator()

        self._organize_menu.add_command(
            label="Cancel Flatten Operation",
            command=on_cancel,
        )

        action_menu.add_cascade(
            label="Organize",
            menu=self._organize_menu,
        )

        self._view_menu = tk.Menu(
            action_menu,
            tearoff=0,
        )

        self._view_menu.add_command(
            label="Clear Activity Log",
            command=on_clear_log,
        )

        self._view_menu.add_command(
            label="Refresh Folder Tree",
            command=on_refresh,
        )

        action_menu.add_cascade(
            label="View",
            menu=self._view_menu,
        )

        self._menu_bar.add_cascade(
            label="Action",
            menu=action_menu,
        )

    def _create_help_menu(
        self,
        *,
        on_about: Callable[[], None],
    ) -> None:
        """Create the Help menu."""
        help_menu = tk.Menu(
            self._menu_bar,
            tearoff=0,
        )

        help_menu.add_command(
            label="About",
            command=on_about,
        )

        self._menu_bar.add_cascade(
            label="Help",
            menu=help_menu,
        )

    # -------------------------------------------------------------------------
    # State
    # -------------------------------------------------------------------------

    def set_states(
        self,
        *,
        select_enabled: bool,
        operations_enabled: bool,
        cancel_enabled: bool,
        utilities_enabled: bool,
    ) -> None:
        """Update menu command states."""
        self._file_menu.entryconfig(
            0,
            state=self._state(
                select_enabled
            ),
        )

        self._organize_menu.entryconfig(
            0,
            state=self._state(
                operations_enabled
            ),
        )

        self._organize_menu.entryconfig(
            1,
            state=self._state(
                operations_enabled
            ),
        )

        self._organize_menu.entryconfig(
            3,
            state=self._state(
                cancel_enabled
            ),
        )

        self._view_menu.entryconfig(
            1,
            state=self._state(
                utilities_enabled
            ),
        )

    @staticmethod
    def _state(
        enabled: bool,
    ) -> str:
        """Convert a boolean to a Tkinter menu state."""
        return (
            tk.NORMAL
            if enabled
            else tk.DISABLED
        )