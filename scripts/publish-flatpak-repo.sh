#!/usr/bin/env bash
set -euo pipefail

APP_ID="io.github.n1ghthill.soundsgood"
REMOTE_NAME="soundsgood"
REPO_TITLE="SoundsGood"
REPO_COMMENT="SoundsGood Flatpak repository"
REPO_DESCRIPTION="Flatpak repository for SoundsGood stable releases."
HOMEPAGE_URL="https://github.com/N1ghthill/soundsgood"
PAGES_URL="https://n1ghthill.github.io/soundsgood"
REPO_URL="${PAGES_URL}/repo/"
GPG_KEY_ID="${SOUNDSGOOD_FLATPAK_GPG_KEY:-452731C50C39B6D4}"
SITE_DIR="dist/flatpak-site"
BUILD_DIR="build-flatpak-repo"

if ! gpg --list-secret-keys "${GPG_KEY_ID}" >/dev/null 2>&1; then
  echo "Missing GPG secret key: ${GPG_KEY_ID}" >&2
  echo "Set SOUNDSGOOD_FLATPAK_GPG_KEY to another signing key if needed." >&2
  exit 1
fi

rm -rf "${SITE_DIR}" "${BUILD_DIR}"
mkdir -p "${SITE_DIR}/repo"

gpg --export "${GPG_KEY_ID}" > "${SITE_DIR}/soundsgood-flatpak.gpg"

flatpak run org.flatpak.Builder \
  --force-clean \
  --default-branch=stable \
  --repo="${SITE_DIR}/repo" \
  --gpg-sign="${GPG_KEY_ID}" \
  "${BUILD_DIR}" \
  "${APP_ID}.yml"

flatpak build-update-repo \
  --generate-static-deltas \
  --default-branch=stable \
  --title="${REPO_TITLE}" \
  --comment="${REPO_COMMENT}" \
  --description="${REPO_DESCRIPTION}" \
  --homepage="${HOMEPAGE_URL}" \
  --gpg-import="${SITE_DIR}/soundsgood-flatpak.gpg" \
  --gpg-sign="${GPG_KEY_ID}" \
  "${SITE_DIR}/repo"

gpg_key_b64="$(base64 --wrap=0 < "${SITE_DIR}/soundsgood-flatpak.gpg")"

cat > "${SITE_DIR}/soundsgood.flatpakrepo" <<EOF
[Flatpak Repo]
Title=${REPO_TITLE}
Url=${REPO_URL}
Homepage=${HOMEPAGE_URL}
Comment=${REPO_COMMENT}
Description=${REPO_DESCRIPTION}
DefaultBranch=stable
GPGKey=${gpg_key_b64}
EOF

touch "${SITE_DIR}/.nojekyll"
cat > "${SITE_DIR}/index.html" <<EOF
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SoundsGood Flatpak Repository</title>
    <style>
      body { font-family: system-ui, sans-serif; max-width: 760px; margin: 3rem auto; padding: 0 1rem; line-height: 1.5; }
      code, pre { background: #f3f4f6; border-radius: 6px; }
      code { padding: .1rem .25rem; }
      pre { padding: 1rem; overflow-x: auto; }
    </style>
  </head>
  <body>
    <h1>SoundsGood Flatpak Repository</h1>
    <p>Add this repository once, then install and update SoundsGood with Flatpak:</p>
    <pre><code>flatpak remote-add --user --if-not-exists ${REMOTE_NAME} ${PAGES_URL}/soundsgood.flatpakrepo
flatpak install --user ${REMOTE_NAME} ${APP_ID}
flatpak update --user ${APP_ID}</code></pre>
    <p>Project: <a href="${HOMEPAGE_URL}">${HOMEPAGE_URL}</a></p>
  </body>
</html>
EOF

pages_worktree="$(mktemp -d)"
trap 'rm -rf "${pages_worktree}"' EXIT

cp -a "${SITE_DIR}/." "${pages_worktree}/"
(
  cd "${pages_worktree}"
  git init
  git config user.name "N1ghthill"
  git config user.email "115030983+N1ghthill@users.noreply.github.com"
  git checkout -b gh-pages
  git add .
  git commit -m "Publish Flatpak repository"
  git remote add origin "https://github.com/N1ghthill/soundsgood.git"
  git push -f origin gh-pages
)

echo "Published ${REPO_URL}"
