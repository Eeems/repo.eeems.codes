#!/bin/bash
set -e
source $(dirname "${BASH_SOURCE[0]}")/lib.sh
setup_chronic_and_keyring
log "Creating repo..."
sublog "Removing old files"
sudo chown -R notroot:notroot repo
cd repo
rm -f "$REPO_NAME.db.tar.gz" "$REPO_NAME.files.tar.gz" "$REPO_NAME.db.tar.gz.old" "$REPO_NAME.db.tar.gz.sig" "$REPO_NAME.files.tar.gz.sig"
log "Signing packages..."
shopt -s dotglob nullglob
packages=($(echo ./*.pkg.tar{,.gz,.bz2,.xz,.Z,.zst}))
for i in "${!packages[@]}";do
  file=${packages[i]}
  echo "    $file.sig"
  if [ -f "$file".sig ];then
    rm "$file".sig
  fi
  gpg --local-user $GPGKEY --detach-sign --batch --output "$file".sig --sign "$file"
  if ! [ -f "$file".sig ];then
    rm "Failed to generate $file.sig"
    exit 1
  fi
done
repo-add --remove --prevent-downgrade --sign "$REPO_NAME.db.tar.gz" ${packages[@]}
