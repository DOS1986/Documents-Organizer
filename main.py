import os
import shutil
import threading
import tkinter as tk
import tkinter.scrolledtext as scrolledtext
from tkinter import filedialog, messagebox, simpledialog, ttk

import pystray
from PIL import Image
from pystray import MenuItem as item

from documents_organizer import __version__
from documents_organizer.filesystem import move_file_safely
from documents_organizer.platform_utils import open_in_file_manager
from documents_organizer.services.organizer import (
    OrganizationResult,
    organize_directory,
)


# Define a global flag for canceling flattening operation
cancel_flattening = False

# Global variable to store the folder path
folder_path = ""

def organize_files(selected_folder):
    """Start an organization operation in a background thread."""
    log_to_text(
        f"Organizing: {selected_folder}"
    )

    worker = threading.Thread(
        target=_run_organizer,
        args=(selected_folder,),
        daemon=True,
    )

    worker.start()


def _run_organizer(selected_folder):
    """Run the organizer service outside the Tkinter main thread."""
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
        win.after(
            0,
            _handle_organization_error,
            str(exc),
        )

        return

    win.after(
        0,
        _handle_organization_result,
        result,
    )


def _handle_organization_result(
    result: OrganizationResult,
):
    """Display organization results on the Tkinter main thread."""
    for extension, count in sorted(
        result.by_extension.items()
    ):
        label = (
            "file"
            if count == 1
            else "files"
        )

        log_to_text(
            f"Organized {count} "
            f"{extension} {label}."
        )

    if result.skipped:
        label = (
            "file"
            if result.skipped == 1
            else "files"
        )

        log_to_text(
            f"Skipped {result.skipped} "
            f"{label}."
        )

    if result.failed:
        label = (
            "file"
            if result.failed == 1
            else "files"
        )

        log_to_text(
            f"Unable to process "
            f"{result.failed} {label}."
        )

        for failure in result.failures:
            log_to_text(
                f"  {failure.path}: "
                f"{failure.error}"
            )

    log_to_text(
        f"Organization complete. "
        f"{result.moved} files moved."
    )

    refresh_treeview()


def _handle_organization_error(
    message: str,
):
    """Display a fatal organization error."""
    log_to_text(
        f"Organization failed: {message}"
    )

    messagebox.showerror(
        "Organization Failed",
        message,
    )


def flatten_folders():
    """Flatten folders based on specified extensions."""
    selected_item = tree.focus()

    if not selected_item:
        messagebox.showerror(
            "Error",
            "Please select a folder first.",
        )
        return

    selected_folder = get_full_path(
        tree,
        selected_item,
    )

    if not selected_folder:
        messagebox.showerror(
            "Error",
            "Unable to determine folder path.",
        )
        return

    global cancel_flattening
    cancel_flattening = False

    threading.Thread(
        target=flatten_folder_recursive,
        args=(selected_folder,),
        daemon=True,
    ).start()


def flatten_folder_recursive(folder):
    """Recursively flatten folders."""
    global cancel_flattening

    if cancel_flattening:
        log_to_text("Flattening operation canceled.")
        return

    try:
        for root, dirs, files in os.walk(folder):
            if cancel_flattening:
                log_to_text(
                    "Flattening operation canceled."
                )
                return

            for directory in dirs[:]:
                if cancel_flattening:
                    log_to_text(
                        "Flattening operation canceled."
                    )
                    return

                dir_path = os.path.join(
                    root,
                    directory,
                )

                if (
                    os.path.basename(directory).lower()
                    in extensions_to_flatten
                ):
                    flatten_subfolders(dir_path)

                    if cancel_flattening:
                        log_to_text(
                            "Flattening operation canceled."
                        )
                        return

                    move_files_to_parent(dir_path)

                    dirs.remove(directory)

                else:
                    if not cancel_flattening:
                        flatten_folder_recursive(
                            dir_path
                        )

        if not os.path.isdir(folder):
            return

        remaining_items = os.listdir(folder)

        if all(
            item_name.lower()
            not in extensions_to_flatten
            for item_name in remaining_items
        ):
            log_to_text(
                f"{os.path.basename(folder)} "
                "is clean of extension folders."
            )

            refresh_treeview()

        log_to_text(
            f"All subfolders in "
            f"{os.path.basename(folder)} flattened."
        )

    except Exception as exc:
        log_to_text(
            f"Error flattening folders: {exc}"
        )


def flatten_subfolders(folder):
    """Flatten subfolders of the specified folder."""
    global cancel_flattening

    for root, dirs, files in os.walk(folder):
        if cancel_flattening:
            return

        for filename in files:
            if cancel_flattening:
                return

            src = os.path.join(
                root,
                filename,
            )

            destination = os.path.join(
                folder,
                filename,
            )

            # A file already located directly in the target folder
            # does not need to be moved.
            if os.path.abspath(src) == os.path.abspath(
                destination
            ):
                continue

            move_file_safely(
                src,
                destination,
            )

    for root, dirs, files in os.walk(
        folder,
        topdown=False,
    ):
        if cancel_flattening:
            return

        for directory in dirs:
            directory_path = os.path.join(
                root,
                directory,
            )

            if os.path.isdir(directory_path):
                shutil.rmtree(directory_path)


def move_files_to_parent(folder):
    """Move files from a folder to its parent folder."""
    global cancel_flattening

    parent_folder = os.path.dirname(folder)

    for root, dirs, files in os.walk(folder):
        if cancel_flattening:
            return

        for filename in files:
            if cancel_flattening:
                return

            src = os.path.join(
                root,
                filename,
            )

            destination = os.path.join(
                parent_folder,
                filename,
            )

            move_file_safely(
                src,
                destination,
            )

    if os.path.isdir(folder):
        shutil.rmtree(folder)


def get_full_path(tree, item):
    """Get the full path of a selected item in the Treeview."""
    path_components = [
        tree.item(item)["text"]
    ]

    parent = tree.parent(item)

    while parent:
        path_components.insert(
            0,
            tree.item(parent)["text"],
        )

        parent = tree.parent(parent)

    return os.path.join(
        *path_components
    )


def add_extensions():
    """Add extensions to the list of extensions to flatten."""
    existing_extensions = extensions_to_flatten

    new_extensions = input_extensions(
        existing_extensions
    )

    extensions_to_flatten.extend(
        new_extensions
    )

    log_to_text(
        "Extensions to flatten:\n"
        + ", ".join(extensions_to_flatten)
    )


def input_extensions(existing_extensions):
    """Prompt user to input extensions to add."""
    extensions_str = simpledialog.askstring(
        "Add Extensions",
        (
            "Enter extensions separated by commas "
            "(e.g., mp4, webp, exe, jpg):"
        ),
    )

    if not extensions_str:
        return []

    new_extensions = [
        extension.strip().lower().lstrip(".")
        for extension in extensions_str.split(",")
        if extension.strip()
    ]

    return list(
        set(new_extensions)
        - set(existing_extensions)
    )


def stop_flattening():
    """Stop the flattening operation."""
    global cancel_flattening

    cancel_flattening = True

    log_to_text(
        "Cancel requested..."
    )


def exit_application(icon, menu_item):
    """Exit the application from the system tray."""
    icon.stop()

    win.after(
        0,
        win.destroy,
    )


def hide_window():
    """Hide the window and display a system tray icon."""
    win.withdraw()

    try:
        image = Image.open(
            "images/folder-256.png"
        )

        menu = (
            item(
                "Show",
                show_window,
            ),
            item(
                "Quit",
                exit_application,
            ),
        )

        icon = pystray.Icon(
            "DocumentsOrganizer",
            image,
            "Documents Organizer",
            menu,
        )

        threading.Thread(
            target=icon.run,
            daemon=True,
        ).start()

    except Exception as exc:
        win.deiconify()

        messagebox.showerror(
            "System Tray Error",
            (
                "Documents Organizer could not "
                f"start the system tray icon.\n\n{exc}"
            ),
        )


def show_window(icon, menu_item):
    """Show the application window again."""
    icon.stop()

    win.after(
        0,
        win.deiconify,
    )


def select_folder():
    """Handle the Select Folder menu option."""
    global folder_path

    selected_folder = filedialog.askdirectory()

    if not selected_folder:
        return

    folder_path = selected_folder

    update_treeview(
        folder_path
    )


def run_organizer():
    """Handle the Organize Folders menu option."""
    selected_item = tree.focus()

    if not selected_item:
        messagebox.showerror(
            "Error",
            "Please select a folder first.",
        )
        return

    selected_folder = get_full_path(
        tree,
        selected_item,
    )

    if not os.path.isdir(
        selected_folder
    ):
        messagebox.showerror(
            "Error",
            "The selected folder does not exist.",
        )
        return

    organize_files(
        selected_folder
    )


def exit_app():
    """Exit the application."""
    win.destroy()


def update_treeview(directory):
    """Update the Treeview with the directory structure."""
    tree.delete(
        *tree.get_children()
    )

    populate_tree(
        tree,
        directory,
    )


def populate_tree(tree, directory):
    """Populate the Treeview with the directory structure."""
    root_node = tree.insert(
        "",
        "end",
        text=directory,
    )

    populate_children(
        tree,
        root_node,
        directory,
    )


def populate_children(tree, parent, directory):
    """Populate children of a node in the Treeview."""
    try:
        items = os.listdir(directory)
    except (PermissionError, FileNotFoundError):
        return

    for item_name in items:
        item_path = os.path.join(
            directory,
            item_name,
        )

        if os.path.isdir(item_path):
            node = tree.insert(
                parent,
                "end",
                text=item_name,
            )

            populate_subdirectories(
                tree,
                node,
                item_path,
            )


def populate_subdirectories(
    tree,
    parent,
    directory,
):
    """Populate subdirectories of a node in the Treeview."""
    try:
        items = os.listdir(directory)
    except (PermissionError, FileNotFoundError):
        return

    for item_name in items:
        item_path = os.path.join(
            directory,
            item_name,
        )

        if os.path.isdir(item_path):
            node = tree.insert(
                parent,
                "end",
                text=item_name,
            )

            populate_subdirectories(
                tree,
                node,
                item_path,
            )


def refresh_treeview():
    """Refresh the Treeview after folder operations."""
    global folder_path

    if not folder_path:
        return

    if not os.path.isdir(folder_path):
        return

    tree.delete(
        *tree.get_children()
    )

    update_treeview(
        folder_path
    )


def scroll_to_end():
    """Scroll to the end of the log."""
    log_text.see(
        tk.END
    )


def start_application():
    """Display application startup information."""
    log_to_text(
        "Extensions to flatten:\n"
        + ", ".join(extensions_to_flatten)
    )


def log_to_text(message):
    """Log a message to the text widget."""
    log_text.config(
        state=tk.NORMAL
    )

    log_text.insert(
        tk.END,
        message + "\n",
    )

    log_text.config(
        state=tk.DISABLED
    )

    scroll_to_end()


def clear_log():
    """Clear the log."""
    log_text.config(
        state=tk.NORMAL
    )

    log_text.delete(
        "1.0",
        tk.END,
    )

    log_text.config(
        state=tk.DISABLED
    )

    start_application()


def open_selected_folder():
    """Open the selected folder in the operating system's file manager."""
    selected_items = tree.selection()

    if not selected_items:
        messagebox.showerror(
            "Error",
            "Please select a folder first.",
        )
        return

    selected_item = selected_items[0]

    selected_path = get_full_path(
        tree,
        selected_item,
    )

    try:
        open_in_file_manager(
            selected_path
        )

    except (
        FileNotFoundError,
        NotADirectoryError,
        OSError,
    ) as exc:
        messagebox.showerror(
            "Unable to Open Folder",
            str(exc),
        )


def popup_menu(event):
    """Display the folder context menu."""
    selected_item = tree.identify_row(
        event.y
    )

    if not selected_item:
        return

    tree.selection_set(
        selected_item
    )

    tree.focus(
        selected_item
    )

    popup = tk.Menu(
        win,
        tearoff=0,
    )

    popup.add_command(
        label="Open in File Manager",
        command=open_selected_folder,
    )

    popup.post(
        event.x_root,
        event.y_root,
    )


def show_about():
    """Display information about the application."""
    messagebox.showinfo(
        "About",
        (
            "Documents Organizer\n"
            f"Version: v{__version__}\n"
            "Created by: David Southwood\n"
            "License: MIT License"
        ),
    )


extensions_to_flatten = [
    "ini",
    "zip",
    "mp4",
    "pdf",
    "cpp",
    "rar",
    "jpg",
    "save",
    "h",
    "txt",
    "doc",
    "bin",
    "exe",
    "jar",
    "png",
    "tmp",
    "docx",
    "webp",
    "mm",
]


win = tk.Tk()

win.title(
    "Documents Organizer"
)

try:
    win.iconbitmap(
        "images/folder-256.ico"
    )
except tk.TclError:
    pass

win.geometry(
    "1080x800"
)


# Menu bar
menu_bar = tk.Menu(
    win
)

win.config(
    menu=menu_bar
)


# File menu
file_menu = tk.Menu(
    menu_bar,
    tearoff=0,
)

file_menu.add_command(
    label="Select Folder",
    command=select_folder,
)

file_menu.add_separator()

file_menu.add_command(
    label="Exit",
    command=exit_app,
)

menu_bar.add_cascade(
    label="File",
    menu=file_menu,
)


# Action menu
action_menu = tk.Menu(
    menu_bar,
    tearoff=0,
)

organize_submenu = tk.Menu(
    action_menu,
    tearoff=0,
)

organize_submenu.add_command(
    label="Organize Folders",
    command=run_organizer,
)

organize_submenu.add_command(
    label="Flatten Folders",
    command=flatten_folders,
)

organize_submenu.add_command(
    label="Cancel Flatten Folders",
    command=stop_flattening,
)

action_menu.add_cascade(
    label="Organize",
    menu=organize_submenu,
)

action_menu.add_command(
    label="Add Extensions",
    command=add_extensions,
)

view_submenu = tk.Menu(
    action_menu,
    tearoff=0,
)

view_submenu.add_command(
    label="Clear Log",
    command=clear_log,
)

view_submenu.add_command(
    label="Refresh TreeView",
    command=refresh_treeview,
)

action_menu.add_cascade(
    label="View",
    menu=view_submenu,
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
    command=show_about,
)

menu_bar.add_cascade(
    label="Help",
    menu=help_menu,
)


# Treeview
tree_frame = tk.Frame(
    win
)

tree_frame.pack(
    side=tk.LEFT,
    fill=tk.BOTH,
    expand=True,
)

tree = ttk.Treeview(
    tree_frame
)

tree.pack(
    expand=tk.YES,
    fill=tk.BOTH,
    padx=5,
    pady=5,
)

tree.bind(
    "<Button-3>",
    popup_menu,
)

ttk.Sizegrip(
    tree_frame
).pack(
    side="right",
    fill="y",
)


# Log
log_frame = tk.Frame(
    win,
    width=500,
)

log_frame.pack(
    side=tk.RIGHT,
    fill=tk.BOTH,
    expand=True,
)

log_text = scrolledtext.ScrolledText(
    log_frame,
    height=10,
    width=50,
)

log_text.pack(
    expand=tk.YES,
    fill=tk.BOTH,
)

log_text.config(
    state=tk.DISABLED
)


win.protocol(
    "WM_DELETE_WINDOW",
    hide_window,
)


start_application()

win.mainloop()