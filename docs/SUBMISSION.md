# OpenAI Build Week submission kit

## Category

Apps for your life

## Short description

SoundsGood is a private, local-first music player for Linux. It indexes music
already on the computer, reads real metadata and artwork, organizes albums and
artists, provides fast search and playback queues, and integrates with desktop
media controls without requiring an account or uploading a library. Version
0.2.2 can remain active after its window closes, exposes an optional tray menu
on compatible desktops, and manages named persistent playlists through direct
actions and native context menus.

The evaluated v0.2.2 release separates temporary playback queues from named
persistent playlists and supports playlist import and export.

The public 0.2.3 release contains additional playlist-editor hardening
requested after that release. It remains separate from the evaluated v0.2.2
claims recorded for the Build Week submission.

The public 0.2.4 release fixes and visually refines the right-click playlist
destination popover. It does not change the evaluated v0.2.2 submission or its
verified claims.

## Problem and impact

People with personal music collections often have to choose between dated
desktop players and cloud-first services. SoundsGood provides a focused GNOME
experience for listeners who want ownership, privacy, and native desktop
integration. Its architecture is designed to remain responsive with large and
imperfect real-world collections.

## Demo video outline (maximum 2:45)

1. **0:00–0:20 — Problem:** show the local demo library and explain the
   local-first/privacy premise.
2. **0:20–0:55 — Library:** open SoundsGood, show cached startup, albums,
   artists, songs, real tags, and artwork.
3. **0:55–1:25 — Playback:** save an album to a playlist, play it, seek, open
   the queue, and demonstrate MPRIS desktop controls and background playback.
4. **1:25–1:50 — Adaptive design:** resize from 1200 px to 600/360 px and show
   navigation, album detail, artist split view, and compact player behavior.
5. **1:50–2:20 — Reliability:** show reindexing, an unreadable file being
   skipped, diagnostics, and recovery without closing the app.
6. **2:20–2:45 — Codex:** summarize the lifecycle audit, async scan,
   virtualization, key human decisions, tests, and final impact.

The word-for-word narration and recording cues are in `docs/DEMO_SCRIPT.md`.

The video must be public on YouTube, under three minutes, and include spoken
coverage of both Codex and GPT-5.6 usage.

## Judge test path

```bash
scripts/create-demo-library.sh
meson setup builddir
meson compile -C builddir
./builddir/local-soundsgood
```

On first launch, choose the generated `demo-music` directory. No account,
network service, or API key is required.

## Submission checklist

- [ ] Join the challenge and confirm eligibility in Devpost.
- [ ] Confirm the selected track is **Apps for your life**.
- [x] Confirm the project builds from a clean clone.
- [x] Run automated tests, contextual-menu model/action tests,
      AppStream/manifest validation, Flatpak build, public update, and GNOME 50
      CI for v0.2.2. The graphical smoke passed on the real display inside an
      isolated GNOME SDK session.
- [ ] Complete and record the full manual matrix with large real collections
      and 360/600/900/1200 px widths.
- [ ] Record the demo against the final commit.
- [ ] Upload a public YouTube video shorter than three minutes.
- [x] Make the repository public with its GPL-2.0-or-later license, or grant
      `testing@devpost.com` and `build-week-event@openai.com` private access.
- [ ] Run `/feedback` in the qualifying Codex session.
- [x] Confirm GPT-5.6 in the qualifying Build Week environment.
- [ ] Enter the verified session ID in Devpost.
- [x] Review `docs/BUILD_WEEK.md` against the official rules and FAQ.
- [ ] Submit before July 21, 2026 at 5:00 PM PDT.

Verified release references:

- Release: <https://github.com/N1ghthill/soundsgood/releases/tag/v0.2.2>
- CI: <https://github.com/N1ghthill/soundsgood/actions/runs/29677482974>
- Flatpak repository deployment: <https://github.com/N1ghthill/soundsgood/actions/runs/29677567194>
- Flatpak app ID: `io.github.n1ghthill.soundsgood`
