# main.py — Ponto de entrada do projeto
"""
Responsabilidades ÚNICAS deste arquivo (nesta ordem):
  1. Garantir que o diretório do projeto está no sys.path
  2. Garantir stdout/stderr válidos (exe sem console: PyInstaller --windowed)
  3. Ativar faulthandler (captura crashes nativos C/Qt antes de qualquer import)
  4. Inicializar o logger → cria LOG_GERAL.log
  5. Inicializar appdata → cria estrutura de pastas do usuário
  6. Registrar crash handler global (sys.excepthook)
  7. Criar QApplication e exibir MainWindow
"""
import sys
import os
import traceback
import faulthandler

# ── Bootstrap: garante que o diretório do projeto está no path ────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

# Configuração pura em Python, sem imports Qt; define o mesmo diretório usado
# pelo AppData e pelo logger para todos os arquivos de diagnóstico.
from _CONFIGURA_ import PASTA_APPDATA

# ── Exe sem console (--windowed / pythonw): stdout/stderr vêm como None ──────
# NUNCA remova este bloco: sem ele, faulthandler.enable() e qualquer biblioteca
# que escreva em stdout/stderr podem falhar apenas no executável.
# Redireciona para CRASH_NATIVO.log em PASTA_APPDATA/logs.
_crash_file = None
try:
    if getattr(sys, "frozen", False):
        _nome_app = os.path.splitext(os.path.basename(sys.executable))[0]
    else:
        _nome_app = "hen-nave"
    _pasta_crash = os.path.join(PASTA_APPDATA, "logs")
    os.makedirs(_pasta_crash, exist_ok=True)
    _crash_file = open(
        os.path.join(_pasta_crash, "CRASH_NATIVO.log"),
        "a", encoding="utf-8", buffering=1,
    )
except Exception:
    _crash_file = None

if sys.stdout is None:
    sys.stdout = _crash_file or open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = _crash_file or open(os.devnull, "w")

# ── faulthandler — captura segfaults e crashes nativos C/Qt ──────────────────
# DEVE ser ativado antes de qualquer import do PySide6.
# Sempre com file= explícito; _crash_file precisa ficar aberto até o fim.
try:
    faulthandler.enable(file=_crash_file or sys.stderr)
except Exception:
    pass

# ── Logger (cria LOG_GERAL.log da sessão) ─────────────────────────────────────
from _LOGS_ import log

# ── AppData (cria estrutura de pastas no computador do usuário) ───────────────
from _APPDATA_ import appdata
appdata.inicializar()
from _CONFIGURA_ import ARQUIVO_LOCK, TEXTO_UI

# ── Crash handler global ──────────────────────────────────────────────────────
def _excepthook(tipo, valor, tb):
    """Captura qualquer exceção não tratada e salva no log antes de exibir."""
    texto = "".join(traceback.format_exception(tipo, valor, tb))
    log.crash("main.py", "excepthook", texto)
    try:
        sys.__excepthook__(tipo, valor, tb)
    except Exception:
        pass

sys.excepthook = _excepthook

# ── Filtro VEH: silencia 0x8001010d (RPC_E_WRONG_THREAD) no Windows ──────────
# QMediaPlayer / WMF levanta essa exceção SEH internamente — é esperado pela MS.
# Sem este filtro o faulthandler imprime "Windows fatal exception" falso.
if sys.platform == "win32":
    try:
        import ctypes as _ctypes
        _PVECTORED_HANDLER = _ctypes.WINFUNCTYPE(_ctypes.c_long, _ctypes.c_void_p)

        @_PVECTORED_HANDLER
        def _veh_com_filter(exc_info):
            try:
                exc_rec = _ctypes.c_size_t.from_address(exc_info).value
                code    = _ctypes.c_uint.from_address(exc_rec    ).value
                flags   = _ctypes.c_uint.from_address(exc_rec + 4).value
                if code == 0x8001010D and not (flags & 0x1):
                    return -1  # EXCEPTION_CONTINUE_EXECUTION
            except Exception:
                pass
            return 1  # EXCEPTION_CONTINUE_SEARCH

        _ctypes.windll.kernel32.AddVectoredExceptionHandler(1, _veh_com_filter)
    except Exception:
        pass

# ── Single instance — impede abrir o app duas vezes ──────────────────────────
from PySide6.QtCore import QLockFile
import tempfile

_LOCK_PATH = os.path.join(tempfile.gettempdir(), ARQUIVO_LOCK)
_lock_file = QLockFile(_LOCK_PATH)
_lock_file.setStaleLockTime(0)

if not _lock_file.tryLock(100):
    # Já existe uma instância rodando
    from PySide6.QtWidgets import QApplication
    from _ULTILIDADES_.popups import popup_aviso
    _app_tmp = QApplication.instance() or QApplication(sys.argv)
    popup_aviso(
        TEXTO_UI["already_open_title"],
        TEXTO_UI["already_open_message"],
    )
    sys.exit(0)

# ── Imports Qt e módulos do projeto ───────────────────────────────────────────
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import qInstallMessageHandler, QtMsgType

from _CONFIGURA_ import (
    FONTE_NOME_UI, FONTE_TAMANHO_BASE,
    TITULO_APP, IMAGEM_ICO, TEMA_QT
)
from browser import BrowserController, register_custom_url_scheme


def _qt_msg_handler(mode, context, message):
    """Filtra e loga mensagens internas do Qt."""
    if "setPointSize" in message and "Point size <= 0" in message:
        return  # qtawesome usa pixelSize; pointSize retorna -1 por design
    if mode == QtMsgType.QtWarningMsg:
        log.aviso("Qt", "msg_handler", message)
    elif mode in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        log.erro("Qt", "msg_handler", message)


def main():
    log.info("main.py", "main", f"{TITULO_APP} iniciando...")

    qInstallMessageHandler(_qt_msg_handler)
    register_custom_url_scheme()
    app = QApplication(sys.argv)
    app.setStyle(TEMA_QT)

    if FONTE_TAMANHO_BASE and FONTE_TAMANHO_BASE > 0:
        app.setFont(QFont(FONTE_NOME_UI, FONTE_TAMANHO_BASE))

    if os.path.isfile(IMAGEM_ICO):
        app.setWindowIcon(QIcon(IMAGEM_ICO))
        log.ok("main.py", "main", f"Ícone carregado: {IMAGEM_ICO}")
    else:
        log.aviso("main.py", "main", f"Ícone não encontrado: {IMAGEM_ICO}")

    log.ok("main.py", "main", "QApplication criada")
    controller = BrowserController(app)
    win = controller.start()
    log.ok("main.py", "main", "Janela do hen-Nave exibida")

    code = app.exec()
    log.info("main.py", "main", f"App encerrada com código {code}")
    sys.exit(code)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        texto = traceback.format_exc()
        log.crash("main.py", "__main__", texto)
        # O executável sem console não possui entrada nem saída de terminal.
        sys.exit(1)
