"""Apply the SOS (biquad-cascade) colour path to a live_stereo.c (in place). Idempotent guard."""
import sys
p = sys.argv[1]; s = open(p).read()
assert 'irSos' not in s, 'already patched'
def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:60], s.count(a)); s = s.replace(a, b)
rep("    MAX_FILT = 112,\n", "    MAX_FILT = 112,\n    MAX_SOS = 6,\n")
rep("    int seen;\n    float prev[PART];\n} Filt;", "    int seen;\n    float prev[PART];\n    double sz[MAX_SOS][2];   /* SOS colour state (TDF-II), used when irSos[ir] > 0 */\n} Filt;")
rep("    int irNpart[MAX_IRS];\n", "    int irNpart[MAX_IRS];\n    int irSos[MAX_IRS];                 /* >0: colour entry is a K-biquad cascade, not an FIR */\n    double sos[MAX_IRS][MAX_SOS * 5];   /* b0 b1 b2 a1 a2 per section (a0 = 1) */\n")
rep("""static void design_ir(LiveStereo *st, int ir, const float *src, int len) {
    int p, npart, i, base;
""", """/* Colour entry format: an FIR impulse, or an SOS record [-2011, K, (b0 b1 b2 a1 a2) x K].
 * The magic -2011 cannot start a real colour FIR (|h[0]| <= a few). */
static int design_sos(LiveStereo *st, int ir, const float *src, int len) {
    int k, j;
    if (len < 7 || src[0] != -2011.0f) return 0;
    k = (int)src[1];
    if (k > MAX_SOS) k = MAX_SOS;
    if (k > (len - 2) / 5) k = (len - 2) / 5;
    if (k < 1) return 0;
    for (j = 0; j < 5 * k; j++) st->sos[ir][j] = (double)src[2 + j];
    st->irSos[ir] = k;
    st->irLen[ir] = len;
    st->irNpart[ir] = 1;
    return 1;
}

static void design_ir(LiveStereo *st, int ir, const float *src, int len) {
    int p, npart, i, base;
    st->irSos[ir] = 0;
    if (design_sos(st, ir, src, len)) return;
""")
rep("""    for (i = 0; i < MAX_FILT; i++) {
        ls_zero(st->filt[i].prev, PART * (int)sizeof(float));
""", """    for (i = 0; i < MAX_FILT; i++) {
        ls_zero(st->filt[i].prev, PART * (int)sizeof(float));
        ls_zero(st->filt[i].sz, (int)sizeof(st->filt[i].sz));
""")
rep("""        f->seen = 1;
        {
            int fi = freeSlot;""", """        f->seen = 1;
        if (st->irSos[ir] <= 0) {
            int fi = freeSlot;""")
rep("""static void run_fir(LiveStereo *st, Filt *f, const float *in, float *out) {
    int i, p, base, npart, pos, silent;
    float *hre, *him, *xre, *xim;
    silent = 1;""", """/* K biquads in series, transposed direct form II, double state. Same causal minimum-phase
 * response as the FIR it replaces (fitted server-side to the same relative_db). */
static void run_sos(LiveStereo *st, Filt *f, const float *in, float *out) {
    int k = st->irSos[f->ir], s, i, silent = 1;
    const double *c = st->sos[f->ir];
    double buf[PART];
    for (i = 0; i < PART; i++) {
        if (in[i] != 0.0f) { silent = 0; break; }
    }
    if (silent) {
        double m = 0.0;
        for (s = 0; s < k; s++) {
            double a = f->sz[s][0], b = f->sz[s][1];
            m += (a < 0 ? -a : a) + (b < 0 ? -b : b);
        }
        if (m < 1.0e-20) {
            for (s = 0; s < k; s++) { f->sz[s][0] = 0; f->sz[s][1] = 0; }
            for (i = 0; i < PART; i++) out[i] = 0;
            return;
        }
    }
    for (i = 0; i < PART; i++) buf[i] = (double)in[i];
    for (s = 0; s < k; s++) {
        double b0 = c[5 * s], b1 = c[5 * s + 1], b2 = c[5 * s + 2], a1 = c[5 * s + 3], a2 = c[5 * s + 4];
        double z1 = f->sz[s][0], z2 = f->sz[s][1];
        for (i = 0; i < PART; i++) {
            double x = buf[i];
            double y = b0 * x + z1;
            z1 = b1 * x - a1 * y + z2;
            z2 = b2 * x - a2 * y;
            buf[i] = y;
        }
        if (z1 < 1.0e-30 && z1 > -1.0e-30) z1 = 0;
        if (z2 < 1.0e-30 && z2 > -1.0e-30) z2 = 0;
        f->sz[s][0] = z1;
        f->sz[s][1] = z2;
    }
    for (i = 0; i < PART; i++) out[i] = (float)buf[i];
}

static void run_fir(LiveStereo *st, Filt *f, const float *in, float *out) {
    int i, p, base, npart, pos, silent;
    float *hre, *him, *xre, *xim;
    if (st->irSos[f->ir] > 0) { run_sos(st, f, in, out); return; }
    silent = 1;""")
open(p, 'w').write(s)
print('patched', p)
