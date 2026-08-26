from __future__ import annotations

from pathlib import Path

from documents_organizer.services.flattener import flatten_directory
from documents_organizer.services.organizer import organize_directory


def test_organize_then_flatten_round_trip(
    tmp_path: Path,
) -> None:
    """Files should survive an organize/flatten round trip."""
    pdf_file = tmp_path / "report.pdf"
    image_file = tmp_path / "photo.jpg"

    nested_folder = tmp_path / "project"
    nested_folder.mkdir()

    text_file = nested_folder / "notes.txt"

    pdf_file.write_text(
        "PDF contents",
        encoding="utf-8",
    )

    image_file.write_bytes(
        b"fake-image-data"
    )

    text_file.write_text(
        "Project notes",
        encoding="utf-8",
    )

    organize_result = organize_directory(
        tmp_path
    )

    assert organize_result.moved == 3
    assert organize_result.failed == 0

    # Original files should have moved.
    assert not pdf_file.exists()
    assert not image_file.exists()
    assert not text_file.exists()

    # Empty original source directories are intentionally preserved.
    assert nested_folder.exists()
    assert nested_folder.is_dir()

    organized_files = [
        path
        for path in tmp_path.rglob("*")
        if path.is_file()
    ]

    assert len(organized_files) == 3

    flatten_result = flatten_directory(
        tmp_path
    )

    assert flatten_result.moved == 3
    assert flatten_result.failed == 0
    assert flatten_result.cancelled is False

    assert (
        tmp_path
        / "report.pdf"
    ).read_text(
        encoding="utf-8"
    ) == "PDF contents"

    assert (
        tmp_path
        / "photo.jpg"
    ).read_bytes() == b"fake-image-data"

    assert (
        tmp_path
        / "notes.txt"
    ).read_text(
        encoding="utf-8"
    ) == "Project notes"

    # The original nested directory remains because
    # it was not created by the organizer.
    assert nested_folder.exists()


def test_round_trip_preserves_duplicate_file_contents(
    tmp_path: Path,
) -> None:
    """Duplicate filenames should survive without overwriting one another."""
    first_folder = tmp_path / "first"
    second_folder = tmp_path / "second"

    first_folder.mkdir()
    second_folder.mkdir()

    first_file = first_folder / "report.pdf"
    second_file = second_folder / "report.pdf"

    first_file.write_text(
        "first report",
        encoding="utf-8",
    )

    second_file.write_text(
        "second report",
        encoding="utf-8",
    )

    organize_result = organize_directory(
        tmp_path
    )

    assert organize_result.moved == 2
    assert organize_result.failed == 0

    flatten_result = flatten_directory(
        tmp_path
    )

    assert flatten_result.moved == 2
    assert flatten_result.failed == 0

    root_pdfs = sorted(
        tmp_path.glob("*.pdf")
    )

    assert len(root_pdfs) == 2

    assert {
        path.read_text(
            encoding="utf-8"
        )
        for path in root_pdfs
    } == {
        "first report",
        "second report",
    }


def test_round_trip_preserves_extensionless_file(
    tmp_path: Path,
) -> None:
    """Extensionless files should survive the full workflow."""
    source = tmp_path / "LICENSE"

    source.write_text(
        "MIT License",
        encoding="utf-8",
    )

    organize_result = organize_directory(
        tmp_path
    )

    assert organize_result.moved == 1
    assert organize_result.failed == 0

    assert not source.exists()

    organized_files = [
        path
        for path in tmp_path.rglob("*")
        if path.is_file()
    ]

    assert len(organized_files) == 1
    assert organized_files[0].name == "LICENSE"

    flatten_result = flatten_directory(
        tmp_path
    )

    assert flatten_result.moved == 1
    assert flatten_result.failed == 0

    restored = tmp_path / "LICENSE"

    assert restored.exists()

    assert restored.read_text(
        encoding="utf-8"
    ) == "MIT License"


def test_second_organize_does_not_move_already_organized_files(
    tmp_path: Path,
) -> None:
    """Running the organizer twice should not reorganize its own output."""
    source = tmp_path / "document.pdf"

    source.write_text(
        "document",
        encoding="utf-8",
    )

    first_result = organize_directory(
        tmp_path
    )

    assert first_result.moved == 1

    organized_files_before = {
        path.relative_to(tmp_path)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    second_result = organize_directory(
        tmp_path
    )

    organized_files_after = {
        path.relative_to(tmp_path)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    assert second_result.moved == 0
    assert second_result.failed == 0

    assert (
        organized_files_after
        == organized_files_before
    )


def test_second_flatten_is_safe(
    tmp_path: Path,
) -> None:
    """Flattening an already flattened directory should be harmless."""
    source = tmp_path / "document.pdf"

    source.write_text(
        "document",
        encoding="utf-8",
    )

    organize_directory(
        tmp_path
    )

    first_result = flatten_directory(
        tmp_path
    )

    assert first_result.moved == 1

    second_result = flatten_directory(
        tmp_path
    )

    assert second_result.moved == 0
    assert second_result.failed == 0
    assert second_result.cancelled is False

    assert source.exists()

    assert source.read_text(
        encoding="utf-8"
    ) == "document"