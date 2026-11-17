"""Source checks for the bundled complete DK Live Block Chromium integration.

No Chromium compilation, browser launch, GitHub Actions, or network access.
Run from the DK Browser checkout:
  python3 -m unittest dk_browser.tests.test_dk_live_block_source
"""
import base64
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "dk_browser" / "integrations" / "dk_live_block"
RUNTIME = DIRECTORY / "runtime"


class DKLiveBlockIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((DIRECTORY / "manifest.json").read_text(encoding="utf-8"))
        cls.rules = json.loads((DIRECTORY / "rules.json").read_text(encoding="utf-8"))
        cls.worker = (DIRECTORY / "chromium-background.js").read_text(encoding="utf-8")
        cls.compat = (DIRECTORY / "chromium-compat.js").read_text(encoding="utf-8")
        cls.dnr = (DIRECTORY / "chromium-dnr.js").read_text(encoding="utf-8")
        cls.loader = (ROOT / "chrome/browser/extensions/component_loader.cc").read_text(encoding="utf-8")
        cls.allow = (ROOT / "chrome/browser/extensions/component_extensions_allowlist/allowlist.cc").read_text(encoding="utf-8")
        cls.build = (ROOT / "chrome/browser/resources/BUILD.gn").read_text(encoding="utf-8")
        cls.gn = (DIRECTORY / "BUILD.gn").read_text(encoding="utf-8")

    def test_full_manifest_is_chromium_v3_not_firefox_v2(self):
        m = self.manifest
        self.assertEqual(m["name"], "DK Live Block")
        self.assertEqual(m["version"], "0.3.371")
        self.assertEqual(m["manifest_version"], 3)
        self.assertIn("declarativeNetRequest", m["permissions"])
        self.assertIn("webRequest", m["permissions"])
        self.assertNotIn("webRequestBlocking", m["permissions"])
        self.assertNotIn("browser_specific_settings", m)
        self.assertNotIn("proxy", m["permissions"])
        self.assertNotIn("nativeMessaging", m.get("permissions", []))
        self.assertNotIn("nativeMessaging", m.get("optional_permissions", []))
        self.assertEqual(m["host_permissions"], ["<all_urls>"])
        self.assertEqual(m["background"]["service_worker"], "chromium-background.js")
        self.assertEqual(m["action"]["default_popup"], "runtime/popup.html")

    def test_full_background_dependency_chain(self):
        imported = re.findall(r'"([^"]+\.js)"', self.worker)
        self.assertGreaterEqual(len(imported), 58)
        self.assertEqual(imported[0], "chromium-compat.js")
        self.assertEqual(imported[-1], "runtime/background.js")
        self.assertIn("runtime/ghostery-vendor.js", imported)
        self.assertIn("runtime/hybrid-engine.js", imported)
        self.assertIn("runtime/nesty-intelligence.js", imported)
        self.assertIn("runtime/meta-graphql.js", imported)
        self.assertIn("runtime/rules.js", imported)
        self.assertIn("chromium-dnr.js", imported)
        self.assertIn("DKChromiumDNR=globalThis.DKChromiumRules.create", self.worker)
        for path in imported:
            with self.subTest(path=path):
                self.assertTrue((DIRECTORY / path).is_file(), path)

    def test_page_scripts_and_resources_are_present(self):
        m = self.manifest
        self.assertEqual(len(m["content_scripts"]), 4)
        all_files = [m["background"]["service_worker"], m["action"]["default_popup"],
                     m["action"]["default_icon"], m["options_ui"]["page"],
                     m["devtools_page"]]
        for entry in m["content_scripts"]:
            all_files.extend(entry["js"])
            all_files.extend(entry.get("css", []))
            if entry.get("world") != "MAIN":
                self.assertEqual(entry["js"][0], "chromium-compat.js")
        for item in m["web_accessible_resources"]:
            all_files.extend(item["resources"])
        for filename in all_files:
            with self.subTest(filename=filename):
                self.assertTrue((DIRECTORY / filename).is_file(), filename)
                self.assertIn('"' + filename + '"', self.gn)

    def test_original_source_modules_and_interfaces_embedded(self):
        source = list(RUNTIME.rglob("*.js"))
        html = list(RUNTIME.rglob("*.html"))
        self.assertGreaterEqual(len(source), 120)
        self.assertGreaterEqual(len(html), 16)
        must_have = [
            "background.js", "rules.js", "engine.js", "hybrid-engine.js",
            "ghostery-vendor.js", "facebook-ads.js", "facebook-full-core.js",
            "youtube-page-bridge.js", "youtube-response.js", "nesty-team.js",
            "nesty-intelligence.js", "meta-graphql.js", "content.js",
            "options.js", "site-dashboard.js", "popup.js", "ui-language.js",
            "public-suffix.js", "safe-scriptlet-runtime.js"
        ]
        for name in must_have:
            self.assertTrue((RUNTIME / name).is_file(), name)
            self.assertIn('"runtime/' + name + '"', self.gn)

    def test_ui_browser_compat_in_every_page(self):
        for page in RUNTIME.glob("*.html"):
            with self.subTest(page=page.name):
                src = page.read_text(encoding="utf-8")
                self.assertIn('../chromium-compat.js', src)

    def test_source_icon_and_licenses(self):
        self.assertTrue((RUNTIME / "icons/dk-live-block.png").is_file())
        self.assertTrue((DIRECTORY / "DK_LIVE_BLOCK_LICENSE.txt").is_file())
        self.assertTrue((RUNTIME / "LICENSE-GHOSTERY.txt").is_file())
        self.assertTrue((RUNTIME / "LICENSE-FACEBOOK-MIT.txt").is_file())
        self.assertTrue((RUNTIME / "LICENSE-PSL.txt").is_file())
        self.assertTrue((DIRECTORY / "upstream/companion/native_host.py").is_file())
        self.assertTrue((DIRECTORY / "MV2-MANIFEST.reference.json").is_file())

    def test_chromium_component_pinned_identity(self):
        key = base64.b64decode(self.manifest["key"], validate=True)
        digest = hashlib.sha256(key).digest()[:16]
        ext_id = "".join(chr(97 + (byte >> shift & 15))
                         for byte in digest for shift in (4, 0))
        self.assertEqual(ext_id, "eoiabdloaoehfmeekmoccllbfebajimh")
        self.assertIn('"' + ext_id + '"', self.allow)

    def test_native_loader_and_outputs(self):
        self.assertIn('Append(FILE_PATH_LITERAL("dk_live_block"))', self.loader)
        self.assertIn("Add(std::move(*manifest), dk_block)", self.loader)
        self.assertNotIn("AddOrReplace(dk_block)", self.loader)
        self.assertIn("BUILDFLAG(IS_LINUX)", self.loader)
        self.assertIn("!BUILDFLAG(GOOGLE_CHROME_BRANDING)", self.loader)
        self.assertIn('dk_live_block:component_resources', self.build)
        self.assertIn('$root_out_dir/resources/dk_live_block/', self.gn)
        self.assertIn('group("component_resources")', self.gn)
        for name in ("runtime_root_assets", "runtime_redirect_assets",
                     "runtime_vendor_assets", "runtime_icons"):
            self.assertIn('copy("' + name + '")', self.gn)

    def test_mv2_sync_interception_not_registered_on_chromium(self):
        legacy = (RUNTIME / "background.js").read_text(encoding="utf-8")
        self.assertIn("if (!globalThis.DKChromiumRuntime?.dnr)", legacy)
        self.assertIn("DKChromiumDNR.sync(next,chromiumSettings)", legacy)
        self.assertIn("chrome", self.compat.lower())
        self.assertIn("onMessage", self.compat)
        self.assertIn("updateDynamicRules", self.dnr)
        self.assertIn("parsed.scope", self.dnr)
        self.assertIn("excludedInitiatorDomains", self.dnr)
        self.assertIn("MAX_DYNAMIC=25000", self.dnr)

    def test_original_fallback_list_is_preserved_but_not_only_backend(self):
        self.assertEqual(len(self.rules), 10)
        self.assertTrue(all(r["action"] == {"type": "block"} for r in self.rules))
        self.assertEqual(
            self.manifest["declarative_net_request"]["rule_resources"],
            [{"id": "dk_live_block_seed", "enabled": True, "path": "rules.json"}]
        )
        self.assertIn('updateDynamicRules', self.dnr)

    def test_chromium_protection_controls_acknowledge_real_backend_state(self):
        background = (RUNTIME / "background.js").read_text(encoding="utf-8")
        popup = (RUNTIME / "popup.js").read_text(encoding="utf-8")
        popup_html = (RUNTIME / "popup.html").read_text(encoding="utf-8")
        self.assertIn("return chromiumResult;", background)
        self.assertIn("const applied=await rebuild();", background)
        self.assertIn("data.settings.enabled=previous;", background)
        self.assertIn("Chromium protection switch failed:", background)
        self.assertIn("dynamic rollback failed", self.dnr)
        self.assertIn("static rollback failed", self.dnr)
        self.assertIn("getEnabledRulesets", self.dnr)
        self.assertIn("chromiumProtectionStatus", popup_html)
        self.assertIn("current.chromiumDNR?.error", popup)
        self.assertIn("reply?.error", popup)

    def test_chromium_controls_report_backend_errors_instead_of_false_success(self):
        background = (RUNTIME / "background.js").read_text(encoding="utf-8")
        self.assertIn("async function acceptRuleChange(rollback,save,label)", background)
        self.assertIn("Selective request block was not applied", background)
        self.assertIn("Remembered request allowance was not applied", background)
        self.assertIn("Website allowlist switch was not applied", background)
        self.assertIn("Settings network filters were not applied", background)
        self.assertIn("Built-in subscription switch was not applied", background)
        self.assertIn("initialRules=await rebuild()", background)
        self.assertIn("temporary/session request allowances are not yet supported", background)
        self.assertIn("Chromium cannot block this request type precisely", background)
        self.assertIn("Chromium cannot allow this request type precisely", background)
        self.assertIn("Protection was not saved; previous setting restored", background)

    def test_chromium_compat_listener_bridge_has_identity_and_multi_listener_safety(self):
        compat_tests = DIRECTORY / "chromium-compat.test.cjs"
        self.assertTrue(compat_tests.is_file())
        self.assertIn("if(result===undefined)return false", self.compat)
        self.assertIn("const bridges=new WeakMap()", self.compat)
        self.assertIn("removeListener(handler)", self.compat)
        self.assertIn("hasListener(handler)", self.compat)

    def test_no_automated_installer_or_action(self):
        self.assertFalse((DIRECTORY / ".github/workflows").exists())
        self.assertFalse((DIRECTORY / "install.sh").exists())
        self.assertTrue((DIRECTORY / "upstream/companion/native_host.py").is_file())


if __name__ == "__main__":
    unittest.main()
