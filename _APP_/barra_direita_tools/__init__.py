"""Componentes da barra vertical de ações e ferramentas do navegador."""

from .ai_assistant import AiAssistantDock
from .browser_downloads import BrowserDownloadsDock
from .anotacoes import NotesDock
from .captura import CaptureManager
from .devtools import DevToolsPanel
from .dialogs import FavoritesDialog, HistoryDialog
from .download_video import VideoDownloadDock
from .manager import RightToolsContext, RightToolsManager
from .sidebar import RightToolsSidebar

__all__ = [
    "BrowserDownloadsDock",
    "AiAssistantDock",
    "CaptureManager",
    "DevToolsPanel",
    "FavoritesDialog",
    "HistoryDialog",
    "NotesDock",
    "RightToolsContext",
    "RightToolsManager",
    "RightToolsSidebar",
    "VideoDownloadDock",
]
