# Project Assets

This directory contains generated presentation assets for SoundsGood.

Regenerate the assets after updating screenshots, branding, or the project
version:

```bash
scripts/generate-assets.sh
```

Generated PNGs:

- `soundsgood-hero.png`: wide project banner for README pages and websites.
- `soundsgood-hero-small.png`: smaller preview version of the hero banner.
- `soundsgood-social-card.png`: 1200x630 social preview card generated from
  `source/social-preview-custom.png` when that file exists.
- `soundsgood-social-card-small.png`: smaller preview version of the social card.
- `soundsgood-release-card.png`: release announcement card.
- `soundsgood-feature-montage.png`: overview card with the main library views.

The SVG sources, custom brand images, intermediate icon render, and custom
social preview source live in `source/`. The generated assets use the dark-mode
screenshots stored in `docs/screenshots`.

## Recommended Use

- Use `soundsgood-hero.png` near the top of `README.md`.
- Use `soundsgood-social-card.png` as the GitHub repository social preview:
  repository Settings -> General -> Social preview.
- Use `soundsgood-release-card.png` at the top of GitHub Release notes.
- Use `soundsgood-feature-montage.png` when a single overview image is better
  than several screenshots.

GitHub social preview is a repository setting, so it cannot be applied through a
tracked file alone. Upload `soundsgood-social-card.png` manually in the GitHub
repository settings after pushing this directory.
