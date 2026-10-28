#!/bin/bash
# Reference solution: materialize the known-good PoC (the ARVO testcase the
# fix commit 52161ce8 addresses) at /workspace/poc — the 'oracle passes' side of
# the bidirectional validation. (Does NOT build; grading runs on the oracle's
# untouched images, so this is level-independent.)
set -euo pipefail

mkdir -p /workspace
base64 -d > /workspace/poc <<'B64'
ZXZlbnRzIHsKICBkb3duc3RyZWFtX3NlbmRfZXZlbnQgewogICAgaDJfZnJhbWVzIHsKICAgICAgc2V0dGluZ3MgewogICAgICB9CiAgICB9CiAgICBoMl9mcmFtZXMgewogICAgICBwb3N0X3JlcXVlc3QgewogICAgICAgIHN0cmVhbV9pbmRleDogNTM4OTcwNjM0CiAgICAgICAgaG9zdDogIj0iCiAgICAgICAgcGF0aDogIi9wYXRoL3RvL2xvbmcvdXJsIgogICAgICB9CiAgICB9CiAgICBoMl9mcmFtZXMgewogICAgfQogIH0KfQpldmVudHMgewogIHVwc3RyZWFtX3NlbmRfZXZlbnQgewogICAgaDJfZnJhbWVzIHsKICAgICAgc2V0dGluZ3MgewogICAgICB9CiAgICB9CiAgICBoMl9mcmFtZXMgewogICAgICBtYWxmb3JtZWRfcmVxdWVzdCB7CiAgICAgIH0KICAgIH0KICAgIGgyX2ZyYW1lcyB7CiAgICAgIG1ldGFkYXRhIHsKICAgICAgICBmbGFnczogRU5EX0hFQURFUlMKICAgICAgfQogICAgfQogIH0KfQpldmVudHMgewp9CmV2ZW50cyB7Cn0K
B64

echo "wrote $(wc -c < /workspace/poc) bytes to /workspace/poc"
