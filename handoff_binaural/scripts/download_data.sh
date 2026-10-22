#!/usr/bin/env bash
# Fetch the source SOFA files (not shipped in the pack). Checksums VERIFIED 30 Sep 2026.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/sadie2 data/thk_ku100
get() { curl -sSL --retry 5 --retry-delay 5 --retry-all-errors -o "$1" "$2"; }
get data/sadie2/D1_HRIR_SOFA.zip https://zenodo.org/api/records/12092466/files/D1_HRIR_SOFA.zip/content
get data/sadie2/D2_HRIR_SOFA.zip https://zenodo.org/api/records/12092466/files/D2_HRIR_SOFA.zip/content
get data/sadie2/LICENSE.txt      https://zenodo.org/api/records/12092466/files/LICENSE.txt/content
get data/thk_ku100/HRIR_FULL2DEG.sofa https://zenodo.org/api/records/3928297/files/HRIR_FULL2DEG.sofa/content
get data/thk_ku100/HRIR_CIRC360.sofa  https://zenodo.org/api/records/3928297/files/HRIR_CIRC360.sofa/content
md5sum -c <<'SUMS'
4850c1eb8e63e2d4f605edcdb4d5c883  data/sadie2/D1_HRIR_SOFA.zip
f555491d1b6b1a108bb4d26b63ad84a4  data/sadie2/D2_HRIR_SOFA.zip
0ba5044c64ef53cb0189c9546081e228  data/sadie2/LICENSE.txt
aa48acb20c1fb8ff3d8de116107b73c2  data/thk_ku100/HRIR_FULL2DEG.sofa
058fcf99ac72c2ab94b2eed514b90bdf  data/thk_ku100/HRIR_CIRC360.sofa
SUMS
(cd data/sadie2 && unzip -o -q D1_HRIR_SOFA.zip 'D1_HRIR_SOFA/D1_44K*' 'D1_HRIR_SOFA/D1_48K*' && unzip -o -q D2_HRIR_SOFA.zip 'D2_HRIR_SOFA/D2_44K*' 'D2_HRIR_SOFA/D2_48K*')
echo "data ready"
