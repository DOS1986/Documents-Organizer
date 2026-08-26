from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
import tkinter.scrolledtext as scrolledtext
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
from documents_organizer.ui.dialogs import (
    ask_confirmation,
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
        self.tray_icon: pystray.Icon | None = None

        # Worker threads communicate with Tkinter through this queue.
        # Tkinter itself is only updated from the main thread.
        self.ui_queue: queue.Queue[
            tuple[str, object]
        ] = queue.Queue()

        self._configure_window()
        self._create_menu_bar()
        self._create_layout()
        self._bind_events()

        self._log_startup_message()

        # Start polling for messages from background workers.
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

    def _bind_events(self) -> None:
        """Bind application-level window events."""
        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.hide_window,
        )

    # -------------------------------------------------------------------------
    # Menus
    # -------------------------------------------------------------------------

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menu_bar = tk.Menu(
            self.root
        )

        self.root.config(
            menu=menu_bar
        )

        # File
        file_menu = tk.Menu(
            menu_bar,
            tearoff=0,
        )

        file_menu.add_command(
            label="Select Folder",
            command=self.select_folder,
        )

        file_menu.add_separator()

        file_menu.add_command(
            label="Exit",
            command=self.exit_app,
        )

        menu_bar.add_cascade(
            label="File",
            menu=file_menu,
        )

        # Actions
        action_menu = tk.Menu(
            menu_bar,
            tearoff=0,
        )

        organize_menu = tk.Menu(
            action_menu,
            tearoff=0,
        )

        organize_menu.add_command(
            label="Organize Files",
            command=self.run_organizer,
        )

        organize_menu.add_command(
            label="Flatten Files",
            command=self.run_flattener,
        )

        organize_menu.add_separator()

        organize_menu.add_command(
            label="Cancel Flatten Operation",
            command=self.stop_flattening,
        )

        action_menu.add_cascade(
            label="Organize",
            menu=organize_menu,
        )

        view_menu = tk.Menu(
            action_menu,
            tearoff=0,
        )

        view_menu.add_command(
            label="Clear Log",
            command=self.clear_log,
        )

        view_menu.add_command(
            label="Refresh Folder Tree",
            command=self.refresh_treeview,
        )

        action_menu.add_cascade(
            label="View",
            menu=view_menu,
        )

        menu_bar.add_cascade(
            label="Action",
            menu=action_menu,
        )

        # Help
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
        self.main_frame = ttk.Frame(
            self.root
        )

        self.main_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self.paned_window = ttk.PanedWindow(
            self.main_frame,
            orient=tk.HORIZONTAL,
        )

        self.paned_window.pack(
            fill=tk.BOTH,
            expand=True,
            padx=8,
            pady=8,
        )

        self._create_tree_panel()
        self._create_log_panel()

    def _create_tree_panel(self) -> None:
        """Create the directory tree panel."""
        tree_frame = ttk.Frame(
            self.paned_window
        )

        self.paned_window.add(
            tree_frame,
            weight=1,
        )

        self.tree = ttk.Treeview(
            tree_frame
        )

        tree_scrollbar = ttk.Scrollbar(
            tree_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview,
        )

        self.tree.configure(
            yscrollcommand=tree_scrollbar.set
        )

        self.tree.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )

        tree_scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y,
        )

        self.tree.bind(
            "<Button-3>",
            self.popup_menu,
        )

    def _create_log_panel(self) -> None:
        """Create the activity log panel."""
        log_frame = ttk.Frame(
            self.paned_window
        )

        self.paned_window.add(
            log_frame,
            weight=1,
        )

        self.log_text = (
            scrolledtext.ScrolledText(
                log_frame,
                wrap=tk.WORD,
                state=tk.DISABLED,
            )
        )

        self.log_text.pack(
            fill=tk.BOTH,
            expand=True,
        )

    # -------------------------------------------------------------------------
    # Folder selection and tree
    # -------------------------------------------------------------------------

    def select_folder(self) -> None:
        """Allow the user to select a directory."""
        selected_folder = (
            filedialog.askdirectory()
        )

        if not selected_folder:
            return

        self.folder_path = Path(
            selected_folder
        ).resolve()

        self.update_treeview(
            self.folder_path
        )

        self.log_to_text(
            f"Selected folder: "
            f"{self.folder_path}"
        )

    def update_treeview(
        self,
        directory: Path | str,
    ) -> None:
        """Update the folder tree with a directory structure."""
        self.tree.delete(
            *self.tree.get_children()
        )

        self.populate_tree(
            Path(directory)
        )

    def populate_tree(
        self,
        directory: Path,
    ) -> None:
        """Populate the root folder in the Treeview."""
        root_node = self.tree.insert(
            "",
            "end",
            text=str(directory),
        )

        self.populate_children(
            root_node,
            directory,
        )

    def populate_children(
        self,
        parent: str,
        directory: Path,
    ) -> None:
        """Populate subdirectories beneath a Treeview node."""
        try:
            items = sorted(
                directory.iterdir(),
                key=lambda path: path.name.lower(),
            )

        except (
            PermissionError,
            FileNotFoundError,
            OSError,
        ):
            return

        for item_path in items:
            if not item_path.is_dir():
                continue

            node = self.tree.insert(
                parent,
                "end",
                text=item_path.name,
            )

            self.populate_children(
                node,
                item_path,
            )

    def refresh_treeview(self) -> None:
        """Refresh the displayed directory tree."""
        if self.folder_path is None:
            return

        if not self.folder_path.is_dir():
            return

        self.update_treeview(
            self.folder_path
        )

    def get_selected_folder(
        self,
    ) -> Path | None:
        """Return the full path for the currently selected tree item."""
        selected_items = (
            self.tree.selection()
        )

        if not selected_items:
            focused_item = (
                self.tree.focus()
            )

            if not focused_item:
                return None

            selected_item = focused_item

        else:
            selected_item = (
                selected_items[0]
            )

        return self.get_full_path(
            selected_item
        )

    def get_full_path(
        self,
        item: str,
    ) -> Path:
        """Build the filesystem path represented by a Treeview item."""
        path_components = [
            self.tree.item(item)["text"]
        ]

        parent = self.tree.parent(
            item
        )

        while parent:
            path_components.insert(
                0,
                self.tree.item(parent)["text"],
            )

            parent = self.tree.parent(
                parent
            )

        return Path(
            os.path.join(
                *path_components
            )
        ).resolve()

    # -------------------------------------------------------------------------
    # Organizer
    # -------------------------------------------------------------------------

    def run_organizer(self) -> None:
        """Start an organize operation for the selected folder."""
        selected_folder = (
            self.get_selected_folder()
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
                "The selected folder does not exist.",
            )
            return

        if not self._begin_operation(
            "organize"
        ):
            return

        self.log_to_text(
            f"Organizing: {selected_folder}"
        )

        worker = threading.Thread(
            target=self._run_organizer_worker,
            args=(selected_folder,),
            daemon=True,
        )

        worker.start()

    def _run_organizer_worker(
        self,
        selected_folder: Path,
    ) -> None:
        """Run the organizer service on a background thread."""
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

        self.current_operation = None

        self.refresh_treeview()

    def _handle_organization_error(
        self,
        message: str,
    ) -> None:
        """Display a fatal organizer error."""
        self.current_operation = None

        self.log_to_text(
            f"Organization failed: "
            f"{message}"
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
            self.get_selected_folder()
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
                "The selected folder does not exist.",
            )
            return

        if not self._begin_operation(
            "flatten"
        ):
            return

        self.flatten_cancel_event.clear()

        self.log_to_text(
            f"Flattening: {selected_folder}"
        )

        worker = threading.Thread(
            target=self._run_flattener_worker,
            args=(selected_folder,),
            daemon=True,
        )

        worker.start()

    def _run_flattener_worker(
        self,
        selected_folder: Path,
    ) -> None:
        """Run the flattener service on a background thread."""
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

        else:
            self.log_to_text(
                f"Flattening complete. "
                f"{result.moved} files moved "
                f"and "
                f"{result.directories_removed} "
                f"empty folders removed."
            )

        self.current_operation = None

        self.refresh_treeview()

    def _handle_flatten_error(
        self,
        message: str,
    ) -> None:
        """Display a fatal flattener error."""
        self.current_operation = None

        self.log_to_text(
            f"Flattening failed: "
            f"{message}"
        )

        show_error(
            self.root,
            "Flattening Failed",
            message,
        )

    def stop_flattening(self) -> None:
        """Request cancellation of the active flatten operation."""
        if self.current_operation != "flatten":
            self.log_to_text(
                "No flatten operation is currently running."
            )
            return

        if self.flatten_cancel_event.is_set():
            return

        self.flatten_cancel_event.set()

        self.log_to_text(
            "Cancel requested..."
        )

    # -------------------------------------------------------------------------
    # Operation state
    # -------------------------------------------------------------------------

    def _begin_operation(
        self,
        operation: str,
    ) -> bool:
        """Prevent conflicting filesystem operations from running together."""
        if self.current_operation is not None:
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

        return True

    # -------------------------------------------------------------------------
    # Worker → UI communication
    # -------------------------------------------------------------------------

    def _process_ui_queue(self) -> None:
        """
        Process messages from worker threads.

        This method runs on the Tkinter main thread so worker threads never
        directly modify Tkinter widgets.
        """
        try:
            while True:
                event_name, payload = (
                    self.ui_queue.get_nowait()
                )

                if (
                    event_name
                    == "organization_result"
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
                    self.root.destroy()

                    return

        except queue.Empty:
            pass

        self.root.after(
            UI_QUEUE_POLL_INTERVAL_MS,
            self._process_ui_queue,
        )

    # -------------------------------------------------------------------------
    # Activity log
    # -------------------------------------------------------------------------

    def _log_startup_message(self) -> None:
        """Display initial application information."""
        self.log_to_text(
            f"{APP_NAME} v{__version__}"
        )

        self.log_to_text(
            "Ready."
        )

    def log_to_text(
        self,
        message: str,
    ) -> None:
        """Append a message to the activity log."""
        self.log_text.config(
            state=tk.NORMAL
        )

        self.log_text.insert(
            tk.END,
            message + "\n",
        )

        self.log_text.config(
            state=tk.DISABLED
        )

        self.log_text.see(
            tk.END
        )

    def clear_log(self) -> None:
        """Clear the activity log."""
        self.log_text.config(
            state=tk.NORMAL
        )

        self.log_text.delete(
            "1.0",
            tk.END,
        )

        self.log_text.config(
            state=tk.DISABLED
        )

        self._log_startup_message()

    # -------------------------------------------------------------------------
    # File manager context menu
    # -------------------------------------------------------------------------

    def popup_menu(
        self,
        event: tk.Event,
    ) -> None:
        """Display the folder context menu."""
        selected_item = (
            self.tree.identify_row(
                event.y
            )
        )

        if not selected_item:
            return

        self.tree.selection_set(
            selected_item
        )

        self.tree.focus(
            selected_item
        )

        popup = tk.Menu(
            self.root,
            tearoff=0,
        )

        popup.add_command(
            label="Open in File Manager",
            command=self.open_selected_folder,
        )

        popup.post(
            event.x_root,
            event.y_root,
        )

    def open_selected_folder(self) -> None:
        """Open the selected folder using the platform file manager."""
        selected_folder = (
            self.get_selected_folder()
        )

        if selected_folder is None:
            show_error(
                self.root,
                "No Folder Selected",
                "Please select a folder first.",
            )
            return

        try:
            open_in_file_manager(
                selected_folder
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
        """Hide the main window and create a system tray icon."""
        self.root.withdraw()

        if self.tray_icon is not None:
            return

        try:
            image = Image.open(
                get_image_path(
                    TRAY_ICON_FILE
                )
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
                    "Documents Organizer could "
                    "not create the system tray "
                    f"icon.\n\n{exc}"
                )
            )

    def show_window(
        self,
        icon: pystray.Icon,
        menu_item: object,
    ) -> None:
        """Restore the main application window from the tray."""
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
        """Exit Documents Organizer from the system tray."""
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
        """Close the application."""
        if self.current_operation is not None:
            should_exit = ask_confirmation(
                self.root,
                "Operation in Progress",
                (
                    "A file operation is still "
                    "running.\n\n"
                    f"Are you sure you want to exit "
                    f"{APP_NAME}?"
                ),
            )

            if not should_exit:
                return

            if (
                    self.current_operation
                    == "flatten"
            ):
                self.flatten_cancel_event.set()

        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None

        self.root.destroy()