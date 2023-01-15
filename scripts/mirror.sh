#!/bin/bash
if ! command -v rsync &> /dev/null;then
  yay -Sy
  yay -S --noconfirm rsync
fi
if ! command -v ssh &> /dev/null;then
  yay -Sy
  yay -S --noconfirm openssh
fi
set -e
log(){ echo -e "\033[0;31m==> $@\033[0m"; }
log "Setting up..."
sudo mkdir -p tmp
sudo chown notroot:notroot tmp repo www
touch tmp/server_key
chmod 600 tmp/server_key
echo "$SSH_KEY" > tmp/server_key
cp -r www/* repo/
log "Uploading to $SERVER..."
rsync -Pcuav --delete -e "ssh -p 22 -oStrictHostKeyChecking=no -i tmp/server_key" repo/* "$USER@$SERVER:$DIR/staging"
ssh -p 22 -oStrictHostKeyChecking=no -i tmp/server_key "$USER@$SERVER" "rsync -a --delete --link-dest='$DIR/staging' '$DIR/staging/'* '$DIR/live'"
rm tmp/server_key
