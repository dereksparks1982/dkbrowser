# DK Live Block bundled in DK Browser

This is a **full-source integration milestone**, not a browser-binary release or
a claim that Firefox's every privileged API works unchanged in Chromium.

## Source identity and ownership

- Source: `https://github.com/dereksparks1982/dkliveblock`
- Upstream snapshot: `264e7f5ad2df24582247bd74fcd18c073e622b01`
- Original extension manifest: `MV2-MANIFEST.reference.json`
- Upstream version: **0.3.371**.
- Original runtime modules and interface resources: `runtime/`.
- Original Linux companion Python source: `upstream/companion/` (not installed).
- Original terms: `DK_LIVE_BLOCK_LICENSE.txt`,
  `upstream/LICENSE`; third-party notices preserved in
  `runtime/LICENSE-GHOSTERY.txt`, `runtime/LICENSE-PSL.txt`,
  `runtime/LICENSE-FACEBOOK-MIT.txt` and `upstream/docs/ATTRIBUTIONS.md`.

The original implementation is brought over rather than replaced with a
collection of example rules. Where Chromium differs from Firefox, a
distinct Chromium adapter handles that boundary.

## Wiring

The native Chromium component loader registers the pinned extension identity
`eoiabdloaoehfmeekmoccllbfebajimh`. The public key in
`manifest.json` determines that exact identity. The GN copy targets
in `BUILD.gn` place the runtime alongside Chromium's
`resources/dk_live_block/` folder.

The Chromium MV3 manifest registers the original content scripts, including
Facebook/YouTube script groups, the original settings popup and diagnostic
pages. Its classic service worker, `chromium-background.js`, imports the
upstream background dependency chain in the same order as the Firefox MV2
manifest, with `chromium-compat.js` and `chromium-dnr.js` loaded at the
specific compatibility boundaries.

- **Original engine retained:** `runtime/rules.js`, `runtime/engine.js`,
  `runtime/hybrid-engine.js`, `runtime/ghostery-vendor.js`, plus the
  subscriber/list/exception modules.
- **Network backend:** DNR translates supported network filters using the
  original `DKRules.network` parser and applies dynamic filter updates.
  Explicit rule exceptions, resource types, selected scope/domain flags,
  global enable/disable and persistent site allowances are supported in
  source. Unsupported syntax is rejected, not broadened. The initial static seed remains active as a fallback if dynamic updates fail.
- **Page-side protection:** Original cosmetic and procedural, Facebook,
  YouTube, Nesty, popup and cookie modules remain registered. Their
  runtime behavior and feature compatibility require real-browser testing.
- **UI:** Original popup, options, site dashboard, local export and
  inspection HTML and JavaScript remain bundled. The `browser` API
  compatibility layer is injected in extension pages and content scripts.

## Known Chromium limits

Firefox Manifest V2 blocking `webRequest` callbacks cannot be reused
unchanged in Chromium MV3; those synchronous callbacks are skipped in the
Chromium worker and supported rules use DNR. Firefox response-body editing
(`filterResponseData`), Firefox-specific DNS/proxy and browser-wide
notification preferences, arbitrary request-by-request decisions and
some temporary per-tab bypasses are **not yet implemented natively**.
Some original UI controls can report unavailable actions or require
a browser-native adapter. Do not label these as working without a compiled
browser check. A snapshot of source modules is not proof of live filtering.

The optional companion remains reference source and is **never installed,
executed or granted nativeMessaging permissions automatically**.

## Checks before acceptance

Source tests (no download or GitHub Actions):

```sh
python3 -m unittest dk_browser.tests.test_dk_live_block_source
node --test dk_browser/integrations/dk_live_block/chromium-dnr.test.cjs
```

These verify manifest references, original module presence, branding,
pinned identity, loader and GN assets, adapter rule generation and
non-destructive rule refresh behavior. They do not compile Chromium.

Still to do: native Linux Chromium build, check extension start-up and
lifetime, DNR quota behaviour on EasyList/EasyPrivacy, runtime UI controls,
FB and YouTube video playback, content-script false positives, refresh
timers, licensing obligations and user-controlled site exceptions.

The built-in DK Live Block component is independent of DK Media Player:
that player remains web-only. No desktop player or browser download is
created by this integration.

## Protection switch correction (November 16, 2026)

The Chromium DNR adapter now toggles the bundled `dk_live_block_seed`
static ruleset along with its dynamic rules. Previously, switching off
protection removed only dynamic rules while ten static seed rules stayed
enabled. The adapter also re-enables the seed when protection resumes and
reports an error rather than claiming success if Chromium lacks the static
ruleset control API. Regression cases cover off/on transitions and the
missing-API case.

**Not a parity claim:** the bundled upstream snapshot is v0.3.371, while
DK Live Block development has progressed beyond that snapshot. Newer source
changes are not automatically synced. A full source refresh, manifest and
permission reconciliation, Chromium-compatible API adapters, a native build,
and actual browser interaction tests are still required before integration
can be called complete. Source tests are not a substitute for that work.
