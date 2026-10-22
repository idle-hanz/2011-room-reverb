/* Bloom tail gain, colour, and pre colour. Coefficients come from the blob.
   bloomOn == 0 and predelayN == 0 never enter these functions.
   The formulas match software/engine/bloom_dsp.py. */

static double ls_ln(double x) {
    union { double d; unsigned long long u; } v;
    int e, i;
    double m, y, y2, s, p;
    if (!(x > 0.0)) return -745.0;
    v.d = x;
    /* 11 exponent bits. 1023 drops the top bit, so ln is wrong for every x >= 2. */
    e = (int)((v.u >> 52) & 2047) - 1023;
    v.u = (v.u & 0x000FFFFFFFFFFFFFULL) | 0x3FF0000000000000ULL;
    m = v.d;
    y = (m - 1.0) / (m + 1.0);
    y2 = y * y;
    s = y;
    p = y;
    for (i = 1; i < 10; i++) {
        p *= y2;
        s += p / (double)(2 * i + 1);
    }
    return 2.0 * s + (double)e * 0.693147180559945309417;
}

static double ls_log10(double x) { return ls_ln(x) * 0.43429448190325182765; }

static double ls_from_db(double db) { return ls_exp(db * 0.1151292546497022842); }

static double ls_tanh(double x) {
    double e;
    if (x > 12.0) return 1.0;
    if (x < -12.0) return -1.0;
    e = ls_exp(-2.0 * x);
    return (1.0 - e) / (1.0 + e);
}

static double bloom_db(double x) {
    double a = x < 0.0 ? -x : x;
    if (a < 1.0e-12) a = 1.0e-12;
    return 20.0 * ls_log10(a);
}

static double bloom_gc(double x_db, const double *c) {
    double T = c[3], R = c[4], W = c[5], R2 = c[6], K2 = c[7];
    double d = x_db - T;
    double y, gr;
    if (W > 0.0 && 2.0 * d < -W) y = x_db;
    else if (W > 0.0 && (2.0 * d < 0.0 ? -2.0 * d : 2.0 * d) <= W)
        y = x_db + (1.0 / R - 1.0) * (d + W / 2.0) * (d + W / 2.0) / (2.0 * W);
    else if (W <= 0.0 && d <= 0.0) y = x_db;
    else y = T + d / R;
    if (R2 > 0.0 && d > K2) y = T + K2 / R + (d - K2) / R2;
    gr = x_db - y;
    if (gr < 0.0) return 0.0;
    return gr;
}

static double bloom_hp(LiveStereo *st, double x) {
    /* DF2T Butterworth. bC[9] is b0. a1 = 1-2*b0. Same state order as sosfilt. */
    double b0 = st->bC[9];
    double a1, y;
    if (!(b0 > 0.0 && b0 < 1.0)) return x;
    a1 = 1.0 - 2.0 * b0;
    y = b0 * x + st->dSc;
    st->dSc = -b0 * x - a1 * y;
    return y;
}

static double bloom_natural(LiveStereo *st, double x_db) {
    const double *c = st->bC;
    double T = ls_from_db(x_db) - 1.0;
    double w, tf, krf;
    if (T < 0.0) T = 0.0;
    if (T > st->dU) {
        if (st->dMode != 1) {
            st->dFa = st->dU;
            st->dSa = st->dU;
            st->dMode = 1;
        }
        st->dFa += (T - st->dFa) * c[10];
        st->dSa += (T - st->dSa) * c[11];
        st->dU = c[12] * st->dFa + (1.0 - c[12]) * st->dSa;
    } else {
        if (st->dMode != 2) {
            st->dRf = st->dU;
            st->dRs = st->dU;
            w = c[18] + c[19] * st->dM;
            if (w < 0.0) w = 0.0;
            if (w > 0.9) w = 0.9;
            st->dWdet = w;
            st->dMode = 2;
        }
        tf = c[20] * c[16] + c[21] * st->dM * c[16];
        if (tf < 1.0e-6) tf = 1.0e-6;
        krf = 1.0 - ls_exp(-1.0 / (tf * c[17]));
        st->dRf += (T - st->dRf) * krf;
        st->dRs += (T - st->dRs) * c[15];
        st->dU = (1.0 - st->dWdet) * st->dRf + st->dWdet * st->dRs;
    }
    if (st->dU > 0.06) st->dM += (1.0 - st->dM) * c[13];
    else st->dM -= st->dM * c[14];
    if (st->dU < 0.0) return 0.0;
    return 20.0 * ls_log10(1.0 + st->dU);
}

static double bloom_glue(LiveStereo *st, double tgt) {
    const double *c = st->bC;
    double v = st->dV1 + st->dV2;
    double cur = 0.0;
    double dt = c[16];
    if (tgt > v) cur = (tgt - v) * c[15] / c[10];
    st->dV1 = (st->dV1 + dt * cur / c[13]) / (1.0 + dt / c[11]);
    st->dV2 = (st->dV2 + dt * cur / c[14]) / (1.0 + dt / c[12]);
    return st->dV1 + st->dV2;
}

static double bloom_nuke(LiveStereo *st, double tgt) {
    const double *c = st->bC;
    double w;
    if (tgt > st->dF) st->dF += (tgt - st->dF) * c[10];
    else st->dF += (tgt - st->dF) * c[11];
    if (tgt > st->dS) st->dS += (tgt - st->dS) * c[10];
    else st->dS += (tgt - st->dS) * c[12];
    if (tgt > 0.5) st->dGv += (1.0 - st->dGv) * c[13];
    else st->dGv -= st->dGv * c[13] * 0.25;
    w = c[14] + c[15] * st->dGv;
    if (w > 0.95) w = 0.95;
    return (1.0 - w) * st->dF + w * st->dS;
}

static double bloom_rc(LiveStereo *st, double tgt) {
    const double *c = st->bC;
    double mix, te, kr;
    if (st->dIdle && tgt > 0.0) {
        st->dCnt += 1;
        if (st->dCnt > (int)c[13]) st->dIdle = 0;
    }
    if (tgt > st->dG && !st->dIdle) {
        st->dF += (tgt - st->dF) * c[10];
        st->dS += (tgt - st->dS) * c[11];
        mix = c[12] * st->dF + (1.0 - c[12]) * st->dS;
        if (mix > st->dG) st->dG = mix;
    } else if (tgt <= st->dG) {
        te = c[14] * ls_exp(c[15] * ls_ln((st->dG > 0.5 ? st->dG : 0.5) / 10.0));
        if (te < 1.0e-8) te = 1.0e-8;
        kr = 1.0 - ls_exp(-1.0 / (te * c[17]));
        st->dG += (tgt - st->dG) * kr;
        if (st->dF > st->dG) st->dF = st->dG;
        if (st->dS > st->dG) st->dS = st->dG;
    }
    if (tgt <= 0.0) st->dQuiet += 1;
    else st->dQuiet = 0;
    if (st->dG < 0.05 && st->dQuiet > (int)c[16]) {
        st->dIdle = 1;
        st->dCnt = 0;
    }
    return st->dG;
}

static double bloom_swell(LiveStereo *st, double vt) {
    const double *c = st->bC;
    double cur = vt > st->dVc ? (vt - st->dVc) / c[10] : 0.0;
    double iu = (st->dVc - st->dVu) / c[13];
    double dt = c[15];
    double v;
    st->dVc += dt * (cur - st->dVc / c[12] - iu) / c[11];
    st->dVu += dt * iu / c[14];
    v = st->dVc < 0.0 ? 0.0 : st->dVc;
    return 18.1 * ls_ln(1.0 + v / 8.06);
}

static double bloom_gr(LiveStereo *st, double x) {
    int pid = (int)(st->bC[0] + 0.5);
    double sc = st->bC[8] > 0.5 ? bloom_hp(st, x) : x;
    double x_db = bloom_db(sc);
    double tgt = bloom_gc(x_db, st->bC);
    if (pid == 0) return bloom_natural(st, tgt);
    if (pid == 1) return bloom_glue(st, tgt);
    if (pid == 2) return bloom_rc(st, tgt);
    if (pid == 3) return bloom_nuke(st, tgt);
    return bloom_swell(st, 8.06 * (ls_exp(tgt / 18.1) - 1.0));
}

static double bloom_pd(LiveStereo *st, int bus, int bank, int line, double y) {
    int n = st->predelayN;
    int w, r;
    if (n < 1) return y;
    if (n > 4799) n = 4799;
    if (bus < 0) bus = 0;
    if (bus > 2) bus = 2;
    if (bank < 0) bank = 0;
    if (bank > 1) bank = 1;
    if (line < 0) line = 0;
    if (line > 31) line = 31;
    w = st->pdW;
    if (w < 0 || w >= 4800) w = 0;
    st->pdMem[bus][bank][line][w] = (float)y;
    r = w - n;
    if (r < 0) r += 4800;
    return (double)st->pdMem[bus][bank][line][r];
}

static float g_hb[47];
static int g_hbReady = 0;

static void hb_init(void) {
    int i, m = 23, n = 47;
    double centre, pi = 3.14159265358979323846;
    if (g_hbReady) return;
    for (i = 0; i < n; i++) {
        int k = i - m;
        double window = 0.42 - 0.5 * ls_cos(2.0 * pi * (double)i / (double)(n - 1))
            + 0.08 * ls_cos(4.0 * pi * (double)i / (double)(n - 1));
        double h = (k == 0) ? 0.5 : ls_sin(0.5 * pi * (double)k) / (pi * (double)k);
        g_hb[i] = (float)(h * window);
    }
    centre = (double)g_hb[m];
    if (centre == 0.0) centre = 0.5;
    for (i = 0; i < n; i++) g_hb[i] = (float)((double)g_hb[i] * (0.5 / centre));
    g_hbReady = 1;
}

static double hb_dot(float *z, double x, int gain2) {
    int i;
    double g = gain2 ? 2.0 : 1.0;
    double acc = g * (double)g_hb[0] * x;
    for (i = 0; i < 46; i++) acc += g * (double)g_hb[i + 1] * (double)z[i];
    for (i = 45; i > 0; i--) z[i] = z[i - 1];
    z[0] = (float)x;
    return acc;
}

static double bloom_distort(LiveStereo *st, int bus, double v, double depth) {
    double vr = st->bC[28];
    double a2 = st->bC[29], a3 = st->bC[30], b = st->bC[31];
    double u, o, tb, s2;
    int fam = (int)(st->bC[27] + 0.5);
    if (!(vr > 1.0e-12)) vr = 1.0;
    u = v / vr;
    if (fam == 1) {
        tb = ls_tanh(b);
        s2 = 1.0 - tb * tb;
        if (s2 < 1.0e-12) s2 = 1.0e-12;
        o = vr * depth * ((ls_tanh(u + b) - tb) / s2 - u);
    } else if (st->bC[37] > 0.5) {
        double F = a2 * u * u * u / 3.0 + a3 * u * u * u * u / 4.0;
        double du = u - st->cX0[bus];
        double g;
        if (du > 1.0e-7 || du < -1.0e-7) g = (F - st->cF0[bus]) / du;
        else {
            double m = 0.5 * (u + st->cX0[bus]);
            g = a2 * m * m + a3 * m * m * m;
        }
        st->cX0[bus] = u;
        st->cF0[bus] = F;
        o = vr * depth * g;
    } else {
        o = vr * depth * (a2 * u * u + a3 * u * u * u);
    }
    return o;
}

static double bloom_mem_dc(LiveStereo *st, int bus, double o) {
    /* Once per base-rate sample, after the down-halfband. */
    if (st->bC[34] > 0.0 && st->bC[34] < 1.0) {
        double a = st->bC[34];
        st->cMem[bus] = a * st->cMem[bus] + (1.0 - a) * o;
        o = st->cMem[bus];
    }
    if (st->bC[35] > 0.0 && st->bC[35] < 1.0) {
        double y = o - st->cDcX[bus] + st->bC[35] * st->cDcY[bus];
        st->cDcX[bus] = o;
        st->cDcY[bus] = y;
        o = y;
    }
    return o;
}

static double bloom_eq(LiveStereo *st, int bus, double x) {
    int n = (st->bN - 40) / 5;
    int s;
    if (n < 0) n = 0;
    if (n > 6) n = 6;
    for (s = 0; s < n; s++) {
        const double *q = st->bC + 40 + 5 * s;
        double y = q[0] * x + st->cEq[bus][s][0];
        st->cEq[bus][s][0] = q[1] * x - q[3] * y + st->cEq[bus][s][1];
        st->cEq[bus][s][1] = q[2] * x - q[4] * y;
        x = y;
    }
    return x;
}

static double bloom_shape(LiveStereo *st, int bus, double v, double gr, double mix) {
    double d0, Gs, depth, dist;
    if (st->bC[26] < 0.5 || mix <= 0.0) return v;
    d0 = st->bC[32];
    Gs = st->bC[33];
    depth = d0;
    if (Gs > 1.0e-12) {
        double t = gr / Gs;
        if (t < 0.0) t = 0.0;
        if (t > 1.0) t = 1.0;
        depth = d0 + (1.0 - d0) * t;
    }
    if (st->bC[36] > 1.5) {
        double a, b, y0, y1;
        hb_init();
        a = hb_dot(st->hbZ[bus][0], v, 1);
        b = hb_dot(st->hbZ[bus][0], 0.0, 1);
        y0 = bloom_distort(st, bus, a, depth);
        y1 = bloom_distort(st, bus, b, depth);
        (void)hb_dot(st->hbZ[bus][1], y0, 0);
        dist = hb_dot(st->hbZ[bus][1], y1, 0);
        return v + bloom_mem_dc(st, bus, dist) * mix;
    }
    return v + bloom_mem_dc(st, bus, bloom_distort(st, bus, v, depth)) * mix;
}

static double bloom_nclip(double v, const double *p, double *mem) {
    double p0 = p[4], p1 = p[5], p2 = p[6];
    double a, sc, w, d;
    if (p[13] != 0.0 && p[14] > 0.0) {
        *mem = p[14] * (*mem) + (1.0 - p[14]) * v;
        a = p1 + p[13] * (*mem);
    } else a = p1;
    sc = v > 0.0 ? 1.0 + a : 1.0 - a;
    if (sc < 1.0e-6) sc = 1.0e-6;
    w = v / sc;
    {
        double aw = w < 0.0 ? -w : w;
        double den;
        if (p0 < 0.5) p0 = 0.5;
        den = ls_exp(ls_ln(1.0 + ls_exp(p0 * ls_ln(aw + 1.0e-30))) / p0);
        d = sc * w / den - v + p2 * v * v;
    }
    return d;
}

static double bloom_pre(LiveStereo *st, int bus, double x) {
    const double *p = st->pC;
    double drive = ls_from_db(p[2]);
    double v = x * drive;
    double h1, ue, u, d, y;
    int os;
    /* H1 */
    h1 = p[15] * v + st->prS[bus][0];
    st->prS[bus][0] = p[16] * v - p[18] * h1 + st->prS[bus][1];
    st->prS[bus][1] = p[17] * v - p[19] * h1;
    v = h1;
    if (p[7] > 0.5) {
        double a = p[8], g = p[9], s1;
        s1 = a * st->prS[bus][2] + (1.0 - a) * v;
        st->prS[bus][2] = s1;
        ue = v + (g - 1.0) * s1;
    } else ue = v;
    u = ue / (p[3] > 1.0e-12 ? p[3] : 1.0);
    os = (int)(p[1] + 0.5);
    if (os < 1) os = 1;
    if (os > 16) os = 16;
    if (os > 1) hb_init();
    d = 0.0;
    if (os == 1) {
        d = p[3] * bloom_nclip(u, p, &st->prS[bus][3]);
    } else {
        /* Cascaded halfband. The last downsampled sample is this input's return. */
        double cur[16];
        double nxt[16];
        int ncur = 1, stage, nup, k;
        int nstage = 0;
        int t = os;
        cur[0] = u;
        while (t > 1) { nstage += 1; t >>= 1; }
        if (nstage > 4) nstage = 4;
        for (stage = 0; stage < nstage; stage++) {
            nup = 0;
            for (k = 0; k < ncur; k++) {
                nxt[nup++] = hb_dot(st->prHb[bus][stage][0], cur[k], 1);
                if (nup < 16) nxt[nup++] = hb_dot(st->prHb[bus][stage][0], 0.0, 1);
            }
            ncur = nup;
            for (k = 0; k < ncur; k++) cur[k] = nxt[k];
        }
        for (k = 0; k < ncur; k++) cur[k] = bloom_nclip(cur[k], p, &st->prS[bus][3]);
        for (stage = nstage - 1; stage >= 0; stage--) {
            nup = 0;
            for (k = 0; k < ncur; k += 2) {
                double a = hb_dot(st->prHb[bus][stage][1], cur[k], 0);
                double b = (k + 1 < ncur) ? hb_dot(st->prHb[bus][stage][1], cur[k + 1], 0) : a;
                nxt[nup++] = b;
                (void)a;
            }
            ncur = nup > 0 ? nup : 1;
            for (k = 0; k < ncur; k++) cur[k] = nxt[k];
        }
        d = p[3] * cur[0];
    }
    if (p[7] > 0.5) {
        double a = p[8], g = p[9];
        double yi = (d - (g - 1.0) * a * st->prS[bus][4]) / (1.0 + (g - 1.0) * (1.0 - a));
        st->prS[bus][4] = a * st->prS[bus][4] + (1.0 - a) * yi;
        d = yi;
    }
    {
        double af = p[10];
        double Vphi = p[11];
        double cphi = p[12];
        double s1 = af * st->prS[bus][5] + (1.0 - af) * v;
        double e, fd;
        st->prS[bus][5] = s1;
        e = s1 / (Vphi > 1.0e-12 ? Vphi : 1.0);
        e = e * e * e;
        fd = cphi * Vphi * (e - af * st->prS[bus][6]) / (1.0 - af > 1.0e-12 ? 1.0 - af : 1.0e-12);
        st->prS[bus][6] = e;
        d += fd;
    }
    /* H2 on the sum of the linear path and the distortion. Linear path is H1(v)
       already in v. Distortion is d. Small-signal d is ~0, so the shelf stays. */
    y = v + d;
    {
        double o = p[20] * y + st->prS[bus][7];
        st->prS[bus][7] = p[21] * y - p[23] * o + st->prS[bus][8];
        st->prS[bus][8] = p[22] * y - p[24] * o;
        y = o;
    }
    /* Section C. H2 is packed already divided by the 1 kHz cascade gain.
       Drive must not change that linear level. */
    if (p[2] != 0.0 && drive > 1.0e-12) y /= drive;
    return y;
}

static void bloom_sample(LiveStereo *st, double x, int t) {
    double gr, wet, hi, lo, g;
    if (!st->bloomOn) return;
    gr = bloom_gr(st, x);
    hi = st->bC[1];
    lo = -st->bC[2];
    if (lo > 0.0) lo = 0.0;
    wet = hi - gr;
    if (wet > hi) wet = hi;
    if (wet < lo) wet = lo;
    g = ls_from_db(wet);
    st->bG[t] = g;
    st->bGR[t] = gr;
    st->bHold = g;
}

static double bloom_apply(LiveStereo *st, int bus, int t, double sum) {
    double y, g, gr, u, p, coloured;
    /* u and p are the 15 ms click ramps. Steady off is u = p = 0 and
       bloomOn = preOn = 0, and this function is not called. */
    u = st->bMixAt[t];
    p = st->pMixAt[t];
    if (!st->bloomOn && u <= 0.0) {
        if (p > 0.0) {
            coloured = bloom_pre(st, bus, sum);
            return sum + (coloured - sum) * p;
        }
        return sum;
    }
    g = st->bloomOn ? st->bG[t] : st->bHold;
    if (u < 1.0) g = 1.0 + (g - 1.0) * u;
    gr = st->bGR[t];
    if (st->bC[38] > 0.5 && st->bC[26] > 0.5) {
        /* Swell is input-side: colour, then 10^(W/20), then EQ. */
        y = bloom_shape(st, bus, sum, gr, u);
        y *= g;
        y = bloom_eq(st, bus, y);
    } else if (st->bC[26] > 0.5) {
        /* Output side: attenuate, colour, makeup 10^((W+GR)/20), then EQ.
           g is the ramped 10^(W/20). Times 10^(GR/20) is the makeup. */
        double att = ls_from_db(-gr);
        y = bloom_shape(st, bus, sum * att, gr, u);
        y *= g * ls_from_db(gr);
        y = bloom_eq(st, bus, y);
    } else {
        y = sum * g;
    }
    if (p > 0.0) {
        coloured = bloom_pre(st, bus, y);
        if (p < 1.0) y = y + (coloured - y) * p;
        else y = coloured;
    }
    return y;
}

static int bloom_hot(const LiveStereo *st) {
    return st->bloomOn || st->preOn || st->bRampLeft > 0 || st->pRampLeft > 0;
}

static void bloom_scrub(LiveStereo *st) {
    st->dSc = st->dU = st->dFa = st->dSa = 0.0;
    st->dRf = st->dRs = st->dWdet = st->dM = 0.0;
    st->dV1 = st->dV2 = st->dF = st->dS = 0.0;
    st->dGv = st->dG = st->dVc = st->dVu = 0.0;
    st->dMode = 0;
    st->dIdle = 1;
    st->dCnt = 0;
    st->dQuiet = 0;
    st->pdW = 0;
    st->bHold = 1.0;
    ls_zero(st->cX0, (int)sizeof(st->cX0));
    ls_zero(st->cF0, (int)sizeof(st->cF0));
    ls_zero(st->cMem, (int)sizeof(st->cMem));
    ls_zero(st->cDcX, (int)sizeof(st->cDcX));
    ls_zero(st->cDcY, (int)sizeof(st->cDcY));
    ls_zero(st->cEq, (int)sizeof(st->cEq));
    ls_zero(st->hbZ, (int)sizeof(st->hbZ));
    ls_zero(st->prS, (int)sizeof(st->prS));
    ls_zero(st->prHb, (int)sizeof(st->prHb));
    ls_zero(st->pdMem, (int)sizeof(st->pdMem));
}

static void bloom_arm(LiveStereo *st, int has10, const float *c10, int n10,
    int has11, float pd, int has12, const float *c12, int n12) {
    int i, n;
    int wantB = (has10 && c10 && n10 >= 40) ? 1 : 0;
    int wantP = (has12 && c12 && n12 >= 25) ? 1 : 0;
    double tgtB = wantB ? 1.0 : 0.0;
    double tgtP = wantP ? 1.0 : 0.0;
    if (wantB) {
        if (n10 > 80) n10 = 80;
        for (i = 0; i < n10; i++) st->bC[i] = (double)c10[i];
        for (; i < 80; i++) st->bC[i] = 0.0;
        st->bN = n10;
    }
    if (has11) {
        n = (int)(pd + (pd < 0.0 ? -0.5 : 0.5));
        if (n < 0) n = 0;
        if (n > 4799) n = 4799;
        st->predelayN = n;
    } else st->predelayN = 0;
    if (wantP) {
        for (i = 0; i < 25; i++) st->pC[i] = (double)c12[i];
    }
    /* First load snaps. live_bind has already zeroed the struct. */
    if (!st->bRampPrimed) {
        st->bRampPrimed = 1;
        st->bloomOn = wantB;
        st->preOn = wantP;
        st->bRampFrom = st->bRampTo = tgtB;
        st->pRampFrom = st->pRampTo = tgtP;
        st->bRampLeft = st->pRampLeft = 0;
        st->bRampTotal = st->pRampTotal = 0;
        st->bMixCur = tgtB;
        st->pMixCur = tgtP;
        st->bHold = 1.0;
        return;
    }
    if (!(!wantB && !st->bloomOn && st->bRampLeft <= 0)) {
        if (tgtB != st->bRampTo || (st->bRampLeft <= 0 && st->bMixCur != tgtB)) {
            n = (int)(0.015 * (double)st->sr + 0.5);
            if (n < 1) n = 1;
            st->bRampFrom = st->bMixCur;
            st->bRampTo = tgtB;
            st->bRampTotal = n;
            st->bRampLeft = n;
            st->bloomOn = 1;
        }
    }
    if (!(!wantP && !st->preOn && st->pRampLeft <= 0)) {
        if (tgtP != st->pRampTo || (st->pRampLeft <= 0 && st->pMixCur != tgtP)) {
            n = (int)(0.015 * (double)st->sr + 0.5);
            if (n < 1) n = 1;
            st->pRampFrom = st->pMixCur;
            st->pRampTo = tgtP;
            st->pRampTotal = n;
            st->pRampLeft = n;
            st->preOn = 1;
        }
    }
}

static void bloom_fill(LiveStereo *st) {
    int i;
    if (st->bRampLeft <= 0 && st->bRampTo <= 0.0) st->bloomOn = 0;
    if (st->pRampLeft <= 0 && st->pRampTo <= 0.0) st->preOn = 0;
    if (!bloom_hot(st)) return;
    for (i = 0; i < PART; i++) {
        double u, p;
        if (st->bRampLeft > 0 && st->bRampTotal > 0) {
            int done = st->bRampTotal - st->bRampLeft;
            u = st->bRampFrom + (st->bRampTo - st->bRampFrom) * ((double)done / (double)st->bRampTotal);
            st->bRampLeft -= 1;
            if (st->bRampLeft <= 0) u = st->bRampTo;
        } else u = st->bRampTo;
        if (st->pRampLeft > 0 && st->pRampTotal > 0) {
            int done = st->pRampTotal - st->pRampLeft;
            p = st->pRampFrom + (st->pRampTo - st->pRampFrom) * ((double)done / (double)st->pRampTotal);
            st->pRampLeft -= 1;
            if (st->pRampLeft <= 0) p = st->pRampTo;
        } else p = st->pRampTo;
        if (u < 0.0) u = 0.0;
        if (u > 1.0) u = 1.0;
        if (p < 0.0) p = 0.0;
        if (p > 1.0) p = 1.0;
        st->bMixAt[i] = u;
        st->pMixAt[i] = p;
    }
    st->bMixCur = st->bMixAt[PART - 1];
    st->pMixCur = st->pMixAt[PART - 1];
}
