#!/bin/bash
trap cleanup EXIT
set -e
log(){ echo -e "\033[0;31m==> $@\033[0m"; }
error(){
  if [[ "x$GITHUB_ACTIONS" != "x" ]];then
    echo -e "::error file=scripts/package.sh::$@"
  else
    echo -e "\033[0;31m$@\033[0m";
  fi
}
warning(){
  if [[ "x$GITHUB_ACTIONS" != "x" ]];then
    echo -e "::warning file=scripts/package.sh::$@"
  else
    echo -e "\033[1;33m$@\033[0m";
  fi
}
debug(){
  if [[ "x$GITHUB_ACTIONS" != "x" ]];then
    echo -e "::debug file=scripts/package.sh::$@"
  elif [[ "x$VERBOSE" != "x" ]];then
    echo -e "$@";
  fi
}
function cleanup(){
  log "Cleaning up..."
  sudo rm -rf pkg/*
}
sudo mkdir -p cache
sudo chown -R notroot:notroot cache pkg
if ! [ -f pkg/PKGBUILD ];then
  error "PKGBUILD missing"
  exit 1
fi
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
      "$@"
      return $!
    }
  fi
fi
function _chronic(){
  if [[ "$VERBOSE" != "" ]];then
    "$@"
    $!
  fi
  chronic "$@"
  return $!
}
shopt -s dotglob nullglob
log "Importing keyring..."
if [[ "$GPG_PRIVKEY" == "" ]];then
  error "GPG key missing from env"
  exit 1
fi
_chronic bash -c 'echo "$GPG_PRIVKEY" | gpg --import'
log "Updating..."
_chronic yay -Sy --cachedir ./cache  --noconfirm || true
command -v rsync &> /dev/null || yay -S --noconfirm --cachedir ./cache rsync
if compgen -G "packages-*/*.pkg.tar.*" > /dev/null;then
  log "Installing defined dependencies..."
  _chronic yay -U --cachedir ./cache  --noconfirm packages-*/*.pkg.tar{,.gz,.bz2,.xz,.Z,.zst}
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
log "Installing PKGBUILD dependencies..."
depends=()
makedepends=()
checkdepends=()
validpgpkeys=()
source pkg/PKGBUILD
deps=( "${depends[@]}" "${makedepends[@]}" "${checkdepends[@]}" )
deps="${deps[@]}" _chronic bash -c 'pacman --deptest "$deps" | xargs -r yay -S --cachedir ./cache  --noconfirm'
arraylength=${#validpgpkeys[@]}
if [ $arraylength != 0 ];then
  log "Getting PGP keys..."
  for (( i=0; i<${arraylength}; i++ ));do
    _chronic { gpg --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver pool.sks-keyservers.net --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver keyserver.ubuntu.com --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver pgp.mit.edu --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver keyserver.pgp.com --recv-key "${validpgpkeys[$i]}" ||
      gpg --keyserver keys.openpgp.org --recv-key "${validpgpkeys[$i]}" }
  done
fi
pushd pkg > /dev/null
log "Checking PKGBUILD..."
if ! namcap -i PKGBUILD;then
  error "PKGBUILD invalid"
  debug "$(cat PKGBUILD)"
fi
log "Building package..."
_chronic makepkg -f --noconfirm --sign
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
