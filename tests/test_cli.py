import tempfile
import unittest
from pathlib import Path

from stitch_youtube_vtt.cli import (
    clean_caption,
    incremental_chunks,
    is_mostly_uppercase,
    is_url,
    sentence_case,
    stitch,
    write_transcript,
)


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


class CaseTests(unittest.TestCase):
    ALL_CAPS = (
        "THANK YOU FOR HAVING US HERE. NVIDIA IS DOWN IN A.I.-ADJACENT NAMES "
        "AND THE U.S. MARKET. DANI: WHAT ABOUT THE S&P 500 IN Q3? I THINK "
        "WE'RE FINE -- THEY'RE BUYING ETF'S SINCE JUNE 22.\n\nNEW PARAGRAPH"
    )

    def test_detects_all_caps_captions(self) -> None:
        self.assertTrue(is_mostly_uppercase(self.ALL_CAPS))
        self.assertFalse(is_mostly_uppercase("Hello brave new world. Welcome to NASA!"))

    def test_sentence_case_preserves_acronyms_and_sentence_starts(self) -> None:
        self.assertEqual(
            sentence_case(self.ALL_CAPS),
            "Thank you for having us here. Nvidia is down in A.I.-adjacent names "
            "and the U.S. market. Dani: What about the S&P 500 in Q3? I think "
            "we're fine -- they're buying ETF's since June 22.\n\nNew paragraph",
        )

    def test_write_transcript_converts_all_caps_unless_keep_case(self) -> None:
        vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n" + self.ALL_CAPS.replace("\n\n", " ")
        with tempfile.TemporaryDirectory() as directory:
            caption = Path(directory) / "captions.en.vtt"
            caption.write_text(vtt, encoding="utf-8")
            output = Path(directory) / "out.txt"

            write_transcript(caption, output, "Title", "")
            self.assertIn("Thank you for having us here.", output.read_text())

            write_transcript(caption, output, "Title", "", keep_case=True)
            self.assertIn("THANK YOU FOR HAVING US HERE.", output.read_text())


if __name__ == "__main__":
    unittest.main()
