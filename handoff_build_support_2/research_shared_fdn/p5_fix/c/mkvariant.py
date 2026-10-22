"""variant.c = live_stereo_1840.c + shared-loop-only research switches (off path untouched by construction:
every change sits behind st->shared, or in shared_prepare which only runs when shared is on)."""
s = open('live_stereo_1840.c').read()
def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:60], s.count(a)); s = s.replace(a, b)
rep("    double jit, jitB;\n", "    double jit, jitB;\n    double osg, osgB;\n")
rep("static double shared_jit(double d) {",
"""#ifndef SH_JIT_US
#define SH_JIT_US 300.0
#endif
#ifndef SH_JSEED
#define SH_JSEED 1u
#endif
#ifndef SH_OSQ
#define SH_OSQ 0
#endif
#ifndef SH_OSSEED
#define SH_OSSEED 7u
#endif
static double shared_hash(double d, unsigned seed) {
    unsigned u = (unsigned)(d * 16.0 + 0.5) + 0x9e3779b9U * seed;
    u ^= u >> 16; u *= 0x7feb352dU; u ^= u >> 15; u *= 0x846ca68bU; u ^= u >> 16;
    return (double)u * (1.0 / 4294967296.0);
}
static double g_dvShared[32];
static const double *g_dvp;
static double shared_jit(double d) {""")
rep("    double js = 300.0e-6 * (double)st->sr;", "    double js = SH_JIT_US * 1.0e-6 * (double)st->sr;")
rep("            m->jitB = js * shared_jit(st->bus[key].line[i].delayBT + (b == BUS_C ? 0.5 : 0.0));\n",
"""            m->jitB = js * shared_jit(st->bus[key].line[i].delayBT + (b == BUS_C ? 0.5 : 0.0));
#if SH_JSEED != 1
            m->jit = js * shared_hash(st->bus[key].line[i].delayT + (b == BUS_C ? 0.5 : 0.0), SH_JSEED);
            m->jitB = js * shared_hash(st->bus[key].line[i].delayBT + (b == BUS_C ? 0.5 : 0.0), SH_JSEED);
#endif
            m->osg = 1.0; m->osgB = 1.0;
#if SH_OSQ > 0
            if (b != BUS_C) {
                m->osg = shared_hash(st->bus[key].line[i].delayT, SH_OSSEED) < SH_OSQ / 1000.0 ? -1.0 : 1.0;
                m->osgB = shared_hash(st->bus[key].line[i].delayBT, SH_OSSEED) < SH_OSQ / 1000.0 ? -1.0 : 1.0;
            }
#endif
#ifdef SH_TAPD
            m->osg *= CSIGN_D_[i]; m->osgB *= CSIGN_D_[i];
#endif
""")
# forward-declare the table for SH_TAPD
rep("static int centre_empty(const LiveStereo *st) {",
"""static const double CSIGN_D_[32] = {
    1.0, -1.0, -1.0, -1.0, -1.0, -1.0, 1.0, -1.0, -1.0, 1.0, -1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
    -1.0, 1.0, 1.0, 1.0, -1.0, 1.0, 1.0, 1.0, -1.0, 1.0, 1.0, 1.0, -1.0, 1.0, 1.0, 1.0 };
static int centre_empty(const LiveStereo *st) {""")
rep("        for (k = 0; k < 32; k++) a[k] *= CSIGN_D[k];", "        const double *dv = g_dvp ? g_dvp : CSIGN_D;\n        for (k = 0; k < 32; k++) a[k] *= dv[k];")
rep("            bus_sample(st, BUS_C, x, xA, xB, split, t, hn, doFwht, doDiff);\n",
"""            {
#ifdef SH_PLAINH
                int gs = g_csign; g_csign = 0;
#endif
#ifdef SH_DVSEED
                if (!g_dvp) { unsigned u = SH_DVSEED; int k; for (k = 0; k < 32; k++) { u = u * 1664525u + 1013904223u; g_dvShared[k] = (u >> 31) ? -1.0 : 1.0; } g_dvShared[0] = 1.0; }
                g_dvp = g_dvShared;
#endif
                bus_sample(st, BUS_C, x, xA, xB, split, t, hn, doFwht, doDiff);
#ifdef SH_PLAINH
                g_csign = gs;
#endif
                g_dvp = 0;
            }
""")
rep("                        st->yBlk[bb][i][t] = st->bus[bb].shG * (double)st->ring[BUS_L][i][ia * LANES + LANE_FDN];\n                        if (split) st->yBlkB[bb][i][t] = st->bus[bb].shGB * (double)st->ring[BUS_L][i][ib * LANES + LANE_FDNB];",
    "                        st->yBlk[bb][i][t] = st->bus[bb].line[i].osg * st->bus[bb].shG * (double)st->ring[BUS_L][i][ia * LANES + LANE_FDN];\n                        if (split) st->yBlkB[bb][i][t] = st->bus[bb].line[i].osgB * st->bus[bb].shGB * (double)st->ring[BUS_L][i][ib * LANES + LANE_FDNB];")
open('variant.c', 'w').write(s); print('ok')
