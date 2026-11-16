# DK Browser engineering plan

DK Browser is a full Chromium source fork developed as its own general-purpose, open-source browser under DK Softworks.

## Implemented in the source fork

- DK Browser product name in the Chromium branding configuration.
- DK Browser English product title, desktop welcome text and selected browser window titles.
- DK Media Player becomes the fresh-session landing page when a default startup tab would normally open. Session restoration, explicit startup URLs and browser preferences are respected.
- The Home command now opens DK Media Player when the browser's homepage is still set to the default new-tab page, without replacing a custom homepage.
- DK Media Player's web app implements File System Access handle persistence via IndexedDB and mouse-wheel volume control. File restore is automatic when read permission persists; otherwise the player offers a button for interactive reauthorization. Firefox remains supported with a session-only file picker. Changes live in the separate `DK-Media-Player` repository.
- DK Browser Linux GN args to select Chromium's existing licensed/proprietary-media build pathways for codec investigation. These flags **do not add an FFmpeg HEVC software decoder** by themselves.
- DK Softworks artwork uses a copy of the previously approved DK identity. The Chromium AUTHORS, LICENSE and upstream legal notice remain intact.
- Widevine key-system support is enabled by the DK Browser Linux GN configuration. On Linux, `DK_BROWSER_WIDEVINE_DIR` selects a previously installed CDM directory with `manifest.json` and `_platform_specific/linux_x64/libwidevinecdm.so` (or the corresponding CPU architecture). The code validates the manifest using Chromium's own CDM parser and falls back to Chromium's existing component/bundled discovery when no valid selection is provided.
- Unit-test fixtures cover the local Widevine directory registration and rejection of a relative directory. These tests are committed but have not run on a compiled Chromium checkout.

## Outstanding before a usable DK Browser release

1. **Compile** on Linux using a synchronized upstream DEPS checkout and check build errors. Widevine is currently source-integrated, not proven working at runtime. A compatible CDM must already be present on the machine or supplied through a supported component flow. Some streaming services additionally enforce client authorization.
2. **Validate native MKV** playback and H.265 decoding on target Linux hardware. Chromium's HEVC parser/build flags alone are not a guarantee of a working video decoder. Implement a real FFmpeg/libavcodec decode path or suitable supported platform decoder and test codec support before claiming this works. Check legal redistribution requirements.
3. **Verify file restoration** in a built DK Browser against real disk files across refresh, browser restart and permission prompts. The web player implementation is committed but not yet browser-tested.
4. **Verify mouse-wheel volume** in regular and fullscreen player mode. The 5% wheel adjustment and overlay are committed to the web player.
5. **Complete branding** across browser surfaces, images, desktop launcher and package naming. Preserve original Chromium credits.
6. **Test** cold startup, session restoration, local video reopen, fullscreen, subtitles, audio/video sync, MKV, H.264, H.265, hardware/software playback and browser upgrades.

## Defaults and user choice

- DK Media Player landing page: https://dereksparks1982.github.io/DK-Media-Player/
- Browser startup URL settings and restore-last-session remain user-controlled.
- No mandatory server, account, Electron wrapper, or additional media desktop application.
- Keep DK Browser source in this fork; DK Media Player remains its own website and codebase.

## Build configuration

The `dk_browser/args.linux.gn` file supplies a starting point for a Linux development build with Chromium's supported media configuration. Actual codec availability depends on built FFmpeg and Linux hardware/platform decoder support. Check the resulting `media_buildflags.h` and inspect runtime decoding using `chrome://media-internals`.

No Chromium executable was compiled by these source commits; this is repository-source development. There is no released DK Browser binary or claimed DRM/codec compatibility matrix.
