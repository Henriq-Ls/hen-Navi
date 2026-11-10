"""Detecção e leitura limitada para prévias locais, somente leitura."""

from __future__ import annotations

import mimetypes
from pathlib import Path


MAX_TEXT_PREVIEW_BYTES = 2 * 1024 * 1024
TEXT_EXTENSIONS = {
    ".bat",
    ".c",
    ".cfg",
    ".conf",
    ".cpp",
    ".cs",
    ".css",
    ".csv",
    ".dockerignore",
    ".editorconfig",
    ".go",
    ".h",
    ".hpp",
    ".htm",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsonl",
    ".jsx",
    ".kt",
    ".log",
    ".lua",
    ".md",
    ".php",
    ".ps1",
    ".py",
    ".rb",
    ".rs",
    ".rst",
    ".sh",
    ".sql",
    ".svg",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
IMAGE_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
AUDIO_EXTENSIONS = {
    ".aac",
    ".flac",
    ".m4a",
    ".mp3",
    ".oga",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
}
VIDEO_EXTENSIONS = {
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".webm",
    ".wmv",
}


class FilePreviewError(ValueError):
    """Erro seguro ao identificar ou ler uma prévia local."""


def classify_preview_file(path: str | Path) -> str:
    """Classifica formatos comuns sem executar nem renderizar HTML ativo."""
    file_path = Path(path)
    suffix = file_path.suffix.casefold()
    if suffix in TEXT_EXTENSIONS:
        return "text"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix == ".pdf":
        return "pdf"

    mime_type, _encoding = mimetypes.guess_type(file_path.name, strict=False)
    if mime_type:
        if mime_type.startswith("image/"):
            return "image"
        if mime_type.startswith("audio/"):
            return "audio"
        if mime_type.startswith("video/"):
            return "video"
        if mime_type == "application/pdf":
            return "pdf"
        if mime_type.startswith("text/"):
            return "text"

    try:
        with file_path.open("rb") as stream:
            sample = stream.read(8192)
    except OSError as error:
        raise FilePreviewError(
            "Não foi possível ler este arquivo."
        ) from error

    if b"\x00" not in sample:
        try:
            sample.decode("utf-8-sig")
        except UnicodeDecodeError:
            pass
        else:
            return "text"
    return "unsupported"


def read_text_preview(
    path: str | Path,
    *,
    max_bytes: int = MAX_TEXT_PREVIEW_BYTES,
) -> tuple[str, bool]:
    """Lê texto com limite de memória; retorna conteúdo e indicação de corte."""
    if max_bytes < 1:
        raise ValueError("max_bytes precisa ser positivo")
    file_path = Path(path)
    try:
        with file_path.open("rb") as stream:
            data = stream.read(max_bytes + 1)
    except OSError as error:
        raise FilePreviewError(
            "Não foi possível ler este arquivo."
        ) from error

    truncated = len(data) > max_bytes
    if truncated:
        data = data[:max_bytes]
    if b"\x00" in data:
        raise FilePreviewError("Este arquivo não parece ser texto.")

    encodings = (
        ("utf-16", "utf-8-sig", "cp1252")
        if data.startswith((b"\xff\xfe", b"\xfe\xff"))
        else ("utf-8-sig", "cp1252")
    )
    for encoding in encodings:
        try:
            return data.decode(encoding), truncated
        except UnicodeDecodeError:
            continue
    raise FilePreviewError("A codificação deste texto não é compatível.")
