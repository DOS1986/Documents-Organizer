# Documents Organizer

![Documents Organizer Logo](images/logo/folder-48.png)

A Python desktop utility for safely organizing files by modification date and file type, flattening organizer-generated folder structures, and managing file collections through a graphical interface.

Documents Organizer was created to automate repetitive file-management tasks while still giving the user control over the folder being processed and visibility into what the application is doing.

> **Current version:** v0.2.0  
> **Current platform focus:** Windows

---

## Features

- **Organize Files:** Organize files into a date-first, file-type-based directory structure.
- **Flatten Folders:** Move files from organizer-generated date/type folders back into the selected root directory.
- **Nested Folder Support:** Recursively discover files inside nested directories and centralize them under the selected root.
- **Duplicate Protection:** Preserve files with duplicate names by automatically adding numbered suffixes instead of overwriting existing files.
- **Extensionless File Support:** Organize files without extensions into an `other` directory.
- **Cancelable Flattening:** Request cancellation of an active flatten operation.
- **Lazy-Loaded Folder Browser:** Load directory contents only as folders are expanded instead of recursively scanning the entire tree at startup.
- **Operation Target Selection:** Select a nested folder in the Folder Browser and use it as the target for file operations.
- **File Manager Integration:** Open selected folders directly in the platform file manager.
- **System Tray Support:** Explicitly minimize Documents Organizer to the system tray and restore or quit it from the tray menu.
- **Activity Log:** View timestamped operation messages, summaries, and errors.
- **Background File Operations:** Run file operations outside the Tkinter UI thread to keep the interface responsive.
- **Safe Directory Cleanup:** Remove only empty organizer-generated directories during flattening.
- **Automated Tests:** Filesystem, controller, presenter, folder browser, and complete workflow behavior are covered by automated tests.

---

## What's New in v0.2.0

v0.2.0 is a major rewrite of Documents Organizer.

The release introduces a new organization structure, safer filesystem behavior, a redesigned interface, background operation management, lazy-loaded folder browsing, and a substantially refactored application architecture.

### New Organization Structure

Previous versions organized files using an extension-first structure.

v0.2.0 uses a **date-first structure**:

```text
Selected Folder/
├── YYYY-MM-DD/
│   ├── pdf/
│   ├── jpg/
│   ├── txt/
│   ├── zip/
│   └── other/
└── YYYY-MM-DD/
    └── ...
```

For example:

```text
Documents/
├── 2026-08-25/
│   ├── pdf/
│   │   └── report.pdf
│   ├── jpg/
│   │   └── photo.jpg
│   └── txt/
│       └── notes.txt
└── 2026-08-26/
    ├── zip/
    │   └── archive.zip
    └── other/
        └── README
```

The date is currently determined using each file's **modified date**.

Files without an extension are placed in:

```text
other/
```

---

## Screenshots

The user interface was redesigned for v0.2.0.

Updated screenshots will be added after the v0.2.0 Windows package has completed final release testing.

The previous screenshots represented the older application interface and workflows and are no longer included here because they do not accurately represent v0.2.0.

---

## Getting Started

### Requirements

Documents Organizer is written in Python and uses Tkinter for its graphical interface.

Development currently targets:

```text
Python >= 3.12
```

Runtime dependencies include:

```text
pillow==10.2.0
pystray==0.19.5
```

Development dependencies include:

```text
pytest>=8,<10
```

You also need permission to read, move, and modify files within the directories you intend to process.

---

### Clone the Repository

Clone the repository:

```powershell
git clone https://github.com/DOS1986/Documents-Organizer.git
```

Enter the project directory:

```powershell
cd Documents-Organizer
```

---

### Create a Virtual Environment

On Windows:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

---

### Install the Project

Install Documents Organizer in editable mode with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

---

### Run the Application

From the project root:

```powershell
python main.py
```

---

## Usage

### Select a Folder

Choose **Select Folder** from the toolbar or File menu.

The selected directory becomes the application's **Root Folder**.

The Folder Browser displays that directory and its immediate subdirectories.

Always verify that the correct folder has been selected before beginning a filesystem operation.

---

### Root Folder vs. Operation Target

Documents Organizer distinguishes between two locations:

- **Root Folder:** The folder originally selected using **Select Folder**.
- **Operation Target:** The folder currently selected in the Folder Browser.

When the root is initially loaded, both values point to the same directory.

Selecting a nested folder changes the Operation Target.

Commands such as **Organize**, **Flatten**, and **Open Selected** operate on the current Operation Target.

---

## Organizing Files

Select the folder you want to organize and choose **Organize**.

Documents Organizer recursively discovers files beneath the Operation Target and centralizes them into:

```text
<modified date>/<file type>/<filename>
```

For example, starting with:

```text
MyFiles/
├── report.pdf
├── photo.jpg
└── project/
    └── notes.txt
```

Organize may produce:

```text
MyFiles/
├── project/
└── 2026-08-26/
    ├── pdf/
    │   └── report.pdf
    ├── jpg/
    │   └── photo.jpg
    └── txt/
        └── notes.txt
```

The original:

```text
project/
```

directory remains.

v0.2.0 intentionally does **not** remove original source directories after their files have been centralized.

---

## Nested Folder Centralization

Files found in nested directories are organized into the selected Operation Target's date/type structure.

For example:

```text
Downloads/
├── first/
│   └── report.pdf
└── second/
    └── photo.jpg
```

may become:

```text
Downloads/
├── first/
├── second/
└── 2026-08-26/
    ├── pdf/
    │   └── report.pdf
    └── jpg/
        └── photo.jpg
```

The original nested hierarchy is not recreated inside the date directories.

This is intentional.

Documents Organizer is designed to **centralize files**, not preserve their original nested folder locations.

---

## Duplicate Filename Protection

Documents Organizer does not intentionally overwrite an existing destination file.

When multiple files have the same name, numbered suffixes are automatically added.

For example:

```text
first/report.pdf
second/report.pdf
third/report.pdf
```

may become:

```text
2026-08-26/
└── pdf/
    ├── report.pdf
    ├── report (1).pdf
    └── report (2).pdf
```

The same collision protection is used when files are flattened back into the root directory.

---

## Files Without Extensions

Files without an extension are supported.

For example:

```text
README
LICENSE
Dockerfile
```

are organized beneath:

```text
other/
```

Example:

```text
2026-08-26/
└── other/
    ├── README
    └── LICENSE
```

---

## Flattening Files

**Flatten** reverses the organizer-generated date/type structure by moving eligible files back into the selected Operation Target.

For example:

```text
Documents/
└── 2026-08-26/
    ├── pdf/
    │   └── report.pdf
    ├── jpg/
    │   └── photo.jpg
    └── txt/
        └── notes.txt
```

becomes:

```text
Documents/
├── report.pdf
├── photo.jpg
└── notes.txt
```

After files are moved, Documents Organizer attempts to remove empty organizer-generated type and date directories.

Directory cleanup is intentionally conservative.

Documents Organizer uses empty-directory removal rather than recursive deletion. If unexpected content remains inside a directory, that directory is preserved.

---

## Flatten Is Not Undo

Flatten reverses the structure created by Documents Organizer, but it is **not a full undo system**.

For example, suppose the original files were:

```text
Documents/
├── work/
│   └── report.pdf
└── personal/
    └── photo.jpg
```

After organizing and then flattening, the result is:

```text
Documents/
├── work/
├── personal/
├── report.pdf
└── photo.jpg
```

Documents Organizer currently does not record enough information to know that:

```text
report.pdf
```

originally belonged inside:

```text
work/
```

A future release may add an operation manifest and full undo support capable of restoring original file locations.

---

## Canceling Flatten

An active flatten operation can be canceled using the **Cancel** button or corresponding menu command.

Cancellation is cooperative.

When cancellation is requested, the application signals the active flatten operation and stops processing at a safe point.

Files already moved before the cancellation request are not automatically moved back.

---

## Folder Browser

v0.2.0 introduces a lazy-loaded Folder Browser.

When a root folder is selected, Documents Organizer loads only its immediate subdirectories.

For example:

```text
LargeFolder/
├── Games/
├── Photos/
├── Projects/
└── Work/
```

Documents Organizer does not immediately scan every directory beneath those folders.

Instead:

```text
Select Folder
    ↓
Load immediate directories
    ↓
Display Folder Browser
    ↓
User expands Projects
    ↓
Load Projects children
```

This prevents the interface from recursively walking potentially very large directory structures merely to display the browser.

Nested folders are loaded as they are expanded.

The Folder Browser also attempts to preserve the current nested selection when the tree is refreshed without loading unrelated branches.

---

## Open in File Manager

The selected Operation Target can be opened directly from Documents Organizer.

Use:

```text
Open Selected
```

or right-click a folder in the Folder Browser and choose:

```text
Open in File Manager
```

On Windows, the folder opens in File Explorer.

The underlying file-manager integration is written with cross-platform support in mind.

---

## Activity Log

Documents Organizer includes a timestamped Activity Log.

Example:

```text
[14:32:18] Documents Organizer v0.2.0 started.
[14:32:20] Selected folder: C:\Documents
[14:32:23] Organizing: C:\Documents
[14:32:24] Organized 4 pdf files.
[14:32:24] Organized 2 jpg files.
[14:32:24] Organization complete. 6 files moved.
```

The log reports:

- application startup
- folder selection
- operation start
- organization summaries
- flatten summaries
- skipped files
- operation failures
- cancellation requests
- operation completion

Use **Clear Log** to reset the current Activity Log.

---

## System Tray

Documents Organizer can be explicitly minimized to the system tray using:

```text
File → Minimize to Tray
```

The tray menu provides:

```text
Show
Quit
```

**Show** restores the application window.

**Quit** closes Documents Organizer.

Clicking the normal Windows close button exits the application rather than silently minimizing it to the tray.

---

## File Safety

Documents Organizer performs real filesystem operations that move files and modify directory structures.

v0.2.0 contains several protections intended to make these operations safer:

- Existing destination files are not intentionally overwritten.
- Duplicate filenames receive numbered suffixes.
- Files without extensions are supported.
- Common operating-system metadata files are ignored.
- Organizer-generated files are detected to prevent repeated reorganization.
- Flattening only processes supported organizer-generated date/type structures.
- Directory cleanup removes only directories that are actually empty.
- Unexpected contents prevent directories from being removed.
- Original source directories are preserved.
- Concurrent organize and flatten operations are prevented.
- Filesystem operations run outside the Tkinter UI thread.
- Flatten operations support cancellation.
- Automated workflow tests verify organize-to-flatten round trips.

Ignored system metadata files currently include:

```text
.DS_Store
Thumbs.db
```

### Important

No filesystem utility can eliminate every possible risk.

Before using Documents Organizer on important files:

1. Keep an appropriate backup.
2. Test the application on a disposable or sample directory first.
3. Verify the selected Root Folder and Operation Target.
4. Avoid manually changing the same files while an operation is running.
5. Review the Activity Log after an operation completes.

---

## Repeated Operations

Documents Organizer is designed to make repeated operations safe.

Running **Organize** again against an already organized directory should not create an increasingly nested organization structure.

Running **Flatten** against a directory that has already been flattened should complete without moving unrelated root files.

These behaviors are covered by automated workflow tests.

---

## Project Structure

v0.2.0 separates filesystem operations, application coordination, presentation logic, and user-interface components.

```text
Documents-Organizer/
├── documents_organizer/
│   ├── __init__.py
│   ├── app.py
│   ├── filesystem.py
│   ├── platform_utils.py
│   ├── resources.py
│   ├── settings.py
│   │
│   ├── controllers/
│   │   ├── __init__.py
│   │   └── operation_controller.py
│   │
│   ├── presenters/
│   │   ├── __init__.py
│   │   └── operation_presenter.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── flattener.py
│   │   └── organizer.py
│   │
│   └── ui/
│       ├── __init__.py
│       ├── dialogs.py
│       ├── main_window.py
│       ├── styles.py
│       ├── tray_manager.py
│       │
│       └── components/
│           ├── __init__.py
│           ├── activity_log.py
│           ├── folder_browser.py
│           ├── folder_summary.py
│           ├── header.py
│           ├── menu_bar.py
│           ├── status_bar.py
│           └── toolbar.py
│
├── images/
├── tests/
├── main.py
├── pyproject.toml
├── requirements.txt
├── README.md
└── LICENSE
```

---

## Architecture

### Services

Filesystem operations are implemented under:

```text
documents_organizer/services/
```

The main services are:

```text
organizer.py
flattener.py
```

They perform filesystem operations without depending on Tkinter.

---

### Operation Controller

Background operation coordination lives in:

```text
documents_organizer/controllers/operation_controller.py
```

The Operation Controller manages:

- organizer worker threads
- flattener worker threads
- operation lifecycle
- busy state
- flatten cancellation
- worker result dispatch
- prevention of concurrent filesystem operations
- clean controller shutdown

---

### Presenters

Operation result formatting lives in:

```text
documents_organizer/presenters/operation_presenter.py
```

The presenter converts organizer and flattener results into user-facing log and status messages.

It does not manipulate Tkinter widgets directly.

---

### UI Components

Reusable interface components live under:

```text
documents_organizer/ui/components/
```

These include:

```text
ActivityLog
FolderBrowser
FolderSummary
Header
MenuBar
StatusBar
Toolbar
```

`MainWindow` coordinates these components rather than implementing their internal behavior.

---

### System Tray

System tray integration is isolated in:

```text
documents_organizer/ui/tray_manager.py
```

This keeps `pystray` implementation details outside the main application window.

---

### Styles

Tkinter/ttk style configuration is centralized in:

```text
documents_organizer/ui/styles.py
```

---

## Testing

Documents Organizer includes automated tests covering both individual application components and complete filesystem workflows.

Run the complete test suite:

```powershell
python -m pytest
```

Run with verbose output:

```powershell
python -m pytest -v
```

Compile-check the application:

```powershell
python -m compileall main.py documents_organizer
```

A useful pre-commit check is:

```powershell
python -m compileall main.py documents_organizer
python -m pytest
```

---

## Test Coverage

The v0.2.0 test suite covers areas including:

- safe filesystem moves
- destination collision handling
- numbered duplicate filenames
- ignored system files
- modified-date organization
- extension/type organization
- extensionless files
- nested file centralization
- already-organized file detection
- flattening
- safe empty-directory cleanup
- flatten cancellation
- operation controller state
- concurrent operation prevention
- worker result dispatch
- operation presenter output
- resource path resolution
- lazy-loaded folder browsing
- on-demand directory expansion
- nested selection restoration
- deleted-selection fallback
- complete organize-to-flatten workflows
- duplicate preservation across round trips
- extensionless file preservation across round trips
- repeated organize safety
- repeated flatten safety

Filesystem tests use temporary directories rather than modifying real user folders.

---

## Running a Packaged Release

Packaged Windows releases are planned to be made available through the project's GitHub Releases page:

[Documents Organizer Releases](https://github.com/DOS1986/Documents-Organizer/releases)

Until an official v0.2.0 executable is published, Documents Organizer can be run directly from source.

---

## Packaging Status

The v0.2.0 application code and test suite are being prepared for packaged Windows distribution.

The current source entry point is:

```powershell
python main.py
```

PyInstaller packaging and automated build workflows are planned as part of the v0.2.0 release process.

Do not assume a prebuilt binary is available until it appears on the GitHub Releases page.

---

## Current Platform Support

v0.2.0 development and release testing are currently focused on:

```text
Windows
```

Some application infrastructure is already implemented with cross-platform support in mind, including file-manager launching and packaged-resource handling.

Linux and macOS packaged builds have not yet completed validation and should not currently be considered officially supported.

---

## Troubleshooting

If Documents Organizer does not behave as expected:

- Review the Activity Log for errors.
- Confirm that the required dependencies are installed.
- Verify that the selected directory still exists.
- Confirm that your user account has permission to read and modify the selected directory.
- Check whether files are locked by another application.
- Try reproducing the issue using a small disposable directory.
- Run the automated test suite if working from source.
- Review existing GitHub issues to see whether the problem has already been reported.

For source installations, useful diagnostic commands include:

```powershell
python -m compileall main.py documents_organizer
python -m pytest -v
python main.py
```

---

## Roadmap

Potential future improvements include:

- Dry-run / preview mode before moving files
- Operation manifests
- Full undo support
- Original-location restoration
- Optional cleanup of original empty source directories
- Configurable organization strategies
- Configurable organization rules
- Additional file metadata options
- Expanded cross-platform testing
- Linux packaging
- macOS packaging
- Automated release builds
- Additional packaged release formats

---

## Contributing

Contributions, bug reports, and suggestions are welcome.

If you would like to contribute:

1. Fork the repository.
2. Create a branch for your change.
3. Install the development dependencies.
4. Make your changes.
5. Run the complete test suite.
6. Confirm the application still launches correctly.
7. Submit a pull request describing what changed and why.

Before submitting a pull request, run:

```powershell
python -m compileall main.py documents_organizer
python -m pytest
```

---

## Issues

Found a bug or have an idea for an improvement?

[Open an issue](https://github.com/DOS1986/Documents-Organizer/issues).

When reporting a bug, please include:

- What you were trying to do
- What happened
- What you expected to happen
- Steps that reproduce the issue
- Your operating system
- Your Python version if running from source
- Any relevant Activity Log output

Please avoid including private file names, personal directory paths, or other sensitive information in public issue reports.

---

## License

Documents Organizer is licensed under the [MIT License](LICENSE).

---

## Disclaimer

Documents Organizer is provided as-is without warranty.

The application performs filesystem operations that may move files and modify directory structures.

Users are responsible for maintaining appropriate backups and verifying the selected directory before performing an operation.

See the [MIT License](LICENSE) for the project's licensing terms.

---

## Author

Created by [David O. Southwood](https://davidosouthwood.com).

- [Website](https://davidosouthwood.com)
- [GitHub](https://github.com/DOS1986)
- [LinkedIn](https://www.linkedin.com/in/davidsouthwood/)