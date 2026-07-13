#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASSET_DIR="$ROOT_DIR/docs/assets"
SOURCE_DIR="$ASSET_DIR/source"
VERSION="$(perl -ne "if (/version:\s*'([^']+)'/) { print \$1; exit }" "$ROOT_DIR/meson.build")"

mkdir -p "$SOURCE_DIR"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command magick
require_command inkscape

inkscape "$ROOT_DIR/data/icons/io.github.n1ghthill.soundsgood.svg" \
  --export-type=png \
  --export-filename="$SOURCE_DIR/icon-256.png" \
  --export-width=256 \
  --export-height=256 \
  >/dev/null 2>&1

cat > "$SOURCE_DIR/soundsgood-hero.svg" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1600" height="900" viewBox="0 0 1600 900">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#f7f9fb"/>
      <stop offset="0.45" stop-color="#eef6f0"/>
      <stop offset="1" stop-color="#f8f0d9"/>
    </linearGradient>
    <linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#3584e4"/>
      <stop offset="0.55" stop-color="#2ec27e"/>
      <stop offset="1" stop-color="#e5a50a"/>
    </linearGradient>
    <clipPath id="shotClip"><rect x="0" y="0" width="900" height="486" rx="24"/></clipPath>
    <clipPath id="smallClip"><rect x="0" y="0" width="292" height="158" rx="16"/></clipPath>
  </defs>
  <rect width="1600" height="900" fill="url(#bg)"/>
  <rect x="0" y="0" width="1600" height="14" fill="url(#bar)"/>
  <circle cx="1380" cy="120" r="170" fill="#3584e4" opacity="0.08"/>
  <circle cx="1240" cy="770" r="220" fill="#2ec27e" opacity="0.09"/>
  <circle cx="240" cy="810" r="190" fill="#e5a50a" opacity="0.08"/>

  <g transform="translate(110 118)">
    <image href="icon-256.png" x="0" y="0" width="116" height="116"/>
    <text x="0" y="190" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="86" font-weight="700" fill="#202124">SoundsGood</text>
    <text x="4" y="252" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="34" font-weight="500" fill="#3b4144">Local-first music player for GNOME</text>
    <text x="4" y="326" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="25" fill="#596064">Albums • Artists • Songs • Search</text>
    <text x="4" y="372" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="25" fill="#596064">GStreamer playback • MPRIS controls • Flatpak</text>
    <rect x="4" y="430" width="428" height="62" rx="31" fill="#241f31"/>
    <text x="38" y="471" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="24" font-weight="700" fill="#ffffff">Built for local music libraries</text>
  </g>

  <g transform="translate(720 150)">
    <rect width="820" height="443" rx="24" fill="#ffffff"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/albums.png" width="820" height="443" preserveAspectRatio="xMidYMid slice"/>
  </g>
  <g transform="translate(740 668)">
    <rect width="255" height="138" rx="16" fill="#ffffff"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/artists.png" width="255" height="138" preserveAspectRatio="xMidYMid slice"/>
  </g>
  <g transform="translate(1022 668)">
    <rect width="255" height="138" rx="16" fill="#ffffff"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/songs.png" width="255" height="138" preserveAspectRatio="xMidYMid slice"/>
  </g>
  <g transform="translate(1304 668)">
    <rect width="255" height="138" rx="16" fill="#ffffff"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/search.png" width="255" height="138" preserveAspectRatio="xMidYMid slice"/>
  </g>
</svg>
SVG

cat > "$SOURCE_DIR/soundsgood-social-card.svg" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#fbfcfd"/>
      <stop offset="0.52" stop-color="#eef7f2"/>
      <stop offset="1" stop-color="#fff5dc"/>
    </linearGradient>
    <clipPath id="shotClip"><rect x="0" y="0" width="660" height="356" rx="22"/></clipPath>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect x="0" y="0" width="1200" height="12" fill="#3584e4"/>
  <rect x="400" y="0" width="400" height="12" fill="#2ec27e"/>
  <rect x="800" y="0" width="400" height="12" fill="#e5a50a"/>
  <circle cx="1060" cy="92" r="132" fill="#3584e4" opacity="0.08"/>
  <circle cx="1028" cy="562" r="190" fill="#2ec27e" opacity="0.08"/>

  <g transform="translate(72 96)">
    <image href="icon-256.png" width="104" height="104"/>
    <text x="0" y="186" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="64" font-weight="700" fill="#202124">SoundsGood</text>
    <text x="2" y="236" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="27" font-weight="500" fill="#3d4446">Local music player for Linux</text>
    <text x="2" y="304" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="22" fill="#5d6468">Albums, artists, songs and search.</text>
    <text x="2" y="340" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="22" fill="#5d6468">GStreamer playback and media keys.</text>
  </g>

  <g transform="translate(610 176)">
    <rect width="532" height="287" rx="22" fill="#ffffff"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/albums.png" width="532" height="287" preserveAspectRatio="xMidYMid slice"/>
  </g>
</svg>
SVG

cat > "$SOURCE_DIR/soundsgood-release-card.svg" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="675" viewBox="0 0 1200 675">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#f6f8fb"/>
      <stop offset="0.58" stop-color="#edf8f1"/>
      <stop offset="1" stop-color="#fff0ca"/>
    </linearGradient>
    <clipPath id="shotClip"><rect x="0" y="0" width="760" height="410" rx="20"/></clipPath>
  </defs>
  <rect width="1200" height="675" fill="url(#bg)"/>
  <circle cx="172" cy="585" r="180" fill="#e5a50a" opacity="0.09"/>
  <circle cx="1100" cy="150" r="210" fill="#3584e4" opacity="0.08"/>
  <g transform="translate(72 70)">
    <image href="icon-256.png" width="86" height="86"/>
    <text x="0" y="164" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="48" font-weight="700" fill="#202124">SoundsGood</text>
    <text x="0" y="216" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="25" font-weight="500" fill="#3e4547">Release $VERSION</text>
    <rect x="0" y="280" width="370" height="54" rx="27" fill="#3584e4"/>
    <text x="28" y="315" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="21" font-weight="700" fill="#ffffff">Playlist opening</text>
    <rect x="0" y="354" width="370" height="54" rx="27" fill="#2ec27e"/>
    <text x="28" y="389" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="21" font-weight="700" fill="#ffffff">Persistent library cache</text>
    <rect x="0" y="428" width="370" height="54" rx="27" fill="#241f31"/>
    <text x="28" y="463" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="21" font-weight="700" fill="#ffffff">MPRIS media controls</text>
  </g>
  <g transform="translate(530 132)">
    <rect width="600" height="324" rx="20" fill="#ffffff"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/search.png" width="600" height="324" preserveAspectRatio="xMidYMid slice"/>
  </g>
</svg>
SVG

cat > "$SOURCE_DIR/soundsgood-feature-montage.svg" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1600" height="900" viewBox="0 0 1600 900">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#f8fafc"/>
      <stop offset="0.5" stop-color="#f0f8f3"/>
      <stop offset="1" stop-color="#fff4d7"/>
    </linearGradient>
    <clipPath id="clip"><rect x="0" y="0" width="640" height="300" rx="18"/></clipPath>
  </defs>
  <rect width="1600" height="900" fill="url(#bg)"/>
  <text x="98" y="94" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="52" font-weight="700" fill="#202124">SoundsGood library views</text>
  <text x="100" y="140" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="25" fill="#5d6468">Albums, artists, songs and search built around local music.</text>

  <text x="100" y="170" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="30" font-weight="700" fill="#202124">Albums</text>
  <g transform="translate(100 190)">
    <rect width="640" height="300" rx="18" fill="#ffffff"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/albums.png" width="640" height="300" preserveAspectRatio="xMidYMid slice"/>
  </g>

  <text x="860" y="170" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="30" font-weight="700" fill="#202124">Artists</text>
  <g transform="translate(860 190)">
    <rect width="640" height="300" rx="18" fill="#ffffff"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/artists.png" width="640" height="300" preserveAspectRatio="xMidYMid slice"/>
  </g>
  <text x="100" y="560" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="30" font-weight="700" fill="#202124">Songs</text>
  <g transform="translate(100 585)">
    <rect width="640" height="300" rx="18" fill="#ffffff"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/songs.png" width="640" height="300" preserveAspectRatio="xMidYMid slice"/>
  </g>

  <text x="860" y="560" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="30" font-weight="700" fill="#202124">Search</text>
  <g transform="translate(860 585)">
    <rect width="640" height="300" rx="18" fill="#ffffff"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/search.png" width="640" height="300" preserveAspectRatio="xMidYMid slice"/>
  </g>
</svg>
SVG

inkscape "$SOURCE_DIR/soundsgood-hero.svg" --export-type=png --export-filename="$ASSET_DIR/soundsgood-hero.png" >/dev/null
if [ -f "$SOURCE_DIR/social-preview-custom.png" ]; then
  magick "$SOURCE_DIR/social-preview-custom.png" \
    -resize 1200x630^ \
    -gravity center \
    -extent 1200x630 \
    "$ASSET_DIR/soundsgood-social-card.png"
else
  inkscape "$SOURCE_DIR/soundsgood-social-card.svg" \
    --export-type=png \
    --export-filename="$ASSET_DIR/soundsgood-social-card.png" \
    >/dev/null
fi
inkscape "$SOURCE_DIR/soundsgood-release-card.svg" --export-type=png --export-filename="$ASSET_DIR/soundsgood-release-card.png" >/dev/null
inkscape "$SOURCE_DIR/soundsgood-feature-montage.svg" --export-type=png --export-filename="$ASSET_DIR/soundsgood-feature-montage.png" >/dev/null

magick "$ASSET_DIR/soundsgood-social-card.png" \
  -resize 640x336 \
  "$ASSET_DIR/soundsgood-social-card-small.png"

magick "$ASSET_DIR/soundsgood-hero.png" \
  -resize 800x450 \
  "$ASSET_DIR/soundsgood-hero-small.png"

echo "Generated assets in $ASSET_DIR"
