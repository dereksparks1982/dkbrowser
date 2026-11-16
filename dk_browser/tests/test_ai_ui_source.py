"""Static checks for DK AI's explicit privacy and locale controls."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2] / "dk_browser/ai"


class DKAIUIModulesTest(unittest.TestCase):
    def test_russian_and_english_controls(self):
        js = (ROOT / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('export:"Сохранить переписку"', js)
        self.assertIn('export:"Export chat"', js)
        self.assertIn('id="export"', html)
        self.assertIn('navigator.language.toLowerCase().starts_with', js.replace('.startsWith(','.starts_with('))
        self.assertIn('document.documentElement.lang = language', js)

    def test_transcript_is_session_only(self):
        js = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('localStorage.setItem("dk-ai-language"', js)
        self.assertNotIn('localStorage.setItem("chat"', js)
        self.assertNotIn('sessionStorage', js)
        self.assertIn('transcript = []', js)
        self.assertIn('URL.createObjectURL(blob)', js)
        self.assertIn('anchor.click()', js)
        self.assertIn('renderMessage(entry.role, entry.content)', js)

    def test_ui_never_injects_html(self):
        js = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", js)
        self.assertIn("line.textContent", js)
        self.assertIn('fetch("/api/chat"', js)


if __name__ == "__main__":
    unittest.main()
