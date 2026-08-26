from __future__ import annotations


import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

import pystray
from PIL import Image
from pystray import MenuItem as TrayMenuItem

from documents_organizer import __version__
from documents_organizer.platform_utils import open_in_file_manager
from documents_organizer.resources import get_image_path
from documents_organizer.services.flattener import (
    FlattenResult,
    flatten_directory,
)
from documents_organizer.services.organizer import (
    OrganizationResult,
    organize_directory,
)
from documents_organizer.settings import (
    APP_NAME,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    TRAY_ICON_FILE,
    TRAY_ICON_NAME,
    UI_QUEUE_POLL_INTERVAL_MS,
    WINDOW_ICON_FILE,
)
from documents_organizer.ui.components.activity_log import ActivityLog
from documents_organizer.ui.components.folder_browser import FolderBrowser
from documents_organizer.ui.components.folder_summary import FolderSummary
from documents_organizer.ui.components.status_bar import StatusBar
from documents_organizer.ui.components.toolbar import Toolbar
from documents_organizer.ui.dialogs import (
    show_about as show_about_dialog,
    show_error,
    show_warning,
)


class MainWindow:
    """Main Documents Organizer application window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root

        self.folder_path: Path | None = None
        self.flatten_cancel_event = threading.Event()
        self.current_operation: str | None = None
        self.is_closing = False
        self.tray_icon: pystray.Icon | None = None

        # Worker threads communicate with Tkinter through this queue.
        self.ui_queue: queue.Queue[
            tuple[str, object]
        ] = queue.Queue()

        # UI state.

        self._configure_window()
        self._configure_styles()
        self._create_menu_bar()
        self._create_layout()
        self._bind_events()

        self._log_startup_message()
        self._update_action_states()

        self.root.after(
            UI_QUEUE_POLL_INTERVAL_MS,
            self._process_ui_queue,
        )

    # -------------------------------------------------------------------------
    # Window setup
    # -------------------------------------------------------------------------

    def _configure_window(self) -> None:
        """Configure the root application window."""
        self.root.title(
            APP_NAME
        )

        self.root.geometry(
            f"{DEFAULT_WINDOW_WIDTH}x"
            f"{DEFAULT_WINDOW_HEIGHT}"
        )

        self.root.minsize(
            MIN_WINDOW_WIDTH,
            MIN_WINDOW_HEIGHT,
        )

        try:
            self.root.iconbitmap(
                str(
                    get_image_path(
                        WINDOW_ICON_FILE
                    )
                )
            )

        except (
            tk.TclError,
            OSError,
        ):
            pass

    def _configure_styles(self) -> None:
        """Configure ttk styles used by the application."""
        style = ttk.Style(
            self.root
        )

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

    def _bind_events(self) -> None:
        """Bind application-level events."""
        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.exit_app,
        )

    # -------------------------------------------------------------------------
    # Menu bar
    # -------------------------------------------------------------------------

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menu_bar = tk.Menu(
            self.root
        )

        self.root.config(
            menu=menu_bar
        )

        # File menu
        self.file_menu = tk.Menu(
            menu_bar,
            tearoff=0,
        )

        self.file_menu.add_command(
            label="Select Folder",
            command=self.select_folder,
        )

        self.file_menu.add_separator()

        self.file_menu.add_command(
            label="Minimize to Tray",
            command=self.hide_window,
        )

        self.file_menu.add_separator()

        self.file_menu.add_command(
            label="Exit",
            command=self.exit_app,
        )

        menu_bar.add_cascade(
            label="File",
            menu=self.file_menu,
        )

        # Action menu
        action_menu = tk.Menu(
            menu_bar,
            tearoff=0,
        )

        self.organize_menu = tk.Menu(
            action_menu,
            tearoff=0,
        )

        self.organize_menu.add_command(
            label="Organize Files",
            command=self.run_organizer,
        )

        self.organize_menu.add_command(
            label="Flatten Files",
            command=self.run_flattener,
        )

        self.organize_menu.add_separator()

        self.organize_menu.add_command(
            label="Cancel Flatten Operation",
            command=self.stop_flattening,
        )

        action_menu.add_cascade(
            label="Organize",
            menu=self.organize_menu,
        )

        self.view_menu = tk.Menu(
            action_menu,
            tearoff=0,
        )

        self.view_menu.add_command(
            label="Clear Activity Log",
            command=self.clear_log,
        )

        self.view_menu.add_command(
            label="Refresh Folder Tree",
            command=self.refresh_treeview,
        )

        action_menu.add_cascade(
            label="View",
            menu=self.view_menu,
        )

        menu_bar.add_cascade(
            label="Action",
            menu=action_menu,
        )

        # Help menu
        help_menu = tk.Menu(
            menu_bar,
            tearoff=0,
        )

        help_menu.add_command(
            label="About",
            command=self.show_about,
        )

        menu_bar.add_cascade(
            label="Help",
            menu=help_menu,
        )

    # -------------------------------------------------------------------------
    # Main layout
    # -------------------------------------------------------------------------

    def _create_layout(self) -> None:
        """Create the primary application layout."""
        self.root.rowconfigure(
            0,
            weight=1,
        )

        self.root.columnconfigure(
            0,
            weight=1,
        )

        self.main_frame = ttk.Frame(
            self.root,
            padding=(
                16,
                14,
            ),
        )

        self.main_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.main_frame.columnconfigure(
            0,
            weight=1,
        )

        self.main_frame.rowconfigure(
            3,
            weight=1,
        )

        self._create_header()
        self._create_toolbar()
        self._create_folder_summary()
        self._create_workspace()
        self._create_status_bar()

    def _create_header(self) -> None:
        """Create the application header."""
        header = ttk.Frame(
            self.main_frame
        )

        header.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(
                0,
                12,
            ),
        )

        header.columnconfigure(
            0,
            weight=1,
        )

        title = ttk.Label(
            header,
            text=APP_NAME,
            style="AppTitle.TLabel",
        )

        title.grid(
            row=0,
            column=0,
            sticky="w",
        )

        subtitle = ttk.Label(
            header,
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

    def _create_toolbar(self) -> None:
        """Create the main action toolbar."""
        self.toolbar = Toolbar(
            self.main_frame,
            on_select_folder=self.select_folder,
            on_organize=self.run_organizer,
            on_flatten=self.run_flattener,
            on_cancel=self.stop_flattening,
            on_open_selected=self.open_selected_folder,
            on_refresh=self.refresh_treeview,
            on_clear_log=self.clear_log,
        )

        self.toolbar.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(
                0,
                12,
            ),
        )

    def _create_folder_summary(self) -> None:
        """Create the selected-location summary."""
        self.folder_summary = FolderSummary(
            self.main_frame
        )

        self.folder_summary.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(
                0,
                12,
            ),
        )

    def _create_folder_browser(self) -> None:
        """Create the folder browser component."""
        self.folder_browser = FolderBrowser(
            self.paned_window,
            on_selection_changed=(
                self._on_folder_selection_changed
            ),
            on_open_selected=(
                self._open_folder_path
            ),
        )

        self.paned_window.add(
            self.folder_browser,
            weight=2,
        )

    def _create_workspace(self) -> None:
        """Create the main folder-browser/activity workspace."""
        self.paned_window = ttk.PanedWindow(
            self.main_frame,
            orient=tk.HORIZONTAL,
        )

        self.paned_window.grid(
            row=3,
            column=0,
            sticky="nsew",
        )

        self._create_folder_browser()
        self._create_log_panel()

    def _create_log_panel(self) -> None:
        """Create the activity log panel."""
        self.activity_log = ActivityLog(
            self.paned_window
        )

        self.paned_window.add(
            self.activity_log,
            weight=3,
        )

    def _create_status_bar(self) -> None:
        """Create the bottom application status area."""
        separator = ttk.Separator(
            self.main_frame,
            orient=tk.HORIZONTAL,
        )

        separator.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(
                12,
                6,
            ),
        )

        self.status_bar = StatusBar(
            self.main_frame
        )

        self.status_bar.grid(
            row=5,
            column=0,
            sticky="ew",
        )

    # -------------------------------------------------------------------------
    # Folder selection and browser
    # -------------------------------------------------------------------------

    def select_folder(self) -> None:
        """Allow the user to select a root directory."""
        if self.current_operation is not None:
            show_warning(
                self.root,
                "Operation in Progress",
                (
                    "Please wait for the current "
                    "file operation to finish."
                ),
            )
            return

        selected_folder = filedialog.askdirectory(
            title="Select Folder",
        )

        if not selected_folder:
            return

        folder = Path(
            selected_folder
        ).resolve()

        try:
            self.folder_browser.load(
                folder
            )

        except (
                FileNotFoundError,
                NotADirectoryError,
                PermissionError,
                OSError,
        ) as exc:
            show_error(
                self.root,
                "Unable to Open Folder",
                str(exc),
            )
            return

        self.folder_path = folder

        self.folder_summary.set_root(
            folder
        )

        self.log_to_text(
            f"Selected folder: {folder}"
        )

        self.set_status(
            "Folder selected."
        )

        self._update_action_states()

    def refresh_treeview(self) -> None:
        """Refresh the displayed folder tree."""
        if self.folder_path is None:
            return

        try:
            self.folder_browser.refresh()

        except (
                FileNotFoundError,
                NotADirectoryError,
                PermissionError,
                OSError,
        ) as exc:
            show_error(
                self.root,
                "Folder Unavailable",
                str(exc),
            )
            return

        self.set_status(
            "Folder tree refreshed."
        )

    def _on_folder_selection_changed(
            self,
            selected_folder: Path | None,
    ) -> None:
        """Handle changes to the folder browser selection."""
        if selected_folder is None:
            self.folder_summary.clear_target()

        else:
            self.folder_summary.set_target(
                selected_folder
            )

        self._update_action_states()

    # -------------------------------------------------------------------------
    # Organizer
    # -------------------------------------------------------------------------

    def run_organizer(self) -> None:
        """Start an organize operation for the selected folder."""
        selected_folder = (
            self.folder_browser.selected_path
        )

        if selected_folder is None:
            show_error(
                self.root,
                "No Folder Selected",
                "Please select a folder first.",
            )
            return

        if not selected_folder.is_dir():
            show_error(
                self.root,
                "Invalid Folder",
                (
                    "The selected folder does "
                    "not exist."
                ),
            )
            return

        if not self._begin_operation(
            "organize"
        ):
            return

        self.log_to_text(
            f"Organizing: "
            f"{selected_folder}"
        )

        worker = threading.Thread(
            target=self._run_organizer_worker,
            args=(
                selected_folder,
            ),
            daemon=True,
        )

        worker.start()

    def _run_organizer_worker(
        self,
        selected_folder: Path,
    ) -> None:
        """Run the organizer service on a worker thread."""
        try:
            result = organize_directory(
                selected_folder
            )

        except (
            FileNotFoundError,
            NotADirectoryError,
            PermissionError,
            OSError,
        ) as exc:
            self.ui_queue.put(
                (
                    "organization_error",
                    str(exc),
                )
            )
            return

        self.ui_queue.put(
            (
                "organization_result",
                result,
            )
        )

    def _handle_organization_result(
        self,
        result: OrganizationResult,
    ) -> None:
        """Display organizer results."""
        for extension, count in sorted(
            result.by_extension.items()
        ):
            label = (
                "file"
                if count == 1
                else "files"
            )

            self.log_to_text(
                f"Organized {count} "
                f"{extension} {label}."
            )

        if result.skipped:
            label = (
                "file"
                if result.skipped == 1
                else "files"
            )

            self.log_to_text(
                f"Skipped "
                f"{result.skipped} {label}."
            )

        if result.failed:
            label = (
                "failure"
                if result.failed == 1
                else "failures"
            )

            self.log_to_text(
                f"Encountered "
                f"{result.failed} {label}."
            )

            for failure in result.failures:
                self.log_to_text(
                    f"  {failure.path}: "
                    f"{failure.error}"
                )

        self.log_to_text(
            f"Organization complete. "
            f"{result.moved} files moved."
        )

        self.refresh_treeview()

        self._finish_operation(
            (
                "Organization complete — "
                f"{result.moved} files moved."
            )
        )

    def _handle_organization_error(
        self,
        message: str,
    ) -> None:
        """Display a fatal organizer error."""
        self.log_to_text(
            f"Organization failed: "
            f"{message}"
        )

        self._finish_operation(
            "Organization failed."
        )

        show_error(
            self.root,
            "Organization Failed",
            message,
        )

    # -------------------------------------------------------------------------
    # Flattener
    # -------------------------------------------------------------------------

    def run_flattener(self) -> None:
        """Start a flatten operation for the selected folder."""
        selected_folder = (
            self.folder_browser.selected_path
        )

        if selected_folder is None:
            show_error(
                self.root,
                "No Folder Selected",
                "Please select a folder first.",
            )
            return

        if not selected_folder.is_dir():
            show_error(
                self.root,
                "Invalid Folder",
                (
                    "The selected folder does "
                    "not exist."
                ),
            )
            return

        if not self._begin_operation(
            "flatten"
        ):
            return

        self.flatten_cancel_event.clear()

        self.log_to_text(
            f"Flattening: "
            f"{selected_folder}"
        )

        worker = threading.Thread(
            target=self._run_flattener_worker,
            args=(
                selected_folder,
            ),
            daemon=True,
        )

        worker.start()

    def _run_flattener_worker(
        self,
        selected_folder: Path,
    ) -> None:
        """Run the flattener service on a worker thread."""
        try:
            result = flatten_directory(
                selected_folder,
                cancel_event=(
                    self.flatten_cancel_event
                ),
            )

        except (
            FileNotFoundError,
            NotADirectoryError,
            PermissionError,
            OSError,
        ) as exc:
            self.ui_queue.put(
                (
                    "flatten_error",
                    str(exc),
                )
            )
            return

        self.ui_queue.put(
            (
                "flatten_result",
                result,
            )
        )

    def _handle_flatten_result(
        self,
        result: FlattenResult,
    ) -> None:
        """Display flattener results."""
        for extension, count in sorted(
            result.by_extension.items()
        ):
            label = (
                "file"
                if count == 1
                else "files"
            )

            self.log_to_text(
                f"Flattened {count} "
                f"{extension} {label}."
            )

        if result.skipped:
            label = (
                "file"
                if result.skipped == 1
                else "files"
            )

            self.log_to_text(
                f"Skipped "
                f"{result.skipped} {label} "
                "that did not match their "
                "file-type folder."
            )

        if result.failed:
            label = (
                "failure"
                if result.failed == 1
                else "failures"
            )

            self.log_to_text(
                f"Encountered "
                f"{result.failed} {label}."
            )

            for failure in result.failures:
                self.log_to_text(
                    f"  {failure.path}: "
                    f"{failure.error}"
                )

        if result.cancelled:
            self.log_to_text(
                "Flattening canceled."
            )

            status = "Flattening canceled."

        else:
            self.log_to_text(
                f"Flattening complete. "
                f"{result.moved} files moved "
                f"and "
                f"{result.directories_removed} "
                f"empty folders removed."
            )

            status = (
                "Flattening complete — "
                f"{result.moved} files moved."
            )

        self.refresh_treeview()

        self._finish_operation(
            status
        )

    def _handle_flatten_error(
        self,
        message: str,
    ) -> None:
        """Display a fatal flattener error."""
        self.log_to_text(
            f"Flattening failed: "
            f"{message}"
        )

        self._finish_operation(
            "Flattening failed."
        )

        show_error(
            self.root,
            "Flattening Failed",
            message,
        )

    def stop_flattening(self) -> None:
        """Request cancellation of an active flatten operation."""
        if (
            self.current_operation
            != "flatten"
        ):
            return

        if (
            self.flatten_cancel_event.is_set()
        ):
            return

        self.flatten_cancel_event.set()

        self.log_to_text(
            "Cancel requested..."
        )

        self.set_status(
            "Canceling flatten operation..."
        )

        self._update_action_states()

    # -------------------------------------------------------------------------
    # Operation state
    # -------------------------------------------------------------------------

    def _begin_operation(
        self,
        operation: str,
    ) -> bool:
        """Start an application file operation."""
        if (
            self.current_operation
            is not None
        ):
            show_warning(
                self.root,
                "Operation in Progress",
                (
                    "Another file operation is "
                    "already running. Please wait "
                    "for it to finish."
                ),
            )
            return False

        self.current_operation = (
            operation
        )

        if operation == "organize":
            self.set_status(
                "Organizing files..."
            )

        elif operation == "flatten":
            self.set_status(
                "Flattening files..."
            )

        self.status_bar.start_progress()

        self._update_action_states()

        return True

    def _finish_operation(
        self,
        status: str,
    ) -> None:
        """Finish the active application file operation."""
        self.current_operation = None

        self.status_bar.stop_progress()

        self.set_status(
            status
        )

        self._update_action_states()

    def _update_action_states(self) -> None:
        """Enable or disable commands based on application state."""
        root_available = (
                self.folder_path is not None
                and self.folder_path.is_dir()
        )

        selected_folder = (
            self.folder_browser.selected_path
        )

        target_available = (
                selected_folder is not None
                and selected_folder.is_dir()
        )

        busy = (
                self.current_operation
                is not None
        )

        flattening = (
                self.current_operation
                == "flatten"
        )

        cancel_available = (
                flattening
                and not self.flatten_cancel_event.is_set()
        )

        select_enabled = (
            not busy
        )

        operations_enabled = (
                target_available
                and not busy
        )

        utilities_enabled = (
                target_available
                and root_available
                and not busy
        )

        self.toolbar.set_states(
            select_enabled=select_enabled,
            operations_enabled=operations_enabled,
            cancel_enabled=cancel_available,
            utilities_enabled=utilities_enabled,
        )

        self._update_menu_states(
            select_enabled=select_enabled,
            operations_enabled=operations_enabled,
            cancel_enabled=cancel_available,
            utilities_enabled=utilities_enabled,
        )

    def _update_menu_states(
            self,
            *,
            select_enabled: bool,
            operations_enabled: bool,
            cancel_enabled: bool,
            utilities_enabled: bool,
    ) -> None:
        """Update menu item states."""
        self.file_menu.entryconfig(
            0,
            state=self._menu_state(
                select_enabled
            ),
        )

        self.organize_menu.entryconfig(
            0,
            state=self._menu_state(
                operations_enabled
            ),
        )

        self.organize_menu.entryconfig(
            1,
            state=self._menu_state(
                operations_enabled
            ),
        )

        self.organize_menu.entryconfig(
            3,
            state=self._menu_state(
                cancel_enabled
            ),
        )

        self.view_menu.entryconfig(
            1,
            state=self._menu_state(
                utilities_enabled
            ),
        )

    @staticmethod
    def _menu_state(
            enabled: bool,
    ) -> str:
        """Convert a boolean to a Tkinter menu state."""
        return (
            tk.NORMAL
            if enabled
            else tk.DISABLED
        )

    # -------------------------------------------------------------------------
    # Worker → UI communication
    # -------------------------------------------------------------------------

    def _process_ui_queue(self) -> None:
        """
        Process messages from worker threads.

        Only the Tkinter main thread updates widgets.
        """
        try:
            while True:
                event_name, payload = (
                    self.ui_queue.get_nowait()
                )

                if (
                    event_name
                    == "organization_result"
                    and isinstance(
                        payload,
                        OrganizationResult,
                    )
                ):
                    self._handle_organization_result(
                        payload
                    )

                elif (
                    event_name
                    == "organization_error"
                ):
                    self._handle_organization_error(
                        str(payload)
                    )

                elif (
                    event_name
                    == "flatten_result"
                    and isinstance(
                        payload,
                        FlattenResult,
                    )
                ):
                    self._handle_flatten_result(
                        payload
                    )

                elif (
                    event_name
                    == "flatten_error"
                ):
                    self._handle_flatten_error(
                        str(payload)
                    )

                elif (
                    event_name
                    == "show_window"
                ):
                    self.root.deiconify()
                    self.root.lift()
                    self.root.focus_force()

                elif (
                    event_name
                    == "exit_application"
                ):
                    self.root.deiconify()
                    self.root.lift()

                    self.exit_app()

        except queue.Empty:
            pass

        if not self.is_closing:
            self.root.after(
                UI_QUEUE_POLL_INTERVAL_MS,
                self._process_ui_queue,
            )

    # -------------------------------------------------------------------------
    # Status and activity log
    # -------------------------------------------------------------------------

    def set_status(
            self,
            message: str,
    ) -> None:
        """Update the application status message."""
        self.status_bar.set_status(
            message
        )

    def _log_startup_message(self) -> None:
        """Display initial application information."""
        self.log_to_text(
            f"{APP_NAME} v{__version__} started."
        )

        self.log_to_text(
            "Select a folder to begin."
        )

    def log_to_text(
            self,
            message: str,
    ) -> None:
        """Write a message to the activity log."""
        self.activity_log.write(
            message
        )

    def clear_log(self) -> None:
        """Clear the activity log."""
        self.activity_log.clear()

        self.activity_log.write(
            "Activity log cleared."
        )

    # -------------------------------------------------------------------------
    # File manager
    # -------------------------------------------------------------------------

    def open_selected_folder(self) -> None:
        """Open the selected folder in the platform file manager."""
        selected_folder = (
            self.folder_browser.selected_path
        )

        if selected_folder is None:
            show_error(
                self.root,
                "No Folder Selected",
                "Please select a folder first.",
            )
            return

        self._open_folder_path(
            selected_folder
        )

    def _open_folder_path(
            self,
            folder: Path,
    ) -> None:
        """Open a folder using the platform file manager."""
        try:
            open_in_file_manager(
                folder
            )

        except (
                FileNotFoundError,
                NotADirectoryError,
                OSError,
        ) as exc:
            show_error(
                self.root,
                "Unable to Open Folder",
                str(exc),
            )

    # -------------------------------------------------------------------------
    # System tray
    # -------------------------------------------------------------------------

    def hide_window(self) -> None:
        """Hide the application in the system tray."""
        self.root.withdraw()

        if (
            self.tray_icon
            is not None
        ):
            return

        try:
            with Image.open(
                get_image_path(
                    TRAY_ICON_FILE
                )
            ) as source_image:
                image = (
                    source_image.copy()
                )

            tray_menu = (
                TrayMenuItem(
                    "Show",
                    self.show_window,
                ),
                TrayMenuItem(
                    "Quit",
                    self.exit_from_tray,
                ),
            )

            self.tray_icon = pystray.Icon(
                TRAY_ICON_NAME,
                image,
                APP_NAME,
                tray_menu,
            )

            threading.Thread(
                target=self.tray_icon.run,
                daemon=True,
            ).start()

        except Exception as exc:
            self.tray_icon = None

            self.root.deiconify()

            show_error(
                self.root,
                "System Tray Error",
                (
                    f"{APP_NAME} could not create "
                    "the system tray icon.\n\n"
                    f"{exc}"
                ),
            )

    def show_window(
        self,
        icon: pystray.Icon,
        menu_item: object,
    ) -> None:
        """Restore the application from the system tray."""
        icon.stop()

        self.tray_icon = None

        self.ui_queue.put(
            (
                "show_window",
                None,
            )
        )

    def exit_from_tray(
        self,
        icon: pystray.Icon,
        menu_item: object,
    ) -> None:
        """Request application exit from the system tray."""
        icon.stop()

        self.tray_icon = None

        self.ui_queue.put(
            (
                "exit_application",
                None,
            )
        )

    # -------------------------------------------------------------------------
    # Application commands
    # -------------------------------------------------------------------------

    def show_about(self) -> None:
        """Display application information."""
        show_about_dialog(
            self.root
        )

    def exit_app(self) -> None:
        """Close the application safely."""
        if self.current_operation is not None:
            show_warning(
                self.root,
                "Operation in Progress",
                (
                    "Files are currently being "
                    "processed.\n\n"
                    "Please allow the operation "
                    "to finish, or cancel the "
                    "flatten operation before "
                    f"exiting {APP_NAME}."
                ),
            )
            return

        self.is_closing = True

        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None

        self.root.destroy()