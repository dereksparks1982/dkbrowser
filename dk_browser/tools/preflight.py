#!/usr/bin/env python3
"""Run DK Browser's CI-free source checks locally.

No downloads, package installations, network calls, background work, or GitHub
Actions. Requires Python 3.10+; optional Node for JavaScript syntax checking.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "images"
# SHA-1 here verifies the known Git blob identities of the two approved
# image masters; it is not used as a cryptographic security signature.
APPROVED_ICONS = {
    "DK Browser Imperial Icon.png": "cdf18df0ab941faccb539026cdf1203749ee8a1e",
    "DK Browser Russian Imperial Icon.png": "d67437ac56aa6ae930ea2b632758237f827568aa",
}


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def visible_russian_text(markdown: str) -> str:
    """Remove URL targets, HTML attributes, and literal code before checking."""
    markdown = re.sub(r"\`\`\`[^\n]*\n[\s\S]*?\`\`\`", "", markdown)
    markdown = re.sub(r"\`[^\`]*\`", "", markdown)
    markdown = re.sub(r"<[^>]*>", "", markdown)
    markdown = re.sub(r"\]\([^)]*\)", "]", markdown)
    return markdown


def validate():
    issues = []

    def check(condition, explanation):
        if not condition:
            issues.append(explanation)

    for file_name, expected_sha in APPROVED_ICONS.items():
        path = ASSETS / file_name
        check(path.is_file(), f"Missing official image: {file_name}")
        if path.is_file():
            check(blob_sha(path.read_bytes()) == expected_sha,
                  f"Approved artwork was replaced: {file_name}")

    en = (ROOT / "README.md").read_text(encoding="utf-8")
    ru = (ROOT / "README.ru.md").read_text(encoding="utf-8")
    check('DK%20Browser%20Imperial%20Icon.png' in en,
          "English front page has no official English icon.")
    check('DK%20Browser%20Russian%20Imperial%20Icon.png' in ru,
          "Russian front page has no official Russian icon.")
    check("(README.ru.md)" in en and "(README.md)" in ru,
          "Both README language navigation links must exist.")
    latin = sorted(set(re.findall(r"[A-Za-z]+", visible_russian_text(ru))))
    check(not latin, "English words are visible in the Russian README: " +
          ", ".join(latin[:10]))

    theme = (ROOT / "chrome/app/theme/theme_resources.grd").read_text()
    for resource in ("IDR_DK_BROWSER_ICON_EN", "IDR_DK_BROWSER_ICON_RU"):
        check(resource in theme, f"Missing native image resource: {resource}")
    for suffix, master in (
        ("en", "DK Browser Imperial Icon.png"),
        ("ru", "DK Browser Russian Imperial Icon.png"),
    ):
        icon = (ROOT / "chrome/app/theme/default_100_percent/chromium" /
                f"dk_browser_icon_{suffix}.png")
        check(icon.is_file(), f"Missing native {suffix} icon.")
        if icon.is_file():
            check(icon.read_bytes() == (ASSETS / master).read_bytes(),
                  f"Native {suffix} resource does not match its approved master.")

    profile = (ROOT / "chrome/common/chrome_paths_linux.cc").read_text()
    check('data_dir_basename = "dk-browser"' in profile,
          "Linux default profile is not isolated from Chromium.")
    package = (ROOT / "chrome/installer/linux/common/chromium-browser.info").read_text()
    check('PACKAGE="dk-browser"' in package,
          "Linux package identity was changed from DK Browser.")
    for path in (
        "chrome/installer/linux/debian/postinst",
        "chrome/installer/linux/common/repo.cron",
        "chrome/installer/linux/common/rpmrepo.cron",
    ):
        text = (ROOT / path).read_text()
        check('"@@package_orig" ' in text and '"dk-browser"' in text,
              f"Missing DK-specific upstream repository safety check: {path}")

    toolbar = (ROOT / "chrome/browser/ui/views/toolbar/toolbar_view.cc").read_text()
    toolbar_header = (ROOT / "chrome/browser/ui/views/toolbar/toolbar_view.h").read_text()
    check('u"ДК ИИ"' in toolbar and 'u"DK AI"' in toolbar,
          "DK AI native toolbar button has lost its bilingual labels.")
    check('GURL(kLocalAssistantURL)' in toolbar and
          'kLocalAssistantURL[] = "http://127.0.0.1:8766/"' in toolbar and
          'kNewForegroundTab' in toolbar and
          'browser_->OpenURL(params,' in toolbar,
          "DK AI toolbar must open its fixed local service in a new tab.")
    check('OnDKAIButtonPressed' in toolbar_header,
          "DK AI native toolbar callback declaration is missing.")

    ui = (ROOT / "dk_browser/ai/app.js").read_text(encoding="utf-8")
    check("localStorage.setItem(\"dk-ai-language\"" in ui,
          "Local assistant lost persisted language selection.")
    check("innerHTML" not in ui,
          "AI chat must never render model-provided HTML.")
    server = (ROOT / "dk_browser/ai/server.py").read_text(encoding="utf-8")
    check('("127.0.0.1", port)' in server,
          "AI service is not explicitly loopback-bound.")
    check('self.headers.get("Origin") != self.server.origin' in server,
          "AI service lost its cross-origin write protection.")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="DK Browser local source checks")
    parser.add_argument("--no-tests", action="store_true",
                        help="Skip local Python tests and JavaScript parser check")
    args = parser.parse_args()

    errors = validate()
    for error in errors:
        print("FAIL:", error)
    if errors:
        return 1
    print("PASS: approved icons, Russian text, browser identity, AI safeguards")

    if not args.no_tests:
        print("Running Python source/unit tests (no external model required)...")
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s",
             "dk_browser/tests"], cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
        node = shutil.which("node")
        if node:
            result = subprocess.run([node, "--check", str(ROOT / "dk_browser/ai/app.js")],
                                    check=False)
            if result.returncode:
                return result.returncode
            print("PASS: DK AI JavaScript syntax")
        else:
            print("SKIP: Node is unavailable; JavaScript syntax check skipped.")
    print("PASS: DK Browser local source preflight")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
