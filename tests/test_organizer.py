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


def test_organize_directory_moves_files_by_extension_and_date(
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
        / "pdf"
        / TEST_DATE
        / "report.pdf"
    )

    expected_image = (
        tmp_path
        / "jpg"
        / TEST_DATE
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


def test_organize_directory_preserves_nested_parent_directory(
    tmp_path: Path,
):
    nested = tmp_path / "project"
    nested.mkdir()

    source = nested / "photo.jpg"
    source.write_text("image")

    set_test_modified_date(source)

    result = organize_directory(
        tmp_path
    )

    destination = (
        nested
        / "jpg"
        / TEST_DATE
        / "photo.jpg"
    )

    assert result.moved == 1
    assert destination.exists()


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
        / "other"
        / TEST_DATE
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


def test_organize_directory_does_not_overwrite_existing_file(
    tmp_path: Path,
):
    source = tmp_path / "report.pdf"
    source.write_text("new report")

    set_test_modified_date(source)

    destination_directory = (
        tmp_path
        / "pdf"
        / TEST_DATE
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
        / "pdf"
        / TEST_DATE
        / "report.pdf"
    )

    nested_duplicate = (
        tmp_path
        / "pdf"
        / TEST_DATE
        / "pdf"
        / TEST_DATE
        / "report.pdf"
    )

    assert first_result.moved == 1

    assert second_result.moved == 0
    assert second_result.skipped == 1

    assert organized_file.exists()
    assert not nested_duplicate.exists()


def test_get_extension_name_returns_other_for_extensionless_file():
    assert (
        get_extension_name(
            Path("README")
        )
        == "other"
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
    file_path = tmp_path / "file.txt"
    file_path.write_text("test")

    with pytest.raises(
        NotADirectoryError
    ):
        organize_directory(
            file_path
        )


def test_is_already_organized_detects_organized_file(
    tmp_path: Path,
):
    organized_directory = (
        tmp_path
        / "pdf"
        / TEST_DATE
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
        file_path
    )


def test_is_already_organized_rejects_normal_file(
    tmp_path: Path,
):
    file_path = (
        tmp_path
        / "report.pdf"
    )

    file_path.write_text("report")

    assert not is_already_organized(
        file_path
    )