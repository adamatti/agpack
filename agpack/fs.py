"""Shared filesystem helpers.

Atomic file I/O and directory-traversal helpers used across the codebase: the copy kinds and
:mod:`agpack.kinds.edit_file` for deploying files, the CLI for counting source files, and the lockfile writer for its
own atomic write. A stdlib-only leaf so any of those can import it without importing each other's layer. Nothing
kind-specific belongs here — if you find yourself about to add behaviour that knows about a single kind, put it in
that kind's module instead. Exception types live in :mod:`agpack.errors`.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path


@contextlib.contextmanager
def atomic_replace(target: Path, *, prefix: str) -> Iterator[Path]:
    """Yield a fresh temp path beside *target*; on clean exit, atomically rename it onto *target*.

    The caller writes its content to the yielded path (``shutil.copy2``, ``write_text``, ...). On success the temp
    file replaces *target* in one ``rename``; if the body raises, the temp file is unlinked and the exception
    propagates, so *target* is never left half-written. *prefix* names the temp file so callers stay individually
    identifiable (and so prefix-checking tests keep passing).
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=target.parent, prefix=prefix)
    tmp = Path(tmp_path)
    try:
        os.close(fd)
        yield tmp
        tmp.replace(target)
    except Exception:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise


def iter_tree_files(root: Path) -> Iterator[Path]:
    """Yield every real file under *root* (sorted), skipping anything inside a ``.git`` path.

    The single source of truth for "the files a copy kind actually deploys" — used both to copy a tree and to count
    it, so the count can't drift from what gets copied.
    """
    for path in sorted(root.rglob("*")):
        if path.is_file() and not any(part.startswith(".git") for part in path.relative_to(root).parts):
            yield path


def atomic_copy_file(src: Path, dst: Path) -> None:
    """Copy a file atomically using write-to-temp-then-rename."""
    with atomic_replace(dst, prefix=".agpack-tmp-") as tmp:
        shutil.copy2(src, tmp)


def _atomic_write(path: Path, content: str) -> None:
    """Write text content to a file atomically."""
    with atomic_replace(path, prefix=".agpack-edit-") as tmp:
        tmp.write_text(content, encoding="utf-8")


def write_if_changed(path: Path, new_text: str) -> bool:
    """Atomic write, but skip when the file already has this exact content.

    Returns ``True`` if a write happened, ``False`` if we noticed the file was already byte-identical and skipped. This
    is what keeps every-sync churn off the user's structured config files when nothing semantically changed.
    """
    try:
        if path.read_text(encoding="utf-8") == new_text:
            return False
    except OSError:
        pass  # Missing or unreadable — fall through to the write.
    _atomic_write(path, new_text)
    return True


def copy_tree(src_dir: Path, dst_dir: Path) -> list[str]:
    """Recursively copy a directory; return absolute destination paths."""
    deployed: list[str] = []
    for src_file in iter_tree_files(src_dir):
        dst_file = dst_dir / src_file.relative_to(src_dir)
        atomic_copy_file(src_file, dst_file)
        deployed.append(str(dst_file))
    return deployed


def find_asset_subfolders(path: Path) -> list[Path]:
    """Return immediate subdirectories that contain at least one file."""
    subfolders: list[Path] = []
    for item in sorted(path.iterdir()):
        if item.is_dir() and not item.name.startswith(".git") and next(iter_tree_files(item), None) is not None:
            subfolders.append(item)
    return subfolders


def find_top_level_files(path: Path) -> list[Path]:
    """Return non-hidden files at the top level of a directory."""
    return sorted(item for item in path.iterdir() if item.is_file() and not item.name.startswith("."))
