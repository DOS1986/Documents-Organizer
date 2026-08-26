from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import ttk


class FolderBrowser(ttk.LabelFrame):
    """Displays and manages the folder navigation tree."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_selection_changed: Callable[
            [Path | None],
            None,
        ]
        | None = None,
        on_open_selected: Callable[
            [Path],
            None,
        ]
        | None = None,
    ) -> None:
        super().__init__(
            parent,
            text="Folder Browser",
            style="Section.TLabelframe",
        )

        self._root_path: Path | None = None
        self._root_item: str | None = None

        # Map Treeview item IDs to filesystem paths.
        self._item_paths: dict[
            str,
            Path,
        ] = {}

        # Reverse lookup used when restoring selections.
        self._path_items: dict[
            Path,
            str,
        ] = {}

        # Tree items whose immediate children have already been loaded.
        self._loaded_items: set[str] = set()

        self._on_selection_changed = (
            on_selection_changed
        )

        self._on_open_selected = (
            on_open_selected
        )

        self.rowconfigure(
            0,
            weight=1,
        )

        self.columnconfigure(
            0,
            weight=1,
        )

        self._create_tree()
        self._create_empty_state()

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def root_path(
        self,
    ) -> Path | None:
        """Return the currently loaded root directory."""
        return self._root_path

    @property
    def selected_path(
        self,
    ) -> Path | None:
        """Return the path represented by the current tree selection."""
        selected_items = (
            self._tree.selection()
        )

        if selected_items:
            item = selected_items[0]
        else:
            item = self._tree.focus()

        if not item:
            return None

        return self._item_paths.get(
            item
        )

    # -------------------------------------------------------------------------
    # Widget construction
    # -------------------------------------------------------------------------

    def _create_tree(self) -> None:
        """Create the Treeview and its scrollbars."""
        self._tree = ttk.Treeview(
            self,
            show="tree",
            selectmode="browse",
        )

        vertical_scrollbar = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL,
            command=self._tree.yview,
        )

        horizontal_scrollbar = ttk.Scrollbar(
            self,
            orient=tk.HORIZONTAL,
            command=self._tree.xview,
        )

        self._tree.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        self._tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        vertical_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        horizontal_scrollbar.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        self._tree.bind(
            "<<TreeviewSelect>>",
            self._handle_selection_changed,
        )

        self._tree.bind(
            "<<TreeviewOpen>>",
            self._handle_tree_open,
        )

        self._tree.bind(
            "<Button-3>",
            self._show_context_menu,
        )

    def _create_empty_state(self) -> None:
        """Create the empty-state message."""
        self._empty_label = ttk.Label(
            self,
            text=(
                "No folder selected\n\n"
                "Choose Select Folder to begin."
            ),
            anchor="center",
            justify="center",
        )

        self._show_empty_state()

    # -------------------------------------------------------------------------
    # Public operations
    # -------------------------------------------------------------------------

    def load(
        self,
        directory: Path | str,
    ) -> None:
        """Load a directory into the folder browser."""
        root = Path(
            directory
        ).resolve()

        if not root.exists():
            raise FileNotFoundError(
                f"Folder does not exist: {root}"
            )

        if not root.is_dir():
            raise NotADirectoryError(
                f"Path is not a directory: {root}"
            )

        self._root_path = root

        self._render(
            root=root,
            preferred_path=root,
        )

    def refresh(self) -> None:
        """Refresh the currently loaded folder tree."""
        if self._root_path is None:
            return

        if not self._root_path.exists():
            raise FileNotFoundError(
                f"Folder does not exist: "
                f"{self._root_path}"
            )

        if not self._root_path.is_dir():
            raise NotADirectoryError(
                f"Path is not a directory: "
                f"{self._root_path}"
            )

        previous_selection = (
            self.selected_path
        )

        self._render(
            root=self._root_path,
            preferred_path=previous_selection,
        )

    def clear(self) -> None:
        """Clear the folder browser."""
        self._root_path = None
        self._root_item = None

        self._item_paths.clear()
        self._path_items.clear()
        self._loaded_items.clear()

        self._tree.delete(
            *self._tree.get_children()
        )

        self._show_empty_state()

        self._notify_selection_changed()

    # -------------------------------------------------------------------------
    # Tree rendering
    # -------------------------------------------------------------------------

    def _render(
        self,
        *,
        root: Path,
        preferred_path: Path | None,
    ) -> None:
        """Render the root and its immediate child directories."""
        self._tree.delete(
            *self._tree.get_children()
        )

        self._item_paths.clear()
        self._path_items.clear()
        self._loaded_items.clear()

        root_item = self._tree.insert(
            "",
            "end",
            text=str(root),
            open=True,
        )

        self._root_item = root_item

        self._register_item(
            root_item,
            root,
        )

        # Only the root's immediate children are loaded here.
        self._load_children(
            root_item
        )

        preferred_item = None

        if preferred_path is not None:
            preferred_item = (
                self._reveal_path(
                    preferred_path
                )
            )

        if preferred_item is None:
            preferred_item = root_item

        self._tree.selection_set(
            preferred_item
        )

        self._tree.focus(
            preferred_item
        )

        self._tree.see(
            preferred_item
        )

        self._hide_empty_state()

        self._notify_selection_changed()

    def _load_children(
        self,
        item: str,
    ) -> None:
        """
        Load one level of child directories beneath a Treeview item.

        Directories are loaded only when their parent is expanded.
        """
        if item in self._loaded_items:
            return

        directory = self._item_paths.get(
            item
        )

        if directory is None:
            return

        # Remove the placeholder used to display the expand arrow.
        children = self._tree.get_children(
            item
        )

        if children:
            self._tree.delete(
                *children
            )

        self._loaded_items.add(
            item
        )

        try:
            directory_items = sorted(
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

        for item_path in directory_items:
            try:
                if not item_path.is_dir():
                    continue

                # Avoid following directory symlinks and junction-like loops.
                if item_path.is_symlink():
                    continue

                resolved_path = (
                    item_path.resolve()
                )

            except OSError:
                continue

            self._insert_directory(
                parent=item,
                directory=resolved_path,
            )

    def _insert_directory(
        self,
        *,
        parent: str,
        directory: Path,
    ) -> str:
        """
        Insert a directory without loading its children.

        A placeholder child gives the directory an expansion arrow.
        """
        node = self._tree.insert(
            parent,
            "end",
            text=directory.name,
        )

        self._register_item(
            node,
            directory,
        )

        # The placeholder makes Tk display an expansion arrow.
        # It is removed the first time the directory is expanded.
        self._tree.insert(
            node,
            "end",
            text="",
        )

        return node

    def _register_item(
        self,
        item: str,
        path: Path,
    ) -> None:
        """Associate a Treeview item with its filesystem path."""
        self._item_paths[
            item
        ] = path

        self._path_items[
            path
        ] = item

    # -------------------------------------------------------------------------
    # Lazy loading
    # -------------------------------------------------------------------------

    def _handle_tree_open(
        self,
        event: tk.Event | None = None,
    ) -> None:
        """Load a directory's children when it is expanded."""
        item = self._tree.focus()

        if not item:
            return

        self._load_children(
            item
        )

    def _reveal_path(
        self,
        path: Path,
    ) -> str | None:
        """
        Load only the ancestors required to reveal a path.

        Used to restore the selected directory after a refresh.
        """
        if self._root_path is None:
            return None

        target = Path(
            path
        ).resolve()

        root = self._root_path

        try:
            relative_path = (
                target.relative_to(
                    root
                )
            )

        except ValueError:
            return None

        if (
            relative_path
            == Path(".")
        ):
            return self._root_item

        if self._root_item is None:
            return None

        current_item = (
            self._root_item
        )

        current_path = root

        for part in relative_path.parts:
            # Make sure the current directory's immediate children exist.
            self._load_children(
                current_item
            )

            self._tree.item(
                current_item,
                open=True,
            )

            current_path = (
                current_path
                / part
            ).resolve()

            next_item = (
                self._path_items.get(
                    current_path
                )
            )

            if next_item is None:
                return None

            current_item = next_item

        return current_item

    # -------------------------------------------------------------------------
    # Selection
    # -------------------------------------------------------------------------

    def _handle_selection_changed(
        self,
        event: tk.Event | None = None,
    ) -> None:
        """Handle Treeview selection changes."""
        self._notify_selection_changed()

    def _notify_selection_changed(
        self,
    ) -> None:
        """Notify the application of a folder selection change."""
        if (
            self._on_selection_changed
            is None
        ):
            return

        self._on_selection_changed(
            self.selected_path
        )

    # -------------------------------------------------------------------------
    # Empty state
    # -------------------------------------------------------------------------

    def _show_empty_state(self) -> None:
        """Display the empty-state message."""
        self._empty_label.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
        )

        self._empty_label.lift()

    def _hide_empty_state(self) -> None:
        """Hide the empty-state message."""
        self._empty_label.place_forget()

    # -------------------------------------------------------------------------
    # Context menu
    # -------------------------------------------------------------------------

    def _show_context_menu(
        self,
        event: tk.Event,
    ) -> None:
        """Display the folder context menu."""
        item = self._tree.identify_row(
            event.y
        )

        if not item:
            return

        self._tree.selection_set(
            item
        )

        self._tree.focus(
            item
        )

        self._notify_selection_changed()

        context_menu = tk.Menu(
            self,
            tearoff=0,
        )

        context_menu.add_command(
            label="Open in File Manager",
            command=self._request_open_selected,
        )

        try:
            context_menu.tk_popup(
                event.x_root,
                event.y_root,
            )

        finally:
            context_menu.grab_release()

    def _request_open_selected(
        self,
    ) -> None:
        """Request that the application open the selected folder."""
        if (
            self._on_open_selected
            is None
        ):
            return

        selected_path = (
            self.selected_path
        )

        if selected_path is None:
            return

        self._on_open_selected(
            selected_path
        )