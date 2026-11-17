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

- **Tab-only pause:** Chromium-specific session DNR rules carry the current
  paused tab IDs with high-priority document-scoped allowances. A session-only
  storage record restores them when MV3 suspends/restarts the worker and
  closed-tab cleanup removes obsolete entries. This does not persist after
  closing the browser and is not a site-wide exception.
- **Selective controls:** Persisted, user-confirmed host/type blocks and
  remembered allowances reach dynamic DNR. Network Monitor session-wide and
  ten-minute tab-specific request allowances now use distinct session DNR
  rules, with saved worker-session state, expiry alarms and tab cleanup.
  Firefox's exact per-request telemetry is not available on Chromium.
  During MV3 worker startup, tab changes cannot overwrite session storage
  before it has been read. Restored short-lived allowances are discarded
  when their tab has closed, changed first-party hostname, or expired.
  After the initial DNR update, a second live-tab query reconciles any
  further changes. These source protections require browser testing.
- **Page-side protection:** Original cosmetic and procedural, Facebook,
  YouTube, Nesty, popup and cookie modules remain registered. Their
  runtime behavior and feature compatibility require real-browser testing.
- **UI:** Original popup, options, site dashboard, local export and
  inspection HTML and JavaScript remain bundled. The `browser` API
  compatibility layer is injected in extension pages and content scripts.

## Chromium site-wide pauses

The Firefox site pause used to compile to a priority-10 document allowance,
which could lose to a priority-30 manual block. The Chromium adapter now
combines up to 300 deduplicated paused hostnames into two priority-50
allowances: document/subframe navigation by request domain, and new
non-main-frame requests by initiator domain. The latter applies to newly
started requests when a tab is already open; it does not turn the pause
into a global allow for other sites. Both rules reserve DNR quota slots.
This is a source-level change, not proof of live Chromium behavior.

## Known Chromium limits

Firefox Manifest V2 blocking `webRequest` callbacks cannot be reused
unchanged in Chromium MV3; those synchronous callbacks are skipped in the
Chromium worker and supported rules use DNR. Firefox response-body editing
(`filterResponseData`), Firefox-specific DNS/proxy and browser-wide
notification preferences and arbitrary Firefox callback decisions are
**not yet implemented natively**. Source-level scoped request allowances do
not provide arbitrary per-request interception.
Some original UI controls can report unavailable actions or require
a browser-native adapter. Do not label these as working without a compiled
browser check. A snapshot of source modules is not proof of live filtering.

Chromium tab pauses, remembered and short-lived request allowances are
source-level only; their effects and UI status have not been verified in a
compiled browser.

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

**Source freshness audit:** As of November 16, 2026, the upstream
`dkliveblock/main` tree still points to
`264e7f5ad2df24582247bd74fcd18c073e622b01`, the precise commit
already vendored here. Its 154 source files were compared with the bundled
runtime by Git blob identity. Only the expected Chromium-adapted
`background.js`, `icon-state.js` and HTML entrypoints differ; the Firefox
manifest is preserved separately as a reference. This does not establish
runtime feature parity or guarantee upstream stays at this commit.

**Additional Chromium rule wiring:** Persisted, user-confirmed selective
blocks and remembered host/type allowances are passed to DNR at startup and
after changes. User blocks take precedence, and specialized resource types
that Chromium cannot represent are skipped rather than widened. Tab-only
and session-only allowances are intentionally **not** promoted into
persistent Chromium dynamic rules. DNR host conditions may also match
subdomains, so the Chromium adaptation is not an exact replacement for
Firefox's every-request decision engine.

**Protection-state error handling (source-only):** The Chromium adapter
requires static ruleset control for acknowledged updates; it snapshots
previous dynamic and static state and attempts rollback on failure.
`setGlobal` now awaits that result and restores the previous preference on
an unsuccessful change instead of persisting a misleading state. The popup
displays Chromium rule and tab-pause errors, and rejects failed user actions
instead of silently proceeding. Session-rule error status retains the last
observed installed count. JavaScript and Python regression/source fixtures
were updated, but **they have not been executed**.

**Still not complete:** Native Chromium equivalents for Firefox-only
blocking responses, response-body rewriting, DNS/proxy controls, temporary
per-request approvals and other unsupported privileged features require
additional source work. Tab-only pauses and all original UI behavior also
need runtime verification. No browser binary was compiled or tested.

## Chromium control reliability pass (November 16, 2026)

The Chromium-specific runtime message bridge now treats a synchronous
`undefined` listener result as **unhandled**, rather than sending an empty
response that could mask another listener. Listener removal and inspection
retain their original handler identities; asynchronous replies still use the
Chromium response callback.

Core rule-editing interfaces now wait for the DNR adapter result before they
claim success and persist a choice. This includes the global switch, site
allowlisting, user-selected request blocks, remembered request exceptions,
built-in subscription toggles and the general Settings form. If DNR rejects
an edit, the handler restores its prior in-memory configuration and attempts
to restore the network rules. Storage-save failures also trigger restoration.
The service worker waits for its initial DNR refresh before marking its
startup path ready.

Unsupported Chromium request types are explicitly refused for user-selected
blocks and remembered exceptions. The Network Monitor now translates
supported session-wide and ten-minute tab-restricted request allowances
into Chromium session DNR rules, while refusing types DNR cannot represent.
Session state is restored after worker suspension; temporary permissions
expire via alarms and are cleared on navigation or tab closure. The
separate **Pause this tab** command retains its own higher-priority
document-wide session rule. These are source changes, not validated behavior.

Regression source cases were added for the message bridge, with source
assertions for the relevant rule-control paths. **None were executed in this
source-only pass.** A compiled browser, live runtime checks and end-to-end
behavior remain outstanding.
