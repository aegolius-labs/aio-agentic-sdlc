import hashlib
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from filelock import FileLock

from .dag_store import guarded_directory_path, guarded_file_path
from .mapping import MappingEngine, MappingError
from .workspace import WORKSPACE_DIR


class TemplateValidationError(ValueError):
    """Raised when caller-provided template data cannot render a document."""


class TemplateNotFoundError(FileNotFoundError):
    """Raised when a requested framework template is unavailable."""


@dataclass(frozen=True)
class _OutputSnapshot:
    identity: tuple[int, int]
    mode: int
    sha256: str


def _snapshot_output(path: Path) -> _OutputSnapshot:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        leaf = os.stat(path, follow_symlinks=False)
        identity = (opened.st_dev, opened.st_ino)
        if (
            not stat.S_ISREG(opened.st_mode)
            or identity != (leaf.st_dev, leaf.st_ino)
            or opened.st_nlink != 1
            or leaf.st_nlink != 1
        ):
            raise TemplateValidationError("document output identity is unsafe")
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        return _OutputSnapshot(
            identity=identity,
            mode=stat.S_IMODE(opened.st_mode),
            sha256=digest.hexdigest(),
        )
    finally:
        os.close(descriptor)


def _output_matches(path: Path, snapshot: _OutputSnapshot) -> bool:
    try:
        return _snapshot_output(path) == snapshot
    except (OSError, TemplateValidationError):
        return False


def _document_recovery_directory(project_root: Path) -> Path:
    recovery_leaf = guarded_file_path(
        project_root
        / WORKSPACE_DIR
        / "backups"
        / "document-transitions"
        / ".reservation",
        create_parent=True,
    )
    return guarded_directory_path(recovery_leaf.parent)


def _unique_output_leaf(
    output: Path,
    recovery_directory: Path,
    suffix: str,
) -> Path:
    for _ in range(32):
        candidate = recovery_directory / (
            f".{output.name}.{secrets.token_hex(16)}{suffix}"
        )
        if not os.path.lexists(candidate):
            return guarded_file_path(candidate)
    raise TemplateValidationError("could not allocate a document recovery path")


def _move_output_no_replace(source: Path, destination: Path) -> None:
    try:
        MappingEngine._move_no_replace(source, destination)
    except MappingError as error:
        raise TemplateValidationError("document output changed during write") from error


def _write_output_staging(
    output: Path,
    recovery_directory: Path,
    payload: bytes,
) -> tuple[Path, _OutputSnapshot]:
    temporary = _unique_output_leaf(output, recovery_directory, ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            opened = os.fstat(handle.fileno())
            staged = _OutputSnapshot(
                identity=(opened.st_dev, opened.st_ino),
                mode=stat.S_IMODE(opened.st_mode),
                sha256=hashlib.sha256(payload).hexdigest(),
            )
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    if not _output_matches(temporary, staged):
        raise TemplateValidationError("document staging changed during write")
    return temporary, staged


def get_package_templates_dir() -> Path:
    """Return the templates bundled with the installed framework package."""

    return Path(__file__).parent / "templates"


def generate_document(
    template_name: str,
    data: Dict[str, Any],
    output_path: str,
    templates_dir: Optional[str] = None,
    project_path: Optional[str] = None,
) -> str:
    """
    Generates a document from a Jinja2 template and writes it to output_path.

    Args:
        template_name: The name of the template file in the templates/ directory.
        data: A dictionary of data to populate the template.
        output_path: The path where the generated document will be saved.
        templates_dir: Optional explicit template directory. When omitted, use the templates
            bundled with the installed framework package.
        project_path: Optional project root for private recovery artifacts. When omitted, the
            output directory is treated as the project root.

    Returns:
        The content of the generated document.
    """
    if templates_dir is not None:
        resolved_templates_dir = Path(templates_dir)
    else:
        resolved_templates_dir = get_package_templates_dir()

    if not resolved_templates_dir.exists():
        raise TemplateNotFoundError(
            f"Templates directory not found at {resolved_templates_dir}"
        )

    import jinja2.sandbox

    env = jinja2.sandbox.SandboxedEnvironment(
        loader=jinja2.FileSystemLoader(str(resolved_templates_dir)),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
    )

    try:
        template = env.get_template(template_name)
    except jinja2.TemplateNotFound:
        raise TemplateNotFoundError(
            f"Template '{template_name}' not found in {resolved_templates_dir}"
        )

    try:
        rendered_content = template.render(**data)
    except jinja2.exceptions.UndefinedError as e:
        raise TemplateValidationError(
            f"Template validation error: missing data field - {str(e)}"
        )

    out_file = guarded_file_path(output_path, create_parent=True)
    lock_file = guarded_file_path(
        out_file.parent / f".{out_file.name}.lock",
        create_parent=True,
    )
    payload = rendered_content.encode("utf-8")
    with FileLock(lock_file, timeout=30, preserve_lock_file=True):
        out_file = guarded_file_path(out_file)
        recovery_directory = _document_recovery_directory(
            Path(project_path).resolve()
            if project_path is not None
            else out_file.parent
        )
        previous = _snapshot_output(out_file) if os.path.lexists(out_file) else None
        temporary, staged = _write_output_staging(
            out_file,
            recovery_directory,
            payload,
        )
        backup: Path | None = None
        if previous is not None:
            backup = _unique_output_leaf(
                out_file,
                recovery_directory,
                ".document-backup",
            )
            _move_output_no_replace(out_file, backup)
            if not _output_matches(backup, previous):
                try:
                    _move_output_no_replace(backup, out_file)
                except TemplateValidationError:
                    pass
                raise TemplateValidationError("document output changed during write")
        try:
            _move_output_no_replace(temporary, out_file)
            if not _output_matches(out_file, staged):
                quarantine = _unique_output_leaf(
                    out_file,
                    recovery_directory,
                    ".document-conflict",
                )
                try:
                    _move_output_no_replace(out_file, quarantine)
                except TemplateValidationError:
                    pass
                if backup is not None:
                    try:
                        _move_output_no_replace(backup, out_file)
                    except TemplateValidationError:
                        pass
                raise TemplateValidationError("document output changed during write")
        except Exception:
            if backup is not None and not os.path.lexists(out_file):
                try:
                    _move_output_no_replace(backup, out_file)
                except TemplateValidationError:
                    pass
            raise

    return rendered_content
