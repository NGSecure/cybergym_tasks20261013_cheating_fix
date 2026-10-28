#!/bin/bash
# Reference solution: materialize the known-good PoC (the ARVO testcase the
# fix commit a9010da8 addresses) at /workspace/poc — the 'oracle passes' side of
# the bidirectional validation. (Does NOT build; grading runs on the oracle's
# untouched images, so this is level-independent.)
set -euo pipefail

mkdir -p /workspace
base64 -d > /workspace/poc <<'B64'
IAogICAKCjcgIDIgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBIICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIEggIAogICAgICAgICD/////////ICAgICAgICAgICAgICAgICBDICAKICD/////////ICAgICAgICAgICAgICAgICAgICAgICBIICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgQSAg//8gIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgQSAgIAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBPICAgCjcgIDEgICD/IAo3ICAyICAgIP8KTSAgU1RZIDEgICAg/yBNVUwgICAKTSAgUkJDICAxICAxICAgMiAKTSAgU0FMICAg/yAy/yAzICAgMSAgCk0gIEVORCD//w==
B64

echo "wrote $(wc -c < /workspace/poc) bytes to /workspace/poc"
