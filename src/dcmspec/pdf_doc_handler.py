"""PDF document handler for IHE Technical Frameworks or Supplements processing in dcmspec.

Provides the PDFDocHandler class for downloading, caching, and parsing PDF documents
from IHE Technical Frameworks or Supplements, returning CSV data from tables in PDF files.
"""

import os
import re
import logging
from typing import Optional, List
# BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
from dcmspec.progress import handle_legacy_callback
from typing import Callable
# END LEGACY SUPPORT

import pdfplumber
import camelot

from dcmspec.config import Config
from dcmspec.doc_handler import DocHandler
from dcmspec.progress import ProgressObserver

# A DICOM tag pattern like "(300A,0230)" appearing in a *header* cell is a strong
# signal that a data (attribute) row was absorbed into the header — typically
# because table_header_rowspan over-counts the header rows for a table.
# select_tables uses this to fail loudly rather than silently drop the row, which
# is unacceptable for conformance tooling.
_DICOM_TAG_RE = re.compile(r"\(\s*[0-9A-Fa-f]{4}\s*,\s*[0-9A-Fa-f]{4}\s*\)")


class PDFDocHandler(DocHandler):
    """Handler class for extracting tables from PDF documents.

    Provides methods to download, cache, and extract tables as CSV data from PDF files.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        logger: Optional[logging.Logger] = None,
        extractor: str = "pdfplumber"
    ):
        """Initialize the PDF document handler.

        Sets up the handler with an optional configuration and logger.

        Args:
            config (Optional[Config]): Configuration object for cache and other settings.
            logger (Optional[logging.Logger]): Logger instance to use. If None, a default logger is created.
            extractor (str): Table extraction library to use. 
                `pdfplumber` (default) uses pdfplumber for extraction.
                `camelot` uses Camelot (lattice flavor) for extraction.
                `pdfplumber` detects tables by analyzing lines and whitespace in the PDF's vector content,
                while `camelot` detects tables by processing the rendered page image to find drawn lines.

        """
        super().__init__(config=config, logger=logger)
        self.extractor = extractor
        self.logger.debug(f"PDFDocHandler initialized with extractor {self.extractor} and logger {self.logger.name} "
                          f"at level {logging.getLevelName(self.logger.level)}")
        
        self.cache_file_name = None

    def load_document(
        self,
        cache_file_name: str,
        url: Optional[str] = None,
        force_download: bool = False,
        progress_observer: 'Optional[ProgressObserver]' = None,
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_callback: 'Optional[Callable[[int], None]]' = None,
        # END LEGACY SUPPORT
        page_numbers: Optional[list] = None,
        table_indices: Optional[list] = None,
        table_header_rowspan: Optional[dict] = None,
        table_id: Optional[str] = None,
    ) -> dict:
        """Download, cache, and extract the logical CSV table from the PDF.

        Args:
            cache_file_name (str): Path to the local cached PDF file.
            url (str, optional): URL to download the file from if not cached or if force_download is True.
            force_download (bool): If True, do not use cache and download the file from the URL.
            progress_observer (Optional[ProgressObserver]): Optional observer to report download progress.
            progress_callback (Optional[Callable[[int], None]]): [LEGACY, Deprecated] Optional callback to
                report progress as an integer percent (0-100, or -1 if indeterminate). Use progress_observer
                instead. Will be removed in a future release.
            page_numbers (list, optional): List of page numbers to extract tables from.
            table_indices (list, optional): List of (page, index) tuples specifying which tables to concatenate.
            table_header_rowspan (dict, optional): Number of header rows (rowspan) for each table in table_indices.
            table_id (str, optional): An identifier for the concatenated table.

        Returns:
            dict: The specification table dict with keys 'header', 'data', and optionally 'table_id'.

        Example:
            ```python
            handler = PDFDocHandler()
            spec_table = handler.load_document(
                cache_file_name="myfile.pdf",
                url="https://example.com/myfile.pdf",
                page_numbers=[10, 11],
                table_indices=[(10, 0), (11, 1)],
                table_header_rowspan={
                    (10, 0): 2,  # Table starts on page 10, index 0 and has 2 header rows
                    (11, 1): 2,  # Table ends on page 11, index 1 and has 2 header rows
                },
                table_id="my_spec_table"
            )
            ```
            
        """
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_observer = handle_legacy_callback(progress_observer, progress_callback)
        # END LEGACY SUPPORT
        self.cache_file_name = cache_file_name
        cache_file_path = os.path.join(self.config.get_param("cache_dir"), "standard", cache_file_name)
        need_download = force_download or (not os.path.exists(cache_file_path))
        if need_download:
            if not url:
                self.logger.error("URL must be provided to download the file.")
                raise ValueError("URL must be provided to download the file.")
            self.logger.info(f"Downloading PDF from {url} to {cache_file_path}")
            cache_file_path = self.download(url, cache_file_name, progress_observer=progress_observer)
        else:
            self.logger.info(f"Loading PDF from cache file {cache_file_path}")

        if page_numbers is None or table_indices is None:
            self.logger.error("page_numbers and table_indices must be provided to extract the logical table.")
            raise ValueError("page_numbers and table_indices must be provided to extract the logical table.")

        self.logger.debug(f"Extracting tables from pages: {page_numbers}")
        if self.extractor == "pdfplumber":
            pdf = pdfplumber.open(cache_file_path)
            all_tables = self.extract_tables_pdfplumber(pdf, page_numbers)
            self.logger.debug(f"Extracted {len(all_tables)} tables from PDF using pdfplumber.")
            pdf.close()
        elif self.extractor == "camelot":
            all_tables = self.extract_tables_camelot(cache_file_path, page_numbers)
            self.logger.debug(f"Extracted {len(all_tables)} tables from PDF using Camelot.")
        else:
            raise ValueError(f"Unknown extractor: {self.extractor}")

        if self.logger.isEnabledFor(logging.DEBUG):
            for idx, table in enumerate(all_tables):
                self.logger.debug(f"\nTable {idx}:")
                for row in table["data"]:
                    self.logger.debug(row)

        self.logger.debug(f"Selecting tables with indices: {table_indices}")
        selected_tables = self.select_tables(all_tables, table_indices, table_header_rowspan)
        self.logger.debug(f"Concatenating selected tables with table_id: {table_id}")
        spec_table = self.concat_tables(selected_tables, table_id=table_id)
        self.logger.debug(f"Returning spec_table with header: {spec_table.get('header', [])}")
        self.logger.debug(f"Returning spec_table with data: {spec_table.get('data', [])}")

        return spec_table

    def download(self,
                url: str,
                cache_file_name: str,
                progress_observer: 'Optional[ProgressObserver]' = None,
                # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
                progress_callback: 'Optional[Callable[[int], None]]' = None
                # END LEGACY SUPPORT
                ) -> str:
        """Download and cache a PDF file from a URL using the base class download method.

        Args:
            url: The URL of the PDF document to download.
            cache_file_name: The filename of the cached document.
            progress_observer (Optional[ProgressObserver]): Optional observer to report download progress.
            progress_callback (Optional[Callable[[int], None]]): [LEGACY, Deprecated] Optional callback to
                report progress as an integer percent (0-100, or -1 if indeterminate). Use progress_observer
                instead. Will be removed in a future release.

        Returns:
            The file path where the document was saved.

        Raises:
            RuntimeError: If the download or save fails.

        """
        # BEGIN LEGACY SUPPORT: Remove for int progress callback deprecation
        progress_observer = handle_legacy_callback(progress_observer, progress_callback)
        # END LEGACY SUPPORT
        file_path = os.path.join(self.config.get_param("cache_dir"), "standard", cache_file_name)
        return super().download(url, file_path, binary=True, progress_observer=progress_observer)

    def extract_tables_pdfplumber(self, pdf: pdfplumber.PDF, page_numbers: List[int]) -> List[dict]:
        """Extract and return all tables from the specified PDF pages using pdfplumber.

        Uses pdfplumber to extract tables from the PDF by analyzing lines and whitespace in the PDF's vector content.

        Args:
            pdf (pdfplumber.PDF): The PDF object.
            page_numbers (List[int]): List of page numbers (1-indexed) to extract tables from.

        Returns:
            List[dict]: List of dicts, each with keys 'page', 'index', and 'data' (table as list of rows).

        Raises:
            IndexError: If a page number is out of range for the PDF.

        """
        all_tables = []
        num_pages = len(pdf.pages)
        for page_num in page_numbers:
            if not (1 <= page_num <= num_pages):
                raise IndexError(
                    f"Page number {page_num} is out of range for this PDF (valid range: 1 to {num_pages})"
                )
            page = pdf.pages[page_num - 1]
            tables = page.extract_tables(
                table_settings={
                    "vertical_strategy": "lines", 
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 8,
                }
            )

            if not tables:
                continue
            all_tables.extend(
                {
                    "page": page_num,
                    "index": idx,
                    "data": table,
                }
                for idx, table in enumerate(tables)
            )
        return all_tables

    def extract_tables_camelot(self, file_path: str, page_numbers: List[int]) -> List[dict]:
        """Extract and return all tables from the specified PDF pages using Camelot.

        Uses Camelot in "lattice" mode, which detects tables by analyzing the rendered page image for drawn lines.

        Args:
            file_path (str): Path to the PDF file.
            page_numbers (List[int]): List of page numbers (1-indexed) to extract tables from.

        Returns:
            List[dict]: List of dicts, each with keys 'page', 'index', and 'data' (table as list of rows).
            
        """
        all_tables = []
        for page_num in page_numbers:
            tables = camelot.read_pdf(
                file_path,
                pages=str(page_num),
                flavor="lattice",
                line_scale=40
            )
            all_tables.extend(
                {
                    "page": page_num,
                    "index": idx,
                    "data": table.df.values.tolist(),
                }
                for idx, table in enumerate(tables)
            )
        return all_tables

    def select_tables(
        self,
        tables: List[dict],
        table_indices: List[tuple],
        table_header_rowspan: Optional[dict] = None,
    ) -> List[dict]:
        """Select tables referenced by table_indices and split each table into header and data.

        This method processes a list of extracted tables, selects those specified by table_indices,
        and splits each selected table into a header and data rows. If a table has multiple header rows
        (as specified by table_header_rowspan), these rows are merged column-wise to form a single header row.


        Args:
            tables (List[dict]): List of table dicts, each with 'page', 'index', and 'data' (raw table rows).
            table_indices (List[tuple]): List of (page, index) tuples specifying which tables to select and process.
            table_header_rowspan (dict, optional): Number of header rows (rowspan) for each table in table_indices,
                keyed by (page, index). If not specified, defaults to 1 header row per table.

        Returns:
            List[dict]: List of dicts, each with keys:
                - 'page': page number of the table
                - 'index': index of the table on the page
                - 'header': merged header row (list of column names)
                - 'data': list of data rows (list of cell values)

        Raises:
            ValueError: If a header cell contains a DICOM tag pattern (e.g. "(300A,0230)"),
                indicating that a data row was absorbed into the header — typically because
                table_header_rowspan over-counts the header rows for that table. Failing loudly
                here prevents silently dropping a real attribute row from the specification.

        Example:
            ```python
            selected_tables = handler.select_tables(
                tables,
                table_indices=[(10, 0), (11, 1)],
                table_header_rowspan={(10, 0): 2, (11, 1): 2}
            )
            for table in selected_tables:
                print(table["header"], table["data"])
            ```

        """
        def merge_multirow_header(header_rows):
            n_cols = max(len(row) for row in header_rows)
            merged = []
            for col in range(n_cols):
                merged_cell = " ".join(
                    str(row[col]).strip() for row in header_rows
                    if col < len(row) and row[col] not in (None, "")
                ).strip()
                merged.append(merged_cell)
            return merged

        selected_tables = []
        for page, idx in table_indices:
            for table in tables:
                if table["page"] == page and table["index"] == idx:
                    table_rows = table["data"]
                    n_header_rows = 1
                    if table_header_rowspan and (page, idx) in table_header_rowspan:
                        n_header_rows = table_header_rowspan[(page, idx)]
                    header_rows = table_rows[:n_header_rows]
                    data_rows = table_rows[n_header_rows:]
                    # Merge header rows if needed
                    if len(header_rows) == 1:
                        header_ = header_rows[0]
                    else:
                        header_ = merge_multirow_header(header_rows)
                    # Fail loudly if a data row was absorbed into the header: a
                    # DICOM tag pattern in a header cell means table_header_rowspan
                    # likely over-counts the header rows for this table, which would
                    # otherwise silently drop a real attribute row from the spec.
                    for cell in header_:
                        if cell and _DICOM_TAG_RE.search(str(cell)):
                            raise ValueError(
                                f"Header for table (page {page}, index {idx}) contains a "
                                f"DICOM tag pattern in cell {cell!r}; a data row was likely "
                                f"absorbed into the header. Check table_header_rowspan for "
                                f"(page {page}, index {idx}) — it may exceed the actual "
                                f"number of header rows."
                            )
                    selected_tables.append({
                        "page": page,
                        "index": idx,
                        "header": header_,
                        "data": data_rows,
                    })
        return selected_tables

    def concat_tables(
        self,
        tables: List[dict],
        table_id: str = None,
    ) -> dict:
        """Concatenate selected tables (across pages or by specification) into a single logical table.

        Args:
            tables (List[dict]): List of table dicts, each with 'page', 'index', 'header', and 'data'.
            table_id (str, optional): An identifier for the concatenated table.

        Returns:
            dict: A dict with keys 'table_id' (if provided), 'header' (from the first table), 
            and 'data' (the concatenated table as a list of rows).

        """
        grouped_table = []
        header = []
        first = True
        for table in tables:
            header_ = table.get("header", [])
            if first:
                header = header_
                first = False
            elif header and header_ != header:
                self.logger.warning(
                    f"Header mismatch in concatenated tables: {header} != {header_} "
                    f"(page {table['page']}, index {table['index']})"
                )
            n_columns = len(header)
            for row in table["data"]:
                # Always pad/truncate to header length
                row = (row + [""] * (n_columns - len(row)))[:n_columns]
                grouped_table.append(row)
                
        # Realign columns: shift non-empty header cells and data cells left to fill gaps ---
        def shift_row_left(row):
            new_row = [cell for cell in row if cell not in (None, "")]
            new_row += [""] * (len(row) - len(new_row))
            return new_row

        header = shift_row_left(header)
        data = [shift_row_left(row) for row in grouped_table]

        # Remove columns where the header is empty
        columns_to_keep = [i for i, cell in enumerate(header) if cell not in (None, "")]
        header = [header[i] for i in columns_to_keep]
        data = [[row[i] for i in columns_to_keep] for row in data]

        result = {"header": header, "data": data}
        if table_id is not None:
            result["table_id"] = table_id
        return result

    def extract_notes(
        self,
        pdf: pdfplumber.PDF,
        page_numbers: List[int],
        table_id: str = None,
        note_pattern: str = r"^\d*\s*Note\s\d+:",
        header_footer_pattern: str = r"^\s*(IHE|_{3,}|Rev\.|Copyright|Template|Page\s\d+|\(TDW-II\))",
        line_number_pattern: str = r"^\d+\s",
        end_note_pattern: str = r".*7\.5\.1\.1\.2",
    ) -> dict:
        """Extract notes referenced in tables from the specified PDF pages.

        Args:
            pdf (pdfplumber.PDF): The PDF object.
            page_numbers (List[int]): List of page numbers (1-indexed) to extract notes from.
            table_id (str, optional): The table_id to associate with these notes.
            note_pattern (str): Regex pattern to identify note lines.
            header_footer_pattern (str): Regex pattern to skip header/footer lines.
            line_number_pattern (str): Regex pattern to remove line numbers.
            end_note_pattern (str): Regex pattern to identify the end of notes section.

        Returns:
            dict: Mapping from note key (e.g., "Note 1:") to a dict with 'text' and 'table_id' (if provided).

        Example return:
            ```json
            {
                "Note 1:": {"text": "...", "table_id": "T-7.5-1"},
                "Note 2:": {"text": "...", "table_id": "T-7.5-1"},
            }
            ```
            
        """
        import re

        notes = {}
        note_re = re.compile(note_pattern)
        header_footer_re = re.compile(header_footer_pattern)
        line_number_re = re.compile(line_number_pattern)
        end_note_re = re.compile(end_note_pattern)
        current_note = None

        for page_num in page_numbers:
            page = pdf.pages[page_num - 1]
            text = page.extract_text()
            if text:
                lines = text.split("\n")
                for line in lines:
                    # Always skip header/footer lines, even in note continuation
                    if header_footer_re.search(line):
                        continue
                    if end_note_re.search(line):
                        current_note = None
                        break
                    match = note_re.search(line)
                    if match:
                        note_number = match.group().strip()
                        note_number = re.sub(r"^\d*\s*", "", note_number)
                        note_text = line[match.end():].strip()
                        notes[note_number] = {
                            "text": note_text,
                            "table_id": table_id
                        } if table_id else {"text": note_text}
                        current_note = note_number
                    elif current_note:
                        line = line_number_re.sub("", line).strip()
                        notes[current_note]["text"] += f" {line}"
        if notes:
            self.logger.debug(f"Extracted notes: {list(notes.keys())}")
        return notes