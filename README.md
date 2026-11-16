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
