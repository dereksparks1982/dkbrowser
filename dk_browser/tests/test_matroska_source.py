"""DK Browser Matroska native-source regression checks.

These are source invariants, not proof of a working Chromium build.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "media/base"

class MatroskaSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (BASE / "container_names.cc").read_text(encoding="utf-8")
        cls.header = (BASE / "container_names.h").read_text(encoding="utf-8")
        cls.tests = (BASE / "container_names_unittest.cc").read_text(encoding="utf-8")
        cls.metrics = (ROOT / "tools/metrics/histograms/metadata/media/enums.xml").read_text(encoding="utf-8")
        cls.mimes = (BASE / "mime_util_internal.cc").read_text(encoding="utf-8")
        cls.glue = (ROOT / "media/filters/ffmpeg_glue.cc").read_text(encoding="utf-8")

    def test_ebml_doctype_native_classification(self):
        self.assertIn("CheckEbmlContainer", self.source)
        self.assertIn("TAG('w', 'e', 'b', 'm')", self.source)
        self.assertIn("TAG('m', 'a', 't', 'r')", self.source)
        self.assertIn("TAG('o', 's', 'k', 'a')", self.source)
        self.assertIn("MediaContainerName::kContainerMatroska", self.source)
        self.assertIn("RCHECK(tagsize == 4)", self.source)
        self.assertIn("RCHECK(tagsize == 8)", self.source)

    def test_native_media_identifiers_are_stable(self):
        self.assertIn("kContainerWEBM", self.header)
        self.assertIn("kContainerMatroska", self.header)
        self.assertIn("kMaxValue = kContainerMatroska", self.header)
        enum_start = self.metrics.index('<enum name="MediaContainers">')
        enum_end = self.metrics.index("</enum>", enum_start)
        values = re.findall(r'<int value="(\d+)" label="([^"]+)"', self.metrics[enum_start:enum_end])
        self.assertIn(("36", "Matroska / WebM"), values)
        self.assertIn(("40", "Matroska"), values)
        self.assertEqual(len(values), 41)
        self.assertEqual([int(x) for x, _ in values], list(range(41)))

    def test_compiled_cpp_regression_cases_exist(self):
        self.assertIn("TEST(ContainerNamesTest, DistinguishMatroskaAndWebmHeaders)", self.tests)
        self.assertIn("VERIFY(kMatroska, MediaContainerName::kContainerMatroska)", self.tests)
        self.assertIn("VERIFY(kWebm, MediaContainerName::kContainerWEBM)", self.tests)
        self.assertIn("kContainerUnknown", self.tests)

    def test_upstream_demuxer_routes_reused(self):
        for value in ('"video/matroska"', '"audio/matroska"',
                      '"video/x-matroska"', '"audio/x-matroska"'):
            self.assertIn(value, self.mimes)
        self.assertIn('"ogg,matroska,wav,flac,mp3,mov"', self.glue)

if __name__ == "__main__":
    unittest.main()
