# DK Browser customizations

This directory contains DK Browser-specific configuration and development notes within the full Chromium fork.

`args.linux.gn` is a development GN configuration, not proof of codec support. It enables the Chromium paths for H.264/AAC/MKV/HEVC where implemented. The actual FFmpeg decoder selection and Linux platform decoding still require inspection, implementation and playback tests.

Before building, follow Chromium's normal Linux instructions and fetch the dependencies defined by `DEPS`. DK Browser is a source fork, not a browser binary or a web app wrapper.

The parent README and `DK_BROWSER.md` track implemented vs planned features.
