# Pass 1: inputs + jobs that need no calibration. Run "python pass1.py write <inputs_dir> <jobs.json>" on the PC.
import sys, os, json, numpy as np
import siglib as S, units as U
SR = S.SR
LV = list(range(-45, 13, 3))            # 20 compressor staircase levels (dBFS peak)
LVF = list(range(-42, 13, 6))           # 10 levels for FR-at-GR
PLV = list(range(-90, 1, 3))            # 31 pre levels
ESS_T = 6.0; ESS_PRE = 1.5; ESS_TAIL = 0.5
CESS_LV = [-30, -18, -6, 6]
CLIP_IN = {"neve": -36, "u610a": -57, "u610b": -54, "api": -36, "sslE": -24, "manley": -24}

def inputs():
    """name -> (callable producing float array, keep ranges or None, meta)"""
    I = {}
    for st in (1.5, 2.0, 2.5):
        for f in (1000.0, 100.0, 5000.0):
            nm = "st_%d_%s" % (int(f), str(st).replace('.', 'p'))
            I[nm] = (lambda f=f, st=st: S.stair(f, LV, st), S.stair_keep(LV, st), {"kind": "stair", "f": f, "levels": LV, "step_s": st})
        I["smpte_%s" % str(st).replace('.', 'p')] = (lambda st=st: S.twotone_stair(60.0, 7000.0, 4.0, LV, st), S.stair_keep(LV, st), {"kind": "smpte", "levels": LV, "step_s": st})
        I["ccif_%s" % str(st).replace('.', 'p')] = (lambda st=st: S.twotone_stair(19000.0, 20000.0, 1.0, LV, st), S.stair_keep(LV, st), {"kind": "ccif", "levels": LV, "step_s": st})
    x, keep = S.tone_sweep_stair(LVF, with_sweep=True)
    I["frs_sw"] = (lambda: S.tone_sweep_stair(LVF, with_sweep=True)[0], keep, {"kind": "frs", "levels": LVF, "with_sweep": True})
    I["frs_tone"] = (lambda: S.tone_sweep_stair(LVF, with_sweep=False)[0], keep, {"kind": "frs", "levels": LVF, "with_sweep": False})
    # compressor ESS with a 1.5 s 1 kHz settle tone at the same peak level, unit-peak (scale via gain_db)
    def cess():
        sw, _ = S.ess(ESS_T); t = np.arange(int(ESS_PRE * SR)) / SR
        return np.concatenate([np.sin(2 * np.pi * 1000 * t), sw, np.zeros(int(ESS_TAIL * SR))])
    I["cess"] = (cess, None, {"kind": "cess", "pre_s": ESS_PRE, "T": ESS_T})
    # pre signals
    for f in (20.0, 30.0, 50.0, 200.0):
        I["pst_%d" % int(f)] = (lambda f=f: S.stair(f, PLV, 1.0), S.stair_keep(PLV, 1.0), {"kind": "stair", "f": f, "levels": PLV, "step_s": 1.0})
    I["psmpte"] = (lambda: S.twotone_stair(60.0, 7000.0, 4.0, PLV, 1.0), S.stair_keep(PLV, 1.0), {"kind": "smpte", "levels": PLV, "step_s": 1.0})
    I["pccif"] = (lambda: S.twotone_stair(19000.0, 20000.0, 1.0, PLV, 1.0), S.stair_keep(PLV, 1.0), {"kind": "ccif", "levels": PLV, "step_s": 1.0})
    I["silence4"] = (lambda: np.zeros(4 * SR), None, {"kind": "silence"})
    def pess():
        sw, _ = S.ess(ESS_T); return np.concatenate([np.zeros(int(0.2 * SR)), sw, np.zeros(int(ESS_TAIL * SR))])
    I["pess"] = (pess, None, {"kind": "pess", "pre_s": 0.2, "T": ESS_T})
    # burst recovery (unit = 0 dB at the 1 % point): 1 s ref tone at -24, 0.5 s burst at 0 dB, 4 s tone at -24
    def brec(fb):
        n0, nb, n1 = SR, SR // 2, 4 * SR; t = np.arange(n0 + nb + n1) / SR
        ref = S.db2a(-24) * np.sin(2 * np.pi * 1000 * t)
        x = ref.copy(); x[n0:n0 + nb] = np.sin(2 * np.pi * fb * t[n0:n0 + nb])
        return x
    I["brec_1k"] = (lambda: brec(1000.0), None, {"kind": "brec", "fb": 1000.0})
    I["brec_40"] = (lambda: brec(40.0), None, {"kind": "brec", "fb": 40.0})
    for i, seed in enumerate((21, 22, 23)):
        I["noise_%d" % i] = (lambda seed=seed: S.bandnoise(6.0, 0.0, seed), None, {"kind": "noise", "seed": seed, "rms_db": 0.0})
    import prog
    P = prog.all_programs()
    for k, v in P.items():
        I["prog_" + k] = (lambda v=v: v, None, {"kind": "prog", "name": k})
    return I

def jobs():
    J = []
    def add(id_, plugin, params, inp, gain_db=None, keep=True, **kw):
        j = {"id": id_, "plugin": plugin, "params": params, "input": inp + ".npy"}
        if gain_db is not None: j["gain_db"] = gain_db
        j.update(kw); J.append(j)
    I = inputs()
    def keepof(n):
        return I[n][1]
    for name, (pl, pr, st, role) in U.COMP.items():
        s = str(st).replace('.', 'p')
        add("c1k_" + name, pl, pr, "st_1000_" + s, keep=keepof("st_1000_" + s))
        J[-1]["keep"] = keepof("st_1000_" + s)
        if role in ("P", "N") or name in ("dis_1_d2", "dis_1_d3", "dis_6_d2", "dis_6_d3"):
            for f in (100, 5000):
                add("c%d_" % f + name, pl, pr, "st_%d_%s" % (f, s)); J[-1]["keep"] = keepof("st_%d_%s" % (f, s))
            for k in ("smpte", "ccif"):
                add("c%s_" % k + name, pl, pr, "%s_%s" % (k, s)); J[-1]["keep"] = keepof("%s_%s" % (k, s))
            for L in CESS_LV:
                add("cess_%s_%+d" % (name, L), pl, pr, "cess", gain_db=float(L))
        if role == "P":
            for v in ("sw", "tone"):
                add("cfr%s_" % v + name, pl, pr, "frs_" + v); J[-1]["keep"] = keepof("frs_" + v)
    for name, (pl, pr, r1, gains) in U.PRES.items():
        c = CLIP_IN[name]
        for f in (20, 30, 50, 200):
            add("p%d_%s" % (f, name), pl, pr, "pst_%d" % f); J[-1]["keep"] = keepof("pst_%d" % f)
        for k in ("smpte", "ccif"):
            add("p%s_%s" % (k, name), pl, pr, "p" + k); J[-1]["keep"] = keepof("p" + k)
        for gname, gp in gains:
            add("pnoise_%s_%s" % (name, gname.replace(' ', '').replace('+', 'p').replace('-', 'm')), pl, gp, "silence4")
        for k in ("1k", "40"):
            add("pbrec_%s_%s" % (k, name), pl, pr, "brec_" + k, gain_db=float(c))
        for rel in (-30, -20, -10, -3):
            add("pess_%s_%+d" % (name, rel), pl, pr, "pess", gain_db=float(c + rel))
        for i, rel in enumerate((-20, -12, -6)):   # noise RMS rel. to the 1 % sine-peak point
            add("pnz_%s_%+d" % (name, rel), pl, pr, "noise_%d" % i, gain_db=float(c + rel))
        for pk in ("mix", "vocal", "drums", "wetmix"):
            for rel in (-6, 0):
                add("pprog_%s_%s_%+d" % (name, pk, rel), pl, pr, "prog_" + pk, gain_db=float(c + rel))
    return J

if __name__ == "__main__":
    if sys.argv[1] == "write":
        d = sys.argv[2]; os.makedirs(d, exist_ok=True)
        for k, (fn, keep, meta) in inputs().items():
            p = os.path.join(d, k + ".npy")
            if not os.path.exists(p): np.save(p, np.asarray(fn(), np.float32))
        json.dump(jobs(), open(sys.argv[3], "w"))
        print("inputs", len(inputs()), "jobs", len(jobs()))
    else:
        J = jobs(); print(len(J))
        tot = 0
        I = inputs()
        for j in J:
            n = len(I[j["input"][:-4]][0]()) if False else 0
