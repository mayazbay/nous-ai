#!/bin/bash
# Read a generic password from macOS Keychain. Value goes to stdout with no trailing newline.
# Usage: secrets-keychain-read.sh <short-name>
# The short-name is prefixed with "nous-agaas/" to form the service.
set -euo pipefail
[[ "$(uname -s)" == "Darwin" ]] || { echo "FAIL: Mac-only" >&2; exit 1; }
[ "$#" -eq 1 ] || { echo "usage: $0 <short-name>" >&2; exit 1; }
exec security find-generic-password -s "nous-agaas/$1" -a nous -w
