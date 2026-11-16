"""Source checks for independent DK Browser Linux packages.

Run with: python3 -m unittest discover -s dk_browser/tests
These checks do not generate or install any binary packages.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


def source(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


class PackageIdentityTests(unittest.TestCase):
    def test_package_name_and_paths(self):
        info = source("chrome/installer/linux/common/chromium-browser.info")
        self.assertIn('PACKAGE="dk-browser"', info)
        self.assertIn('INSTALLDIR=/opt/dksoftworks/dk-browser', info)
        self.assertIn('MENUNAME="DK Browser"', info)
        self.assertIn('RDN="io.github.dereksparks1982.DKBrowser"', info)
        self.assertIn('PROGNAME=chrome', info)

    def test_linux_gn_package_name(self):
        gn = source("chrome/installer/linux/BUILD.gn")
        self.assertIn('package = "dk-browser"', gn)
        self.assertIn('if (is_chrome_branded)', gn)
        self.assertIn('package = "google-chrome"', gn)
        self.assertIn('package = "google-chrome-repo"', gn)

    def test_launcher_identity_and_russian_translation(self):
        shell = source("chrome/browser/shell_integration_linux.cc")
        self.assertIn('return "dk-browser";', shell)
        desktop = source("chrome/installer/linux/common/desktop.template")
        self.assertIn('Name[ru]=ДК Браузер', desktop)
        self.assertIn('Icon=@@desktop_icon', desktop)

    def test_no_google_updater_for_dk_package(self):
        for script in (
            "chrome/installer/linux/debian/postinst",
            "chrome/installer/linux/debian/postrm",
            "chrome/installer/linux/common/repo.cron",
            "chrome/installer/linux/common/rpmrepo.cron",
        ):
            text = source(script)
            self.assertIn('if [ "@@package_orig" ', text, script)
        spec = source("chrome/installer/linux/rpm/chrome.spec.template")
        self.assertIn('"@@package_orig" != "dk-browser"', spec)
        installer = source("chrome/installer/linux/common/installer.py")
        self.assertIn('if package == "dk-browser":', installer)
        self.assertIn('return "", ""', installer)


if __name__ == "__main__":
    unittest.main()
