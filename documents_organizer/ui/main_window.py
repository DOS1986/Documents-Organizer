from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
import tkinter.scrolledtext as scrolledtext
from datetime import datetime
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
        self.root_folder_var = tk.StringVar(
            value="No folder selected"
        )

        self.target_folder_var = tk.StringVar(
            value="No folder selected"
        )

        self.status_var = tk.StringVar(
            value="Ready"
        )

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
        toolbar = ttk.Frame(
            self.main_frame
        )

        toolbar.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(
                0,
                12,
            ),
        )

        # Flexible space between file operations and utility actions.
        toolbar.columnconfigure(
            5,
            weight=1,
        )

        self.select_folder_button = ttk.Button(
            toolbar,
            text="Select Folder",
            command=self.select_folder,
            style="Primary.TButton",
        )

        self.select_folder_button.grid(
            row=0,
            column=0,
            padx=(
                0,
                6,
            ),
        )

        first_separator = ttk.Separator(
            toolbar,
            orient=tk.VERTICAL,
        )

        first_separator.grid(
            row=0,
            column=1,
            sticky="ns",
            padx=8,
        )

        self.organize_button = ttk.Button(
            toolbar,
            text="Organize",
            command=self.run_organizer,
            style="Toolbar.TButton",
        )

        self.organize_button.grid(
            row=0,
            column=2,
            padx=6,
        )

        self.flatten_button = ttk.Button(
            toolbar,
            text="Flatten",
            command=self.run_flattener,
            style="Toolbar.TButton",
        )

        self.flatten_button.grid(
            row=0,
            column=3,
            padx=6,
        )

        self.cancel_button = ttk.Button(
            toolbar,
            text="Cancel",
            command=self.stop_flattening,
            style="Toolbar.TButton",
        )

        self.cancel_button.grid(
            row=0,
            column=4,
            padx=6,
        )

        second_separator = ttk.Separator(
            toolbar,
            orient=tk.VERTICAL,
        )

        second_separator.grid(
            row=0,
            column=6,
            sticky="ns",
            padx=8,
        )

        self.open_folder_button = ttk.Button(
            toolbar,
            text="Open Selected",
            command=self.open_selected_folder,
            style="Toolbar.TButton",
        )

        self.open_folder_button.grid(
            row=0,
            column=7,
            padx=6,
        )

        self.refresh_button = ttk.Button(
            toolbar,
            text="Refresh",
            command=self.refresh_treeview,
            style="Toolbar.TButton",
        )

        self.refresh_button.grid(
            row=0,
            column=8,
            padx=6,
        )

        self.clear_log_button = ttk.Button(
            toolbar,
            text="Clear Log",
            command=self.clear_log,
            style="Toolbar.TButton",
        )

        self.clear_log_button.grid(
            row=0,
            column=9,
            padx=(
                6,
                0,
            ),
        )

    def _create_folder_summary(self) -> None:
        """Create the current-folder summary panel."""
        folder_frame = ttk.LabelFrame(
            self.main_frame,
            text="Selected Location",
            style="Section.TLabelframe",
        )

        folder_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(
                0,
                12,
            ),
        )

        folder_frame.columnconfigure(
            1,
            weight=1,
        )

        ttk.Label(
            folder_frame,
            text="Root Folder:",
        ).grid(
            row=0,
            column=0,
            sticky="nw",
            padx=(
                0,
                10,
            ),
            pady=2,
        )

        ttk.Label(
            folder_frame,
            textvariable=self.root_folder_var,
            style="PathLabel.TLabel",
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=2,
        )

        ttk.Label(
            folder_frame,
            text="Operation Target:",
        ).grid(
            row=1,
            column=0,
            sticky="nw",
            padx=(
                0,
                10,
            ),
            pady=2,
        )

        ttk.Label(
            folder_frame,
            textvariable=self.target_folder_var,
            style="PathLabel.TLabel",
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=2,
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

        self._create_tree_panel()
        self._create_log_panel()

    def _create_tree_panel(self) -> None:
        """Create the folder browser panel."""
        tree_frame = ttk.LabelFrame(
            self.paned_window,
            text="Folder Browser",
            style="Section.TLabelframe",
        )

        self.paned_window.add(
            tree_frame,
            weight=2,
        )

        tree_frame.rowconfigure(
            0,
            weight=1,
        )

        tree_frame.columnconfigure(
            0,
            weight=1,
        )

        self.tree = ttk.Treeview(
            tree_frame,
            show="tree",
            selectmode="browse",
        )

        tree_scrollbar = ttk.Scrollbar(
            tree_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview,
        )

        horizontal_scrollbar = ttk.Scrollbar(
            tree_frame,
            orient=tk.HORIZONTAL,
            command=self.tree.xview,
        )

        self.tree.configure(
            yscrollcommand=tree_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        tree_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        horizontal_scrollbar.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self._on_tree_selection,
        )

        self.tree.bind(
            "<Button-3>",
            self.popup_menu,
        )

        self.tree_empty_label = ttk.Label(
            tree_frame,
            text=(
                "No folder selected\n\n"
                "Choose Select Folder to begin."
            ),
            anchor="center",
            justify="center",
        )

        self.tree_empty_label.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
        )

    def _create_log_panel(self) -> None:
        """Create the activity log panel."""
        log_frame = ttk.LabelFrame(
            self.paned_window,
            text="Activity Log",
            style="Section.TLabelframe",
        )

        self.paned_window.add(
            log_frame,
            weight=3,
        )

        log_frame.rowconfigure(
            0,
            weight=1,
        )

        log_frame.columnconfigure(
            0,
            weight=1,
        )

        self.log_text = (
            scrolledtext.ScrolledText(
                log_frame,
                wrap=tk.WORD,
                state=tk.DISABLED,
                font=(
                    "Consolas",
                    10,
                ),
                padx=10,
                pady=10,
                relief=tk.SOLID,
                borderwidth=1,
            )
        )

        self.log_text.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

    def _create_status_bar(self) -> None:
        """Create the bottom status bar."""
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

        status_frame = ttk.Frame(
            self.main_frame
        )

        status_frame.grid(
            row=5,
            column=0,
            sticky="ew",
        )

        status_frame.columnconfigure(
            0,
            weight=1,
        )

        status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            style="Status.TLabel",
        )

        status_label.grid(
            row=0,
            column=0,
            sticky="w",
        )

        self.progress_bar = ttk.Progressbar(
            status_frame,
            mode="indeterminate",
            length=180,
        )

        self.progress_bar.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(
                10,
                16,
            ),
        )

        self.progress_bar.grid_remove()

        version_label = ttk.Label(
            status_frame,
            text=f"v{__version__}",
            style="Version.TLabel",
        )

        version_label.grid(
            row=0,
            column=2,
            sticky="e",
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
            title="Select Folder to Organize",
        )

        if not selected_folder:
            return

        self.folder_path = Path(
            selected_folder
        ).resolve()

        self.root_folder_var.set(
            str(self.folder_path)
        )

        self.target_folder_var.set(
            str(self.folder_path)
        )

        self.update_treeview(
            self.folder_path
        )

        self.log_to_text(
            f"Selected folder: "
            f"{self.folder_path}"
        )

        self.set_status(
            "Folder selected."
        )

        self._update_action_states()

    def update_treeview(
        self,
        directory: Path | str,
    ) -> None:
        """Update the folder tree with a directory structure."""
        directory = Path(
            directory
        ).resolve()

        self.tree_empty_label.place_forget()

        self.tree.delete(
            *self.tree.get_children()
        )

        root_node = self.populate_tree(
            directory
        )

        self.tree.selection_set(
            root_node
        )

        self.tree.focus(
            root_node
        )

        self.tree.see(
            root_node
        )

        self.target_folder_var.set(
            str(directory)
        )

    def populate_tree(
        self,
        directory: Path,
    ) -> str:
        """Populate the root directory in the Treeview."""
        root_node = self.tree.insert(
            "",
            "end",
            text=str(directory),
            open=True,
        )

        self.populate_children(
            root_node,
            directory,
        )

        return root_node

    def populate_children(
        self,
        parent: str,
        directory: Path,
    ) -> None:
        """Populate subdirectories beneath a Treeview node."""
        try:
            items = sorted(
                directory.iterdir(),
                key=lambda path: (
                    path.name.lower()
                ),
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
        """Refresh the displayed folder tree."""
        if self.folder_path is None:
            return

        if not self.folder_path.is_dir():
            show_error(
                self.root,
                "Folder Unavailable",
                (
                    "The selected root folder "
                    "no longer exists."
                ),
            )
            return

        self.update_treeview(
            self.folder_path
        )

        self.set_status(
            "Folder tree refreshed."
        )

    def _on_tree_selection(
        self,
        event: tk.Event | None = None,
    ) -> None:
        """Update the displayed operation target."""
        selected_folder = (
            self.get_selected_folder()
        )

        if selected_folder is None:
            self.target_folder_var.set(
                "No folder selected"
            )
        else:
            self.target_folder_var.set(
                str(selected_folder)
            )

        self._update_action_states()

    def get_selected_folder(
        self,
    ) -> Path | None:
        """Return the path represented by the selected Treeview item."""
        selected_items = (
            self.tree.selection()
        )

        if not selected_items:
            focused_item = (
                self.tree.focus()
            )

            if not focused_item:
                return None

            selected_item = (
                focused_item
            )

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
            self.tree.item(
                item
            )["text"]
        ]

        parent = self.tree.parent(
            item
        )

        while parent:
            path_components.insert(
                0,
                self.tree.item(
                    parent
                )["text"],
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

        self.progress_bar.grid()

        self.progress_bar.start(
            12
        )

        self._update_action_states()

        return True

    def _finish_operation(
        self,
        status: str,
    ) -> None:
        """Finish the active application file operation."""
        self.current_operation = None

        self.progress_bar.stop()

        self.progress_bar.grid_remove()

        self.set_status(
            status
        )

        self._update_action_states()

    def _update_action_states(self) -> None:
        """Enable or disable commands based on application state."""
        folder_available = (
            self.folder_path is not None
            and self.folder_path.is_dir()
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

        select_state = (
            tk.DISABLED
            if busy
            else tk.NORMAL
        )

        operation_state = (
            tk.NORMAL
            if folder_available
            and not busy
            else tk.DISABLED
        )

        utility_state = (
            tk.NORMAL
            if folder_available
            and not busy
            else tk.DISABLED
        )

        cancel_state = (
            tk.NORMAL
            if cancel_available
            else tk.DISABLED
        )

        self.select_folder_button.configure(
            state=select_state
        )

        self.organize_button.configure(
            state=operation_state
        )

        self.flatten_button.configure(
            state=operation_state
        )

        self.cancel_button.configure(
            state=cancel_state
        )

        self.open_folder_button.configure(
            state=utility_state
        )

        self.refresh_button.configure(
            state=utility_state
        )

        # Menus
        self.file_menu.entryconfig(
            0,
            state=select_state,
        )

        self.organize_menu.entryconfig(
            0,
            state=operation_state,
        )

        self.organize_menu.entryconfig(
            1,
            state=operation_state,
        )

        self.organize_menu.entryconfig(
            3,
            state=cancel_state,
        )

        self.view_menu.entryconfig(
            1,
            state=utility_state,
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
        self.status_var.set(
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
        """Append a timestamped message to the activity log."""
        timestamp = (
            datetime.now().strftime(
                "%H:%M:%S"
            )
        )

        self.log_text.configure(
            state=tk.NORMAL
        )

        self.log_text.insert(
            tk.END,
            (
                f"[{timestamp}] "
                f"{message}\n"
            ),
        )

        self.log_text.configure(
            state=tk.DISABLED
        )

        self.log_text.see(
            tk.END
        )

    def clear_log(self) -> None:
        """Clear the activity log."""
        self.log_text.configure(
            state=tk.NORMAL
        )

        self.log_text.delete(
            "1.0",
            tk.END,
        )

        self.log_text.configure(
            state=tk.DISABLED
        )

        self.log_to_text(
            "Activity log cleared."
        )

    # -------------------------------------------------------------------------
    # File manager
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
        """Open the selected folder in the platform file manager."""
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