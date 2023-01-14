#!/bin/bash
if ! command -v act &> /dev/null;then
  echo "Please install act from: https://github.com/nektos/act"
  exit 1
fi
if ! [ -f .secrets ];then
  echo ".secrets file missing"
  exit 1
fi
if ! [ -f .keyring/pubring.kbx ];then
  mkdir -p .keyring
  gpg --verbose --batch --gen-key <<EOF
    %echo Generating a basic OpenPGP key
    Key-Type: RSA
    Key-Length: 2048
    Subkey-Type: RSA
    Subkey-Length: 2048
    Name-Real: User 1
    Name-Comment: User 1
    Name-Email: user@1.com
    Expire-Date: 0
    %no-ask-passphrase
    %no-protection
    %pubring .keyring/pubring.kbx
    %secring .keyring.trustdb.gpg
    %commit
    %echo done
EOF
    echo -e "5\ny\n" \
      |  gpg \
          --no-default-keyring \
          --secret-keyring .keyring/trustdb.gpg \
          --keyring .keyring/pubring.kbx \
          --command-fd 0 \
          --expert \
          --edit-key user@1.com trust
fi
GPGKEY="$(gpg \
    --no-default-keyring \
    --secret-keyring .keyring/trustdb.gpg \
    --keyring .keyring/pubring.kbx \
    --list-secret-keys \
    --with-colons \
  2> /dev/null \
  | grep '^sec:' \
  | cut \
    --delimiter ':' \
    --fields 5)"
SSH_KEY="$(cat ~/.ssh/id_rsa)"
GPG_PRIVKEY="$(gpg \
  --no-default-keyring \
  --secret-keyring .keyring/trustdb.gpg \
  --keyring .keyring/pubring.kbx \
  --export-secret-key \
  --armor \
  $GPGKEY)"

if [[ "$1" == "--direct" ]];then
  eval < .secrets
  GPG_PRIVKEY="$GPG_PRIVKEY" GPGKEY="$GPGKEY" SSH_KEY="$SSH_KEY" python3 scripts/build.py build all
elif [[ "$1" == "--repo" ]];then
  if [[ "x$2" == "x" ]];then
    echo "You must specify a repo"
    exit 1
  fi
  eval < .secrets
  GPG_PRIVKEY="$GPG_PRIVKEY" GPGKEY="$GPGKEY" SSH_KEY="$SSH_KEY" python3 scripts/build.py build repo "$2"
else
  GPG_PRIVKEY="$GPG_PRIVKEY" GPGKEY="$GPGKEY" SSH_KEY="$SSH_KEY" act \
    -s SSH_KEY \
    -s GPGKEY \
    -s GPG_PRIVKEY \
    --secret-file .secrets \
    --privileged \
    -P ubuntu-latest=catthehacker/ubuntu:full-latest
fi
