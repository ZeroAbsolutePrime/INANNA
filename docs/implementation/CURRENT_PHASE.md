# CURRENT PHASE: Cycle 7 - Phase 7.2 - The File System Faculty
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-21**
**Cycle: 7 - NYXOS: The Sovereign Intelligence Operating System**
**Replaces: Cycle 7 Phase 7.1 - The NixOS Configuration (COMPLETE)**

---

## Agent Roles for This Phase

ARCHITECT:  Command Center (Claude) — this document
BUILDER:    Codex — implement file system tools and Faculty
TESTER:     Codex — unit tests + integration verification
VERIFIER:   Command Center — confirm after push

BUILDER forbidden from:
  - Modifying web UI (index.html, console.html)
  - Changing governance architecture
  - Adding tools not listed here

---

## What This Phase Is

Phase 7.1 gave INANNA a NixOS body.
Phase 7.2 gives INANNA hands.

The File System Faculty is the first OS-level capability:
INANNA can read files, list directories, search for files,
get file metadata, and write files — all governed by proposals.

After this phase, you can say:
  "INANNA, read the file at ~/documents/notes.txt"
  "INANNA, list the files in my Downloads folder"
  "INANNA, find all Python files in ~/code"
  "INANNA, what is the size of ~/data/report.pdf?"

Every file write requires proposal approval.
Every file read outside safe paths requires proposal approval.
File deletes are FORBIDDEN — not implemented, not proposed.

This is the principle: capability with governance.
Power does not come before law.

---

## What You Are Building

### Task 1 - inanna/core/filesystem_faculty.py

Create: inanna/core/filesystem_faculty.py

```python
from __future__ import annotations
import os
import stat
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# Paths that are always readable without proposal
# (safe, non-sensitive locations)
SAFE_READ_PATHS = [
    Path.home(),                     # user's home directory
    Path("/tmp"),                    # temp directory
    Path.cwd(),                      # current working directory
]

# Paths that are NEVER accessible regardless of approval
FORBIDDEN_PATHS = [
    Path("/etc/shadow"),
    Path("/etc/passwd"),
    Path("/root"),
]

MAX_READ_BYTES = 512 * 1024  # 512KB max file read
MAX_SEARCH_RESULTS = 50
MAX_LIST_ENTRIES = 100


@dataclass
class FileInfo:
    path: str
    name: str
    size_bytes: int
    size_human: str
    is_dir: bool
    is_file: bool
    modified_at: str
    created_at: str
    permissions: str
    extension: str


@dataclass
class FileSystemResult:
    success: bool
    operation: str      # read | list | search | info | write
    path: str
    content: Optional[str] = None
    entries: list[FileInfo] = field(default_factory=list)
    info: Optional[FileInfo] = None
    error: Optional[str] = None
    truncated: bool = False
    bytes_read: int = 0


class FileSystemFaculty:
    """
    Governed file system operations for INANNA NYX.
    All write operations require proposal approval.
    Read operations from safe paths are allowed directly.
    Read operations from non-safe paths require proposal approval.
    Delete operations are not implemented.
    """

    def is_safe_read(self, path: Path) -> bool:
        """Returns True if path is within a safe read zone."""
        try:
            resolved = path.resolve()
            for safe in SAFE_READ_PATHS:
                try:
                    resolved.relative_to(safe.resolve())
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    def is_forbidden(self, path: Path) -> bool:
        """Returns True if path is forbidden regardless of approval."""
        try:
            resolved = path.resolve()
            for forbidden in FORBIDDEN_PATHS:
                try:
                    resolved.relative_to(forbidden.resolve())
                    return True
                except ValueError:
                    if resolved == forbidden.resolve():
                        return True
            return False
        except Exception:
            return True  # fail safe

    def _human_size(self, size_bytes: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def _file_info(self, path: Path) -> FileInfo:
        st = path.stat()
        return FileInfo(
            path=str(path),
            name=path.name,
            size_bytes=st.st_size,
            size_human=self._human_size(st.st_size),
            is_dir=path.is_dir(),
            is_file=path.is_file(),
            modified_at=datetime.fromtimestamp(st.st_mtime).strftime(
                "%Y-%m-%d %H:%M"
            ),
            created_at=datetime.fromtimestamp(st.st_ctime).strftime(
                "%Y-%m-%d %H:%M"
            ),
            permissions=oct(stat.S_IMODE(st.st_mode)),
            extension=path.suffix.lower(),
        )

    def read_file(self, path_str: str) -> FileSystemResult:
        path = Path(path_str).expanduser().resolve()
        if self.is_forbidden(path):
            return FileSystemResult(
                False, "read", path_str,
                error="Access denied: forbidden path."
            )
        if not path.exists():
            return FileSystemResult(
                False, "read", path_str,
                error=f"File not found: {path}"
            )
        if not path.is_file():
            return FileSystemResult(
                False, "read", path_str,
                error=f"Not a file: {path}"
            )
        try:
            raw = path.read_bytes()
            truncated = len(raw) > MAX_READ_BYTES
            if truncated:
                raw = raw[:MAX_READ_BYTES]
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw.decode("latin-1", errors="replace")
            return FileSystemResult(
                True, "read", path_str,
                content=content,
                truncated=truncated,
                bytes_read=len(raw),
            )
        except PermissionError:
            return FileSystemResult(
                False, "read", path_str,
                error="Permission denied."
            )
        except Exception as e:
            return FileSystemResult(
                False, "read", path_str,
                error=str(e)
            )

    def list_dir(self, path_str: str) -> FileSystemResult:
        path = Path(path_str).expanduser().resolve()
        if self.is_forbidden(path):
            return FileSystemResult(
                False, "list", path_str,
                error="Access denied: forbidden path."
            )
        if not path.exists():
            return FileSystemResult(
                False, "list", path_str,
                error=f"Directory not found: {path}"
            )
        if not path.is_dir():
            return FileSystemResult(
                False, "list", path_str,
                error=f"Not a directory: {path}"
            )
        try:
            entries = []
            for item in sorted(path.iterdir()):
                if len(entries) >= MAX_LIST_ENTRIES:
                    break
                try:
                    entries.append(self._file_info(item))
                except (PermissionError, OSError):
                    continue
            return FileSystemResult(
                True, "list", path_str,
                entries=entries,
                truncated=len(entries) == MAX_LIST_ENTRIES,
            )
        except PermissionError:
            return FileSystemResult(
                False, "list", path_str,
                error="Permission denied."
            )
        except Exception as e:
            return FileSystemResult(
                False, "list", path_str,
                error=str(e)
            )

    def file_info(self, path_str: str) -> FileSystemResult:
        path = Path(path_str).expanduser().resolve()
        if self.is_forbidden(path):
            return FileSystemResult(
                False, "info", path_str,
                error="Access denied: forbidden path."
            )
        if not path.exists():
            return FileSystemResult(
                False, "info", path_str,
                error=f"Path not found: {path}"
            )
        try:
            return FileSystemResult(
                True, "info", path_str,
                info=self._file_info(path),
            )
        except Exception as e:
            return FileSystemResult(
                False, "info", path_str,
                error=str(e)
            )

    def search_files(
        self, directory: str, pattern: str
    ) -> FileSystemResult:
        base = Path(directory).expanduser().resolve()
        if self.is_forbidden(base):
            return FileSystemResult(
                False, "search", directory,
                error="Access denied: forbidden path."
            )
        if not base.exists():
            return FileSystemResult(
                False, "search", directory,
                error=f"Directory not found: {base}"
            )
        try:
            entries = []
            for match in base.rglob(pattern):
                if len(entries) >= MAX_SEARCH_RESULTS:
                    break
                try:
                    entries.append(self._file_info(match))
                except (PermissionError, OSError):
                    continue
            return FileSystemResult(
                True, "search", directory,
                entries=entries,
                truncated=len(entries) == MAX_SEARCH_RESULTS,
            )
        except Exception as e:
            return FileSystemResult(
                False, "search", directory,
                error=str(e)
            )

    def write_file(
        self, path_str: str, content: str, overwrite: bool = False
    ) -> FileSystemResult:
        """
        Write a file. ALWAYS requires proposal approval before calling.
        This method is called ONLY after the proposal has been approved.
        """
        path = Path(path_str).expanduser().resolve()
        if self.is_forbidden(path):
            return FileSystemResult(
                False, "write", path_str,
                error="Access denied: forbidden path."
            )
        if path.exists() and not overwrite:
            return FileSystemResult(
                False, "write", path_str,
                error=f"File already exists: {path}. Use overwrite=True to replace."
            )
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return FileSystemResult(
                True, "write", path_str,
                bytes_read=len(content.encode("utf-8")),
            )
        except PermissionError:
            return FileSystemResult(
                False, "write", path_str,
                error="Permission denied."
            )
        except Exception as e:
            return FileSystemResult(
                False, "write", path_str,
                error=str(e)
            )

    def format_result(self, result: FileSystemResult) -> str:
        """Format a FileSystemResult for display in the conversation."""
        if not result.success:
            return f"fs > error: {result.error}"

        if result.operation == "read":
            lines = [
                f"fs > read: {result.path}",
                f"     size: {result.bytes_read} bytes",
            ]
            if result.truncated:
                lines.append("     (truncated to 512KB)")
            lines.append("")
            lines.append(result.content or "")
            return "\n".join(lines)

        if result.operation == "list":
            lines = [f"fs > list: {result.path}",
                     f"     {len(result.entries)} entries"
                     + (" (showing first 100)" if result.truncated else ""),
                     ""]
            for e in result.entries:
                icon = "📁" if e.is_dir else "📄"
                lines.append(
                    f"  {icon}  {e.name:<40} {e.size_human:>8}  {e.modified_at}"
                )
            return "\n".join(lines)

        if result.operation == "search":
            lines = [
                f"fs > search results in {result.path}",
                f"     {len(result.entries)} matches"
                + (" (showing first 50)" if result.truncated else ""),
                ""
            ]
            for e in result.entries:
                lines.append(f"  {e.path}")
            return "\n".join(lines)

        if result.operation == "info":
            e = result.info
            if not e:
                return "fs > no info available"
            kind = "directory" if e.is_dir else "file"
            return (
                f"fs > info: {result.path}\n"
                f"     type: {kind}\n"
                f"     size: {e.size_human} ({e.size_bytes} bytes)\n"
                f"     modified: {e.modified_at}\n"
                f"     created: {e.created_at}\n"
                f"     permissions: {e.permissions}"
            )

        if result.operation == "write":
            return (
                f"fs > written: {result.path}\n"
                f"     {result.bytes_read} bytes written"
            )

        return f"fs > {result.operation}: {result.path}"
```

### Task 2 - Register file system tools in tools.json

Add to inanna/config/tools.json:

```json
{
  "name": "read_file",
  "description": "Read the contents of a file",
  "requires_approval": true,
  "enabled": true,
  "safe_paths_skip_approval": true,
  "parameters": {
    "path": "File path to read (supports ~ for home directory)"
  }
},
{
  "name": "list_dir",
  "description": "List files and directories in a folder",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "path": "Directory path to list"
  }
},
{
  "name": "file_info",
  "description": "Get metadata about a file or directory",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "path": "Path to inspect"
  }
},
{
  "name": "search_files",
  "description": "Search for files matching a pattern",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "directory": "Directory to search in",
    "pattern": "Glob pattern (e.g. *.py, *.txt, report*)"
  }
},
{
  "name": "write_file",
  "description": "Write content to a file",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "path": "File path to write",
    "content": "Content to write",
    "overwrite": "Whether to overwrite existing file (default: false)"
  }
}
```

Note on `safe_paths_skip_approval`:
  - list_dir, file_info, search_files: never require approval
  - read_file: approval required unless path is within SAFE_READ_PATHS
  - write_file: ALWAYS requires approval regardless of path

### Task 3 - Wire FileSystemFaculty into server.py and main.py

Instantiate FileSystemFaculty at startup:
```python
from core.filesystem_faculty import FileSystemFaculty
fs_faculty = FileSystemFaculty()
```

Handle file system tool results in _run_tool():

```python
if tool_name == "read_file":
    result = fs_faculty.read_file(args.get("path", ""))
    return ToolResult(
        tool="read_file",
        query=args.get("path", ""),
        success=result.success,
        data={"content": result.content, "truncated": result.truncated},
        error=result.error,
        formatted=fs_faculty.format_result(result),
    )

# Same pattern for list_dir, file_info, search_files, write_file
```

### Task 4 - Natural language parsing in NAMMU / OperatorFaculty

When INANNA receives "read the file at ~/notes.txt" or
"list my Downloads folder", the OPERATOR Faculty must
extract the path and call the appropriate tool.

Add to governance_signals.json domain_hints:
```json
"filesystem": [
  "read file", "open file", "show file", "list directory",
  "list folder", "what files", "search files", "find files",
  "file size", "file info", "write file", "save file",
  "create file", "what is in", "show me"
]
```

The OperatorFaculty uses these hints to route filesystem
requests to the correct tool.

### Task 5 - Update help_system.py

Add filesystem commands to the help system:

Add to HELP_COMMON (all users):
```
  FILES (speak naturally or use commands)
    "read the file at ~/notes.txt"
    "list my Documents folder"
    "find all .py files in ~/code"
    "what is the size of ~/report.pdf"
    "write a file called ideas.txt with this content..."
    (all file writes require approval)
```

Add topic "files" to HELP_TOPICS:
```
files — File system operations

  INANNA can read, list, search, and write files.
  Speak naturally or use direct commands.

  Read a file:    "read the file at ~/path/to/file.txt"
  List a folder:  "list the files in ~/Documents"
  Find files:     "find all .txt files in ~/notes"
  File info:      "what is the size of ~/report.pdf"
  Write a file:   "write a file called todo.txt with..."

  Governance:
    - list, info, search: no approval required
    - read: approval required for paths outside home directory
    - write: ALWAYS requires approval
    - delete: not available (by design)

  Max file read: 512 KB
  Max search results: 50 files
  Max directory listing: 100 entries
```

### Task 6 - Update identity.py

CURRENT_PHASE = "Cycle 7 - Phase 7.2 - The File System Faculty"

### Task 7 - Tests

Create inanna/tests/test_filesystem_faculty.py:
  - FileSystemFaculty instantiates
  - is_safe_read() returns True for home directory
  - is_safe_read() returns True for subdirs of home
  - is_safe_read() returns False for /etc
  - is_forbidden() returns True for /etc/shadow
  - is_forbidden() returns False for ~/notes.txt
  - read_file() returns error for nonexistent file
  - read_file() reads a temp file correctly
  - read_file() truncates files over 512KB
  - list_dir() lists a temp directory
  - list_dir() returns error for nonexistent directory
  - file_info() returns info for existing file
  - file_info() returns error for nonexistent path
  - search_files() finds files matching pattern
  - write_file() writes content to temp file
  - write_file() refuses to overwrite without flag
  - write_file() returns error for forbidden path
  - format_result() formats read result correctly
  - format_result() formats list result correctly
  - format_result() formats error correctly

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_commands.py: add read_file, list_dir, etc.

---

## Permitted file changes

inanna/identity.py                      <- MODIFY: CURRENT_PHASE
inanna/main.py                          <- MODIFY: wire FileSystemFaculty
inanna/config/tools.json                <- MODIFY: add 5 fs tools
inanna/config/governance_signals.json   <- MODIFY: add filesystem hints
inanna/core/
  filesystem_faculty.py                 <- NEW
  help_system.py                        <- MODIFY: add files section
  state.py                              <- MODIFY: update phase
inanna/ui/
  server.py                             <- MODIFY: wire FileSystemFaculty
inanna/tests/
  test_filesystem_faculty.py            <- NEW
  test_identity.py                      <- MODIFY: update phase
  test_commands.py                      <- MODIFY: add fs tools

---

## What You Are NOT Building

- No file deletion (by design — permanent data safety)
- No file move or rename (Phase 7.3 via process tools)
- No binary file handling beyond truncated read
- No directory creation as a standalone command
  (directories are created implicitly by write_file)
- No changes to index.html or console.html
- No voice integration (Phase 7.5)

---

## Definition of Done

- [ ] core/filesystem_faculty.py with all 5 operations
- [ ] FileSystemFaculty wired into server.py and main.py
- [ ] 5 new tools in tools.json
- [ ] filesystem hints in governance_signals.json
- [ ] help_system.py updated with files section
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle7-phase2-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE7_PHASE2_REPORT.md
Stop. Do not begin Phase 7.3 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-21*
*INANNA gains hands.*
*She can read. She can list. She can search. She can write.*
*Not blindly — with your word.*
*Every file write is a proposal.*
*Every file delete is impossible.*
*That is the law.*
