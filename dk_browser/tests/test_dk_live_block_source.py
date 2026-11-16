"""Checks the first built-in DK Live Block source integration.

These checks do not claim Firefox rule parity, complete Chromium compilation
or live browser blocking behavior.
"""
import base64
import hashlib
import json
from pathlib import Path
import unittest

from dk_browser.integrations.dk_live_block.generate_rules import generate

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "dk_browser" / "integrations" / "dk_live_block"


class DKLiveBlockComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((DIR / "manifest.json").read_text(encoding="utf-8"))
        cls.rules = json.loads((DIR / "rules.json").read_text(encoding="utf-8"))
        cls.loader = (ROOT / "chrome/browser/extensions/component_loader.cc").read_text(encoding="utf-8")
        cls.allow = (ROOT / "chrome/browser/extensions/component_extensions_allowlist/allowlist.cc").read_text(encoding="utf-8")
        cls.build = (ROOT / "chrome/browser/resources/BUILD.gn").read_text(encoding="utf-8")
        cls.resources = (DIR / "BUILD.gn").read_text(encoding="utf-8")

    def test_mv3_not_firefox_addon(self):
        m = self.manifest
        self.assertEqual(m["name"], "DK Live Block")
        self.assertEqual(m["manifest_version"], 3)
        self.assertEqual(m["permissions"], ["declarativeNetRequest"])
        self.assertNotIn("webRequestBlocking", m["permissions"])
        self.assertNotIn("browser_specific_settings", m)
        self.assertNotIn("nativeMessaging", m["permissions"])

    def test_manifest_assets_are_bundled(self):
        rule = self.manifest["declarative_net_request"]["rule_resources"][0]
        self.assertEqual(rule["path"], "rules.json")
        self.assertTrue(rule["enabled"])
        for script in self.manifest["content_scripts"]:
            for css in script.get("css", []):
                self.assertTrue((DIR / css).is_file(), css)
                self.assertIn('"' + css + '"', self.resources)
        self.assertIn('"manifest.json"', self.resources)
        self.assertIn('"rules.json"', self.resources)
        self.assertIn('"DK_LIVE_BLOCK_LICENSE.txt"', self.resources)

    def test_stable_key_matches_allowlist(self):
        public = base64.b64decode(self.manifest["key"], validate=True)
        digest = hashlib.sha256(public).digest()[:16]
        extension_id = "".join(chr(97 + (c >> 4)) + chr(97 + (c & 15))
                               for c in digest)
        self.assertEqual(extension_id, "eoiabdloaoehfmeekmoccllbfebajimh")
        self.assertIn('"' + extension_id + '"', self.allow)

    def test_normal_component_loader_not_development_bypass(self):
        self.assertIn('Append(FILE_PATH_LITERAL("dk_live_block"))', self.loader)
        self.assertIn("Add(std::move(*manifest), dk_block)", self.loader)
        self.assertIn("file_util::LoadManifest(dk_block", self.loader)
        self.assertIn("should_disable_background_extensions", self.loader)
        self.assertNotIn("AddOrReplace(dk_block)", self.loader)

    def test_limited_linux_wiring(self):
        self.assertIn("BUILDFLAG(IS_LINUX)", self.loader)
        self.assertIn("!BUILDFLAG(GOOGLE_CHROME_BRANDING)", self.loader)
        self.assertIn('dk_live_block:component_resources', self.build)
        self.assertIn('copy("component_resources")', self.resources)
        self.assertIn('$root_out_dir/resources/dk_live_block/{{source_file_part}}',
                      self.resources)

    def test_initial_network_seed_is_scoped(self):
        self.assertEqual(len(self.rules), 10)
        ids = [x["id"] for x in self.rules]
        self.assertEqual(ids, list(range(1, len(ids) + 1)))
        self.assertTrue(all(x["action"] == {"type": "block"} for x in self.rules))
        self.assertIn("||doubleclick.net^",
                      [x["condition"]["urlFilter"] for x in self.rules])
        targeted = [x for x in self.rules
                    if "initiatorDomains" in x["condition"]]
        self.assertEqual(len(targeted), 1)
        self.assertEqual(targeted[0]["condition"]["resourceTypes"], ["media"])

    def test_css_targets_are_separated(self):
        generic = (DIR / "cosmetics.css").read_text(encoding="utf-8")
        youtube = (DIR / "youtube.css").read_text(encoding="utf-8")
        self.assertIn(".adsbygoogle", generic)
        self.assertIn("#player-ads", youtube)
        self.assertNotIn("#player-ads", generic)

    def test_adapter_rejects_untranslatable_rules(self):
        sample = 'const SEED=["! Comment","||example.org^","##.ads"].join("\\n");'
        generated = generate(sample)
        self.assertEqual(len(json.loads(generated["rules.json"])), 1)
        self.assertIn(".ads", generated["cosmetics.css"])
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            generate('const SEED=["||example.com^$script,important"].join("\\n");')
        with self.assertRaisesRegex(ValueError, "not found"):
            generate("const unrelated = true;")


if __name__ == "__main__":
    unittest.main()
