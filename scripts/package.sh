#!/bin/bash
set -e
source $(dirname "${BASH_SOURCE[0]}")/lib.sh
function cleanup(){
  log "Cleaning up..."
  sudo rm -rf pkg/*
}
trap cleanup EXIT
sudo mkdir -p cache
sudo chown -R notroot:notroot cache pkg
setup_chronic_and_keyring
shopt -s dotglob nullglob
log "Generating local repo..."
if [ -d /pkg/repo ];then
  sudo mkdir /repo
  sudo chown -R notroot:notroot /repo
  packages=($(echo ./*.pkg.tar{,.gz,.bz2,.xz,.Z,.zst}))
  repo-add --remove --prevent-downgrade /repo/localrepo.db.tar.gz ${packages[@]}
  if [ -f /pkg/repo/localrepo.db ];then
    echo '[localrepo]' | sudo tee -a /etc/pacman.conf
    echo 'SigLevel = Optional TrustAll' | sudo tee -a /etc/pacman.conf
    echo 'Server = file:///repo' | sudo tee -a /etc/pacman.conf
  fi
fi
log "Updating..."
_chronic yay -Sy --cachedir ./cache  --noconfirm || true
command -v rsync &> /dev/null || yay -S --noconfirm --cachedir ./cache rsync
if compgen -G "depends/*.pkg.tar.*" > /dev/null;then
  log "Installing defined dependencies..."
  _chronic yay -U --cachedir ./cache  --noconfirm depends/*.pkg.tar{,.gz,.bz2,.xz,.Z,.zst}
fi
if [[ "x$SETUP_SCRIPT" != "x" ]];then
  sudo mkdir tmp
  sudo chown -R notroot:notroot tmp
  pushd tmp > /dev/null
  sudo ln -s ../pkg
  sudo ln -s ../cache
  log "Running setup script..."
  _chronic bash -c "$SETUP_SCRIPT"
  popd > /dev/null
fi
if ! [ -f pkg/PKGBUILD ];then
  error "PKGBUILD missing"
  exit 1
fi
if [[ "x$MAKE_DEPENDS" != "x" ]];then
  log "Installing Make Depends..."
  _chronic bash -c "$MAKE_DEPENDS"
fi
log "Installing PKGBUILD dependencies..."
depends=()
makedepends=()
checkdepends=()
validpgpkeys=()
source pkg/PKGBUILD
deps=( "${depends[@]}" "${makedepends[@]}" "${checkdepends[@]}" )
deps="${deps[@]}" _chronic bash -c 'pacman --deptest $deps | xargs -r yay -S --cachedir ./cache  --noconfirm'
arraylength=${#validpgpkeys[@]}
if [ $arraylength != 0 ];then
  log "Getting PGP keys..."
  for (( i=0; i<${arraylength}; i++ ));do
    _chronic gpg --recv-key "${validpgpkeys[$i]}" \
    || _chronic gpg --keyserver pool.sks-keyservers.net --recv-key "${validpgpkeys[$i]}" \
    || _chronic gpg --keyserver keyserver.ubuntu.com --recv-key "${validpgpkeys[$i]}" \
    || _chronic gpg --keyserver pgp.mit.edu --recv-key "${validpgpkeys[$i]}" \
    || _chronic gpg --keyserver keyserver.pgp.com --recv-key "${validpgpkeys[$i]}" \
    || _chronic gpg --keyserver keys.openpgp.org --recv-key "${validpgpkeys[$i]}"
  done
fi
pushd pkg > /dev/null
log "Checking PKGBUILD..."
if ! namcap -i PKGBUILD;then
  error "PKGBUILD invalid"
  debug "$(cat PKGBUILD)"
fi
log "Building package..."
_chronic makepkg -f --noconfirm
if [[ "x$CLEANUP_SCRIPT" != "x" ]];then
  log "Running cleanup script..."
  pushd . > /dev/null
  _chronic bash -c "$CLEANUP_SCRIPT"
  popd > /dev/null
fi
popd > /dev/null
sudo chown notroot:notroot packages
log "Checking packages..."
ls pkg/*.pkg.tar.* | while read pkgfile;do namcap -i "$pkgfile" || true;done
log "Exporting packages..."
_chronic rsync -Pcuav pkg/*.pkg.tar.* packages
log "Done with package"
