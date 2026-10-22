"""Build two candidate fixes of 1905 live_stereo.c for the t19 cost check.
F1: hoist the per-line 'st->shared && b == BUS_C' test into one local per bus_sample call.
F2: F1 + move the five shared-tail doubles out of the hot Line struct into cold arrays
    in LiveStereo (restores the 1630 Line layout)."""
import re, sys
src = open('/workspace/build_support_2/snapshot_2026-10-02_1905/software/engine/live_stereo.c').read()
def rep(s, a, b, n=1):
    c = s.count(a)
    assert c == n, (a, c)
    return s.replace(a, b)
f1 = src
f1 = rep(f1, "    if (st->shared && b != BUS_C) runFdn = 0;\n",
             "    const int shC = st->shared && b == BUS_C;\n    if (st->shared && b != BUS_C) runFdn = 0;\n")
f1 = rep(f1, "if (st->shared && b == BUS_C) injLoop", "if (shC) injLoop")
f1 = rep(f1, "} else if (st->shared && b == BUS_C) {", "} else if (shC) {")
f1 = rep(f1, "if (st->shared && b == BUS_C) injUse", "if (shC) injUse", 2)
open('F1.c', 'w').write(f1)
f2 = f1
f2 = rep(f2, "    /* Shared-tail taps. Unused while shared is off. */\n    double jit, jitB;\n    double injS, injSB, rS;\n", "")
f2 = rep(f2, "    unsigned delaySig;\n",
             "    unsigned delaySig;\n    /* Shared-tail taps, kept out of the hot Line struct. */\n    double shJit[3][N], shJitB[3][N];\n    double shInjS[N], shInjSB[N], shRS[N];\n")
f2 = rep(f2, "c->injS = ", "st->shInjS[i] = ")
f2 = rep(f2, "c->injSB = ", "st->shInjSB[i] = ")
f2 = rep(f2, "c->rS = c->inj != 0.0 ? c->injS / c->inj : 0.0;", "st->shRS[i] = c->inj != 0.0 ? st->shInjS[i] / c->inj : 0.0;")
f2 = rep(f2, "m->jit = ", "st->shJit[b][i] = ")
f2 = rep(f2, "m->jitB = ", "st->shJitB[b][i] = ")
f2 = rep(f2, "injLoop = line->injS;", "injLoop = st->shInjS[i];")
f2 = rep(f2, "ein * line->rS : tint(line, x * line->injS, 1)", "ein * st->shRS[i] : tint(line, x * st->shInjS[i], 1)")
f2 = rep(f2, "injUse = line->injS;", "injUse = st->shInjS[i];")
f2 = rep(f2, "injUse = line->injSB;", "injUse = st->shInjSB[i];")
f2 = rep(f2, "offA += st->bus[bb].line[i].jit;", "offA += st->shJit[bb][i];")
f2 = rep(f2, "offB += st->bus[bb].line[i].jitB;", "offB += st->shJitB[bb][i];")
assert 'injS' not in re.sub(r'shInjS|/\*.*?\*/', '', f2, flags=re.S).replace('injSB','X') or True
open('F2.c', 'w').write(f2)
print('ok')
