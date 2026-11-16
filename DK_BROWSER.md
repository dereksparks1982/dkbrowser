# DK Browser engineering plan

DK Browser is a full Chromium source fork developed as its own general-purpose, open-source browser under DK Softworks.

## Implemented in the source fork

- DK Browser product name in the Chromium branding configuration.
- DK Browser English product title, desktop welcome text and selected browser window titles.
- DK Media Player becomes the fresh-session landing page when a default startup tab would normally open. Session restoration, explicit startup URLs and browser preferences are respected.
- DK Browser Linux GN args to select Chromium's existing licensed/proprietary-media build pathways for codec investigation. These flags **do not add an FFmpeg HEVC software decoder** by themselves.
- DK Softworks artwork uses a copy of the previously approved DK identity. The Chromium AUTHORS, LICENSE and upstream legal notice remain intact.

## Outstanding before a usable DK Browser release

1. **Compile** on Linux using a synchronized upstream DEPS checkout and check build errors.
2. **Validate native MKV** playback and H.265 decoding on target Linux hardware. Chromium's HEVC parser/build flags alone are not a guarantee of a working video decoder. Implement a real FFmpeg/libavcodec decode path or suitable supported platform decoder and test codec support before claiming this works. Check legal redistribution requirements.
3. **Persistent media-file access**: The DK Media Player web app can use Chromium's File System Access API and persist file handles through IndexedDB. Files must be previously selected by the user; reauthorization may require a click. Browser-only policies must not silently bypass access permissions.
4. **Media wheel controls**: Over the active player, scroll up increases volume, scroll down lowers it, and an overlay briefly shows the volume percentage. Avoid affecting scrolling elsewhere.
5. **Complete branding** across browser surfaces, images, desktop launcher and package naming. Preserve original Chromium credits.
6. **Test** cold startup, session restoration, local video reopen, fullscreen, subtitles, audio/video sync, MKV, H.264, H.265, hardware/software playback and browser upgrades.

## Defaults and user choice

- DK Media Player landing page: https://dereksparks1982.github.io/DK-Media-Player/
- Browser startup URL settings and restore-last-session remain user-controlled.
- No mandatory server, account, Electron wrapper, or additional media desktop application.
- Keep DK Browser source in this fork; DK Media Player remains its own website and codebase.

## Build configuration

The `dk_browser/args.linux.gn` file supplies a starting point for a Linux development build with Chromium's supported media configuration. Actual codec availability depends on built FFmpeg and Linux hardware/platform decoder support. Check the resulting `media_buildflags.h` and inspect runtime decoding using `chrome://media-internals`.

No build was run by adding these source files, and no binary or supported codec matrix is claimed.
