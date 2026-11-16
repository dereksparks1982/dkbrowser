# DK Browser engineering plan

DK Browser is a full Chromium source fork developed as its own general-purpose, open-source browser under DK Softworks.

## Implemented in the source fork

- DK Browser product name in the Chromium branding configuration.
- DK Browser English product title, desktop welcome text and selected browser window titles.
- DK Media Player becomes the fresh-session landing page when a default startup tab would normally open. Session restoration, explicit startup URLs and browser preferences are respected.
- The Home command now opens DK Media Player when the browser's homepage is still set to the default new-tab page, without replacing a custom homepage.
- DK Media Player's web app implements File System Access handle persistence via IndexedDB and mouse-wheel volume control. File restore is automatic when read permission persists; otherwise the player offers a button for interactive reauthorization. Changes live in the separate `DK-Media-Player` repository.
- DK Browser Linux GN args to select Chromium's existing licensed/proprietary-media build pathways for codec investigation. These flags **do not add an FFmpeg HEVC software decoder** by themselves.
- DK Softworks artwork uses a copy of the previously approved DK identity. The Chromium AUTHORS, LICENSE and upstream legal notice remain intact.
- Widevine key-system support is enabled by the DK Browser Linux GN configuration. On Linux, `DK_BROWSER_WIDEVINE_DIR` selects a previously installed CDM directory with `manifest.json` and `_platform_specific/linux_x64/libwidevinecdm.so` (or the corresponding CPU architecture). The code validates the manifest using Chromium's own CDM parser and falls back to Chromium's existing component/bundled discovery when no valid selection is provided.
- Unit-test fixtures cover the local Widevine directory registration and rejection of a relative directory. These tests are committed but have not run on a compiled Chromium checkout.

## Russian-first AI assistant roadmap

**Status: research and planning only.** No model weights, inference engine, toolbar AI button, or remote AI service are integrated or tested yet. The target is an Alice AI-class assistant for Russian and English users, **not** a claim of performance parity.

### Candidate open-weight models (research snapshot: November 2026)

| Role | Candidate | Why / constraints |
| --- | --- | --- |
| **Primary local Russian model** | [Sber GigaChat 3.1 Lightning, 10B total / 1.8B active](https://huggingface.co/ai-sage/GigaChat3.1-10B-A1.8B), [GGUF](https://huggingface.co/ai-sage/GigaChat3.1-10B-A1.8B-GGUF) | Russian/English, instruction-tuned, tool-use capable, MIT license indicated by publisher. Good first candidate for an optional local model with quantization and a local inference backend such as llama.cpp. Measure RAM, CPU/GPU speed and accuracy on actual Linux hardware; no assumption that every computer can run it. |
| **Stronger optionally self-hosted model** | [Sber GigaChat 3.5 Ultra, 432B total / 28B active](https://huggingface.co/ai-sage/GigaChat3.5-432B-A28B), [GGUF](https://huggingface.co/ai-sage/GigaChat3.5-432B-A28B-GGUF) | Strong published Russian/English assistant, agentic and reasoning capabilities; model card lists MIT license. Its published FP8 weights are roughly **438 GB**, requiring substantial inference hardware. **Do not bundle this model into the browser** or pretend it runs on ordinary desktops. Optional user-selected self-hosted endpoint only. |
| **Secondary local-size candidate** | [Sber GigaChat 20B-A3B Instruct](https://huggingface.co/ai-sage/GigaChat-20B-A3B-instruct) | Russian/English instruction model, MIT license shown in model metadata; compare against the 10B alternative before selecting a default. |
| **Russian research comparison only** | [Yandex AliceAI Foundation 80B-A3B Base](https://ir.yandex/press-releases?id=2026-09-21&year=2026) | Yandex released an Apache-2.0 pretrained **base** model in September 2026. It is **not** the finished Alice AI chat/agent product and must not be passed off as such. Consider for independent Russian benchmarks or future fine-tuning, subject to review of the published weights and terms. |

Models are candidates, not embedded distributions. Check upstream license files and dependency licenses before distribution. The small and large models have very different hardware requirements. Independent testing against **Alice AI**, not just older YandexGPT or a publisher's own benchmark, is mandatory before promising equal quality.

### Product behavior and implementation phases

1. **Native AI interface**: an obvious AI button and Russian/English sidebar; explain chat data handling, allow disabling the feature, support keyboard use, dark/light modes and complete translated labels. Keep the existing browser functional without AI.
2. **Local-first inference**: introduce an interchangeable OpenAI-compatible local HTTP inference adapter (e.g., llama.cpp) with optional downloaded model, explicit resource limits and **no forced login, cloud connection or background model download**. A user can choose their own locally installed model.
3. **Optional server AI**: support user-selected, authenticated/self-hosted remote inference endpoints for larger models with clear consent before text from pages, documents or audio leaves the machine. Never hard-code a developer's account or API keys. Do not promise permanently free hosted inference without an operator and funding.
4. **Russian-first abilities**: ask questions about the active page (only on user action), Russian/English summaries, search-grounded answers with citations, multi-tab summaries, translation of text/PDF/images, voice dictation and text-to-speech. Video transcription, translated subtitles and dubbing are **separate speech/video engineering projects**, not abilities provided by a text LLM alone.
5. **Advanced Alice-style assistant**: optional tool use, form filling, multi-step browsing and other agents; use permission scoping, domain boundaries, sensitive-data redaction, safe confirmations for consequential actions and visible activity logs. Follow the user approval model when taking actions.
6. **Evaluation gate**: compare Russian and English factual accuracy, ruMMLU/MERA-style tasks, Russian writing and morphology, hallucinations, coding, tool-use, latency, RAM/VRAM, offline usability and privacy with reproducible tests. Include native-Russian testers and real Russian-site compatibility. Change candidates based on evidence.
7. **Government suitability research**: aim for independent security audits, Russian-localized user support, transparent code provenance and a deployment/data-handling option that can comply with applicable Russian requirements. **An endorsement, approval or entry in the Russian Software Register is not obtained or guaranteed by being Russian-language**. Registry eligibility includes rightsholder/control requirements; an independently owned foreign project may not qualify. Seek qualified local legal advice before any application or claim.

### Useful references

- [Alice AI](https://ir.yandex/press-releases?id=2025-10-28-01&year=2025) and its [new Do it! agent (13 Nov 2026)](https://ir.yandex/press-releases?id=2026-11-13&year=2026) illustrate the product capabilities being targeted; model parity cannot be inferred from feature lists.
- [Sber's GigaChat 3.5 model card](https://huggingface.co/ai-sage/GigaChat3.5-432B-A28B), [GigaChat 3.1 Lightning](https://huggingface.co/ai-sage/GigaChat3.1-10B-A1.8B), [Yandex's released foundation model](https://ir.yandex/press-releases?id=2026-09-21&year=2026).
- [Russian software registry law, Article 12.1 of Law 149-FZ](https://www.consultant.ru/document/cons_doc_LAW_61798/2fe6eb6774cbaae1a62e4c317f27a1350b504280/) for assessing any future registration strategy.

## English/Russian branding and language switch

- A native Chromium Views toolbar **EN / РУ** button switches `intl.app_locale` between English and Russian and requests a session-preserving browser restart. The UI text comes from Chromium's existing language resources; DK-specific Russian product labels are updated to ДК Браузер.
- Corrected the approved English and Russian icons in `assets/images`. Their filenames had been assigned to the wrong original source artwork. Both original Git blobs are retained unmodified, and two Linux theme resources point to the correct variants.
- Normal browser windows select an icon according to the current interface locale. Web-app windows keep the relevant site's icon. The default OS launcher icon requires a pre-packaging generation step, `python3 dk_browser/tools/prepare_icons.py`; a locale-switching OS desktop launcher remains a future task.
- Both GitHub README front pages feature their appropriate icon, with English/Russian navigation. Russian product translation strings are improved but still require native-language review.
- **Not compiled or run yet**: check toolbar layout, restart behavior, Russian translations, Chromium app packaging and correct icons on a real Ubuntu machine.

## Outstanding before a usable DK Browser release

1. **Compile** on Linux using a synchronized upstream DEPS checkout and check build errors. Widevine is currently source-integrated, not proven working at runtime. A compatible CDM must already be present on the machine or supplied through a supported component flow. Some streaming services additionally enforce client authorization.
2. **Validate native MKV** playback and H.265 decoding on target Linux hardware. Chromium's HEVC parser/build flags alone are not a guarantee of a working video decoder. Implement a real FFmpeg/libavcodec decode path or suitable supported platform decoder and test codec support before claiming this works. Check legal redistribution requirements.
3. **Verify file restoration** in a built DK Browser against real disk files across refresh, browser restart and permission prompts. The web player implementation is committed but not yet browser-tested.
4. **Verify mouse-wheel volume** in regular and fullscreen player mode. The 5% wheel adjustment and overlay are committed to the web player.
5. **Complete branding** across browser surfaces, Linux desktop launcher and package naming. Bilingual icons, Russian product strings and the native language selector are source-integrated but untested. Preserve original Chromium credits.
6. **Test** cold startup, session restoration, local video reopen, fullscreen, subtitles, audio/video sync, MKV, H.264, H.265, hardware/software playback and browser upgrades.

## Defaults and user choice

- DK Media Player landing page: https://dereksparks1982.github.io/DK-Media-Player/
- Browser startup URL settings and restore-last-session remain user-controlled.
- No mandatory server, account, Electron wrapper, or additional media desktop application.
- Keep DK Browser source in this fork; DK Media Player remains its own website and codebase.

## Build configuration

The `dk_browser/args.linux.gn` file supplies a starting point for a Linux development build with Chromium's supported media configuration. Actual codec availability depends on built FFmpeg and Linux hardware/platform decoder support. Check the resulting `media_buildflags.h` and inspect runtime decoding using `chrome://media-internals`.

No Chromium executable was compiled by these source commits; this is repository-source development. There is no released DK Browser binary or claimed DRM/codec compatibility matrix.
