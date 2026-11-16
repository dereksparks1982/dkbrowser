#!/usr/bin/env python3
"""Read-only local Matroska track inventory for DK Browser development.

This is an FFprobe-backed diagnostic, NOT a Chromium playback/decoder or
subtitle-rendering implementation. No files are uploaded or modified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

SCHEMA = "dk-browser.matroska-tracks.v1"
EXTENSIONS = frozenset({".mkv", ".mka", ".mks", ".mk3d"})
KINDS = frozenset({"video", "audio", "subtitle"})
OUTPUT_LIMIT = 2 * 1024 * 1024
TIMEOUT_SECONDS = 25

# Strictly local files: FFprobe is not allowed to open network/HTTP/FTP URLs.
PROBE_ARGS = (
    "-v", "error", "-hide_banner", "-protocol_whitelist", "file",
    "-print_format", "json",
    "-show_entries",
    "format=format_name,duration:"
    "stream=index,codec_type,codec_name,profile,width,height,channels,channel_layout:"
    "stream_tags=language,title:"
    "stream_disposition=default,forced:"
    "chapter=id,start_time,end_time:chapter_tags=title",
    "-show_format", "-show_streams", "-show_chapters",
)


class ProbeError(Exception):
    """Local diagnostic failure without exposing command internals."""


def _clean(value: Any, limit: int = 160) -> str:
    """Avoid embedded controls in terminal/JSON metadata."""
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isprintable())[:limit]


def _integer(value: Any, default: int = 0) -> int:
    try:
        result = int(value)
        return result if result >= 0 else default
    except (TypeError, ValueError, OverflowError):
        return default


def normalize_tracks(document: dict[str, Any], filename: str) -> dict[str, Any]:
    """Produce a stable small result that a future native track UI can consume.

    We do not claim codecs are decodable or that tracks are selectable.
    """
    if not isinstance(document, dict):
        raise ProbeError("Invalid FFprobe document")
    streams = document.get("streams", [])
    chapters = document.get("chapters", [])
    if not isinstance(streams, list) or not isinstance(chapters, list):
        raise ProbeError("Invalid FFprobe stream list")
    if len(streams) > 256 or len(chapters) > 10000:
        raise ProbeError("Track/chapter count exceeds diagnostic limit")
    tracks = []
    used_indices = set()
    for stream in streams:
        if not isinstance(stream, dict) or stream.get("codec_type") not in KINDS:
            continue
        index = _integer(stream.get("index"), -1)
        if index < 0 or index in used_indices:
            raise ProbeError("Invalid or repeated stream index")
        used_indices.add(index)
        tags = stream.get("tags") if isinstance(stream.get("tags"), dict) else {}
        disposition = stream.get("disposition") if isinstance(stream.get("disposition"), dict) else {}
        kind = stream["codec_type"]
        track = {
            "index": index,
            "type": kind,
            "codec": _clean(stream.get("codec_name")) or "unknown",
            "language": _clean(tags.get("language"), 32) or "und",
            "title": _clean(tags.get("title")),
            "default": bool(_integer(disposition.get("default"))),
            "forced": bool(_integer(disposition.get("forced"))),
        }
        if kind == "video":
            track.update(width=_integer(stream.get("width")),
                         height=_integer(stream.get("height")))
        elif kind == "audio":
            track.update(channels=_integer(stream.get("channels")))
        tracks.append(track)
    parsed_chapters = []
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        tags = chapter.get("tags") if isinstance(chapter.get("tags"), dict) else {}
        parsed_chapters.append({
            "start": _clean(chapter.get("start_time"), 32),
            "end": _clean(chapter.get("end_time"), 32),
            "title": _clean(tags.get("title")),
        })
    track_counts = {kind: sum(t["type"] == kind for t in tracks)
                    for kind in ("video", "audio", "subtitle")}
    return {
        "schema": SCHEMA,
        "filename": _clean(filename, 255),
        "tracks": tracks,
        "chapters": parsed_chapters,
        "counts": track_counts,
        "playable": None,  # Unknown until actual browser pipeline testing.
    }


def inspect_file(path: Path, runner=subprocess.run) -> dict[str, Any]:
    """Probe only an existing, locally selected Matroska file."""
    source = Path(path).expanduser().resolve(strict=True)
    if not source.is_file():
        raise ProbeError("Path must be a regular local file")
    if source.suffix.lower() not in EXTENSIONS:
        raise ProbeError("Expected a Matroska file (.mkv/.mka/.mks/.mk3d)")
    executable = shutil.which("ffprobe")
    if executable is None:
        raise ProbeError("FFprobe is required (install ffmpeg locally)")
    args = [executable, *PROBE_ARGS, "-i", str(source)]
    try:
        result = runner(args, capture_output=True, timeout=TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ProbeError("FFprobe timed out") from exc
    except OSError as exc:
        raise ProbeError("FFprobe could not start") from exc
    if result.returncode != 0:
        raise ProbeError("FFprobe could not inspect this Matroska file")
    if len(result.stdout) > OUTPUT_LIMIT:
        raise ProbeError("Metadata output is too large")
    try:
        document = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProbeError("FFprobe returned invalid JSON") from exc
    return normalize_tracks(document, source.name)


def format_text(report: dict[str, Any], language: str = "en") -> str:
    ru = language == "ru"
    if ru:
        label = {"file": "Файл", "video": "Видео", "audio": "Звук",
                 "subtitle": "Субтитры", "chapters": "Главы",
                 "unknown": "Проверка воспроизведения не проводилась"}
    else:
        label = {"file": "File", "video": "Video", "audio": "Audio",
                 "subtitle": "Subtitles", "chapters": "Chapters",
                 "unknown": "Playback/decoding not tested"}
    lines = [f'{label["file"]}: {report["filename"]}']
    for kind in ("video", "audio", "subtitle"):
        matching = [track for track in report["tracks"] if track["type"] == kind]
        lines.append(f'{label[kind]}: {len(matching)}')
        for track in matching:
            name = track["title"] or track["codec"]
            lines.append(f'  #{track["index"]}: {name} [{track["language"]}] '
                         f'({track["codec"]})')
    lines.append(f'{label["chapters"]}: {len(report["chapters"])}')
    lines.append(label["unknown"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only local Matroska track inspector for DK Browser development")
    parser.add_argument("file", type=Path, help="A local .mkv, .mka, .mks or .mk3d file")
    parser.add_argument("--lang", choices=("en", "ru"), default="en")
    parser.add_argument("--json", action="store_true",
                        help="Print stable machine-readable track metadata")
    options = parser.parse_args(argv)
    try:
        report = inspect_file(options.file)
    except (ProbeError, OSError, ValueError) as exc:
        print(f"Matroska inspection failed: {exc}", file=sys.stderr)
        return 1
    if options.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_text(report, options.lang))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
