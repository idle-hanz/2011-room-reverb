"""CPU prototype of the D-UI26 SURF colour on top of F2 (box only, not for shipping).
Per line and per source: one K-biquad cascade on the image input (srcSmp[i] -> early lane AND, in the
no-radiation path, the FDN) and one on the diffuse input (diffSmp -> FDN inject). Identity coefficients
(b0=1) so the output stays bit-identical while the full arithmetic runs. K from -DSURF_K (default 4).
The cascades are shared by the 3 buses (same tap -> same hit faces)."""
import sys
src=open('F2.c').read()
def rep(s,a,b,n=1):
    c=s.count(a); assert c==n,(a,c); return s.replace(a,b)
s=src
s=rep(s,"/* One source filter: gain, RBJ high shelf (TDF-II), optional soft one-pole. */",
"""#ifndef SURF_K
#define SURF_K 4
#endif
/* D-UI26 prototype: per-line surface colour cascade, DF2T, shared by the 3 buses. */
typedef struct SurfCas { int k; double c[SURF_K][5]; double z[SURF_K][2]; } SurfCas;
static inline double surf_step(SurfCas *f, double x) {
    int j;
    for (j = 0; j < f->k; j++) {
        double *c = f->c[j], *z = f->z[j];
        double y = c[0] * x + z[0];
        z[0] = c[1] * x - c[3] * y + z[1];
        z[1] = c[2] * x - c[4] * y;
        x = y;
    }
    return x;
}
/* One source filter: gain, RBJ high shelf (TDF-II), optional soft one-pole. */""")
s=rep(s,"    double diffSmp, diffSmpB;\n","    double diffSmp, diffSmpB;\n    double diffArr[N], diffArrB[N];\n    SurfCas sfI[2][N], sfD[2][N];\n    int surfOn;\n")
s=rep(s,"    st->earlyGateOn = 0;\n    st->cEmpty = 0;\n",
"""    st->earlyGateOn = 0;
    st->surfOn = 1;
    for (b = 0; b < 2; b++) for (i = 0; i < N; i++) {
        int j;
        st->sfI[b][i].k = SURF_K; st->sfD[b][i].k = SURF_K;
        for (j = 0; j < SURF_K; j++) { st->sfI[b][i].c[j][0] = 1.0; st->sfD[b][i].c[j][0] = 1.0; }
    }
    st->cEmpty = 0;
""")
s=rep(s,"""            for (b = 0; b < 3; b++) {
                if (st->radA && st->srcDir[0][b].on)""",
"""            if (st->surfOn) {
                for (i = 0; i < N; i++) {
                    st->srcSmp[i] = surf_step(&st->sfI[0][i], st->srcSmp[i]);
                    st->diffArr[i] = surf_step(&st->sfD[0][i], st->diffSmp);
                    if (two) {
                        st->srcSmpB[i] = surf_step(&st->sfI[1][i], st->srcSmpB[i]);
                        st->diffArrB[i] = surf_step(&st->sfD[1][i], st->diffSmpB);
                    }
                }
            }
            for (b = 0; b < 3; b++) {
                if (st->radA && st->srcDir[0][b].on)""")
s=rep(s,"xin = tint(line, st->diffSmp * injLoop, 0);","xin = tint(line, st->diffArr[i] * injLoop, 0);")
s=rep(s,"tint(line, 0.5 * st->diffSmp * injUse, 0)","tint(line, 0.5 * st->diffArr[i] * injUse, 0)")
s=rep(s,"tint(line, 0.5 * st->diffSmpB * injUse, 3)","tint(line, 0.5 * st->diffArrB[i] * injUse, 3)")
open('SURF_proto.c','w').write(s); print('ok')
