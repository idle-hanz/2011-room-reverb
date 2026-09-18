#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
cat part*.b64 | base64 -d > 2011-room-reverb.zip
echo "Wrote 2011-room-reverb.zip ($(wc -c < 2011-room-reverb.zip) bytes)"
