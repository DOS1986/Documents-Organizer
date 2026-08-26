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

        self._item_paths: dict[
            str,
            Path,
        ] = {}

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
            yscrollcommand=(
                vertical_scrollbar.set
            ),
            xscrollcommand=(
                horizontal_scrollbar.set
            ),
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
            preferred_path=(
                previous_selection
            ),
        )

    def clear(self) -> None:
        """Clear the folder browser."""
        self._root_path = None

        self._item_paths.clear()

        self._tree.delete(
            *self._tree.get_children()
        )

        self._show_empty_state()

        self._notify_selection_changed()

    # -------------------------------------------------------------------------
    # Tree population
    # -------------------------------------------------------------------------

    def _render(
        self,
        *,
        root: Path,
        preferred_path: Path | None,
    ) -> None:
        """Render the folder tree."""
        self._tree.delete(
            *self._tree.get_children()
        )

        self._item_paths.clear()

        root_item = self._tree.insert(
            "",
            "end",
            text=str(root),
            open=True,
        )

        self._item_paths[
            root_item
        ] = root

        preferred_item: str | None = None

        if preferred_path == root:
            preferred_item = root_item

        child_preferred_item = (
            self._populate_children(
                parent=root_item,
                directory=root,
                preferred_path=preferred_path,
            )
        )

        if child_preferred_item is not None:
            preferred_item = (
                child_preferred_item
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

    def _populate_children(
        self,
        *,
        parent: str,
        directory: Path,
        preferred_path: Path | None,
    ) -> str | None:
        """
        Populate all child directories.

        Returns the Treeview item matching preferred_path when found.
        """
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
            return None

        preferred_item: str | None = None

        for item_path in items:
            try:
                if (
                    not item_path.is_dir()
                    or item_path.is_symlink()
                ):
                    continue

            except OSError:
                continue

            node = self._tree.insert(
                parent,
                "end",
                text=item_path.name,
            )

            resolved_path = (
                item_path.resolve()
            )

            self._item_paths[
                node
            ] = resolved_path

            if (
                preferred_path is not None
                and resolved_path
                == preferred_path
            ):
                preferred_item = node

            child_preferred_item = (
                self._populate_children(
                    parent=node,
                    directory=resolved_path,
                    preferred_path=(
                        preferred_path
                    ),
                )
            )

            if (
                child_preferred_item
                is not None
            ):
                preferred_item = (
                    child_preferred_item
                )

        return preferred_item

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