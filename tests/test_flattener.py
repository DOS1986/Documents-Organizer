import threading
from pathlib import Path

import pytest

from documents_organizer.services.flattener import (
    flatten_directory,
    is_date_directory,
)


TEST_DATE = "2026-08-25"


def test_flatten_directory_moves_files_back_to_root(
    tmp_path: Path,
):
    pdf_directory = (
        tmp_path
        / TEST_DATE
        / "pdf"
    )

    pdf_directory.mkdir(
        parents=True
    )

    source = (
        pdf_directory
        / "report.pdf"
    )

    source.write_text("report")

    result = flatten_directory(
        tmp_path
    )

    destination = (
        tmp_path
        / "report.pdf"
    )

    assert result.moved == 1
    assert result.skipped == 0
    assert result.failed == 0
    assert not result.cancelled

    assert destination.exists()
    assert destination.read_text() == (
        "report"
    )

    assert not source.exists()


def test_flatten_directory_handles_multiple_file_types(
    tmp_path: Path,
):
    pdf_directory = (
        tmp_path
        / TEST_DATE
        / "pdf"
    )

    jpg_directory = (
        tmp_path
        / TEST_DATE
        / "jpg"
    )

    pdf_directory.mkdir(
        parents=True
    )

    jpg_directory.mkdir(
        parents=True
    )

    report = (
        pdf_directory
        / "report.pdf"
    )

    image = (
        jpg_directory
        / "photo.jpg"
    )

    report.write_text("report")
    image.write_text("photo")

    result = flatten_directory(
        tmp_path
    )

    assert result.moved == 2

    assert result.by_extension == {
        "pdf": 1,
        "jpg": 1,
    }

    assert (
        tmp_path / "report.pdf"
    ).exists()

    assert (
        tmp_path / "photo.jpg"
    ).exists()


def test_flatten_directory_preserves_duplicate_names(
    tmp_path: Path,
):
    first_date = (
        tmp_path
        / "2026-08-24"
        / "pdf"
    )

    second_date = (
        tmp_path
        / "2026-08-25"
        / "pdf"
    )

    first_date.mkdir(
        parents=True
    )

    second_date.mkdir(
        parents=True
    )

    first = (
        first_date
        / "report.pdf"
    )

    second = (
        second_date
        / "report.pdf"
    )

    first.write_text("first")
    second.write_text("second")

    result = flatten_directory(
        tmp_path
    )

    original = (
        tmp_path
        / "report.pdf"
    )

    renamed = (
        tmp_path
        / "report (1).pdf"
    )

    assert result.moved == 2

    assert original.exists()
    assert renamed.exists()

    assert {
        original.read_text(),
        renamed.read_text(),
    } == {
        "first",
        "second",
    }


def test_flatten_directory_does_not_overwrite_existing_root_file(
    tmp_path: Path,
):
    existing = (
        tmp_path
        / "report.pdf"
    )

    existing.write_text(
        "existing"
    )

    organized_directory = (
        tmp_path
        / TEST_DATE
        / "pdf"
    )

    organized_directory.mkdir(
        parents=True
    )

    source = (
        organized_directory
        / "report.pdf"
    )

    source.write_text(
        "organized"
    )

    result = flatten_directory(
        tmp_path
    )

    renamed = (
        tmp_path
        / "report (1).pdf"
    )

    assert result.moved == 1

    assert existing.read_text() == (
        "existing"
    )

    assert renamed.read_text() == (
        "organized"
    )


def test_flatten_directory_handles_other_files(
    tmp_path: Path,
):
    other_directory = (
        tmp_path
        / TEST_DATE
        / "other"
    )

    other_directory.mkdir(
        parents=True
    )

    source = (
        other_directory
        / "README"
    )

    source.write_text("readme")

    result = flatten_directory(
        tmp_path
    )

    destination = (
        tmp_path
        / "README"
    )

    assert result.moved == 1
    assert destination.exists()


def test_flatten_directory_skips_file_in_wrong_type_directory(
    tmp_path: Path,
):
    pdf_directory = (
        tmp_path
        / TEST_DATE
        / "pdf"
    )

    pdf_directory.mkdir(
        parents=True
    )

    source = (
        pdf_directory
        / "photo.jpg"
    )

    source.write_text("photo")

    result = flatten_directory(
        tmp_path
    )

    assert result.moved == 0
    assert result.skipped == 1

    assert source.exists()

    assert not (
        tmp_path
        / "photo.jpg"
    ).exists()


def test_flatten_directory_ignores_normal_directories(
    tmp_path: Path,
):
    normal_directory = (
        tmp_path
        / "project"
        / "pdf"
    )

    normal_directory.mkdir(
        parents=True
    )

    source = (
        normal_directory
        / "report.pdf"
    )

    source.write_text("report")

    result = flatten_directory(
        tmp_path
    )

    assert result.moved == 0

    assert source.exists()


def test_flatten_directory_ignores_invalid_date_directory(
    tmp_path: Path,
):
    invalid_directory = (
        tmp_path
        / "2026-99-99"
        / "pdf"
    )

    invalid_directory.mkdir(
        parents=True
    )

    source = (
        invalid_directory
        / "report.pdf"
    )

    source.write_text("report")

    result = flatten_directory(
        tmp_path
    )

    assert result.moved == 0
    assert source.exists()


def test_flatten_directory_removes_empty_organizer_directories(
    tmp_path: Path,
):
    directory = (
        tmp_path
        / TEST_DATE
        / "pdf"
    )

    directory.mkdir(
        parents=True
    )

    source = (
        directory
        / "report.pdf"
    )

    source.write_text("report")

    result = flatten_directory(
        tmp_path
    )

    assert result.moved == 1

    assert not (
        tmp_path
        / TEST_DATE
        / "pdf"
    ).exists()

    assert not (
        tmp_path
        / TEST_DATE
    ).exists()

    assert (
        result.directories_removed
        == 2
    )


def test_flatten_directory_does_not_remove_directory_with_unexpected_content(
    tmp_path: Path,
):
    pdf_directory = (
        tmp_path
        / TEST_DATE
        / "pdf"
    )

    unexpected_directory = (
        pdf_directory
        / "keep-me"
    )

    unexpected_directory.mkdir(
        parents=True
    )

    source = (
        pdf_directory
        / "report.pdf"
    )

    source.write_text("report")

    unexpected_file = (
        unexpected_directory
        / "something.txt"
    )

    unexpected_file.write_text(
        "keep this"
    )

    result = flatten_directory(
        tmp_path
    )

    assert result.moved == 1

    assert unexpected_file.exists()

    assert pdf_directory.exists()

    assert (
        tmp_path
        / TEST_DATE
    ).exists()


def test_flatten_directory_respects_cancellation(
    tmp_path: Path,
):
    directory = (
        tmp_path
        / TEST_DATE
        / "pdf"
    )

    directory.mkdir(
        parents=True
    )

    source = (
        directory
        / "report.pdf"
    )

    source.write_text("report")

    cancel_event = (
        threading.Event()
    )

    cancel_event.set()

    result = flatten_directory(
        tmp_path,
        cancel_event=cancel_event,
    )

    assert result.cancelled
    assert result.moved == 0
    assert source.exists()


def test_flatten_directory_rejects_missing_directory(
    tmp_path: Path,
):
    missing = (
        tmp_path
        / "missing"
    )

    with pytest.raises(
        FileNotFoundError
    ):
        flatten_directory(
            missing
        )


def test_flatten_directory_rejects_file_as_root(
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
        flatten_directory(
            file_path
        )


def test_is_date_directory_accepts_valid_iso_date(
    tmp_path: Path,
):
    directory = (
        tmp_path
        / TEST_DATE
    )

    directory.mkdir()

    assert is_date_directory(
        directory
    )


def test_is_date_directory_rejects_invalid_date(
    tmp_path: Path,
):
    directory = (
        tmp_path
        / "2026-99-99"
    )

    directory.mkdir()

    assert not is_date_directory(
        directory
    )


def test_is_date_directory_rejects_normal_folder_name(
    tmp_path: Path,
):
    directory = (
        tmp_path
        / "documents"
    )

    directory.mkdir()

    assert not is_date_directory(
        directory
    )