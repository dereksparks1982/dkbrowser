# DK NetNav roadmap

**Updated November 17, 2026.** One development branch: `main`. Source changes are not accepted as a working product until the required checks and native browser verification pass. No compiling, runtime testing, or GitHub Actions are authorized at this stage.

## Order and commitments

1. **DK Kinehall player proportions**: source work in `dereksparks1982/dkkinehall`; widen neither the Up Next sidebar nor the queue images; make entries and artwork taller, equalize transport controls and retain the red Play/Pause key. See DK Kinehall's own roadmap. A code change in the separate player is not a compiled DK NetNav release.
2. **DK Live Block becomes the ordinary, built-in, default-on protection in DK NetNav**, not an optional Firefox extension, a second download, or a separate purchase. Consolidate complete compatible source, retain DK licenses/third-party notices and adapt Firefox-only functionality natively where needed.
3. **Nougat Security Analysis becomes DK NetNav's free, browser-integrated antivirus/download protection**, beginning with the actual existing DK Media Plus scanner, not a newly invented or paid engine. Roadmapped below. Native automatic protection is **not yet implemented**.
4. **A native, built-in DK NetNav IDE**, for local coding inside the browser, without an external coding website or standalone installer. Roadmapped below. The IDE is **not yet implemented**.
5. Resume other planned work (media formats, Chromium native playback, AI interface, localization, packaging) in the established `DK_BROWSER.md` engineering plan.

## DK Live Block: Chromium acceptance, not just copied source

**Source present:** `dk_browser/integrations/dk_live_block` contains a Chromium Manifest V3 component, original runtime and licensing, background worker, Chromium compatibility shim, DNR network adapter and bundled GN resources. The native non-Google Linux component loader registers the allowlisted pinned component at startup, and `runtime/background.js` defines `DEFAULT.enabled=true`. Manifest static DNR seed rules are enabled. Source comparison on November 17 confirmed all 58 declared upstream background modules in the correct order and all declared upstream content scripts in Chromium's four script groups.

**Still required before claiming full integration:**
- Verify the complete manifest, file and GN resource inventory as part of local source review. Keep the upstream provenance and Chromium adapters in **this repository**. No runtime fetching of code from the standalone DK Live Block repository.
- Resolve or explicitly replace functionality dependent on Firefox MV2 synchronous `webRequestBlocking`, `filterResponseData`, Firefox DNS/proxy/browser settings and request telemetry. Don't silently call an unsupported control functional.
- Check defaults, enable/disable state, per-site pause and exceptions, manual rules, subscription refreshes, tab-only pauses, popup/UI actions and failure rollback in real Chromium.
- Confirm Facebook ads, YouTube ads and playback, stream compatibility, cookie/popup protection, English/Russian UI and false positives against real sites. Playback must not be broken just to hide an ad.
- Verify MV3 worker suspension/resume, DNR rule quotas, persistent vs session rules, untrusted input handling, installer resource paths and memory/performance on a real non-Google Linux build.
- Retain meaningful checks; fix failures rather than disabling jobs or reporting green without evidence. Standalone DK Live Block's November 17 verification was failing; source integration alone does not correct that failed run. Do not declare the old repository disposable until runtime parity and provenance are confirmed.

## Nougat Security Analysis -> native default-on protection

**Actual donor code:** `dereksparks1982/dkmediaplus`, `components/security/nougat_security_worker.py`, `src/security/scanner_process.cpp/.hpp`, `src/security/security_advisory_service.cpp/.hpp`, plus `docs/security/NOUGAT_SECURITY_ANALYSIS_DEPENDENCIES.md`.

**Existing behavior, NOT a resident antivirus:** The scanner is one-shot and runs only when requested. The documented local engines are YARA-X **1.19.0**, capa **9.4.0** with matching rules and Magika **1.0.3**; optional existing `clamscan` gives a second opinion. Optional free abuse.ch lookups can use MalwareBazaar, ThreatFox and URLhaus with a user-provided free key. The existing system **does not** watch downloads continuously and does **not** quarantine, delete, move or rename files automatically. Therefore the automatic browser protection still needs to be engineered.

**Implementation milestones:**
1. **Port and review:** map original code, dependency licenses, engine runtime/updates, rule provenance and Linux process-management interfaces; preserve source attribution and all threat/verdict semantics. Remove stale Nougat paths from new *browser-facing* labels, not upstream credits.
2. **Native download gate:** hook Chromium's download lifecycle in DK NetNav. Newly downloaded files, archives and risky executable/script types should be examined automatically *before Open/Run is offered*, using a restricted local security worker. The browser should visibly say *scanning*, *threat detected*, *suspicious*, *analysis incomplete*, or *no threats detected* as appropriate. Never label an incomplete scan *safe*.
3. **Safe isolation:** bounded worker subprocess, read-only file access, time/file-size limits, cancellation, protected temporary files, resource limits and fail-closed reporting when scanners are missing. Never execute the examined file while scanning. Do not stall the UI.
4. **Browser threat signals:** integrate known malicious URLs, downloads, extensions and phishing/malvertising checks with DK Live Block and native navigation/download safeguards; deduplicate alerts, avoid contradictory verdicts, and keep origin boundaries. Do not claim these rules replace all antivirus functions.
5. **Free updates and offline behavior:** locally bundled baseline definitions; optional verified free engine/rule updates; handle expired/missing definitions visibly. No paid license, subscription, forced login, commercial API dependency, automatic media/file uploads or background surveillance.
6. **User control:** enforce the existing **WARN ME FIRST** rule. Do **not** auto-quarantine, delete, rename or move files. Prompt before any destructive or execution-related action; allow explicit review and dismissal where safely appropriate. Offer manual file/folder scans as a separate user-initiated action.
7. **Acceptance:** regression tests for infected/clean/unknown fixtures, mock scan failures/timeouts, false positives, archive handling, malicious file names/paths, cancellations, downloads and real-browser startup/performance. Do not advertise automatic AV as present until these checks actually pass.

## Built-in native IDE inside DK NetNav

**Product requirement:** Open a local, browser-owned coding workspace in a native Chromium tab/window (for example a dedicated internal WebUI route backed by native browser code). It must be part of DK NetNav, not a remote IDE service, unrelated app, Electron wrapper or downloaded extension. **Status: roadmap only.**

**Milestones:**
1. **Native shell:** add a DK-owned, localized browser menu/toolbar entry and internal IDE route with a native Chromium backend, safe security origin, embedded editor assets and no outside network requirement.
2. **Editor and projects:** syntax-highlighting source editor (review CodeMirror/Monaco licenses and bundled footprint), tabbed files, file tree, open/save with user-approved local directories, autosave/recovery, undo/redo, find/replace and language modes. Keep source code on the device.
3. **Engineering features:** local search, diff and Git status/commit UI, diagnostics, optional local language servers/formatters, build/output console, terminal and project tasks. No commands, scripts or builds run without an explicit user action.
4. **Safe run and preview:** isolated, user-triggered execution and preview for supported local project types. Sandboxed workspace permissions, safe localhost origin boundaries and no arbitrary web-page access to the host filesystem or terminal.
5. **Polish and release gate:** English/Russian UI, keyboard navigation, project recovery, responsive layout, failure handling, accessibility, dependency licensing, Linux performance and native Chromium integration tests.

## Non-negotiable development rules

- Preserve DK NetNav Chromium-only direction, one `main` branch, original DK ownership/license boundaries and upstream third-party notices.
- Free features by default. No paid antivirus or paid editor subscription.
- Update documentation alongside source changes. Don't claim runtime success from code presence.
- Do not compile or run tests while that project hold remains in force; once testing resumes, failed required checks mean failed builds and must be fixed, not hidden.
