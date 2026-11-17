#!/bin/sh
# Adds the app built by flatpak-builder (ostree repo $1, branch "stable") to our own Flatpak
# repository on GitHub Pages: branch gh-pages, served at https://michalsiman.github.io/aprs-kiss-app/
#
# Needs: VERSION, GPG_KEY (the armoured private signing key), GITHUB_TOKEN, GITHUB_REPOSITORY; flatpak, ostree.
# The gh-pages branch is always one commit (no history), so old builds don't pile up in git;
# the ostree repo itself keeps the last few builds for updates and rollbacks.
set -eu

SRC=$1
ID=io.github.michalsiman.aprs_kiss_app
URL=https://michalsiman.github.io/aprs-kiss-app
HERE=$(cd "$(dirname "$0")" && pwd)

GNUPGHOME=$(mktemp -d)
export GNUPGHOME
printf '%s\n' "$GPG_KEY" | gpg --batch --quiet --import
KEY=$(gpg --list-secret-keys --with-colons | awk -F: '/^fpr/ {print $10; exit}')

# The published site so far (nothing on the first run).
rm -rf site && mkdir site
if git fetch --quiet --depth 1 origin gh-pages; then
    git archive FETCH_HEAD | tar -x -C site
fi
[ -d site/repo/objects ] || ostree init --mode=archive-z2 --repo=site/repo

flatpak build-commit-from --src-repo="$SRC" --gpg-sign="$KEY" --gpg-homedir="$GNUPGHOME" \
    --no-update-summary site/repo "app/$ID/x86_64/stable"
flatpak build-update-repo --gpg-sign="$KEY" --gpg-homedir="$GNUPGHOME" \
    --title="APRS & Packet" --default-branch=stable \
    --generate-static-deltas --prune --prune-depth=3 site/repo

# Files people click on: .flatpakref installs the app (and the GNOME runtime from Flathub),
# .flatpakrepo only adds the repository.
B64=$(base64 -w0 "$HERE/aprs-kiss.gpg")
cat > site/aprs-kiss.flatpakref <<EOF
[Flatpak Ref]
Name=$ID
Branch=stable
Title=APRS & Packet
Url=$URL/repo/
SuggestRemoteName=aprs-kiss
RuntimeRepo=https://dl.flathub.org/repo/flathub.flatpakrepo
IsRuntime=false
Homepage=https://github.com/michalsiman/aprs-kiss-app
Icon=$URL/icon.png
GPGKey=$B64
EOF
cat > site/aprs-kiss.flatpakrepo <<EOF
[Flatpak Repo]
Title=APRS & Packet
Url=$URL/repo/
Homepage=https://github.com/michalsiman/aprs-kiss-app
Comment=APRS and packet radio with a KISS TNC
Icon=$URL/icon.png
GPGKey=$B64
EOF
cp "$HERE/site/index.html" site/index.html
cp "$HERE/../linux/icons/128.png" site/icon.png
cp "$HERE/aprs-kiss.gpg" site/aprs-kiss.gpg
touch site/.nojekyll

cd site
git init --quiet -b gh-pages
git add -A
git -c user.name="github-actions[bot]" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
    commit --quiet -m "Flatpak repository: ${VERSION:-build}"
git push --quiet --force "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" gh-pages
