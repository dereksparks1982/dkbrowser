# DK NetNav approved icons

The two current master image files are:

- **English:** `Glossy Russian-Inspired Digital Emblem.png` (DK NetNav)
- **Русский:** `ДК НетНав_ Золотой цифровой собор.png` (ДК НетНав)

Both are Russian-inspired, flag-free emblems with transparent backgrounds.
The English and Russian images remain separate, and filenames must be
preserved exactly, including spaces and Cyrillic characters.

Chromium's native language-dependent icons are kept at
`chrome/app/theme/default_100_percent/chromium/dk_netnav_icon_en.png`
and `chrome/app/theme/default_100_percent/chromium/dk_netnav_icon_ru.png`.
Those native files must contain the **same bytes** as the corresponding
master images.

`python3 dk_browser/tools/prepare_icons.py` prepares resized launcher
icons for Linux packaging from these masters. It does not compile Chromium.
The generated launcher sizes have not been regenerated or tested as part
of this source-only update.

Previous masters were removed from this directory. Their earlier
versions can still be found in the repository's Git history.
