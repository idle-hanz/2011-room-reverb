/* live_stereo — the Play block, one function.
 *
 * 32 lines stay 32 lines. The room loop is the worklet loop: diffuser
 * output y, then × g through the unscaled Hadamard, back into the allpass.
 * With Dffs, that feedback is the previous sample. Loop gain is the value sent in.
 * Measured mic colour (FIR impulse, or SOS record [-2011, K, b0 b1 b2 a1 a2 × K])
 * is applied on the way out and is not written
 * back into the delay. Direct is filtered, then × 0.55. Early left and
 * right join that source's FDN filters. Centre early stays uncoloured.
 * Source B is coloured with B's own map, then added to A. Speakers get
 * left and right.
 *
 * Each line stores FDN A, early A, FDN B, and early B together at one time
 * index. The ring is the 1000 ms cap plus a few samples for the fractional
 * read. Direct stays its own ring: its time is not the line time.
 *
 * Page build: zig cc -target wasm32-freestanding -O3 -msimd128 -nostdlib
 *   -ffreestanding -Wl,--no-entry -Wl,--export-memory -Wl,--export=live_stereo
 *   -Wl,--max-memory=1073741824
 *   -o software/static/wasm/live_stereo.wasm software/engine/live_stereo.c
 * Export every live_* the worklet calls, not only live_stereo.
 *
 * Room blob v1 (float, magic 1) is still accepted. Order after the magic:
 *   g, fdn_wet, direct_wet, early_wet, dry_gain, makeup, gain_a, gain_b,
 *   two, colour_on, mono, direct_index, max_delay_ms, snap, ignored_sr,
 *   mic g,pan,phase × L C R,
 *   peaking on,b0,b1,b2,a1,a2 × 3,
 *   per bus L C R:
 *     32 delay_ms, 32 inject, 32 dffs, 32 air_g, air_lp,
 *     32 × (shelf on,b0,b1,b2,a1,a2), dir_ms, dir_gain,
 *     the same block again for source B.
 *   then line_t60 (seconds; 0 = absorption off).
 * Blob v2: magic 2, major 2, minor, n_sections, total_len, then
 *   n_sections × {id, offset, length, section_version}.
 *   1 CORE = the v1 body without the magic, plus 8 reserved floats.
 *     Reserve 0 is hadamard_n. 8, 16, and 32 size the FWHT. Anything else
 *     stays 32, so a 32-line blob is unchanged. fwht8/16/32 and the matching
 *     diffuse copy are picked once per block. One-sample feedback, unity.
 *     Reserve 1 is loop_semantics. 1 = plain Hadamard (reaktor_parity).
 *     0 = column signs H·D inside fwht32. Reserves 2..7 are solo_mute[6], one float
 *     per face A–F. Those six floats are not an audio gate. FDN inject and
 *     Dffs stay un-gated. Solo/Mute is the SURF early gate.
 *   2 AIR = second shelf, 1152 floats, or length 0 (bypass).
 *   3 SURF length 0 (no Solo/Mute, no cascade: bit-exact)
 *     or 192 floats: early_gate for L, C, R, each 32 bank A then 32 bank B.
 *     0 silences that line's early read. xin and the FDN lane stay open.
 *     v1 appends [version=1, K_max] and per bank A,B × 32 lines: k_i then
 *     K_max × 5 normalised biquads (b0 b1 b2 a1 a2). Any other length is
 *     no cascade and no gate. The cascade is outside the loop. Parity sends
 *     no cascade. Flat cards omit it, so those blobs stay 0 or 192.
 *   4 SCATTER length 0 until a later phase.
 *   5 SRC_RAD length 0 (omni, the current sound) or 716 floats:
 *     rad_on_A, rad_on_B, then per source the diffuse shelf (7),
 *     direct L/C/R (3×10) and 32 image filters (32×10).
 *     Filters run on the write, before tint. The tail uses the diffuse shelf.
 *   6 SHARED one float, present only when the Live "shared tail" option is on.
 *     Missing section is off, so a default blob is unchanged. Binaural (empty
 *     centre) ignores it. Render never sends it.
 *   7 DESK six floats ll,lr,cl,cr,rl,rr. Present only when the speaker fold
 *     is not the 477 default. Missing section leaves side() on mic gain/pan/
 *     phase, so a default blob is unchanged.
 *   9 SUB_HP five floats b0,b1,b2,a1,a2. Present only when the rumble
 *     filter is on. Missing section leaves subHpOn at 0, so the tank
 *     add is the old sample. Direct and early are never filtered.
 *   10 BLOOM follower and colour. Present only when amount_db > 0.
 *     40 floats plus 5 per EQ biquad, capped at 96. Missing section is off.
 *   11 PREDELAY one float, samples, usable 1..4799. Missing section is 0.
 *   12 PRE colour, 25 floats, capped at 32. Missing section is off.
 *   13 SIDE inserts. 217 floats, only when an array or room strip is on.
 *     3 place flags (1 = room, otherwise array), then array and room.
 *     Each strip is a comp flag, 80 comp coeffs, a pre flag, and 25 pre
 *     coeffs. Pre runs, then the comp. The master chain is sections 10
 *     and 12 and stays one coeff set. Missing section is off.
 * Route (int), in order: fdn[3][32], early L/R [2][32], early B L/R [2][32],
 * direct[3], direct B[3], fdn B[3][32]. -1 is a wire. < -1 is silent.
 */

#if defined(_MSC_VER)
#define LS_API __declspec(dllexport)
#define LS_ALIGN16 __declspec(align(16))
#else
#define LS_API __attribute__((visibility("default")))
#define LS_ALIGN16 __attribute__((aligned(16)))
#endif
#if defined(__wasm__)
#define LS_EXPORT(name) __attribute__((export_name(name))) LS_API
#else
#define LS_EXPORT(name) LS_API
#endif

typedef struct LiveStereo LiveStereo;

/* One source filter: gain, RBJ high shelf (TDF-II), optional soft one-pole. */
typedef struct SrcFilt {
    int on;
    int order;
    double g, b0, b1, b2, a1, a2, pg, pm;
    double z1, z2, pz, pz2;
} SrcFilt;

enum {
    N = 32,
    PART = 128,
    FFTN = 256,
    MAX_PART = 64,
    MAX_IRS = 192,
    /* Two sources: 3 buses × 32 lines × 2 maps, plus the direct filters. */
    MAX_FILT = 208,
    MAX_SOS = 6,
    /* 1000 ms is the delay cap. These extra samples cover the fractional read. */
    RING_GUARD = 8,
    CAP_MAX = 192000,
    LANES = 4,
    LANE_FDN = 0,
    LANE_EARLY = 1,
    LANE_FDNB = 2,
    LANE_EARLYB = 3,
    MAX_BLOB = 16384,
    MAX_IR_FLOATS = MAX_IRS * 8192,
    MAX_AUDIO = 2048,
    ROUTE_LEN = 3 * 32 + 2 * 32 + 2 * 32 + 3 + 3 + 3 * 32,
    BUS_L = 0,
    BUS_C = 1,
    BUS_R = 2,
    /* Desk gains that ramp. W is six speaker weights, L then R per bus. */
    RG_FDN = 0,
    RG_DIR = 1,
    RG_EARLY = 2,
    RG_DRY = 3,
    RG_MK = 4,
    RG_W = 5,
    RG_N = 11
};

static const double DIRECT_FOLD = 0.55;
static const double SMOOTH = 0.0025;
static const double LS_TINY = 1.0e-20;
static const double LS_DC = 1.0e-18;

typedef struct Line {
    double delay, delayT, delayB, delayBT;
    double dffs, dffsB, inj, injB;
    double airG, airGb, airLp;
    double airZ, airZe, airZb, airZf;
    int shelfOn, shelfOnB;
    double sb0, sb1, sb2, sa1, sa2;
    double sb0b, sb1b, sb2b, sa1b, sa2b;
    double sz1, sz2, sz1e, sz2e, sz1b, sz2b, sz1f, sz2f;
    /* Second shelf (ISO high band). Same four kinds as the first shelf. */
    int sh2On, sh2OnB;
    double h2b0, h2b1, h2b2, h2a1, h2a2;
    double h2b0b, h2b1b, h2b2b, h2a1b, h2a2b;
    double h2z1, h2z2, h2z1e, h2z2e, h2z1b, h2z2b, h2z1f, h2z2f;
    double pz1, pz2, pz1b, pz2b;
    /* Per-line absorption for the decay lock: lg = 10^(-3 d / (sr T60)). 1 = off. */
    double lg, lgB;
    int w;
    /* EQ-1b. 0 keeps today's read_lane. Set only for the modulated half. */
    int modOn, modOnB;
    double modW, modPh, modWB, modPhB;
    double modYap, modYapB;
} Line;

typedef struct Bus {
    Line line[N];
    double dirD, dirDT, dirDB, dirDBT;
    double dirGain, dirGainB;
    int dirW, dirWB;
    int anyDffs, anyDffsB;
    double fb[N], fbB[N];
    double shG, shGB;
} Bus;

typedef struct Filt {
    int used;
    int bus;
    int kind;
    int ir;
    int npart;
    int pos;
    int cold;
    int seen;
    float prev[PART];
    double sz[MAX_SOS][2];
} Filt;

/* Per-line face colour. One coefficient set, two states (image and diffuse). */
#define SURF_K_MAX 6
typedef struct SurfCas {
    int k;
    double c[SURF_K_MAX][5];
    double z[SURF_K_MAX][2];
} SurfCas;

#define SL_SEC 3
/* ROOMTONE. Side pointer, not a room-blob section. 3 counts + 3*16*5 coeffs. */
#define HARM_MAX 16
#define HARM_PACK (3 + 3 * HARM_MAX * 5)

struct LiveStereo {
    int magic;
    int ready;
    int sr;
    int cap;
    int maxDelay;
    int two;
    int colour_on;
    int mono;
    int n_irs;
    int direct_index;
    double g, fdn_wet, direct_wet, early_wet, dry_gain, makeup, gain_a, gain_b;
    double lineT60;
    double micG[3], micPan[3], micPh[3];
    /* SL3. slOn 0 is today's read_peaked path. Sections stay Float64, off the room blob.
       slKeep drops an axis whose mode is at or above 30 Hz (D-SL3). slPk is that float64 bank. */
    int slOn;
    int slKeep[3];
    double slPk[3][5];
    double slBuf[3 * N * SL_SEC * 5];
    double slBufB[3 * N * SL_SEC * 5];
    LS_ALIGN16 double slC[3][SL_SEC][5][N];
    LS_ALIGN16 double slCB[3][SL_SEC][5][N];
    LS_ALIGN16 double slZ[3][2][SL_SEC][2][N];
    int peakOn[3];
    double pb0[3], pb1[3], pb2[3], pa1[3], pa2[3];
    Bus bus[3];
    int fdnIdx[3][N];
    int fdnIdxB[3][N];
    int earlyIdx[2][N];
    int earlyBIdx[2][N];
    int directIdx[3];
    int directBIdx[3];
    int irLen[MAX_IRS];
    int irNpart[MAX_IRS];
    int irSos[MAX_IRS];
    double sos[MAX_IRS][MAX_SOS * 5];
    Filt filt[MAX_FILT];
    float *dir[3];
    float *dirB[3];
    /* cap * LANES floats: FDN A, early A, FDN B, early B at each time index. */
    float *ring[3][N];
    float *slab;
    int slabN;
    float *specRe;
    float *specIm;
    float *fdlRe;
    float *fdlIm;
    float *blob;
    float *irScratch;
    int *lenScratch;
    int *routeScratch;
    float *inL;
    float *inR;
    float *outL;
    float *outR;
    double yBlk[3][N][PART];
    double yBlkB[3][N][PART];
    double eaBlk[3][N][PART];
    double ebBlk[3][N][PART];
    double daBlk[3][PART];
    double dbBlk[3][PART];
    double esBlk[3][PART];
    double dryBlk[PART];
    double reads[N];
    double delayed[N];
    double xinArr[N];
    double yA[N];
    double yB[N];
    float pendL[PART];
    float pendR[PART];
    int pendN;
    float qL[PART];
    float qR[PART];
    int qN, qAt;
    float firIn[MAX_FILT][PART];
    /* Diffuse-tail IC mixer. Off unless live_load_ic ran after this room. */
    int icOn;
    int icN;
    float icHp[513];
    float icHm[513];
    float icHistM[512];
    float icHistS[512];
    float icBuf[1026];
    /* Source radiation. Off (radA = radB = 0) is the omni path. */
    int radA, radB;
    SrcFilt srcImg[2][N];
    SrcFilt srcDir[2][3];
    SrcFilt srcDiff[2];
    double srcSmp[N];
    double srcSmpB[N];
    double diffSmp, diffSmpB;
    /* Per-line diffuse input after the surface cascade. Shared by L, C and R. */
    double diffArr[N], diffArrB[N];
    SurfCas sfI[2][N], sfD[2][N];
    int surfOn;
    double dirSmp[3];
    double dirSmpB[3];
    /* Hadamard order in {8, 16, 32}. 32 is the bit-exact default. */
    int hn;
    /* 1 after a block whose FDN target was up. Mute does not clear the tank. */
    int fdnWas;
    /* SURF early gate. Off when the section length is 0. */
    int earlyGateOn;
    double earlyGate[3][N];
    double earlyGateB[3][N];
    /* Centre bus gain is 0 and every centre inject is 0. Skip that bus. */
    int cEmpty;
    /* Centre speaker weights are 0 for this whole partition and shared tail
       is off. The tank is not run. Unmute starts it cold. */
    int cSkip;
    /* 1 = reaktor_parity, plain Hadamard. 0 = column signs on fwht32. */
    int plainH;
    /* Shared tail. sharedReq is the blob flag. shared is req and a real centre. */
    int sharedReq;
    int shared;
    unsigned delaySig;
    /* Shared-tail taps, kept out of the hot Line struct. */
    double shJit[3][N], shJitB[3][N];
    double shInjS[N], shInjSB[N], shRS[N];
    /* SURF lines-across. Lane 0 image A, 1 image B, 2 diffuse A, 3 diffuse B.
       [lane][section][coef][line] and [lane][section][state][line].
       soaK[lane] is that lane's section count. A coefficient load rewrites
       soaC and leaves soaZ, the same way SurfCas.z is kept. */
    int soaK[4];
    LS_ALIGN16 double soaC[4][SURF_K_MAX][5][N];
    LS_ALIGN16 double soaZ[4][SURF_K_MAX][2][N];
    /* Section 7. deskOn is 0 unless that section arrived. */
    int deskOn;
    double deskW[3][2];
    /* Soft-limit window. limPeak is the loudest |x| over the knee. */
    double limPeak;
    double limOut;
    int limN;
    /* 10 ms linear desk ramps. Idle (rampUse 0) leaves every gain multiply alone.
       The first load snaps to the targets so a static scene does not ramp. */
    int rampPrimed;
    int rampLeft;
    int rampTotal;
    int rampUse;
    double rampFrom[RG_N];
    double rampTo[RG_N];
    double rampBlk[RG_N][PART];
    /* EQ-1b Movement. modOn 0 skips the allpass. modAbs is the sample at t = 0
       of this room load. absT is modAbs plus the index inside the partition. */
    int modOn;
    double modA;
    double modAbs;
    double absT;
    /* D-PROX. Side buffer, not a room-blob section. g == 0 and scale == 1
       leave the sample alone. Scales start at 1 because live_bind zeroes
       the struct before wire_defaults. */
    int proxInited;
    int proxHot;
    int proxRamp;
    double proxP;
    double proxGA[3], proxGB[3];
    double proxTgtA[3], proxTgtB[3];
    double proxStepA[3], proxStepB[3];
    double proxScA[3][N], proxScB[3][N];
    double proxLpDA[3], proxLpDB[3];
    double proxLpEA[3][N], proxLpEB[3][N];
    double proxBuf[199];
    /* ROOMTONE. harmOn 0 is today's delay read. Coeffs are per axis.
       State is per bus, bank, stage, and line. C applies DF1 only. */
    int harmOn;
    int harmN[3];
    double harmC[3][HARM_MAX][5];
    double harmZ[3][2][HARM_MAX][2][N];
    double harmBuf[HARM_PACK];
    /* SUB_HP. One causal 2nd-order Butterworth at 15 Hz on the FDN
       excitation only. subHpOn 0 skips the call, so the off path is the
       old add. State is per bus, source bank, and line. Bank 0 is the
       one-source path and source A. Bank 1 is source B. Each line keeps
       its own state because tint, inj, and srcSmp differ per line, and
       Render filters each impulse column from a cold biquad. A single
       biquad stepped across 32 lines would cross-couple them. */
    int subHpOn;
    double subB0, subB1, subB2, subA1, subA2;
    double subZ[3][2][2][N];
    /* Bloom. bloomOn 0, preOn 0, predelayN 0 and idle ramps are not read
       on the sample path. pdMem is the 99.98 ms predelay ring (4799 samples). */
    int bloomOn;
    int preOn;
    int predelayN;
    int pdW;
    int bN;
    int bRampPrimed;
    int bRampLeft;
    int bRampTotal;
    int pRampLeft;
    int pRampTotal;
    int dMode;
    int dIdle;
    int dCnt;
    int dQuiet;
    double bRampFrom, bRampTo, pRampFrom, pRampTo, bMixCur, pMixCur, bHold;
    double dSc, dU, dFa, dSa, dRf, dRs, dWdet, dM;
    double dV1, dV2, dF, dS, dGv, dG, dVc, dVu;
    double bC[80];
    double bG[PART];
    double bGR[PART];
    double bMixAt[PART];
    double pMixAt[PART];
    double cX0[3], cF0[3], cMem[3], cDcX[3], cDcY[3];
    double cEq[3][6][2];
    float hbZ[3][2][46];
    double pC[25];
    double prS[3][9];
    float prHb[3][4][2][46];
    float pdMem[3][2][N][4800];
    /* Section 13. sideHot 0 is not read on the sample path. */
    int sideHot;
    int sidePlace[3];
    int sideComp[2];
    int sidePre[2];
    double sideC[2][80];
    double sideP[2][25];
    double sideG[2][PART];
    int sMode[2];
    int sIdle[2];
    int sCnt[2];
    int sQuiet[2];
    double sSc[2], sU[2], sFa[2], sSa[2], sRf[2], sRs[2], sWdet[2], sM[2];
    double sV1[2], sV2[2], sF[2], sS[2], sGv[2], sGdet[2], sVc[2], sVu[2];
    double sHold[2];
    double sPr[3][9];
    float sPrHb[3][4][2][46];
};

static LS_ALIGN16 float g_wre[FFTN];
static LS_ALIGN16 float g_wim[FFTN];
static int g_wready = 0;
static LS_ALIGN16 float g_re[FFTN];
static LS_ALIGN16 float g_im[FFTN];
static LS_ALIGN16 float g_accR[FFTN];
static LS_ALIGN16 float g_accI[FFTN];

static void ls_zero(void *dst, int n) {
    unsigned char *d = (unsigned char *)dst;
    unsigned long long *w;
    int i, n8;
    if (!dst || n <= 0) return;
    w = (unsigned long long *)dst;
    n8 = n >> 3;
    for (i = 0; i < n8; i++) w[i] = 0;
    for (i = n8 << 3; i < n; i++) d[i] = 0;
}

static int ptr_aligned4(const void *p) {
    union { const void *p; unsigned char b[sizeof(void *)]; } x;
    x.p = p;
    return (x.b[0] & 3) == 0;
}

static void ls_copy(void *dst, const void *src, int n) {
    unsigned char *d = (unsigned char *)dst;
    const unsigned char *s = (const unsigned char *)src;
    int i = 0;
    if (n >= 4 && ptr_aligned4(d) && ptr_aligned4(s)) {
        float *df = (float *)dst;
        const float *sf = (const float *)src;
        int n4 = n >> 2;
        for (; i < n4; i++) df[i] = sf[i];
        i = n4 << 2;
    }
    for (; i < n; i++) d[i] = s[i];
}

#if defined(__wasm__)
void *memcpy(void *dst, const void *src, unsigned long n) {
    ls_copy(dst, src, (int)n);
    return dst;
}
void *memset(void *dst, int c, unsigned long n) {
    unsigned char *d = (unsigned char *)dst;
    unsigned long i;
    for (i = 0; i < n; i++) d[i] = (unsigned char)c;
    return dst;
}
#endif

static int cap_for(int sr) {
    int c;
    if (sr < 8000) sr = 48000;
    c = sr + RING_GUARD;
    if (c < 256 + RING_GUARD) c = 256 + RING_GUARD;
    if (c > CAP_MAX) c = CAP_MAX;
    return c;
}

static int align_up(int n) {
    return (n + 31) & ~31;
}

static int layout_bytes(int sr) {
    int cap = cap_for(sr);
    int used = align_up((int)sizeof(LiveStereo));
    int slab = 3 * (2 + N * 4) * cap;
    int spec = MAX_IRS * MAX_PART * FFTN;
    int fdl = MAX_FILT * MAX_PART * FFTN;
    used = align_up(used + slab * (int)sizeof(float));
    used = align_up(used + spec * (int)sizeof(float));
    used = align_up(used + spec * (int)sizeof(float));
    used = align_up(used + fdl * (int)sizeof(float));
    used = align_up(used + fdl * (int)sizeof(float));
    used = align_up(used + MAX_BLOB * (int)sizeof(float));
    used = align_up(used + MAX_IR_FLOATS * (int)sizeof(float));
    used = align_up(used + MAX_IRS * (int)sizeof(int));
    used = align_up(used + ROUTE_LEN * (int)sizeof(int));
    used = align_up(used + MAX_AUDIO * (int)sizeof(float));
    used = align_up(used + MAX_AUDIO * (int)sizeof(float));
    used = align_up(used + MAX_AUDIO * (int)sizeof(float));
    used = align_up(used + MAX_AUDIO * (int)sizeof(float));
    return used + 4096;
}

LS_EXPORT("live_bytes")
int live_bytes(int sr) { return layout_bytes(sr); }

static double ls_sin(double x) {
    const double pi = 3.14159265358979323846;
    const double half = 1.57079632679489661923;
    int neg = 0;
    double x2, s;
    while (x > pi) x -= 2.0 * pi;
    while (x < -pi) x += 2.0 * pi;
    if (x < 0) { neg = 1; x = -x; }
    if (x > half) x = pi - x;
    x2 = x * x;
    s = x * (1.0 + x2 * (-1.0 / 6.0 + x2 * (1.0 / 120.0 + x2 * (-1.0 / 5040.0
        + x2 * (1.0 / 362880.0 + x2 * (-1.0 / 39916800.0
        + x2 * (1.0 / 6227020800.0)))))));
    return neg ? -s : s;
}

static double ls_cos(double x) {
    return ls_sin(x + 1.57079632679489661923);
}

static double ls_exp(double x) {
    const double ln2 = 0.693147180559945309417;
    int n, i;
    double nd, f, f2, p, s;
    if (x > 40.0) x = 40.0;
    if (x < -40.0) return 0.0;
    nd = x / ln2;
    n = (int)(nd + (nd < 0.0 ? -0.5 : 0.5));
    f = x - (double)n * ln2;
    f2 = f * f;
    p = 1.0 + f + f2 * (0.5 + f * (1.0 / 6.0 + f * (1.0 / 24.0 + f * (1.0 / 120.0
        + f * (1.0 / 720.0 + f * (1.0 / 5040.0 + f * (1.0 / 40320.0
        + f * (1.0 / 362880.0 + f / 3628800.0))))))));
    s = 1.0;
    if (n >= 0) {
        for (i = 0; i < n; i++) s *= 2.0;
    } else {
        for (i = 0; i < -n; i++) s *= 0.5;
    }
    return s * p;
}

#include "bloom_live.inc"

/* Positive square root. No libm: wasm is freestanding. Four Newton steps. */
static double ls_sqrt(double x) {
    union { double d; unsigned long long u; } v;
    double y;
    if (!(x > 0.0)) return 0.0;
    v.d = x;
    v.u = (v.u >> 1) + 0x1FF8000000000000ULL;
    y = v.d;
    y = 0.5 * (y + x / y);
    y = 0.5 * (y + x / y);
    y = 0.5 * (y + x / y);
    y = 0.5 * (y + x / y);
    return y;
}

static double soft_limit(double x) {
    double a, u, e, th;
    a = x < 0.0 ? -x : x;
    if (a <= 0.95) return x;
    u = (a - 0.95) * 20.0;
    if (u > 16.0) return x < 0.0 ? -0.999 : 0.999;
    e = ls_exp(-2.0 * u);
    th = (1.0 - e) / (1.0 + e);
    return (x < 0.0 ? -1.0 : 1.0) * (0.95 + 0.05 * th);
}

LS_EXPORT("live_soft")
float live_soft(float x) { return (float)soft_limit((double)x); }

static void note_limit(LiveStereo *st, double x, double y) {
    double a = x < 0.0 ? -x : x;
    double ya;
    if (!(a > 0.95)) return;
    ya = y < 0.0 ? -y : y;
    st->limN += 1;
    if (a > st->limPeak) {
        st->limPeak = a;
        st->limOut = ya;
    }
}

LS_EXPORT("live_limiter_peak")
float live_limiter_peak(LiveStereo *st) { return st ? (float)st->limPeak : 0.f; }

LS_EXPORT("live_limiter_out")
float live_limiter_out(LiveStereo *st) { return st ? (float)st->limOut : 0.f; }

LS_EXPORT("live_limiter_n")
int live_limiter_n(LiveStereo *st) { return st ? st->limN : 0; }

LS_EXPORT("live_limiter_reset")
void live_limiter_reset(LiveStereo *st) {
    if (!st) return;
    st->limPeak = 0.0;
    st->limOut = 0.0;
    st->limN = 0;
}

static double ls_flush(double x) {
    double a = x < 0.0 ? -x : x;
    return a < LS_TINY ? 0.0 : x;
}

/* DF2T. k == 0 returns x. State is kept across a coefficient update. */
static double surf_step(SurfCas *f, double x) {
    int j;
    for (j = 0; j < f->k; j++) {
        double *c = f->c[j];
        double *z = f->z[j];
        double y = c[0] * x + z[0];
        z[0] = ls_flush(c[1] * x - c[3] * y + z[1]);
        z[1] = ls_flush(c[2] * x - c[4] * y);
        x = y;
    }
    return x;
}

static int finite_d(double x) {
    if (x != x) return 0;
    if (x > 1.0e30 || x < -1.0e30) return 0;
    return 1;
}

#if defined(__wasm_simd128__)
#include <wasm_simd128.h>
#define LS_SIMD 1
#elif defined(_M_X64) || defined(__SSE2__)
#include <immintrin.h>
#define LS_SIMD 1
#endif

/* Two DF2T cascades, one f64x2 lane each (bank A and bank B). Same arithmetic
   and the same denormal flush as surf_step. Unequal k stays scalar. */
static void surf_step2(SurfCas *a, SurfCas *b, double *x, double *y) {
#if defined(LS_SIMD) && !defined(LS_NO_SIMD)
    if (a->k == b->k) {
        int j;
        double xa = *x, ya = *y;
        for (j = 0; j < a->k; j++) {
            double *ca = a->c[j], *cb = b->c[j];
            double *za = a->z[j], *zb = b->z[j];
#if defined(__wasm_simd128__)
            v128_t xv = wasm_f64x2_make(xa, ya);
            v128_t yv = wasm_f64x2_add(wasm_f64x2_mul(wasm_f64x2_make(ca[0], cb[0]), xv), wasm_f64x2_make(za[0], zb[0]));
            v128_t nz0 = wasm_f64x2_add(
                wasm_f64x2_sub(wasm_f64x2_mul(wasm_f64x2_make(ca[1], cb[1]), xv), wasm_f64x2_mul(wasm_f64x2_make(ca[3], cb[3]), yv)),
                wasm_f64x2_make(za[1], zb[1]));
            v128_t nz1 = wasm_f64x2_sub(wasm_f64x2_mul(wasm_f64x2_make(ca[2], cb[2]), xv), wasm_f64x2_mul(wasm_f64x2_make(ca[4], cb[4]), yv));
            v128_t tiny = wasm_f64x2_splat(LS_TINY);
            nz0 = wasm_v128_andnot(nz0, wasm_f64x2_lt(wasm_f64x2_abs(nz0), tiny));
            nz1 = wasm_v128_andnot(nz1, wasm_f64x2_lt(wasm_f64x2_abs(nz1), tiny));
            za[0] = wasm_f64x2_extract_lane(nz0, 0);
            zb[0] = wasm_f64x2_extract_lane(nz0, 1);
            za[1] = wasm_f64x2_extract_lane(nz1, 0);
            zb[1] = wasm_f64x2_extract_lane(nz1, 1);
            xa = wasm_f64x2_extract_lane(yv, 0);
            ya = wasm_f64x2_extract_lane(yv, 1);
#else
            __m128d xv = _mm_set_pd(ya, xa);
            __m128d yv = _mm_add_pd(_mm_mul_pd(_mm_set_pd(cb[0], ca[0]), xv), _mm_set_pd(zb[0], za[0]));
            __m128d nz0 = _mm_add_pd(
                _mm_sub_pd(_mm_mul_pd(_mm_set_pd(cb[1], ca[1]), xv), _mm_mul_pd(_mm_set_pd(cb[3], ca[3]), yv)),
                _mm_set_pd(zb[1], za[1]));
            __m128d nz1 = _mm_sub_pd(_mm_mul_pd(_mm_set_pd(cb[2], ca[2]), xv), _mm_mul_pd(_mm_set_pd(cb[4], ca[4]), yv));
            __m128d sign = _mm_set1_pd(-0.0);
            __m128d tiny = _mm_set1_pd(LS_TINY);
            nz0 = _mm_andnot_pd(_mm_cmplt_pd(_mm_andnot_pd(sign, nz0), tiny), nz0);
            nz1 = _mm_andnot_pd(_mm_cmplt_pd(_mm_andnot_pd(sign, nz1), tiny), nz1);
            _mm_storel_pd(&za[0], nz0);
            _mm_storeh_pd(&zb[0], nz0);
            _mm_storel_pd(&za[1], nz1);
            _mm_storeh_pd(&zb[1], nz1);
            _mm_storel_pd(&xa, yv);
            _mm_storeh_pd(&ya, yv);
#endif
        }
        *x = xa;
        *y = ya;
        return;
    }
#endif
    *x = surf_step(a, *x);
    *y = surf_step(b, *y);
}

/* SoA lane of one bank. Two consecutive lines share one f64x2. Sections are
   the outer loop. Lines shorter than this lane's K are identity sections
   (b0 = 1, the rest 0), so the pair stays in lockstep. Flush matches surf_step. */
static SurfCas *soa_cas(LiveStereo *st, int L, int i) {
    if (L == 0) return &st->sfI[0][i];
    if (L == 1) return &st->sfI[1][i];
    if (L == 2) return &st->sfD[0][i];
    return &st->sfD[1][i];
}

static void soa_build(LiveStereo *st) {
    int L, i, s, q;
    for (L = 0; L < 4; L++) {
        int km = 0;
        for (i = 0; i < N; i++) {
            int k = soa_cas(st, L, i)->k;
            if (k > km) km = k;
        }
        if (km > SURF_K_MAX) km = SURF_K_MAX;
        st->soaK[L] = km;
        for (i = 0; i < N; i++) {
            SurfCas *f = soa_cas(st, L, i);
            int k = f->k;
            if (k < 0) k = 0;
            if (k > km) k = km;
            for (s = 0; s < km; s++) {
                for (q = 0; q < 5; q++)
                    st->soaC[L][s][q][i] = (s < k) ? f->c[s][q] : (q == 0 ? 1.0 : 0.0);
            }
        }
    }
}

#if defined(LS_SIMD) && !defined(LS_NO_SIMD)
static void soa_lane(LiveStereo *st, int L, double *x) {
    int s, i, km = st->soaK[L];
#if defined(__wasm_simd128__)
    v128_t tiny = wasm_f64x2_splat(LS_TINY);
#else
    __m128d sign = _mm_set1_pd(-0.0);
    __m128d tiny = _mm_set1_pd(LS_TINY);
#endif
    for (s = 0; s < km; s++) {
        double *c0 = st->soaC[L][s][0];
        double *c1 = st->soaC[L][s][1];
        double *c2 = st->soaC[L][s][2];
        double *c3 = st->soaC[L][s][3];
        double *c4 = st->soaC[L][s][4];
        double *z0 = st->soaZ[L][s][0];
        double *z1 = st->soaZ[L][s][1];
        for (i = 0; i < N; i += 2) {
#if defined(__wasm_simd128__)
            v128_t xv = wasm_v128_load(x + i);
            v128_t yv = wasm_f64x2_add(wasm_f64x2_mul(wasm_v128_load(c0 + i), xv), wasm_v128_load(z0 + i));
            v128_t nz0 = wasm_f64x2_add(
                wasm_f64x2_sub(wasm_f64x2_mul(wasm_v128_load(c1 + i), xv), wasm_f64x2_mul(wasm_v128_load(c3 + i), yv)),
                wasm_v128_load(z1 + i));
            v128_t nz1 = wasm_f64x2_sub(wasm_f64x2_mul(wasm_v128_load(c2 + i), xv), wasm_f64x2_mul(wasm_v128_load(c4 + i), yv));
            nz0 = wasm_v128_andnot(nz0, wasm_f64x2_lt(wasm_f64x2_abs(nz0), tiny));
            nz1 = wasm_v128_andnot(nz1, wasm_f64x2_lt(wasm_f64x2_abs(nz1), tiny));
            wasm_v128_store(z0 + i, nz0);
            wasm_v128_store(z1 + i, nz1);
            wasm_v128_store(x + i, yv);
#else
            __m128d xv = _mm_loadu_pd(x + i);
            __m128d yv = _mm_add_pd(_mm_mul_pd(_mm_loadu_pd(c0 + i), xv), _mm_loadu_pd(z0 + i));
            __m128d nz0 = _mm_add_pd(
                _mm_sub_pd(_mm_mul_pd(_mm_loadu_pd(c1 + i), xv), _mm_mul_pd(_mm_loadu_pd(c3 + i), yv)),
                _mm_loadu_pd(z1 + i));
            __m128d nz1 = _mm_sub_pd(_mm_mul_pd(_mm_loadu_pd(c2 + i), xv), _mm_mul_pd(_mm_loadu_pd(c4 + i), yv));
            nz0 = _mm_andnot_pd(_mm_cmplt_pd(_mm_andnot_pd(sign, nz0), tiny), nz0);
            nz1 = _mm_andnot_pd(_mm_cmplt_pd(_mm_andnot_pd(sign, nz1), tiny), nz1);
            _mm_storeu_pd(z0 + i, nz0);
            _mm_storeu_pd(z1 + i, nz1);
            _mm_storeu_pd(x + i, yv);
#endif
        }
    }
}
#endif

/* Three staging paths. rad: image lane and diffuse lane. No rad: image lane
   only. split: bank A and bank B. Otherwise bank A. Scalar is surf_step. */
static void surf_stage(LiveStereo *st, int rad, int split, double xin, double xB) {
    int i;
#if defined(LS_SIMD) && !defined(LS_NO_SIMD)
    if (rad && split) {
        for (i = 0; i < N; i++) {
            st->diffArr[i] = st->diffSmp;
            st->diffArrB[i] = st->diffSmpB;
        }
        soa_lane(st, 0, st->srcSmp);
        soa_lane(st, 1, st->srcSmpB);
        soa_lane(st, 2, st->diffArr);
        soa_lane(st, 3, st->diffArrB);
        return;
    }
    if (rad) {
        for (i = 0; i < N; i++) st->diffArr[i] = st->diffSmp;
        soa_lane(st, 0, st->srcSmp);
        soa_lane(st, 2, st->diffArr);
        return;
    }
    if (split) {
        for (i = 0; i < N; i++) {
            st->srcSmp[i] = xin;
            st->srcSmpB[i] = xB;
        }
        soa_lane(st, 0, st->srcSmp);
        soa_lane(st, 1, st->srcSmpB);
        return;
    }
    for (i = 0; i < N; i++) st->srcSmp[i] = xin;
    soa_lane(st, 0, st->srcSmp);
#else
    if (rad) {
        for (i = 0; i < N; i++) {
            if (split) {
                double dA = st->diffSmp, dB = st->diffSmpB;
                surf_step2(&st->sfI[0][i], &st->sfI[1][i], &st->srcSmp[i], &st->srcSmpB[i]);
                surf_step2(&st->sfD[0][i], &st->sfD[1][i], &dA, &dB);
                st->diffArr[i] = dA;
                st->diffArrB[i] = dB;
            } else {
                st->srcSmp[i] = surf_step(&st->sfI[0][i], st->srcSmp[i]);
                st->diffArr[i] = surf_step(&st->sfD[0][i], st->diffSmp);
            }
        }
        return;
    }
    for (i = 0; i < N; i++) {
        if (split) {
            double a = xin, b = xB;
            surf_step2(&st->sfI[0][i], &st->sfI[1][i], &a, &b);
            st->srcSmp[i] = a;
            st->srcSmpB[i] = b;
        } else {
            st->srcSmp[i] = surf_step(&st->sfI[0][i], xin);
        }
    }
#endif
}

static void init_twiddles(void) {
    int k;
    if (g_wready) return;
    for (k = 0; k < FFTN; k++) {
        double ang = -2.0 * 3.14159265358979323846 * (double)k / (double)FFTN;
        g_wre[k] = (float)ls_cos(ang);
        g_wim[k] = (float)ls_sin(ang);
    }
    g_wready = 1;
}

static void fft_complex(float *re, float *im, int inv) {
    int i, j, bit, len, half, step, u, v;
    for (i = 1, j = 0; i < FFTN; i++) {
        bit = FFTN >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) {
            float tr = re[i]; re[i] = re[j]; re[j] = tr;
            float ti = im[i]; im[i] = im[j]; im[j] = ti;
        }
    }
    for (len = 2; len <= FFTN; len <<= 1) {
        half = len >> 1;
        step = FFTN / len;
        for (i = 0; i < FFTN; i += len) {
            j = 0;
#if defined(LS_SIMD)
            for (; j + 4 <= half; j += 4) {
                LS_ALIGN16 float wrv[4], wiv[4];
                int k;
                for (k = 0; k < 4; k++) {
                    int tw = (j + k) * step;
                    wrv[k] = g_wre[tw];
                    wiv[k] = inv ? -g_wim[tw] : g_wim[tw];
                }
                u = i + j;
#if defined(__wasm_simd128__)
                {
                    v128_t vre = wasm_v128_load(re + u + half);
                    v128_t vim = wasm_v128_load(im + u + half);
                    v128_t vwr = wasm_f32x4_make(wrv[0], wrv[1], wrv[2], wrv[3]);
                    v128_t vwi = wasm_f32x4_make(wiv[0], wiv[1], wiv[2], wiv[3]);
                    v128_t tr = wasm_f32x4_sub(wasm_f32x4_mul(vwr, vre), wasm_f32x4_mul(vwi, vim));
                    v128_t ti = wasm_f32x4_add(wasm_f32x4_mul(vwr, vim), wasm_f32x4_mul(vwi, vre));
                    v128_t ure = wasm_v128_load(re + u);
                    v128_t uim = wasm_v128_load(im + u);
                    wasm_v128_store(re + u + half, wasm_f32x4_sub(ure, tr));
                    wasm_v128_store(im + u + half, wasm_f32x4_sub(uim, ti));
                    wasm_v128_store(re + u, wasm_f32x4_add(ure, tr));
                    wasm_v128_store(im + u, wasm_f32x4_add(uim, ti));
                }
#else
                {
                    __m128 vre = _mm_loadu_ps(re + u + half);
                    __m128 vim = _mm_loadu_ps(im + u + half);
                    __m128 vwr = _mm_load_ps(wrv);
                    __m128 vwi = _mm_load_ps(wiv);
                    __m128 tr = _mm_sub_ps(_mm_mul_ps(vwr, vre), _mm_mul_ps(vwi, vim));
                    __m128 ti = _mm_add_ps(_mm_mul_ps(vwr, vim), _mm_mul_ps(vwi, vre));
                    __m128 ure = _mm_loadu_ps(re + u);
                    __m128 uim = _mm_loadu_ps(im + u);
                    _mm_storeu_ps(re + u + half, _mm_sub_ps(ure, tr));
                    _mm_storeu_ps(im + u + half, _mm_sub_ps(uim, ti));
                    _mm_storeu_ps(re + u, _mm_add_ps(ure, tr));
                    _mm_storeu_ps(im + u, _mm_add_ps(uim, ti));
                }
#endif
            }
#endif
            for (; j < half; j++) {
                int tw = j * step;
                float wr = g_wre[tw];
                float wi = inv ? -g_wim[tw] : g_wim[tw];
                u = i + j;
                v = u + half;
                {
                    float tr = wr * re[v] - wi * im[v];
                    float ti = wr * im[v] + wi * re[v];
                    re[v] = re[u] - tr;
                    im[v] = im[u] - ti;
                    re[u] += tr;
                    im[u] += ti;
                }
            }
        }
    }
    if (inv) {
        float s = 1.0f / (float)FFTN;
        for (i = 0; i < FFTN; i++) { re[i] *= s; im[i] *= s; }
    }
}

static void *take(unsigned char *base, int *used, int bytes) {
    int u = align_up(*used);
    void *p = base + u;
    *used = u + bytes;
    return p;
}

static void wire_defaults(LiveStereo *st) {
    int b, i;
    for (b = 0; b < 3; b++) {
        st->directIdx[b] = -1;
        st->directBIdx[b] = -1;
        st->micG[b] = 1.0;
        st->micPh[b] = 1.0;
        for (i = 0; i < N; i++) {
            st->fdnIdx[b][i] = -1;
            st->fdnIdxB[b][i] = -1;
        }
    }
    st->micPan[0] = -1.0;
    st->micPan[1] = 0.0;
    st->micPan[2] = 1.0;
    for (b = 0; b < 2; b++) {
        for (i = 0; i < N; i++) {
            st->earlyIdx[b][i] = -2;
            st->earlyBIdx[b][i] = -2;
        }
    }
    st->g = 0.03;
    st->hn = 32;
    st->fdnWas = 0;
    st->earlyGateOn = 0;
    st->surfOn = 0;
    st->cEmpty = 0;
    st->cSkip = 0;
    st->plainH = 0;
    st->sharedReq = 0;
    st->shared = 0;
    st->delaySig = 0;
    st->deskOn = 0;
    st->fdn_wet = 1.0;
    st->direct_wet = 1.0;
    st->gain_a = 1.0;
    st->gain_b = 1.0;
    st->makeup = 1.0;
    for (b = 0; b < 3; b++) {
        st->bus[b].dirGain = 1.0;
        st->bus[b].dirGainB = 1.0;
        st->bus[b].dirD = 64.0;
        st->bus[b].dirDT = 64.0;
        st->bus[b].dirDB = 64.0;
        st->bus[b].dirDBT = 64.0;
        for (i = 0; i < N; i++) {
            st->bus[b].line[i].delay = 64.0;
            st->bus[b].line[i].delayT = 64.0;
            st->bus[b].line[i].delayB = 64.0;
            st->bus[b].line[i].delayBT = 64.0;
            st->bus[b].line[i].sb0 = 1.0;
            st->bus[b].line[i].sb0b = 1.0;
            st->bus[b].line[i].lg = 1.0;
            st->bus[b].line[i].lgB = 1.0;
            st->proxScA[b][i] = 1.0;
            st->proxScB[b][i] = 1.0;
        }
        st->proxGA[b] = 0.0;
        st->proxGB[b] = 0.0;
        st->proxTgtA[b] = 0.0;
        st->proxTgtB[b] = 0.0;
    }
    st->proxP = ls_exp(-2.0 * 3.14159265358979323846 * 20.0 / (double)st->sr);
    st->proxInited = 0;
    st->proxHot = 0;
    st->proxRamp = 0;
}

LS_EXPORT("live_bind")
LiveStereo *live_bind(void *mem, int bytes, int sr) {
    unsigned char *base;
    int used, cap, slabN, specN, fdlN, b, i;
    LiveStereo *st;
    float *p;
    if (!mem || bytes < (int)sizeof(LiveStereo) + 1024) return 0;
    if (sr < 8000) sr = 48000;
    if (bytes < layout_bytes(sr)) return 0;
    /* Caller memory is already clear: wasm memory.grow, or a zeroed test buffer.
     * Wiping the whole delay slab here blocks the audio thread long enough to kill Play. */
    ls_zero(mem, (int)sizeof(LiveStereo));
    base = (unsigned char *)mem;
    st = (LiveStereo *)mem;
    used = (int)sizeof(LiveStereo);
    cap = cap_for(sr);
    slabN = 3 * (2 + N * 4) * cap;
    st->slab = (float *)take(base, &used, slabN * (int)sizeof(float));
    st->slabN = slabN;
    specN = MAX_IRS * MAX_PART * FFTN;
    st->specRe = (float *)take(base, &used, specN * (int)sizeof(float));
    st->specIm = (float *)take(base, &used, specN * (int)sizeof(float));
    fdlN = MAX_FILT * MAX_PART * FFTN;
    st->fdlRe = (float *)take(base, &used, fdlN * (int)sizeof(float));
    st->fdlIm = (float *)take(base, &used, fdlN * (int)sizeof(float));
    st->blob = (float *)take(base, &used, MAX_BLOB * (int)sizeof(float));
    st->irScratch = (float *)take(base, &used, MAX_IR_FLOATS * (int)sizeof(float));
    st->lenScratch = (int *)take(base, &used, MAX_IRS * (int)sizeof(int));
    st->routeScratch = (int *)take(base, &used, ROUTE_LEN * (int)sizeof(int));
    st->inL = (float *)take(base, &used, MAX_AUDIO * (int)sizeof(float));
    st->inR = (float *)take(base, &used, MAX_AUDIO * (int)sizeof(float));
    st->outL = (float *)take(base, &used, MAX_AUDIO * (int)sizeof(float));
    st->outR = (float *)take(base, &used, MAX_AUDIO * (int)sizeof(float));
    if (used > bytes) return 0;
    st->sr = sr;
    st->cap = cap;
    st->maxDelay = cap - RING_GUARD;
    if (st->maxDelay < 256) st->maxDelay = 256;
    p = st->slab;
    for (b = 0; b < 3; b++) {
        st->dir[b] = p; p += cap;
        st->dirB[b] = p; p += cap;
        for (i = 0; i < N; i++) {
            st->ring[b][i] = p;
            p += cap * LANES;
        }
    }
    wire_defaults(st);
    init_twiddles();
    st->magic = 0x2011;
    st->ready = 1;
    return st;
}

LS_EXPORT("live_blob_ptr") float *live_blob_ptr(LiveStereo *st) { return st ? st->blob : 0; }
/* SL3. JS writes live_surf_ptr and live_surf_ptr_b (Float64, 3 x 32 x 3 x 5),
   live_surf_peak_ptr (3 x 5), and live_surf_keep, then live_load_surf(st, 1).
   A non-finite coefficient or a Jury fail (|a2| >= 1 or |a1| >= 1+a2) on either
   bank leaves slOn = 0. Bank B's gain stays lgB from delayBT. The loop-gain
   guard stays in Python. live_load_surf(st, 0) turns sections off. Returns 1 if on. */
LS_EXPORT("live_surf_ptr") double *live_surf_ptr(LiveStereo *st) { return st ? st->slBuf : 0; }
LS_EXPORT("live_surf_ptr_b") double *live_surf_ptr_b(LiveStereo *st) { return st ? st->slBufB : 0; }
LS_EXPORT("live_surf_peak_ptr") double *live_surf_peak_ptr(LiveStereo *st) { return st ? &st->slPk[0][0] : 0; }
LS_EXPORT("live_surf_keep") int live_surf_keep(LiveStereo *st, int kx, int ky, int kz) {
    if (!st) return 0;
    st->slKeep[0] = kx ? 1 : 0;
    st->slKeep[1] = ky ? 1 : 0;
    st->slKeep[2] = kz ? 1 : 0;
    return 1;
}
LS_EXPORT("live_load_surf") int live_load_surf(LiveStereo *st, int on) {
    int b, i, k, j;
    if (!st) return 0;
    if (!on) { st->slOn = 0; return 0; }
    for (j = 0; j < 3 * N * SL_SEC * 5; j++) if (!finite_d(st->slBuf[j])) { st->slOn = 0; return 0; }
    for (j = 0; j < 3 * N * SL_SEC * 5; j++) if (!finite_d(st->slBufB[j])) { st->slOn = 0; return 0; }
    for (j = 0; j < 3 * N * SL_SEC; j++) {
        const double *c = &st->slBuf[5 * j];
        if (!(c[4] < 1.0 && c[4] > -1.0 && c[3] < 1.0 + c[4] && -c[3] < 1.0 + c[4])) { st->slOn = 0; return 0; }
    }
    for (j = 0; j < 3 * N * SL_SEC; j++) {
        const double *c = &st->slBufB[5 * j];
        if (!(c[4] < 1.0 && c[4] > -1.0 && c[3] < 1.0 + c[4] && -c[3] < 1.0 + c[4])) { st->slOn = 0; return 0; }
    }
    for (b = 0; b < 3; b++) for (i = 0; i < N; i++) for (k = 0; k < SL_SEC; k++) {
        for (j = 0; j < 5; j++) {
            st->slC[b][k][j][i] = st->slBuf[((b * N + i) * SL_SEC + k) * 5 + j];
            st->slCB[b][k][j][i] = st->slBufB[((b * N + i) * SL_SEC + k) * 5 + j];
        }
        if (!st->slOn) {
            st->slZ[b][0][k][0][i] = st->slZ[b][0][k][1][i] = 0.0;
            st->slZ[b][1][k][0][i] = st->slZ[b][1][k][1][i] = 0.0;
        }
    }
    st->slOn = 1;
    return 1;
}
/* ROOMTONE. JS writes live_harm_ptr (Float64, HARM_PACK) then live_load_harm(st, 1).
   Layout: nX nY nZ, then axis-major HARM_MAX stages of b0 b1 b2 a1 a2.
   A non-finite coefficient or a Jury fail leaves the cascade off.
   live_load_harm(st, 0) is the size-gate bypass. Returns 1 if on. */
LS_EXPORT("live_harm_ptr") double *live_harm_ptr(LiveStereo *st) { return st ? st->harmBuf : 0; }
LS_EXPORT("live_load_harm") int live_load_harm(LiveStereo *st, int on) {
    int ax, k, j, n, any;
    if (!st) return 0;
    if (!on) {
        st->harmOn = 0;
        st->harmN[0] = st->harmN[1] = st->harmN[2] = 0;
        ls_zero(st->harmZ, (int)sizeof(st->harmZ));
        return 0;
    }
    for (j = 0; j < HARM_PACK; j++) {
        if (!finite_d(st->harmBuf[j])) {
            st->harmOn = 0;
            st->harmN[0] = st->harmN[1] = st->harmN[2] = 0;
            return 0;
        }
    }
    any = 0;
    for (ax = 0; ax < 3; ax++) {
        n = (int)(st->harmBuf[ax] + 0.5);
        if (n < 0) n = 0;
        if (n > HARM_MAX) n = HARM_MAX;
        for (k = 0; k < n; k++) {
            const double *c = &st->harmBuf[3 + (ax * HARM_MAX + k) * 5];
            if (!(c[4] < 1.0 && c[4] > -1.0 && c[3] < 1.0 + c[4] && -c[3] < 1.0 + c[4])) {
                st->harmOn = 0;
                st->harmN[0] = st->harmN[1] = st->harmN[2] = 0;
                return 0;
            }
        }
        st->harmN[ax] = n;
        if (n) any = 1;
        for (k = 0; k < n; k++) {
            const double *c = &st->harmBuf[3 + (ax * HARM_MAX + k) * 5];
            for (j = 0; j < 5; j++) st->harmC[ax][k][j] = c[j];
        }
    }
    if (!any) {
        st->harmOn = 0;
        return 0;
    }
    if (!st->harmOn) ls_zero(st->harmZ, (int)sizeof(st->harmZ));
    st->harmOn = 1;
    return 1;
}
LS_EXPORT("live_ir_ptr") float *live_ir_ptr(LiveStereo *st) { return st ? st->irScratch : 0; }
LS_EXPORT("live_len_ptr") int *live_len_ptr(LiveStereo *st) { return st ? st->lenScratch : 0; }
LS_EXPORT("live_route_ptr") int *live_route_ptr(LiveStereo *st) { return st ? st->routeScratch : 0; }
LS_EXPORT("live_in_l") float *live_in_l(LiveStereo *st) { return st ? st->inL : 0; }
LS_EXPORT("live_in_r") float *live_in_r(LiveStereo *st) { return st ? st->inR : 0; }
LS_EXPORT("live_out_l") float *live_out_l(LiveStereo *st) { return st ? st->outL : 0; }
LS_EXPORT("live_out_r") float *live_out_r(LiveStereo *st) { return st ? st->outR : 0; }

static double clampf(double x, double lo, double hi) {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

static double ms_to_delay(LiveStereo *st, double ms) {
    double d;
    if (!(ms > 0.0)) ms = 20.0;
    d = ms * 0.001 * (double)st->sr;
    if (d < 2.0) d = 2.0;
    if (d > (double)st->maxDelay) d = (double)st->maxDelay;
    return d;
}

static void clear_b(LiveStereo *st) {
    int b, i;
    for (b = 0; b < 3; b++) {
        Bus *bus = &st->bus[b];
        ls_zero(st->dirB[b], st->cap * (int)sizeof(float));
        bus->dirWB = 0;
        for (i = 0; i < N; i++) {
            Line *line = &bus->line[i];
            int t;
            float *ring = st->ring[b][i];
            for (t = 0; t < st->cap; t++) {
                ring[t * LANES + LANE_FDNB] = 0;
                ring[t * LANES + LANE_EARLYB] = 0;
            }
            line->pz1b = 0; line->pz2b = 0;
            line->airZe = 0; line->sz1e = 0; line->sz2e = 0;
            line->airZb = 0; line->sz1b = 0; line->sz2b = 0;
            line->airZf = 0; line->sz1f = 0; line->sz2f = 0;
            line->h2z1b = 0; line->h2z2b = 0;
            line->h2z1f = 0; line->h2z2f = 0;
            bus->fb[i] = 0;
            bus->fbB[i] = 0;
        }
    }
    for (i = 0; i < MAX_FILT; i++) {
        if (st->filt[i].used && st->filt[i].kind == 2) {
            st->filt[i].used = 0;
            st->filt[i].cold = MAX_PART;
        }
    }
}

/* earlyToo: also drop the early lanes (Hadamard order changed).
   Otherwise only the FDN lanes and their feedback, so Early stays continuous. */
static void clear_line_lanes(LiveStereo *st, int earlyToo) {
    int b, i, t;
    for (b = 0; b < 3; b++) {
        Bus *bus = &st->bus[b];
        for (i = 0; i < N; i++) {
            Line *line = &bus->line[i];
            float *ring = st->ring[b][i];
            for (t = 0; t < st->cap; t++) {
                ring[t * LANES + LANE_FDN] = 0;
                ring[t * LANES + LANE_FDNB] = 0;
                if (earlyToo) {
                    ring[t * LANES + LANE_EARLY] = 0;
                    ring[t * LANES + LANE_EARLYB] = 0;
                }
            }
            line->airZ = 0; line->sz1 = 0; line->sz2 = 0;
            line->h2z1 = 0; line->h2z2 = 0;
            line->airZf = 0; line->sz1f = 0; line->sz2f = 0;
            line->h2z1f = 0; line->h2z2f = 0;
            line->pz1 = 0; line->pz2 = 0;
            line->pz1b = 0; line->pz2b = 0;
            line->modYap = 0; line->modYapB = 0;
            bus->fb[i] = 0;
            bus->fbB[i] = 0;
            if (earlyToo) {
                line->airZe = 0; line->sz1e = 0; line->sz2e = 0;
                line->h2z1e = 0; line->h2z2e = 0;
                line->airZb = 0; line->sz1b = 0; line->sz2b = 0;
                line->h2z1b = 0; line->h2z2b = 0;
            }
        }
    }
}

typedef struct Rd { const float *p; int i, n; } Rd;
static double rf(Rd *r) {
    if (r->i >= r->n) return 0.0;
    return (double)r->p[r->i++];
}

static void load_shelf(Rd *r, Line *line, int bankB) {
    int on = rf(r) > 0.5;
    double b0 = rf(r), b1 = rf(r), b2 = rf(r), a1 = rf(r), a2 = rf(r);
    if (bankB) {
        line->shelfOnB = on;
        if (on) {
            line->sb0b = b0; line->sb1b = b1; line->sb2b = b2;
            line->sa1b = a1; line->sa2b = a2;
        }
    } else {
        line->shelfOn = on;
        if (on) {
            line->sb0 = b0; line->sb1 = b1; line->sb2 = b2;
            line->sa1 = a1; line->sa2 = a2;
        }
    }
}

static void load_core_body(LiveStereo *st, Rd *src) {
    Rd r = *src;
    int b, i, nextTwo, snap, maxMs;
    double d;
    d = rf(&r); if (finite_d(d)) st->g = d;
    st->fdn_wet = rf(&r);
    st->direct_wet = rf(&r);
    st->early_wet = rf(&r);
    st->dry_gain = rf(&r);
    st->makeup = rf(&r);
    st->gain_a = clampf(rf(&r), 0.0, 1.0);
    st->gain_b = clampf(rf(&r), 0.0, 1.0);
    nextTwo = rf(&r) > 0.5;
    st->colour_on = rf(&r) > 0.5;
    st->mono = rf(&r) > 0.5;
    st->direct_index = (int)rf(&r);
    if (st->direct_index < 0) st->direct_index = 0;
    if (st->direct_index > N - 1) st->direct_index = N - 1;
    maxMs = (int)(rf(&r) + 0.5);
    if (maxMs < 1) maxMs = 1000;
    d = (double)st->sr * (double)maxMs * 0.001;
    st->maxDelay = (int)(d + 0.5);
    if (st->maxDelay < 256) st->maxDelay = 256;
    if (st->maxDelay > st->cap - RING_GUARD) st->maxDelay = st->cap - RING_GUARD;
    snap = rf(&r) > 0.5;
    (void)rf(&r);
    for (b = 0; b < 3; b++) {
        st->micG[b] = clampf(rf(&r), 0.0, 16.0);
        st->micPan[b] = clampf(rf(&r), -1.0, 1.0);
        st->micPh[b] = rf(&r) < 0.0 ? -1.0 : 1.0;
    }
    for (b = 0; b < 3; b++) {
        int on = rf(&r) > 0.5;
        st->peakOn[b] = on;
        st->pb0[b] = rf(&r); st->pb1[b] = rf(&r); st->pb2[b] = rf(&r);
        st->pa1[b] = rf(&r); st->pa2[b] = rf(&r);
        /* Cut-only peaking is unity at DC. Float32 storage of b2 loses that.
           Restore it in double. Render stays float64 and does not need this. */
        if (on) st->pb2[b] = 1.0 + st->pa1[b] + st->pa2[b] - st->pb0[b] - st->pb1[b];
        if (!on) {
            int bb, j;
            for (bb = 0; bb < 3; bb++) {
                for (j = 0; j < N; j++) {
                    if ((j % 3) == b) {
                        st->bus[bb].line[j].pz1 = 0;
                        st->bus[bb].line[j].pz2 = 0;
                        st->bus[bb].line[j].pz1b = 0;
                        st->bus[bb].line[j].pz2b = 0;
                    }
                }
            }
        }
    }
    if (nextTwo && !st->two) clear_b(st);
    st->two = nextTwo;
    for (b = 0; b < 3; b++) {
        Bus *bus = &st->bus[b];
        int any = 0, anyB = 0;
        double airLp;
        for (i = 0; i < N; i++) {
            Line *line = &bus->line[i];
            line->delayT = ms_to_delay(st, rf(&r));
            if (snap) line->delay = line->delayT;
        }
        for (i = 0; i < N; i++) bus->line[i].inj = rf(&r);
        for (i = 0; i < N; i++) {
            bus->line[i].dffs = clampf(rf(&r), -0.98, 0.98);
            if (bus->line[i].dffs > 1.0e-12 || bus->line[i].dffs < -1.0e-12) any = 1;
        }
        for (i = 0; i < N; i++) bus->line[i].airG = rf(&r);
        airLp = rf(&r);
        for (i = 0; i < N; i++) {
            bus->line[i].airLp = airLp;
            load_shelf(&r, &bus->line[i], 0);
        }
        bus->dirDT = ms_to_delay(st, rf(&r));
        if (snap) bus->dirD = bus->dirDT;
        bus->dirGain = clampf(rf(&r), -2.0, 2.0);
        bus->anyDffs = any;
        for (i = 0; i < N; i++) {
            bus->line[i].delayBT = ms_to_delay(st, rf(&r));
            if (snap) bus->line[i].delayB = bus->line[i].delayBT;
        }
        for (i = 0; i < N; i++) bus->line[i].injB = rf(&r);
        for (i = 0; i < N; i++) {
            bus->line[i].dffsB = clampf(rf(&r), -0.98, 0.98);
            if (bus->line[i].dffsB > 1.0e-12 || bus->line[i].dffsB < -1.0e-12) anyB = 1;
        }
        for (i = 0; i < N; i++) bus->line[i].airGb = rf(&r);
        (void)rf(&r);
        for (i = 0; i < N; i++) load_shelf(&r, &bus->line[i], 1);
        bus->dirDBT = ms_to_delay(st, rf(&r));
        if (snap) bus->dirDB = bus->dirDBT;
        bus->dirGainB = clampf(rf(&r), -2.0, 2.0);
        bus->anyDffsB = anyB;
    }
    /* Optional trailing float (blob length 1982): line T60 in seconds.
     * > 0.05 turns on delay-proportional line absorption so every path through
     * the loop (Hadamard or the Dffs allpass self-loop) loses 60 dB per T60.
     * lg uses the TARGET delay (delayT); delay glides to it within ~10 ms. */
    st->lineT60 = rf(&r);
    for (b = 0; b < 3; b++) {
        for (i = 0; i < N; i++) {
            Line *line = &st->bus[b].line[i];
            if (st->lineT60 > 0.05) {
                double k = -6.907755278982137 / ((double)st->sr * st->lineT60);
                line->lg = ls_exp(k * line->delayT);
                line->lgB = ls_exp(k * line->delayBT);
            } else {
                line->lg = 1.0;
                line->lgB = 1.0;
            }
        }
    }
    /* Eight reserved CORE floats. hadamard_n, loop_semantics, solo_mute[6].
     * solo_mute is not an audio gate. Early Solo/Mute is the SURF section. */
    {
        int prevHn = st->hn;
        int nowFdn;
        if (prevHn != 8 && prevHn != 16 && prevHn != 32) prevHn = 32;
        st->hn = 32;
        st->plainH = 0;
        if (r.n - r.i >= 8) {
            int hn = (int)(rf(&r) + 0.5);
            int sem, k;
            if (hn == 8 || hn == 16 || hn == 32) st->hn = hn;
            sem = (int)(rf(&r) + 0.5);
            st->plainH = sem == 1;
            for (k = 2; k < 8; k++) (void)rf(&r);
        }
        nowFdn = st->fdn_wet > 1.0e-4;
        /* An order change drops every lane. Mute does not: the tank keeps running
           and the output gain ramps, so unmuting still has the tail. */
        if (st->hn != prevHn) clear_line_lanes(st, 1);
        st->fdnWas = nowFdn;
    }
}

static void clear_sh2_on(LiveStereo *st) {
    int b, i;
    for (b = 0; b < 3; b++) {
        for (i = 0; i < N; i++) {
            st->bus[b].line[i].sh2On = 0;
            st->bus[b].line[i].sh2OnB = 0;
        }
    }
}

static void load_sh2_one(Rd *r, Line *line, int bankB) {
    int on = rf(r) > 0.5;
    double b0 = rf(r), b1 = rf(r), b2 = rf(r), a1 = rf(r), a2 = rf(r);
    if (bankB) {
        line->sh2OnB = on;
        if (on) {
            line->h2b0b = b0; line->h2b1b = b1; line->h2b2b = b2;
            line->h2a1b = a1; line->h2a2b = a2;
        }
    } else {
        line->sh2On = on;
        if (on) {
            line->h2b0 = b0; line->h2b1 = b1; line->h2b2 = b2;
            line->h2a1 = a1; line->h2a2 = a2;
        }
    }
}

static double src_step(SrcFilt *f, double x) {
    double v, o, lp;
    if (!f->on) return x;
    v = f->g * x;
    o = f->b0 * v + f->z1;
    f->z1 = f->b1 * v - f->a1 * o + f->z2;
    f->z2 = f->b2 * v - f->a2 * o;
    if (f->pg > 0.0) {
        f->pz += f->pg * (o - f->pz);
        lp = f->pz;
        if (f->order >= 2) {
            f->pz2 += f->pg * (f->pz - f->pz2);
            lp = f->pz2;
        }
        o = (1.0 - f->pm) * o + f->pm * lp;
    }
    if (!finite_d(o) || !finite_d(f->z1) || !finite_d(f->z2)) {
        f->z1 = f->z2 = f->pz = f->pz2 = 0.0;
        f->on = 0;
        return x;
    }
    f->z1 = ls_flush(f->z1);
    f->z2 = ls_flush(f->z2);
    f->pz = ls_flush(f->pz);
    f->pz2 = ls_flush(f->pz2);
    return o;
}

static void load_src_filt(Rd *r, SrcFilt *f, int with_pole) {
    f->g = rf(r);
    f->b0 = rf(r);
    f->b1 = rf(r);
    f->b2 = rf(r);
    f->a1 = rf(r);
    f->a2 = rf(r);
    if (with_pole) {
        f->pg = rf(r);
        f->pm = rf(r);
        f->order = (int)rf(r);
        f->on = rf(r) > 0.5;
    } else {
        f->pg = 0.0;
        f->pm = 0.0;
        f->order = 1;
        f->on = rf(r) > 0.5;
    }
    if (!finite_d(f->g) || !finite_d(f->b0) || !finite_d(f->a1)) f->on = 0;
    if (f->order < 1) f->order = 1;
    if (f->order > 2) f->order = 2;
}

/* SRC_RAD: 2 flags + 2 × (diffuse 7 + direct 30 + image 320) = 716. Else bypass. */
static void load_src_section(LiveStereo *st, int off, int n) {
    Rd r;
    int s, i;
    if (n != 716) return;
    if (off < 0 || off + n > MAX_BLOB) return;
    r.p = st->blob;
    r.i = off;
    r.n = off + n;
    st->radA = rf(&r) > 0.5;
    st->radB = rf(&r) > 0.5;
    for (s = 0; s < 2; s++) {
        load_src_filt(&r, &st->srcDiff[s], 0);
        for (i = 0; i < 3; i++) load_src_filt(&r, &st->srcDir[s][i], 1);
        for (i = 0; i < N; i++) load_src_filt(&r, &st->srcImg[s][i], 1);
    }
}

/* SURF v0 is 192 gate floats. v1 is those gates plus [1, K_max] and the
   per-line cascades. Any other length leaves the gate off and the cascade off. */
static void load_surf_section(LiveStereo *st, int off, int n) {
    Rd r;
    int b, i, kmax, ver, expect, any, s;
    if (off < 0 || off + n > MAX_BLOB) return;
    if (n == 3 * 64) {
        r.p = st->blob; r.i = off; r.n = off + n;
        for (b = 0; b < 3; b++) {
            for (i = 0; i < N; i++) st->earlyGate[b][i] = rf(&r);
            for (i = 0; i < N; i++) st->earlyGateB[b][i] = rf(&r);
        }
        st->earlyGateOn = 1;
        return;
    }
    if (n < 192 + 2) return;
    ver = (int)(st->blob[off + 192] + 0.5);
    kmax = (int)(st->blob[off + 193] + 0.5);
    if (ver != 1 || kmax < 1 || kmax > SURF_K_MAX) return;
    expect = 192 + 2 + (2 * N) * (1 + 5 * kmax);
    if (n != expect) return;
    r.p = st->blob; r.i = off; r.n = off + n;
    for (b = 0; b < 3; b++) {
        for (i = 0; i < N; i++) st->earlyGate[b][i] = rf(&r);
        for (i = 0; i < N; i++) st->earlyGateB[b][i] = rf(&r);
    }
    st->earlyGateOn = 1;
    (void)rf(&r);
    (void)rf(&r);
    any = 0;
    for (b = 0; b < 2; b++) {
        for (i = 0; i < N; i++) {
            int k = (int)(rf(&r) + 0.5);
            SurfCas *img = &st->sfI[b][i];
            SurfCas *dif = &st->sfD[b][i];
            if (k < 0) k = 0;
            if (k > kmax) k = kmax;
            for (s = 0; s < kmax; s++) {
                double b0 = rf(&r), b1 = rf(&r), b2 = rf(&r), a1 = rf(&r), a2 = rf(&r);
                if (!finite_d(b0) || !finite_d(b1) || !finite_d(b2) || !finite_d(a1) || !finite_d(a2)) {
                    k = 0;
                    b0 = 1.0;
                    b1 = b2 = a1 = a2 = 0.0;
                }
                if (s < SURF_K_MAX) {
                    img->c[s][0] = dif->c[s][0] = b0;
                    img->c[s][1] = dif->c[s][1] = b1;
                    img->c[s][2] = dif->c[s][2] = b2;
                    img->c[s][3] = dif->c[s][3] = a1;
                    img->c[s][4] = dif->c[s][4] = a2;
                }
            }
            img->k = k;
            dif->k = k;
            if (k > 0) any = 1;
        }
    }
    st->surfOn = any;
    soa_build(st);
}

/* AIR section: 3 buses × (32 A + 32 B) × 6 floats. Any other length is a bypass. */
static void load_sh2_section(LiveStereo *st, int off, int n) {
    Rd r;
    int b, i;
    if (n != 3 * 64 * 6) return;
    if (off < 0 || off + n > MAX_BLOB) return;
    r.p = st->blob; r.i = off; r.n = off + n;
    for (b = 0; b < 3; b++) {
        for (i = 0; i < N; i++) load_sh2_one(&r, &st->bus[b].line[i], 0);
        for (i = 0; i < N; i++) load_sh2_one(&r, &st->bus[b].line[i], 1);
    }
}

/* 0..1 hash of a delay target, 1/16-sample grid, seed 1. Mirror-safe when
   keyed on the partner bus. Computed at load, not per sample. */
static double shared_jit(double d) {
    unsigned u = (unsigned)(d * 16.0 + 0.5) + 0x9e3779b9U * 1u;
    u ^= u >> 16;
    u *= 0x7feb352dU;
    u ^= u >> 15;
    u *= 0x846ca68bU;
    u ^= u >> 16;
    return (double)u * (1.0 / 4294967296.0);
}

static int centre_empty(const LiveStereo *st) {
    int i, e = st->micG[BUS_C] == 0.0;
    for (i = 0; e && i < N; i++) {
        if (st->bus[BUS_C].line[i].inj != 0.0 || st->bus[BUS_C].line[i].injB != 0.0) e = 0;
    }
    return e;
}

static unsigned delay_sig(const LiveStereo *st) {
    unsigned u = 2166136261u;
    int b, i;
    for (b = 0; b < 3; b++) {
        for (i = 0; i < N; i++) {
            const Line *ln = &st->bus[b].line[i];
            unsigned a = (unsigned)(ln->delayT * 16.0 + 0.5);
            unsigned c = (unsigned)(ln->delayBT * 16.0 + 0.5);
            u ^= a + 0x9e3779b9u + (u << 6) + (u >> 2);
            u ^= c + 0x9e3779b9u + (u << 6) + (u >> 2);
        }
    }
    return u;
}

/* injS over the three real mics. Stereo always has a centre; binaural never
   reaches here (the empty centre forces shared off). No virtual centre. */
static void shared_prepare(LiveStereo *st) {
    int i, b;
    double es = 0.0, esB = 0.0;
    double eb[3] = {0.0, 0.0, 0.0};
    double ebB[3] = {0.0, 0.0, 0.0};
    double js = 300.0e-6 * (double)st->sr;
    int mics[3] = {BUS_L, BUS_R, BUS_C};
    for (i = 0; i < N; i++) {
        double s = 0.0, q = 0.0, sB = 0.0, qB = 0.0;
        Line *c = &st->bus[BUS_C].line[i];
        for (b = 0; b < 3; b++) {
            Line *m = &st->bus[mics[b]].line[i];
            s += m->inj;
            q += m->inj * m->inj;
            sB += m->injB;
            qB += m->injB * m->injB;
            eb[mics[b]] += m->inj * m->inj;
            ebB[mics[b]] += m->injB * m->injB;
        }
        st->shInjS[i] = (s < 0.0 ? -1.0 : 1.0) * ls_sqrt(q / 3.0);
        st->shInjSB[i] = (sB < 0.0 ? -1.0 : 1.0) * ls_sqrt(qB / 3.0);
        st->shRS[i] = c->inj != 0.0 ? st->shInjS[i] / c->inj : 0.0;
        es += q / 3.0;
        esB += qB / 3.0;
    }
    for (b = 0; b < 3; b++) {
        int key = b == BUS_L ? BUS_R : (b == BUS_R ? BUS_L : BUS_C);
        for (i = 0; i < N; i++) {
            Line *m = &st->bus[b].line[i];
            st->shJit[b][i] = js * shared_jit(st->bus[key].line[i].delayT + (b == BUS_C ? 0.5 : 0.0));
            st->shJitB[b][i] = js * shared_jit(st->bus[key].line[i].delayBT + (b == BUS_C ? 0.5 : 0.0));
        }
        st->bus[b].shG = es > 0.0 ? ls_sqrt(eb[b] / es) : 0.0;
        st->bus[b].shGB = esB > 0.0 ? ls_sqrt(ebB[b] / esB) : 0.0;
    }
}

/* On/off edge, or a delay change while the option stays on, drops the tail
   so a stale tap does not play. A wet-fader reload with the same delays does not. */
static void finish_shared(LiveStereo *st, int prevShared, unsigned prevSig) {
    int next = st->sharedReq && !centre_empty(st);
    unsigned sig;
    if (next) shared_prepare(st);
    sig = delay_sig(st);
    if (next != prevShared || (next && sig != prevSig)) clear_line_lanes(st, 0);
    st->shared = next;
    st->delaySig = sig;
}

static void arm_ramps(LiveStereo *st);

static void mod_clear(LiveStereo *st) {
    int b, i;
    st->modOn = 0;
    st->modA = 0.0;
    st->modAbs = 0.0;
    for (b = 0; b < 3; b++) {
        for (i = 0; i < N; i++) {
            Line *line = &st->bus[b].line[i];
            line->modOn = 0;
            line->modOnB = 0;
            line->modYap = 0.0;
            line->modYapB = 0.0;
        }
    }
}

/* order[1::2] after a stable sort by (delay, index). k is the enumerate
   index among those 16 lines, not the line index. Bank A and bank B sort
   apart. Each of the three buses is its own tank. */
static void mod_arm_bank(LiveStereo *st, int bus, int bankB) {
    int order[N];
    int i, j, k, nmod;
    double delays[N];
    double sr, phi = 0.6180339887498949;
    for (i = 0; i < N; i++) {
        Line *line = &st->bus[bus].line[i];
        delays[i] = bankB ? line->delayBT : line->delayT;
        order[i] = i;
        if (bankB) {
            line->modOnB = 0;
            line->modYapB = 0.0;
        } else {
            line->modOn = 0;
            line->modYap = 0.0;
        }
    }
    for (i = 1; i < N; i++) {
        int key = order[i];
        double kd = delays[key];
        j = i - 1;
        while (j >= 0) {
            int oj = order[j];
            if (delays[oj] < kd || (delays[oj] == kd && oj < key)) break;
            order[j + 1] = oj;
            j--;
        }
        order[j + 1] = key;
    }
    sr = (double)st->sr;
    if (sr < 1.0) sr = 48000.0;
    nmod = 0;
    for (k = 1; k < N; k += 2) {
        int idx = order[k];
        double u = (double)nmod * phi;
        double r = 0.6 + 0.8 * (u - (double)(int)u);
        double w = 2.0 * 3.14159265358979323846 * 0.7 * r / sr;
        double ph = (112.5 * (double)nmod) * 3.14159265358979323846 / 180.0;
        Line *line = &st->bus[bus].line[idx];
        if (bankB) {
            line->modOnB = 1;
            line->modWB = w;
            line->modPhB = ph;
        } else {
            line->modOn = 1;
            line->modW = w;
            line->modPh = ph;
        }
        nmod++;
    }
}

static void mod_apply(LiveStereo *st, double peakMs) {
    int b;
    if (peakMs <= 0.0 || st->hn != 32) {
        mod_clear(st);
        return;
    }
    st->modOn = 1;
    st->modA = peakMs * 1e-3 * (double)st->sr;
    st->modAbs = 0.0;
    for (b = 0; b < 3; b++) {
        mod_arm_bank(st, b, 0);
        mod_arm_bank(st, b, 1);
    }
}

LS_EXPORT("live_load_room")
void live_load_room(LiveStereo *st, int n) {
    Rd r;
    int magic, nsec, s, core;
    int id[16], off[16], ln[16];
    int prevShared;
    unsigned prevSig;
    if (!st || st->magic != 0x2011 || n < 16) return;
    /* Absent section 9 is off. Absent section 13 is off. Magic 1 returns early. */
    st->subHpOn = 0;
    st->sideHot = 0;
    st->sideComp[0] = st->sideComp[1] = 0;
    st->sidePre[0] = st->sidePre[1] = 0;
    st->sidePlace[0] = st->sidePlace[1] = st->sidePlace[2] = 0;
    prevShared = st->shared;
    prevSig = st->delaySig;
    if (n > MAX_BLOB) n = MAX_BLOB;
    r.p = st->blob; r.i = 0; r.n = n;
    magic = (int)rf(&r);
    if (magic == 1) {
        clear_sh2_on(st);
        st->radA = 0;
        st->radB = 0;
        st->earlyGateOn = 0;
        st->surfOn = 0;
        st->deskOn = 0;
        load_core_body(st, &r);
        st->sharedReq = 0;
        finish_shared(st, prevShared, prevSig);
        st->icOn = 0;
        mod_apply(st, 0.0);
        arm_ramps(st);
        bloom_arm(st, 0, 0, 0, 0, 0.0f, 0, 0, 0);
        return;
    }
    if (magic != 2) return;
    (void)rf(&r);
    (void)rf(&r);
    nsec = (int)rf(&r);
    (void)rf(&r);
    if (nsec < 1 || nsec > 16) return;
    for (s = 0; s < nsec; s++) {
        id[s] = (int)rf(&r);
        off[s] = (int)rf(&r);
        ln[s] = (int)rf(&r);
        (void)rf(&r);
    }
    core = -1;
    for (s = 0; s < nsec; s++) {
        if (id[s] == 1 && ln[s] >= 16 && off[s] >= 0 && off[s] + ln[s] <= n) core = s;
    }
    if (core < 0) return;
    clear_sh2_on(st);
    st->radA = 0;
    st->radB = 0;
    st->earlyGateOn = 0;
    st->surfOn = 0;
    st->deskOn = 0;
    st->sharedReq = 0;
    r.p = st->blob;
    r.i = off[core];
    r.n = off[core] + ln[core];
    load_core_body(st, &r);
    for (s = 0; s < nsec; s++) {
        if (id[s] != 2) continue;
        if (ln[s] < 1 || off[s] < 0 || off[s] + ln[s] > n) continue;
        load_sh2_section(st, off[s], ln[s]);
    }
    for (s = 0; s < nsec; s++) {
        if (id[s] != 5) continue;
        if (ln[s] < 1 || off[s] < 0 || off[s] + ln[s] > n) continue;
        load_src_section(st, off[s], ln[s]);
    }
    for (s = 0; s < nsec; s++) {
        if (id[s] != 3) continue;
        if (ln[s] < 1 || off[s] < 0 || off[s] + ln[s] > n) continue;
        load_surf_section(st, off[s], ln[s]);
    }
    for (s = 0; s < nsec; s++) {
        if (id[s] != 6) continue;
        if (ln[s] < 1 || off[s] < 0 || off[s] + ln[s] > n) continue;
        st->sharedReq = st->blob[off[s]] > 0.5f;
    }
    for (s = 0; s < nsec; s++) {
        if (id[s] != 7) continue;
        if (ln[s] < 6 || off[s] < 0 || off[s] + ln[s] > n) continue;
        st->deskW[0][0] = st->blob[off[s] + 0];
        st->deskW[0][1] = st->blob[off[s] + 1];
        st->deskW[1][0] = st->blob[off[s] + 2];
        st->deskW[1][1] = st->blob[off[s] + 3];
        st->deskW[2][0] = st->blob[off[s] + 4];
        st->deskW[2][1] = st->blob[off[s] + 5];
        st->deskOn = 1;
    }
    {
        /* Section 8 is one float, peak depth in ms. Absent means Movement 0. */
        double peak = 0.0;
        for (s = 0; s < nsec; s++) {
            if (id[s] != 8) continue;
            if (ln[s] < 1 || off[s] < 0 || off[s] + ln[s] > n) continue;
            peak = (double)st->blob[off[s]];
        }
        mod_apply(st, peak);
    }
    for (s = 0; s < nsec; s++) {
        /* Section 9 is five Butterworth coefficients. Absent stays off. */
        if (id[s] != 9) continue;
        if (ln[s] < 5 || off[s] < 0 || off[s] + ln[s] > n) continue;
        st->subB0 = (double)st->blob[off[s] + 0];
        st->subB1 = (double)st->blob[off[s] + 1];
        st->subB2 = (double)st->blob[off[s] + 2];
        st->subA1 = (double)st->blob[off[s] + 3];
        st->subA2 = (double)st->blob[off[s] + 4];
        st->subHpOn = 1;
    }
    {
        int has10 = 0, has11 = 0, has12 = 0, n10 = 0, n12 = 0, bs;
        const float *c10 = 0;
        const float *c12 = 0;
        float pd = 0.0f;
        for (bs = 0; bs < nsec; bs++) {
            if (ln[bs] < 1 || off[bs] < 0 || off[bs] + ln[bs] > n) continue;
            if (id[bs] == 10 && ln[bs] >= 40) {
                has10 = 1;
                c10 = st->blob + off[bs];
                n10 = ln[bs];
            } else if (id[bs] == 11) {
                has11 = 1;
                pd = st->blob[off[bs]];
            } else if (id[bs] == 12 && ln[bs] >= 25) {
                has12 = 1;
                c12 = st->blob + off[bs];
                n12 = ln[bs];
            }
        }
        bloom_arm(st, has10, c10, n10, has11, pd, has12, c12, n12);
    }
    for (s = 0; s < nsec; s++) {
        /* Section 13. One side-insert block. Absent stays off. */
        if (id[s] != 13) continue;
        if (ln[s] < 217 || off[s] < 0 || off[s] + ln[s] > n) continue;
        load_side_section(st, off[s]);
    }
    finish_shared(st, prevShared, prevSig);
    st->icOn = 0;
    arm_ramps(st);
}

static void zero_filts(LiveStereo *st) {
    int i;
    int n = MAX_FILT * MAX_PART * FFTN;
    ls_zero(st->fdlRe, n * (int)sizeof(float));
    ls_zero(st->fdlIm, n * (int)sizeof(float));
    for (i = 0; i < MAX_FILT; i++) {
        ls_zero(st->filt[i].prev, PART * (int)sizeof(float));
        ls_zero(st->filt[i].sz, (int)sizeof(st->filt[i].sz));
        st->filt[i].pos = 0;
        st->filt[i].cold = MAX_PART;
    }
}

/* Colour entry: FIR impulse, or SOS [-2011, K, (b0 b1 b2 a1 a2) × K]. */
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
    if (len < 1) len = 1;
    if (len > 8192) len = 8192;
    npart = (len + PART - 1) / PART;
    if (npart > MAX_PART) npart = MAX_PART;
    st->irLen[ir] = len;
    st->irNpart[ir] = npart;
    base = ir * MAX_PART * FFTN;
    ls_zero(st->specRe + base, MAX_PART * FFTN * (int)sizeof(float));
    ls_zero(st->specIm + base, MAX_PART * FFTN * (int)sizeof(float));
    for (p = 0; p < npart; p++) {
        int off = p * PART;
        int n = len - off;
        if (n > PART) n = PART;
        if (n < 0) n = 0;
        for (i = 0; i < FFTN; i++) { g_re[i] = 0; g_im[i] = 0; }
        for (i = 0; i < n; i++) g_re[i] = src[off + i];
        fft_complex(g_re, g_im, 0);
        ls_copy(st->specRe + base + p * FFTN, g_re, FFTN * (int)sizeof(float));
        ls_copy(st->specIm + base + p * FFTN, g_im, FFTN * (int)sizeof(float));
    }
}

LS_EXPORT("live_load_irs")
void live_load_irs(LiveStereo *st, int nIrs) {
    int i, o;
    if (!st || st->magic != 0x2011) return;
    if (nIrs < 0) nIrs = 0;
    if (nIrs > MAX_IRS) {
        st->n_irs = 0;
        st->colour_on = 0;
        zero_filts(st);
        return;
    }
    o = 0;
    for (i = 0; i < nIrs; i++) {
        int len = st->lenScratch[i];
        if (len < 0) len = 0;
        if (o + len > MAX_IR_FLOATS) len = MAX_IR_FLOATS - o;
        if (len < 0) len = 0;
        design_ir(st, i, st->irScratch + o, len);
        o += len;
    }
    st->n_irs = nIrs;
    zero_filts(st);
}

LS_EXPORT("live_load_route")
void live_load_route(LiveStereo *st) {
    int o, b, i;
    const int *r;
    if (!st || st->magic != 0x2011) return;
    r = st->routeScratch;
    o = 0;
    for (b = 0; b < 3; b++) {
        for (i = 0; i < N; i++) st->fdnIdx[b][i] = r[o++];
    }
    for (b = 0; b < 2; b++) {
        for (i = 0; i < N; i++) st->earlyIdx[b][i] = r[o++];
    }
    for (b = 0; b < 2; b++) {
        for (i = 0; i < N; i++) st->earlyBIdx[b][i] = r[o++];
    }
    for (b = 0; b < 3; b++) st->directIdx[b] = r[o++];
    for (b = 0; b < 3; b++) st->directBIdx[b] = r[o++];
    for (b = 0; b < 3; b++) {
        for (i = 0; i < N; i++) st->fdnIdxB[b][i] = r[o++];
    }
}

LS_EXPORT("live_ic_ptr")
float *live_ic_ptr(LiveStereo *st) { return st ? st->icBuf : 0; }

/* hp[n] then hm[n] in icBuf. n is odd, at most 513. Clears the FIR history. */
LS_EXPORT("live_load_ic")
void live_load_ic(LiveStereo *st, int n) {
    int i;
    if (!st || st->magic != 0x2011) return;
    if (n < 1 || n > 513 || (n & 1) == 0) {
        st->icOn = 0;
        st->icN = 0;
        return;
    }
    for (i = 0; i < n; i++) {
        st->icHp[i] = st->icBuf[i];
        st->icHm[i] = st->icBuf[n + i];
    }
    for (i = 0; i < 512; i++) {
        st->icHistM[i] = 0;
        st->icHistS[i] = 0;
    }
    st->icN = n;
    st->icOn = 1;
}

LS_EXPORT("live_force_delay")
void live_force_delay(LiveStereo *st, float samples) {
    double d;
    int b, i;
    if (!st || st->magic != 0x2011) return;
    d = (double)samples;
    if (d < 2.0) d = 2.0;
    if (d > (double)st->maxDelay) d = (double)st->maxDelay;
    for (b = 0; b < 3; b++) {
        st->bus[b].dirD = d;
        st->bus[b].dirDT = d;
        st->bus[b].dirDB = d;
        st->bus[b].dirDBT = d;
        for (i = 0; i < N; i++) {
            st->bus[b].line[i].delay = d;
            st->bus[b].line[i].delayT = d;
            st->bus[b].line[i].delayB = d;
            st->bus[b].line[i].delayBT = d;
        }
    }
}

LS_EXPORT("live_probe")
float live_probe(LiveStereo *st, int bus, int line, int which, int back) {
    float *bptr;
    int w, i, lane;
    if (!st || st->magic != 0x2011) return 0;
    if (bus < 0 || bus > 2) return 0;
    if (line < 0) line = 0;
    if (line > N - 1) line = N - 1;
    if (which == 4) { bptr = st->dir[bus]; w = st->bus[bus].dirW; lane = -1; }
    else if (which == 5) { bptr = st->dirB[bus]; w = st->bus[bus].dirWB; lane = -1; }
    else {
        w = st->bus[bus].line[line].w;
        bptr = st->ring[bus][line];
        if (which == 1) lane = LANE_FDNB;
        else if (which == 2) lane = LANE_EARLY;
        else if (which == 3) lane = LANE_EARLYB;
        else lane = LANE_FDN;
    }
    i = w - 1 - back;
    while (i < 0) i += st->cap;
    while (i >= st->cap) i -= st->cap;
    if (lane < 0) return bptr[i];
    return bptr[i * LANES + lane];
}

static void write_lane(float *ring, int w, int lane, float v) {
    ring[w * LANES + lane] = v;
}

/* Frenette first-order allpass. Centre is this engine's nominal delay.
   D = delay + A*sin(w*t+ph); N = floor(D-0.5); dl = D-N;
   eta = (1-dl)/(1+dl);
   y = eta*x[n-N] + x[n-N-1] - eta*y[n-1].
   The ring already stores the sample written into the delay. Coefficient
   updates every sample. A = 0 is not used: Movement 0 keeps read_lane. */
static int ls_ifloor(double x) {
    int n = (int)x;
    if ((double)n > x) n -= 1;
    return n;
}

static double ls_sin_ang(double ang) {
    const double twopi = 6.28318530717958647692;
    const double pi = 3.14159265358979323846;
    double q = ang / twopi;
    double ip;
    if (q >= 0.0) ip = (double)(unsigned long long)q;
    else {
        ip = (double)ls_ifloor(q);
    }
    ang = (q - ip) * twopi;
    if (ang > pi) ang -= twopi;
    if (ang < -pi) ang += twopi;
    return ls_sin(ang);
}

static int ring_at(int w, int back, int cap) {
    int i;
    if (cap < 1) return 0;
    i = w - back;
    if (i >= cap || i < 0) {
        i %= cap;
        if (i < 0) i += cap;
    }
    return i;
}

static double read_mod_allpass(LiveStereo *st, Line *line, const float *ring, int lane, int i, int bankB, double delay) {
    double A = st->modA;
    double w = bankB ? line->modWB : line->modW;
    double ph = bankB ? line->modPhB : line->modPh;
    double *yap = bankB ? &line->modYapB : &line->modYap;
    double D = delay + A * ls_sin_ang(w * st->absT + ph);
    int Nlag = ls_ifloor(D - 0.5);
    double dl = D - (double)Nlag;
    double eta = (1.0 - dl) / (1.0 + dl);
    int cap = st->cap;
    double xN = (double)ring[ring_at(line->w, Nlag, cap) * LANES + lane];
    double xN1 = (double)ring[ring_at(line->w, Nlag + 1, cap) * LANES + lane];
    double y = eta * xN + xN1 - eta * (*yap);
    *yap = y;
    return y;
}

static double read_lane(const float *ring, int lane, int w, double delay, int cap) {
    double r, frac, a, b;
    int i0, i1;
    r = (double)w - delay;
    if (r < 0.0) r += (double)cap;
    if (r >= (double)cap) r -= (double)cap;
    if (r < 0.0) r = 0.0;
    i0 = (int)r;
    if (i0 >= cap) i0 = 0;
    if (i0 < 0) i0 = 0;
    frac = r - (double)i0;
    if (frac < 0.0) frac = 0.0;
    else if (frac > 1.0) frac = 1.0;
    i1 = i0 + 1;
    if (i1 >= cap) i1 = 0;
    a = (double)ring[i0 * LANES + lane];
    b = (double)ring[i1 * LANES + lane];
    return a + frac * (b - a);
}

static double read_lin(const float *buf, int w, double delay, int cap) {
    double r, frac, a, b;
    int i0, i1;
    r = (double)w - delay;
    if (r < 0.0) r += (double)cap;
    if (r >= (double)cap) r -= (double)cap;
    if (r < 0.0) r = 0.0;
    i0 = (int)r;
    if (i0 >= cap) i0 = 0;
    if (i0 < 0) i0 = 0;
    frac = r - (double)i0;
    if (frac < 0.0) frac = 0.0;
    else if (frac > 1.0) frac = 1.0;
    i1 = i0 + 1;
    if (i1 >= cap) i1 = 0;
    a = (double)buf[i0];
    b = (double)buf[i1];
    return a + frac * (b - a);
}

static void adv(int *w, int cap) {
    int n = *w + 1;
    if (n >= cap) n = 0;
    *w = n;
}

/* n is a literal so the butterflies unroll. Same adds and subtracts as the old loop. */
#define FWHT_BODY(NFIX) \
    do { \
        int len, step, i, j; \
        for (len = 1; len < (NFIX); len = step) { \
            step = len << 1; \
            for (i = 0; i < (NFIX); i += step) { \
                for (j = 0; j < len; j++) { \
                    double u = a[i + j]; \
                    double v = a[i + j + len]; \
                    a[i + j] = u + v; \
                    a[i + j + len] = u - v; \
                } \
            } \
        } \
    } while (0)

static void fwht8(double *a) { FWHT_BODY(8); }
static void fwht16(double *a) { FWHT_BODY(16); }
/* H·D. d is not a Walsh row, so no row of H·D is parallel to the all-ones sum.
   The output tap and the first pass stay +1. Plain H when loop_semantics is 1. */
static const double CSIGN_D[32] = {
    1.0, -1.0, -1.0, -1.0, -1.0, -1.0, 1.0, -1.0,
    -1.0, 1.0, -1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
    -1.0, 1.0, 1.0, 1.0, -1.0, 1.0, 1.0, 1.0,
    -1.0, 1.0, 1.0, 1.0, -1.0, 1.0, 1.0, 1.0
};
/* Shared loop only. CSIGN_D with the mirror orbit {3,24} flipped. Invariant under
   pi = (b0 b4)(b1 b3), so the mirror stays exact; not a Walsh row (max|Hd|/32 = 0.375).
   Lowers shared-tail L/R LF coherence and keeps the LF spectrum of the H.D loop (P6). */
static const double CSIGN_DS[32] = {
    1.0, -1.0, -1.0,  1.0, -1.0, -1.0,  1.0, -1.0,
   -1.0,  1.0, -1.0,  1.0,  1.0,  1.0,  1.0,  1.0,
   -1.0,  1.0,  1.0,  1.0, -1.0,  1.0,  1.0,  1.0,
    1.0,  1.0,  1.0,  1.0, -1.0,  1.0,  1.0,  1.0
};
static const double *g_csignTab = CSIGN_D;
static int g_csign = 1;
static void fwht32(double *a) {
    if (g_csign) {
        int k;
        for (k = 0; k < 32; k++) a[k] *= g_csignTab[k];
    }
    FWHT_BODY(32);
}

typedef void (*FwhtFn)(double *a);
typedef void (*DiffuseFn)(LiveStereo *st, int b, int bankB, const double *xin, double *fb, double *yOut);

static double sh2_step(double xin, int on, double b0, double b1, double b2,
    double a1, double a2, double *s1, double *s2) {
    double yi;
    if (!on) return xin;
    yi = b0 * xin + *s1;
    *s1 = b1 * xin - a1 * yi + *s2;
    *s2 = b2 * xin - a2 * yi;
    return yi;
}

static double tint(Line *line, double xin, int kind) {
    double g, z, lp, b0, b1, b2, a1, a2, s1, s2, yi;
    double q0, q1, q2, p1, p2, u1, u2;
    int on, on2;
    lp = line->airLp;
    if (kind == 3) {
        g = line->airGb; z = line->airZf; on = line->shelfOnB;
        b0 = line->sb0b; b1 = line->sb1b; b2 = line->sb2b;
        a1 = line->sa1b; a2 = line->sa2b; s1 = line->sz1f; s2 = line->sz2f;
        on2 = line->sh2OnB;
        q0 = line->h2b0b; q1 = line->h2b1b; q2 = line->h2b2b;
        p1 = line->h2a1b; p2 = line->h2a2b; u1 = line->h2z1f; u2 = line->h2z2f;
    } else if (kind == 2) {
        g = line->airGb; z = line->airZb; on = line->shelfOnB;
        b0 = line->sb0b; b1 = line->sb1b; b2 = line->sb2b;
        a1 = line->sa1b; a2 = line->sa2b; s1 = line->sz1b; s2 = line->sz2b;
        on2 = line->sh2OnB;
        q0 = line->h2b0b; q1 = line->h2b1b; q2 = line->h2b2b;
        p1 = line->h2a1b; p2 = line->h2a2b; u1 = line->h2z1b; u2 = line->h2z2b;
    } else if (kind == 1) {
        g = line->airG; z = line->airZe; on = line->shelfOn;
        b0 = line->sb0; b1 = line->sb1; b2 = line->sb2;
        a1 = line->sa1; a2 = line->sa2; s1 = line->sz1e; s2 = line->sz2e;
        on2 = line->sh2On;
        q0 = line->h2b0; q1 = line->h2b1; q2 = line->h2b2;
        p1 = line->h2a1; p2 = line->h2a2; u1 = line->h2z1e; u2 = line->h2z2e;
    } else {
        g = line->airG; z = line->airZ; on = line->shelfOn;
        b0 = line->sb0; b1 = line->sb1; b2 = line->sb2;
        a1 = line->sa1; a2 = line->sa2; s1 = line->sz1; s2 = line->sz2;
        on2 = line->sh2On;
        q0 = line->h2b0; q1 = line->h2b1; q2 = line->h2b2;
        p1 = line->h2a1; p2 = line->h2a2; u1 = line->h2z1; u2 = line->h2z2;
    }
    if (lp > 0.0 && g > 0.0) {
        z += g * (xin - z);
        xin = (1.0 - lp) * xin + lp * z;
    }
    if (on) {
        yi = b0 * xin + s1;
        s1 = b1 * xin - a1 * yi + s2;
        s2 = b2 * xin - a2 * yi;
        xin = yi;
    }
    xin = sh2_step(xin, on2, q0, q1, q2, p1, p2, &u1, &u2);
    z = ls_flush(z);
    s1 = ls_flush(s1);
    s2 = ls_flush(s2);
    u1 = ls_flush(u1);
    u2 = ls_flush(u2);
    if (kind == 3) {
        line->airZf = z; line->sz1f = s1; line->sz2f = s2;
        line->h2z1f = u1; line->h2z2f = u2;
    } else if (kind == 2) {
        line->airZb = z; line->sz1b = s1; line->sz2b = s2;
        line->h2z1b = u1; line->h2z2b = u2;
    } else if (kind == 1) {
        line->airZe = z; line->sz1e = s1; line->sz2e = s2;
        line->h2z1e = u1; line->h2z2e = u2;
    } else {
        line->airZ = z; line->sz1 = s1; line->sz2 = s2;
        line->h2z1 = u1; line->h2z2 = u2;
    }
    return xin;
}

/* SL3. Integer or Movement read, then lg. Sections run on st->delayed before the kept peaks. */
static double read_raw_lg(LiveStereo *st, Line *line, const float *ring, int lane, int i, int bankB, double delay) {
    double raw;
    if (st->modOn && (bankB ? line->modOnB : line->modOn))
        raw = read_mod_allpass(st, line, ring, lane, i, bankB, delay);
    else
        raw = read_lane(ring, lane, line->w, delay, st->cap);
    return (bankB ? line->lgB : line->lg) * raw;
}

static double apply_kept_peak(LiveStereo *st, Line *line, int i, int bankB, double v) {
    int ax = i % 3;
    double *z1, *z2, yi, nz1, nz2;
    if (!st->slKeep[ax]) return v;
    z1 = bankB ? &line->pz1b : &line->pz1;
    z2 = bankB ? &line->pz2b : &line->pz2;
    yi = st->slPk[ax][0] * v + *z1;
    nz1 = st->slPk[ax][1] * v - st->slPk[ax][3] * yi + *z2;
    nz2 = st->slPk[ax][2] * v - st->slPk[ax][4] * yi;
    *z1 = nz1;
    *z2 = nz2;
    return yi;
}

static void surf_batch(LiveStereo *st, int b, int bankB, int hn) {
    int k, i;
    double *v = st->delayed;
    for (k = 0; k < SL_SEC; k++) {
        const double (*C)[5][N] = bankB ? st->slCB[b] : st->slC[b];
        const double *c0 = C[k][0], *c1 = C[k][1], *c2 = C[k][2];
        const double *c3 = C[k][3], *c4 = C[k][4];
        double *z1 = st->slZ[b][bankB][k][0], *z2 = st->slZ[b][bankB][k][1];
        for (i = 0; i < hn; i++) {
            double x = v[i];
            double y = c0[i] * x + z1[i];
            z1[i] = c1[i] * x - c3[i] * y + z2[i];
            z2[i] = c2[i] * x - c4[i] * y;
            v[i] = y;
        }
    }
}

static double read_peaked(LiveStereo *st, Line *line, const float *ring, int lane, int i, int bankB, double delay) {
    double v, yi, nz1, nz2;
    int ax = i % 3;
    double *z1, *z2;
    double raw;
    if (st->modOn && (bankB ? line->modOnB : line->modOn))
        raw = read_mod_allpass(st, line, ring, lane, i, bankB, delay);
    else
        raw = read_lane(ring, lane, line->w, delay, st->cap);
    v = (bankB ? line->lgB : line->lg) * raw;
    if (!st->peakOn[ax]) return v;
    z1 = bankB ? &line->pz1b : &line->pz1;
    z2 = bankB ? &line->pz2b : &line->pz2;
    yi = st->pb0[ax] * v + *z1;
    nz1 = st->pb1[ax] * v - st->pa1[ax] * yi + *z2;
    nz2 = st->pb2[ax] * v - st->pa2[ax] * yi;
    *z1 = nz1;
    *z2 = nz2;
    return yi;
}

/* ROOMTONE. DF1 on this line's own axis, after read_peaked or apply_kept_peak.
   The caller skips this when harmOn is 0, so a gated-off room does no extra math. */
static double apply_harm(LiveStereo *st, int b, int i, int bankB, double v) {
    int ax = i % 3;
    int k, n = st->harmN[ax];
    for (k = 0; k < n; k++) {
        double *c = st->harmC[ax][k];
        double *z1 = &st->harmZ[b][bankB][k][0][i];
        double *z2 = &st->harmZ[b][bankB][k][1][i];
        double yi = c[0] * v + *z1;
        double nz1 = c[1] * v - c[3] * yi + *z2;
        double nz2 = c[2] * v - c[4] * yi;
        *z1 = nz1;
        *z2 = nz2;
        v = yi;
    }
    return v;
}

#define DIFFUSE_FN(name, HN, FW) \
static void name(LiveStereo *st, int b, int bankB, const double *xin, double *fb, double *yOut) { \
    Bus *bus = &st->bus[b]; \
    int i; \
    double g; \
    for (i = 0; i < (HN); i++) { \
        Line *line = &bus->line[i]; \
        double gi = bankB ? line->dffsB : line->dffs; \
        double s = xin[i] + fb[i]; \
        double y = -gi * s + st->delayed[i]; \
        write_lane(st->ring[b][i], line->w, bankB ? LANE_FDNB : LANE_FDN, (float)(s + gi * y)); \
        yOut[i] = y; \
        st->reads[i] = y; \
    } \
    for (i = (HN); i < N; i++) { \
        yOut[i] = 0.0; \
        fb[i] = 0.0; \
        st->reads[i] = 0.0; \
    } \
    FW(st->reads); \
    g = st->g; \
    for (i = 0; i < (HN); i++) fb[i] = g * st->reads[i]; \
}

DIFFUSE_FN(diffuse8, 8, fwht8)
DIFFUSE_FN(diffuse16, 16, fwht16)
DIFFUSE_FN(diffuse32, 32, fwht32)

static double early_mul(LiveStereo *st, int b, int i, int bankB, double ev) {
    if (!st->earlyGateOn) return ev;
    return ev * (bankB ? st->earlyGateB[b][i] : st->earlyGate[b][i]);
}

static void prox_zero_lp(LiveStereo *st) {
    int b, i;
    for (b = 0; b < 3; b++) {
        st->proxLpDA[b] = 0.0;
        st->proxLpDB[b] = 0.0;
        for (i = 0; i < N; i++) {
            st->proxLpEA[b][i] = 0.0;
            st->proxLpEB[b][i] = 0.0;
        }
    }
}

static int prox_is_hot(LiveStereo *st) {
    int b, i;
    if (st->proxRamp > 0) return 1;
    for (b = 0; b < 3; b++) {
        if (st->proxGA[b] != 0.0 || st->proxGB[b] != 0.0) return 1;
        for (i = 0; i < N; i++) {
            if (st->proxScA[b][i] != 1.0 || st->proxScB[b][i] != 1.0) return 1;
        }
    }
    return 0;
}

static void prox_bypass(LiveStereo *st) {
    int b, i;
    st->proxRamp = 0;
    st->proxInited = 0;
    for (b = 0; b < 3; b++) {
        st->proxGA[b] = 0.0;
        st->proxGB[b] = 0.0;
        st->proxTgtA[b] = 0.0;
        st->proxTgtB[b] = 0.0;
        st->proxStepA[b] = 0.0;
        st->proxStepB[b] = 0.0;
        for (i = 0; i < N; i++) {
            st->proxScA[b][i] = 1.0;
            st->proxScB[b][i] = 1.0;
        }
    }
    prox_zero_lp(st);
    st->proxHot = 0;
}

/* Scrub drops the shelf and its state. Scales stay, so the early floor
   holds until the next live_set_prox, which snaps because proxInited is 0. */
static void prox_scrub(LiveStereo *st) {
    int b;
    prox_zero_lp(st);
    st->proxInited = 0;
    st->proxRamp = 0;
    for (b = 0; b < 3; b++) {
        st->proxGA[b] = 0.0;
        st->proxGB[b] = 0.0;
        st->proxTgtA[b] = 0.0;
        st->proxTgtB[b] = 0.0;
        st->proxStepA[b] = 0.0;
        st->proxStepB[b] = 0.0;
    }
    st->proxHot = prox_is_hot(st);
}

static void prox_advance(LiveStereo *st) {
    int b, i;
    if (st->proxRamp <= 0) return;
    st->proxRamp--;
    if (st->proxRamp <= 0) {
        for (b = 0; b < 3; b++) {
            st->proxGA[b] = st->proxTgtA[b];
            st->proxGB[b] = st->proxTgtB[b];
            if (st->proxGA[b] == 0.0) {
                st->proxLpDA[b] = 0.0;
                for (i = 0; i < N; i++) st->proxLpEA[b][i] = 0.0;
            }
            if (st->proxGB[b] == 0.0) {
                st->proxLpDB[b] = 0.0;
                for (i = 0; i < N; i++) st->proxLpEB[b][i] = 0.0;
            }
        }
        st->proxHot = prox_is_hot(st);
        return;
    }
    for (b = 0; b < 3; b++) {
        st->proxGA[b] += st->proxStepA[b];
        st->proxGB[b] += st->proxStepB[b];
    }
}

static double prox_direct(LiveStereo *st, int b, int bankB, double x) {
    double g = bankB ? st->proxGB[b] : st->proxGA[b];
    double *lp;
    double lpv;
    if (g == 0.0) return x;
    lp = bankB ? &st->proxLpDB[b] : &st->proxLpDA[b];
    lpv = (1.0 - st->proxP) * x + st->proxP * (*lp);
    *lp = lpv;
    return x + g * lpv;
}

static double prox_early(LiveStereo *st, int b, int i, int bankB, double ev) {
    double s = bankB ? st->proxScB[b][i] : st->proxScA[b][i];
    double g = bankB ? st->proxGB[b] : st->proxGA[b];
    double *lp;
    double lpv;
    if (s != 1.0) ev *= s;
    if (g == 0.0) return ev;
    lp = bankB ? &st->proxLpEB[b][i] : &st->proxLpEA[b][i];
    lpv = (1.0 - st->proxP) * ev + st->proxP * (*lp);
    *lp = lpv;
    return ev + g * lpv;
}

/* n == 0 is a hard bypass. Otherwise the buffer is 199 doubles:
   [0] snap, [1..3] gA, [4..6] gB, [7..102] scaleA, [103..198] scaleB.
   C does not recompute g. The first set, a snap flag, and the set after
   scrub copy the target. A later change ramps g over 15 ms. */
LS_EXPORT("live_prox_ptr") double *live_prox_ptr(LiveStereo *st) { return st ? st->proxBuf : 0; }
LS_EXPORT("live_set_prox") int live_set_prox(LiveStereo *st, int n) {
    int b, i, changed, snap;
    double tgtA[3], tgtB[3];
    if (!st) return 0;
    if (n <= 0) { prox_bypass(st); return 0; }
    for (i = 0; i < 199; i++) {
        if (!finite_d(st->proxBuf[i])) { prox_bypass(st); return 0; }
    }
    for (b = 0; b < 3; b++) {
        tgtA[b] = st->proxBuf[1 + b];
        tgtB[b] = st->proxBuf[4 + b];
        for (i = 0; i < N; i++) {
            st->proxScA[b][i] = st->proxBuf[7 + b * N + i];
            st->proxScB[b][i] = st->proxBuf[7 + 3 * N + b * N + i];
        }
    }
    snap = !st->proxInited || st->proxBuf[0] > 0.5;
    changed = 0;
    if (!snap) {
        for (b = 0; b < 3; b++) {
            if (tgtA[b] != st->proxTgtA[b] || tgtB[b] != st->proxTgtB[b]) changed = 1;
        }
    }
    for (b = 0; b < 3; b++) {
        st->proxTgtA[b] = tgtA[b];
        st->proxTgtB[b] = tgtB[b];
    }
    if (snap) {
        for (b = 0; b < 3; b++) {
            st->proxGA[b] = tgtA[b];
            st->proxGB[b] = tgtB[b];
            st->proxStepA[b] = 0.0;
            st->proxStepB[b] = 0.0;
        }
        st->proxRamp = 0;
        prox_zero_lp(st);
        st->proxInited = 1;
    } else if (changed) {
        int ramp = (int)(0.015 * (double)st->sr + 0.5);
        if (ramp < 1) ramp = 1;
        st->proxRamp = ramp;
        for (b = 0; b < 3; b++) {
            st->proxStepA[b] = (tgtA[b] - st->proxGA[b]) / (double)ramp;
            st->proxStepB[b] = (tgtB[b] - st->proxGB[b]) / (double)ramp;
        }
    }
    st->proxHot = prox_is_hot(st);
    return st->proxHot;
}

/* DF1. Called only when subHpOn is set, so the off path never touches subZ. */
static double sub_apply(LiveStereo *st, int bus, int bank, int line, double xin) {
    double *z1 = &st->subZ[bus][bank][0][line];
    double *z2 = &st->subZ[bus][bank][1][line];
    double y = st->subB0 * xin + *z1;
    *z1 = st->subB1 * xin - st->subA1 * y + *z2;
    *z2 = st->subB2 * xin - st->subA2 * y;
    return y;
}

/* Tank excitation. tint stays on the unfiltered argument. The high-pass,
   when on, is a copy of that tint, and LS_DC stays after it. */
static double fdn_excite(LiveStereo *st, int b, int bank, int line, Line *ln, double pre, int kind) {
    double y = tint(ln, pre, kind);
    if (st->subHpOn) y = sub_apply(st, b, bank, line, y);
    if (st->predelayN > 0) y = bloom_pd(st, b, bank, line, y);
    return y + LS_DC;
}

static void bus_sample(LiveStereo *st, int b, double x, double xA, double xB, int two, int t,
    int hn, FwhtFn doFwht, DiffuseFn doDiff) {
    Bus *bus = &st->bus[b];
    int i, cap = st->cap;
    /* The tank runs while the output gain is down. Shared L/R still borrow C. */
    int runFdn = 1;
    int runEarly = st->early_wet > 1.0e-4 || st->rampUse;
    double dA, dB = 0.0, early = 0.0;
    /* Only the centre bus runs the shared network. L and R keep direct and early. */
    const int shC = st->shared && b == BUS_C;
    if (st->shared && b != BUS_C) runFdn = 0;
    for (i = 0; i < N; i++) {
        Line *line = &bus->line[i];
        line->delay += SMOOTH * (line->delayT - line->delay);
        if (two) line->delayB += SMOOTH * (line->delayBT - line->delayB);
    }
    bus->dirD += SMOOTH * (bus->dirDT - bus->dirD);
    dA = read_lin(st->dir[b], bus->dirW, bus->dirD, cap);
    /* D19: both sources scale the direct write by dirGain. An absent key is 1,
     * so a one-source scene with no Side strip stays the old sample.
     * Radiation, when on, filters that write. */
    if (st->radA || (two && st->radB)) {
        if (two) st->dir[b][bus->dirW] = (float)((st->radA ? st->dirSmp[b] : xA) * bus->dirGain);
        else st->dir[b][bus->dirW] = (float)((st->radA ? st->dirSmp[b] : x) * bus->dirGain);
    } else {
        st->dir[b][bus->dirW] = (float)((two ? xA : x) * bus->dirGain);
    }
    adv(&bus->dirW, cap);
    if (two) {
        bus->dirDB += SMOOTH * (bus->dirDBT - bus->dirDB);
        dB = read_lin(st->dirB[b], bus->dirWB, bus->dirDB, cap);
        st->dirB[b][bus->dirWB] = (float)((st->radB ? st->dirSmpB[b] : xB) * bus->dirGainB);
        adv(&bus->dirWB, cap);
    }
    if (st->proxHot) {
        dA = prox_direct(st, b, 0, dA);
        if (two) dB = prox_direct(st, b, 1, dB);
    }
    st->daBlk[b][t] = dA;
    st->dbBlk[b][t] = dB;

    if (!two) {
        int mix1 = runFdn && bus->anyDffs;
        if (runFdn && !mix1) {
            if (st->slOn) {
                for (i = 0; i < hn; i++)
                    st->delayed[i] = read_raw_lg(st, &bus->line[i], st->ring[b][i], LANE_FDN, i, 0, bus->line[i].delay);
                surf_batch(st, b, 0, hn);
                for (i = 0; i < hn; i++) {
                    st->delayed[i] = apply_kept_peak(st, &bus->line[i], i, 0, st->delayed[i]);
                    if (st->harmOn) st->delayed[i] = apply_harm(st, b, i, 0, st->delayed[i]);
                    st->reads[i] = st->delayed[i];
                }
            } else {
                for (i = 0; i < hn; i++) {
                    st->delayed[i] = read_peaked(st, &bus->line[i], st->ring[b][i], LANE_FDN, i, 0, bus->line[i].delay);
                    if (st->harmOn) st->delayed[i] = apply_harm(st, b, i, 0, st->delayed[i]);
                    st->reads[i] = st->delayed[i];
                }
            }
            for (i = hn; i < N; i++) st->reads[i] = 0.0;
            doFwht(st->reads);
        } else if (mix1) {
            if (st->slOn) {
                for (i = 0; i < hn; i++)
                    st->delayed[i] = read_raw_lg(st, &bus->line[i], st->ring[b][i], LANE_FDN, i, 0, bus->line[i].delay);
                surf_batch(st, b, 0, hn);
                for (i = 0; i < hn; i++) {
                    st->delayed[i] = apply_kept_peak(st, &bus->line[i], i, 0, st->delayed[i]);
                    if (st->harmOn) st->delayed[i] = apply_harm(st, b, i, 0, st->delayed[i]);
                }
            } else {
                for (i = 0; i < hn; i++) {
                    st->delayed[i] = read_peaked(st, &bus->line[i], st->ring[b][i], LANE_FDN, i, 0, bus->line[i].delay);
                    if (st->harmOn) st->delayed[i] = apply_harm(st, b, i, 0, st->delayed[i]);
                }
            }
        }
        /* Lines at or past hn are outside this Hadamard. The tail loop only
         * keeps their write pointer moving. Kind 0 tints once: the image
         * filter feeds Early, the diffuse filter feeds the FDN. */
        for (i = 0; i < hn; i++) {
            Line *line = &bus->line[i];
            double xin;
            if (st->radA) {
                double diffIn = st->surfOn ? st->diffArr[i] : st->diffSmp;
                double earlyIn = tint(line, st->srcSmp[i] * line->inj, 1);
                double injLoop = line->inj;
                if (shC) injLoop = st->shInjS[i];
                xin = tint(line, diffIn * injLoop, 0);
                if (runEarly) {
                    double ev = early_mul(st, b, i, 0, read_lane(st->ring[b][i], LANE_EARLY, line->w, line->delay, cap));
                    if (st->proxHot) ev = prox_early(st, b, i, 0, ev);
                    st->eaBlk[b][i][t] = ev;
                    early += ev;
                }
                write_lane(st->ring[b][i], line->w, LANE_EARLY, (float)earlyIn);
            } else if (shC) {
                /* Centre early keeps its own inject. Tint is linear, so the loop
                   input is that tint scaled by injS/inj. The cascade, when on,
                   has already filtered this line's x once. */
                double xIn = st->surfOn ? st->srcSmp[i] : x;
                double ein = tint(line, xIn * line->inj, 0);
                double injS = st->shInjS[i];
                xin = line->inj != 0.0 ? ein * st->shRS[i] : tint(line, xIn * injS, 1);
                if (runEarly) {
                    double ev = early_mul(st, b, i, 0, read_lane(st->ring[b][i], LANE_EARLY, line->w, line->delay, cap));
                    if (st->proxHot) ev = prox_early(st, b, i, 0, ev);
                    st->eaBlk[b][i][t] = ev;
                    early += ev;
                }
                write_lane(st->ring[b][i], line->w, LANE_EARLY, (float)ein);
            } else {
                double xIn = st->surfOn ? st->srcSmp[i] : x;
                xin = tint(line, xIn * line->inj, 0);
                if (runEarly) {
                    double ev = early_mul(st, b, i, 0, read_lane(st->ring[b][i], LANE_EARLY, line->w, line->delay, cap));
                    if (st->proxHot) ev = prox_early(st, b, i, 0, ev);
                    st->eaBlk[b][i][t] = ev;
                    early += ev;
                }
                write_lane(st->ring[b][i], line->w, LANE_EARLY, (float)xin);
            }
            {
                /* FDN copy only. Early already stored the unfiltered xin.
                   Off: tank is xin, so the add is the old sample. */
                double tank = xin;
                if (st->subHpOn) tank = sub_apply(st, b, 0, i, xin);
                if (st->predelayN > 0) tank = bloom_pd(st, b, 0, i, tank);
                if (mix1) st->xinArr[i] = tank + LS_DC;
                else if (runFdn) {
                    double gi = line->dffs;
                    double mixed = st->g * st->reads[i] + tank + LS_DC;
                    double y = -gi * mixed + st->delayed[i];
                    write_lane(st->ring[b][i], line->w, LANE_FDN, (float)(mixed + gi * y));
                    st->yBlk[b][i][t] = y;
                }
            }
            if (!mix1) adv(&line->w, cap);
        }
        if (!mix1) {
            for (i = hn; i < N; i++) adv(&bus->line[i].w, cap);
        }
        if (mix1) {
            doDiff(st, b, 0, st->xinArr, bus->fb, st->yA);
            for (i = 0; i < N; i++) {
                st->yBlk[b][i][t] = st->yA[i];
                adv(&bus->line[i].w, cap);
            }
        }
        st->esBlk[b][t] = early;
        return;
    }

    for (i = 0; i < hn; i++) {
        Line *line = &bus->line[i];
        /* Kinds 1 and 2 stay running while Early is down. Kinds 0 and 3 stay with the FDN. */
        double imgA = (st->radA || st->surfOn) ? st->srcSmp[i] : xA;
        double imgB = (st->radB || st->surfOn) ? st->srcSmpB[i] : xB;
        double eA = tint(line, imgA * line->inj, 1);
        double eB = tint(line, imgB * line->injB, 2);
        if (runEarly) {
            double ev = early_mul(st, b, i, 0, read_lane(st->ring[b][i], LANE_EARLY, line->w, line->delay, cap));
            double evB = early_mul(st, b, i, 1, read_lane(st->ring[b][i], LANE_EARLYB, line->w, line->delayB, cap));
            if (st->proxHot) {
                ev = prox_early(st, b, i, 0, ev);
                evB = prox_early(st, b, i, 1, evB);
            }
            st->eaBlk[b][i][t] = ev;
            st->ebBlk[b][i][t] = evB;
            early += ev + evB;
        }
        write_lane(st->ring[b][i], line->w, LANE_EARLY, (float)eA);
        write_lane(st->ring[b][i], line->w, LANE_EARLYB, (float)eB);
    }
    if (runFdn) {
        int mixA = bus->anyDffs;
        int mixB = bus->anyDffsB;
        if (st->slOn) {
            for (i = 0; i < hn; i++) {
                Line *line = &bus->line[i];
                st->delayed[i] = read_raw_lg(st, line, st->ring[b][i], LANE_FDN, i, 0, line->delay);
            }
            surf_batch(st, b, 0, hn);
            for (i = 0; i < hn; i++) {
                Line *line = &bus->line[i];
                double injUse = line->inj;
                if (shC) injUse = st->shInjS[i];
                st->delayed[i] = apply_kept_peak(st, line, i, 0, st->delayed[i]);
                if (st->harmOn) st->delayed[i] = apply_harm(st, b, i, 0, st->delayed[i]);
                st->reads[i] = st->delayed[i];
                if (st->radA) {
                    double diffIn = st->surfOn ? st->diffArr[i] : st->diffSmp;
                    if (st->subHpOn) st->xinArr[i] = fdn_excite(st, b, 0, i, line, 0.5 * diffIn * injUse, 0);
                    else st->xinArr[i] = st->predelayN > 0 ? bloom_pd(st, b, 0, i, tint(line, 0.5 * diffIn * injUse, 0)) + LS_DC : tint(line, 0.5 * diffIn * injUse, 0) + LS_DC;
                } else if (st->surfOn) {
                    if (st->subHpOn) st->xinArr[i] = fdn_excite(st, b, 0, i, line, 0.5 * st->srcSmp[i] * injUse, 0);
                    else st->xinArr[i] = st->predelayN > 0 ? bloom_pd(st, b, 0, i, tint(line, 0.5 * st->srcSmp[i] * injUse, 0)) + LS_DC : tint(line, 0.5 * st->srcSmp[i] * injUse, 0) + LS_DC;
                }
                else {
                    if (st->subHpOn) st->xinArr[i] = fdn_excite(st, b, 0, i, line, 0.5 * xA * injUse, 0);
                    else st->xinArr[i] = st->predelayN > 0 ? bloom_pd(st, b, 0, i, tint(line, 0.5 * xA * injUse, 0)) + LS_DC : tint(line, 0.5 * xA * injUse, 0) + LS_DC;
                }
            }
        } else {
            for (i = 0; i < hn; i++) {
                Line *line = &bus->line[i];
                double injUse = line->inj;
                if (shC) injUse = st->shInjS[i];
                st->delayed[i] = read_peaked(st, line, st->ring[b][i], LANE_FDN, i, 0, line->delay);
                if (st->harmOn) st->delayed[i] = apply_harm(st, b, i, 0, st->delayed[i]);
                st->reads[i] = st->delayed[i];
                if (st->radA) {
                    double diffIn = st->surfOn ? st->diffArr[i] : st->diffSmp;
                    if (st->subHpOn) st->xinArr[i] = fdn_excite(st, b, 0, i, line, 0.5 * diffIn * injUse, 0);
                    else st->xinArr[i] = st->predelayN > 0 ? bloom_pd(st, b, 0, i, tint(line, 0.5 * diffIn * injUse, 0)) + LS_DC : tint(line, 0.5 * diffIn * injUse, 0) + LS_DC;
                } else if (st->surfOn) {
                    if (st->subHpOn) st->xinArr[i] = fdn_excite(st, b, 0, i, line, 0.5 * st->srcSmp[i] * injUse, 0);
                    else st->xinArr[i] = st->predelayN > 0 ? bloom_pd(st, b, 0, i, tint(line, 0.5 * st->srcSmp[i] * injUse, 0)) + LS_DC : tint(line, 0.5 * st->srcSmp[i] * injUse, 0) + LS_DC;
                }
                else {
                    if (st->subHpOn) st->xinArr[i] = fdn_excite(st, b, 0, i, line, 0.5 * xA * injUse, 0);
                    else st->xinArr[i] = st->predelayN > 0 ? bloom_pd(st, b, 0, i, tint(line, 0.5 * xA * injUse, 0)) + LS_DC : tint(line, 0.5 * xA * injUse, 0) + LS_DC;
                }
            }
        }
        if (mixA) doDiff(st, b, 0, st->xinArr, bus->fb, st->yA);
        else {
            for (i = hn; i < N; i++) st->reads[i] = 0.0;
            doFwht(st->reads);
            for (i = 0; i < hn; i++) {
                Line *line = &bus->line[i];
                double gi = line->dffs;
                double mixed = st->g * st->reads[i] + st->xinArr[i];
                double y = -gi * mixed + st->delayed[i];
                write_lane(st->ring[b][i], line->w, LANE_FDN, (float)(mixed + gi * y));
                st->yA[i] = y;
            }
            for (i = hn; i < N; i++) st->yA[i] = 0.0;
        }
        if (st->slOn) {
            for (i = 0; i < hn; i++) {
                Line *line = &bus->line[i];
                st->delayed[i] = read_raw_lg(st, line, st->ring[b][i], LANE_FDNB, i, 1, line->delayB);
            }
            surf_batch(st, b, 1, hn);
            for (i = 0; i < hn; i++) {
                Line *line = &bus->line[i];
                double injUse = line->injB;
                if (shC) injUse = st->shInjSB[i];
                st->delayed[i] = apply_kept_peak(st, line, i, 1, st->delayed[i]);
                if (st->harmOn) st->delayed[i] = apply_harm(st, b, i, 1, st->delayed[i]);
                st->reads[i] = st->delayed[i];
                if (st->radB) {
                    double diffIn = st->surfOn ? st->diffArrB[i] : st->diffSmpB;
                    if (st->subHpOn) st->xinArr[i] = fdn_excite(st, b, 1, i, line, 0.5 * diffIn * injUse, 3);
                    else st->xinArr[i] = st->predelayN > 0 ? bloom_pd(st, b, 1, i, tint(line, 0.5 * diffIn * injUse, 3)) + LS_DC : tint(line, 0.5 * diffIn * injUse, 3) + LS_DC;
                } else if (st->surfOn) {
                    if (st->subHpOn) st->xinArr[i] = fdn_excite(st, b, 1, i, line, 0.5 * st->srcSmpB[i] * injUse, 3);
                    else st->xinArr[i] = st->predelayN > 0 ? bloom_pd(st, b, 1, i, tint(line, 0.5 * st->srcSmpB[i] * injUse, 3)) + LS_DC : tint(line, 0.5 * st->srcSmpB[i] * injUse, 3) + LS_DC;
                }
                else {
                    if (st->subHpOn) st->xinArr[i] = fdn_excite(st, b, 1, i, line, 0.5 * xB * injUse, 3);
                    else st->xinArr[i] = st->predelayN > 0 ? bloom_pd(st, b, 1, i, tint(line, 0.5 * xB * injUse, 3)) + LS_DC : tint(line, 0.5 * xB * injUse, 3) + LS_DC;
                }
            }
        } else {
            for (i = 0; i < hn; i++) {
                Line *line = &bus->line[i];
                double injUse = line->injB;
                if (shC) injUse = st->shInjSB[i];
                st->delayed[i] = read_peaked(st, line, st->ring[b][i], LANE_FDNB, i, 1, line->delayB);
                if (st->harmOn) st->delayed[i] = apply_harm(st, b, i, 1, st->delayed[i]);
                st->reads[i] = st->delayed[i];
                if (st->radB) {
                    double diffIn = st->surfOn ? st->diffArrB[i] : st->diffSmpB;
                    if (st->subHpOn) st->xinArr[i] = fdn_excite(st, b, 1, i, line, 0.5 * diffIn * injUse, 3);
                    else st->xinArr[i] = st->predelayN > 0 ? bloom_pd(st, b, 1, i, tint(line, 0.5 * diffIn * injUse, 3)) + LS_DC : tint(line, 0.5 * diffIn * injUse, 3) + LS_DC;
                } else if (st->surfOn) {
                    if (st->subHpOn) st->xinArr[i] = fdn_excite(st, b, 1, i, line, 0.5 * st->srcSmpB[i] * injUse, 3);
                    else st->xinArr[i] = st->predelayN > 0 ? bloom_pd(st, b, 1, i, tint(line, 0.5 * st->srcSmpB[i] * injUse, 3)) + LS_DC : tint(line, 0.5 * st->srcSmpB[i] * injUse, 3) + LS_DC;
                }
                else {
                    if (st->subHpOn) st->xinArr[i] = fdn_excite(st, b, 1, i, line, 0.5 * xB * injUse, 3);
                    else st->xinArr[i] = st->predelayN > 0 ? bloom_pd(st, b, 1, i, tint(line, 0.5 * xB * injUse, 3)) + LS_DC : tint(line, 0.5 * xB * injUse, 3) + LS_DC;
                }
            }
        }
        if (mixB) {
            doDiff(st, b, 1, st->xinArr, bus->fbB, st->yB);
            for (i = 0; i < N; i++) {
                st->yBlk[b][i][t] = st->yA[i];
                st->yBlkB[b][i][t] = st->yB[i];
            }
        } else {
            for (i = hn; i < N; i++) st->reads[i] = 0.0;
            doFwht(st->reads);
            for (i = 0; i < hn; i++) {
                Line *line = &bus->line[i];
                double gi = line->dffsB;
                double mixed = st->g * st->reads[i] + st->xinArr[i];
                double y = -gi * mixed + st->delayed[i];
                write_lane(st->ring[b][i], line->w, LANE_FDNB, (float)(mixed + gi * y));
                st->yBlk[b][i][t] = st->yA[i];
                st->yBlkB[b][i][t] = y;
            }
            for (i = hn; i < N; i++) {
                st->yBlk[b][i][t] = st->yA[i];
                st->yBlkB[b][i][t] = 0.0;
            }
        }
    }
    for (i = 0; i < N; i++) adv(&bus->line[i].w, cap);
    st->esBlk[b][t] = early;
}

static void scrub(LiveStereo *st) {
    int b, i;
    ls_zero(st->slab, st->slabN * (int)sizeof(float));
    for (b = 0; b < 3; b++) {
        Bus *bus = &st->bus[b];
        for (i = 0; i < N; i++) {
            Line *line = &bus->line[i];
            line->pz1 = line->pz2 = line->pz1b = line->pz2b = 0;
            line->modYap = line->modYapB = 0;
            line->airZ = line->airZe = line->airZb = line->airZf = 0;
            line->sz1 = line->sz2 = line->sz1e = line->sz2e = 0;
            line->sz1b = line->sz2b = line->sz1f = line->sz2f = 0;
            bus->fb[i] = 0;
            bus->fbB[i] = 0;
        }
    }
    for (b = 0; b < 2; b++) {
        for (i = 0; i < N; i++) {
            int s;
            for (s = 0; s < SURF_K_MAX; s++) {
                st->sfI[b][i].z[s][0] = st->sfI[b][i].z[s][1] = 0.0;
                st->sfD[b][i].z[s][0] = st->sfD[b][i].z[s][1] = 0.0;
            }
        }
    }
    ls_zero(st->soaZ, (int)sizeof(st->soaZ));
    ls_zero(st->slZ, (int)sizeof(st->slZ));
    ls_zero(st->harmZ, (int)sizeof(st->harmZ));
    ls_zero(st->subZ, (int)sizeof(st->subZ));
    prox_scrub(st);
    zero_filts(st);
    bloom_scrub(st);
    st->modAbs = 0;
}

static int early_target(const int *fdnIdx, int line, int earlyIdx) {
    /* Early shares the FDN line's filter when that line has one.
     * A wire line (-1) keeps a real early record, which is the binaural HRTF.
     * earlyIdx < -1 stays mute. */
    if (earlyIdx < -1) return -2;
    if (fdnIdx[line] >= 0) return fdnIdx[line];
    if (earlyIdx >= 0) return earlyIdx;
    if (fdnIdx[line] >= -1) return fdnIdx[line];
    return -2;
}

static Filt *take_filt(LiveStereo *st, int bus, int kind, int ir) {
    int i, freeSlot = -1;
    for (i = 0; i < MAX_FILT; i++) {
        Filt *f = &st->filt[i];
        if (f->used && f->bus == bus && f->kind == kind && f->ir == ir) {
            f->seen = 1;
            return f;
        }
        if (!f->used && freeSlot < 0) freeSlot = i;
    }
    if (freeSlot < 0) return 0;
    {
        Filt *f = &st->filt[freeSlot];
        ls_zero(f, (int)sizeof(Filt));
        f->used = 1;
        f->bus = bus;
        f->kind = kind;
        f->ir = ir;
        f->npart = st->irNpart[ir];
        if (f->npart < 1) f->npart = 1;
        f->cold = MAX_PART;
        f->seen = 1;
        if (st->irSos[ir] <= 0) {
            int fi = freeSlot;
            int nfloat = MAX_PART * FFTN;
            ls_zero(st->fdlRe + fi * nfloat, nfloat * (int)sizeof(float));
            ls_zero(st->fdlIm + fi * nfloat, nfloat * (int)sizeof(float));
        }
        return f;
    }
}

static void mac_bins(float *accR, float *accI, const float *xr, const float *xi,
                      const float *hr, const float *hi, int n) {
    int i = 0;
#if defined(__wasm_simd128__)
    if ((((unsigned long)accR | (unsigned long)accI | (unsigned long)xr |
          (unsigned long)xi | (unsigned long)hr | (unsigned long)hi) & 15ul) == 0) {
        for (; i + 4 <= n; i += 4) {
            v128_t ar = wasm_v128_load(xr + i);
            v128_t ai = wasm_v128_load(xi + i);
            v128_t br = wasm_v128_load(hr + i);
            v128_t bi = wasm_v128_load(hi + i);
            v128_t rr = wasm_f32x4_sub(wasm_f32x4_mul(ar, br), wasm_f32x4_mul(ai, bi));
            v128_t ii = wasm_f32x4_add(wasm_f32x4_mul(ar, bi), wasm_f32x4_mul(ai, br));
            wasm_v128_store(accR + i, wasm_f32x4_add(wasm_v128_load(accR + i), rr));
            wasm_v128_store(accI + i, wasm_f32x4_add(wasm_v128_load(accI + i), ii));
        }
    }
#elif defined(LS_SIMD)
    for (; i + 4 <= n; i += 4) {
        __m128 ar = _mm_loadu_ps(xr + i);
        __m128 ai = _mm_loadu_ps(xi + i);
        __m128 br = _mm_loadu_ps(hr + i);
        __m128 bi = _mm_loadu_ps(hi + i);
        __m128 rr = _mm_sub_ps(_mm_mul_ps(ar, br), _mm_mul_ps(ai, bi));
        __m128 ii = _mm_add_ps(_mm_mul_ps(ar, bi), _mm_mul_ps(ai, br));
        _mm_storeu_ps(accR + i, _mm_add_ps(_mm_loadu_ps(accR + i), rr));
        _mm_storeu_ps(accI + i, _mm_add_ps(_mm_loadu_ps(accI + i), ii));
    }
#endif
    for (; i < n; i++) {
        float ar = xr[i], ai = xi[i], br = hr[i], bi = hi[i];
        accR[i] += ar * br - ai * bi;
        accI[i] += ar * bi + ai * br;
    }
}

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
    silent = 1;
    for (i = 0; i < PART; i++) {
        if (in[i] > 1.0e-12f || in[i] < -1.0e-12f) { silent = 0; break; }
    }
    if (silent && f->cold >= f->npart) {
        for (i = 0; i < PART; i++) out[i] = 0;
        return;
    }
    if (silent) f->cold += 1;
    else f->cold = 0;
    npart = f->npart;
    if (npart < 1) npart = 1;
    if (npart > MAX_PART) npart = MAX_PART;
    for (i = 0; i < PART; i++) { g_re[i] = f->prev[i]; g_im[i] = 0; }
    for (i = 0; i < PART; i++) {
        g_re[PART + i] = silent ? 0.0f : in[i];
        g_im[PART + i] = 0;
    }
    fft_complex(g_re, g_im, 0);
    pos = f->pos;
    xre = st->fdlRe + ((f - st->filt) * MAX_PART + pos) * FFTN;
    xim = st->fdlIm + ((f - st->filt) * MAX_PART + pos) * FFTN;
    ls_copy(xre, g_re, FFTN * (int)sizeof(float));
    ls_copy(xim, g_im, FFTN * (int)sizeof(float));
    for (i = 0; i < PART; i++) f->prev[i] = silent ? 0.0f : in[i];
    for (i = 0; i < FFTN; i++) { g_accR[i] = 0; g_accI[i] = 0; }
    base = f->ir * MAX_PART * FFTN;
    hre = st->specRe + base;
    him = st->specIm + base;
    for (p = 0; p < npart; p++) {
        int src = pos - p;
        float *xr, *xi, *hr, *hi;
        if (src < 0) src += MAX_PART;
        xr = st->fdlRe + ((f - st->filt) * MAX_PART + src) * FFTN;
        xi = st->fdlIm + ((f - st->filt) * MAX_PART + src) * FFTN;
        hr = hre + p * FFTN;
        hi = him + p * FFTN;
        mac_bins(g_accR, g_accI, xr, xi, hr, hi, FFTN);
    }
    f->pos = pos + 1;
    if (f->pos >= MAX_PART) f->pos = 0;
    ls_copy(g_re, g_accR, FFTN * (int)sizeof(float));
    ls_copy(g_im, g_accI, FFTN * (int)sizeof(float));
    fft_complex(g_re, g_im, 1);
    for (i = 0; i < PART; i++) out[i] = g_re[PART + i];
}

static int usable_ir(LiveStereo *st, int idx) {
    if (idx < 0) return idx == -1 ? -1 : -2;
    if (idx >= st->n_irs || st->irLen[idx] < 1) return -1;
    return idx;
}

static void side(LiveStereo *st, int b, double *sl, double *sr); 

static void ramp_targets(LiveStereo *st, double *to) {
    int b;
    double sl, sr;
    to[RG_FDN] = st->fdn_wet;
    to[RG_DIR] = st->direct_wet;
    to[RG_EARLY] = st->early_wet;
    to[RG_DRY] = st->dry_gain;
    to[RG_MK] = st->makeup;
    if (st->deskOn) {
        to[RG_W + 0] = st->deskW[0][0];
        to[RG_W + 1] = st->deskW[0][1];
        to[RG_W + 2] = st->deskW[1][0];
        to[RG_W + 3] = st->deskW[1][1];
        to[RG_W + 4] = st->deskW[2][0];
        to[RG_W + 5] = st->deskW[2][1];
        return;
    }
    for (b = 0; b < 3; b++) {
        side(st, b, &sl, &sr);
        to[RG_W + 2 * b] = sl;
        to[RG_W + 2 * b + 1] = sr;
    }
}

static double ramp_now(const LiveStereo *st, int i) {
    double u;
    if (st->rampLeft <= 0 || st->rampTotal <= 0) return st->rampTo[i];
    u = 1.0 - (double)st->rampLeft / (double)st->rampTotal;
    return st->rampFrom[i] + (st->rampTo[i] - st->rampFrom[i]) * u;
}

static void arm_ramps(LiveStereo *st) {
    double to[RG_N];
    int i, moved = 0;
    int nSamp;
    ramp_targets(st, to);
    if (!st->rampPrimed) {
        for (i = 0; i < RG_N; i++) st->rampFrom[i] = st->rampTo[i] = to[i];
        st->rampLeft = 0;
        st->rampTotal = 0;
        st->rampPrimed = 1;
        return;
    }
    for (i = 0; i < RG_N; i++) {
        if (to[i] != st->rampTo[i]) moved = 1;
    }
    if (!moved) return;
    for (i = 0; i < RG_N; i++) st->rampFrom[i] = ramp_now(st, i);
    for (i = 0; i < RG_N; i++) st->rampTo[i] = to[i];
    nSamp = (int)(0.010 * (double)st->sr + 0.5);
    if (nSamp < 1) nSamp = 1;
    st->rampTotal = nSamp;
    st->rampLeft = nSamp;
}

static void fill_ramp_block(LiveStereo *st) {
    int t, i, left, total;
    st->rampUse = 0;
    if (st->rampLeft <= 0) return;
    st->rampUse = 1;
    left = st->rampLeft;
    total = st->rampTotal;
    if (total < 1) total = 1;
    for (t = 0; t < PART; t++) {
        if (left <= 0) {
            for (i = 0; i < RG_N; i++) st->rampBlk[i][t] = st->rampTo[i];
            continue;
        }
        {
            double u = (double)(total - left + 1) / (double)total;
            for (i = 0; i < RG_N; i++) {
                st->rampBlk[i][t] = st->rampFrom[i] + (st->rampTo[i] - st->rampFrom[i]) * u;
            }
            left--;
        }
    }
    st->rampLeft = left;
}

static void side(LiveStereo *st, int b, double *sl, double *sr) {
    double t, amp;
    if (st->deskOn) {
        *sl = st->deskW[b][0];
        *sr = st->deskW[b][1];
        return;
    }
    t = (st->micPan[b] + 1.0) * 0.5;
    if (t < 0.0) t = 0.0;
    else if (t > 1.0) t = 1.0;
    amp = st->micG[b] * (st->micPh[b] < 0.0 ? -1.0 : 1.0);
    *sl = amp * (1.0 - t);
    *sr = amp * t;
}

/* 1 when this partition does not send the centre bus to either speaker
   and the shared tail is off. The ramp block is the applied weight while
   a ramp is running. Shared tail keeps the tank: it is the shared source. */
static int centre_unheard(LiveStereo *st) {
    int t;
    double sl, sr;
    if (st->shared) return 0;
    if (st->rampUse) {
        for (t = 0; t < PART; t++) {
            if (st->rampBlk[RG_W + 2 * BUS_C][t] != 0.0) return 0;
            if (st->rampBlk[RG_W + 2 * BUS_C + 1][t] != 0.0) return 0;
        }
        return 1;
    }
    side(st, BUS_C, &sl, &sr);
    return sl == 0.0 && sr == 0.0;
}

static void fir_or_wire(LiveStereo *st, int bus, int kind, int idx, const double *in, double *out) {
    int i, u;
    float tmp[PART], y[PART];
    Filt *f;
    u = usable_ir(st, idx);
    if (u < -1) {
        for (i = 0; i < PART; i++) out[i] = 0;
        return;
    }
    if (u < 0) {
        for (i = 0; i < PART; i++) out[i] = in[i];
        return;
    }
    f = take_filt(st, bus, kind, u);
    if (!f) {
        for (i = 0; i < PART; i++) out[i] = in[i];
        return;
    }
    f->npart = st->irNpart[u];
    for (i = 0; i < PART; i++) tmp[i] = (float)in[i];
    run_fir(st, f, tmp, y);
    for (i = 0; i < PART; i++) out[i] = (double)y[i];
}

static void paint_lines(LiveStereo *st, int b, const int *idx, double (*y)[PART],
                         int *map, int *keep, double *ident) {
    int i, t;
    for (i = 0; i < N; i++) {
        int ir = usable_ir(st, idx[i]);
        Filt *f;
        if (ir >= 0) {
            if (map[ir] < 0) {
                f = take_filt(st, b, 0, ir);
                if (!f) ir = -1;
                else {
                    map[ir] = (int)(f - st->filt);
                    f->npart = st->irNpart[ir];
                    keep[map[ir]] = 1;
                }
            }
            if (ir >= 0) {
                int s = map[ir];
                if (st->rampUse) {
                    for (t = 0; t < PART; t++) {
                        st->firIn[s][t] += (float)(st->rampBlk[RG_FDN][t] * y[i][t]);
                    }
                } else {
                    for (t = 0; t < PART; t++) {
                        st->firIn[s][t] += (float)(st->fdn_wet * y[i][t]);
                    }
                }
                continue;
            }
        }
        if (ir == -1) {
            if (st->rampUse) {
                for (t = 0; t < PART; t++) ident[t] += st->rampBlk[RG_FDN][t] * y[i][t];
            } else {
                for (t = 0; t < PART; t++) ident[t] += st->fdn_wet * y[i][t];
            }
        }
    }
}

static int ensure_mapped(LiveStereo *st, int b, int *map, int *keep, int u) {
    Filt *f;
    if (u < 0 || u >= MAX_IRS) return -1;
    if (map[u] >= 0) return map[u];
    f = take_filt(st, b, 0, u);
    if (!f) return -1;
    map[u] = (int)(f - st->filt);
    f->npart = st->irNpart[u];
    keep[map[u]] = 1;
    return map[u];
}

static void ic_collect(LiveStereo *st, int b, double *A, double *B) {
    int i, t;
    double s2 = 1.4142135623730951;
    if (b == BUS_L) {
        for (i = 0; i < N; i += 2) {
            for (t = 0; t < PART; t++) A[t] += s2 * (st->yBlk[b][i][t] + st->yBlkB[b][i][t]);
        }
    } else if (b == BUS_R) {
        for (i = 1; i < N; i += 2) {
            for (t = 0; t < PART; t++) B[t] += s2 * (st->yBlk[b][i][t] + st->yBlkB[b][i][t]);
        }
    }
}

static void ic_apply(LiveStereo *st, const double *A, const double *B, double *oL, double *oR) {
    int n = st->icN;
    int t, k;
    if (n < 1) n = 1;
    if (n > 513) n = 513;
    for (t = 0; t < PART; t++) {
        double M = A[t] + B[t];
        double S = A[t] - B[t];
        double pm = (double)st->icHp[0] * M;
        double sm = (double)st->icHm[0] * S;
        for (k = 1; k < n; k++) {
            pm += (double)st->icHp[k] * (double)st->icHistM[k - 1];
            sm += (double)st->icHm[k] * (double)st->icHistS[k - 1];
        }
        if (n > 1) {
            for (k = n - 2; k > 0; k--) {
                st->icHistM[k] = st->icHistM[k - 1];
                st->icHistS[k] = st->icHistS[k - 1];
            }
            st->icHistM[0] = (float)M;
            st->icHistS[0] = (float)S;
        }
        oL[t] = 0.5 * (pm + sm);
        oR[t] = 0.5 * (pm - sm);
    }
}

static float g_fdlSaveRe[MAX_PART * FFTN];
static float g_fdlSaveIm[MAX_PART * FFTN];
static float g_fdnRaw[MAX_FILT][PART];

static void paint_raw(LiveStereo *st, int b, const int *idx, double (*y)[PART],
    int *map, int *keep, double *ident, float (*dst)[PART]) {
    int i, t;
    for (i = 0; i < N; i++) {
        int ir = usable_ir(st, idx[i]);
        Filt *f;
        if (ir >= 0) {
            if (map[ir] < 0) {
                f = take_filt(st, b, 0, ir);
                if (!f) ir = -1;
                else {
                    map[ir] = (int)(f - st->filt);
                    f->npart = st->irNpart[ir];
                    keep[map[ir]] = 1;
                }
            }
            if (ir >= 0) {
                int s = map[ir];
                for (t = 0; t < PART; t++) dst[s][t] += (float)y[i][t];
                continue;
            }
        }
        if (ir == -1) {
            for (t = 0; t < PART; t++) ident[t] += y[i][t];
        }
    }
}

/* Colour on and Bloom hot. The cold colour block is left as it is.
   Mic colour runs on the unweighted FDN sum. Bloom follows that sum.
   fdn_wet multiplies after Bloom. Early is filtered on its own and added after. */
static void bloom_colour_bus(LiveStereo *st, int b, double sl, double sr,
    double *accL, double *accR, int *keep) {
    double directA[PART], directB[PART];
    double ident[PART], rawIdent[PART];
    double yRawSum[PART], yFullSum[PART], fdnPre[PART];
    int map[MAX_IRS];
    int eiBase = (b == BUS_L) ? 0 : 1;
    int i, t, slot;
    for (i = 0; i < MAX_IRS; i++) map[i] = -1;
    for (t = 0; t < PART; t++) {
        ident[t] = 0;
        rawIdent[t] = 0;
        yRawSum[t] = 0;
        yFullSum[t] = 0;
        fdnPre[t] = 0;
    }
    for (slot = 0; slot < MAX_FILT; slot++) {
        for (t = 0; t < PART; t++) {
            st->firIn[slot][t] = 0;
            g_fdnRaw[slot][t] = 0;
        }
    }
    paint_lines(st, b, st->fdnIdx[b], st->yBlk[b], map, keep, ident);
    paint_raw(st, b, st->fdnIdx[b], st->yBlk[b], map, keep, rawIdent, g_fdnRaw);
    if (st->two) {
        paint_lines(st, b, st->fdnIdxB[b], st->yBlkB[b], map, keep, ident);
        paint_raw(st, b, st->fdnIdxB[b], st->yBlkB[b], map, keep, rawIdent, g_fdnRaw);
    }
    if (b != BUS_C) {
        for (i = 0; i < N; i++) {
            int tgt = early_target(st->fdnIdx[b], i, st->earlyIdx[eiBase][i]);
            int tgtB = st->two ? early_target(st->fdnIdxB[b], i, st->earlyBIdx[eiBase][i]) : -2;
            int u = usable_ir(st, tgt);
            int uB = usable_ir(st, tgtB);
            if (u >= 0) {
                int s = ensure_mapped(st, b, map, keep, u);
                if (s >= 0) {
                    if (st->rampUse) {
                        for (t = 0; t < PART; t++) st->firIn[s][t] += (float)(st->rampBlk[RG_EARLY][t] * st->eaBlk[b][i][t]);
                    } else {
                        for (t = 0; t < PART; t++) st->firIn[s][t] += (float)(st->early_wet * st->eaBlk[b][i][t]);
                    }
                }
            } else if (u == -1) {
                if (st->rampUse) {
                    for (t = 0; t < PART; t++) ident[t] += st->rampBlk[RG_EARLY][t] * st->eaBlk[b][i][t];
                } else {
                    for (t = 0; t < PART; t++) ident[t] += st->early_wet * st->eaBlk[b][i][t];
                }
            }
            if (uB >= 0) {
                int s = ensure_mapped(st, b, map, keep, uB);
                if (s >= 0) {
                    if (st->rampUse) {
                        for (t = 0; t < PART; t++) st->firIn[s][t] += (float)(st->rampBlk[RG_EARLY][t] * st->ebBlk[b][i][t]);
                    } else {
                        for (t = 0; t < PART; t++) st->firIn[s][t] += (float)(st->early_wet * st->ebBlk[b][i][t]);
                    }
                }
            } else if (uB == -1) {
                if (st->rampUse) {
                    for (t = 0; t < PART; t++) ident[t] += st->rampBlk[RG_EARLY][t] * st->ebBlk[b][i][t];
                } else {
                    for (t = 0; t < PART; t++) ident[t] += st->early_wet * st->ebBlk[b][i][t];
                }
            }
        }
    }
    for (slot = 0; slot < MAX_FILT; slot++) {
        Filt *f;
        float yRaw[PART], yFull[PART];
        if (!keep[slot] || !st->filt[slot].used || st->filt[slot].bus != b || st->filt[slot].kind != 0) continue;
        f = &st->filt[slot];
        if (st->irSos[f->ir] > 0) {
            double sz[MAX_SOS][2];
            int s;
            for (s = 0; s < MAX_SOS; s++) { sz[s][0] = f->sz[s][0]; sz[s][1] = f->sz[s][1]; }
            run_fir(st, f, g_fdnRaw[slot], yRaw);
            for (s = 0; s < MAX_SOS; s++) { f->sz[s][0] = sz[s][0]; f->sz[s][1] = sz[s][1]; }
            run_fir(st, f, st->firIn[slot], yFull);
        } else {
            int fi = (int)(f - st->filt);
            int nsave = MAX_PART * FFTN;
            float prev[PART];
            int pos = f->pos, cold = f->cold;
            for (t = 0; t < PART; t++) prev[t] = f->prev[t];
            ls_copy(g_fdlSaveRe, st->fdlRe + fi * nsave, nsave * (int)sizeof(float));
            ls_copy(g_fdlSaveIm, st->fdlIm + fi * nsave, nsave * (int)sizeof(float));
            run_fir(st, f, g_fdnRaw[slot], yRaw);
            ls_copy(st->fdlRe + fi * nsave, g_fdlSaveRe, nsave * (int)sizeof(float));
            ls_copy(st->fdlIm + fi * nsave, g_fdlSaveIm, nsave * (int)sizeof(float));
            for (t = 0; t < PART; t++) f->prev[t] = prev[t];
            f->pos = pos;
            f->cold = cold;
            run_fir(st, f, st->firIn[slot], yFull);
        }
        for (t = 0; t < PART; t++) {
            yRawSum[t] += (double)yRaw[t];
            yFullSum[t] += (double)yFull[t];
        }
    }
    for (t = 0; t < PART; t++) {
        double w = st->rampUse ? st->rampBlk[RG_FDN][t] : st->fdn_wet;
        double raw = yRawSum[t] + rawIdent[t];
        double full = yFullSum[t] + ident[t];
        double early = full - w * raw;
        double x = raw;
        if (st->sideHot) x = side_apply(st, b, t, x);
        if (bloom_hot(st)) x = bloom_apply(st, b, t, x);
        fdnPre[t] = x * w + early;
    }
    for (t = 0; t < PART; t++) directA[t] = st->daBlk[b][t];
    fir_or_wire(st, b, 1, st->directIdx[b], directA, directA);
    if (st->two) {
        for (t = 0; t < PART; t++) directB[t] = st->dbBlk[b][t];
        fir_or_wire(st, b, 2, st->directBIdx[b], directB, directB);
    } else {
        for (t = 0; t < PART; t++) directB[t] = 0;
    }
    if (st->rampUse) {
        for (t = 0; t < PART; t++) {
            double earlyC = (b == BUS_C) ? st->rampBlk[RG_EARLY][t] * st->esBlk[b][t] : 0.0;
            double wet = st->rampBlk[RG_DIR][t] * DIRECT_FOLD * (directA[t] + directB[t])
                + st->rampBlk[RG_MK][t] * (fdnPre[t] + earlyC);
            accL[t] += st->rampBlk[RG_W + 2 * b][t] * wet;
            accR[t] += st->rampBlk[RG_W + 2 * b + 1][t] * wet;
        }
    } else {
        for (t = 0; t < PART; t++) {
            double earlyC = (b == BUS_C) ? st->early_wet * st->esBlk[b][t] : 0.0;
            double wet = st->direct_wet * DIRECT_FOLD * (directA[t] + directB[t])
                + st->makeup * (fdnPre[t] + earlyC);
            accL[t] += sl * wet;
            accR[t] += sr * wet;
        }
    }
}

static void mix_partition(LiveStereo *st, float *outL, float *outR) {
    int b, t, i, slot;
    double accL[PART], accR[PART];
    double icA[PART], icB[PART];
    int keep[MAX_FILT];
    for (t = 0; t < PART; t++) { accL[t] = 0; accR[t] = 0; icA[t] = 0; icB[t] = 0; }
    for (i = 0; i < MAX_FILT; i++) {
        keep[i] = 0;
        st->filt[i].seen = 0;
    }

    for (b = 0; b < 3; b++) {
        double sl, sr;
        if (b == BUS_C && (st->cEmpty || st->cSkip)) continue;
        if (!st->rampUse) side(st, b, &sl, &sr);
        if (!st->colour_on) {
            if (st->icOn) ic_collect(st, b, icA, icB);
            if (st->rampUse) {
                for (t = 0; t < PART; t++) {
                    double sumY = 0.0;
                    double direct, wet, gl, gr;
                    if (!st->icOn) {
                        for (i = 0; i < N; i++) sumY += st->yBlk[b][i][t] + st->yBlkB[b][i][t];
                    }
                    if (st->sideHot && !st->icOn) sumY = side_apply(st, b, t, sumY);
                    if (bloom_hot(st) && !st->icOn) sumY = bloom_apply(st, b, t, sumY);
                    direct = st->daBlk[b][t] + st->dbBlk[b][t];
                    gl = st->rampBlk[RG_W + 2 * b][t];
                    gr = st->rampBlk[RG_W + 2 * b + 1][t];
                    wet = st->rampBlk[RG_DIR][t] * DIRECT_FOLD * direct
                        + st->rampBlk[RG_MK][t] * (st->rampBlk[RG_FDN][t] * sumY
                            + st->rampBlk[RG_EARLY][t] * st->esBlk[b][t]);
                    accL[t] += gl * wet;
                    accR[t] += gr * wet;
                }
            } else {
                for (t = 0; t < PART; t++) {
                    double sumY = 0.0;
                    double direct, wet;
                    if (!st->icOn) {
                        for (i = 0; i < N; i++) sumY += st->yBlk[b][i][t] + st->yBlkB[b][i][t];
                    }
                    if (st->sideHot && !st->icOn) sumY = side_apply(st, b, t, sumY);
                    if (bloom_hot(st) && !st->icOn) sumY = bloom_apply(st, b, t, sumY);
                    direct = st->daBlk[b][t] + st->dbBlk[b][t];
                    wet = st->direct_wet * DIRECT_FOLD * direct
                        + st->makeup * (st->fdn_wet * sumY + st->early_wet * st->esBlk[b][t]);
                    accL[t] += sl * wet;
                    accR[t] += sr * wet;
                }
            }
            continue;
        }
        if ((bloom_hot(st) || st->sideHot) && !st->icOn) {
            bloom_colour_bus(st, b, sl, sr, accL, accR, keep);
        } else
        {
            double directA[PART], directB[PART];
            double ident[PART];
            double fdnPre[PART];
            int map[MAX_IRS];
            int eiBase = (b == BUS_L) ? 0 : 1;
            for (i = 0; i < MAX_IRS; i++) map[i] = -1;
            for (t = 0; t < PART; t++) { ident[t] = 0; fdnPre[t] = 0; }
            for (slot = 0; slot < MAX_FILT; slot++) {
                for (t = 0; t < PART; t++) st->firIn[slot][t] = 0;
            }
            if (st->icOn) {
                ic_collect(st, b, icA, icB);
            } else {
                paint_lines(st, b, st->fdnIdx[b], st->yBlk[b], map, keep, ident);
                if (st->two) paint_lines(st, b, st->fdnIdxB[b], st->yBlkB[b], map, keep, ident);
            }
            if (b != BUS_C) {
                for (i = 0; i < N; i++) {
                    int tgt = early_target(st->fdnIdx[b], i, st->earlyIdx[eiBase][i]);
                    int tgtB = st->two ? early_target(st->fdnIdxB[b], i, st->earlyBIdx[eiBase][i]) : -2;
                    int u = usable_ir(st, tgt);
                    int uB = usable_ir(st, tgtB);
                    if (u >= 0) {
                        int s = ensure_mapped(st, b, map, keep, u);
                        if (s >= 0) {
                            if (st->rampUse) {
                                for (t = 0; t < PART; t++) st->firIn[s][t] += (float)(st->rampBlk[RG_EARLY][t] * st->eaBlk[b][i][t]);
                            } else {
                                for (t = 0; t < PART; t++) st->firIn[s][t] += (float)(st->early_wet * st->eaBlk[b][i][t]);
                            }
                        }
                    } else if (u == -1) {
                        if (st->rampUse) {
                            for (t = 0; t < PART; t++) ident[t] += st->rampBlk[RG_EARLY][t] * st->eaBlk[b][i][t];
                        } else {
                            for (t = 0; t < PART; t++) ident[t] += st->early_wet * st->eaBlk[b][i][t];
                        }
                    }
                    if (uB >= 0) {
                        int s = ensure_mapped(st, b, map, keep, uB);
                        if (s >= 0) {
                            if (st->rampUse) {
                                for (t = 0; t < PART; t++) st->firIn[s][t] += (float)(st->rampBlk[RG_EARLY][t] * st->ebBlk[b][i][t]);
                            } else {
                                for (t = 0; t < PART; t++) st->firIn[s][t] += (float)(st->early_wet * st->ebBlk[b][i][t]);
                            }
                        }
                    } else if (uB == -1) {
                        if (st->rampUse) {
                            for (t = 0; t < PART; t++) ident[t] += st->rampBlk[RG_EARLY][t] * st->ebBlk[b][i][t];
                        } else {
                            for (t = 0; t < PART; t++) ident[t] += st->early_wet * st->ebBlk[b][i][t];
                        }
                    }
                }
            }
            for (slot = 0; slot < MAX_FILT; slot++) {
                if (!keep[slot] || !st->filt[slot].used || st->filt[slot].bus != b || st->filt[slot].kind != 0) continue;
                {
                    float y[PART];
                    run_fir(st, &st->filt[slot], st->firIn[slot], y);
                    for (t = 0; t < PART; t++) fdnPre[t] += (double)y[t];
                }
            }
            for (t = 0; t < PART; t++) fdnPre[t] += ident[t];
            for (t = 0; t < PART; t++) directA[t] = st->daBlk[b][t];
            fir_or_wire(st, b, 1, st->directIdx[b], directA, directA);
            if (st->two) {
                for (t = 0; t < PART; t++) directB[t] = st->dbBlk[b][t];
                fir_or_wire(st, b, 2, st->directBIdx[b], directB, directB);
            } else {
                for (t = 0; t < PART; t++) directB[t] = 0;
            }
            if (st->rampUse) {
                for (t = 0; t < PART; t++) {
                    double earlyC = (b == BUS_C) ? st->rampBlk[RG_EARLY][t] * st->esBlk[b][t] : 0.0;
                    double wet = st->rampBlk[RG_DIR][t] * DIRECT_FOLD * (directA[t] + directB[t])
                        + st->rampBlk[RG_MK][t] * (fdnPre[t] + earlyC);
                    accL[t] += st->rampBlk[RG_W + 2 * b][t] * wet;
                    accR[t] += st->rampBlk[RG_W + 2 * b + 1][t] * wet;
                }
            } else {
                for (t = 0; t < PART; t++) {
                    double earlyC = (b == BUS_C) ? st->early_wet * st->esBlk[b][t] : 0.0;
                    double wet = st->direct_wet * DIRECT_FOLD * (directA[t] + directB[t])
                        + st->makeup * (fdnPre[t] + earlyC);
                    accL[t] += sl * wet;
                    accR[t] += sr * wet;
                }
            }
        }
    }

    if (st->icOn) {
        double oL[PART], oR[PART];
        ic_apply(st, icA, icB, oL, oR);
        if (bloom_hot(st) || st->sideHot) {
            for (t = 0; t < PART; t++) {
                if (st->sideHot) {
                    oL[t] = side_apply(st, 0, t, oL[t]);
                    oR[t] = side_apply(st, 2, t, oR[t]);
                }
                if (bloom_hot(st)) {
                    oL[t] = bloom_apply(st, 0, t, oL[t]);
                    oR[t] = bloom_apply(st, 2, t, oR[t]);
                }
            }
        }
        if (st->rampUse) {
            for (t = 0; t < PART; t++) {
                accL[t] += st->rampBlk[RG_MK][t] * st->rampBlk[RG_FDN][t] * oL[t];
                accR[t] += st->rampBlk[RG_MK][t] * st->rampBlk[RG_FDN][t] * oR[t];
            }
        } else {
            for (t = 0; t < PART; t++) {
                accL[t] += st->makeup * st->fdn_wet * oL[t];
                accR[t] += st->makeup * st->fdn_wet * oR[t];
            }
        }
    }

    if (st->colour_on) {
        for (i = 0; i < MAX_FILT; i++) {
            if (st->filt[i].used && !st->filt[i].seen) st->filt[i].used = 0;
        }
    }
    for (t = 0; t < PART; t++) {
        double yL = st->dryBlk[t] + accL[t];
        double yR = st->dryBlk[t] + accR[t];
        if (!finite_d(yL) || !finite_d(yR)) {
            scrub(st);
            for (; t < PART; t++) { outL[t] = 0; outR[t] = 0; }
            return;
        }
        {
            double zL = soft_limit(yL);
            double zR = soft_limit(yR);
            note_limit(st, yL, zL);
            note_limit(st, yR, zR);
            outL[t] = (float)zL;
            outR[t] = (float)zR;
        }
    }
}

static void zero_centre_bus(LiveStereo *st) {
    int i, f;
    Bus *bus = &st->bus[BUS_C];
    for (i = 0; i < N; i++) {
        Line *line = &bus->line[i];
        ls_zero(st->ring[BUS_C][i], st->cap * LANES * (int)sizeof(float));
        line->pz1 = line->pz2 = line->pz1b = line->pz2b = 0;
        line->airZ = line->airZe = line->airZb = line->airZf = 0;
        line->sz1 = line->sz2 = line->sz1e = line->sz2e = 0;
        line->sz1b = line->sz2b = line->sz1f = line->sz2f = 0;
        line->h2z1 = line->h2z2 = line->h2z1e = line->h2z2e = 0;
        line->h2z1b = line->h2z2b = line->h2z1f = line->h2z2f = 0;
        bus->fb[i] = 0;
        bus->fbB[i] = 0;
    }
    if (st->dir[BUS_C]) ls_zero(st->dir[BUS_C], st->cap * (int)sizeof(float));
    if (st->dirB[BUS_C]) ls_zero(st->dirB[BUS_C], st->cap * (int)sizeof(float));
    for (f = 0; f < MAX_FILT; f++) {
        if (st->filt[f].bus != BUS_C) continue;
        ls_zero(st->filt[f].prev, PART * (int)sizeof(float));
        ls_zero(st->filt[f].sz, (int)sizeof(st->filt[f].sz));
        st->filt[f].pos = 0;
        st->filt[f].cold = MAX_PART;
    }
}

static void run_partition(LiveStereo *st, const float *inL, const float *inR, float *outL, float *outR) {
    int t, b, i, hn;
    FwhtFn doFwht;
    DiffuseFn doDiff;
    bloom_fill(st);
    side_prepare(st, inL, inR);
    fill_ramp_block(st);
    {
        int e = st->micG[BUS_C] == 0.0;
        for (i = 0; e && i < N; i++) {
            if (st->bus[BUS_C].line[i].inj != 0.0 || st->bus[BUS_C].line[i].injB != 0.0) e = 0;
        }
        if (st->cEmpty && !e) zero_centre_bus(st);
        st->cEmpty = e;
    }
    {
        int skip = centre_unheard(st);
        /* Was silent, now heard. The skipped tank is stale, so start cold. */
        if (st->cSkip && !skip) zero_centre_bus(st);
        st->cSkip = skip;
    }
    g_csign = st->plainH ? 0 : 1;
    hn = st->hn;
    if (hn == 8) { doFwht = fwht8; doDiff = diffuse8; }
    else if (hn == 16) { doFwht = fwht16; doDiff = diffuse16; }
    else { hn = N; doFwht = fwht32; doDiff = diffuse32; }
    for (b = 0; b < 3; b++) {
        for (i = 0; i < N; i++) {
            for (t = 0; t < PART; t++) {
                st->yBlk[b][i][t] = 0;
                st->yBlkB[b][i][t] = 0;
                st->eaBlk[b][i][t] = 0;
                st->ebBlk[b][i][t] = 0;
            }
        }
    }
    for (t = 0; t < PART; t++) {
        double xL = (double)inL[t];
        double xR = (double)inR[t];
        double x, xA, xB, dry;
        int split = st->two;
        st->absT = st->modAbs + (double)t;
        if (st->proxRamp > 0) prox_advance(st);
        if (split) {
            xA = xL * st->gain_a;
            xB = xR * st->gain_b;
            x = 0.5 * (xA + xB);
        } else {
            xA = 0;
            xB = 0;
            x = 0.5 * (xL + xR);
        }
        if (st->bloomOn) {
            double det;
            if (split) {
                double aa = xA < 0.0 ? -xA : xA;
                double bb = xB < 0.0 ? -xB : xB;
                det = aa > bb ? aa : bb;
            } else det = x < 0.0 ? -x : x;
            bloom_sample(st, det, t);
        }
        if (st->radA || st->radB) {
            double xin = split ? xA : x;
            double yin = split ? xB : x;
            /* On-axis packs on=0 and src_step would return x. Skip the call.
               Image filters run only while that image's filter is live. */
            for (i = 0; i < N; i++) {
                if (st->radA && st->srcImg[0][i].on)
                    st->srcSmp[i] = src_step(&st->srcImg[0][i], xin);
                else
                    st->srcSmp[i] = xin;
                if (st->radB && st->srcImg[1][i].on)
                    st->srcSmpB[i] = src_step(&st->srcImg[1][i], yin);
                else
                    st->srcSmpB[i] = yin;
            }
            if (st->radA && st->srcDiff[0].on)
                st->diffSmp = src_step(&st->srcDiff[0], xin);
            else
                st->diffSmp = xin;
            if (st->radB && st->srcDiff[1].on)
                st->diffSmpB = src_step(&st->srcDiff[1], yin);
            else
                st->diffSmpB = yin;
            if (st->surfOn) {
                /* One cascade per line per source, shared by L, C and R.
                   Image lane colours early and, with no radiation, the inject.
                   Diffuse lane colours only the radiation inject.
                   Both banks, or bank A alone, are lines-across f64x2. */
                surf_stage(st, 1, split, 0.0, 0.0);
            }
            for (b = 0; b < 3; b++) {
                if (st->radA && st->srcDir[0][b].on)
                    st->dirSmp[b] = src_step(&st->srcDir[0][b], xin);
                else
                    st->dirSmp[b] = xin;
                if (st->radB && st->srcDir[1][b].on)
                    st->dirSmpB[b] = src_step(&st->srcDir[1][b], yin);
                else
                    st->dirSmpB[b] = yin;
            }
        } else if (st->surfOn) {
            /* No radiation: early and inject share x, so filter it once per line. */
            double xin = split ? xA : x;
            surf_stage(st, 0, split, xin, xB);
        }
        if (st->shared) {
            /* History of the shared line outputs lives in bus L's FDN lanes.
               L's write pointer advances inside bus_sample(L), so the tap
               offset carries +1 to read the sample just stored.
               The C loop (FWHT and diffuser, both banks) uses CSIGN_DS.
               L and R stay on CSIGN_D. */
            g_csignTab = CSIGN_DS;
            bus_sample(st, BUS_C, x, xA, xB, split, t, hn, doFwht, doDiff);
            g_csignTab = CSIGN_D;
            for (i = 0; i < N; i++) {
                Line *hl = &st->bus[BUS_L].line[i];
                write_lane(st->ring[BUS_L][i], hl->w, LANE_FDN, (float)st->yBlk[BUS_C][i][t]);
                if (split) write_lane(st->ring[BUS_L][i], hl->w, LANE_FDNB, (float)st->yBlkB[BUS_C][i][t]);
            }
            bus_sample(st, BUS_L, x, xA, xB, split, t, hn, doFwht, doDiff);
            bus_sample(st, BUS_R, x, xA, xB, split, t, hn, doFwht, doDiff);
            {
                double d0A = 0.0, d0B = 0.0;
                int bb;
                for (bb = 0; bb < 3; bb += 2) {
                    for (i = 0; i < hn; i++) {
                        double dA = st->bus[BUS_C].line[i].delay - st->bus[bb].line[i].delay;
                        double dB = st->bus[BUS_C].line[i].delayB - st->bus[bb].line[i].delayB;
                        if (dA > d0A) d0A = dA;
                        if (split && dB > d0B) d0B = dB;
                    }
                }
                d0A = (double)(int)(d0A + 0.999999);
                d0B = (double)(int)(d0B + 0.999999);
                for (bb = 0; bb < 3; bb++) {
                    for (i = 0; i < hn; i++) {
                        Line *hl = &st->bus[BUS_L].line[i];
                        double offA = d0A + 1.0;
                        double offB = d0B + 1.0;
                        int ia, ib;
                        if (bb != BUS_C) {
                            offA += st->bus[bb].line[i].delay - st->bus[BUS_C].line[i].delay;
                            offB += st->bus[bb].line[i].delayB - st->bus[BUS_C].line[i].delayB;
                        }
                        offA += st->shJit[bb][i];
                        offB += st->shJitB[bb][i];
                        ia = hl->w - (int)(offA + 0.5);
                        ib = hl->w - (int)(offB + 0.5);
                        while (ia < 0) ia += st->cap;
                        while (ib < 0) ib += st->cap;
                        while (ia >= st->cap) ia -= st->cap;
                        while (ib >= st->cap) ib -= st->cap;
                        st->yBlk[bb][i][t] = st->bus[bb].shG * (double)st->ring[BUS_L][i][ia * LANES + LANE_FDN];
                        if (split) st->yBlkB[bb][i][t] = st->bus[bb].shGB * (double)st->ring[BUS_L][i][ib * LANES + LANE_FDNB];
                    }
                }
            }
        } else {
            for (b = 0; b < 3; b++) {
                if (b == BUS_C && (st->cEmpty || st->cSkip)) continue;
                bus_sample(st, b, x, xA, xB, split, t, hn, doFwht, doDiff);
            }
        }
        if (st->rampUse) {
            double dg = st->rampBlk[RG_DRY][t];
            if (st->colour_on && st->mono) dry = dg * xL;
            else if (st->two) dry = dg * 0.5 * (st->gain_a * xL + st->gain_b * xR);
            else dry = dg * x;
        } else if (st->colour_on && st->mono) dry = st->dry_gain * xL;
        else if (st->two) dry = st->dry_gain * 0.5 * (st->gain_a * xL + st->gain_b * xR);
        else dry = st->dry_gain * x;
        st->dryBlk[t] = dry;
        if (st->predelayN > 0) {
            st->pdW += 1;
            if (st->pdW >= 4800) st->pdW = 0;
        }
    }
    if (st->modOn) st->modAbs += (double)PART;
    mix_partition(st, outL, outR);
}

LS_EXPORT("live_stereo")
void live_stereo(LiveStereo *st, const float *inL, const float *inR, float *outL, float *outR, int n) {
    int inI = 0, outI = 0;
    if (!outL || !outR || n <= 0) return;
    if (!st || st->magic != 0x2011 || !st->ready || !inL || !inR) {
        int i;
        for (i = 0; i < n; i++) { outL[i] = 0; outR[i] = 0; }
        return;
    }
    while (inI < n || outI < n) {
        if (st->pendN == PART) {
            run_partition(st, st->pendL, st->pendR, st->qL, st->qR);
            st->pendN = 0;
            st->qN = PART;
            st->qAt = 0;
            continue;
        }
        if (outI < n && st->qAt < st->qN) {
            int k = st->qN - st->qAt;
            if (k > n - outI) k = n - outI;
            ls_copy(outL + outI, st->qL + st->qAt, k * (int)sizeof(float));
            ls_copy(outR + outI, st->qR + st->qAt, k * (int)sizeof(float));
            outI += k;
            st->qAt += k;
            if (st->qAt >= st->qN) { st->qN = 0; st->qAt = 0; }
            continue;
        }
        if (inI < n && st->pendN < PART) {
            int k = PART - st->pendN;
            if (k > n - inI) k = n - inI;
            ls_copy(st->pendL + st->pendN, inL + inI, k * (int)sizeof(float));
            ls_copy(st->pendR + st->pendN, inR + inI, k * (int)sizeof(float));
            st->pendN += k;
            inI += k;
            continue;
        }
        if (outI < n) {
            int i;
            for (i = outI; i < n; i++) { outL[i] = 0; outR[i] = 0; }
            break;
        }
        break;
    }
}
