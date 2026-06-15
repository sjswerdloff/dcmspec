"""Tests for the PDFDocHandler class in dcmspec.pdf_doc_handler."""
import pytest
from unittest.mock import MagicMock
import logging

from dcmspec.config import Config
from dcmspec.pdf_doc_handler import PDFDocHandler


def make_handler():
    """Test helper to create a PDFDocHandler with a real Config and a test logger."""
    return PDFDocHandler(config=Config(), logger=logging.getLogger("test"))

def test_load_document_happy_path(monkeypatch, patch_dirs):
    """Test load_document returns expected result when all arguments are provided and file exists."""
    # Arrange
    handler = make_handler()
    cache_file_name = "test.pdf"
    url = "http://example.com/file.pdf"
    page_numbers = [1]
    table_indices = [(1, 0)]
    table_id = "T-1"
    dummy_pdf = MagicMock()
    dummy_pdf.pages = [MagicMock()]
    dummy_pdf.close = MagicMock()
    dummy_tables = [
        {"page": 1, "index": 0, "header": ["A", "B"], "data": [["C", "D"]]}
    ]
    dummy_concat = {"header": ["A", "B"], "data": [["C", "D"]], "table_id": table_id}

    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("pdfplumber.open", lambda path: dummy_pdf)
    monkeypatch.setattr(handler, "extract_tables_pdfplumber", lambda pdf, pn: dummy_tables)
    monkeypatch.setattr(handler, "concat_tables", lambda tables, table_id=None: dummy_concat)

    # Act
    result = handler.load_document(
        cache_file_name=cache_file_name,
        url=url,
        force_download=False,
        page_numbers=page_numbers,
        table_indices=table_indices,
        table_id=table_id,
    )

    # Assert
    assert result == dummy_concat

def test_load_document_happy_path_camelot(monkeypatch, patch_dirs):
    """Test load_document returns expected result with Camelot extractor."""
    handler = make_handler()
    handler.extractor = "camelot"
    cache_file_name = "test.pdf"
    url = "http://example.com/file.pdf"
    page_numbers = [1]
    table_indices = [(1, 0)]
    table_id = "T-1"
    dummy_tables = [
        {"page": 1, "index": 0, "header": ["A", "B"], "data": [["C", "D"]]}
    ]
    dummy_concat = {"header": ["A", "B"], "data": [["C", "D"]], "table_id": table_id}

    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr(handler, "extract_tables_camelot", lambda path, pn: dummy_tables)
    monkeypatch.setattr(handler, "concat_tables", lambda tables, table_id=None: dummy_concat)

    result = handler.load_document(
        cache_file_name=cache_file_name,
        url=url,
        force_download=False,
        page_numbers=page_numbers,
        table_indices=table_indices,
        table_id=table_id,
    )

    assert result == dummy_concat

def test_load_document_download(monkeypatch, patch_dirs):
    """Test load_document triggers download if file does not exist."""
    # Arrange
    handler = make_handler()
    cache_file_name = "test.pdf"
    url = "http://example.com/file.pdf"
    page_numbers = [1]
    table_indices = [(1, 0)]
    dummy_pdf = MagicMock()
    dummy_pdf.pages = [MagicMock()]
    dummy_pdf.close = MagicMock()
    monkeypatch.setattr("os.path.exists", lambda path: False)
    monkeypatch.setattr("pdfplumber.open", lambda path: dummy_pdf)
    monkeypatch.setattr(
        handler,
        "download",
        lambda url, cache_file_name, progress_observer=None, progress_callback=None: "test.pdf"
)
    monkeypatch.setattr(handler, "extract_tables_pdfplumber", lambda pdf, pn: [])
    monkeypatch.setattr(handler, "concat_tables", lambda tables, table_id=None, pad_columns=None: {})

    # Act
    handler.load_document(
        cache_file_name=cache_file_name,
        url=url,
        force_download=False,
        page_numbers=page_numbers,
        table_indices=table_indices,
    )

def test_load_document_missing_url(monkeypatch, patch_dirs):
    """Test load_document raises ValueError if url is missing and download is needed."""
    # Arrange
    handler = make_handler()
    cache_file_name = "test.pdf"
    page_numbers = [1]
    table_indices = [(1, 0)]
    monkeypatch.setattr("os.path.exists", lambda path: False)

    # Act & Assert
    with pytest.raises(ValueError, match="URL must be provided to download the file."):
        handler.load_document(
            cache_file_name=cache_file_name,
            url=None,
            force_download=True,
            page_numbers=page_numbers,
            table_indices=table_indices,
        )

def test_load_document_missing_args(monkeypatch, patch_dirs):
    """Test load_document raises ValueError if page_numbers or table_indices are missing."""
    # Arrange
    handler = make_handler()
    cache_file_name = "test.pdf"
    url = "http://example.com/file.pdf"
    dummy_pdf = MagicMock()
    dummy_pdf.pages = [MagicMock()]
    dummy_pdf.close = MagicMock()
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("pdfplumber.open", lambda path: dummy_pdf)
    monkeypatch.setattr(handler, "extract_tables_pdfplumber", lambda pdf, pn: [])
    monkeypatch.setattr(handler, "concat_tables", lambda tables, table_id=None, pad_columns=None: {})

    # Act & Assert
    with pytest.raises(ValueError, match="page_numbers and table_indices must be provided"):
        handler.load_document(
            cache_file_name=cache_file_name,
            url=url,
            force_download=False,
            page_numbers=None,
            table_indices=None,
        )

def test_load_document_unknown_extractor(monkeypatch, patch_dirs):
    """Test load_document raises ValueError if an unknown extractor is set."""
    # Arrange
    handler = make_handler()
    handler.extractor = "unknown_extractor"
    cache_file_name = "test.pdf"
    url = "http://example.com/file.pdf"
    page_numbers = [1]
    table_indices = [(1, 0)]
    # os.path.exists must return True to avoid triggering download
    monkeypatch.setattr("os.path.exists", lambda path: True)

    # Act & Assert
    with pytest.raises(ValueError, match="Unknown extractor: unknown_extractor"):
        handler.load_document(
            cache_file_name=cache_file_name,
            url=url,
            force_download=False,
            page_numbers=page_numbers,
            table_indices=table_indices,
        )

def test_download_calls_super(monkeypatch, patch_dirs):
    """Test download calls the super().download method with correct arguments."""
    # Arrange
    handler = make_handler()
    called = {}
    def fake_super_download(url, file_path, binary, progress_observer=None, progress_callback=None):
        called["args"] = (url, file_path, binary)
        return "SAVED_PATH"
    monkeypatch.setattr("dcmspec.doc_handler.DocHandler.download", staticmethod(fake_super_download))
    url = "http://example.com/file.pdf"
    cache_file_name = "test.pdf"
    expected_path = str(patch_dirs / "cache" / "standard" / "test.pdf")

    # Act
    result = handler.download(url, cache_file_name)

    # Assert
    assert result == "SAVED_PATH"
    assert called["args"] == (url, expected_path, True)

def test_extract_tables_happy(monkeypatch, patch_dirs):
    """Test extract_tables_pdfplumber returns expected structure for multiple pages with tables."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page = MagicMock()
    dummy_pdf.pages = [dummy_page, dummy_page]
    dummy_page.extract_tables.side_effect = [
        [[["A", "B"], ["C", "D"]]],
        [[["E", "F"], ["G", "H"]]]
    ]
    # Act
    result = handler.extract_tables_pdfplumber(dummy_pdf, [1, 2])
    # Assert
    assert isinstance(result, list)
    assert result[0]["data"] == [["A", "B"], ["C", "D"]]
    assert result[1]["data"] == [["E", "F"], ["G", "H"]]
    assert result[0]["page"] == 1
    assert result[1]["page"] == 2

def test_extract_tables_empty(monkeypatch, patch_dirs):
    """Test extract_tables_pdfplumber returns empty list if no tables are found."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page = MagicMock()
    dummy_pdf.pages = [dummy_page]
    dummy_page.extract_tables.return_value = []
    # Act
    result = handler.extract_tables_pdfplumber(dummy_pdf, [1])
    # Assert
    assert result == []

def test_extract_tables_camelot_empty(monkeypatch):
    """Test extract_tables_camelot returns empty list if no tables are found."""
    # Arrange
    handler = make_handler()
    # Patch camelot.read_pdf to return an empty list
    monkeypatch.setattr("camelot.read_pdf", lambda file_path, pages, flavor, line_scale=40: [])
    # Act
    result = handler.extract_tables_camelot("dummy.pdf", [1])
    
    assert result == []

def test_extract_tables_page_num_out_of_range(monkeypatch, patch_dirs):
    """Test extract_tables_pdfplumber raises IndexError if page number is out of range."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page = MagicMock()
    dummy_pdf.pages = [dummy_page]  # Only 1 page
    # Act & Assert
    with pytest.raises(IndexError, match="Page number 2 is out of range for this PDF"):
        handler.extract_tables_pdfplumber(dummy_pdf, [2])

def test_select_tables_single_row_header():
    """Test select_tables with a single header row (rowspan=1)."""
    # Arrange
    handler = make_handler()
    # Simulate a table with a single header row and 2 data rows
    header_row = ["A", "B", "C", "D", "E"]
    data_rows = [
        ["1", "2", "3", "4", "5"],
        ["6", "7", "8", "9", "10"]
    ]
    tables = [
        {"page": 1, "index": 0, "data": [header_row] + data_rows}
    ]
    table_indices = [(1, 0)]
    table_header_rowspan = {(1, 0): 1}

    # Act
    selected = handler.select_tables(
        tables,
        table_indices=table_indices,
        table_header_rowspan=table_header_rowspan
    )

    # Assert
    merged_header = selected[0]["header"]
    # The merged header should be the same as the single header row
    assert merged_header == ["A", "B", "C", "D", "E"]
    # Data rows should be preserved
    assert selected[0]["data"][0] == ["1", "2", "3", "4", "5"]
    assert selected[0]["data"][1] == ["6", "7", "8", "9", "10"]

def test_select_tables_multirow_header_simple():
    """Test select_tables merges a simple multi-row header."""
    # Arrange
    handler = make_handler()
    # Simulate a table with a 2-row header and 2 data rows
    header_rows = [
        ["A", "", "B", "", "C"],
        ["", "D", "", "E", ""]
    ]
    data_rows = [
        ["1", "2", "3", "4", "5"],
        ["6", "7", "8", "9", "10"]
    ]
    tables = [
        {"page": 1, "index": 0, "data": header_rows + data_rows}
    ]
    table_indices = [(1, 0)]
    table_header_rowspan = {(1, 0): 2}

    # Act
    selected = handler.select_tables(
        tables,
        table_indices=table_indices,
        table_header_rowspan=table_header_rowspan
    )

    # Assert
    merged_header = selected[0]["header"]
    # The merged header should be ["A", "D", "B", "E", "C"]
    assert merged_header == ["A", "D", "B", "E", "C"]
    # Data rows should be preserved
    assert selected[0]["data"][0] == ["1", "2", "3", "4", "5"]
    assert selected[0]["data"][1] == ["6", "7", "8", "9", "10"]

def test_select_tables_raises_on_tag_in_header():
    """Fail loudly when a data row is absorbed into the header.

    Mirrors the real IHE-RO TPPC-Brachy page-35 failure: table_header_rowspan=2
    over-counts the header, so the "Application Setup Sequence" attribute row
    (tag 300A,0230) is merged into the header and silently dropped. select_tables
    must raise rather than warn-and-drop — silent attribute loss is unacceptable
    for conformance tooling.
    """
    # Arrange
    handler = make_handler()
    rows = [
        ["Attribute", "Tag", "Type", "Presence", "Specific Rules"],
        ["Application Setup Sequence", "(300A,0230)", "1", "R+*", "Number of items shall be 1."],
        [">Application Setup Type", "(300A,0232)", "1", "-*", ""],
    ]
    tables = [{"page": 35, "index": 0, "data": rows}]

    # Act / Assert
    with pytest.raises(ValueError, match=r"DICOM tag pattern"):
        handler.select_tables(
            tables,
            table_indices=[(35, 0)],
            table_header_rowspan={(35, 0): 2},
        )

def test_select_tables_skips_guard_when_not_strict():
    """strict_header_check=False opts out of the tag-in-header guard.

    Same absorbed-header input as the strict test, but the consumer has opted out:
    select_tables returns normally (the prior warn-and-continue behavior) instead of raising.
    """
    # Arrange
    handler = make_handler()
    rows = [
        ["Attribute", "Tag", "Type", "Presence", "Specific Rules"],
        ["Application Setup Sequence", "(300A,0230)", "1", "R+*", "Number of items shall be 1."],
        [">Application Setup Type", "(300A,0232)", "1", "-*", ""],
    ]
    tables = [{"page": 35, "index": 0, "data": rows}]

    # Act — opted out, so no raise
    selected = handler.select_tables(
        tables,
        table_indices=[(35, 0)],
        table_header_rowspan={(35, 0): 2},
        strict_header_check=False,
    )

    # Assert
    assert len(selected) == 1
    assert selected[0]["page"] == 35

def test_concat_tables_basic(monkeypatch, patch_dirs):
    """Test concat_tables concatenates tables with matching headers."""
    # Arrange
    handler = make_handler()
    tables = [
        {"page": 1, "index": 0, "header": ["A", "B"], "data": [["C", "D"]]},
        {"page": 2, "index": 0, "header": ["A", "B"], "data": [["E", "F"]]}
    ]
    table_indices = [(1, 0), (2, 0)]
    # Act
    result = handler.concat_tables(tables, table_indices)
    # Assert
    assert result["header"] == ["A", "B"]
    assert result["data"] == [["C", "D"], ["E", "F"]]

def test_concat_tables_pads_and_truncates_to_header(monkeypatch, patch_dirs):
    """Test concat_tables pads or truncates rows to match header length."""
    # Arrange
    handler = make_handler()
    tables = [
        {"page": 1, "index": 0, "header": ["A", "B"], "data": [["C"], ["D", "E", "F"]]},
    ]
    table_indices = [(1, 0)]
    # Act
    result = handler.concat_tables(tables, table_indices)
    # Assert
    assert result["header"] == ["A", "B"]
    # First row is padded, second row is truncated
    assert result["data"] == [["C", ""], ["D", "E"]]

def test_concat_tables_header_mismatch(monkeypatch, caplog, patch_dirs):
    """Test concat_tables logs a warning if headers do not match."""
    # Arrange
    handler = make_handler()
    tables = [
        {"page": 1, "index": 0, "header": ["A", "B"], "data": [["C", "D"]]},
        {"page": 2, "index": 0, "header": ["X", "Y"], "data": [["E", "F"]]}
    ]
    table_indices = [(1, 0), (2, 0)]
    caplog.set_level(logging.WARNING)
    # Act
    result = handler.concat_tables(tables, table_indices)
    # Assert
    assert result["header"] == ["A", "B"]
    assert result["data"] == [["C", "D"], ["E", "F"]]
    assert "Header mismatch" in caplog.text

def test_extract_notes_basic(monkeypatch, patch_dirs):
    """Test extract_notes extracts notes from PDF text."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page = MagicMock()
    dummy_page.extract_text.return_value = "Note 1: This is a note.\nSome more text\nNote 2: Second note."
    dummy_pdf.pages = [dummy_page]
    # Act
    result = handler.extract_notes(dummy_pdf, [1])
    # Assert
    assert "Note 1:" in result
    assert "Note 2:" in result
    assert result["Note 1:"]["text"].startswith("This is a note.")
    assert result["Note 2:"]["text"].startswith("Second note.")

def test_extract_notes_with_table_id(monkeypatch, patch_dirs):
    """Test extract_notes includes table_id in the result if provided."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page = MagicMock()
    dummy_page.extract_text.return_value = "Note 1: Text"
    dummy_pdf.pages = [dummy_page]
    # Act
    result = handler.extract_notes(dummy_pdf, [1], table_id="T-1")
    # Assert
    assert "Note 1:" in result
    assert result["Note 1:"]["table_id"] == "T-1"

def test_extract_notes_multi_page(monkeypatch, patch_dirs):
    """Test extract_notes can extract notes spanning multiple pages."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page1 = MagicMock()
    dummy_page2 = MagicMock()
    # Note starts on page 1 and continues on page 2
    dummy_page1.extract_text.return_value = "Header\nNote 1: This is a note that starts on page 1"
    dummy_page2.extract_text.return_value = "and continues on page 2. Footer"
    dummy_pdf.pages = [dummy_page1, dummy_page2]

    # Act
    result = handler.extract_notes(dummy_pdf, [1, 2])

    # Assert
    # The note should be concatenated across both pages
    assert "Note 1:" in result
    assert "This is a note that starts on page 1 and continues on page 2." in result["Note 1:"]["text"]

def test_extract_notes_interrupted_by_headers_footers(monkeypatch, patch_dirs):
    """Test extract_notes handles notes interrupted by headers, footers, or end patterns."""
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page1 = MagicMock()
    dummy_page2 = MagicMock()
    # Note starts on page 1, continues on page 2, both have headers/footers as separate lines
    dummy_page1.extract_text.return_value = "Header\nNote 2: This note is interrupted by a header."
    dummy_page2.extract_text.return_value = "Header\nStill part of note 2.\nFooter\nEnd of Notes"
    dummy_pdf.pages = [dummy_page1, dummy_page2]

    # Act
    result = handler.extract_notes(
        dummy_pdf,
        [1, 2],
        header_footer_pattern=r"^(Header|Footer|End of Notes)$"
    )

    # Assert
    # The note should be correctly concatenated and not include headers/footers
    assert "Note 2:" in result
    assert "This note is interrupted by a header. Still part of note 2." in result["Note 2:"]["text"]
    assert "Header" not in result["Note 2:"]["text"]
    assert "Footer" not in result["Note 2:"]["text"]
    assert "End of Notes" not in result["Note 2:"]["text"]

