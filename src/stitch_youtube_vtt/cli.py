"""Download and stitch YouTube WebVTT captions."""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse


TIMING_LINE = re.compile(
    r"^(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+"
    r"(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})"
)
INLINE_TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")
WORD = re.compile(r"[A-Za-z0-9$][A-Za-z0-9&.'’$-]*")
DOTTED_ACRONYM = re.compile(r"(?:[A-Za-z]\.){2,}")
# Uppercase tokens that should survive sentence-casing of all-caps captions.
ACRONYMS = {
    "AI", "API", "CEO", "CFO", "CIO", "COO", "CPI", "CTO", "EPS", "ESG", "ETF",
    "EU", "FBI", "FOMC", "GDP", "IMF", "IPO", "IRS", "NASA", "NASDAQ", "NATO",
    "NBA", "NFL", "NYSE", "OK", "OPEC", "PCE", "SEC", "TV", "UK", "UN", "USA",
}
CAPITALIZED = {
    "january", "february", "april", "june", "july", "august",
    "september", "october", "november", "december", "monday", "tuesday",
    "wednesday", "thursday", "friday", "saturday", "sunday",
}


def seconds(timestamp: str) -> float:
    hours, minutes, rest = timestamp.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def clean_caption(text: str) -> str:
    text = html.unescape(INLINE_TAG.sub("", text))
    return SPACE.sub(" ", text).strip()


def incremental_chunks(vtt: str) -> list[tuple[float, float, str]]:
    """Extract only newly introduced text from YouTube rolling captions."""
    chunks: list[tuple[float, float, str]] = []
    previous_tokens: list[str] = []

    for block in re.split(r"\n\s*\n", vtt):
        lines = block.splitlines()
        if not lines:
            continue

        match = TIMING_LINE.match(lines[0])
        if not match:
            continue

        start = seconds(match.group("start"))
        end = seconds(match.group("end"))
        caption_lines = [line.strip() for line in lines[1:] if line.strip()]
        current_tokens = clean_caption(" ".join(caption_lines)).split()
        if not current_tokens:
            continue

        overlap = 0
        for size in range(min(len(previous_tokens), len(current_tokens)), 0, -1):
            if previous_tokens[-size:] == current_tokens[:size]:
                overlap = size
                break

        new_tokens = current_tokens[overlap:]
        if new_tokens:
            chunks.append((start, end, " ".join(new_tokens)))
        previous_tokens = current_tokens

    return chunks


def stitch(chunks: list[tuple[float, float, str]]) -> str:
    """Join incremental caption chunks into readable paragraphs."""
    paragraphs: list[str] = []
    current: list[str] = []
    current_length = 0
    previous_end: float | None = None

    for start, end, text in chunks:
        marker = text.startswith("[") and text.endswith("]")
        long_pause = previous_end is not None and start - previous_end >= 2.5

        if marker:
            if current:
                paragraphs.append(" ".join(current))
                current, current_length = [], 0
            paragraphs.append(text)
            previous_end = end
            continue

        if current and long_pause:
            paragraphs.append(" ".join(current))
            current, current_length = [], 0

        current.append(text)
        current_length += len(text)

        if current_length >= 650 and re.search(r"[.!?][\"']?$", text):
            paragraphs.append(" ".join(current))
            current, current_length = [], 0

        previous_end = end

    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


def is_mostly_uppercase(text: str, threshold: float = 0.9) -> bool:
    """Detect broadcast-style captions that are written entirely in capitals."""
    letters = [char for char in text if char.isalpha()]
    if len(letters) < 20:
        return False
    return sum(char.isupper() for char in letters) / len(letters) >= threshold


def case_part(part: str) -> str:
    stem = re.split(r"['’]", part, maxsplit=1)[0]
    suffix = part[len(stem) :].lower()
    if (
        stem.upper() in ACRONYMS
        or stem.upper() == "I"
        or re.search(r"\d|&", stem)
        or DOTTED_ACRONYM.fullmatch(stem)
    ):
        return stem.upper() + suffix
    if stem.lower() in CAPITALIZED:
        return stem.capitalize() + suffix
    return part.lower()


def sentence_case(text: str) -> str:
    """Convert all-caps caption text into sentence case."""

    def replace(match: re.Match[str]) -> str:
        nonlocal capitalize
        word = match.group()
        cased = "-".join(case_part(part) for part in word.split("-"))
        if capitalize:
            cased = cased[:1].upper() + cased[1:]
        following = text[match.end() :].split(maxsplit=1)
        separator = following[0] if following else ""
        # A trailing period ends a sentence unless it belongs to an acronym
        # such as "A.I.", which mid-sentence captions use frequently.
        ends_with_period = word.endswith(".") and not DOTTED_ACRONYM.search(word)
        capitalize = (
            ends_with_period
            or bool(re.match(r"[.!?:]", separator))
            or text[match.end() : match.end() + 2] == "\n\n"
        )
        return cased

    capitalize = True
    return WORD.sub(replace, text)


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def yt_dlp_command() -> list[str]:
    executable = shutil.which("yt-dlp")
    if executable:
        return [executable]

    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, "--from", "yt-dlp", "yt-dlp"]

    raise SystemExit("Neither yt-dlp nor uvx was found. Install yt-dlp or uv first.")


def download_captions(
    url: str, language: str, directory: Path
) -> tuple[Path, str, str, str]:
    template = str(directory / "captions.%(ext)s")
    command = yt_dlp_command() + [
        "--skip-download",
        "--no-simulate",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        language,
        "--sub-format",
        "vtt",
        "--output",
        template,
        "--print",
        "%(id)s\t%(title)s\t%(webpage_url)s",
        "--no-warnings",
        url,
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as error:
        details = (error.stderr or error.stdout or "unknown yt-dlp error").strip()
        raise SystemExit(f"yt-dlp could not retrieve captions:\n{details}") from error

    metadata_lines = [line for line in result.stdout.splitlines() if "\t" in line]
    if not metadata_lines:
        raise SystemExit("yt-dlp returned no video metadata.")
    video_id, title, source = metadata_lines[-1].split("\t", 2)

    caption_files = sorted(directory.glob("captions*.vtt"))
    if not caption_files:
        raise SystemExit(
            f"No {language!r} VTT captions were available for this video. "
            "Try another language with --lang."
        )

    exact = directory / f"captions.{language}.vtt"
    caption_path = exact if exact.exists() else caption_files[0]
    return caption_path, video_id, title, source


def write_transcript(
    caption_path: Path,
    output_path: Path,
    title: str,
    source: str,
    keep_case: bool = False,
) -> None:
    vtt = caption_path.read_text(encoding="utf-8-sig")
    transcript = stitch(incremental_chunks(vtt))
    if not keep_case and is_mostly_uppercase(transcript):
        transcript = sentence_case(transcript)

    header = [title]
    if source:
        header.append(f"Source: {source}")
    header.append("")
    output_path.write_text("\n".join(header) + transcript + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download and stitch YouTube captions, or stitch a local VTT file."
    )
    parser.add_argument("input", help="YouTube URL or local WebVTT caption file")
    parser.add_argument("output", nargs="?", type=Path, help="Destination text file")
    parser.add_argument("--lang", default="en", help="Caption language (default: en)")
    parser.add_argument("--title", help="Override the transcript title")
    parser.add_argument("--source", default="", help="Source URL for local VTT input")
    parser.add_argument(
        "--keep-case",
        action="store_true",
        help="Do not convert all-caps captions to sentence case",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if is_url(args.input):
        with tempfile.TemporaryDirectory(prefix="stitch-youtube-vtt-") as temporary:
            caption_path, video_id, fetched_title, fetched_source = download_captions(
                args.input, args.lang, Path(temporary)
            )
            output = args.output or Path.cwd() / f"{video_id}-transcript.txt"
            write_transcript(
                caption_path,
                output,
                args.title or fetched_title,
                args.source or fetched_source,
                args.keep_case,
            )
    else:
        caption_path = Path(args.input).expanduser()
        if not caption_path.is_file():
            raise SystemExit(f"Caption file not found: {caption_path}")
        output = args.output or caption_path.with_suffix(".txt")
        write_transcript(
            caption_path,
            output,
            args.title or "Transcript",
            args.source,
            args.keep_case,
        )

    print(output.resolve())


if __name__ == "__main__":
    main()
