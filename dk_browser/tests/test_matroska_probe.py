"""Offline regression tests for read-only Matroska track inventory.

No real FFmpeg process, media file, network connection, or Chromium build needed.
"""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from dk_browser.tools import matroska_probe as probe


SAMPLE = {
    "format": {"format_name": "matroska,webm", "duration": "120.5"},
    "streams": [
        {"index": 0, "codec_type": "video", "codec_name": "hevc",
         "width": 1920, "height": 1080, "tags": {"language": "und"},
         "disposition": {"default": 1}},
        {"index": 1, "codec_type": "audio", "codec_name": "aac",
         "channels": 2, "tags": {"language": "eng", "title": "Original"},
         "disposition": {"default": 1}},
        {"index": 2, "codec_type": "audio", "codec_name": "flac",
         "channels": 6, "tags": {"language": "rus", "title": "Русский 5.1"}},
        {"index": 3, "codec_type": "subtitle", "codec_name": "ass",
         "tags": {"language": "rus", "title": "Русские субтитры"},
         "disposition": {"forced": 0}},
        {"index": 4, "codec_type": "subtitle", "codec_name": "hdmv_pgs_subtitle",
         "tags": {"language": "eng"}, "disposition": {"forced": 1}},
        {"index": 5, "codec_type": "attachment", "codec_name": "ttf"},
    ],
    "chapters": [
        {"id": 0, "start_time": "0.000", "end_time": "25.000",
         "tags": {"title": "Начало"}},
        {"id": 1, "start_time": "25.000", "end_time": "120.500",
         "tags": {"title": "The End"}},
    ],
}


class MatroskaProbeTests(unittest.TestCase):
    def test_multiple_audio_subtitle_languages_and_chapters(self):
        report = probe.normalize_tracks(SAMPLE, "фильм.mkv")
        self.assertEqual(report["schema"], "dk-browser.matroska-tracks.v1")
        self.assertEqual(report["counts"], {"video": 1, "audio": 2, "subtitle": 2})
        self.assertEqual([x["index"] for x in report["tracks"]], [0, 1, 2, 3, 4])
        self.assertEqual(report["tracks"][2]["language"], "rus")
        self.assertEqual(report["tracks"][3]["codec"], "ass")
        self.assertEqual(report["tracks"][4]["codec"], "hdmv_pgs_subtitle")
        self.assertTrue(report["tracks"][4]["forced"])
        self.assertEqual(report["tracks"][0]["width"], 1920)
        self.assertEqual(report["tracks"][2]["channels"], 6)
        self.assertEqual(len(report["chapters"]), 2)
        self.assertIsNone(report["playable"])

    def test_terminal_control_characters_are_stripped(self):
        source = {"streams": [{"index": 0, "codec_type": "audio",
                               "tags": {"title": "\x1b[31mRed\nTitle", "language": "ru\ns"}}]}
        report = probe.normalize_tracks(source, "film.mka")
        self.assertNotIn("\x1b", report["tracks"][0]["title"])
        self.assertNotIn("\n", report["tracks"][0]["title"])
        self.assertEqual(report["tracks"][0]["language"], "rus")

    def test_missing_or_malformed_metadata(self):
        report = probe.normalize_tracks({"streams": [
            {"index": "0", "codec_type": "subtitle", "codec_name": "subrip"},
            {"index": 1, "codec_type": "data", "codec_name": "x"},
        ]}, "film.mks")
        self.assertEqual(report["counts"]["subtitle"], 1)
        self.assertEqual(report["tracks"][0]["language"], "und")
        self.assertEqual(report["chapters"], [])

    def test_reject_invalid_streams_and_duplicates(self):
        with self.assertRaises(probe.ProbeError):
            probe.normalize_tracks({"streams": {}}, "movie.mkv")
        with self.assertRaises(probe.ProbeError):
            probe.normalize_tracks({"streams": [{"index": 1, "codec_type": "audio"},
                                               {"index": 1, "codec_type": "subtitle"}]}, "movie.mkv")
        with self.assertRaises(probe.ProbeError):
            probe.normalize_tracks({"streams": [
                {"codec_type": "audio", "index": -1}]}, "movie.mkv")
        with self.assertRaises(probe.ProbeError):
            probe.normalize_tracks({"streams": [{}] * 257}, "movie.mkv")

    def test_text_report_in_both_languages(self):
        report = probe.normalize_tracks(SAMPLE, "фильм.mkv")
        english = probe.format_text(report)
        russian = probe.format_text(report, "ru")
        self.assertIn("Subtitles: 2", english)
        self.assertIn("Субтитры: 2", russian)
        self.assertIn("Русские субтитры [rus]", russian)
        self.assertIn("Playback/decoding not tested", english)
        self.assertIn("Проверка воспроизведения не проводилась", russian)

    def _run_fake(self, filename, *, data=SAMPLE, returncode=0, output=None,
                  side_effect=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, filename)
            path.write_bytes(b"\x1a\x45\xdf\xa3")  # fixture is not decoded
            called = []
            def fake_run(argv, **kwargs):
                called.append((argv, kwargs))
                if side_effect:
                    raise side_effect
                return subprocess.CompletedProcess(
                    argv, returncode,
                    json.dumps(data, ensure_ascii=False).encode() if output is None else output,
                    b"")
            with mock.patch.object(probe.shutil, "which", return_value="/usr/bin/ffprobe"):
                if path.suffix.lower() not in probe.EXTENSIONS:
                    with self.assertRaises(probe.ProbeError):
                        probe.inspect_file(path, runner=fake_run)
                    return called
                if side_effect or returncode or output is not None:
                    with self.assertRaises(probe.ProbeError):
                        probe.inspect_file(path, runner=fake_run)
                    return called
                return probe.inspect_file(path, runner=fake_run), called

    def test_local_probe_command_is_restricted(self):
        report, calls = self._run_fake("Movie.MKV")
        self.assertEqual(report["filename"], "Movie.MKV")
        argv, kwargs = calls[0]
        self.assertIn("-protocol_whitelist", argv)
        self.assertEqual(argv[argv.index("-protocol_whitelist") + 1], "file")
        self.assertEqual(argv[argv.index("-i") + 1], str(Path(argv[-1]).resolve()))
        self.assertNotIn("http,https", argv)
        self.assertEqual(kwargs["timeout"], probe.TIMEOUT_SECONDS)
        self.assertTrue(kwargs["capture_output"])

    def test_other_types_are_rejected(self):
        self.assertEqual(self._run_fake("movie.mp4"), [])
        with self.assertRaises(FileNotFoundError):
            probe.inspect_file(Path("/nonexistent-private-file/movie.mkv"))

    def test_probe_failures_are_contained(self):
        self._run_fake("movie.mkv", returncode=1)
        self._run_fake("movie.mkv", output=b"{corrupt json")
        self._run_fake("movie.mkv", output=b"x" * (probe.OUTPUT_LIMIT + 1))
        self._run_fake("movie.mkv", side_effect=subprocess.TimeoutExpired("ffprobe", 1))
        self._run_fake("movie.mkv", side_effect=OSError("bad executable"))

    def test_json_serializes_with_russian_names(self):
        report = probe.normalize_tracks(SAMPLE, "фильм.mkv")
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertIn("Русский", encoded)
        self.assertEqual(json.loads(encoded)["tracks"][2]["title"], "Русский 5.1")

    def test_cli_json_and_russian_modes(self):
        report = probe.normalize_tracks(SAMPLE, "фильм.mkv")
        stdout = io.StringIO()
        with mock.patch.object(probe, "inspect_file", return_value=report):
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(probe.main(["movie.mkv", "--json"]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["schema"], probe.SCHEMA)
        stdout = io.StringIO()
        with mock.patch.object(probe, "inspect_file", return_value=report):
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(probe.main(["movie.mkv", "--lang", "ru"]), 0)
        self.assertIn("Субтитры: 2", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
