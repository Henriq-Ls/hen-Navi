"""Helpers for preparing directory uploads for QtWebEngine."""

from __future__ import annotations

import os
from pathlib import Path


def collect_folder_upload_files(folder_path: str) -> list[str] | None:
    """Return upload files with a root-level file first, or None if unavailable.

    QtWebEngine treats a selected directory as an instruction to recursively
    enumerate it. Its directory entries can become ``/.`` paths in the upload
    list. Returning the real files directly avoids those markers while keeping
    the selected folder as the upload base directory. QtWebEngine derives that
    base directory from the first returned file, so this is only safe when the
    selected folder has at least one regular file at its root.
    """
    root = Path(os.path.abspath(os.path.expanduser(folder_path)))
    if root.is_symlink() or not root.is_dir():
        raise ValueError("A pasta selecionada não existe ou não pode ser lida.")

    root_key = os.path.normcase(str(root))
    root_files: list[str] = []
    nested_files: list[str] = []

    def raise_walk_error(error: OSError):
        raise error

    for current, directories, filenames in os.walk(
        root,
        topdown=True,
        onerror=raise_walk_error,
        followlinks=False,
    ):
        current_path = Path(current)
        directories[:] = sorted(
            (
                name
                for name in directories
                if not (current_path / name).is_symlink()
            ),
            key=str.casefold,
        )
        for name in filenames:
            file_path = current_path / name
            if file_path.is_symlink() or not file_path.is_file():
                continue
            absolute_path = str(file_path.absolute())
            if os.path.normcase(str(file_path.parent.absolute())) == root_key:
                root_files.append(absolute_path)
            else:
                nested_files.append(absolute_path)

    root_files.sort(key=lambda path: Path(path).name.casefold())
    nested_files.sort(key=lambda path: os.path.relpath(path, root).casefold())
    if root_files:
        return root_files + nested_files
    if nested_files:
        return None
    return []
