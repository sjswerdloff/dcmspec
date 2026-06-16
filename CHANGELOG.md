# Release Notes

These release notes summarize key changes, improvements, and breaking updates for each version of **dcmspec**.

## [Unreleased]

### Fixed

- `PDFDocHandler.concat_tables` now reconstructs page-straddling description cells. When an attribute's description wraps across a PDF page boundary, pdfplumber emits the continuation as an untagged row (empty name and tag, description only) atop the next page's table; this is now merged into the preceding tagged row's description instead of becoming a floating node. Recovers enum values and conditional requirements that were silently lost at page breaks (e.g. HDSS Contour Geometric Type `(3006,0042)` losing its `POINT` / `CLOSED_PLANAR` / `CLOSEDPLANAR_XOR` enumeration).
- `PDFDocHandler.load_document` / `extract_tables_pdfplumber` now accept a `snap_tolerance_overrides` dict (keyed by 1-indexed page number) to lower pdfplumber's `snap_tolerance` for individual pages. The default (8) snaps two near-coincident header rules together on a few pages, fusing a repeated continuation sub-header (e.g. `Presence | Specific Rules`) into the first data row of the next page; that row then trips the tag-in-header guard (rowspan over-count) and the page cannot be extracted. Lowering the tolerance for just that page (e.g. `{34: 6}`) keeps the two rules distinct so the sub-header is recognized as a header row, recovering the first attribute of the continuation table (e.g. TPPC-Brachy HDR/PDR Source `(0008,1040)`) without disturbing extraction of any other page. This also un-fuses line-snapped "frankenrows" at the source on the affected page; the `concat_tables` split below remains as a downstream safety net for pages that still fuse at the default tolerance.
- `PDFDocHandler.concat_tables` now splits fused "frankenrow" rows back into their constituent attribute rows. pdfplumber's line-snapping can merge two adjacent table rows whose separating rule falls within `snap_tolerance` into one row, newline-joining every column (e.g. tag `(300A,0214)\n(300A,0216)`, type `1\n3`). A legitimate attribute row carries exactly one DICOM tag, so a tag cell holding N≥2 DICOM-tag patterns is unambiguously a fusion; the row is split into N rows **only** when every structured column yields exactly N aligned newline-parts (the description must be blank or also N parts), otherwise it is left intact and logged. Mirrors the continuation-merge discriminator and recovers attributes (e.g. TPPC-Brachy `(300A,0214)` Source Type / `(300A,0216)` Source Manufacturer) that were fused into a single malformed node.

## [0.3.0] - 2025-11-27

### Added

- CSV output mode in `SpecPrinter` via `print_csv` method
- Excel OOXML output mode in `SpecPrinter` via `print_xlsx` method
- Optional `output` parameter in `SpecPrinter` for writing to files
- Optional `column_width` parameter in `print_table` and `print_xlsx`
- `--print-mode` option in `modattributes` CLI for CSV and OOXML output
- `--output` option in `modattributes` CLI for directing output to files

### Changed

- Switch PyPI version badge in `README` from `badge.fury.io` to `shields.io` for faster updates
- Update modattributes CLI example for CSV and XLSX output
- Improved nesting level color schemes for consistency and better contrast and readability.

### Fixed

- Correct handling of `include_table` names in `DOMTableSpecParser`
- Correct handling of empty node attributes in `SpecPrinter`

## [0.2.3] - 2025-09-29

### Fixed

- Hotfix: Force UTF-8 decoding for DICOM standard XHTML downloads to prevent mojibake when server omits charset ([#85](https://github.com/dwikler/dcmspec/issues/85)).
- Hotfix: Add missing `progress_observer` argument to `CSVTableSpecParser.parse` for interface compatibility and to prevent `TypeError` when used with `SpecFactory` ([#86](https://github.com/dwikler/dcmspec/issues/86)).

## [0.2.2] - 2025-09-25

### Fixed

- Fix CONTRIBUTING.md link in README for PyPI compatibility
- Remove focus border and misleading text cursor in iod-explorer details panel

### Changed

- Update README: add PyPI and Python version badges
- Replace Unicode ▶ with ASCII > in status bar for compatibility
- Improve DICOM Modules usage condition parsing using regex for robustness to missing spaces
- Add PR template to remind contributors to check the target branch and check tests and docs were updated
- Move detailed table parsing logs to DEBUG level for less verbose INFO output

## [0.2.1] - 2025-09-19

### Fixed

- Sanitize node and attribute names to remove "/" in DOMTableSpecParser ([#56](https://github.com/dwikler/dcmspec/issues/56))

### Changed

- Major project restructure: move CLI and UI apps to new `apps/cli` and `apps/ui` folders
- Improve installation instructions and documentation
- Prepare and publish the package to [PyPI](https://pypi.org/project/dcmspec/)

## [0.2.0] - 2025-09-13

### Changed

- **Breaking change:** `IODSpecBuilder.build_from_url` now returns a tuple `(iod_model, module_models)` instead of just the IOD model. All callers must be updated to unpack the tuple
- Update CLI and UI applications to support new return value
- Add registry mode to `IODSpecBuilder` for efficient module model sharing

## [0.1.0] - 2025-05-25

### Added

- Initial release
