# DK Browser customizations

This directory contains DK Browser-specific configuration and development notes within the full Chromium fork.

`args.linux.gn` is a development GN configuration, not proof of codec support. It enables the Chromium paths for H.264/AAC/MKV/HEVC where implemented. The actual FFmpeg decoder selection and Linux platform decoding still require inspection, implementation and playback tests.

Before building, follow Chromium's normal Linux instructions and fetch the dependencies defined by `DEPS`. DK Browser is a source fork, not a browser binary or a web app wrapper.

The parent README and `DK_BROWSER.md` track implemented vs planned features.

Widevine support is enabled in the GN config. A local CDM may be selected at startup with `DK_BROWSER_WIDEVINE_DIR` pointing to the installation's Widevine directory. This is implemented in `chrome/common/media/cdm_registration.cc` and tested in `cdm_registration_unittest.cc`. This configuration does not ship the CDM binary.

## English and Russian assets

The original approved English/Russian artwork is stored under `assets/images`. Normal Linux browser windows use the icon matching the current UI language. A visible **EN / РУ** toolbar switch persists the preferred language and restarts the browser.

Before packaging a Linux release, regenerate standard icon sizes with Pillow (`python3-pil`):

```bash
python3 dk_browser/tools/prepare_icons.py
```

The script does not compile Chromium or run GitHub Actions. It creates default English launcher icon sizes and separate Russian versions. Changing the installed desktop launcher's icon automatically is not yet implemented.

## Linux data separation

The fork's non-Google Linux profile defaults to `~/.config/dk-browser`. Google-branded source paths remain untouched. The snap helper uses the matching directory basename and `dk-browser-config` plug so an unrelated Chromium profile is not imported automatically.

To check the source invariants without compiling Chromium:
`python3 -m unittest discover -s dk_browser/tests`.

## Linux package identity

Non-Google Linux packages are named `dk-browser`, install under
`/opt/dksoftworks/dk-browser`, and register a `dk-browser` desktop/icon
identity. The internal Chromium executable remains named `chrome`.
`Name[ru]=ДК Браузер` selects Russian application-menu labeling.

No DK repository or signing infrastructure has been deployed. The DK .deb
and .rpm maintenance scripts must not register Google's apt/yum repositories
or signing keys. Packaging still requires building Chromium, preparing
native icon sizes with `dk_browser/tools/prepare_icons.py` and testing actual
install/uninstall lifecycle.

## DK AI experimental local service

`python3 -m dk_browser.ai --open` starts a localhost-only text chat UI
that forwards requests to an already-running Ollama local model.
See `dk_browser/ai/README.md` for installation and privacy constraints.
This is a separately launched development tool, not yet a compiled native
browser sidebar or a shipped model.

## No-actions source preflight

Run `python3 dk_browser/tools/preflight.py` after edits and before
accepting a source build. It invokes local Python tests and uses Node to
check JavaScript syntax when installed. It also verifies Russian README
language, approved English/Russian image bytes, safe Linux package identity
and local AI boundaries. Run `--no-tests` for the fast invariants alone.

It neither requires nor starts GitHub Actions, and is **not** a Chromium build.


## Native DK AI entry point

The standard toolbar contains a localized **DK AI / ДК ИИ** button.
It opens the fixed local URL `http://127.0.0.1:8766/` in a new foreground
tab using Chromium's browser-initiated navigation API. The separate Python
service must already be running. No page content is forwarded automatically.
The native integration is source-only until a full Chromium build verifies it.
