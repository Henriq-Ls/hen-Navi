"""Diagnóstico local de formatos anunciados pelo Chromium do QtWebEngine."""

from __future__ import annotations


MEDIA_CAPABILITY_SCRIPT = r"""
(() => {
  const video = document.createElement("video");
  const audio = document.createElement("audio");
  const canPlay = (element, mime) => {
    try {
      return element.canPlayType(mime) || "";
    } catch (_) {
      return "";
    }
  };
  const mediaSourceSupports = (mime) => {
    try {
      return typeof window.MediaSource === "function"
        && window.MediaSource.isTypeSupported(mime);
    } catch (_) {
      return false;
    }
  };
  return {
    h264: canPlay(video, 'video/mp4; codecs="avc1.42E01E"'),
    aac: canPlay(audio, 'audio/mp4; codecs="mp4a.40.2"'),
    vp9: canPlay(video, 'video/webm; codecs="vp9"'),
    av1: canPlay(video, 'video/mp4; codecs="av01.0.05M.08"'),
    mediaSource: typeof window.MediaSource === "function",
    mseH264: mediaSourceSupports('video/mp4; codecs="avc1.42E01E"')
  };
})()
"""


def _can_play_label(value: object) -> str:
    if value == "probably":
        return "Sim"
    if value == "maybe":
        return "Possível"
    if value == "":
        return "Não detectado"
    return "Inconclusivo"


def summarize_media_capabilities(result: object) -> dict[str, str]:
    """Converte o retorno JavaScript em valores curtos para a interface."""
    if not isinstance(result, dict):
        result = {}

    media_source = result.get("mediaSource")
    mse_h264 = result.get("mseH264")
    return {
        "h264": _can_play_label(result.get("h264")),
        "aac": _can_play_label(result.get("aac")),
        "vp9": _can_play_label(result.get("vp9")),
        "av1": _can_play_label(result.get("av1")),
        "media_source": (
            "Disponível"
            if media_source is True
            else "Indisponível"
            if media_source is False
            else "Inconclusivo"
        ),
        "mse_h264": (
            "Sim"
            if mse_h264 is True
            else "Não"
            if mse_h264 is False
            else "Inconclusivo"
        ),
    }
