import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from _SERVICOS_.video_download import VideoDownloadService


class FakeYoutubeDL:
    last_options = None

    def __init__(self, options):
        type(self).last_options = options

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def extract_info(self, _url, download=False):
        assert download is False
        return {
            "id": "video-123",
            "title": "Exemplo",
            "uploader": "Canal",
            "duration": 3661,
            "height": 1080,
            "fps": 30,
            "ext": "mp4",
            "formats": [
                {"height": 720, "vcodec": "avc1"},
                {"height": 1080, "vcodec": "vp9"},
                {"height": 480, "vcodec": "none"},
            ],
        }

    def download(self, _urls):
        return 0


class FakeYtDlp:
    YoutubeDL = FakeYoutubeDL


class VideoDownloadServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = VideoDownloadService()

    def test_validates_only_http_urls_with_host(self):
        self.assertEqual(
            self.service.validar_url(" https://example.com/video "),
            "https://example.com/video",
        )
        for address in ("file:///tmp/video.mp4", "https:///video", "not a URL"):
            with self.subTest(address=address):
                with self.assertRaises(ValueError):
                    self.service.validar_url(address)

    def test_extracts_video_metadata_and_available_heights(self):
        with patch.object(
            VideoDownloadService,
            "_importar_yt_dlp",
            return_value=FakeYtDlp,
        ):
            info = self.service.obter_informacoes("https://example.com/video")

        self.assertEqual(info["title"], "Exemplo")
        self.assertEqual(info["uploader"], "Canal")
        self.assertEqual(info["duration"], "1:01:01")
        self.assertEqual(info["resolution"], "1080p · 30 fps")
        self.assertEqual(info["available_heights"], [1080, 720])
        self.assertTrue(FakeYoutubeDL.last_options["skip_download"])
        self.assertTrue(FakeYoutubeDL.last_options["noplaylist"])

    def test_download_passes_resolution_format_and_progress_hook(self):
        with tempfile.TemporaryDirectory() as destination:
            ffmpeg = Path(destination) / "ffmpeg.exe"
            ffmpeg.touch()
            progress = []
            with (
                patch.object(
                    VideoDownloadService,
                    "_importar_yt_dlp",
                    return_value=FakeYtDlp,
                ),
                patch.object(
                    VideoDownloadService,
                    "_localizar_ffmpeg",
                    return_value=ffmpeg,
                ),
            ):
                result = self.service.baixar_video(
                    "https://example.com/video",
                    destination,
                    resolucao_max=720,
                    formato="mkv",
                    progresso=lambda percent, message: progress.append(
                        (percent, message)
                    ),
                )

            options = FakeYoutubeDL.last_options
            self.assertIn("height<=720", options["format"])
            self.assertEqual(options["merge_output_format"], "mkv")
            self.assertEqual(options["ffmpeg_location"], str(ffmpeg))
            self.assertEqual(result, {"folder": destination, "format": "mkv"})
            options["progress_hooks"][0](
                {"status": "downloading", "_percent_str": "45.0%"}
            )
            options["progress_hooks"][0]({"status": "finished"})
            self.assertEqual(progress[0][0], 45)
            self.assertEqual(progress[1][0], -1)

    def test_audio_download_uses_selected_format_and_ffmpeg(self):
        with tempfile.TemporaryDirectory() as destination:
            ffmpeg = Path(destination) / "ffmpeg.exe"
            with (
                patch.object(
                    VideoDownloadService,
                    "_importar_yt_dlp",
                    return_value=FakeYtDlp,
                ),
                patch.object(
                    VideoDownloadService,
                    "_localizar_ffmpeg",
                    return_value=ffmpeg,
                ),
            ):
                result = self.service.baixar_audio(
                    "https://example.com/video",
                    destination,
                    formato="flac",
                )

            options = FakeYoutubeDL.last_options
            self.assertEqual(options["format"], "bestaudio/best")
            self.assertEqual(options["ffmpeg_location"], str(ffmpeg))
            self.assertEqual(
                options["postprocessors"][0]["preferredcodec"],
                "flac",
            )
            self.assertEqual(result["format"], "flac")

    def test_transcription_only_runs_without_video_or_audio_download(self):
        with tempfile.TemporaryDirectory() as destination:
            output = Path(destination)
            info = {"id": "video-123", "title": "Exemplo"}
            transcription = {
                "text": "Texto detectado",
                "path": str(output / "transcricao.txt"),
                "srt_path": "",
                "source": "legenda",
                "title": "Exemplo",
            }
            with (
                patch.object(
                    self.service,
                    "obter_informacoes",
                    return_value=info,
                ),
                patch.object(
                    self.service,
                    "preparar_pasta_video",
                    return_value=output,
                ),
                patch.object(self.service, "baixar_video") as baixar_video,
                patch.object(self.service, "baixar_audio") as baixar_audio,
                patch.object(
                    self.service,
                    "criar_transcricao",
                    return_value=transcription,
                ) as criar_transcricao,
            ):
                result = self.service.processar_midia(
                    "https://example.com/video",
                    destination,
                    transcrever=True,
                    organizar_por_video=False,
                )

            baixar_video.assert_not_called()
            baixar_audio.assert_not_called()
            criar_transcricao.assert_called_once()
            self.assertEqual(result["transcription"], transcription)

    def test_creates_text_and_srt_from_existing_caption_segments(self):
        segments = [
            {"start": 1.0, "end": 2.5, "text": "Olá, mundo"},
        ]
        with tempfile.TemporaryDirectory() as destination:
            with (
                patch.object(
                    self.service,
                    "obter_informacoes",
                    return_value={"id": "id-1", "title": "Meu vídeo"},
                ),
                patch.object(
                    self.service,
                    "_obter_legenda",
                    return_value={
                        "text": "Olá, mundo",
                        "segments": segments,
                    },
                ),
            ):
                result = self.service.criar_transcricao(
                    "https://example.com/video",
                    destination,
                    criar_srt=True,
                    salvar_txt=True,
                )

            self.assertEqual(Path(result["path"]).read_text(), "Olá, mundo\n")
            self.assertIn(
                "00:00:01,000 --> 00:00:02,500",
                Path(result["srt_path"]).read_text(),
            )

    def test_parses_webvtt_html_and_timestamped_lines(self):
        with tempfile.TemporaryDirectory() as temporary:
            subtitle = Path(temporary) / "video.pt.vtt"
            subtitle.write_text(
                "WEBVTT\n\n"
                "00:00:01.000 --> 00:00:02.500\n"
                "Olá, <b>mundo</b> &amp; todos\n",
                encoding="utf-8",
            )
            result = self.service._ler_legenda(subtitle)

        self.assertEqual(result["text"], "Olá, mundo & todos")
        self.assertEqual(result["segments"][0]["start"], 1.0)
        self.assertEqual(result["segments"][0]["end"], 2.5)

    def test_requires_at_least_one_media_task(self):
        with self.assertRaises(ValueError):
            self.service.processar_midia(
                "https://example.com/video",
                "/tmp/hen-nave-no-tasks",
            )

    def test_rejects_unavailable_video_format(self):
        with self.assertRaises(ValueError):
            self.service.baixar_video(
                "https://example.com/video",
                "/tmp/video-download-test",
                formato="exe",
            )

    def test_finds_ffmpeg_inside_the_project_ffmpeg_bin_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            ffmpeg_folder = Path(temporary) / "FFmpeg" / "bin"
            ffmpeg_folder.mkdir(parents=True)
            executable = ffmpeg_folder / "ffmpeg.exe"
            executable.touch()
            with (
                patch(
                    "_SERVICOS_.video_download.CAMINHOS_FFMPEG",
                    (Path(temporary) / "FFmpeg",),
                ),
                patch("_SERVICOS_.video_download.shutil.which", return_value=None),
            ):
                found = self.service._localizar_ffmpeg()
        self.assertEqual(found, executable)


if __name__ == "__main__":
    unittest.main()
