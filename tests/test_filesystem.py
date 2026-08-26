from pathlib import Path

from documents_organizer.filesystem import (
    get_unique_destination,
    move_file_safely,
    should_ignore_file,
)


def test_unique_destination_returns_original_when_available(tmp_path: Path):
    destination = tmp_path / "report.pdf"

    result = get_unique_destination(destination)

    assert result == destination


def test_unique_destination_adds_number_when_file_exists(tmp_path: Path):
    original = tmp_path / "report.pdf"
    original.write_text("original")

    result = get_unique_destination(original)

    assert result == tmp_path / "report (1).pdf"


def test_unique_destination_increments_until_available(tmp_path: Path):
    (tmp_path / "report.pdf").write_text("original")
    (tmp_path / "report (1).pdf").write_text("duplicate")
    (tmp_path / "report (2).pdf").write_text("duplicate")

    result = get_unique_destination(tmp_path / "report.pdf")

    assert result == tmp_path / "report (3).pdf"


def test_move_file_safely_moves_file(tmp_path: Path):
    source = tmp_path / "source" / "report.pdf"
    source.parent.mkdir()
    source.write_text("test file")

    destination = tmp_path / "destination" / "report.pdf"

    result = move_file_safely(source, destination)

    assert result == destination
    assert destination.exists()
    assert destination.read_text() == "test file"
    assert not source.exists()


def test_move_file_safely_does_not_overwrite_existing_file(tmp_path: Path):
    source = tmp_path / "source" / "report.pdf"
    source.parent.mkdir()
    source.write_text("new file")

    destination = tmp_path / "destination" / "report.pdf"
    destination.parent.mkdir()
    destination.write_text("existing file")

    result = move_file_safely(source, destination)

    assert result == tmp_path / "destination" / "report (1).pdf"

    assert destination.read_text() == "existing file"
    assert result.read_text() == "new file"

    assert not source.exists()


def test_move_file_safely_rejects_missing_source(tmp_path: Path):
    source = tmp_path / "missing.pdf"
    destination = tmp_path / "destination.pdf"

    try:
        move_file_safely(source, destination)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_should_ignore_ds_store():
    assert should_ignore_file(Path(".DS_Store"))


def test_should_ignore_thumbs_db():
    assert should_ignore_file(Path("Thumbs.db"))


def test_normal_file_is_not_ignored():
    assert not should_ignore_file(Path("report.pdf"))