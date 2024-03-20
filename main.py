import os
import shutil
import datetime
import pystray
import threading
import tkinter as tk
import tkinter.scrolledtext as scrolledtext
from tkinter import PhotoImage
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from pystray import MenuItem as item

# Define a global flag for canceling flattening operation
cancel_flattening = False

# Global variable to store the folder path
folder_path = ""

# Global dictionary to track files organized by extension
organized_files = {}

# Function to organize files and folders by extension and date modified
def organize_files(folder_path):
    """Organize files and folders by extension and date modified."""
    log_to_text("Organizing files...")
    threading.Thread(target=organize_folder, args=(folder_path,)).start()

def organize_folder(folder):
    """Organize files in the specified folder."""
    for root, dirs, files in os.walk(folder):
        # Organize files
        for filename in files:
            if filename not in ['.DS_Store', 'Thumbs.db']:  # Exclude system files
                src = os.path.join(root, filename)
                organize_file(src)
                
    # Log message after organizing files of each extension
    for extension, files in organized_files.items():
        log_to_text(f"Organized {len(files)} {extension} files")

def organize_file(src):
    """Organize a single file based on its extension and date modified."""
    extension = os.path.splitext(src)[1].lower()
    modified_time = os.path.getmtime(src)
    modified_date = datetime.datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d')

    # Create extension folder and modified date folder within the parent directory
    parent_dir = os.path.dirname(src)
    extension_folder = os.path.join(parent_dir, extension[1:])
    os.makedirs(extension_folder, exist_ok=True)
    date_folder = os.path.join(extension_folder, modified_date)
    os.makedirs(date_folder, exist_ok=True)

    # Move the file to the organized folder
    dst = os.path.join(date_folder, os.path.basename(src))
    shutil.move(src, dst)
    
    # Update organized_files dictionary
    if extension in organized_files:
        organized_files[extension].append(dst)
    else:
        organized_files[extension] = [dst]
        
    
# Function to flatten folders
def flatten_folders():
    """Flatten folders based on specified extensions."""
    selected_item = tree.focus()
    if not selected_item:
        messagebox.showerror("Error", "Please select a folder first.")
        return

    folder_path = get_full_path(tree, selected_item)
    if not folder_path:
        messagebox.showerror("Error", "Unable to determine folder path.")
        return
    
    global cancel_flattening
    cancel_flattening = False  # Reset the flag before starting flattening operation
    threading.Thread(target=flatten_folder_recursive, args=(folder_path,)).start()

def flatten_folder_recursive(folder):
    """Recursively flatten folders."""
    global cancel_flattening
    if cancel_flattening:
        log_to_text("Flattening operation canceled.")
        return
    
    for root, dirs, files in os.walk(folder):
        for dir in dirs[:]:
            dir_path = os.path.join(root, dir)
            if os.path.basename(dir).lower() in extensions_to_flatten:
                flatten_subfolders(dir_path)  # Flatten the extension-named folder
                move_files_to_parent(dir_path)  # Move files to the parent folder
                dirs.remove(dir)  # Remove the extension-named folder from further traversal
            else:
                if not cancel_flattening:
                    flatten_folder_recursive(dir_path)  # Continue traversing non-extension-named folders
    
    # Log when a primary folder is clean of extension folders
    if all(os.path.basename(dir).lower() not in extensions_to_flatten for dir in os.listdir(folder)):
        log_to_text(f"{os.path.basename(folder)} is clean of extension folders.")
        refresh_treeview()
        
    # Log flattening completion
    log_to_text(f"All subfolders in {os.path.basename(folder)} flattened.")

def flatten_subfolders(folder):
    """Flatten subfolders of the specified folder."""
    for root, dirs, files in os.walk(folder):
        for file in files:
            src = os.path.join(root, file)
            dst = os.path.join(folder, file)
            shutil.move(src, dst)

    # Delete all subfolders
    for root, dirs, files in os.walk(folder, topdown=False):
        for dir in dirs:
            shutil.rmtree(os.path.join(root, dir))

def move_files_to_parent(folder):
    """Move files from a folder to its parent folder."""
    for root, dirs, files in os.walk(folder):
        for file in files:
            src = os.path.join(root, file)
            dst = os.path.join(os.path.dirname(folder), file)
            shutil.move(src, dst)

    # Delete the extension-named folder
    shutil.rmtree(folder)
    
# Function to get the full path of a selected item in the Treeview
def get_full_path(tree, item):
    """Get the full path of a selected item in the Treeview."""
    path_components = [tree.item(item)['text']]
    parent = tree.parent(item)
    while parent:
        path_components.insert(0, tree.item(parent)['text'])
        parent = tree.parent(parent)
    return os.path.join(*path_components)

# Function to add extensions to flatten
def add_extensions():
    """Add extensions to the list of extensions to flatten."""
    existing_extensions = extensions_to_flatten
    new_extensions = input_extensions(existing_extensions)
    extensions_to_flatten.extend(new_extensions)
    log_to_text("Extensions to flatten:\n" + ', '.join(extensions_to_flatten))

def input_extensions(existing_extensions):
    """Prompt user to input extensions to add."""
    extensions_str = tk.simpledialog.askstring("Add Extensions", "Enter extensions separated by commas (e.g., mp4, webp, exe, jpg): ")
    if extensions_str:
        new_extensions = [ext.strip() for ext in extensions_str.split(",")]
        return list(set(new_extensions) - set(existing_extensions))
    return []

def stop_flattening():
    """Stop the flattening operation."""
    global cancel_flattening
    cancel_flattening = True

# Function to exit the application
def exit_application(icon, item):
    """Exit the application."""
    icon.stop()
    win.destroy()

# Function to hide the window
def hide_window():
    """Hide the window and display a system tray icon."""
    win.withdraw()

    # Create a system tray icon
    image = Image.open("images/folder-256.png")
    menu = (item('Quit', exit_application), item('Show', show_window))
    icon = pystray.Icon("DownloadOrganizer", image, "DownloadOrganizer", menu)
    
    # Run the application
    icon.run()

# Function to show the window again
def show_window(icon, item):
    """Show the window again."""
    icon.stop()
    win.after(0, win.deiconify())

# Function to handle "Select Folder" menu option
def select_folder():
    """Handle the 'Select Folder' menu option."""
    global folder_path
    folder_path = filedialog.askdirectory()
    if folder_path:
        update_treeview(folder_path)

# Function to handle "Run" menu option
def run_organizer():
    """Handle the 'Run' menu option."""
    selected_item = tree.focus()
    if not selected_item:
        messagebox.showerror("Error", "Please select a folder first.")
        return
    
    global folder_path
    folder_path = tree.item(selected_item)['text']
    organize_files(folder_path)

# Function to handle "Exit" menu option
def exit_app():
    """Handle the 'Exit' menu option."""
    root.quit()

# Function to update the Treeview with directory structure
def update_treeview(directory):
    """Update the Treeview with the directory structure."""
    tree.delete(*tree.get_children())
    populate_tree(tree, directory)

def populate_tree(tree, directory):
    """Populate the Treeview with the directory structure."""
    root_node = tree.insert('', 'end', text=directory)
    populate_children(tree, root_node, directory)

def populate_children(tree, parent, directory):
    """Populate children of a node in the Treeview."""
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            node = tree.insert(parent, 'end', text=item)
            populate_subdirectories(tree, node, item_path)

def populate_subdirectories(tree, parent, directory):
    """Populate subdirectories of a node in the Treeview."""
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            node = tree.insert(parent, 'end', text=item)
            populate_subdirectories(tree, node, item_path)

# Function to refresh the Treeview after folder operations
def refresh_treeview():
    """Refresh the Treeview after folder operations."""
    global folder_path
    tree.delete(*tree.get_children())  # Clear the Treeview
    update_treeview(folder_path)

# Function to ensure the latest log entry is always visible
def scroll_to_end():
    """Scroll to the end of the log."""
    log_text.see(tk.END)
    
def start_application():
    # Display all extensions to flatten in log_text
    log_to_text("Extensions to flatten:\n" + ', '.join(extensions_to_flatten))  

# Add log_text modification to ensure latest entry is visible
def log_to_text(message):
    """Log a message to the text widget."""
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, message + "\n")
    log_text.config(state=tk.DISABLED)
    scroll_to_end()

# Function to clear log
def clear_log():
    """Clear the log."""
    log_text.config(state=tk.NORMAL)
    log_text.delete('1.0', tk.END)
    log_text.config(state=tk.DISABLED)
    start_application()
    
def open_explorer_folder():
    selected_item = tree.selection()[0]
    folder_path = get_full_path(tree, selected_item)
    os.startfile(folder_path)
    
def popup_menu(event):
    # Get the item that was clicked on
    item = tree.identify_row(event.y)
    tree.selection_set(item)

    # Create the popup menu
    popup = tk.Menu(win, tearoff=0)
    popup.add_command(label="Reveal in Explorer", command=open_explorer_folder)

    # Display the popup menu at the location of the click
    popup.post(event.x_root, event.y_root)
    
# Function to display information about the application
def show_about():
    messagebox.showinfo("About", "Document Organizer\nVersion: v0.1\nPython Version: v3.12.0\nCreated by: David Southwood\nLicense: MIT License")


# Extensions to be flattened
extensions_to_flatten = ['ini', 'zip', 'mp4', 'pdf', 'cpp', 'rar', 'jpg', 'save', 'h', 'txt', 'doc', 'bin', 'exe', 'jar', 'png', 'tmp', 'docx', 'webp', 'mm']  # Add more as needed

# Create an instance of tkinter frame or window
win = tk.Tk()

win.title("Documents Organizer")
win.iconbitmap("images/folder-256.ico")
# Set the size of the window
win.geometry("1080x800")

# Create menu bar
menu_bar = tk.Menu(win)
win.config(menu=menu_bar)

# Create "File" menu
file_menu = tk.Menu(menu_bar, tearoff=0)
file_menu.add_command(label="Select Folder", command=select_folder)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=exit_app)
menu_bar.add_cascade(label="File", menu=file_menu)

# Create "Action" menu
action_menu = tk.Menu(menu_bar, tearoff=0)

# Organize submenu
organize_submenu = tk.Menu(action_menu, tearoff=0)
organize_submenu.add_command(label="Organize Folders", command=run_organizer)
organize_submenu.add_command(label="Flatten Folders", command=flatten_folders)
organize_submenu.add_command(label="Cancel Flatten Folders", command=stop_flattening)
action_menu.add_cascade(label="Organize", menu=organize_submenu)

# Extensions submenu
action_menu.add_command(label="Add Extensions", command=add_extensions)

# View submenu
view_submenu = tk.Menu(action_menu, tearoff=0)
view_submenu.add_command(label="Clear Log", command=clear_log)
view_submenu.add_command(label="Refresh TreeView", command=refresh_treeview)
action_menu.add_cascade(label="View", menu=view_submenu)

menu_bar.add_cascade(label="Action", menu=action_menu)

# Create "Help" menu
help_menu = tk.Menu(menu_bar, tearoff=0)
help_menu.add_command(label="About", command=show_about)
menu_bar.add_cascade(label="Help", menu=help_menu)

# Create and configure Treeview widget
tree_frame = tk.Frame(win)
tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Make the Treeview expand to fill the entire frame
tree = ttk.Treeview(tree_frame)
tree.pack(expand=tk.YES, fill=tk.BOTH, padx=5, pady=5)

# Bind the right-click event to the popup_menu function
tree.bind("<Button-3>", popup_menu)

# Add a Sizegrip for resizing
ttk.Sizegrip(tree_frame).pack(side="right", fill="y")

# Create and configure ScrolledText widget to display logs
log_frame = tk.Frame(win, width=500)
log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

log_text = scrolledtext.ScrolledText(log_frame, height=10, width=50)
log_text.pack(expand=tk.YES, fill=tk.BOTH)

win.protocol('WM_DELETE_WINDOW', hide_window)

start_application()
win.mainloop()