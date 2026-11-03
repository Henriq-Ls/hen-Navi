"""Consulta informações e baixa vídeos usando yt-dlp e FFmpeg local."""

from __future__ import annotations

import html
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from typing import Callable

from _CONFIGURA_ import (
    CAMINHOS_FFMPEG,
    EXECUTAVEIS_FFMPEG,
    FORMATOS_AUDIO_DOWNLOAD,
    FORMATOS_VIDEO_DOWNLOAD,
    FORMATO_AUDIO_DOWNLOAD_PADRAO,
    FORMATO_VIDEO_DOWNLOAD_PADRAO,
    IDIOMAS_LEGENDA_DOWNLOAD,
    IDIOMA_TRANSCRICAO_DOWNLOAD,
    MODELO_WHISPER_DOWNLOAD,
    PASTAS_RELATIVAS_FFMPEG,
    PASTA_FFMPEG,
    QUALIDADE_AUDIO_KBPS_DOWNLOAD,
    TEXTO_UI,
)
from _APPDATA_ import appdata
from _LOGS_ import log


AtualizacaoProgresso = Callable[[int, str], None]


class VideoDownloadService:
    """Implementa análise e download de um vídeo individual."""

    @staticmethod
    def _importar_yt_dlp():
        try:
            import yt_dlp
        except ImportError as error:
            raise RuntimeError(TEXTO_UI["video_download_yt_dlp_missing"]) from error
        return yt_dlp

    @staticmethod
    def validar_url(url: str) -> str:
        endereco = (url or "").strip()
        partes = urlsplit(endereco)
        if (
            partes.scheme.lower() not in ("http", "https")
            or not partes.hostname
        ):
            raise ValueError(TEXTO_UI["video_download_status_invalid_url"])
        return endereco

    @staticmethod
    def formatar_duracao(duracao: int | float | None) -> str:
        if not duracao:
            return TEXTO_UI["video_download_not_reported"]
        horas, restante = divmod(int(duracao), 3600)
        minutos, segundos = divmod(restante, 60)
        if horas:
            return f"{horas}:{minutos:02d}:{segundos:02d}"
        return f"{minutos}:{segundos:02d}"

    def obter_informacoes(self, url: str) -> dict:
        endereco = self.validar_url(url)
        yt_dlp = self._importar_yt_dlp()
        opcoes = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(endereco, download=False)

        if not info:
            raise RuntimeError(TEXTO_UI["video_download_status_no_info"])
        if info.get("_type") == "playlist":
            raise ValueError(TEXTO_UI["video_download_playlist_unsupported"])

        alturas = sorted(
            {
                int(formato["height"])
                for formato in info.get("formats") or []
                if formato.get("height")
                and formato.get("vcodec") not in (None, "none")
            },
            reverse=True,
        )
        altura = info.get("height")
        resolucao = (
            f"{altura}p"
            if altura
            else TEXTO_UI["video_download_not_reported"]
        )
        fps = info.get("fps")
        if fps:
            resolucao = f"{resolucao} · {fps} fps"

        return {
            "id": str(info.get("id") or ""),
            "title": str(info.get("title") or TEXTO_UI["video_download_unknown_title"]),
            "uploader": str(
                info.get("uploader")
                or info.get("channel")
                or TEXTO_UI["video_download_unknown_channel"]
            ),
            "duration": self.formatar_duracao(info.get("duration")),
            "resolution": resolucao,
            "format": str(
                info.get("ext") or TEXTO_UI["video_download_not_reported"]
            ).upper(),
            "available_heights": alturas,
        }

    @staticmethod
    def _localizar_ffmpeg() -> Path:
        tentativas = []
        for raiz in CAMINHOS_FFMPEG:
            for relativo in PASTAS_RELATIVAS_FFMPEG:
                pasta = Path(raiz) / relativo if relativo else Path(raiz)
                for nome in EXECUTAVEIS_FFMPEG:
                    caminho = pasta / nome
                    tentativas.append(str(caminho))
                    if caminho.is_file():
                        return caminho

        executavel = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
        if executavel:
            return Path(executavel)
        raise RuntimeError(
            TEXTO_UI["video_download_ffmpeg_missing"].format(folder=PASTA_FFMPEG)
            + "\nCaminhos verificados: "
            + "; ".join(tentativas)
        )

    @staticmethod
    def _hook_progresso(
        callback: AtualizacaoProgresso | None,
        mensagem_formatada: str = "",
    ) -> Callable[[dict], None]:
        formato_mensagem = (
            mensagem_formatada
            or TEXTO_UI["video_download_status_progress"]
        )

        def atualizar(dados: dict) -> None:
            situacao = dados.get("status")
            if situacao == "downloading":
                percentual = -1
                texto_percentual = str(dados.get("_percent_str", "")).replace(
                    "%", ""
                ).strip()
                try:
                    percentual = max(0, min(100, round(float(texto_percentual))))
                except (TypeError, ValueError):
                    total = dados.get("total_bytes") or dados.get(
                        "total_bytes_estimate"
                    )
                    baixado = dados.get("downloaded_bytes")
                    if total and baixado is not None:
                        percentual = max(0, min(100, round(baixado * 100 / total)))
                if callback:
                    callback(
                        percentual,
                        (
                            formato_mensagem.format(percent=percentual)
                            if percentual >= 0
                            else TEXTO_UI["video_download_status_downloading"]
                        ),
                    )
            elif situacao == "finished" and callback:
                callback(-1, TEXTO_UI["video_download_status_finalizing"])

        return atualizar

    def preparar_pasta_video(
        self,
        info: dict,
        destino: str | Path,
        organizar_por_video: bool,
    ) -> Path:
        pasta_saida = Path(destino).expanduser()
        if organizar_por_video:
            titulo = self._nome_seguro(
                str(info.get("title") or TEXTO_UI["video_download_unknown_title"]),
                limite=48,
            )
            id_bruto = str(info.get("id") or "").strip()
            identificador = (
                self._nome_seguro(id_bruto, limite=18)
                if id_bruto
                else ""
            )
            nome_pasta = f"{titulo} [{identificador}]" if identificador else titulo
            pasta_saida = pasta_saida / nome_pasta
        pasta_saida.mkdir(parents=True, exist_ok=True)
        return pasta_saida

    @staticmethod
    def _nome_seguro(texto: str, limite: int = 90) -> str:
        nome = re.sub(r"[^\w.-]+", "_", texto, flags=re.UNICODE).strip("._")
        nome = nome[:limite].rstrip("._")
        return nome or "video"

    def processar_midia(
        self,
        url: str,
        destino: str | Path,
        *,
        baixar_video: bool = False,
        baixar_audio: bool = False,
        transcrever: bool = False,
        criar_srt: bool = False,
        resolucao_max: int | None = None,
        formato_video: str = FORMATO_VIDEO_DOWNLOAD_PADRAO,
        formato_audio: str = FORMATO_AUDIO_DOWNLOAD_PADRAO,
        organizar_por_video: bool = True,
        progresso: AtualizacaoProgresso | None = None,
    ) -> dict:
        if not any((baixar_video, baixar_audio, transcrever, criar_srt)):
            raise ValueError(TEXTO_UI["video_download_status_no_tasks"])

        endereco = self.validar_url(url)
        info = self.obter_informacoes(endereco)
        pasta_saida = self.preparar_pasta_video(
            info,
            destino,
            organizar_por_video,
        )
        resultados = {}
        if baixar_video:
            resultados["video"] = self.baixar_video(
                endereco,
                pasta_saida,
                resolucao_max=resolucao_max,
                formato=formato_video,
                progresso=progresso,
            )
        if baixar_audio:
            resultados["audio"] = self.baixar_audio(
                endereco,
                pasta_saida,
                formato=formato_audio,
                progresso=progresso,
            )
        if transcrever or criar_srt:
            resultados["transcription"] = self.criar_transcricao(
                endereco,
                pasta_saida,
                progresso=progresso,
                criar_srt=criar_srt,
                salvar_txt=transcrever,
            )
        return {"folder": str(pasta_saida), **resultados}

    def baixar_video(
        self,
        url: str,
        destino: str | Path,
        *,
        resolucao_max: int | None = None,
        formato: str = FORMATO_VIDEO_DOWNLOAD_PADRAO,
        progresso: AtualizacaoProgresso | None = None,
    ) -> dict:
        endereco = self.validar_url(url)
        formato = str(formato or "").lower()
        if formato not in FORMATOS_VIDEO_DOWNLOAD:
            raise ValueError(TEXTO_UI["video_download_invalid_format"])
        if resolucao_max is not None and int(resolucao_max) < 1:
            raise ValueError(TEXTO_UI["video_download_status_quality_positive"])

        yt_dlp = self._importar_yt_dlp()
        ffmpeg = self._localizar_ffmpeg()
        pasta_saida = Path(destino).expanduser()
        pasta_saida.mkdir(parents=True, exist_ok=True)

        seletor = "bestvideo+bestaudio/best"
        if resolucao_max is not None:
            altura = int(resolucao_max)
            seletor = (
                f"bestvideo[height<={altura}]+bestaudio/"
                f"best[height<={altura}]/best"
            )
        opcoes = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "outtmpl": str(pasta_saida / "%(title).120B [%(id)s].%(ext)s"),
            "progress_hooks": [self._hook_progresso(progresso)],
            "ffmpeg_location": str(ffmpeg),
            "format": seletor,
        }
        if formato == "avi":
            opcoes["merge_output_format"] = "mp4"
            opcoes["postprocessors"] = [
                {"key": "FFmpegVideoConvertor", "preferedformat": "avi"}
            ]
        else:
            opcoes["merge_output_format"] = formato

        with yt_dlp.YoutubeDL(opcoes) as ydl:
            resultado = ydl.download([endereco])
        if resultado:
            raise RuntimeError(TEXTO_UI["video_download_status_yt_dlp_failed"])

        log.ok("VideoDownloadService", "baixar_video", str(pasta_saida))
        return {"folder": str(pasta_saida), "format": formato}

    def baixar_audio(
        self,
        url: str,
        destino: str | Path,
        *,
        formato: str = FORMATO_AUDIO_DOWNLOAD_PADRAO,
        progresso: AtualizacaoProgresso | None = None,
    ) -> dict:
        endereco = self.validar_url(url)
        formato = str(formato or "").lower()
        if formato not in FORMATOS_AUDIO_DOWNLOAD:
            raise ValueError(TEXTO_UI["video_download_audio_format_error"])

        yt_dlp = self._importar_yt_dlp()
        ffmpeg = self._localizar_ffmpeg()
        pasta_saida = Path(destino).expanduser()
        pasta_saida.mkdir(parents=True, exist_ok=True)
        opcoes = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": "bestaudio/best",
            "outtmpl": str(pasta_saida / "%(title).120B [%(id)s].%(ext)s"),
            "progress_hooks": [
                self._hook_progresso(
                    progresso,
                    TEXTO_UI["video_download_audio_progress"],
                )
            ],
            "ffmpeg_location": str(ffmpeg),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": formato,
                    "preferredquality": QUALIDADE_AUDIO_KBPS_DOWNLOAD,
                }
            ],
        }
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            resultado = ydl.download([endereco])
        if resultado:
            raise RuntimeError(TEXTO_UI["video_download_audio_error"])
        log.ok("VideoDownloadService", "baixar_audio", str(pasta_saida))
        return {"folder": str(pasta_saida), "format": formato}

    @staticmethod
    def _tempo_legenda_segundos(valor: str) -> float | None:
        valor = (valor or "").strip().replace(",", ".")
        partes = valor.split(".")
        if len(partes) != 2:
            return None
        relogio, fracao = partes
        campos = relogio.split(":")
        try:
            if len(campos) == 3:
                horas, minutos, segundos = map(int, campos)
            elif len(campos) == 2:
                horas = 0
                minutos, segundos = map(int, campos)
            else:
                return None
            milissegundos = int((fracao + "000")[:3])
        except ValueError:
            return None
        return horas * 3600 + minutos * 60 + segundos + milissegundos / 1000

    @classmethod
    def _ler_segmentos_legenda(cls, caminho: Path) -> list[dict]:
        conteudo = caminho.read_text(encoding="utf-8-sig", errors="replace")
        padrao = re.compile(
            r"((?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{1,3})\s*-->\s*"
            r"((?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{1,3})"
        )
        segmentos = []
        anterior = None
        for bloco in re.split(r"\r?\n\s*\r?\n", conteudo):
            linhas = [linha.strip() for linha in bloco.splitlines()]
            indice_tempo = next(
                (indice for indice, linha in enumerate(linhas) if "-->" in linha),
                None,
            )
            if indice_tempo is None:
                continue
            correspondencia = padrao.search(linhas[indice_tempo])
            if not correspondencia:
                continue
            inicio = cls._tempo_legenda_segundos(correspondencia.group(1))
            fim = cls._tempo_legenda_segundos(correspondencia.group(2))
            texto = " ".join(linhas[indice_tempo + 1 :])
            texto = re.sub(r"<[^>]*>", " ", texto)
            texto = html.unescape(re.sub(r"\s+", " ", texto)).strip()
            if inicio is None or fim is None or fim <= inicio or not texto:
                continue
            if texto == anterior:
                continue
            segmentos.append({"start": inicio, "end": fim, "text": texto})
            anterior = texto
        return segmentos

    @classmethod
    def _ler_legenda(cls, caminho: Path) -> dict:
        segmentos = cls._ler_segmentos_legenda(caminho)
        texto = " ".join(
            str(segmento["text"]) for segmento in segmentos
        ).strip()
        if texto:
            return {"text": texto, "segments": segmentos}

        conteudo = caminho.read_text(encoding="utf-8-sig", errors="replace")
        linhas = []
        anterior = None
        for linha in conteudo.splitlines():
            item = linha.strip()
            if (
                not item
                or item.startswith(("WEBVTT", "NOTE", "STYLE", "REGION"))
                or "-->" in item
                or re.fullmatch(r"\d+", item)
            ):
                continue
            item = html.unescape(re.sub(r"<[^>]*>", "", item))
            item = re.sub(r"\s+", " ", item).strip()
            if item and item != anterior:
                linhas.append(item)
                anterior = item
        return {"text": " ".join(linhas).strip(), "segments": []}

    def _obter_legenda(self, url: str, pasta_temporaria: Path) -> dict:
        yt_dlp = self._importar_yt_dlp()
        opcoes = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": list(IDIOMAS_LEGENDA_DOWNLOAD),
            "subtitlesformat": "vtt/best",
            "outtmpl": str(pasta_temporaria / "%(title).160B [%(id)s].%(ext)s"),
        }
        try:
            with yt_dlp.YoutubeDL(opcoes) as ydl:
                ydl.download([url])
        except Exception as error:
            log.aviso(
                "VideoDownloadService",
                "_obter_legenda",
                str(error),
            )
            return {"text": "", "segments": []}

        arquivos = list(pasta_temporaria.rglob("*.vtt"))
        arquivos.extend(pasta_temporaria.rglob("*.srt"))
        for idioma in IDIOMAS_LEGENDA_DOWNLOAD:
            for arquivo in arquivos:
                if idioma.lower() in arquivo.name.lower():
                    resultado = self._ler_legenda(arquivo)
                    if resultado["text"]:
                        return resultado
        for arquivo in arquivos:
            resultado = self._ler_legenda(arquivo)
            if resultado["text"]:
                return resultado
        return {"text": "", "segments": []}

    def _transcrever_audio(
        self,
        url: str,
        pasta_temporaria: Path,
        progresso: AtualizacaoProgresso | None,
    ) -> dict:
        try:
            import whisper
        except ImportError as error:
            raise RuntimeError(TEXTO_UI["video_download_whisper_missing"]) from error

        yt_dlp = self._importar_yt_dlp()
        ffmpeg = self._localizar_ffmpeg()
        pasta_ffmpeg = str(ffmpeg.parent)
        caminhos_path = os.environ.get("PATH", "").split(os.pathsep)
        if pasta_ffmpeg not in caminhos_path:
            os.environ["PATH"] = os.pathsep.join([pasta_ffmpeg, *caminhos_path])
        if progresso:
            progresso(-1, TEXTO_UI["video_download_status_transcribe_audio"])
        opcoes = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": "bestaudio/best",
            "outtmpl": str(pasta_temporaria / "audio.%(ext)s"),
            "progress_hooks": [
                self._hook_progresso(
                    progresso,
                    TEXTO_UI["video_download_transcribe_progress"],
                )
            ],
            "ffmpeg_location": str(ffmpeg),
        }
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            resultado = ydl.download([url])
        if resultado:
            raise RuntimeError(TEXTO_UI["video_download_transcription_failed"])

        arquivos = [
            arquivo
            for arquivo in pasta_temporaria.glob("audio.*")
            if arquivo.is_file()
            and not arquivo.name.endswith((".part", ".json"))
        ]
        if not arquivos:
            raise RuntimeError(
                TEXTO_UI["video_download_transcription_file_missing"]
            )

        appdata.inicializar()
        if progresso:
            progresso(-1, TEXTO_UI["video_download_status_load_whisper"])
        modelo = whisper.load_model(
            MODELO_WHISPER_DOWNLOAD,
            download_root=appdata.pasta_cache,
        )
        if progresso:
            progresso(-1, TEXTO_UI["video_download_status_whisper"])
        transcricao = modelo.transcribe(
            str(arquivos[0]),
            language=IDIOMA_TRANSCRICAO_DOWNLOAD,
            fp16=False,
        )
        segmentos = []
        for segmento in transcricao.get("segments") or []:
            try:
                inicio = float(segmento.get("start"))
                fim = float(segmento.get("end"))
            except (AttributeError, TypeError, ValueError):
                continue
            texto = str(segmento.get("text") or "").strip()
            if texto and fim > inicio:
                segmentos.append({"start": inicio, "end": fim, "text": texto})
        return {
            "text": str(transcricao.get("text") or "").strip(),
            "segments": segmentos,
        }

    @staticmethod
    def _formatar_timestamp_srt(segundos: float) -> str:
        total_ms = max(0, round(float(segundos) * 1000))
        horas, restante = divmod(total_ms, 3_600_000)
        minutos, restante = divmod(restante, 60_000)
        segundos_inteiros, milissegundos = divmod(restante, 1000)
        return (
            f"{horas:02}:{minutos:02}:{segundos_inteiros:02},"
            f"{milissegundos:03}"
        )

    @classmethod
    def _formatar_legenda_srt(cls, segmentos: list[dict]) -> str:
        entradas = []
        for segmento in segmentos:
            texto = re.sub(r"\s+", " ", str(segmento.get("text") or "")).strip()
            try:
                inicio = float(segmento.get("start"))
                fim = float(segmento.get("end"))
            except (TypeError, ValueError):
                continue
            if not texto or fim <= inicio:
                continue
            entradas.append(
                f"{len(entradas) + 1}\n"
                f"{cls._formatar_timestamp_srt(inicio)} --> "
                f"{cls._formatar_timestamp_srt(fim)}\n"
                f"{texto}"
            )
        return "\n\n".join(entradas) + ("\n" if entradas else "")

    def criar_transcricao(
        self,
        url: str,
        destino: str | Path,
        *,
        progresso: AtualizacaoProgresso | None = None,
        criar_srt: bool = False,
        salvar_txt: bool = True,
    ) -> dict:
        endereco = self.validar_url(url)
        metadados = self.obter_informacoes(endereco)
        pasta_saida = Path(destino).expanduser()
        pasta_saida.mkdir(parents=True, exist_ok=True)
        if progresso:
            progresso(-1, TEXTO_UI["video_download_status_find_subtitles"])

        with tempfile.TemporaryDirectory(prefix="hen_nave_video_") as temporary:
            pasta_temporaria = Path(temporary)
            legenda = self._obter_legenda(endereco, pasta_temporaria)
            texto = str(legenda.get("text") or "").strip()
            segmentos = legenda.get("segments") or []
            origem = "legenda"
            if not texto or (criar_srt and not segmentos):
                resultado_whisper = self._transcrever_audio(
                    endereco,
                    pasta_temporaria,
                    progresso,
                )
                texto = str(resultado_whisper.get("text") or "").strip()
                segmentos = resultado_whisper.get("segments") or []
                origem = "Whisper"

        if not texto and segmentos:
            texto = " ".join(
                str(segmento.get("text") or "").strip()
                for segmento in segmentos
                if str(segmento.get("text") or "").strip()
            )
        if not texto:
            raise RuntimeError(TEXTO_UI["video_download_status_transcript_empty"])

        nome = self._nome_seguro(str(metadados.get("title") or "video"))
        identificador = self._nome_seguro(
            str(metadados.get("id") or ""),
            limite=40,
        )
        base_nome = f"{nome}-{identificador}" if identificador else nome
        caminho_txt = ""
        caminho_srt = ""
        if criar_srt:
            conteudo_srt = self._formatar_legenda_srt(segmentos)
            if not conteudo_srt:
                raise RuntimeError(TEXTO_UI["video_download_status_srt_no_segments"])
            arquivo_srt = pasta_saida / f"{base_nome}-legenda.srt"
            arquivo_srt.write_text(conteudo_srt, encoding="utf-8")
            caminho_srt = str(arquivo_srt)
        if salvar_txt:
            arquivo_txt = pasta_saida / f"{base_nome}-transcricao.txt"
            arquivo_txt.write_text(texto + "\n", encoding="utf-8")
            caminho_txt = str(arquivo_txt)
        if progresso:
            progresso(100, TEXTO_UI["video_download_transcription_title"])
        log.ok(
            "VideoDownloadService",
            "criar_transcricao",
            f"saídas criadas: {caminho_txt or caminho_srt}",
        )
        return {
            "text": texto,
            "path": caminho_txt,
            "srt_path": caminho_srt,
            "source": origem,
            "title": metadados.get("title", ""),
        }
