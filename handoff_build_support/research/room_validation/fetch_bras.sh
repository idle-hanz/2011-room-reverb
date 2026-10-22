#!/bin/sh
# Download the BRAS pieces used by the validation (about 0.9 GB). Licence: CC BY-SA 4.0.
# Record: https://doi.org/10.14279/depositonce-6726.3  (DepositOnce item 38410727-febb-4769-8002-9c710ba393c4)
set -e
D=${BRAS_DIR:-/workspace/bras}; mkdir -p "$D"; cd "$D"
B=https://api-depositonce.tu-berlin.de/server/api/core/bitstreams
curl -L -o Documentation.pdf $B/ba6b4f29-418b-4ec8-bb9d-72d488b8e5e6/content
curl -L -o CR2.zip  $B/53c3cf64-3547-4aa6-946b-1b4755729f2a/content
curl -L -o surf.zip $B/b2970524-fb10-482a-ab14-f07da5ad7615/content
curl -L -o add.zip  $B/5e27800e-78ef-47a8-855e-78ac5a5adff6/content
unzip -q -o CR2.zip -x '*BRIRs*' -d cr2
unzip -q -o surf.zip '3 Surface descriptions/_csv/*' -d surf
unzip -q -o add.zip '4 Additional data/Room acoustic parameters/*' -d add
