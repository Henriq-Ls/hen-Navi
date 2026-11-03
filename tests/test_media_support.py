import unittest

from _APP_.media_support import (
    MEDIA_CAPABILITY_SCRIPT,
    summarize_media_capabilities,
)


class MediaSupportTests(unittest.TestCase):
    def test_diagnostic_checks_common_video_audio_and_streaming_codecs(self):
        self.assertIn("canPlayType", MEDIA_CAPABILITY_SCRIPT)
        self.assertIn("MediaSource.isTypeSupported", MEDIA_CAPABILITY_SCRIPT)
        self.assertIn("avc1.42E01E", MEDIA_CAPABILITY_SCRIPT)
        self.assertIn("mp4a.40.2", MEDIA_CAPABILITY_SCRIPT)
        self.assertIn('video/webm; codecs="vp9"', MEDIA_CAPABILITY_SCRIPT)
        self.assertIn('video/mp4; codecs="av01.0.05M.08"', MEDIA_CAPABILITY_SCRIPT)

    def test_formats_detected_capabilities_for_user(self):
        result = summarize_media_capabilities({
            "h264": "probably",
            "aac": "maybe",
            "vp9": "",
            "av1": "probably",
            "mediaSource": True,
            "mseH264": False,
        })

        self.assertEqual(
            result,
            {
                "h264": "Sim",
                "aac": "Possível",
                "vp9": "Não detectado",
                "av1": "Sim",
                "media_source": "Disponível",
                "mse_h264": "Não",
            },
        )

    def test_missing_javascript_result_is_inconclusive(self):
        result = summarize_media_capabilities(None)

        self.assertTrue(all(value == "Inconclusivo" for value in result.values()))


if __name__ == "__main__":
    unittest.main()
