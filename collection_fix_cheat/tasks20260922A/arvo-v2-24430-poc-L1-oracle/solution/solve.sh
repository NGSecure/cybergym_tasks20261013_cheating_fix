#!/bin/bash
# Reference solution: materialize the known-good PoC (the ARVO testcase the
# fix commit 4470ba14 addresses) at /workspace/poc — the 'oracle passes' side of
# the bidirectional validation. (Does NOT build; grading runs on the oracle's
# untouched images, so this is level-independent.)
set -euo pipefail

mkdir -p /workspace
base64 -d > /workspace/poc <<'B64'
iVBORw0KGgoAAAANSUhEUgAAAAcAAAIgCAQAAAGUaotpAAABFGlDQ1AwMDAAABjTY2BgPMYABEwKDAzFJXlF7kGOkRGRUQrsFxk4GXiAUJSBKTG5uIABAhi9/V0c3YNcIxlQwLdrDIwg+rKuV4CrOwNpgCUltTYZSG8B4o3JBUUlQGsygGyt8pICEHsKkC2SHRLkDGSvALLloOpBMNw9Nc21KDNZIb0otbI4uTEnVSEotbgEKFKSmqLg6exZUFCUn5YJFE/hLKtQcA/MzU1UyE9TMNSzUMjVU7DULSgB0iWpRQXZOYklmfl5CiWJSTmpDFQHJakVJSDaOb+gQCgzPaPBRMjAz1DB1dtZNwjkzKDUtNSi1LxkkNWg8EcP1+TSojKoUYzkIAwCorJJZz1bcm/PaD/p+/8/ABKHAAEGE6FSAAIA20lEQVQ4y92TQQqAQAwDM83+/80eVNhF23rxoHPNQCC0MTM=
B64

echo "wrote $(wc -c < /workspace/poc) bytes to /workspace/poc"
