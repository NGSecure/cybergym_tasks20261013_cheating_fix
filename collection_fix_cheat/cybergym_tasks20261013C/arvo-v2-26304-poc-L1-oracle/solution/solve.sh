#!/bin/bash
# Reference solution: materialize the known-good PoC (the ARVO testcase the
# fix commit 979a9bb7 addresses) at /workspace/poc — the 'oracle passes' side of
# the bidirectional validation. (Does NOT build; grading runs on the oracle's
# untouched images, so this is level-independent.)
set -euo pipefail

mkdir -p /workspace
base64 -d > /workspace/poc <<'B64'
jwEAAAX/q/8AAQgAJyPTgM63AAAJAP41//f3mCeY79fXLMYAAAEAAAAAAAAAAAAAAJiY948BcQIAANDQ98cAAAAAAADmpADv78yK6+/vzAAABwIAAAAAAOakAAAAAACj7+/vzO+RAe/z7+8oijFjM+8d7+/v1wABAAAAAAAAAACYmPePAXECAADQ0PfHAAAAAAAA5qQAAAAAAO/vo4rM7+vv78wAAAcCAAAAxQAAAIUA/wIAAAAAAAAFAAAAgaGBgf3///////fHAAAAgAAAAAAA5qQAAAAAAKPv7+/M75EB7/Pv7yiKMWMBAGCg/v//AB+kzAgA//+lbgAsAABK0i3aAAAAANoAAAAAANoAAAAAAAAAAAAAANoAAf8AAACorKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqKioqLS0tLS04ODgAAEqAgClAgCliIiI8oiIiADFAAAAhQAJAP4w/wCjBgUAAACBoYGB/f//////1M/U1DKHBfu6+9gA/28yzO+RAe/z7+8oijNjM+8d7wkA/jX/9/eYJ5jv188sxgAAAQAAAAAAAAAAmJj3jwFxAgAA0ND3xwAAAACQoKD3GNv/AAAABaOKzO/r7+/MAAAHAgAAAMUAAACFAAkA/jX/AKMGBQAAAIGhgYH9///////Uz88=
B64

echo "wrote $(wc -c < /workspace/poc) bytes to /workspace/poc"
