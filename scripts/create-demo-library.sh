#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later

set -euo pipefail

demo_dir=${1:-"$PWD/demo-music"}

if ! command -v gst-launch-1.0 >/dev/null 2>&1; then
    echo "gst-launch-1.0 is required to generate demo audio." >&2
    exit 1
fi

mkdir -p "$demo_dir/Codex Ensemble/Local Signals"
mkdir -p "$demo_dir/Open Source Quartet/Offline Sessions"

generate_track() {
    frequency=$1
    target=$2
    if [[ -f "$target" ]]; then
        return
    fi
    gst-launch-1.0 -q \
        audiotestsrc wave=sine freq="$frequency" num-buffers=120 \
        ! audioconvert \
        ! wavenc \
        ! filesink location="$target"
}

generate_track 220 "$demo_dir/Codex Ensemble/Local Signals/01 - First Light.wav"
generate_track 330 "$demo_dir/Codex Ensemble/Local Signals/02 - Main Loop.wav"
generate_track 440 "$demo_dir/Open Source Quartet/Offline Sessions/01 - No Cloud Required.wav"
generate_track 550 "$demo_dir/Open Source Quartet/Offline Sessions/02 - Native Window.wav"

echo "Demo library created at: $demo_dir"
