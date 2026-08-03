# stitch-youtube-vtt

Turn a YouTube URL into a clean plain-text transcript with one command.

```console
$ stitch-youtube-vtt 'https://www.youtube.com/watch?v=VIDEO_ID' transcript_title.txt
```

The tool uses [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) to download an
available caption track, removes the duplicated text produced by YouTube's
rolling WebVTT cues, groups the result into readable paragraphs, and adds the
video title and source URL.

## Features

- Accepts a YouTube URL or an existing `.vtt` caption file
- Uses creator-provided subtitles when available and automatic captions as a fallback
- Removes overlapping text from YouTube's rolling captions
- Preserves non-speech markers such as `[music]` and `[applause]`
- Detects the video title and source URL automatically
- Supports caption languages through `--lang`
- Has no runtime dependencies besides `yt-dlp`

## Requirements

- Python 3.10 or newer
- Internet access when processing a URL
- A video with subtitles or automatic captions available

## Install

### With uv (recommended)

```bash
uv tool install git+https://github.com/rishsriv/stitch-youtube-vtt.git
```

### With pipx

```bash
pipx install git+https://github.com/rishsriv/stitch-youtube-vtt.git
```

### With pip

```bash
python -m pip install git+https://github.com/rishsriv/stitch-youtube-vtt.git
```

To install an editable development checkout:

```bash
git clone https://github.com/rishsriv/stitch-youtube-vtt.git
cd stitch-youtube-vtt
python -m pip install -e .
```

## Usage

### Transcribe a YouTube video

```bash
stitch-youtube-vtt 'https://www.youtube.com/watch?v=VIDEO_ID'
```

The default output is `VIDEO_ID-transcript.txt` in the current directory.

### Choose the output file

```bash
stitch-youtube-vtt 'https://www.youtube.com/watch?v=VIDEO_ID' interview.txt
```

### Choose a caption language

```bash
stitch-youtube-vtt 'https://www.youtube.com/watch?v=VIDEO_ID' --lang es
```

The value is passed to `yt-dlp`'s `--sub-langs` option. Examples include `en`,
`en-US`, `es`, and `de`. Availability depends on the video.

### Convert an existing VTT file

```bash
stitch-youtube-vtt captions.en.vtt transcript.txt
```

For local files, optional metadata can be added to the output:

```bash
stitch-youtube-vtt captions.en.vtt transcript.txt \
  --title 'My video title' \
  --source 'https://example.com/video'
```

### Show all options

```bash
stitch-youtube-vtt --help
```

## How it works

YouTube's automatic WebVTT captions commonly contain a rolling window of words:
each cue repeats text from the previous cue and adds a few new words. Simply
stripping the VTT markup therefore creates a transcript full of duplicates.

`stitch-youtube-vtt` compares each cue with the preceding cue, finds the largest
word overlap, and emits only newly introduced words. It then uses pauses and
sentence boundaries to form readable paragraphs. Caption downloads happen in a
temporary directory and are removed automatically after conversion.

## Troubleshooting

**No captions were available**

The requested language may not exist for that video. Try another track:

```bash
yt-dlp --list-subs 'https://www.youtube.com/watch?v=VIDEO_ID'
stitch-youtube-vtt 'https://www.youtube.com/watch?v=VIDEO_ID' --lang LANGUAGE
```

**YouTube extraction errors**

YouTube changes frequently. Upgrade the tool so it receives the latest `yt-dlp`:

```bash
uv tool upgrade stitch-youtube-vtt
```

For pipx, use `pipx upgrade stitch-youtube-vtt`.

**The command is not found after installation**

Ensure your tool directory is on `PATH`. For uv, run `uv tool update-shell`; for
pipx, run `pipx ensurepath`, then open a new terminal.

## Development

```bash
git clone https://github.com/rishsriv/stitch-youtube-vtt.git
cd stitch-youtube-vtt
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Responsible use

Only download or reproduce captions when you have the right to do so. Respect
copyright, privacy, YouTube's terms, and the laws that apply to you.

## License

[MIT](LICENSE)
