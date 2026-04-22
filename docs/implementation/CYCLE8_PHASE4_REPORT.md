# Cycle 8 Phase 8.4 Report - Document Faculty

## Summary

Phase 8.4 adds the Document Faculty to INANNA NYX. The system can now
read common document formats directly from disk, build structured
document comprehension for CROWN, write new text and DOCX documents,
open documents in LibreOffice, and export documents to PDF through the
LibreOffice CLI path.

This phase was implemented as a direct-reader faculty first, with
LibreOffice used only for consequential application-level tasks such as
open and export.

## Python library installation result

Executed command:

```powershell
py -3 -m pip install python-docx python-pptx openpyxl pymupdf odfpy --break-system-packages
```

Successful installs:

- `python-docx 1.2.0`
- `python-pptx 1.0.2`
- `openpyxl 3.1.5`
- `pymupdf 1.27.2.2`
- `odfpy 1.4.1`

Transitive packages also installed or satisfied:

- `lxml`
- `Pillow`
- `XlsxWriter`
- `et-xmlfile`
- `defusedxml`

Fallback status:

- `pypdf` fallback was not needed because `pymupdf` installed cleanly.

## Runtime additions

- Added `inanna/core/document_workflows.py`
- Added four governed tools:
  - `doc_read`
  - `doc_write`
  - `doc_open`
  - `doc_export_pdf`
- Added document routing hints in `governance_signals.json`
- Wired document routing into both CLI and WebSocket execution before filesystem routing
- Added document-specific context shaping and audit trail entries

## Formats verified in tests

Confirmed working in the offline test suite:

- `.txt`
- `.md`
- `.docx`
- `.pdf`
- `.xlsx`
- `.csv`

Supported by implementation but not fully exercised with a fixture in this phase:

- `.rst`
- `.log`
- `.odt`
- `.xls`
- `.ods`

## Known limits

- DOCX writing is implemented directly.
- ODT writing is not implemented yet; text and DOCX are the write paths in this phase.
- PDF export depends on `soffice` being available on the host.
- LibreOffice UI opening is routed through the existing Desktop Faculty and is intentionally mocked in tests.

## NixOS equivalents

NixOS package equivalents for all Phase 8.4 dependencies:

- `python-docx` -> `python3Packages.python-docx`
- `python-pptx` -> `python3Packages.python-pptx`
- `openpyxl` -> `python3Packages.openpyxl`
- `pymupdf` -> `python3Packages.pymupdf`
- `odfpy` -> `python3Packages.odfpy`
- LibreOffice export/open path -> `libreoffice`

See `docs/nixos_document_faculty.md` for the consolidated NixOS note.

## Verification

Phase verification for this implementation includes:

- offline document workflow unit tests
- updated operator registry tests
- updated identity tests
- updated command/help tests
- full `unittest discover` run across the tracked suite
