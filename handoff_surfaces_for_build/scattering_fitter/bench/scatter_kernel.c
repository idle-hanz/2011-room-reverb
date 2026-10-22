/* Prototype Track-C scattering kernel (feed-forward, early lane only). Box benchmark, not product code.
 * Per line per sample: 1 specular read (lin-interp) -> biquad ; K cluster reads (lin-interp, ±1/sqrt(K) sign gain)
 * summed -> one biquad (scatter shelf). One ring write (models the existing early-lane write). */
#define MAXN 128
#define MAXK 32
#define RING 16384
#define MASK (RING-1)
#ifdef __wasm__
#define EXPORT(n) __attribute__((export_name(n)))
#else
#define EXPORT(n)
#endif
typedef struct { float b0,b1,b2,a1,a2,z1,z2; } BQ;
static float ring[MAXN][RING];
static int   w;
static float dly[MAXN];
static int   off[MAXN][MAXK];
static float amp[MAXN][MAXK];
static BQ    bs[MAXN], bd[MAXN];
static float inbuf[128], outbuf[128];
static int   gN = 32, gK = 16;
static unsigned rs = 1u;
static float rnd(void){ rs = rs*1664525u + 1013904223u; return (float)(rs>>8) * (1.0f/16777216.0f); }
static inline float bq(BQ *q, float x){ float y = q->b0*x + q->z1; q->z1 = q->b1*x - q->a1*y + q->z2; q->z2 = q->b2*x - q->a2*y; return y; }
static inline float rd(const float *r, float d){ float p = (float)w - d; int i0; float fr;
  if (p < 0) p += RING; i0 = (int)p; fr = p - (float)i0; return r[i0 & MASK]*(1.0f-fr) + r[(i0+1) & MASK]*fr; }
EXPORT("sk_init") void sk_init(int N, int K){ int i,k; gN=N; gK=K; w=0;
  for(i=0;i<N;i++){ dly[i] = 400.0f + 2400.0f*rnd();
    for(k=0;k<K;k++){ off[i][k] = 1 + k*40 + (int)(40.0f*rnd()); amp[i][k] = (rnd()<0.5f?-1.0f:1.0f)*0.25f; }
    bs[i] = (BQ){0.9f,-0.5f,0.2f,-0.55f,0.22f,0,0}; bd[i] = (BQ){0.1f,-0.05f,0.02f,-0.55f,0.22f,0,0};
    for(k=0;k<RING;k++) ring[i][k]=0; } }
EXPORT("sk_in") float *sk_in(void){ return inbuf; }
EXPORT("sk_out") float *sk_out(void){ return outbuf; }
EXPORT("sk_block") void sk_block(void){ int t,i,k;
  for(t=0;t<128;t++){ float x = inbuf[t], acc = 0.0f;
    for(i=0;i<gN;i++){ float *r = ring[i]; float d = dly[i]; float sp, sc = 0.0f;
      r[w] = x;                              /* early-lane write (exists today) */
      sp = bq(&bs[i], rd(r, d));             /* specular: sqrt(prod(1-s)) shelf */
      for(k=0;k<gK;k++) sc += amp[i][k]*rd(r, d + (float)off[i][k]);
      acc += sp + bq(&bd[i], sc); }          /* scatter shelf after the sparse sum */
    outbuf[t] = acc; w = (w+1) & MASK; } }
