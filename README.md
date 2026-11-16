<div align="center">

<img src="assets/images/DK%20Browser%20Imperial%20Icon.png" alt="DK Browser English imperial icon" width="220">

# DK Browser

**English** | **[Русский](README.ru.md)**

**Free, open-source browser for English and Russian users, built from Chromium by DK Softworks.**

</div>

**DK Browser** is DK Softworks' free, open-source web browser built from a complete fork of [Chromium](https://github.com/chromium/chromium).

This repository **contains Chromium's actual browser source code**, not a launcher, an Electron wrapper, or a source submodule. DK-specific changes are committed directly to the fork and maintained here.

## Development status

DK Browser source changes introduce DK Softworks branding, updated browser product and window titles, and DK Media Player as the default page when launching a fresh browsing session (while retaining Chromium's session restore and user-selected startup URL behavior). The browser Home command also opens DK Media Player while preserving a custom homepage.

A separate DK Browser Linux build configuration enables Chromium's available proprietary media/HEVC parser pathways for investigation. DK Browser also enables Widevine key-system registration and can use a previously installed CDM directory on Linux through `DK_BROWSER_WIDEVINE_DIR`. **Actual H.265 decoding depends on decoder support and has not been built or tested yet**. Native MKV/HEVC playback remains an engineering milestone. The DK Media Player web app now implements persistent last-file handles through IndexedDB and mouse-wheel volume control; those source features are not yet verified in a compiled DK Browser. See [DK_BROWSER.md](DK_BROWSER.md).

## English and Russian editions

DK Browser is designed with English and Russian interface support. The browser's native toolbar includes a visible **EN / РУ** button. Switching changes Chromium's application-locale preference and restarts through its normal session-preserving restart mechanism. Existing Russian resources provide native translations, and DK-specific Russian product wording uses **ДК Браузер**.

Both approved imperial icons live under [assets/images](assets/images), with the original filenames corrected to match the actual Latin/Cyrillic lettering. Linux browser windows select the proper icon based on the active language. Desktop launcher icon preparation is documented in [dk_browser/README.md](dk_browser/README.md).

This is a **source implementation**; there is no compiled DK Browser executable yet, and native layout, locale persistence and icon display need runtime testing.

## Relationship to DK Media Player

[DK Media Player](https://github.com/dereksparks1982/DK-Media-Player) remains a **web application** and is opened by DK Browser. Browser features are implemented here; site-specific player functionality remains in its own repository. Its [live web player](https://dereksparks1982.github.io/DK-Media-Player/) supports opening media, resume positions, a saved last-file handle in compatible browsers, and volume adjustment by scrolling over the video.

## Separate Linux user profile

DK Browser uses its own **`~/.config/dk-browser`** profile directory instead of Chromium's `~/.config/chromium`. Bookmarks, history, settings and extensions are therefore kept separate by default. The matching snap configuration path is also DK-specific. Existing Chromium overrides such as `--user-data-dir` and the XDG configuration location still take precedence when explicitly chosen.

## Linux package identity

The Linux packaging source now uses a separate **`dk-browser`** application/package name and `/opt/dksoftworks/dk-browser` installation directory. The desktop entry has a Russian display name (**ДК Браузер**) while retaining an English name for English-language desktops. DK Browser packaging must **not** add Google's software repositories, fetch Google's update signing key or claim Google-hosted updates. No DK update feed exists yet; system package upgrades and signatures need real release infrastructure before distribution.

The normal upstream `chrome` executable remains internal to the package, while `dk-browser` is the launcher and installed icon name. The approved icon source files and preparer are under `assets/images` and `dk_browser/tools`. **Linux packages have not been built or verified yet.**

## Optional local AI prototype

An experimental bilingual **DK AI** interface now lives in [dk_browser/ai](dk_browser/ai). It connects to either a local [Ollama](https://ollama.com) server or a locally installed OpenAI-compatible model server, lists already installed models, and supports an English/Russian text chat without an account or automatic model download. The native toolbar now has a **DK AI** button opening the assistant in a foreground tab at `http://127.0.0.1:8766/`. Start the local assistant service yourself first. The button neither launches a background process nor sends page contents. The assistant is still a separate local development page, **not a built-in Chromium sidebar**.

After starting Ollama and installing your own compatible model, run `python3 -m dk_browser.ai --open` from the repository root. This starts a local-only web page at `http://127.0.0.1:8766`. No third-party Python modules are required to serve it. The assistant displays the approved English or Russian imperial icon for the selected language, remembers only the UI language, offers Ctrl+Enter to send, and exports a text transcript only on request. See [AI instructions](dk_browser/ai/README.md) for security limits, including the fact that a local service is accessible to other programs running as your user.

## Source quality checks (no GitHub Actions)

Run `python3 dk_browser/tools/preflight.py` in a full checkout for local checks of the approved icons, Russian README text, Linux profile and package identity, AI request boundaries, Python unit tests and (when Node is installed) JavaScript syntax. Use `--no-tests` for fast, offline source-only checks. This does **not compile Chromium, install packages, start model services or run a cloud workflow**.

## Build groundwork

Chromium uses `depot_tools`, `gclient`, `gn` and `autoninja`. Forking the source provides Chromium's main tree, but a local checkout must also synchronize dependencies from `DEPS` before compiling. Do not treat GitHub's ZIP download as a complete build environment.

DK Browser's Linux GN configuration lives at [dk_browser/args.linux.gn](dk_browser/args.linux.gn); import these arguments into your chosen GN output directory when a build environment is ready.

For upstream build prerequisites and commands, follow [Chromium's Linux build instructions](docs/linux/build_instructions.md).

## Source licensing and attribution

Chromium is open source under a [BSD-style license](LICENSE) and numerous [third-party licenses](third_party). DK Browser retains these licenses and Chromium author attribution. DK Softworks is responsible for DK Browser-specific modifications. Some media codecs may involve additional patent or redistribution obligations and require separate review before distributing builds.

This is a development source fork; **there is no DK Browser executable released yet**.

### Widevine on Linux

The build configuration sets `enable_widevine = true`. If a Widevine CDM is already installed, point `DK_BROWSER_WIDEVINE_DIR` to the *directory containing* its `manifest.json`, not directly to the `.so` library. DK Browser then checks the manifest and platform library using Chromium's own CDM registration pathway. If that directory is invalid or not set, Chromium's existing component discovery remains in place.

This does **not** install Google's CDM, defeat DRM, certify DK Browser for streaming services, or guarantee that a site will accept it. Actual playback requires a compatible local CDM and runtime testing. See [DK_BROWSER.md](DK_BROWSER.md) for implementation status.

**No custom GitHub Actions or automatic builds are added to this project.**
