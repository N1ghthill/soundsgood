# SoundsGood contributor guidance

SoundsGood is a local-first GNOME music player. Preserve GTK4/libadwaita,
GStreamer, Meson, and the separation between library, playback, platform
integration, and UI.

## Product boundaries

- Do not add streaming, radio, podcasts, accounts, or mandatory remote services.
- Keep file scanning and metadata work outside widgets and the GTK main thread.
- UI collections must use `Gio.ListModel` and GTK list/grid factories when they
  can contain an unbounded number of items.
- Every GLib source, GObject signal, monitor, GStreamer watch, and D-Bus
  registration must have an explicit lifecycle owner and teardown path.
- A malformed media file must be reported and skipped, never terminate a scan.
- Prefer adaptive libadwaita layout primitives over fixed size requests.
- Reuse the semantic classes in `soundsgood/style.css`; icon actions must stay
  vertically centered and must not inherit the height of adjacent artwork.

The detailed architecture and metadata rules remain in `agent.md` and
`docs/ARCHITECTURE.md`.

## Required validation

```bash
python3 -m py_compile soundsgood/*.py soundsgood/catalog/*.py soundsgood/views/*.py soundsgood/widgets/*.py tests/*.py
python3 -m unittest discover -s tests
meson setup builddir --reconfigure
meson compile -C builddir
meson test -C builddir --print-errorlogs
```

For UI work, also run the graphical smoke tests under a display and the manual
matrix in `docs/MANUAL_TESTS.md`.

## OpenAI Build Week

This repository participates in OpenAI Build Week 2026. Material changes must
keep `docs/BUILD_WEEK.md` and `docs/SUBMISSION.md` accurate. Do not claim a
model version, successful test, or demo capability that was not verified.
