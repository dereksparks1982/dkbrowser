# DK Browser

**DK Browser** is DK Softworks' free, open-source web browser built from a complete fork of [Chromium](https://github.com/chromium/chromium).

This repository **contains Chromium's actual browser source code**, not a launcher, an Electron wrapper, or a source submodule. DK-specific changes are committed directly to the fork and maintained here.

## Development status

The first DK Browser source changes introduce DK Softworks branding, updated browser product and window titles, and DK Media Player as the default page when launching a fresh browsing session (while retaining Chromium's session restore and user-selected startup URL behavior).

A separate DK Browser Linux build configuration enables Chromium's available proprietary media/HEVC parser pathways for investigation. DK Browser also enables Widevine key-system registration and can use a previously installed CDM directory on Linux through `DK_BROWSER_WIDEVINE_DIR`. **Actual H.265 decoding depends on decoder support and has not been built or tested yet**. Native MKV/HEVC playback, persistent file access and mouse-wheel media controls remain engineering milestones, not completed features. See [DK_BROWSER.md](DK_BROWSER.md).

## Relationship to DK Media Player

[DK Media Player](https://github.com/dereksparks1982/DK-Media-Player) remains a **web application** and is opened by DK Browser. Browser features will be implemented here; site-specific player functionality remains in its own repository.

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
