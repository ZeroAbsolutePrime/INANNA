# CURRENT PHASE: Cycle 8 - Phase 8.4 - Document Faculty
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-22**
**Cycle: 8 - The Desktop Bridge**
**Replaces: Cycle 8 Phase 8.3c - The Startup Fix (COMPLETE)**

---

## MANDATORY READING — in this exact order

1. docs/platform_architecture.md
2. docs/cycle8_master_plan.md
3. docs/cycle9_master_plan.md
4. docs/implementation/CURRENT_PHASE.md (this file)
5. CODEX_DOCTRINE.md (canonical location)
6. ABSOLUTE_PROTOCOL.md

All documentation produced in this phase must be complete,
honest, and permanent. Future AI reading this project
depends on what is written here.

---

## Current System State

LibreOffice 24.2.4.2 installed:
  swriter.exe   (Writer — word processor)
  scalc.exe     (Calc — spreadsheet)
  simpress.exe  (Impress — presentations)

Python document libraries: NOT YET INSTALLED
  python-docx, python-pptx, openpyxl, pymupdf — all missing

Tools registered: 31 across 8 categories
Tests passing: 520
Phase: Cycle 8 - Phase 8.3c - The Startup Fix

---

## What This Phase Is

Phase 8.3 gave INANNA access to email.
Phase 8.4 gives INANNA access to documents.

Documents are the second most important communication
medium after email. INANNA must be able to:
  - Read any document (ODT, DOCX, PDF, TXT)
  - Write a new document from natural language
  - Edit existing documents
  - Save and export documents
  - Summarize long documents

Unlike email, documents exist as files. The Document Faculty
works at two levels:
  Level 1 — File level: read/write document files directly
             using Python libraries (python-docx, etc.)
             No UI automation needed. Fast, reliable, exact.
  Level 2 — Application level: open documents in LibreOffice
             and interact with the UI via Desktop Faculty
             (for complex editing, formatting, macros)

Level 1 is the primary approach — it is hardware-agnostic,
works without LibreOffice running, and produces no hallucination.
Level 2 is used only when Level 1 cannot accomplish the task
(e.g., rendering a document to PDF with LibreOffice formatting).

This follows the same ground-truth principle as ThunderbirdDirectReader:
access data at the source, not through the UI.

---

## Architecture Principle

```
Document request
    ↓
DocumentWorkflows.read_document(path)
    ↓
Level 1: DocumentDirectReader
  ├── .txt  → open() read
  ├── .md   → open() read
  ├── .docx → python-docx extract_text()
  ├── .odt  → odfpy or zipfile XML parse
  ├── .pdf  → pymupdf page.get_text()
  └── .xlsx / .ods → openpyxl / odfpy
    ↓
Returns: DocumentRecord(title, content, pages, word_count)
    ↓
Comprehension: structure + summary + key_points
    ↓
CROWN presents naturally
```

Level 2 (LibreOffice UI) used only for:
  - Creating richly formatted documents
  - Rendering to PDF via LibreOffice export
  - Complex table editing
  - Mail merge operations

---

## What You Are Building

### Task 1 — Add Python document libraries to requirements.txt

Add to inanna/requirements.txt:
```
# Document Faculty
python-docx>=1.1.0
python-pptx>=0.6.23
openpyxl>=3.1.0
pymupdf>=1.24.0
odfpy>=1.4.1
```

Also pip install them immediately:
```
pip install python-docx python-pptx openpyxl pymupdf odfpy --break-system-packages
```

Verify each installs cleanly. If pymupdf fails (it requires
build tools), use pypdf as fallback for PDF:
```
pip install pypdf --break-system-packages
```

### Task 2 — inanna/core/document_workflows.py

Create: inanna/core/document_workflows.py

```python
"""
INANNA NYX Document Faculty
Reads, writes, and manages documents.

Supported formats:
  Read:   .txt .md .docx .odt .pdf .xlsx .ods .csv
  Write:  .txt .md .docx .odt
  Export: .pdf (via LibreOffice CLI)

Architecture:
  Level 1 (primary): Direct file reading via Python libraries
    - No UI automation needed
    - Works without LibreOffice running
    - Ground truth data — no hallucination
  Level 2 (secondary): LibreOffice Desktop Faculty
    - Used for complex formatting tasks
    - Requires LibreOffice to be installed

Governance:
  Reading documents: no proposal required (observation)
  Writing new documents: proposal required
  Editing existing documents: proposal required (consequential)
  Deleting documents: FORBIDDEN (by design, Phase 7 rule)

See docs/platform_architecture.md for full platform context.
See docs/cycle8_master_plan.md for Cycle 8 architecture.
"""
from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.desktop_faculty import DesktopFaculty


@dataclass
class DocumentRecord:
    """Structured representation of a document's content."""
    path: str = ""
    title: str = ""
    format: str = ""         # txt, md, docx, odt, pdf, xlsx, csv
    content: str = ""        # full text content
    word_count: int = 0
    page_count: int = 0
    sheet_names: list[str] = field(default_factory=list)  # for spreadsheets
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.content or self.sheet_names)

    def summary_line(self) -> str:
        parts = [f"doc > {self.format}"]
        if self.title:
            parts.append(self.title[:50])
        if self.word_count:
            parts.append(f"{self.word_count} words")
        if self.page_count:
            parts.append(f"{self.page_count} pages")
        return " | ".join(parts)


@dataclass
class DocumentWriteResult:
    """Result of a document write operation."""
    success: bool
    path: str = ""
    format: str = ""
    word_count: int = 0
    error: Optional[str] = None


# ── DOCUMENT DIRECT READER ───────────────────────────────────────────
# Reads document files directly — no UI automation, no hallucination.
# This is the primary reading path for all document types.

class DocumentDirectReader:
    """
    Reads documents directly from the file system.
    No LibreOffice required. No UI automation.
    Returns structured DocumentRecord objects.
    """

    def read(self, path: str | Path) -> DocumentRecord:
        """
        Read any supported document format.
        Auto-detects format from file extension.
        """
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return DocumentRecord(
                path=str(p),
                error=f"File not found: {p}"
            )

        suffix = p.suffix.lower()
        record = DocumentRecord(path=str(p), format=suffix.lstrip("."))

        try:
            if suffix in (".txt", ".md", ".rst", ".log"):
                return self._read_text(p, record)
            elif suffix == ".docx":
                return self._read_docx(p, record)
            elif suffix == ".odt":
                return self._read_odt(p, record)
            elif suffix == ".pdf":
                return self._read_pdf(p, record)
            elif suffix in (".xlsx", ".xls"):
                return self._read_xlsx(p, record)
            elif suffix == ".ods":
                return self._read_ods(p, record)
            elif suffix == ".csv":
                return self._read_csv(p, record)
            else:
                record.error = f"Unsupported format: {suffix}"
                return record
        except Exception as e:
            record.error = str(e)
            return record

    def _read_text(self, p: Path, r: DocumentRecord) -> DocumentRecord:
        content = p.read_text(encoding="utf-8", errors="replace")
        r.title = p.stem
        r.content = content
        r.word_count = len(content.split())
        r.page_count = max(1, content.count("\f") + 1)
        return r

    def _read_docx(self, p: Path, r: DocumentRecord) -> DocumentRecord:
        try:
            import docx
            doc = docx.Document(str(p))
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            # Extract title from first heading or filename
            for para in doc.paragraphs:
                if para.style.name.startswith("Heading") and para.text.strip():
                    r.title = para.text.strip()
                    break
            if not r.title:
                r.title = p.stem
            r.content = "\n".join(paragraphs)
            r.word_count = len(r.content.split())
            # Approximate page count from section breaks
            r.page_count = max(1, len(doc.sections))
            return r
        except ImportError:
            r.error = "python-docx not installed. Run: pip install python-docx"
            return r

    def _read_odt(self, p: Path, r: DocumentRecord) -> DocumentRecord:
        # ODT is a ZIP containing XML — readable without odfpy
        try:
            import odf.opendocument
            import odf.text
            doc = odf.opendocument.load(str(p))
            texts = []
            for elem in doc.text.childNodes:
                if hasattr(elem, 'data'):
                    texts.append(elem.data)
                elif elem.qname[1] == 'p':
                    text = elem.firstChild.data if elem.firstChild else ""
                    if text.strip():
                        texts.append(text)
            r.title = p.stem
            r.content = "\n".join(t for t in texts if t.strip())
            r.word_count = len(r.content.split())
            return r
        except ImportError:
            pass
        # Fallback: read XML directly from ZIP
        try:
            with zipfile.ZipFile(str(p)) as z:
                with z.open("content.xml") as f:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(f)
                    texts = []
                    for elem in tree.iter():
                        if elem.text and elem.text.strip():
                            texts.append(elem.text.strip())
                    r.title = p.stem
                    r.content = "\n".join(texts)
                    r.word_count = len(r.content.split())
                    return r
        except Exception as e:
            r.error = f"Could not read ODT: {e}"
            return r

    def _read_pdf(self, p: Path, r: DocumentRecord) -> DocumentRecord:
        try:
            import fitz  # pymupdf
            doc = fitz.open(str(p))
            r.page_count = len(doc)
            r.title = doc.metadata.get("title") or p.stem
            pages = []
            for page in doc:
                pages.append(page.get_text())
            r.content = "\n\n".join(pages)
            r.word_count = len(r.content.split())
            doc.close()
            return r
        except ImportError:
            pass
        # Fallback: pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(str(p))
            r.page_count = len(reader.pages)
            r.title = (reader.metadata.get("/Title") or p.stem) if reader.metadata else p.stem
            pages = [page.extract_text() or "" for page in reader.pages]
            r.content = "\n\n".join(pages)
            r.word_count = len(r.content.split())
            return r
        except ImportError:
            r.error = "No PDF library installed. Run: pip install pymupdf"
            return r

    def _read_xlsx(self, p: Path, r: DocumentRecord) -> DocumentRecord:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(p), read_only=True, data_only=True)
            r.title = p.stem
            r.sheet_names = wb.sheetnames
            lines = []
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                lines.append(f"=== Sheet: {sheet_name} ===")
                for row in ws.iter_rows(max_row=100, values_only=True):
                    row_text = "\t".join(
                        str(v) if v is not None else "" for v in row
                    )
                    if row_text.strip():
                        lines.append(row_text)
            r.content = "\n".join(lines)
            r.word_count = len(r.content.split())
            wb.close()
            return r
        except ImportError:
            r.error = "openpyxl not installed. Run: pip install openpyxl"
            return r

    def _read_ods(self, p: Path, r: DocumentRecord) -> DocumentRecord:
        # ODS is a ZIP containing XML
        try:
            with zipfile.ZipFile(str(p)) as z:
                with z.open("content.xml") as f:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(f)
                    ns = {
                        "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
                        "text":  "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
                    }
                    lines = []
                    for sheet in tree.iter("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table"):
                        name = sheet.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}name", "")
                        lines.append(f"=== Sheet: {name} ===")
                        r.sheet_names.append(name)
                        for row in sheet.iter("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-row"):
                            cells = []
                            for cell in row.iter("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-cell"):
                                t = cell.find("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}p")
                                cells.append(t.text if t is not None and t.text else "")
                            row_text = "\t".join(cells)
                            if row_text.strip():
                                lines.append(row_text)
                    r.title = p.stem
                    r.content = "\n".join(lines)
                    r.word_count = len(r.content.split())
                    return r
        except Exception as e:
            r.error = f"Could not read ODS: {e}"
            return r

    def _read_csv(self, p: Path, r: DocumentRecord) -> DocumentRecord:
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
            r.title = p.stem
            r.content = "\n".join("\t".join(row) for row in rows[:200])
            r.word_count = sum(len(row) for row in rows)
            return r
        except Exception as e:
            r.error = f"Could not read CSV: {e}"
            return r


# ── DOCUMENT WRITER ──────────────────────────────────────────────────

class DocumentWriter:
    """
    Writes new documents to the file system.
    Supports .txt, .md, .docx formats.
    Writing always requires proposal approval (governed).
    """

    def write_text(
        self, path: str | Path, content: str
    ) -> DocumentWriteResult:
        """Write plain text or markdown file."""
        p = Path(path).expanduser().resolve()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return DocumentWriteResult(
                success=True,
                path=str(p),
                format=p.suffix.lstrip("."),
                word_count=len(content.split()),
            )
        except Exception as e:
            return DocumentWriteResult(success=False, path=str(p), error=str(e))

    def write_docx(
        self,
        path: str | Path,
        title: str = "",
        content: str = "",
        paragraphs: list[str] | None = None,
    ) -> DocumentWriteResult:
        """Write a .docx document."""
        try:
            import docx
        except ImportError:
            return DocumentWriteResult(
                success=False,
                path=str(path),
                error="python-docx not installed. Run: pip install python-docx",
            )
        p = Path(path).expanduser().resolve()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            doc = docx.Document()
            if title:
                doc.add_heading(title, level=1)
            # Split content into paragraphs if not provided explicitly
            paras = paragraphs or (content.split("\n\n") if content else [])
            for para_text in paras:
                para_text = para_text.strip()
                if para_text.startswith("# "):
                    doc.add_heading(para_text[2:], level=1)
                elif para_text.startswith("## "):
                    doc.add_heading(para_text[3:], level=2)
                elif para_text.startswith("### "):
                    doc.add_heading(para_text[4:], level=3)
                elif para_text:
                    doc.add_paragraph(para_text)
            doc.save(str(p))
            full_content = title + "\n\n" + content
            return DocumentWriteResult(
                success=True,
                path=str(p),
                format="docx",
                word_count=len(full_content.split()),
            )
        except Exception as e:
            return DocumentWriteResult(success=False, path=str(p), error=str(e))

    def export_pdf_via_libreoffice(
        self, input_path: str | Path, output_dir: str | Path | None = None
    ) -> DocumentWriteResult:
        """
        Export any document to PDF using LibreOffice CLI.
        Requires LibreOffice to be installed.
        Does not require the UI — uses headless mode.
        """
        import subprocess
        p = Path(input_path).expanduser().resolve()
        if not p.exists():
            return DocumentWriteResult(
                success=False, path=str(p),
                error=f"Input file not found: {p}"
            )
        out_dir = Path(output_dir).expanduser().resolve() if output_dir else p.parent
        # LibreOffice headless export
        cmd = [
            "soffice", "--headless", "--convert-to", "pdf",
            "--outdir", str(out_dir), str(p)
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            pdf_path = out_dir / (p.stem + ".pdf")
            if pdf_path.exists():
                return DocumentWriteResult(
                    success=True,
                    path=str(pdf_path),
                    format="pdf",
                )
            return DocumentWriteResult(
                success=False, path=str(pdf_path),
                error=f"PDF not created. stderr: {result.stderr[:200]}"
            )
        except subprocess.TimeoutExpired:
            return DocumentWriteResult(
                success=False, path=str(p),
                error="LibreOffice timed out during PDF export"
            )
        except FileNotFoundError:
            return DocumentWriteResult(
                success=False, path=str(p),
                error="LibreOffice (soffice) not found. Is it installed?"
            )


# ── DOCUMENT WORKFLOWS ───────────────────────────────────────────────

@dataclass
class DocumentComprehension:
    """
    Structured comprehension of a document.
    Produced after reading — given to CROWN for natural presentation.
    No LLM needed — pure deterministic analysis.
    """
    title: str = ""
    format: str = ""
    word_count: int = 0
    page_count: int = 0
    summary_lines: list[str] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)

    def to_crown_context(self) -> str:
        """Format for CROWN to present naturally."""
        lines = [
            f"DOCUMENT: {self.title} ({self.format})",
            f"Size: {self.word_count} words"
            + (f", {self.page_count} pages" if self.page_count > 1 else ""),
        ]
        if self.key_points:
            lines.append("KEY POINTS:")
            for kp in self.key_points[:5]:
                lines.append(f"  - {kp}")
        if self.suggested_actions:
            lines.append("SUGGESTED ACTIONS:")
            for a in self.suggested_actions[:3]:
                lines.append(f"  - {a}")
        return "\n".join(lines)


def build_document_comprehension(record: DocumentRecord) -> DocumentComprehension:
    """
    Build structured comprehension from a DocumentRecord.
    Extracts key points from content heuristically.
    No LLM — deterministic. No hallucination.
    """
    comp = DocumentComprehension(
        title=record.title,
        format=record.format,
        word_count=record.word_count,
        page_count=record.page_count,
    )
    if not record.content:
        return comp

    lines = [l.strip() for l in record.content.splitlines() if l.strip()]

    # Extract key points: headings, short bold-like lines, numbered items
    for line in lines[:200]:
        if len(line) < 120 and (
            line.startswith("#")
            or line[0].isupper() and line.endswith(":")
            or (line[0].isdigit() and ". " in line[:5])
        ):
            kp = line.lstrip("#").strip().rstrip(":")
            if kp and len(kp) > 5:
                comp.key_points.append(kp)
        if len(comp.key_points) >= 8:
            break

    # Summary: first 3 non-empty lines of real content
    content_lines = [
        l for l in lines if len(l) > 20 and not l.startswith("#")
    ]
    comp.summary_lines = content_lines[:3]

    # Suggested actions
    if record.format == "pdf":
        comp.suggested_actions.append("Ask INANNA to summarize specific sections")
    if record.word_count > 2000:
        comp.suggested_actions.append("Ask for a shorter summary")
    if record.format in ("xlsx", "ods", "csv"):
        comp.suggested_actions.append("Ask INANNA to explain the data")

    return comp


class DocumentWorkflows:
    """
    Orchestrates document reading and writing.
    Uses DocumentDirectReader (Level 1) as primary approach.
    Uses Desktop Faculty (Level 2) only when necessary.
    """

    def __init__(self, desktop: DesktopFaculty) -> None:
        self.desktop = desktop
        self.reader = DocumentDirectReader()
        self.writer = DocumentWriter()

    def read_document(self, path: str) -> tuple[DocumentRecord, DocumentComprehension]:
        """
        Read any document and return record + comprehension.
        No proposal needed — observation only.
        """
        record = self.reader.read(path)
        comp = build_document_comprehension(record)
        return record, comp

    def write_document(
        self,
        path: str,
        content: str,
        title: str = "",
        format: str = "txt",
    ) -> DocumentWriteResult:
        """
        Write a new document.
        Requires proposal approval — writing is consequential.
        """
        p = Path(path).expanduser()
        suffix = p.suffix.lower() or f".{format}"
        if suffix in (".docx",):
            return self.writer.write_docx(p, title=title, content=content)
        else:
            # txt, md, odt (odt as text for now)
            if title:
                content = f"# {title}\n\n{content}"
            return self.writer.write_text(p, content)

    def open_in_libreoffice(self, path: str) -> bool:
        """
        Open a document in LibreOffice via Desktop Faculty.
        Requires proposal approval.
        """
        result = self.desktop.open_app(f"soffice \"{path}\"")
        return result.success

    def export_to_pdf(
        self, input_path: str, output_dir: str | None = None
    ) -> DocumentWriteResult:
        """
        Export document to PDF using LibreOffice headless CLI.
        Requires proposal approval.
        """
        return self.writer.export_pdf_via_libreoffice(input_path, output_dir)

    def format_read_result(
        self, record: DocumentRecord, comp: DocumentComprehension
    ) -> str:
        """Format document read result for CROWN."""
        if not record.success:
            return f"doc > error: {record.error}"
        return comp.to_crown_context() + "\n\nCONTENT (first 1500 chars):\n" + record.content[:1500]

    def format_write_result(self, result: DocumentWriteResult) -> str:
        """Format document write result for CROWN."""
        if not result.success:
            return f"doc > write error: {result.error}"
        return (
            f"doc > written: {result.path}\n"
            f"Format: {result.format} | Words: {result.word_count}"
        )
```

### Task 3 — Register document tools in tools.json

Add to inanna/config/tools.json under category "document":

```json
"doc_read": {
  "display_name": "Read Document",
  "description": "Read any document file: txt, md, docx, odt, pdf, xlsx, csv",
  "category": "document",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "path": "File path to read (supports ~ expansion)"
  }
},
"doc_write": {
  "display_name": "Write Document",
  "description": "Write a new document file",
  "category": "document",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "path": "File path to write",
    "content": "Document content",
    "title": "Document title (optional)",
    "format": "Format: txt, md, docx (default: txt)"
  }
},
"doc_open": {
  "display_name": "Open in LibreOffice",
  "description": "Open a document in LibreOffice for viewing or editing",
  "category": "document",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "path": "File path to open"
  }
},
"doc_export_pdf": {
  "display_name": "Export to PDF",
  "description": "Export a document to PDF using LibreOffice",
  "category": "document",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "path": "Input document path",
    "output_dir": "Output directory (optional, defaults to same as input)"
  }
}
```

Total tools after this phase: 35

### Task 4 — Wire DocumentWorkflows into server.py and main.py

Add DOCUMENT_TOOL_NAMES:
```python
DOCUMENT_TOOL_NAMES = {
    "doc_read",
    "doc_write",
    "doc_open",
    "doc_export_pdf",
}
```

Instantiate in InterfaceServer.__init__:
```python
from core.document_workflows import DocumentWorkflows
self.document_workflows = DocumentWorkflows(self.desktop_faculty)
```

Add run_document_tool() following the established pattern.

For doc_read: call read_document(), build comprehension,
pass to_crown_context() as tool_result_summary.
No proposal needed — pure observation.

For doc_write, doc_open, doc_export_pdf: require proposal.

### Task 5 — Natural language routing in main.py

Add document domain hints to governance_signals.json:
```json
"document": [
  "read document", "open document", "read file", "open file",
  "read the", "summarize document", "what does the document say",
  "write a document", "create a document", "write a letter",
  "create a report", "write a report", "save as pdf",
  "export to pdf", "open in libreoffice", "open with libreoffice",
  "read pdf", "read docx", "read odt", "read the pdf",
  "what is in the file", "show me the document"
]
```

Add extract_document_tool_request() in main.py:

Patterns (with natural_match guard following the email pattern):
  "read [path]" → doc_read(path=path)
  "read the document at [path]" → doc_read
  "summarize [path]" → doc_read (output_format=summary)
  "write a document called [name] with [content]" → doc_write
  "open [path] in libreoffice" → doc_open
  "export [path] to pdf" → doc_export_pdf
  "create a letter to [name] saying [content]" → doc_write

### Task 6 — Update help_system.py

Add DOCUMENTS section to HELP_COMMON:
```
  DOCUMENTS (LibreOffice, PDF, DOCX, ODT)
    "read the document at ~/path/to/file.pdf"
                                       Read any document (no approval)
    "summarize ~/report.docx"          Summarize document (no approval)
    "write a document called report.txt saying..."
                                       Write document (approval required)
    "open ~/proposal.odt in libreoffice"
                                       Open in LibreOffice (approval)
    "export ~/letter.docx to pdf"      Export to PDF (approval)

  Supported: .txt .md .docx .odt .pdf .xlsx .ods .csv
  (reading never requires approval — writing always does)
```

### Task 7 — Update identity.py

CURRENT_PHASE = "Cycle 8 - Phase 8.4 - Document Faculty"

### Task 8 — Tests (all offline — no actual files required)

Create inanna/tests/test_document_workflows.py (20 tests):

  - DocumentWorkflows instantiates
  - DocumentDirectReader instantiates
  - DocumentWriter instantiates
  - DocumentRecord defaults are correct
  - DocumentRecord.success False when error set
  - DocumentRecord.success True when content present
  - DocumentRecord.summary_line includes format
  - build_document_comprehension returns correct word_count
  - build_document_comprehension extracts headings as key_points
  - build_document_comprehension.to_crown_context includes title
  - DocumentDirectReader._read_csv reads temp CSV correctly
  - DocumentDirectReader._read_text reads temp txt correctly
  - DocumentDirectReader handles missing file gracefully
  - DocumentDirectReader handles unsupported format gracefully
  - DocumentWriter.write_text creates file with correct content
  - DocumentWriter.write_text returns correct word_count
  - DOCUMENT_TOOL_NAMES contains all 4 tools
  - doc_read in tools.json with requires_approval=False
  - doc_write in tools.json with requires_approval=True
  - doc_open in tools.json with requires_approval=True

Update test_identity.py: CURRENT_PHASE assertion.
Update test_operator.py: PERMITTED_TOOLS includes doc tools.
Update test_commands.py: tool registry count updated to 35.

---

## NixOS Notes (for docs/nixos_document_faculty.md — create this)

On NixOS, the Python libraries are declared in configuration.nix:

```nix
environment.systemPackages = with pkgs; [
  python311Packages.python-docx
  python311Packages.pymupdf
  python311Packages.openpyxl
  # odfpy may need to be added as a custom package
  libreoffice-fresh  # for headless PDF export
];
```

LibreOffice CLI path on NixOS:
  soffice = ${pkgs.libreoffice-fresh}/bin/soffice

The DocumentWriter.export_pdf_via_libreoffice() method
uses `soffice` — this works identically on Windows and NixOS.

---

## Permitted file changes

inanna/core/document_workflows.py      <- NEW
inanna/main.py                         <- MODIFY: routing, DOCUMENT_TOOL_NAMES
inanna/ui/server.py                    <- MODIFY: wire DocumentWorkflows
inanna/config/tools.json               <- MODIFY: add 4 document tools
inanna/config/governance_signals.json  <- MODIFY: document domain hints
inanna/requirements.txt                <- MODIFY: add document libraries
inanna/core/help_system.py             <- MODIFY: document section
inanna/identity.py                     <- MODIFY: CURRENT_PHASE
inanna/tests/test_document_workflows.py <- NEW
inanna/tests/test_identity.py          <- MODIFY
inanna/tests/test_operator.py          <- MODIFY
inanna/tests/test_commands.py          <- MODIFY
docs/nixos_document_faculty.md         <- NEW (mandatory documentation)

---

## What You Are NOT Building

- No IMAP/SMTP (that was email)
- No browser automation (Phase 8.5)
- No calendar (Phase 8.6)
- No voice changes
- No auth changes
- Do not attempt to start LibreOffice in tests

---

## Definition of Done

- [ ] core/document_workflows.py complete with all classes
- [ ] Python document libraries installed and working
- [ ] 4 document tools in tools.json (35 total)
- [ ] Document domain hints in governance_signals.json
- [ ] DocumentWorkflows wired into server.py and main.py
- [ ] help_system.py updated with document section
- [ ] docs/nixos_document_faculty.md written
- [ ] CURRENT_PHASE = "Cycle 8 - Phase 8.4 - Document Faculty"
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle8-phase4-complete

---

## Handoff

Commit: cycle8-phase4-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE8_PHASE4_REPORT.md

The report MUST include:
  - Which Python libraries were installed successfully
  - Which formats were tested and confirmed working
  - Any formats that failed and why
  - NixOS equivalents for all dependencies

Stop. Do not begin Phase 8.5 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-22*
*Documents are memory made permanent.*
*INANNA reads what ZAERA writes.*
*INANNA writes what ZAERA speaks.*
*The document faculty is the bridge*
*between thought and record.*
*No hallucination — only what is on the page.*
*No invention — only what ZAERA approves.*
