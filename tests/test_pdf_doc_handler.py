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
    monkeypatch.setattr(handler, "extract_tables_pdfplumber", lambda pdf, pn, snap=None: dummy_tables)
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
    monkeypatch.setattr(handler, "extract_tables_pdfplumber", lambda pdf, pn, snap=None: [])
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
    monkeypatch.setattr(handler, "extract_tables_pdfplumber", lambda pdf, pn, snap=None: [])
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

def test_extract_tables_default_snap_tolerance(patch_dirs):
    """extract_tables_pdfplumber uses the default snap_tolerance (8) when no overrides are given."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page = MagicMock()
    dummy_pdf.pages = [dummy_page]
    dummy_page.extract_tables.return_value = [[["A", "B"]]]
    # Act
    handler.extract_tables_pdfplumber(dummy_pdf, [1])
    # Assert
    settings = dummy_page.extract_tables.call_args.kwargs["table_settings"]
    assert settings["snap_tolerance"] == 8


def test_extract_tables_snap_tolerance_override_applies_per_page(patch_dirs):
    """A per-page override changes snap_tolerance for that page only; others keep the default."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    page1 = MagicMock()
    page2 = MagicMock()
    page1.extract_tables.return_value = [[["A", "B"]]]
    page2.extract_tables.return_value = [[["C", "D"]]]
    dummy_pdf.pages = [page1, page2]
    # Act: override page 2 only
    handler.extract_tables_pdfplumber(dummy_pdf, [1, 2], snap_tolerance_overrides={2: 6})
    # Assert: page 1 keeps default 8, page 2 uses the override 6
    assert page1.extract_tables.call_args.kwargs["table_settings"]["snap_tolerance"] == 8
    assert page2.extract_tables.call_args.kwargs["table_settings"]["snap_tolerance"] == 6


def test_extract_tables_snap_tolerance_override_none_is_default(patch_dirs):
    """Passing None for overrides is equivalent to no overrides (default 8 everywhere)."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_page = MagicMock()
    dummy_pdf.pages = [dummy_page]
    dummy_page.extract_tables.return_value = [[["A", "B"]]]
    # Act
    handler.extract_tables_pdfplumber(dummy_pdf, [1], snap_tolerance_overrides=None)
    # Assert
    assert dummy_page.extract_tables.call_args.kwargs["table_settings"]["snap_tolerance"] == 8


def test_load_document_forwards_snap_tolerance_overrides(monkeypatch, patch_dirs):
    """load_document forwards snap_tolerance_overrides through to extract_tables_pdfplumber."""
    # Arrange
    handler = make_handler()
    dummy_pdf = MagicMock()
    dummy_pdf.pages = [MagicMock()]
    dummy_pdf.close = MagicMock()
    dummy_tables = [{"page": 1, "index": 0, "header": ["A", "B"], "data": [["C", "D"]]}]
    captured = {}

    def fake_extract(pdf, pn, snap=None):
        captured["snap"] = snap
        return dummy_tables

    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("pdfplumber.open", lambda path: dummy_pdf)
    monkeypatch.setattr(handler, "extract_tables_pdfplumber", fake_extract)
    monkeypatch.setattr(handler, "concat_tables", lambda tables, table_id=None: {"header": [], "data": []})
    # Act
    handler.load_document(
        cache_file_name="dummy.pdf",
        page_numbers=[1],
        table_indices=[(1, 0)],
        table_id="t",
        snap_tolerance_overrides={1: 6},
    )
    # Assert
    assert captured["snap"] == {1: 6}


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
    with pytest.raises(ValueError) as excinfo:
        handler.select_tables(
            tables,
            table_indices=[(35, 0)],
            table_header_rowspan={(35, 0): 2},
        )
    # The failure must stay ACTIONABLE: it names the table (page/index) and the
    # offending cell, not just a generic "DICOM tag pattern". Pin that context so a
    # regression toward a less actionable message is caught.
    msg = str(excinfo.value)
    assert "DICOM tag pattern" in msg
    assert "page 35" in msg
    assert "index 0" in msg
    assert "(300A,0230)" in msg

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

def test_concat_tables_preserves_empty_string_cell(monkeypatch, patch_dirs):
    """Test concat_tables keeps a blank-but-present ('') cell in its own column.

    A cell that is the empty string "" (e.g. an attribute row with no DCM Type) must
    NOT be dropped during realignment: doing so shifts every subsequent cell left by one,
    silently moving a value (here an IHE-RO requirement code) into the wrong column.
    This pins the fix for the IHE-RO empty-string column left-shift (TDRC-ION
    setup_beams > Recorded Snout Sequence (3008,00F0)).
    """
    # Arrange
    handler = make_handler()
    tables = [
        {
            "page": 1, "index": 0,
            "header": ["Attribute", "Tag", "DCM Type", "Type", "Attribute Note"],
            # DCM Type is blank ("") and the requirement code "-" sits in the Type column.
            "data": [["Recorded Snout Sequence", "(3008,00F0)", "", "-", ""]],
        },
    ]
    # Act
    result = handler.concat_tables(tables, table_id="t")
    # Assert
    assert result["header"] == ["Attribute", "Tag", "DCM Type", "Type", "Attribute Note"]
    # "-" stays under "Type"; "DCM Type" stays blank — no left shift.
    assert result["data"] == [["Recorded Snout Sequence", "(3008,00F0)", "", "-", ""]]

def test_concat_tables_fills_none_gaps(monkeypatch, patch_dirs):
    """Test concat_tables still slides cells left to fill genuine structural gaps (None).

    pdfplumber emits None for merged/absent cells; those ARE removed so real values
    fill the gap. This is the complement to empty-string preservation and guards that
    the realignment intent is retained.
    """
    # Arrange
    handler = make_handler()
    tables = [
        {"page": 1, "index": 0, "header": ["A", "B", "C"], "data": [["x", None, "y"]]},
    ]
    # Act
    result = handler.concat_tables(tables, table_id="t")
    # Assert
    assert result["header"] == ["A", "B", "C"]
    # None gap removed; "y" slides left to fill it; row padded back to header width.
    assert result["data"] == [["x", "y", ""]]

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



_IHE_HEADER = ["Attribute Name", "Tag", "Type", "Attribute Description"]


def _make_ihe_tables(*page_groups):
    """Build concat_tables input: one IHE-RO 4-column table dict per page group.

    Each positional arg is a list of rows (each row a 4-cell list of
    name, tag, type, description) representing one page's extracted table.
    """
    return [
        {"page": idx + 1, "index": 0, "header": list(_IHE_HEADER), "data": [list(r) for r in rows]}
        for idx, rows in enumerate(page_groups)
    ]


def test_concat_tables_single_continuation_merges_description():
    """Contract: a single orphan fragment merges into the prior tagged row's description.

    The fragment row must be absent from the result; the owning row's description
    must contain both the original text and the continuation text.
    """
    handler = make_handler()
    owning_row = [
        ">>Contour Geometric Type",
        "(3006,0042)",
        "1",
        "Geometric type of contour. See DICOM Standard,\nPS3.3, Section C.8.8.6.1.",
    ]
    fragment_row = ["", "", "", "Shall be of value\nPOINT single point\nCLOSED_PLANAR ..."]

    tables = _make_ihe_tables([owning_row], [fragment_row])
    result = handler.concat_tables(tables, table_id="t")

    # Fragment row must be gone — only one data row remains
    assert len(result["data"]) == 1, "Fragment row must be absorbed; only the owning row should remain"

    description = result["data"][0][3]
    assert "Geometric type of contour" in description
    assert "CLOSED_PLANAR" in description
    assert "POINT single point" in description


def test_concat_tables_multiple_consecutive_fragments_all_merge():
    """Contract: multiple consecutive fragment rows all accumulate onto the same owning row.

    Each fragment's description is appended in order; the owning row's description
    contains all parts; all fragment rows are gone from the result.
    """
    handler = make_handler()
    owning_row = ["Beam Sequence", "(300A,00B0)", "1", "Sequence of treatment beams."]
    fragment1 = ["", "", "", "Each beam defines one irradiation."]
    fragment2 = ["", "", "", "Required if RT Plan is for external beam."]

    tables = _make_ihe_tables([owning_row, fragment1, fragment2])
    result = handler.concat_tables(tables, table_id="t")

    assert len(result["data"]) == 1, "Both fragments must be absorbed; one owning row expected"

    description = result["data"][0][3]
    assert "Sequence of treatment beams" in description
    assert "Each beam defines one irradiation" in description
    assert "Required if RT Plan is for external beam" in description


def test_concat_tables_zero_orphans_postcondition():
    """Acceptance test: after concat_tables, no data row has empty name AND empty tag AND non-empty description.

    This is the key post-condition that the merge step must guarantee.  Any row
    that passes this discriminator in the result is a silently-lost orphan fragment.
    """
    handler = make_handler()
    # Mix of normal rows and fragments spread across two pages
    page1_rows = [
        ["Contour Sequence", "(3006,0040)", "1C", "Sequence of contours."],
        [">>Contour Geometric Type", "(3006,0042)", "1", "Geometric type."],
        ["", "", "", "Continuation of geometric type description."],
    ]
    page2_rows = [
        [">Referenced ROI Number", "(3006,0084)", "1", "References the ROI."],
        ["", "", "", "Must be unique within the structure set."],
        ["Observation Label", "(3006,0085)", "3", "User-defined label."],
    ]
    tables = _make_ihe_tables(page1_rows, page2_rows)
    result = handler.concat_tables(tables, table_id="t")

    for row in result["data"]:
        name = row[0] if row else ""
        tag = row[1] if len(row) > 1 else ""
        desc = row[3] if len(row) > 3 else ""
        name_empty = not (name and str(name).strip())
        tag_empty = not (tag and str(tag).strip())
        desc_nonempty = bool(desc and str(desc).strip())
        assert not (name_empty and tag_empty and desc_nonempty), f"Orphan fragment survived in result: {row!r}"


def test_concat_tables_include_table_row_not_treated_as_fragment():
    """Contract: an '>>>Include Table N-N' row (has a name, no tag) is NOT merged as a fragment.

    Such rows are directives, not continuations.  The discriminator requires BOTH
    name AND tag to be empty; a named-but-untagged row must pass through unchanged.
    """
    handler = make_handler()
    include_row = [">>>Include Table 10-3", "", "", ""]
    next_attr = ["Beam Meterset", "(300A,0086)", "1", "Machine setting."]

    tables = _make_ihe_tables([include_row, next_attr])
    result = handler.concat_tables(tables, table_id="t")

    assert len(result["data"]) == 2, "Include-table row must not be merged/dropped"
    # The include row must still be first
    assert "Include Table 10-3" in result["data"][0][0]


def test_concat_tables_fragment_as_first_row_left_in_place(caplog):
    """Contract: a fragment that has no preceding tagged row is left in place with a warning.

    This is an anomalous edge case (a fragment at the very start of the data).
    The guard must not merge it (there is nothing to merge into) and must log a warning.
    """
    handler = make_handler()
    fragment_row = ["", "", "", "Orphaned continuation with no owner."]

    tables = _make_ihe_tables([fragment_row])
    caplog.set_level(logging.WARNING)
    result = handler.concat_tables(tables, table_id="t")

    # Row must survive (not silently vanish)
    assert len(result["data"]) == 1
    # Assert on the specific warning via caplog.records (not brittle full-text scanning).
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("Untagged continuation row" in r.getMessage() for r in warnings), (
        "Expected a WARNING naming the untagged continuation row"
    )


def test_concat_tables_whitespace_only_name_and_tag_merges_like_empty():
    """Contract: a fragment whose name/tag are whitespace-only (not "") still merges.

    The continuation discriminator uses ``str.strip()``, so spaces emitted by pdfplumber in
    place of empty strings must still be treated as empty and merged into the owning row.
    """
    handler = make_handler()
    owning_row = [">>Contour Geometric Type", "(3006,0042)", "1", "Geometric type of contour."]
    fragment_row = ["   ", "  ", "", "Shall be POINT, CLOSED_PLANAR, or CLOSEDPLANAR_XOR."]

    tables = _make_ihe_tables([owning_row, fragment_row])
    result = handler.concat_tables(tables, table_id="t")

    assert len(result["data"]) == 1, "Whitespace-only fragment must merge, same as an empty fragment"
    assert "CLOSEDPLANAR_XOR" in result["data"][0][3]


def test_concat_tables_continuation_merge_preserves_existing_empty_string_fix():
    """Regression: the empty-string ('') blank-cell preservation still works after adding merge logic.

    A cell that is the empty string "" (e.g. no DCM Type) must NOT be dropped during
    realignment — doing so shifts every subsequent cell left by one.  This test mirrors
    test_concat_tables_preserves_empty_string_cell to confirm the cherry-picked fix survives
    the new merge step.
    """
    handler = make_handler()
    tables = [
        {
            "page": 1,
            "index": 0,
            "header": ["Attribute", "Tag", "DCM Type", "Type", "Attribute Note"],
            "data": [["Recorded Snout Sequence", "(3008,00F0)", "", "-", ""]],
        },
    ]
    result = handler.concat_tables(tables, table_id="t")

    assert result["header"] == ["Attribute", "Tag", "DCM Type", "Type", "Attribute Note"]
    assert result["data"] == [["Recorded Snout Sequence", "(3008,00F0)", "", "-", ""]]


# --- Fused "frankenrow" split (mirror of the continuation merge) ----------------

_IHE5_HEADER = ["Attribute Name", "Tag", "Type", "IHE-RO", "Attribute Description"]


def _make_ihe5_tables(*page_groups):
    """Build concat_tables input: one IHE-RO 5-column table dict per page group.

    Each positional arg is a list of rows (each row a 5-cell list of
    name, tag, type, ihe-ro requirement, description) representing one page's table.
    """
    return [
        {"page": idx + 1, "index": 0, "header": list(_IHE5_HEADER), "data": [list(r) for r in rows]}
        for idx, rows in enumerate(page_groups)
    ]


def test_concat_tables_fused_frankenrow_splits_into_two():
    """Contract: a row whose tag cell holds two DICOM tags splits into two aligned rows.

    Models the observed TPPC fusion of (300A,0214) Source Type and (300A,0216)
    Source Manufacturer: every column newline-joins the two source rows; both
    descriptions are blank. The split must recover two single-tag rows, value-aligned.
    """
    handler = make_handler()
    fused = [">Source Type\n>Source Manufacturer", "(300A,0214)\n(300A,0216)", "1\n3", "-*\n-", ""]
    result = handler.concat_tables(_make_ihe5_tables([fused]), table_id="t")

    assert len(result["data"]) == 2, "Fused row must split into two attribute rows"
    assert result["data"][0] == [">Source Type", "(300A,0214)", "1", "-*", ""]
    assert result["data"][1] == [">Source Manufacturer", "(300A,0216)", "3", "-", ""]


def test_concat_tables_fused_three_way_splits_into_three():
    """Contract: the discriminator generalises to N>=2; a three-tag fusion yields three rows."""
    handler = make_handler()
    fused = [">A\n>B\n>C", "(1111,0001)\n(2222,0002)\n(3333,0003)", "1\n2\n3", "R\nO\n-", ""]
    result = handler.concat_tables(_make_ihe5_tables([fused]), table_id="t")

    assert len(result["data"]) == 3
    assert [r[1] for r in result["data"]] == ["(1111,0001)", "(2222,0002)", "(3333,0003)"]
    assert [r[2] for r in result["data"]] == ["1", "2", "3"]
    assert [r[3] for r in result["data"]] == ["R", "O", "-"]


def test_concat_tables_fused_splits_per_attribute_descriptions():
    """Contract: a non-blank description that also splits into N parts aligns 1:1 with the tags."""
    handler = make_handler()
    fused = [">A\n>B", "(300A,0214)\n(300A,0216)", "1\n3", "-*\n-", "first desc\nsecond desc"]
    result = handler.concat_tables(_make_ihe5_tables([fused]), table_id="t")

    assert len(result["data"]) == 2
    assert result["data"][0][4] == "first desc"
    assert result["data"][1][4] == "second desc"


def test_concat_tables_fused_not_split_when_structured_columns_misaligned(caplog):
    """Fail-safe: if a structured column does not yield exactly N parts, leave the row intact.

    Here the tag cell has two tags but the type cell has only one part, so the split
    would be ambiguous. The row must NOT be split and a warning must be logged.
    """
    import logging

    handler = make_handler()
    fused = [">A\n>B", "(300A,0214)\n(300A,0216)", "1", "-*\n-", ""]  # type has 1 part, not 2
    with caplog.at_level(logging.WARNING):
        result = handler.concat_tables(_make_ihe5_tables([fused]), table_id="t")

    assert len(result["data"]) == 1, "Misaligned fusion must be left intact, never split blindly"
    assert result["data"][0][1] == "(300A,0214)\n(300A,0216)", "Tag cell stays fused when not splittable"
    assert any("could not be cleanly split" in r.message for r in caplog.records)


def test_concat_tables_fused_not_split_when_description_nonempty_misaligned():
    """Fail-safe: a non-blank description with a different part-count than N blocks the split."""
    handler = make_handler()
    fused = [">A\n>B", "(300A,0214)\n(300A,0216)", "1\n3", "-*\n-", "one shared description"]
    result = handler.concat_tables(_make_ihe5_tables([fused]), table_id="t")

    assert len(result["data"]) == 1, "Ambiguous description must block the split"
    assert result["data"][0][4] == "one shared description"


def test_concat_tables_single_tag_row_never_split_despite_description_newline():
    """Negative: a legitimate single-tag row is never split, even with newlines in its description."""
    handler = make_handler()
    row = [">A", "(300A,0214)", "1", "-*", "line one\nline two\nline three"]
    result = handler.concat_tables(_make_ihe5_tables([row]), table_id="t")

    assert len(result["data"]) == 1
    assert result["data"][0][1] == "(300A,0214)"


def test_concat_tables_tag_cell_with_nontag_part_not_treated_as_fusion():
    """Negative: a tag cell with one DICOM tag plus non-tag text is not a fusion (not every part is a tag)."""
    handler = make_handler()
    row = [">A", "(300A,0214)\nsee note 2", "1", "-*", ""]
    result = handler.concat_tables(_make_ihe5_tables([row]), table_id="t")

    assert len(result["data"]) == 1, "Only all-DICOM-tag multi-part cells are fusions"
    assert result["data"][0][1] == "(300A,0214)\nsee note 2"


def test_concat_tables_fused_row_then_continuation_splits_then_merges():
    """Interaction: split runs before merge, so a continuation after a fusion lands on the LAST split row.

    The fused row becomes two rows; the trailing untagged continuation fragment then
    merges into the immediately preceding (second) split row's description.
    """
    handler = make_handler()
    fused = [">A\n>B", "(300A,0214)\n(300A,0216)", "1\n3", "-*\n-", ""]
    continuation = ["", "", "", "", "continued requirement text"]
    result = handler.concat_tables(_make_ihe5_tables([fused, continuation]), table_id="t")

    assert len(result["data"]) == 2, "Two split rows; the continuation must not survive as its own row"
    assert result["data"][0][1] == "(300A,0214)"
    assert result["data"][1][1] == "(300A,0216)"
    assert "continued requirement text" in result["data"][1][4]
