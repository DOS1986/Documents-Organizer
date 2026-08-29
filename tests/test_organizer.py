import datetime
import os
from pathlib import Path

import pytest

from documents_organizer.services.organizer import (
    get_extension_name,
    is_already_organized,
    organize_directory,
)


TEST_DATE = "2026-08-25"


def set_test_modified_date(path: Path) -> None:
    """Give a test file a deterministic modification date."""
    timestamp = datetime.datetime(
        2026,
        8,
        25,
        12,
        0,
        0,
    ).timestamp()

    os.utime(
        path,
        (
            timestamp,
            timestamp,
        ),
    )


def test_organize_directory_moves_files_by_date_then_extension(
    tmp_path: Path,
):
    report = tmp_path / "report.pdf"
    image = tmp_path / "photo.jpg"

    report.write_text("report")
    image.write_text("image")

    set_test_modified_date(report)
    set_test_modified_date(image)

    result = organize_directory(
        tmp_path
    )

    expected_report = (
        tmp_path
        / TEST_DATE
        / "pdf"
        / "report.pdf"
    )

    expected_image = (
        tmp_path
        / TEST_DATE
        / "jpg"
        / "photo.jpg"
    )

    assert result.moved == 2
    assert result.skipped == 0
    assert result.failed == 0

    assert result.by_extension == {
        "pdf": 1,
        "jpg": 1,
    }

    assert expected_report.exists()
    assert expected_image.exists()

    assert not report.exists()
    assert not image.exists()


def test_nested_files_are_centralized_into_selected_root(
    tmp_path: Path,
):
    project = tmp_path / "project"
    project.mkdir()

    source = project / "photo.jpg"
    source.write_text("image")

    set_test_modified_date(source)

    result = organize_directory(
        tmp_path
    )

    destination = (
        tmp_path
        / TEST_DATE
        / "jpg"
        / "photo.jpg"
    )

    assert result.moved == 1
    assert destination.exists()
    assert not source.exists()


def test_files_from_multiple_nested_directories_are_centralized(
    tmp_path: Path,
):
    first_directory = tmp_path / "project-a"
    second_directory = tmp_path / "project-b"

    first_directory.mkdir()
    second_directory.mkdir()

    first_file = first_directory / "one.pdf"
    second_file = second_directory / "two.pdf"

    first_file.write_text("one")
    second_file.write_text("two")

    set_test_modified_date(first_file)
    set_test_modified_date(second_file)

    result = organize_directory(
        tmp_path
    )

    destination_directory = (
        tmp_path
        / TEST_DATE
        / "pdf"
    )

    assert result.moved == 2
    assert (destination_directory / "one.pdf").exists()
    assert (destination_directory / "two.pdf").exists()


def test_organize_directory_handles_files_without_extension(
    tmp_path: Path,
):
    source = tmp_path / "README"
    source.write_text("readme")

    set_test_modified_date(source)

    result = organize_directory(
        tmp_path
    )

    destination = (
        tmp_path
        / TEST_DATE
        / "other"
        / "README"
    )

    assert result.moved == 1

    assert result.by_extension == {
        "other": 1
    }

    assert destination.exists()


def test_organize_directory_ignores_system_files(
    tmp_path: Path,
):
    ds_store = tmp_path / ".DS_Store"
    thumbs = tmp_path / "Thumbs.db"

    ds_store.write_text("system")
    thumbs.write_text("system")

    result = organize_directory(
        tmp_path
    )

    assert result.moved == 0
    assert result.skipped == 2
    assert result.failed == 0

    assert ds_store.exists()
    assert thumbs.exists()


def test_organizer_does_not_overwrite_existing_file(
    tmp_path: Path,
):
    source = tmp_path / "report.pdf"
    source.write_text("new report")

    set_test_modified_date(source)

    destination_directory = (
        tmp_path
        / TEST_DATE
        / "pdf"
    )

    destination_directory.mkdir(
        parents=True
    )

    existing = (
        destination_directory
        / "report.pdf"
    )

    existing.write_text(
        "existing report"
    )

    result = organize_directory(
        tmp_path
    )

    renamed = (
        destination_directory
        / "report (1).pdf"
    )

    assert result.moved == 1

    assert existing.read_text() == (
        "existing report"
    )

    assert renamed.read_text() == (
        "new report"
    )


def test_duplicate_names_from_different_folders_are_preserved(
    tmp_path: Path,
):
    first_directory = tmp_path / "project-a"
    second_directory = tmp_path / "project-b"

    first_directory.mkdir()
    second_directory.mkdir()

    first = first_directory / "report.pdf"
    second = second_directory / "report.pdf"

    first.write_text("first")
    second.write_text("second")

    set_test_modified_date(first)
    set_test_modified_date(second)

    result = organize_directory(
        tmp_path
    )

    destination_directory = (
        tmp_path
        / TEST_DATE
        / "pdf"
    )

    original_name = (
        destination_directory
        / "report.pdf"
    )

    renamed = (
        destination_directory
        / "report (1).pdf"
    )

    assert result.moved == 2

    assert original_name.exists()
    assert renamed.exists()

    assert {
        original_name.read_text(),
        renamed.read_text(),
    } == {
        "first",
        "second",
    }


def test_running_organizer_twice_does_not_reorganize_files(
    tmp_path: Path,
):
    source = tmp_path / "report.pdf"
    source.write_text("report")

    set_test_modified_date(source)

    first_result = organize_directory(
        tmp_path
    )

    second_result = organize_directory(
        tmp_path
    )

    organized_file = (
        tmp_path
        / TEST_DATE
        / "pdf"
        / "report.pdf"
    )

    nested_duplicate = (
        tmp_path
        / TEST_DATE
        / "pdf"
        / TEST_DATE
        / "pdf"
        / "report.pdf"
    )

    assert first_result.moved == 1

    assert second_result.moved == 0
    assert second_result.skipped == 1

    assert organized_file.exists()
    assert not nested_duplicate.exists()


def test_get_extension_name_returns_extension_without_dot():
    assert (
        get_extension_name(
            Path("report.PDF")
        )
        == "pdf"
    )


def test_get_extension_name_returns_other_for_extensionless_file():
    assert (
        get_extension_name(
            Path("README")
        )
        == "other"
    )


def test_is_already_organized_detects_date_type_layout(
    tmp_path: Path,
):
    organized_directory = (
        tmp_path
        / TEST_DATE
        / "pdf"
    )

    organized_directory.mkdir(
        parents=True
    )

    file_path = (
        organized_directory
        / "report.pdf"
    )

    file_path.write_text("report")

    assert is_already_organized(
        file_path,
        tmp_path,
    )


def test_is_already_organized_rejects_old_extension_date_layout(
    tmp_path: Path,
):
    old_directory = (
        tmp_path
        / "pdf"
        / TEST_DATE
    )

    old_directory.mkdir(
        parents=True
    )

    file_path = (
        old_directory
        / "report.pdf"
    )

    file_path.write_text("report")

    assert not is_already_organized(
        file_path,
        tmp_path,
    )


def test_is_already_organized_rejects_normal_nested_file(
    tmp_path: Path,
):
    project = tmp_path / "project"
    project.mkdir()

    file_path = (
        project
        / "report.pdf"
    )

    file_path.write_text("report")

    assert not is_already_organized(
        file_path,
        tmp_path,
    )


def test_organize_directory_rejects_missing_directory(
    tmp_path: Path,
):
    missing = (
        tmp_path
        / "does-not-exist"
    )

    with pytest.raises(
        FileNotFoundError
    ):
        organize_directory(
            missing
        )


def test_organize_directory_rejects_file_as_root(
    tmp_path: Path,
):
    file_path = (
        tmp_path
        / "file.txt"
    )

    file_path.write_text("test")

    with pytest.raises(
        NotADirectoryError
    ):
        organize_directory(
            file_path
        )