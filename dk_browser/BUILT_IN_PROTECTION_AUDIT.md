# DK NetNav built-in protection: source-state audit

**November 17, 2026. Source review only, no compiled browser run.**

The code paths currently designed to load DK Live Block without an external add-on:
- `chrome/browser/extensions/component_loader.cc`: on non-Google Linux builds, locate `DIR_RESOURCES/dk_live_block/manifest.json` and use Chromium's ordinary allowlisted component `Add()` path.
- `chrome/browser/extensions/component_extensions_allowlist/allowlist.cc`: allows pinned component ID `eoiabdloaoehfmeekmoccllbfebajimh` under the same platform/branding guards.
- `chrome/browser/resources/BUILD.gn`: depends on `//dk_browser/integrations/dk_live_block:component_resources` under Linux with the extensions core enabled.
- `dk_browser/integrations/dk_live_block/BUILD.gn`: copies the Chromium manifest, adapter scripts, runtime scripts, UI pages, licenses, redirect resources, vendor files and icon into the expected resource tree.
- `dk_browser/integrations/dk_live_block/manifest.json`: Manifest V3 service worker, action, options, four groups of content scripts, and `declarative_net_request` static rule set `dk_live_block_seed` with `enabled: true`.
- `dk_browser/integrations/dk_live_block/runtime/background.js`: starts from `DEFAULT.enabled=true`; Chromium adapter synchronizes the compiled original filtering language to supported DNR dynamic rules and per-site controls.

**November 17 manifest review:** all 58 upstream background module filenames are imported in the correct relative order; all original content scripts in each of four groups are referenced in the Chromium manifest. Chromium-only compatibility paths are additional and intentionally precede original modules where needed.

**Remaining risks:** The native path has not been exercised in a compiled browser. Files existing, default flags, static lists and a manifest do not prove ad blocking, worker lifecycle, request cancellation or UI operation. Firefox-only response rewriting, synchronous per-request decisions and platform-specific DNS/proxy behavior need separate Chromium-native implementations. The standalone DK Live Block repository had failing verification; no green acceptance claim is warranted.

**Future acceptance:** source inventory; native Linux build/loader and manifest parsing; DNR quotas/state/rollback; pause and allowlist; MV3 worker restart; Facebook/YouTube behavior and playback safety; UI settings; EN/РУ; licenses; memory and repeatable, passing checks. Never disable a failing check to present a false green build.
