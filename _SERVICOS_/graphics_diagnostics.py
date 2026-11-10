"""Diagnóstico gráfico local e explícito para QtWebEngine."""

from __future__ import annotations

from collections import deque
from fnmatch import fnmatchcase
from threading import Lock


GRAPHICS_CAPABILITY_SCRIPT = r"""
(() => {
  const canvas = document.createElement("canvas");
  let gl = null;
  let webglVersion = "";
  try {
    gl = canvas.getContext("webgl2");
    if (gl) {
      webglVersion = "WebGL 2";
    } else {
      gl = canvas.getContext("webgl");
      if (gl) webglVersion = "WebGL";
    }
  } catch (_) {
    gl = null;
  }

  let vendor = "";
  let renderer = "";
  let rendererUnmasked = false;
  if (gl) {
    try {
      const info = gl.getExtension("WEBGL_debug_renderer_info");
      rendererUnmasked = Boolean(info);
      vendor = gl.getParameter(
        info ? info.UNMASKED_VENDOR_WEBGL : gl.VENDOR
      ) || "";
      renderer = gl.getParameter(
        info ? info.UNMASKED_RENDERER_WEBGL : gl.RENDERER
      ) || "";
    } catch (_) {
      vendor = "";
      renderer = "";
    }
    try {
      const loseContext = gl.getExtension("WEBGL_lose_context");
      if (loseContext) loseContext.loseContext();
    } catch (_) {}
  }

  let webgpuAvailable = null;
  try {
    webgpuAvailable = Boolean(navigator.gpu);
  } catch (_) {}

  return {
    webglAvailable: Boolean(gl),
    webglVersion,
    vendor,
    renderer,
    rendererUnmasked,
    webgpuAvailable
  };
})()
"""

_QT_GRAPHICS_CATEGORY = "qt.webenginecontext"
_QT_GRAPHICS_PREFIXES = (
    "chromium gl backend:",
    "chromium angle backend:",
    "chromium vulkan backend:",
    "qsg rhi backend:",
    "qsg rhi backend supported:",
    "qsg rhi device:",
    "qsg rhi gpu vendor:",
)
_SOFTWARE_RENDERER_MARKERS = (
    "swiftshader",
    "llvmpipe",
    "softpipe",
    "software rasterizer",
    "microsoft basic render driver",
    "warp device",
)
_GENERIC_RENDERERS = {"", "angle", "webgl", "webkit", "webkit webgl"}
_GRAPHICS_DETAILS: deque[str] = deque(maxlen=24)
_GRAPHICS_LOCK = Lock()


def graphics_logging_rules(existing_rules: str = "") -> str:
    """Preserva regras existentes e habilita somente o contexto gráfico Qt."""
    existing = [
        rule.strip()
        for rule in str(existing_rules or "").replace(";", "\n").splitlines()
        if rule.strip()
    ]
    disabled_levels = set()
    for rule in existing:
        pattern, separator, value = rule.rpartition("=")
        if not separator or value.strip().lower() != "false":
            continue
        pattern = pattern.strip()
        for level in ("debug", "info"):
            target = f"{_QT_GRAPHICS_CATEGORY}.{level}"
            if pattern == _QT_GRAPHICS_CATEGORY or fnmatchcase(target, pattern):
                disabled_levels.add(level)

    for level in ("debug", "info"):
        if level in disabled_levels:
            continue
        rule = f"{_QT_GRAPHICS_CATEGORY}.{level}=true"
        if rule not in existing:
            existing.append(rule)
    return "\n".join(existing)


def _clean_text(value: object, limit: int = 180) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return " ".join(str(value or "").split())[:limit]


def capture_qt_graphics_message(category: object, message: object) -> int:
    """Mantém apenas linhas gráficas permitidas, em memória e sem logar URLs."""
    if callable(category):
        try:
            category = category()
        except Exception:
            return 0
    if _clean_text(category, 80) != _QT_GRAPHICS_CATEGORY:
        return 0

    captured: list[str] = []
    if isinstance(message, bytes):
        message = message.decode("utf-8", errors="replace")
    for raw_line in str(message or "").splitlines():
        line = _clean_text(raw_line)
        lowered = line.lower()
        if line and lowered.startswith(_QT_GRAPHICS_PREFIXES):
            captured.append(line)

    if not captured:
        return 0

    with _GRAPHICS_LOCK:
        for line in captured:
            if line not in _GRAPHICS_DETAILS:
                _GRAPHICS_DETAILS.append(line)
    return len(captured)


def reset_graphics_diagnostics() -> None:
    """Limpa a amostra em memória, principalmente para testes isolados."""
    with _GRAPHICS_LOCK:
        _GRAPHICS_DETAILS.clear()


def _qt_fields(details: list[str]) -> dict[str, str | None]:
    fields = {
        "chromium_gl_backend": None,
        "chromium_angle_backend": None,
        "chromium_vulkan_backend": None,
        "qt_rhi_backend": None,
        "qt_rhi_supported": None,
        "qt_rhi_device": None,
        "qt_rhi_vendor": None,
    }
    mapping = {
        "chromium gl backend": "chromium_gl_backend",
        "chromium angle backend": "chromium_angle_backend",
        "chromium vulkan backend": "chromium_vulkan_backend",
        "qsg rhi backend": "qt_rhi_backend",
        "qsg rhi backend supported": "qt_rhi_supported",
        "qsg rhi device": "qt_rhi_device",
        "qsg rhi gpu vendor": "qt_rhi_vendor",
    }
    for line in details:
        label, separator, value = line.partition(":")
        key = mapping.get(label.strip().lower())
        if key and separator:
            fields[key] = value.strip()[:180] or None
    return fields


def _safe_page_probe(value: object) -> dict:
    if not isinstance(value, dict):
        value = {}

    def safe_string(key: str, limit: int) -> str:
        item = value.get(key)
        return _clean_text(item, limit) if isinstance(item, str) else ""

    return {
        "webgl_available": (
            value.get("webglAvailable")
            if type(value.get("webglAvailable")) is bool
            else None
        ),
        "webgl_version": safe_string("webglVersion", 32),
        "vendor": safe_string("vendor", 100),
        "renderer": safe_string("renderer", 180),
        "renderer_unmasked": (
            value.get("rendererUnmasked")
            if type(value.get("rendererUnmasked")) is bool
            else False
        ),
        "webgpu_available": (
            value.get("webgpuAvailable")
            if type(value.get("webgpuAvailable")) is bool
            else None
        ),
    }


def graphics_diagnostic_snapshot(page_probe: object = None) -> dict:
    """Combina dados Qt coletados no início e uma sondagem acionada pelo usuário."""
    with _GRAPHICS_LOCK:
        details = list(_GRAPHICS_DETAILS)
    qt = _qt_fields(details)
    page = _safe_page_probe(page_probe)

    renderer = page["renderer"]
    renderer_kind = renderer.lower()
    if renderer and any(
        marker in renderer_kind for marker in _SOFTWARE_RENDERER_MARKERS
    ):
        state = "software_renderer"
    elif renderer and renderer_kind not in _GENERIC_RENDERERS:
        state = "renderer_reported"
    elif page["webgl_available"] is True:
        state = "webgl_available"
    elif qt["qt_rhi_supported"] == "no":
        state = "qt_backend_unsupported"
    elif qt["qt_rhi_device"] or qt["qt_rhi_vendor"]:
        state = "qt_device_reported"
    else:
        state = "inconclusive"

    return {
        "state": state,
        "details": details,
        "qt": qt,
        "page": page,
    }
