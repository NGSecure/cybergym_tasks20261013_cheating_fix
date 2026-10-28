#!/bin/bash
# Reference solution: materialize the known-good PoC (the ARVO testcase the
# fix commit e670bb40 addresses) at /workspace/poc — the 'oracle passes' side of
# the bidirectional validation. (Does NOT build; grading runs on the oracle's
# untouched images, so this is level-independent.)
set -euo pipefail

mkdir -p /workspace
base64 -d > /workspace/poc <<'B64'
Ef+8AAAA//+7LgAAAACHAAAAAAAAAAC8AgAAAAAAAAAAAAAjALy8AAAAAAAAAAAjwwC8BP87AAAAAAAA1faUqEQkCQD6AgAQAJvOaACgAAAbAAD////P+En/AN4AAK0AQQDOAAgXCgAAhwAACADThwAAAAAAAAAAACL/AwCHqv74KOIBegCAAgA0Bg0AAGABAABXMgAAACsAAAAtAAAAAAAA+VoAzgAAAAoAAIcKAAAAAAAAAAAAAN4AAAA=
B64

echo "wrote $(wc -c < /workspace/poc) bytes to /workspace/poc"
