# Unit/setting definitions for round 2 (UAD knob values; strings for enums, floats for continuous knobs).
FC = "uaudio_fairchild_670"; SSL = "uaudio_ssl_g_bus_compressor"; LAS = "uaudio_teletronix_la-2a_silver"
LAG = "uaudio_teletronix_la-2a_gray"; LA2 = "uaudio_teletronix_la-2"; LA3 = "uaudio_la3a"
LN = "uaudio_ua_1176ln_rev_e"; RA = "uaudio_ua_1176_rev_a"; FET = "uaudio_ua_1176"; DIS = "uaudio_distressor"
DBX = "uaudio_dbx_160"; MVM = "uaudio_manley_variable_mu"
def fc(tc=2.0, thr=5.0, **k):
    d = {"l_input": 0.0, "r_input": 0.0, "l_thresh": thr, "r_thresh": thr, "l_timecnst": float(tc), "r_timecnst": float(tc)}; d.update(k); return d
def ssl(ratio="4:1", att=10.0, rel="Auto", thr=0.0, **k):
    d = {"thresh": thr, "make_up": 0.0, "ratio": ratio, "attack": att, "release": rel}; d.update(k); return d
def la2a(pr="50", mode="Comp", **k):
    d = {"peak_reduct": pr, "gain": "30", "comp_limit": mode}; d.update(k); return d
def la2(pr="50", **k):
    d = {"peak_reduct": pr, "gain": "30"}; d.update(k); return d
def la3(pr=5.0, mode="Comp", **k):
    d = {"peak_reduction": pr, "gain": 5.0, "comp_limit": mode}; d.update(k); return d
def u76(ratio="4:1", att="4.00", rel=5.0, inp=-40.0, out=-20.0, **k):
    d = {"input": inp, "output": out, "ratio": ratio, "attack": att, "release": rel}; d.update(k); return d
def fet(ratio="ALL", att=4.0, rel=5.0, inp=-20.0, out=-20.0, **k):
    d = {"input": inp, "output": out, "ratio": ratio, "attack": att, "release": rel}; d.update(k); return d
def dis(ratio="6:1", att=5.0, rel=3.0, det="Norm", audio="Norm", **k):
    d = {"input": 5.0, "ratio": ratio, "attack": att, "release": rel, "output": 5.0, "detector": det, "audio": audio}; d.update(k); return d
def dbx(thr=-30.0, comp=" 4.0:1", **k):
    d = {"thresh": thr, "compress": comp, "gain": 0.0}; d.update(k); return d
def mvm(inp=5.0, thr=5.0, mode="Comp", rec="Fast", att=5.0, **k):
    d = {"dual_input": inp, "l_thresh": thr, "r_thresh": thr, "l_recovery": rec, "r_recovery": rec, "l_attack": att, "r_attack": att,
         "l_comp_lim": mode, "r_comp_lim": mode}; d.update(k); return d

# name: (plugin, params, step_s, role) ; role: 'P' primary (1k+100+5k, IMD, FR, ESS), 'N' no-compression twin of a primary, 'S' extra setting (1k only)
COMP = {
 "fc_t2":     (FC, fc(2.0), 2.0, "P"),
 "fc_t5":     (FC, fc(5.0), 2.5, "S"),
 "fc_t2_thr8":(FC, fc(2.0, 8.0), 2.0, "S"),
 "fc_t2_hr8": (FC, fc(2.0, headroom="8.0"), 2.0, "S"),
 "fc_t2_latvert": (FC, fc(2.0, agc_matrix="L-V"), 2.0, "S"),
 "fc_nocomp": (FC, fc(2.0, 0.0), 2.0, "N"),
 "ssl_4_auto":(SSL, ssl("4:1"), 1.5, "P"),
 "ssl_2_auto":(SSL, ssl("2:1"), 1.5, "S"),
 "ssl_10_auto":(SSL, ssl("10:1"), 1.5, "S"),
 "ssl_4_a01_r01":(SSL, ssl("4:1", 0.1, "0.1 s"), 1.5, "S"),
 "ssl_4_a30_r12":(SSL, ssl("4:1", 30.0, "1.2 s"), 2.0, "S"),
 "ssl_4_hr8": (SSL, ssl("4:1", headroom="8.0"), 1.5, "S"),
 "ssl_nocomp":(SSL, ssl("4:1", thr=15.0), 1.5, "N"),
 "la2as_pr50":(LAS, la2a("50"), 2.0, "P"),
 "la2as_pr30":(LAS, la2a("30"), 2.0, "S"),
 "la2as_pr70":(LAS, la2a("70"), 2.0, "S"),
 "la2as_lim50":(LAS, la2a("50", "Limit"), 2.0, "S"),
 "la2as_nocomp":(LAS, la2a("0"), 2.0, "N"),
 "la2ag_pr50":(LAG, la2a("50"), 2.0, "P"),
 "la2ag_nocomp":(LAG, la2a("0"), 2.0, "N"),
 "la2_pr50":  (LA2, la2("50"), 2.0, "P"),
 "la2_nocomp":(LA2, la2("0"), 2.0, "N"),
 "la3a_pr5":  (LA3, la3(5.0), 2.0, "P"),
 "la3a_lim5": (LA3, la3(5.0, "Limit"), 2.0, "S"),
 "la3a_nocomp":(LA3, la3(0.0), 2.0, "N"),
 "ln_4":      (LN, u76("4:1"), 1.5, "P"),
 "ln_20":     (LN, u76("20:1"), 1.5, "S"),
 "ln_4_20":   (LN, u76("4:1+20:1"), 1.5, "S"),
 "ln_4_fastest":(LN, u76("4:1", "7.00", 7.0), 1.5, "S"),
 "ln_4_slowest":(LN, u76("4:1", "1.00", 1.0), 2.0, "S"),
 "ln_nocomp": (LN, u76("4:1", "OFF"), 1.5, "N"),
 "reva_4":    (RA, u76("4:1"), 1.5, "P"),
 "reva_nocomp":(RA, u76("4:1", "OFF"), 1.5, "N"),
 "fet_all":   (FET, fet("ALL"), 1.5, "P"),
 "fet_4":     (FET, fet("4:1"), 1.5, "S"),
 "fet_all_a7r7":(FET, fet("ALL", 7.0, 7.0), 1.5, "S"),
 "dis_6":     (DIS, dis("6:1"), 1.5, "P"),
 "dis_3":     (DIS, dis("3:1"), 1.5, "S"),
 "dis_nuke":  (DIS, dis("NUKE"), 1.5, "P"),
 "dis_10":    (DIS, dis("10:1"), 2.5, "S"),
 "dis_6_d2":  (DIS, dis("6:1", audio="Dist 2"), 1.5, "S"),
 "dis_6_d3":  (DIS, dis("6:1", audio="Dist 3"), 1.5, "S"),
 "dis_1_norm":(DIS, dis("1:1"), 1.5, "N"),
 "dis_1_d2":  (DIS, dis("1:1", audio="Dist 2"), 1.5, "N"),
 "dis_1_d3":  (DIS, dis("1:1", audio="Dist 3"), 1.5, "N"),
 "dbx_4":     (DBX, dbx(), 1.5, "P"),
 "dbx_inf":   (DBX, dbx(comp="Inf:1"), 1.5, "S"),
 "dbx_nocomp":(DBX, dbx(0.0, " 1.0:1"), 1.5, "N"),
 "mvm_lim":   (MVM, mvm(mode="Limit"), 2.0, "P"),
 "mvm_comp":  (MVM, mvm(), 2.0, "S"),
 "mvm_hot":   (MVM, mvm(10.0, 10.0, "Limit"), 2.0, "S"),
 "mvm_nocomp":(MVM, mvm(mode="Limit", l_bypass="Bypass", r_bypass="Bypass"), 2.0, "N"),
 "mvm_thr0":  (MVM, mvm(thr=0.0, mode="Limit"), 2.0, "N"),
}
# primary -> its no-compression twin
TWIN = {"fc_t2": "fc_nocomp", "ssl_4_auto": "ssl_nocomp", "la2as_pr50": "la2as_nocomp", "la2ag_pr50": "la2ag_nocomp",
        "la2_pr50": "la2_nocomp", "la3a_pr5": "la3a_nocomp", "ln_4": "ln_nocomp", "reva_4": "reva_nocomp", "fet_all": None,
        "dis_6": "dis_1_norm", "dis_nuke": "dis_1_norm", "dbx_4": "dbx_nocomp", "mvm_lim": "mvm_nocomp"}

NV = "uaudio_neve_1073"; A610 = "uaudio_610_a"; B610 = "uaudio_610_b"; API = "uaudio_api_vision_channel_strip"
SSLE = "uaudio_ssl_e_channel_strip"; MP = "uaudio_manley_preamp"
def neve(g="M -50 dB"): return {"input_select": "Mic", "impedance": "Hi", "pad": 0.0, "mic_gain": g, "eql": "Out", "hp_filt": "Off", "output": 0.0}
def a610(g="Hi"): return {"input_select": "Mic", "input_pad": "Off", "input_gain": g, "level": "0.0 dB", "output": "0.00 dB", "low_eq_gain": 0.0, "hi_eq_gain": 0.0}
def b610(g=0.0): return {"input_select": "(Mic) 500", "input_pad": "Off", "input_gain": g, "level": 10.0, "lo_eq_gain": 0.0, "hi_eq_gain": 0.0}
def api(g=45.0): return {"input_select": "Mic", "mic_gain": g, "pad": False, "cut_filter": "Off", "215_on": False, "235_on": False, "225_on": False, "eq_on": False}
def sslE(g=40.0): return {"input_select": "Mic", "mic_gain": g, "pad": False, "transformer": True, "dyn_in": "Out", "eq_in": "Out", "hp_freq": "Out", "lp_freq": "Out"}
def manp(g=50.0): return {"source_select": "Mic", "low_cut": "Off", "pad": 0.0, "gain": g, "input": 10.0, "transformer": "In", "output": 0.0}
# name: (plugin, params(mid gain), round-1 run prefix for 1 kHz, gains for noise)
PRES = {
 "neve": (NV, neve(), "neve_Mm50dB", [("M -30 dB", neve("M -30 dB")), ("M -50 dB", neve()), ("M -70 dB", neve("M -70 dB"))]),
 "u610a": (A610, a610(), "u610a_Hi", [("Lo", a610("Lo")), ("Hi", a610())]),
 "u610b": (B610, b610(), "u610b_0", [("-10", b610(-10.0)), ("0", b610()), ("+10", b610(10.0))]),
 "api": (API, api(), "api_45", [("30", api(30.0)), ("45", api()), ("60", api(60.0))]),
 "sslE": (SSLE, sslE(), "sslE_40", [("20", sslE(20.0)), ("40", sslE()), ("60", sslE(60.0))]),
 "manley": (MP, manp(), "manley_50", [("40", manp(40.0)), ("50", manp()), ("60", manp(60.0))]),
}
