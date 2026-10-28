#!/bin/bash
# Reference solution: materialize the known-good PoC (the ARVO testcase the
# fix commit 0451adeb addresses) at /workspace/poc — the 'oracle passes' side of
# the bidirectional validation. (Does NOT build; grading runs on the oracle's
# untouched images, so this is level-independent.)
set -euo pipefail

mkdir -p /workspace
base64 -d > /workspace/poc <<'B64'
KGNsYXNzcGVybWlzc2lvbiBmaWxlX3J3KShjbGFzc3Blcm1pc3Npb25zZXQgZmlsZV9ydyBsb3AyKShvcHRpb25hbCBvKGNsYXNzcGVybWlzc2lvbiBsb3AyKShsZXZlbCBTKFMpKSk=
B64

echo "wrote $(wc -c < /workspace/poc) bytes to /workspace/poc"
