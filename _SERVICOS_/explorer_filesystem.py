"""Leitura segura de diretórios e geração de árvores sem acesso ao conteúdo."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import stat
import time
from threading import Event
from typing import Iterable


class ExplorerError(ValueError):
    """Erro seguro de validação ou leitura do Explorador."""


class ExplorerOutsideRootError(ExplorerError):
    """O caminho pedido não pertence à raiz escolhida."""


class ExplorerLinkError(ExplorerError):
    """Um link simbólico ou ponto de reanálise não pode ser atravessado."""


class ExplorerCancelled(Exception):
    """A operação foi cancelada cooperativamente."""


@dataclass(frozen=True)
class ExplorerLimits:
    max_items: int
    max_seconds: float
    max_depth: int
    max_lines: int
    max_chars: int = 40000

    def __post_init__(self):
        if self.max_items < 1:
            raise ValueError("max_items precisa ser positivo")
        if self.max_seconds <= 0:
            raise ValueError("max_seconds precisa ser positivo")
        if self.max_depth < 1:
            raise ValueError("max_depth precisa ser positivo")
        if self.max_lines < 2:
            raise ValueError("max_lines precisa ser pelo menos 2")
        if self.max_chars < 128:
            raise ValueError("max_chars precisa ser pelo menos 128")


@dataclass(frozen=True)
class ExplorerEntry:
    name: str
    relative_path: str
    kind: str
    folder_count: int | None = None
    file_count: int | None = None
    counts_incomplete: bool = False


@dataclass(frozen=True)
class ExplorerScanResult:
    root: str
    directory: str
    entries: tuple[ExplorerEntry, ...]
    incomplete: bool = False
    limit_reason: str = ""
    error: str = ""


@dataclass(frozen=True)
class ExplorerTreeResult:
    text: str
    included_count: int
    omitted_count: int
    incomplete: bool
    limit_reason: str = ""
    omitted_count_exact: bool = True


def _is_reparse_point(path: Path, info) -> bool:
    if stat.S_ISLNK(info.st_mode):
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction):
        try:
            if is_junction():
                return True
        except OSError:
            return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _inside_root(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def canonical_root(root_path: str | os.PathLike[str]) -> Path:
    try:
        root = Path(root_path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise ExplorerError("A pasta raiz não existe ou não pode ser lida.") from None
    if not root.is_dir():
        raise ExplorerError("A raiz escolhida não é uma pasta.")
    return root


def resolve_inside_root(
    root_path: str | os.PathLike[str],
    candidate_path: str | os.PathLike[str],
) -> Path:
    """Resolve uma pasta sem atravessar links nem sair da raiz canônica."""
    root = canonical_root(root_path)
    candidate = Path(candidate_path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    lexical = Path(os.path.abspath(os.fspath(candidate)))
    if not _inside_root(root, lexical):
        raise ExplorerOutsideRootError(
            "O caminho está fora da pasta raiz escolhida."
        )

    try:
        relative = lexical.relative_to(root)
    except ValueError:
        raise ExplorerOutsideRootError(
            "O caminho está fora da pasta raiz escolhida."
        ) from None

    current = root
    try:
        for part in relative.parts:
            if part in {"", ".", ".."}:
                raise ExplorerOutsideRootError(
                    "O caminho está fora da pasta raiz escolhida."
                )
            current = current / part
            info = current.lstat()
            if _is_reparse_point(current, info):
                raise ExplorerLinkError(
                    "Links e pontos de reanálise não são abertos."
                )
            resolved = current.resolve(strict=True)
            if not _inside_root(root, resolved):
                raise ExplorerOutsideRootError(
                    "O caminho está fora da pasta raiz escolhida."
                )
            current = resolved
    except ExplorerError:
        raise
    except (OSError, RuntimeError, ValueError):
        raise ExplorerError("O caminho não existe ou não pode ser lido.") from None

    if not current.is_dir():
        raise ExplorerError("O caminho escolhido não é uma pasta.")
    return current


def resolve_file_inside_root(
    root_path: str | os.PathLike[str],
    candidate_path: str | os.PathLike[str],
) -> Path:
    """Resolve um arquivo local sem atravessar links nem sair da raiz."""
    root = canonical_root(root_path)
    candidate = Path(candidate_path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    lexical = Path(os.path.abspath(os.fspath(candidate)))
    if not _inside_root(root, lexical):
        raise ExplorerOutsideRootError(
            "O caminho está fora da pasta raiz escolhida."
        )

    try:
        relative = lexical.relative_to(root)
    except ValueError:
        raise ExplorerOutsideRootError(
            "O caminho está fora da pasta raiz escolhida."
        ) from None

    current = root
    try:
        for part in relative.parts:
            if part in {"", ".", ".."}:
                raise ExplorerOutsideRootError(
                    "O caminho está fora da pasta raiz escolhida."
                )
            current = current / part
            info = current.lstat()
            if _is_reparse_point(current, info):
                raise ExplorerLinkError(
                    "Links e pontos de reanálise não são abertos."
                )
            resolved = current.resolve(strict=True)
            if not _inside_root(root, resolved):
                raise ExplorerOutsideRootError(
                    "O caminho está fora da pasta raiz escolhida."
                )
            current = resolved
    except ExplorerError:
        raise
    except (OSError, RuntimeError, ValueError):
        raise ExplorerError("O caminho não existe ou não pode ser lido.") from None

    if not current.is_file():
        raise ExplorerError("O caminho escolhido não é um arquivo.")
    return current


def _normalize_ignored(names: Iterable[str]) -> set[str]:
    normalized = set()
    for value in names:
        if not isinstance(value, str):
            continue
        name = value.strip()
        if not name or name in {".", ".."}:
            continue
        if "/" in name or "\\" in name or "\x00" in name:
            continue
        normalized.add(os.path.normcase(name))
    return normalized


def _is_ignored(name: str, ignored: set[str]) -> bool:
    return os.path.normcase(name) in ignored


class _Budget:
    def __init__(
        self,
        limits: ExplorerLimits,
        cancel_event: Event | None,
        *,
        deadline: float | None = None,
    ):
        self.max_items = limits.max_items
        self.deadline = (
            time.monotonic() + limits.max_seconds
            if deadline is None
            else deadline
        )
        self.cancel_event = cancel_event
        self.visited = 0
        self.limit_reason = ""

    def take(self) -> bool:
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise ExplorerCancelled()
        if time.monotonic() >= self.deadline:
            self.limit_reason = "time"
            return False
        if self.visited >= self.max_items:
            self.limit_reason = "items"
            return False
        self.visited += 1
        return True

    def check_cancelled(self):
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise ExplorerCancelled()


def _raw_kind(path: Path, info) -> str:
    if _is_reparse_point(path, info):
        return "link"
    if stat.S_ISDIR(info.st_mode):
        return "directory"
    if stat.S_ISREG(info.st_mode):
        return "file"
    return "other"


def _sort_key(entry: ExplorerEntry):
    return (
        0 if entry.kind == "directory" else 1,
        os.path.normcase(entry.name),
        entry.name,
    )


def _relative_name(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_direct_entries(
    directory: Path,
    root: Path,
    budget: _Budget,
    ignored: set[str],
    show_ignored: bool,
) -> tuple[list[ExplorerEntry], bool]:
    # Revalidate immediately before every directory read.  A previously listed
    # child can have been replaced by a symlink/reparse point between requests.
    directory = resolve_inside_root(root, directory)
    entries: list[ExplorerEntry] = []
    incomplete = False
    try:
        with os.scandir(directory) as iterator:
            for record in iterator:
                if not budget.take():
                    incomplete = True
                    break
                if not show_ignored and _is_ignored(record.name, ignored):
                    continue
                path = Path(record.path)
                try:
                    info = record.stat(follow_symlinks=False)
                except OSError:
                    entries.append(
                        ExplorerEntry(
                            name=record.name,
                            relative_path=_relative_name(root, path),
                            kind="blocked",
                        )
                    )
                    continue
                entries.append(
                    ExplorerEntry(
                        name=record.name,
                        relative_path=_relative_name(root, path),
                        kind=_raw_kind(path, info),
                    )
                )
    except PermissionError:
        raise
    except OSError:
        raise ExplorerError("A pasta não pode ser listada.") from None
    entries.sort(key=_sort_key)
    return entries, incomplete


def _count_direct_children(
    directory: Path,
    root: Path,
    budget: _Budget,
    ignored: set[str],
    show_ignored: bool,
) -> tuple[int, int, bool]:
    # Counts are filesystem reads too: never trust paths captured by an earlier
    # listing without checking their real path and every intermediate component.
    directory = resolve_inside_root(root, directory)
    folders = 0
    files = 0
    incomplete = False
    try:
        with os.scandir(directory) as iterator:
            for record in iterator:
                if not budget.take():
                    incomplete = True
                    break
                if not show_ignored and _is_ignored(record.name, ignored):
                    continue
                path = Path(record.path)
                try:
                    info = record.stat(follow_symlinks=False)
                except OSError:
                    incomplete = True
                    continue
                kind = _raw_kind(path, info)
                if kind == "directory":
                    folders += 1
                elif kind == "file":
                    files += 1
    except PermissionError:
        return folders, files, True
    except OSError:
        return folders, files, True
    return folders, files, incomplete


def scan_directory(
    root_path: str | os.PathLike[str],
    directory_path: str | os.PathLike[str],
    ignored_names: Iterable[str],
    limits: ExplorerLimits,
    *,
    show_ignored: bool = False,
    cancel_event: Event | None = None,
) -> ExplorerScanResult:
    root = canonical_root(root_path)
    directory = resolve_inside_root(root, directory_path)
    ignored = _normalize_ignored(ignored_names)
    listing_budget = _Budget(limits, cancel_event)
    try:
        entries, incomplete = _read_direct_entries(
            directory,
            root,
            listing_budget,
            ignored,
            show_ignored,
        )
    except PermissionError:
        return ExplorerScanResult(
            root=str(root),
            directory=str(directory),
            entries=(),
            error="permission",
        )

    counts_budget = listing_budget
    counted: list[ExplorerEntry] = []
    limit_reason = listing_budget.limit_reason
    counts_limited = False
    counts_error = False
    for entry in entries:
        if entry.kind != "directory":
            counted.append(entry)
            continue
        if counts_limited:
            counted.append(
                ExplorerEntry(
                    **{
                        **entry.__dict__,
                        "counts_incomplete": True,
                    }
                )
            )
            continue
        child_directory = root.joinpath(*PurePosixPath(entry.relative_path).parts)
        try:
            folders, files, count_incomplete = _count_direct_children(
                child_directory,
                root,
                counts_budget,
                ignored,
                show_ignored,
            )
        except ExplorerCancelled:
            raise
        if count_incomplete:
            if counts_budget.limit_reason:
                counts_limited = True
                limit_reason = counts_budget.limit_reason or limit_reason
            else:
                counts_error = True
                counted.append(
                    ExplorerEntry(
                        name=entry.name,
                        relative_path=entry.relative_path,
                        kind="blocked",
                    )
                )
                continue
        counted.append(
            ExplorerEntry(
                name=entry.name,
                relative_path=entry.relative_path,
                kind=entry.kind,
                folder_count=folders,
                file_count=files,
                counts_incomplete=count_incomplete,
            )
        )
    return ExplorerScanResult(
        root=str(root),
        directory=str(directory),
        entries=tuple(counted),
        incomplete=incomplete or counts_limited or counts_error,
        limit_reason=limit_reason or ("permission" if counts_error else ""),
    )


def _safe_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("O caminho relativo está vazio.")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("O caminho relativo não é seguro.")
    return path.as_posix()


def _is_ancestor(ancestor: str, path: str, *, strict: bool = False) -> bool:
    if ancestor == path:
        return not strict
    return path.startswith(f"{ancestor}/")


class ExplorerSelection:
    """Seleção recursiva, opcionalmente iniciada com todo o projeto marcado."""

    def __init__(
        self,
        included: Iterable[str] = (),
        excluded: Iterable[str] = (),
        *,
        include_all: bool = False,
    ):
        self.included = {_safe_relative_path(path) for path in included}
        self.excluded = {_safe_relative_path(path) for path in excluded}
        self.include_all = bool(include_all)

    def set_checked(self, relative_path: str, checked: bool):
        path = _safe_relative_path(relative_path)
        if checked:
            self.included = {
                item
                for item in self.included
                if not _is_ancestor(path, item, strict=True)
            }
            self.included.add(path)
            self.excluded = {
                item
                for item in self.excluded
                if not _is_ancestor(path, item)
            }
            return

        inherited = self.include_all or any(
            _is_ancestor(item, path, strict=True)
            for item in self.included
        )
        self.included = {
            item
            for item in self.included
            if not _is_ancestor(path, item)
        }
        self.excluded = {
            item
            for item in self.excluded
            if not _is_ancestor(path, item)
        }
        if inherited:
            self.excluded.add(path)

    def is_selected(self, relative_path: str) -> bool:
        path = _safe_relative_path(relative_path)
        rules = [
            (len(item), True)
            for item in self.included
            if _is_ancestor(item, path)
        ]
        rules.extend(
            (len(item), False)
            for item in self.excluded
            if _is_ancestor(item, path)
        )
        return max(rules, default=(0, self.include_all))[1]

    def has_selected_descendant(self, relative_path: str) -> bool:
        path = _safe_relative_path(relative_path)
        return any(
            _is_ancestor(path, item, strict=True)
            for item in self.included
        )

    def state(self, relative_path: str, is_directory: bool) -> str:
        path = _safe_relative_path(relative_path)
        selected = self.is_selected(path)
        if is_directory:
            has_excluded_child = any(
                _is_ancestor(path, item, strict=True)
                for item in self.excluded
            )
            if selected and not has_excluded_child:
                return "checked"
            if selected or self.has_selected_descendant(path):
                return "partial"
        elif selected:
            return "checked"
        return "unchecked"

    def is_empty(self) -> bool:
        return not self.include_all and not self.included

    def to_dict(self) -> dict[str, object]:
        result = {
            "included": sorted(self.included),
            "excluded": sorted(self.excluded),
        }
        if self.include_all:
            result["include_all"] = True
        return result


def generate_tree(
    root_path: str | os.PathLike[str],
    selection: ExplorerSelection,
    ignored_names: Iterable[str],
    limits: ExplorerLimits,
    *,
    show_ignored: bool = False,
    cancel_event: Event | None = None,
) -> ExplorerTreeResult:
    from _CONFIGURA_ import TEXTO_UI

    root = canonical_root(root_path)
    ignored = _normalize_ignored(ignored_names)
    budget = _Budget(limits, cancel_event)
    count_budget = budget
    lines = [root.name or str(root)]
    included_count = 0
    omitted_count = 0
    limit_reason = ""
    omitted_count_exact = True
    output_chars = len(lines[0])

    def walk(directory: Path, relative_parent: str, depth: int, prefix: str):
        nonlocal included_count, omitted_count, limit_reason
        nonlocal omitted_count_exact, output_chars
        try:
            entries, stopped = _read_direct_entries(
                directory,
                root,
                budget,
                ignored,
                show_ignored,
            )
        except PermissionError:
            return
        except ExplorerCancelled:
            raise
        if stopped:
            limit_reason = budget.limit_reason

        selected_entries = []
        for entry in entries:
            is_directory = entry.kind == "directory"
            state = selection.state(entry.relative_path, is_directory)
            if (
                state == "unchecked"
                and not selection.has_selected_descendant(entry.relative_path)
            ):
                continue
            selected_entries.append((entry, state, is_directory))

        for position, (entry, state, is_directory) in enumerate(selected_entries):
            budget.check_cancelled()
            path = entry.relative_path
            if depth > limits.max_depth:
                omitted_count += 1
                limit_reason = limit_reason or "depth"
                continue

            connector = (
                "└── "
                if position == len(selected_entries) - 1
                else "├── "
            )
            suffix = ""
            folders = 0
            files = 0
            if is_directory:
                folders, files, count_incomplete = _count_direct_children(
                    root.joinpath(*PurePosixPath(path).parts),
                    root,
                    count_budget,
                    ignored,
                    show_ignored,
                )
                suffix = TEXTO_UI["explorer_tree_folder_count"].format(
                    folders=folders,
                    files=files,
                )
                if count_incomplete:
                    suffix += " +"
                    if count_budget.limit_reason:
                        limit_reason = limit_reason or count_budget.limit_reason
                    else:
                        limit_reason = limit_reason or "permission"
                        omitted_count += 1
                        omitted_count_exact = False
            line = f"{prefix}{connector}{entry.name}{suffix}"
            if (
                included_count + 1 >= limits.max_lines
                or output_chars + len(line) + 1 > limits.max_chars - 80
            ):
                omitted_count += 1
                limit_reason = limit_reason or "output"
                continue

            lines.append(line)
            output_chars += len(line) + 1
            included_count += 1
            if is_directory:
                if depth >= limits.max_depth:
                    omitted_count += folders + files
                    if folders or files:
                        limit_reason = limit_reason or "depth"
                elif state != "unchecked" or selection.has_selected_descendant(path):
                    walk(
                        root.joinpath(*PurePosixPath(path).parts),
                        path,
                        depth + 1,
                        prefix
                        + (
                            "    "
                            if position == len(selected_entries) - 1
                            else "│   "
                        ),
                    )

    if not selection.is_empty():
        walk(root, "", 1, "")

    incomplete = bool(limit_reason or omitted_count)
    if limit_reason in {"items", "time"}:
        omitted_count_exact = False
        if omitted_count == 0:
            omitted_count = 1
    if omitted_count:
        summary_template = (
            TEXTO_UI["explorer_omitted"]
            if omitted_count_exact
            else (
                TEXTO_UI["explorer_omitted_at_least_one"]
                if omitted_count == 1
                else TEXTO_UI["explorer_omitted_at_least"]
            )
        )
        summary = summary_template.format(count=omitted_count)
        if len(lines) >= limits.max_lines:
            lines = lines[: limits.max_lines - 1]
        while lines and len("\n".join(lines)) + len(summary) + 1 > limits.max_chars:
            removed = lines.pop()
            if removed != lines[0] if lines else False:
                omitted_count += 1
                if not omitted_count_exact and omitted_count == 2:
                    summary_template = TEXTO_UI["explorer_omitted_at_least"]
            summary = summary_template.format(count=omitted_count)
        lines.append(summary)
    text = "\n".join(lines)
    return ExplorerTreeResult(
        text=text[: limits.max_chars],
        included_count=included_count,
        omitted_count=omitted_count,
        incomplete=incomplete,
        limit_reason=limit_reason,
        omitted_count_exact=omitted_count_exact,
    )
