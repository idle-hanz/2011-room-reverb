"""List / split p4->p5 unified-diff hunks into concern patches.
Usage: python split_hunks.py list  |  python split_hunks.py write <outdir>"""
import sys, subprocess, re, json
from pathlib import Path
W = Path('/workspace/build_support_2/work')
A, B = W / 'p4' / 'software', W / 'p5' / 'software'
FILES = subprocess.run(['bash', '-c', f'cd {B} && diff -rq {A} {B} | grep -v __pycache__ | grep -v "\\.wasm"'], capture_output=True, text=True).stdout

def file_hunks(rel):
    a = A / rel
    out = subprocess.run(['diff', '-u', '-N', '--label', f'a/{rel}', '--label', f'b/{rel}', str(a) if a.exists() else '/dev/null', str(B / rel)], capture_output=True, text=True).stdout
    lines = out.splitlines(keepends=True)
    head, hunks, cur = lines[:2], [], None
    for ln in lines[2:]:
        if ln.startswith('@@'):
            cur = [ln]; hunks.append(cur)
        else:
            cur.append(ln)
    return head, [''.join(h) for h in hunks]

RULES = [  # (concern, regex on the hunk's +/- lines), first match wins
    ('09_versions_and_build_tests', r'WORKLET_VER|\?v=\d+|sr = 48000  # decision 7|K1 \(28 Sep 2026\): with the yaw flip|40\.0, 0\.0, 0\.0'),
    ('08_colour_per_rate', r'SUPPORTED_RATES|rate_supported|unsupported_rate_notice|colour_notice|colourNotice|lastColourNotice|notice|tables_dir\(|_load_one\(|fit_fs'),
    ('07_headroom_trim', r'loop_level_trim|LOOP_LEVEL_TRIM|Loop level trim|loop_trim_db|Headroom decision'),
    ('06_K4_stale_early_lane', r'K4 stale-early fix|write_lane\(st->ring\[b\]\[i\], line->w, LANE_EARLY'),
    ('04_K1_yaw_convention', r'YAW_X_SIGN|look_vector|_look_vector|K1|yaw_rad|hotter|Superseded note|PATTERN_|SUPER_A|CENTRE_DZ_MAX_M'),
    ('05_K2_K3_K4_defaults_diffusion', r'DIFFUSION_MASTER|diffusion_master'),
    ('05_K2_K3_K4_defaults_diffusion', r'air_lp|"sx"|"sy"|\bsx:|\bsy\b|early_wet|fader_direct|ewEnable|id="sy"'),
]

def classify(h):
    ch = ''.join(l for l in h.splitlines(keepends=True)[1:] if l[:1] in '+-')
    for name, rx in RULES:
        if re.search(rx, ch):
            return name
    return 'UNCLASSIFIED'

def all_hunks():
    rels = []
    for ln in FILES.splitlines():
        m = re.match(r'Files (\S+) and (\S+) differ', ln)
        if m: rels.append(str(Path(m.group(2)).relative_to(B)))
        m = re.match(r'Only in (\S+): (\S+)', ln)
        if m:
            d = Path(m.group(1)) / m.group(2)
            for f in sorted(d.rglob('*')) if d.is_dir() else [d]:
                if f.is_file(): rels.append(str(f.relative_to(B)))
    res = []
    for rel in rels:
        head, hs = file_hunks(rel)
        for h in hs: res.append((rel, head, h, classify(h)))
    return res

if __name__ == '__main__':
    hs = all_hunks()
    if sys.argv[1] == 'list':
        for rel, _, h, c in hs:
            if 'sos_tables/44100' in rel: continue
            print(f'{c:30s} {rel:40s} {h.splitlines()[0]}')
        print('new table files:', sum(1 for r in hs if 'sos_tables/44100' in r[0]))
    else:
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        groups = {}
        for rel, head, h, c in hs:
            groups.setdefault(c, {}).setdefault(rel, [''.join(head)]).append(h)
        for c, files in groups.items():
            with open(out / f'{c}.diff', 'w', encoding='utf-8') as f:
                for rel, parts in files.items():
                    f.write(''.join(parts))
        print({c: sum(len(v) - 1 for v in files.values()) for c, files in groups.items()})
