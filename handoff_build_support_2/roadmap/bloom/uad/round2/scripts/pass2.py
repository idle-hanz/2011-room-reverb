# Pass 2 jobs (calibrated from pass-1 staircases). Run on the box: python3 pass2.py > jobs_pass2.json
import json, csv, collections, numpy as np, units as U
AN = "/workspace/uad2/an"
R = list(csv.DictReader(open(AN + "/comp_colour_steps.csv")))
D = collections.defaultdict(list)
for r in R: D[(r["setting"], int(r["freq"]))].append((float(r["in_dbfs"]), float(r["gr_db"])))
def lvl_for_gr(setting, target, freq=1000):
    v = D[(setting, freq)] or D[(setting, 1000)]
    L = np.array([a for a, b in v]); g = np.array([b for a, b in v])
    for i in range(1, len(g)):
        if g[i - 1] < target <= g[i]:
            return float(L[i - 1] + (target - g[i - 1]) / (g[i] - g[i - 1]) * (L[i] - L[i - 1]))
    return None
def probe_level(setting, freq=1000):
    v = D[(setting, freq)] or D[(setting, 1000)]
    k = 0
    while k + 1 < len(v) and v[k + 1][1] < 0.3: k += 1
    return v[k][0] - 3.0
J = []
def add(id_, setting, params=None, **kw):
    pl, pr, st, role = U.COMP[setting] if setting in U.COMP else (None, None, None, None)
    p = dict(pr); p.update(params or {})
    j = {"id": id_, "plugin": kw.pop("plugin", pl), "params": p}; j.update(kw); J.append(j)

# new setting for Nuke-preset comparison: Distressor Nuke, attack 4.5, release 2.5, detector HP (room recipe + 100 Hz SC HPF)
NUKE_ROOM = dict(U.dis("NUKE", 4.5, 2.5, det="HP"))
U.COMP["dis_nuke_room"] = (U.DIS, NUKE_ROOM, 1.5, "S")
add("c1k_dis_nuke_room", "dis_nuke_room", input="st_1000_1p5.npy", keep=[[ (i + 1) * 72000 - 24000, (i + 1) * 72000] for i in range(20)])
for L in (-30, -18, -6, 6):
    add("cess_dis_nuke_room_%+d" % L, "dis_nuke_room", input="cess.npy", gain_db=float(L))
    add("cess_fc_t5_%+d" % L, "fc_t5", input="cess.npy", gain_db=float(L))

# (b) program material through the preset-reference settings
TARGET = {"la2as_pr50": 6, "ssl_4_auto": 4, "fet_all": 10, "dis_nuke_room": 18, "fc_t5": 6, "mvm_comp": 4}
CAL = {"dis_nuke_room": "dis_nuke"}
PROGS = ["drums", "vocal", "bass", "tail", "mix", "wetmix"]
prog_levels = {}
for s, tg in TARGET.items():
    L0 = lvl_for_gr(CAL.get(s, s), tg)
    prog_levels[s] = L0
    for pk in PROGS:
        for k, off in (("a", 0.0), ("b", 8.0)):
            add("prog_%s_%s_%s" % (s, pk, k), s, input="prog_%s.npy" % pk, gain_db=round(L0 + off, 2))

# (c) GR-depth burst sweep (store envelope)
TAIL = {"fc_t5": 20.0, "la3a_pr5": 10.0, "dis_10": 15.0, "mvm_lim": 10.0, "fc_t2": 6.0}
PD = ["la2as_pr50", "la2ag_pr50", "la2_pr50", "la3a_pr5", "dis_10", "ssl_4_auto", "fc_t5", "ln_4", "mvm_lim"]
BU = ["fc_t2", "fc_t5", "ssl_4_auto", "la2as_pr50", "la2ag_pr50", "la2_pr50", "la3a_pr5", "ln_4", "reva_4", "fet_all", "dis_6", "dis_nuke", "dis_10", "dbx_4", "mvm_lim"]
for s in BU:
    pr = probe_level(s)
    for dep in (5, 10, 20):
        Lb = lvl_for_gr(s, dep)
        if Lb is None or Lb > 12: continue
        lens = [1.0] + ([0.05, 0.3, 5.0] if (s in PD and dep in (5, 20)) else [])
        for bl in lens:
            add("bd_%s_%d_%s" % (s, dep, str(bl).replace('.', 'p')), s, store="env",
                spec={"kind": "burst", "probe_db": round(pr, 2), "burst_db": round(Lb, 2), "pre_s": 1.0, "burst_s": bl, "tail_s": TAIL.get(s, 6.0)})

# (d) sub-ms attack: 5 kHz quadrature pair
QA = [("ln_4", {"attack": a}, "ln_4") for a in ("1.00", "4.00", "7.00")] + [("ln_20", {"attack": "7.00"}, "ln_20")] + \
     [("reva_4", {"attack": a}, "reva_4") for a in ("1.00", "7.00")] + [("fet_all", {"attack": a}, "fet_all") for a in (1.0, 4.0, 7.0)] + \
     [("fet_4", {"attack": 7.0}, "fet_4")] + \
     [("fc_t2", {"l_timecnst": float(t), "r_timecnst": float(t)}, "fc_t2") for t in range(1, 7)] + \
     [("dis_6", {"attack": a}, "dis_6") for a in (0.0, 1.0, 2.0, 3.0, 5.0)] + [("dis_nuke", {"attack": a}, "dis_nuke") for a in (0.0, 4.5)] + \
     [("ssl_4_auto", {"attack": a}, "ssl_4_auto") for a in (0.1, 0.3, 1.0, 3.0, 10.0, 30.0)] + \
     [("dbx_4", {}, "dbx_4"), ("la2as_pr50", {}, "la2as_pr50"), ("la2ag_pr50", {}, "la2ag_pr50"), ("la2_pr50", {}, "la2_pr50"), ("la3a_pr5", {}, "la3a_pr5")] + \
     [("mvm_lim", {"l_attack": a, "r_attack": a}, "mvm_lim") for a in (0.0, 5.0, 10.0)]
for i, (s, over, cal) in enumerate(QA):
    hi = lvl_for_gr(cal, 10, 5000) or lvl_for_gr(cal, 10)
    lo = probe_level(cal, 5000)
    tag = "%s_%s" % (s, "_".join("%s%s" % (k[:3], v) for k, v in over.items()) or "def")
    for ph, nm in ((0.0, "s"), (np.pi / 2, "c")):
        add("qa_%s_%s" % (tag, nm), s, over, spec={"kind": "quad", "fc": 5000.0, "lo_db": round(lo, 2), "hi_db": round(hi, 2), "phase": ph,
                                                     "t_step": 0.5, "t_hi": 0.3, "t_after": 0.7})

# (e) side-chain frequency response (fixed-level frequency staircase at the 1 kHz / 10 dB-GR level)
FREQS = [30, 50, 80, 120, 200, 300, 500, 1000, 2000, 3000, 5000, 8000, 12000, 16000]
SC = [("ssl_4_auto", {"sc_filter": "Off"}), ("ssl_4_auto", {"sc_filter": "~100"}), ("ssl_4_auto", {"sc_filter": "~250"}),
      ("dis_6", {"detector": "Norm"}), ("dis_6", {"detector": "HP"}), ("dis_6", {"detector": "Emp"}), ("dis_6", {"detector": "HP+Emp"}),
      ("fc_t2", {}), ("fc_t2", {"l_sc_filt": "~100", "r_sc_filt": "~100"}), ("fc_t2", {"l_sc_filt": "~250", "r_sc_filt": "~250"}),
      ("la2as_pr50", {"emphasis": "~0"}), ("la2as_pr50", {"emphasis": "~50"}), ("la2as_pr50", {"emphasis": "~100"}),
      ("la3a_pr5", {"hf_emphasis": "~0"}), ("la3a_pr5", {"hf_emphasis": "~100"}),
      ("ln_4", {"sc_filter": False}), ("ln_4", {"sc_filter": True}), ("mvm_lim", {}), ("mvm_lim", {"l_hp_sc_filt": "In", "r_hp_sc_filt": "In"}),
      ("dbx_4", {"sc_filter": False}), ("dbx_4", {"sc_filter": True})]
for s, over in SC:
    L10 = lvl_for_gr(s, 10); st = U.COMP[s][2]
    tag = "_".join("%s%s" % (k.replace('_', '')[:6], str(v).replace('~', '').replace('+', 'p')) for k, v in over.items()) or "def"
    add("sc_%s_%s" % (s, tag), s, over, spec={"kind": "fstair", "freqs": FREQS, "level_db": round(L10, 2), "step_s": st},
        fstair={"freqs": FREQS, "step_s": st})

# (f) stereo link / one channel only: L 1 kHz at the 10 dB-GR level for 2 s, R 3 kHz probe 10 dB below threshold throughout
LK = [("fc_t2", {}), ("fc_t2", {"sc_link": "Unlink", "ctrl_link": "Unlink"}), ("fc_t2", {"agc_matrix": "L-V"}),
      ("ssl_4_auto", {}), ("la2as_pr50", {}), ("la3a_pr5", {}), ("ln_4", {}), ("fet_all", {}),
      ("dis_6", {"detector": "Norm"}), ("dis_6", {"detector": "Link"}), ("dbx_4", {}),
      ("mvm_lim", {}), ("mvm_lim", {"sc_link": "Unlink", "ctrl_link": "Unlink"}), ("mvm_lim", {"in_matrix": "M-S", "out_matrix": "M-S"})]
for s, over in LK:
    L10 = lvl_for_gr(s, 10); pr = probe_level(s) - 7.0
    tag = "_".join("%s%s" % (k.replace('_', '')[:6], str(v).replace('-', '')) for k, v in over.items()) or "def"
    add("lk_%s_%s" % (s, tag), s, over, spec={"kind": "link", "l_db": round(L10, 2), "r_db": round(pr, 2), "on_s": 2.0, "off_s": 1.5})
if __name__ == "__main__":
    import sys
    json.dump(J, open(sys.argv[1] if len(sys.argv) > 1 else "/workspace/uad2/jobs/jobs_pass2.json", "w"), indent=0)
    json.dump({"prog_levels": prog_levels, "NUKE_ROOM": NUKE_ROOM}, open(AN + "/pass2_cal.json", "w"), indent=1)
    import collections as C
    print(len(J), C.Counter(j["id"].split("_")[0] for j in J))
