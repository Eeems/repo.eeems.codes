#!/bin/bash
log(){ echo -e "\033[0;31m==> $@\033[0m"; }
sublog(){ echo -e "\033[0;31m  ->  $@\033[0m"; }
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
function _chronic(){
  if [[ "$VERBOSE" != "" ]];then
    "$@"
    return $!
  fi
  chronic "$@"
  return $!
}
setup_chronic_and_keyring(){
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
  log "Importing keyring..."
  if [[ "$GPG_PRIVKEY" == "" ]];then
    error "GPG key missing from env"
    exit 1
  fi
  _chronic bash -c 'echo "$GPG_PRIVKEY" | gpg --import'
}
