# Runtime fonts

Glyph subsets read by the stdlib-only live-card generator (`python -m scripts.generate`)
and embedded as base64 `@font-face` data in every live SVG. They are rebuilt by
`python -m scripts.build` from the strings in `scripts/shrine/labels.py`, the phishEye
plaque and printable ASCII; do not edit them by hand.

| File | Font | Weight | CSS family | Licence |
|---|---|---|---|---|
| `runtime-serif-400.woff2` | Noto Serif JP (subset) | Regular | `Shrine Serif` | SIL OFL 1.1, Copyright 2017-2024 Adobe |
| `runtime-serif-700.woff2` | Noto Serif JP (subset) | Bold | `Shrine Serif` | SIL OFL 1.1, Copyright 2017-2024 Adobe |
| `runtime-mono-400.woff2` | JetBrains Mono (subset) | Regular | `Shrine Mono` | SIL OFL 1.1, Copyright 2020 The JetBrains Mono Project Authors |
| `runtime-mono-700.woff2` | JetBrains Mono (subset) | Bold | `Shrine Mono` | SIL OFL 1.1, Copyright 2020 The JetBrains Mono Project Authors |

The full licence text is in [`OFL.txt`](OFL.txt). The static cards in `assets/` embed
per-card subsets of the same two fonts under the same licence.

## Sources (dev only)

The build and the font tests read the full TTFs from two directories:

- `SHRINE_SERIF_DIR` (default `~/.cache/shrine-fonts/serif`): `NotoSerifJP-Regular.ttf`
  and `NotoSerifJP-Bold.ttf`, the static instances from the Google Fonts download of
  Noto Serif JP (https://fonts.google.com/noto/specimen/Noto+Serif+JP, `static/`).
- `SHRINE_MONO_DIR` (default `~/.cache/shrine-fonts`): `JetBrainsMono-Regular.ttf` and
  `JetBrainsMono-Bold.ttf` from the JetBrains Mono release zip
  (https://github.com/JetBrains/JetBrainsMono/releases), `fonts/ttf/`.

Without them `python -m scripts.build` stops with an error and the font-dependent tests
skip. CI never needs them: it only reads the prebuilt woff2 files here.
