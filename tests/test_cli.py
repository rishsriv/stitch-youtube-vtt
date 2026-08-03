import tempfile
import unittest
from pathlib import Path

from stitch_youtube_vtt.cli import clean_caption, incremental_chunks, is_url, stitch


SAMPLE_VTT = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello<00:00:00.500><c> brave</c><00:00:01.000><c> new</c>

00:00:02.000 --> 00:00:03.000
Hello brave new

00:00:03.000 --> 00:00:05.000
Hello brave new
world.<00:00:04.000><c> Welcome!</c>

00:00:08.000 --> 00:00:09.000
[music]
"""


class CaptionTests(unittest.TestCase):
    def test_clean_caption_removes_tags_and_decodes_entities(self) -> None:
        self.assertEqual(clean_caption("A<c> &amp; B</c>"), "A & B")

    def test_rolling_cues_are_not_duplicated(self) -> None:
        chunks = incremental_chunks(SAMPLE_VTT)
        self.assertEqual(
            [text for _, _, text in chunks],
            ["Hello brave new", "world. Welcome!", "[music]"],
        )

    def test_stitch_preserves_words_and_markers(self) -> None:
        transcript = stitch(incremental_chunks(SAMPLE_VTT))
        self.assertEqual(transcript, "Hello brave new world. Welcome!\n\n[music]")

    def test_url_detection(self) -> None:
        self.assertTrue(is_url("https://www.youtube.com/watch?v=abc"))
        self.assertFalse(is_url("captions.en.vtt"))


if __name__ == "__main__":
    unittest.main()
