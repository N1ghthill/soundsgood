# Build Week demo script

Target length: 2:30–2:40. Record at 1080p with the application text readable,
the pointer visible, and no personal paths or notifications on screen.

## 0:00–0:18 — The problem

**Screen:** Show the generated demo library folder, then launch SoundsGood.

**Narration:**

> Personal music collections deserve a modern player without an account,
> upload, or streaming subscription. SoundsGood is a native GNOME application
> that turns music already on a Linux computer into a private, searchable
> library.

## 0:18–0:53 — Library and search

**Screen:** Move through Albums, Artists, and Songs. Search for one generated
track and open an album.

**Narration:**

> SoundsGood reads local metadata and artwork, organizes albums and artists,
> and provides accent-insensitive ranked search. The library index is cached
> locally, so unchanged collections reopen quickly. Scanning and metadata work
> happen outside the GTK interface thread, keeping navigation responsive even
> when the collection is being updated.

## 0:53–1:25 — Playback

**Screen:** Play an album, seek, open playback options, change repeat mode,
open the queue, remove an item, show the desktop media control, then close and
reopen the window while playback continues.

**Narration:**

> Playback uses GStreamer and integrates with Linux media controls through
> MPRIS. I can seek, change repeat or shuffle behavior, and manage the current
> queue. Closing the window can keep the session playing, while an explicit
> Quit still releases its timers, bus watches, monitors, D-Bus registrations,
> and playback resources. This explicit ownership prevents the intermittent
> exits that motivated the refactor.

## 1:25–1:52 — Adaptive interface

**Screen:** Resize the window from 1200 to 600 and then 360 pixels. Navigate
back from an artist and show the lower page switcher and compact album header.

**Narration:**

> The interface is designed for the whole window range, not patched for one
> screenshot. Libadwaita breakpoints change navigation and composition at
> narrow widths. Large collections and the playback queue use factory-backed
> GTK views, so only visible items create widgets.

## 1:52–2:17 — Reliability

**Screen:** Trigger Rescan Library, then open Preferences and the Diagnostics
section. Briefly show the test workflow or successful CI page.

**Narration:**

> A malformed file is isolated instead of terminating a scan, cache updates
> are atomic, repeated scan requests are consolidated, and bounded local logs
> make failures diagnosable. Automated lifecycle, cache, player, responsive UI,
> AppStream, and complete Flatpak checks run against the GNOME 50 environment.

## 2:17–2:38 — Codex and impact

**Screen:** Show `docs/BUILD_WEEK.md`, the public repository, and the running
application side by side.

**Narration:**

> I used Codex with GPT-5.6 to audit the existing project, identify lifecycle
> and rendering risks, implement the architectural changes, and build the
> regression and release workflow. The product decisions remained human:
> native GNOME technology, local-first privacy, and a focused music experience.
> SoundsGood is now a tested, distributable application rather than a fragile
> prototype.

## Recording checklist

- Generate the library with `scripts/create-demo-library.sh` before recording.
- Use only generated audio and non-personal paths.
- Keep the final video under three minutes.
- Verify spoken references to both Codex and GPT-5.6.
- Do not describe the temporary queue as a saved playlist.
- Export H.264 video with AAC audio and upload it publicly to YouTube.
