#!/bin/bash
# Sign artifact with GPG
gpg --batch --yes --passphrase $GPG_PASS --detach-sign --armor $1
sha256sum $1 > $1.sha256
echo "Signed $1"
