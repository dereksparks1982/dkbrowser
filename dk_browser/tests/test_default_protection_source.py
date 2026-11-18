"""Read-only source contract for DK NetNav's default-on built-in blocker.

No compilation, browser execution, network access or GitHub Actions.
Not proof of runtime parity with the standalone Firefox blocker.
"""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = ROOT / "dk_browser" / "integrations" / "dk_live_block"
RUNTIME = COMPONENT / "runtime"

class DefaultProtectionSourceContract(unittest.TestCase):
    def test_default_on_and_bundled_dnr(self):
        manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertEqual(manifest["name"], "DK Live Block")
        self.assertIn("declarativeNetRequest", manifest["permissions"])
        self.assertTrue(manifest["declarative_net_request"]["rule_resources"][0]["enabled"])
        self.assertEqual(manifest["declarative_net_request"]["rule_resources"][0]["path"], "rules.json")
        self.assertIn("const DEFAULT={enabled:true", (RUNTIME / "background.js").read_text(encoding="utf-8"))

    def test_component_loads_natively_without_separate_installation(self):
        loader = (ROOT / "chrome/browser/extensions/component_loader.cc").read_text(encoding="utf-8")
        allowed = (ROOT / "chrome/browser/extensions/component_extensions_allowlist/allowlist.cc").read_text(encoding="utf-8")
        build = (ROOT / "chrome/browser/resources/BUILD.gn").read_text(encoding="utf-8")
        self.assertIn('Append(FILE_PATH_LITERAL("dk_live_block"))', loader)
        self.assertIn('Add(std::move(*manifest), dk_block)', loader)
        self.assertIn('"eoiabdloaoehfmeekmoccllbfebajimh"', allowed)
        self.assertIn('dk_live_block:component_resources', build)

    def test_every_declared_page_and_script_is_in_the_repo(self):
        manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
        worker = (COMPONENT / "chromium-background.js").read_text(encoding="utf-8")
        imported = re.findall(r'"([^"]+\\.js)"', worker)
        self.assertIn("runtime/background.js", imported)
        self.assertIn("chromium-dnr.js", imported)
        for module in imported:
            with self.subTest(module=module):
                self.assertTrue((COMPONENT / module).is_file(), module)
        for group in manifest["content_scripts"]:
            for module in [*group.get("js", []), *group.get("css", [])]:
                with self.subTest(module=module):
                    self.assertTrue((COMPONENT / module).is_file(), module)

    def test_no_claim_that_pending_av_or_ide_already_runs(self):
        roadmap = (ROOT / "dk_browser/ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("Nougat Security Analysis", roadmap)
        self.assertIn("native IDE", roadmap)
        self.assertIn("not yet implemented", roadmap)

if __name__ == "__main__":
    unittest.main()
