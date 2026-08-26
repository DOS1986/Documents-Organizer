from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from documents_organizer.ui.components.folder_browser import FolderBrowser


class FakeTree:
    """Minimal Treeview replacement for FolderBrowser tests."""

    def __init__(self) -> None:
        self._counter = 0

        self._nodes: dict[
            str,
            dict[str, object],
        ] = {}

        self._children: dict[
            str,
            list[str],
        ] = {
            "": [],
        }

        self._selection: tuple[str, ...] = ()
        self._focus = ""

    def insert(
        self,
        parent: str,
        index: str,
        *,
        text: str = "",
        open: bool = False,
    ) -> str:
        """Insert a fake tree item."""
        self._counter += 1

        item = f"I{self._counter:03d}"

        self._nodes[item] = {
            "parent": parent,
            "text": text,
            "open": open,
        }

        self._children.setdefault(
            parent,
            [],
        ).append(
            item
        )

        self._children[
            item
        ] = []

        return item

    def get_children(
        self,
        item: str = "",
    ) -> tuple[str, ...]:
        """Return an item's children."""
        return tuple(
            self._children.get(
                item,
                [],
            )
        )

    def delete(
        self,
        *items: str,
    ) -> None:
        """Delete tree items and their descendants."""
        for item in items:
            self._delete_item(
                item
            )

    def _delete_item(
        self,
        item: str,
    ) -> None:
        """Delete one tree item recursively."""
        for child in list(
            self._children.get(
                item,
                [],
            )
        ):
            self._delete_item(
                child
            )

        node = self._nodes.pop(
            item,
            None,
        )

        self._children.pop(
            item,
            None,
        )

        if node is not None:
            parent = str(
                node["parent"]
            )

            parent_children = (
                self._children.get(
                    parent,
                    [],
                )
            )

            if item in parent_children:
                parent_children.remove(
                    item
                )

        if item in self._selection:
            self._selection = tuple(
                selected
                for selected
                in self._selection
                if selected != item
            )

        if self._focus == item:
            self._focus = ""

    def selection(
        self,
    ) -> tuple[str, ...]:
        """Return the current selection."""
        return self._selection

    def selection_set(
        self,
        item: str,
    ) -> None:
        """Set the current selection."""
        self._selection = (
            item,
        )

    def focus(
        self,
        item: str | None = None,
    ) -> str:
        """Get or set the focused tree item."""
        if item is not None:
            self._focus = item

        return self._focus

    def see(
        self,
        item: str,
    ) -> None:
        """Pretend to scroll an item into view."""

    def item(
        self,
        item: str,
        **options: object,
    ) -> dict[str, object]:
        """Read or update tree item options."""
        node = self._nodes[
            item
        ]

        node.update(
            options
        )

        return dict(
            node
        )


class FakeLabel:
    """Minimal label replacement for empty-state tests."""

    def __init__(self) -> None:
        self.visible = False

    def place(
        self,
        **kwargs: object,
    ) -> None:
        """Show the label."""
        self.visible = True

    def place_forget(
        self,
    ) -> None:
        """Hide the label."""
        self.visible = False

    def lift(
        self,
    ) -> None:
        """Pretend to raise the label."""


def create_browser(
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
) -> FolderBrowser:
    """
    Create a FolderBrowser without initializing real Tk widgets.

    The filesystem and lazy-loading logic can then be tested
    independently from Tkinter.
    """
    browser = FolderBrowser.__new__(
        FolderBrowser
    )

    browser._root_path = None
    browser._root_item = None

    browser._item_paths = {}
    browser._path_items = {}
    browser._loaded_items = set()

    browser._on_selection_changed = (
        on_selection_changed
    )

    browser._on_open_selected = (
        on_open_selected
    )

    browser._tree = FakeTree()
    browser._empty_label = FakeLabel()

    return browser


def test_load_only_populates_immediate_directories(
    tmp_path: Path,
) -> None:
    """Initial loading should not recursively scan child directories."""
    alpha = (
        tmp_path
        / "Alpha"
    )

    nested = (
        alpha
        / "Nested"
    )

    deep = (
        nested
        / "Deep"
    )

    beta = (
        tmp_path
        / "Beta"
    )

    deep.mkdir(
        parents=True
    )

    beta.mkdir()

    browser = create_browser()

    browser.load(
        tmp_path
    )

    loaded_paths = set(
        browser._path_items
    )

    assert tmp_path.resolve() in loaded_paths
    assert alpha.resolve() in loaded_paths
    assert beta.resolve() in loaded_paths

    # Nested directories must not be discovered yet.
    assert nested.resolve() not in loaded_paths
    assert deep.resolve() not in loaded_paths

    assert browser.selected_path == (
        tmp_path.resolve()
    )


def test_child_directory_is_not_marked_loaded_initially(
    tmp_path: Path,
) -> None:
    """Child directories should remain unloaded until expanded."""
    child = (
        tmp_path
        / "Child"
    )

    (
        child
        / "Grandchild"
    ).mkdir(
        parents=True
    )

    browser = create_browser()

    browser.load(
        tmp_path
    )

    root_item = (
        browser._path_items[
            tmp_path.resolve()
        ]
    )

    child_item = (
        browser._path_items[
            child.resolve()
        ]
    )

    assert root_item in (
        browser._loaded_items
    )

    assert child_item not in (
        browser._loaded_items
    )


def test_expanding_directory_loads_one_level(
    tmp_path: Path,
) -> None:
    """Expanding a folder should load only its immediate children."""
    child = (
        tmp_path
        / "Child"
    )

    grandchild = (
        child
        / "Grandchild"
    )

    great_grandchild = (
        grandchild
        / "GreatGrandchild"
    )

    great_grandchild.mkdir(
        parents=True
    )

    browser = create_browser()

    browser.load(
        tmp_path
    )

    child_item = (
        browser._path_items[
            child.resolve()
        ]
    )

    browser._tree.focus(
        child_item
    )

    browser._handle_tree_open()

    assert grandchild.resolve() in (
        browser._path_items
    )

    # Grandchild itself has not been expanded,
    # so its children must remain undiscovered.
    assert great_grandchild.resolve() not in (
        browser._path_items
    )

    assert child_item in (
        browser._loaded_items
    )


def test_empty_directory_placeholder_is_removed_when_expanded(
    tmp_path: Path,
) -> None:
    """Expanding an empty folder should remove its placeholder."""
    empty_folder = (
        tmp_path
        / "Empty"
    )

    empty_folder.mkdir()

    browser = create_browser()

    browser.load(
        tmp_path
    )

    empty_item = (
        browser._path_items[
            empty_folder.resolve()
        ]
    )

    # Newly inserted directories receive one placeholder.
    assert len(
        browser._tree.get_children(
            empty_item
        )
    ) == 1

    browser._tree.focus(
        empty_item
    )

    browser._handle_tree_open()

    assert (
        browser._tree.get_children(
            empty_item
        )
        == ()
    )

    assert empty_item in (
        browser._loaded_items
    )


def test_loading_children_twice_does_not_duplicate_items(
    tmp_path: Path,
) -> None:
    """A directory should only be loaded once."""
    child = (
        tmp_path
        / "Child"
    )

    grandchild = (
        child
        / "Grandchild"
    )

    grandchild.mkdir(
        parents=True
    )

    browser = create_browser()

    browser.load(
        tmp_path
    )

    child_item = (
        browser._path_items[
            child.resolve()
        ]
    )

    browser._load_children(
        child_item
    )

    children_after_first_load = (
        browser._tree.get_children(
            child_item
        )
    )

    browser._load_children(
        child_item
    )

    children_after_second_load = (
        browser._tree.get_children(
            child_item
        )
    )

    assert children_after_first_load == (
        children_after_second_load
    )

    assert (
        len(
            children_after_second_load
        )
        == 1
    )


def test_directories_are_sorted_case_insensitively(
    tmp_path: Path,
) -> None:
    """Folder entries should be shown in case-insensitive name order."""
    for name in (
        "Zulu",
        "alpha",
        "Bravo",
    ):
        (
            tmp_path
            / name
        ).mkdir()

    browser = create_browser()

    browser.load(
        tmp_path
    )

    root_item = (
        browser._root_item
    )

    assert root_item is not None

    child_items = (
        browser._tree.get_children(
            root_item
        )
    )

    names = [
        str(
            browser._tree.item(
                item
            )["text"]
        )
        for item in child_items
    ]

    assert names == [
        "alpha",
        "Bravo",
        "Zulu",
    ]


def test_refresh_restores_nested_selection_lazily(
    tmp_path: Path,
) -> None:
    """
    Refresh should restore a nested selection without
    recursively loading unrelated branches.
    """
    selected_folder = (
        tmp_path
        / "Alpha"
        / "One"
        / "Selected"
    )

    selected_folder.mkdir(
        parents=True
    )

    unrelated_folder = (
        tmp_path
        / "Beta"
        / "Unrelated"
    )

    unrelated_folder.mkdir(
        parents=True
    )

    browser = create_browser()

    browser.load(
        tmp_path
    )

    alpha_item = (
        browser._path_items[
            (
                tmp_path
                / "Alpha"
            ).resolve()
        ]
    )

    browser._load_children(
        alpha_item
    )

    one_item = (
        browser._path_items[
            (
                tmp_path
                / "Alpha"
                / "One"
            ).resolve()
        ]
    )

    browser._load_children(
        one_item
    )

    selected_item = (
        browser._path_items[
            selected_folder.resolve()
        ]
    )

    browser._tree.selection_set(
        selected_item
    )

    browser._tree.focus(
        selected_item
    )

    assert browser.selected_path == (
        selected_folder.resolve()
    )

    browser.refresh()

    assert browser.selected_path == (
        selected_folder.resolve()
    )

    # Restoring Alpha/One/Selected must not recursively
    # load the unrelated Beta branch.
    assert unrelated_folder.resolve() not in (
        browser._path_items
    )


def test_refresh_falls_back_to_root_when_selection_was_deleted(
    tmp_path: Path,
) -> None:
    """Refresh should safely select the root if the old target disappeared."""
    child = (
        tmp_path
        / "Child"
    )

    child.mkdir()

    browser = create_browser()

    browser.load(
        tmp_path
    )

    child_item = (
        browser._path_items[
            child.resolve()
        ]
    )

    browser._tree.selection_set(
        child_item
    )

    browser._tree.focus(
        child_item
    )

    assert browser.selected_path == (
        child.resolve()
    )

    child.rmdir()

    browser.refresh()

    assert browser.selected_path == (
        tmp_path.resolve()
    )


def test_selection_callback_receives_selected_path(
    tmp_path: Path,
) -> None:
    """Folder selections should notify the application with a Path."""
    child = (
        tmp_path
        / "Child"
    )

    child.mkdir()

    selections: list[
        Path | None
    ] = []

    browser = create_browser(
        on_selection_changed=(
            selections.append
        )
    )

    browser.load(
        tmp_path
    )

    # Loading selects the root.
    assert selections[-1] == (
        tmp_path.resolve()
    )

    child_item = (
        browser._path_items[
            child.resolve()
        ]
    )

    browser._tree.selection_set(
        child_item
    )

    browser._tree.focus(
        child_item
    )

    browser._handle_selection_changed()

    assert selections[-1] == (
        child.resolve()
    )


def test_open_callback_receives_selected_path(
    tmp_path: Path,
) -> None:
    """Open requests should pass the selected directory to the application."""
    child = (
        tmp_path
        / "Child"
    )

    child.mkdir()

    opened_paths: list[Path] = []

    browser = create_browser(
        on_open_selected=(
            opened_paths.append
        )
    )

    browser.load(
        tmp_path
    )

    child_item = (
        browser._path_items[
            child.resolve()
        ]
    )

    browser._tree.selection_set(
        child_item
    )

    browser._tree.focus(
        child_item
    )

    browser._request_open_selected()

    assert opened_paths == [
        child.resolve()
    ]


def test_clear_resets_browser(
    tmp_path: Path,
) -> None:
    """Clearing should remove all tree and path state."""
    child = (
        tmp_path
        / "Child"
    )

    child.mkdir()

    selections: list[
        Path | None
    ] = []

    browser = create_browser(
        on_selection_changed=(
            selections.append
        )
    )

    browser.load(
        tmp_path
    )

    browser.clear()

    assert browser.root_path is None
    assert browser.selected_path is None
    assert browser._root_item is None

    assert browser._item_paths == {}
    assert browser._path_items == {}
    assert browser._loaded_items == set()

    assert (
        browser._tree.get_children()
        == ()
    )

    assert browser._empty_label.visible is True

    assert selections[-1] is None


def test_load_rejects_missing_directory(
    tmp_path: Path,
) -> None:
    """Loading a missing directory should fail clearly."""
    browser = create_browser()

    missing = (
        tmp_path
        / "Missing"
    )

    with pytest.raises(
        FileNotFoundError
    ):
        browser.load(
            missing
        )


def test_load_rejects_file_path(
    tmp_path: Path,
) -> None:
    """Loading a file instead of a directory should fail clearly."""
    file_path = (
        tmp_path
        / "document.txt"
    )

    file_path.write_text(
        "test",
        encoding="utf-8",
    )

    browser = create_browser()

    with pytest.raises(
        NotADirectoryError
    ):
        browser.load(
            file_path
        )