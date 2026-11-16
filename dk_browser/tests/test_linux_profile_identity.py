"""Static checks for DK Browser's isolated Linux profile.

Run with: python3 -m unittest discover -s dk_browser/tests
No Chromium binary is compiled or launched.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class LinuxProfileIdentityTests(unittest.TestCase):
    def test_own_profile_and_preserved_implementation(self):
        cpp = (ROOT / "chrome/common/chrome_paths_linux.cc").read_text()
        self.assertIn('data_dir_basename = "dk-browser"', cpp)
        self.assertNotIn('data_dir_basename = "chromium"', cpp)
        self.assertIn('data_dir_basename = "google-chrome-for-testing"', cpp)
        self.assertIn('data_dir_basename = "google-chrome"', cpp)
        self.assertIn('GetChannelSuffixForDataDir()', cpp)
        self.assertIn('GetVar("CHROME_CONFIG_HOME")', cpp)
        self.assertIn('GetXDGDirectory(', cpp)

    def test_snap_config_agrees(self):
        snap = (ROOT / "chrome/installer/linux/snap/build.py").read_text()
        self.assertIn('return "dk-browser"', snap)
        self.assertIn('return "dk-browser-config"', snap)
        self.assertNotIn('return "chromium-config"', snap)
        self.assertIn('return f"google-chrome{suffix}"', snap)


if __name__ == "__main__":
    unittest.main()
