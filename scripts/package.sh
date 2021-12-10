#!/bin/bash
set -e
log(){ echo -e "\033[0;31m==> $@\033[0m"; }
shopt -s dotglob nullglob
log "Importing keyring..."
echo "$GPG_PRIVKEY" | gpg --import
log "Updating..."
chronic yay -Sy --cachedir ./cache --noconfirm || true
chronic yay -S --cachedir ./cache --noconfirm chronic
command -v rsync &> /dev/null || yay -S --noconfirm rsync
sudo mkdir -p cache
sudo chown -R notroot:notroot cache pkg
if compgen -G "packages-*/*.pkg.tar.*" > /dev/null;then
  log "Installing defined dependencies..."
  chronic yay -U --cachedir ./cache --noconfirm packages-*/*.pkg.tar{,.gz,.bz2,.xz,.Z,.zst}
fi
if [[ "x$SETUP_SCRIPT" != "x" ]];then
  sudo mkdir tmp
  sudo chown -R notroot:notroot tmp
  pushd tmp > /dev/null
  sudo ln -s ../pkg pkg
  sudo ln -s ../cache cache
  log "Running setup script..."
  chronic bash -c "$SETUP_SCRIPT"
  popd > /dev/null
fi
log "Installing PKGBUILD dependencies..."
depends=()
makedepends=()
checkdepends=()
validpgpkeys=()
source pkg/PKGBUILD
deps=( "${depends[@]}" "${makedepends[@]}" "${checkdepends[@]}" )
chronic pacman --deptest "${deps[@]}" | xargs -r yay -S --cachedir ./cache --noconfirm
arraylength=${#validpgpkeys[@]}
if [ $arraylength != 0 ];then
  log "Getting PGP keys..."
  for (( i=0; i<${arraylength}; i++ ));do
    gpg --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver pool.sks-keyservers.net --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver keyserver.ubuntu.com --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver pgp.mit.edu --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver keyserver.pgp.com --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver keys.openpgp.org --recv-key "${validpgpkeys[$i]}"
  done
fi
log "Checking PKGBUILD..."
if ! namcap -i pkg/PKGBUILD;then
  log "PKGBUILD contents:"
  echo pkg/PKGBUILD
fi
log "Building package..."
pushd pkg > /dev/null
chronic makepkg -f --noconfirm --sign
if [[ "x$CLEANUP_SCRIPT" != "x" ]];then
  log "Running cleanup script..."
  pushd . > /dev/null
  chronic bash -c "$CLEANUP_SCRIPT"
  popd > /dev/null
fi
popd > /dev/null
sudo chown notroot:notroot packages
log "Checking packages..."
ls pkg/*.pkg.tar.* | while read pkgfile;do namcap -i "$pkgfile" || true;done
log "Exporting packages..."
chronic rsync -Pcuav pkg/*.pkg.tar.* packages
log "Cleaning up..."
rm -rf pkg/*
