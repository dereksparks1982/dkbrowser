"""Check the fixed local-only DK AI entry point in Chromium's toolbar source.

This is a static test, not a Chromium compilation or UI runtime test.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
TOOLBAR = ROOT / "chrome/browser/ui/views/toolbar/toolbar_view.cc"
HEADER = ROOT / "chrome/browser/ui/views/toolbar/toolbar_view.h"


class DKAINativeToolbarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = TOOLBAR.read_text(encoding="utf-8")
        cls.header = HEADER.read_text(encoding="utf-8")

    def test_button_bilingual(self):
        self.assertIn('u"DK AI"', self.source)
        self.assertIn('u"ДК ИИ"', self.source)
        self.assertIn("OnDKAIButtonPressed", self.header)
        self.assertIn("ai_button_ = AddChildView", self.source)

    def test_only_fixed_loopback_new_tab(self):
        match = re.search(r"void ToolbarView::OnDKAIButtonPressed\("
                          r"[\s\S]*?\n\}", self.source)
        self.assertIsNotNone(match)
        method = match.group(0)
        self.assertIn('"http://127.0.0.1:8766/"', method)
        self.assertIn("content::OpenURLParams::CreateBrowserInitiated", method)
        self.assertIn("ui::mojom::WindowOpenDisposition::kNewForegroundTab",
                      method)
        self.assertIn("browser_->OpenURL(params", method)
        self.assertNotIn("GetActiveWebContents", method)
        self.assertNotIn("GetVisibleURL", method)
        self.assertNotIn("base::LaunchProcess", method)

    def test_language_switch_retained(self):
        self.assertIn("OnDKLanguageButtonPressed", self.source)
        self.assertIn('u"EN / РУ"', self.source)
        self.assertIn("chrome::AttemptRestart()", self.source)


if __name__ == "__main__":
    unittest.main()
