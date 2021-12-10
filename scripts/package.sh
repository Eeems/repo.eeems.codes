#!/bin/bash
trap cleanup EXIT
set -e
log(){ echo -e "\033[0;31m==> $@\033[0m"; }
error(){
  if [[ "$GITHUB_ACTIONS" != "" ]];then
    echo -e "::error file=scripts/package.sh::$@"
  else
    echo -e "\033[0;31m$@\033[0m";
  fi
}
function cleanup(){
  log "Cleaning up..."
  sudo rm -rf pkg/*
}
sudo mkdir -p cache
sudo chown -R notroot:notroot cache pkg
if ! command chronic &> /dev/null;then
  log "Installing chronic"
  if compgen -G "cache/chronic-*.pkg.tar.*" > /dev/null;then
    ls cache/chronic-*.pkg.tar.* | while read package;do
      yay -U --cachedir ./cache --noconfirm $package
    done
  elif yay -Sy --cachedir ./cache --builddir ./cache --noconfirm chronic;then
    cp cache/chronic/chronic-*.pkg.tar.* cache/
    rm -r cache/chronic
  else
    function chronic(){
      return "$@"
    }
  fi
fi
shopt -s dotglob nullglob
log "Importing keyring..."
if [[ "$GPG_PRIVKEY" == "" ]];then
  error "GPG key missing from env"
  exit 1
fi
chronic bash -c 'echo "$GPG_PRIVKEY" | gpg --import'
log "Updating..."
chronic yay -Sy --cachedir ./cache  --noconfirm || true
command -v rsync &> /dev/null || yay -S --noconfirm --cachedir ./cache rsync
if compgen -G "packages-*/*.pkg.tar.*" > /dev/null;then
  log "Installing defined dependencies..."
  chronic yay -U --cachedir ./cache  --noconfirm packages-*/*.pkg.tar{,.gz,.bz2,.xz,.Z,.zst}
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
pacman --deptest "${deps[@]}" | xargs -r chronic yay -S --cachedir ./cache  --noconfirm
arraylength=${#validpgpkeys[@]}
if [ $arraylength != 0 ];then
  log "Getting PGP keys..."
  for (( i=0; i<${arraylength}; i++ ));do
    chronic { gpg --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver pool.sks-keyservers.net --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver keyserver.ubuntu.com --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver pgp.mit.edu --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver keyserver.pgp.com --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver keys.openpgp.org --recv-key "${validpgpkeys[$i]}" }
  done
fi
log "Checking PKGBUILD..."
if ! namcap -i pkg/PKGBUILD;then
  error "PKGBUILD contents:\n$(cat pkg/PKGBUILD)"
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
log "Done with package"
