import tempfile
from pathlib import Path
from project import scan_files, organize_by_sufix, get_default_path


def test_get_default_path_fallback():
    path = get_default_path()
    assert isinstance(path, Path)
    assert path.exists()


def test_scan_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "file.pdf").touch()
        (path / "doc.docx").touch()

        result = scan_files(path)
        assert "file.pdf" in result
        assert "doc.docx" in result

def test_organize_by_sufix():
    from data_dict import data_dict

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "file.pdf").touch()
        (path / "doc.docx").touch()

        files = ["file.pdf", "doc.docx"]
        organize_by_sufix(files, path)

        for f in files:
            suffix = Path(f).suffix
            folder = next(d["Folder"] for d in data_dict if suffix in d["Suffixes"])
            expected_path = path / "Documents" / folder / f
            assert expected_path.exists()
