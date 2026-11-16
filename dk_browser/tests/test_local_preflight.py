"""Small unit tests for the local, CI-free source preflight checker."""
import unittest

from dk_browser.tools import preflight


class LocalPreflightTests(unittest.TestCase):
    def test_visible_russian_prose_excludes_code_and_links(self):
        source = ("Описание [изображения](images/file.png) и "
                  "`text: Linux`\n"
                  "```bash\nnode --check app.js\n```")
        self.assertNotIn("Linux", preflight.visible_russian_text(source))
        self.assertNotIn("node", preflight.visible_russian_text(source))
        self.assertNotIn("images", preflight.visible_russian_text(source))
        self.assertIn("Описание", preflight.visible_russian_text(source))

    def test_git_blob_digest_of_known_content(self):
        self.assertEqual(
            preflight.blob_sha(b"hello world\n"),
            "3b18e512dba79e4c8300dd08aeb37f8e728b8dad"
        )

    def test_current_repository_passes_baseline(self):
        self.assertEqual([], preflight.validate())


if __name__ == "__main__":
    unittest.main()
