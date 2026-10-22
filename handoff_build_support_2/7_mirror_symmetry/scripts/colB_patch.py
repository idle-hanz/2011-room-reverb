"""Prototype: B-side FDN colour map (fdn_b) for two-source Play. Box-only."""
import sys, re
from pathlib import Path
sw = Path(sys.argv[1])
def sub(p, old, new, count=1):
    f = sw / p; t = f.read_text()
    assert t.count(old) >= 1, (p, old[:60])
    t = t.replace(old, new, count); f.write_text(t)
# Python bank
sub('mic_colour/live_bank.py', '        sig["early_b"] = {b: [_deg(th) for th in _line_thetas(taps_b, n, b)] for b in ("l", "r")}\n',
    '        sig["early_b"] = {b: [_deg(th) for th in _line_thetas(taps_b, n, b)] for b in ("l", "r")}\n'
    '        sig["fdn_b"] = {b: [_deg(th) for th in _line_thetas(taps_b, n, b)] for b in buses}\n')
sub('mic_colour/live_bank.py', '        out["early_b"] = {b: [ix.idx(th, b) for th in _line_thetas(taps_b, n, b)] for b in ("l", "r")}\n',
    '        out["early_b"] = {b: [ix.idx(th, b) for th in _line_thetas(taps_b, n, b)] for b in ("l", "r")}\n'
    '        out["fdn_b"] = {b: [ix.idx(th, b) for th in _line_thetas(taps_b, n, b)] for b in buses}\n')
# JS route (page + worklet)
for p in ('static/js/live_fdn.js', 'static/js/fdn_worklet.js'):
    sub(p, 'ROUTE_LEN = 230;', 'ROUTE_LEN = 326;')
sub('static/js/live_fdn.js', '    for (c = 0; c < 3; c++) r[o++] = at(b.direct_b && b.direct_b[names[c]], -1);\n    return r;',
    '    for (c = 0; c < 3; c++) r[o++] = at(b.direct_b && b.direct_b[names[c]], -1);\n'
    '    for (c = 0; c < 3; c++) {\n      row = (b.fdn_b && b.fdn_b[names[c]]) || (b.fdn && b.fdn[names[c]]);\n'
    '      for (i = 0; i < 32; i++) r[o++] = at(row && row[i], -1);\n    }\n    return r;')
sub('static/js/live_fdn.js', '      early_b: colour.early_b || null,\n', '      early_b: colour.early_b || null,\n      fdn_b: colour.fdn_b || null,\n')
# C
c = 'engine/live_stereo.c'
sub(c, 'MAX_FILT = 112,', 'MAX_FILT = 176,')
sub(c, 'ROUTE_LEN = 3 * 32 + 2 * 32 + 2 * 32 + 3 + 3,', 'ROUTE_LEN = 3 * 32 + 2 * 32 + 2 * 32 + 3 + 3 + 3 * 32,')
sub(c, '    int fdnIdx[3][N];\n', '    int fdnIdx[3][N];\n    int fdnIdxB[3][N];\n')
sub(c, '    double yBlk[3][N][PART];\n', '    double yBlk[3][N][PART];\n    double yBlkB[3][N][PART];\n')
sub(c, '        for (i = 0; i < N; i++) st->fdnIdx[b][i] = -1;\n    }\n', '        for (i = 0; i < N; i++) { st->fdnIdx[b][i] = -1; st->fdnIdxB[b][i] = -1; }\n    }\n')
sub(c, '    for (b = 0; b < 3; b++) st->directBIdx[b] = r[o++];\n}', '    for (b = 0; b < 3; b++) st->directBIdx[b] = r[o++];\n'
       '    for (b = 0; b < 3; b++) {\n        for (i = 0; i < N; i++) st->fdnIdxB[b][i] = r[o++];\n    }\n}')
sub(c, '            for (i = 0; i < N; i++) st->yBlk[b][i][t] = st->yB[i] + st->yA[i];',
       '            for (i = 0; i < N; i++) { st->yBlk[b][i][t] = st->yA[i]; st->yBlkB[b][i][t] = st->yB[i]; }')
sub(c, '                st->yBlk[b][i][t] = y + st->yA[i];', '                st->yBlk[b][i][t] = st->yA[i];\n                st->yBlkB[b][i][t] = y;')
sub(c, '                for (i = 0; i < N; i++) sumY += st->yBlk[b][i][t];', '                for (i = 0; i < N; i++) sumY += st->yBlk[b][i][t] + st->yBlkB[b][i][t];')
sub(c, '                st->yBlk[b][i][t] = 0;\n', '                st->yBlk[b][i][t] = 0;\n                st->yBlkB[b][i][t] = 0;\n')
# colour path: after the A loop, add B lines through fdnIdxB, and early B targets fdnIdxB
old_early = '            if (b != BUS_C) {\n                for (i = 0; i < N; i++) {\n                    int tgt = early_target(st->fdnIdx[b], i, st->earlyIdx[eiBase][i]);\n                    int tgtB = st->two ? early_target(st->fdnIdx[b], i, st->earlyBIdx[eiBase][i]) : -2;'
new_early = ('            if (st->two) {\n                for (i = 0; i < N; i++) {\n                    int idx = usable_ir(st, st->fdnIdxB[b][i]);\n                    Filt *f;\n'
             '                    if (idx >= 0 && map[idx] < 0) {\n                        f = take_filt(st, b, 0, idx);\n                        if (!f) idx = -1;\n'
             '                        else { map[idx] = (int)(f - st->filt); f->npart = st->irNpart[idx]; keep[map[idx]] = 1; }\n                    }\n'
             '                    if (idx >= 0) {\n                        int s = map[idx];\n'
             '                        for (t = 0; t < PART; t++) st->firIn[s][t] += (float)(st->fdn_wet * st->yBlkB[b][i][t]);\n                    } else if (idx == -1) {\n'
             '                        for (t = 0; t < PART; t++) ident[t] += st->fdn_wet * st->yBlkB[b][i][t];\n                    }\n                }\n            }\n'
             '            if (b != BUS_C) {\n                for (i = 0; i < N; i++) {\n                    int tgt = early_target(st->fdnIdx[b], i, st->earlyIdx[eiBase][i]);\n'
             '                    int tgtB = st->two ? early_target(st->fdnIdxB[b], i, st->earlyBIdx[eiBase][i]) : -2;')
sub(c, old_early, new_early)
print('patched', sw)
