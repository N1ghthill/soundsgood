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

if [ -f "$SOURCE_DIR/brand-icon.png" ]; then
  magick "$SOURCE_DIR/brand-icon.png" \
    -resize 256x256 \
    -background none \
    -gravity center \
    -extent 256x256 \
    "$SOURCE_DIR/icon-256.png"
else
  magick "$ROOT_DIR/data/icons/io.github.n1ghthill.soundsgood.png" \
    -resize 256x256 \
    -background none \
    -gravity center \
    -extent 256x256 \
    "$SOURCE_DIR/icon-256.png"
fi

if [ -f "$SOURCE_DIR/brand-logo.png" ]; then
  LOGO_IMAGE="brand-logo.png"
else
  LOGO_IMAGE="icon-256.png"
fi

cat > "$SOURCE_DIR/soundsgood-hero.svg" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1600" height="900" viewBox="0 0 1600 900">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#050812"/>
      <stop offset="0.55" stop-color="#09162d"/>
      <stop offset="1" stop-color="#12061f"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#16d9ff"/>
      <stop offset="1" stop-color="#9b4dff"/>
    </linearGradient>
  </defs>
  <rect width="1600" height="900" fill="url(#bg)"/>
  <circle cx="1360" cy="120" r="260" fill="#2857ff" opacity="0.18"/>
  <circle cx="690" cy="760" r="360" fill="#00b7ff" opacity="0.10"/>
  <circle cx="1180" cy="770" r="300" fill="#8b2cff" opacity="0.16"/>
  <path d="M530 622 C650 560 720 680 820 600 S1000 510 1110 580 S1310 680 1490 540" fill="none" stroke="#16d9ff" stroke-width="6" opacity="0.33"/>
  <path d="M530 650 C650 588 720 708 820 628 S1000 538 1110 608 S1310 708 1490 568" fill="none" stroke="#9b4dff" stroke-width="5" opacity="0.25"/>

  <g transform="translate(76 96)">
    <image href="$LOGO_IMAGE" x="0" y="0" width="570" height="154" preserveAspectRatio="xMinYMid meet"/>
    <rect x="4" y="232" width="70" height="5" rx="2.5" fill="url(#accent)"/>
    <text x="4" y="304" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="36" fill="#f5f7ff">Local-first music player</text>
    <text x="4" y="352" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="36" fill="#f5f7ff">for GNOME desktops.</text>
    <text x="4" y="430" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="24" fill="#a8b5d4">Albums • Artists • Songs • Search</text>
    <text x="4" y="470" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="24" fill="#a8b5d4">GStreamer playback • MPRIS controls • Flatpak</text>
  </g>

  <g transform="translate(800 138)">
    <rect x="-10" y="-10" width="740" height="493" rx="28" fill="#4d7dff" opacity="0.38"/>
    <rect width="720" height="480" rx="22" fill="#111827"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/albums.png" width="720" height="480" preserveAspectRatio="xMidYMid slice"/>
  </g>
  <g transform="translate(820 704)">
    <rect width="228" height="152" rx="14" fill="#111827"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/artists.png" width="228" height="152" preserveAspectRatio="xMidYMid slice"/>
  </g>
  <g transform="translate(1082 704)">
    <rect width="228" height="152" rx="14" fill="#111827"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/songs.png" width="228" height="152" preserveAspectRatio="xMidYMid slice"/>
  </g>
  <g transform="translate(1344 704)">
    <rect width="228" height="152" rx="14" fill="#111827"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/search.png" width="228" height="152" preserveAspectRatio="xMidYMid slice"/>
  </g>
</svg>
SVG

cat > "$SOURCE_DIR/soundsgood-social-card.svg" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#050812"/>
  <image href="$LOGO_IMAGE" x="80" y="90" width="560" height="152" preserveAspectRatio="xMinYMid meet"/>
  <text x="84" y="322" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="34" fill="#f5f7ff">A modern local music player</text>
  <text x="84" y="370" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="34" fill="#f5f7ff">for Linux desktops.</text>
  <rect x="84" y="430" width="70" height="5" rx="2.5" fill="#16d9ff"/>
</svg>
SVG

cat > "$SOURCE_DIR/soundsgood-release-card.svg" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="675" viewBox="0 0 1200 675">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#050812"/>
      <stop offset="0.6" stop-color="#09162d"/>
      <stop offset="1" stop-color="#160927"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="675" fill="url(#bg)"/>
  <circle cx="1040" cy="92" r="180" fill="#2857ff" opacity="0.20"/>
  <circle cx="1040" cy="600" r="250" fill="#8b2cff" opacity="0.15"/>
  <g transform="translate(58 70)">
    <image href="$LOGO_IMAGE" x="0" y="0" width="390" height="106" preserveAspectRatio="xMinYMid meet"/>
    <text x="4" y="176" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="28" font-weight="700" fill="#f5f7ff">Release $VERSION</text>
    <rect x="4" y="238" width="350" height="54" rx="27" fill="#246bfe"/>
    <text x="32" y="273" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="21" font-weight="700" fill="#ffffff">Playlist opening</text>
    <rect x="4" y="316" width="350" height="54" rx="27" fill="#7738ff"/>
    <text x="32" y="351" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="21" font-weight="700" fill="#ffffff">Persistent library cache</text>
    <rect x="4" y="394" width="350" height="54" rx="27" fill="#101b35"/>
    <text x="32" y="429" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="21" font-weight="700" fill="#ffffff">MPRIS media controls</text>
  </g>
  <g transform="translate(464 118)">
    <rect x="-8" y="-8" width="692" height="477" rx="22" fill="#4d7dff" opacity="0.35"/>
    <rect width="676" height="451" rx="18" fill="#111827"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/search.png" width="676" height="451" preserveAspectRatio="xMidYMid slice"/>
  </g>
</svg>
SVG

cat > "$SOURCE_DIR/soundsgood-feature-montage.svg" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1600" height="900" viewBox="0 0 1600 900">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#050812"/>
      <stop offset="0.54" stop-color="#09162d"/>
      <stop offset="1" stop-color="#160927"/>
    </linearGradient>
  </defs>
  <rect width="1600" height="900" fill="url(#bg)"/>
  <image href="$LOGO_IMAGE" x="90" y="62" width="470" height="127" preserveAspectRatio="xMinYMid meet"/>
  <text x="96" y="218" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="27" fill="#a8b5d4">Dark library views for local music collections.</text>

  <text x="100" y="276" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="30" font-weight="700" fill="#f5f7ff">Albums</text>
  <g transform="translate(100 300)">
    <rect width="640" height="250" rx="16" fill="#111827"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/albums.png" width="640" height="250" preserveAspectRatio="xMidYMin slice"/>
  </g>

  <text x="860" y="276" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="30" font-weight="700" fill="#f5f7ff">Artists</text>
  <g transform="translate(860 300)">
    <rect width="640" height="250" rx="16" fill="#111827"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/artists.png" width="640" height="250" preserveAspectRatio="xMidYMin slice"/>
  </g>

  <text x="100" y="624" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="30" font-weight="700" fill="#f5f7ff">Songs</text>
  <g transform="translate(100 648)">
    <rect width="640" height="220" rx="16" fill="#111827"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/songs.png" width="640" height="220" preserveAspectRatio="xMidYMin slice"/>
  </g>

  <text x="860" y="624" font-family="DejaVu Sans, Noto Sans, sans-serif" font-size="30" font-weight="700" fill="#f5f7ff">Search</text>
  <g transform="translate(860 648)">
    <rect width="640" height="220" rx="16" fill="#111827"/>
    <image xlink:href="file://$ROOT_DIR/docs/screenshots/search.png" width="640" height="220" preserveAspectRatio="xMidYMin slice"/>
  </g>
</svg>
SVG

inkscape "$SOURCE_DIR/soundsgood-hero.svg" \
  --export-type=png \
  --export-filename="$ASSET_DIR/soundsgood-hero.png" \
  >/dev/null

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

inkscape "$SOURCE_DIR/soundsgood-release-card.svg" \
  --export-type=png \
  --export-filename="$ASSET_DIR/soundsgood-release-card.png" \
  >/dev/null

inkscape "$SOURCE_DIR/soundsgood-feature-montage.svg" \
  --export-type=png \
  --export-filename="$ASSET_DIR/soundsgood-feature-montage.png" \
  >/dev/null

magick "$ASSET_DIR/soundsgood-social-card.png" \
  -resize 640x336 \
  "$ASSET_DIR/soundsgood-social-card-small.png"

magick "$ASSET_DIR/soundsgood-hero.png" \
  -resize 800x450 \
  "$ASSET_DIR/soundsgood-hero-small.png"

echo "Generated assets in $ASSET_DIR"
