"""Restore software/ and harness golden/ from the replacement preBLOOM zip.

Refuses the incomplete zip. Does not delete files that are not in the zip.
"""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
ZIP = ROOT / "software_backup_2026-10-19_preBLOOM.zip"
MANIFEST = (
    ROOT / "handoff_build_support_2" / "roadmap" / "overnight" / "PIN_MANIFEST_preBLOOM.txt"
)
HARNESS = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness"
EXPECT_SHA = "58a0d50b4a49b84ee09c973bb1f1f87f97ca6256"
EXPECT_BYTES = 95289838


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    got = sha1(ZIP)
    size = ZIP.stat().st_size
    print("ZIP", got, size)
    if got != EXPECT_SHA or size != EXPECT_BYTES:
        raise SystemExit("WRONG ZIP")
    rows = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        bits = line.split()
        if len(bits) != 3 or len(bits[0]) != 40:
            continue
        rows.append((bits[0], int(bits[1]), bits[2].replace("\\", "/")))
    print("MANIFEST_ROWS", len(rows))
    z = zipfile.ZipFile(ZIP)
    names = set(z.namelist())
    missing = [rel for _h, _n, rel in rows if rel not in names]
    print("MISSING_IN_ZIP", len(missing))
    for rel in missing[:10]:
        print(" MISSING", rel)
    if missing:
        raise SystemExit("manifest names missing from zip")
    for info in z.infolist():
        name = info.filename.replace("\\", "/")
        if name.endswith("/"):
            continue
        if name.startswith("software/"):
            dest = ROOT / name
        elif name.startswith("golden/"):
            dest = HARNESS / name
        else:
            raise SystemExit("unexpected zip name " + name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with z.open(info) as src, dest.open("wb") as out:
            out.write(src.read())
    bad = 0
    for digest, nbytes, rel in rows:
        if rel.startswith("software/"):
            dest = ROOT / rel
        else:
            dest = HARNESS / rel
        if not dest.is_file():
            print("ABSENT", rel)
            bad += 1
            continue
        if dest.stat().st_size != nbytes or sha1(dest) != digest:
            print("MISMATCH", rel, dest.stat().st_size, sha1(dest), "want", digest)
            bad += 1
    print("VERIFY_BAD", bad, "OF", len(rows))
    listed = {rel for _h, _n, rel in rows}
    survivors = []
    for p in (ROOT / "software").rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if "/.venv/" in "/" + rel or "__pycache__" in rel:
            continue
        if rel not in listed:
            survivors.append(rel)
    print("SURVIVORS", len(survivors))
    for rel in survivors:
        print(" SURVIVE", rel)


if __name__ == "__main__":
    main()
