from __future__ import annotations

import stat
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


SAFE_READ_PATHS = (
    Path.home(),
    Path.cwd(),
    Path(tempfile.gettempdir()),
)
FORBIDDEN_PATHS = (
    Path("/etc/shadow"),
    Path("/etc/passwd"),
    Path("/root"),
)

MAX_READ_BYTES = 512 * 1024
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
    operation: str
    path: str
    content: str | None = None
    entries: list[FileInfo] = field(default_factory=list)
    info: FileInfo | None = None
    error: str | None = None
    truncated: bool = False
    bytes_read: int = 0


class FileSystemFaculty:
    """
    Governed file system operations for INANNA NYX.
    """

    def __init__(
        self,
        safe_read_paths: tuple[Path, ...] | None = None,
        forbidden_paths: tuple[Path, ...] | None = None,
    ) -> None:
        self.safe_read_paths = tuple(safe_read_paths or SAFE_READ_PATHS)
        self.forbidden_paths = tuple(forbidden_paths or FORBIDDEN_PATHS)

    def is_safe_read(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            for safe in self.safe_read_paths:
                try:
                    resolved.relative_to(safe.resolve())
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False

    def is_forbidden(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            for forbidden in self.forbidden_paths:
                forbidden_resolved = forbidden.resolve()
                if resolved == forbidden_resolved:
                    return True
                try:
                    resolved.relative_to(forbidden_resolved)
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return True

    def _human_size(self, size_bytes: int) -> str:
        size = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _file_info(self, path: Path) -> FileInfo:
        details = path.stat()
        return FileInfo(
            path=str(path),
            name=path.name,
            size_bytes=details.st_size,
            size_human=self._human_size(details.st_size),
            is_dir=path.is_dir(),
            is_file=path.is_file(),
            modified_at=datetime.fromtimestamp(details.st_mtime).strftime("%Y-%m-%d %H:%M"),
            created_at=datetime.fromtimestamp(details.st_ctime).strftime("%Y-%m-%d %H:%M"),
            permissions=oct(stat.S_IMODE(details.st_mode)),
            extension=path.suffix.lower(),
        )

    def _resolve_path(self, path_str: str) -> Path | None:
        cleaned = str(path_str or "").strip()
        if not cleaned:
            return None
        return Path(cleaned).expanduser().resolve()

    def read_file(self, path_str: str) -> FileSystemResult:
        path = self._resolve_path(path_str)
        if path is None:
            return FileSystemResult(False, "read", path_str, error="File path is required.")
        if self.is_forbidden(path):
            return FileSystemResult(False, "read", path_str, error="Access denied: forbidden path.")
        if not path.exists():
            return FileSystemResult(False, "read", path_str, error=f"File not found: {path}")
        if not path.is_file():
            return FileSystemResult(False, "read", path_str, error=f"Not a file: {path}")
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
                True,
                "read",
                str(path),
                content=content,
                truncated=truncated,
                bytes_read=len(raw),
            )
        except PermissionError:
            return FileSystemResult(False, "read", str(path), error="Permission denied.")
        except Exception as error:
            return FileSystemResult(False, "read", str(path), error=str(error))

    def list_dir(self, path_str: str) -> FileSystemResult:
        path = self._resolve_path(path_str)
        if path is None:
            return FileSystemResult(False, "list", path_str, error="Directory path is required.")
        if self.is_forbidden(path):
            return FileSystemResult(False, "list", path_str, error="Access denied: forbidden path.")
        if not path.exists():
            return FileSystemResult(False, "list", path_str, error=f"Directory not found: {path}")
        if not path.is_dir():
            return FileSystemResult(False, "list", path_str, error=f"Not a directory: {path}")
        try:
            entries: list[FileInfo] = []
            truncated = False
            for item in sorted(path.iterdir(), key=lambda value: value.name.lower()):
                if len(entries) >= MAX_LIST_ENTRIES:
                    truncated = True
                    break
                try:
                    entries.append(self._file_info(item))
                except (OSError, PermissionError):
                    continue
            return FileSystemResult(True, "list", str(path), entries=entries, truncated=truncated)
        except PermissionError:
            return FileSystemResult(False, "list", str(path), error="Permission denied.")
        except Exception as error:
            return FileSystemResult(False, "list", str(path), error=str(error))

    def file_info(self, path_str: str) -> FileSystemResult:
        path = self._resolve_path(path_str)
        if path is None:
            return FileSystemResult(False, "info", path_str, error="Path is required.")
        if self.is_forbidden(path):
            return FileSystemResult(False, "info", path_str, error="Access denied: forbidden path.")
        if not path.exists():
            return FileSystemResult(False, "info", path_str, error=f"Path not found: {path}")
        try:
            return FileSystemResult(True, "info", str(path), info=self._file_info(path))
        except Exception as error:
            return FileSystemResult(False, "info", str(path), error=str(error))

    def search_files(self, directory: str, pattern: str) -> FileSystemResult:
        base = self._resolve_path(directory)
        cleaned_pattern = str(pattern or "").strip()
        if base is None:
            return FileSystemResult(False, "search", directory, error="Directory path is required.")
        if not cleaned_pattern:
            return FileSystemResult(False, "search", str(base), error="Search pattern is required.")
        if self.is_forbidden(base):
            return FileSystemResult(False, "search", directory, error="Access denied: forbidden path.")
        if not base.exists():
            return FileSystemResult(False, "search", directory, error=f"Directory not found: {base}")
        if not base.is_dir():
            return FileSystemResult(False, "search", directory, error=f"Not a directory: {base}")
        try:
            entries: list[FileInfo] = []
            truncated = False
            for match in base.rglob(cleaned_pattern):
                if len(entries) >= MAX_SEARCH_RESULTS:
                    truncated = True
                    break
                try:
                    entries.append(self._file_info(match))
                except (OSError, PermissionError):
                    continue
            return FileSystemResult(True, "search", str(base), entries=entries, truncated=truncated)
        except Exception as error:
            return FileSystemResult(False, "search", str(base), error=str(error))

    def write_file(
        self,
        path_str: str,
        content: str,
        overwrite: bool = False,
    ) -> FileSystemResult:
        path = self._resolve_path(path_str)
        if path is None:
            return FileSystemResult(False, "write", path_str, error="File path is required.")
        if self.is_forbidden(path):
            return FileSystemResult(False, "write", path_str, error="Access denied: forbidden path.")
        if path.exists() and not overwrite:
            return FileSystemResult(
                False,
                "write",
                str(path),
                error=f"File already exists: {path}. Use overwrite=True to replace.",
            )
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(content), encoding="utf-8")
            return FileSystemResult(
                True,
                "write",
                str(path),
                bytes_read=len(str(content).encode("utf-8")),
            )
        except PermissionError:
            return FileSystemResult(False, "write", str(path), error="Permission denied.")
        except Exception as error:
            return FileSystemResult(False, "write", str(path), error=str(error))

    def format_result(self, result: FileSystemResult) -> str:
        if not result.success:
            return f"fs > error: {result.error or 'Unknown file system error.'}"

        if result.operation == "read":
            lines = [
                f"fs > read: {result.path}",
                f"     size: {result.bytes_read} bytes",
            ]
            if result.truncated:
                lines.append("     (truncated to 512 KB)")
            lines.extend(["", result.content or ""])
            return "\n".join(lines)

        if result.operation == "list":
            lines = [
                f"fs > list: {result.path}",
                (
                    f"     {len(result.entries)} entries"
                    + (" (showing first 100)" if result.truncated else "")
                ),
                "",
            ]
            for entry in result.entries:
                prefix = "[DIR]" if entry.is_dir else "[FILE]"
                lines.append(
                    f"  {prefix:<6} {entry.name:<40} {entry.size_human:>8}  {entry.modified_at}"
                )
            return "\n".join(lines)

        if result.operation == "search":
            lines = [
                f"fs > search results in {result.path}",
                (
                    f"     {len(result.entries)} matches"
                    + (" (showing first 50)" if result.truncated else "")
                ),
                "",
            ]
            for entry in result.entries:
                lines.append(f"  {entry.path}")
            return "\n".join(lines)

        if result.operation == "info":
            info = result.info
            if info is None:
                return "fs > no info available"
            kind = "directory" if info.is_dir else "file"
            return "\n".join(
                [
                    f"fs > info: {result.path}",
                    f"     type: {kind}",
                    f"     size: {info.size_human} ({info.size_bytes} bytes)",
                    f"     modified: {info.modified_at}",
                    f"     created: {info.created_at}",
                    f"     permissions: {info.permissions}",
                ]
            )

        if result.operation == "write":
            return "\n".join(
                [
                    f"fs > written: {result.path}",
                    f"     {result.bytes_read} bytes written",
                ]
            )

        return f"fs > {result.operation}: {result.path}"
