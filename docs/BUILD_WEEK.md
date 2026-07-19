# OpenAI Build Week 2026

SoundsGood is entered in the **Apps for your life** track. It is a local-first
music player that turns an existing Linux music folder into a responsive,
searchable library without accounts, uploads, or streaming services.

Release evaluated for the submission: [v0.2.2](https://github.com/N1ghthill/soundsgood/releases/tag/v0.2.2),
from commit `e62551bd21fc8f2a0ae0ba474a63d80dfc817c87`. Its public GNOME 50
[CI run](https://github.com/N1ghthill/soundsgood/actions/runs/29677482974)
passed alongside 61 automated tests, a graphical smoke test on the real
display, AppStream checks, and a clean Flatpak build on July 19, 2026.

## Codex session

- Core implementation session: `019f7856-0676-79b0-838c-97e81573eb0f`
- Submission source: obtain and verify the value shown by `/feedback` in the
  Codex session before copying it into Devpost.
- Model verification: the local Codex session metadata records
  `gpt-5.6-sol` for this thread. The `/feedback` dialog must still be submitted
  interactively so the shareable session ID can be confirmed before submission.

The session ID is recorded for traceability. The value entered in Devpost must
be the `/feedback` value from the session containing the majority of the final
core implementation.

The repository records a candidate implementation-session identifier, not a
claim that the interactive `/feedback` requirement has been completed. That
item remains open in `docs/SUBMISSION.md` until the owner verifies it.

## How Codex accelerated the project

Codex was used to:

- audit the GTK/GObject lifecycle and connect intermittent failures to
  synchronous filesystem work, unbounded widget creation, signal retention,
  artwork decoding, and incomplete GStreamer shutdown;
- design and implement bounded diagnostics and explicit resource teardown;
- move library validation and scanning away from the GTK main thread;
- make scans recoverable, coalesce concurrent requests, isolate malformed
  files, and write the library cache atomically;
- introduce factory-backed, virtualized song rendering;
- redesign navigation and playback controls around adaptive libadwaita
  patterns;
- separate background lifetime from window lifetime and add optional,
  cross-desktop StatusNotifier integration;
- virtualize album and artist detail collections and remove duplicate playback
  activation paths;
- add lifecycle, failure, cache, GTK smoke, and responsive-width tests;
- prepare reproducible demo data and submission documentation.

## Human decisions

The project owner made the decisions that define the product:

- retain Python, GTK4/libadwaita, GStreamer, and the GNOME desktop experience;
- remain local-first and exclude streaming, accounts, radio, and podcasts;
- distribute independently rather than rewrite the application only to target
  another package registry;
- reject point fixes and require architectural improvements for stability and
  UI quality;
- prioritize a coherent everyday music experience over feature count.

## Key technical decisions

1. Heavy filesystem/cache validation runs outside the GTK main thread.
2. Worker failures are converted into observable library states on the main
   loop; individual unreadable files are skipped with diagnostics.
3. Cache replacement is atomic, preserving the last complete index.
4. Unbounded collections use `Gio.ListModel` and factory-backed GTK views.
5. Signal and GLib/GStreamer resources have explicit teardown ownership.
6. Artwork is normalized into bounded thumbnails before being shown by views.
7. Narrow layouts are a first-class design target, not a CSS afterthought.
8. Playback uses a compact, adaptive three-zone bar: track context, centered
   transport controls, and secondary actions, with a dedicated seek line.
9. Closing the window can preserve playback without weakening explicit
   shutdown; tray integration remains optional and MPRIS stays authoritative.

## Current product boundary

The v0.2.2 release keeps the temporary playback queue separate from
named persistent playlists. It can open `.m3u`, `.m3u8`, and `.pls` files into
the queue or import them as saved collections, export playlists as M3U8, and
add songs or albums through native contextual playlist submenus.

## Official submission requirements

The challenge requires a working project, category, project description,
public demo video under three minutes, accessible code repository, README with
setup/test instructions, an explanation of Codex/GPT-5.6 usage, and the
qualifying `/feedback` session ID. The operational checklist and video outline
are in `docs/SUBMISSION.md`.

Official references checked on July 19, 2026:

- [OpenAI Build Week official rules](https://openai.devpost.com/rules)
- [OpenAI Build Week FAQ](https://openai.devpost.com/details/faqs)
- [Submission schedule](https://openai.devpost.com/details/dates)
