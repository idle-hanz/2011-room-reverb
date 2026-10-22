/* Block-major variant: per line, 128 interpolated reads -> short history (integer, contiguous) ->
 * sparse FIR over the block (vectorisable axpy per pulse) -> biquads. Same maths as scatter_kernel.c
 * except cluster reads are integer offsets from the (already fractionally-read) specular stream. */
#define MAXN 128
#define MAXK 32
#define RING 16384
#define MASK (RING-1)
#define HIST 2048      /* >= max cluster offset (30 ms @48k = 1440) + 128 */
#ifdef __wasm__
#define EXPORT(n) __attribute__((export_name(n)))
#else
#define EXPORT(n)
#endif
typedef struct { float b0,b1,b2,a1,a2,z1,z2; } BQ;
static float ring[MAXN][RING];
static float hist[MAXN][2*HIST];
static int   hp;
static int   w;
static float dly[MAXN];
static int   off[MAXN][MAXK];
static float amp[MAXN][MAXK];
static BQ    bs[MAXN], bd[MAXN];
static float inbuf[128], outbuf[128];
static int   gN = 32, gK = 16;
static unsigned rs = 1u;
static float rnd(void){ rs = rs*1664525u + 1013904223u; return (float)(rs>>8) * (1.0f/16777216.0f); }
EXPORT("sk_init") void sk_init(int N, int K){ int i,k; gN=N; gK=K; w=0;
  for(i=0;i<N;i++){ dly[i] = 400.0f + 2400.0f*rnd();
    for(k=0;k<K;k++){ off[i][k] = 1 + k*40 + (int)(40.0f*rnd()); amp[i][k] = (rnd()<0.5f?-1.0f:1.0f)*0.25f; }
    bs[i] = (BQ){0.9f,-0.5f,0.2f,-0.55f,0.22f,0,0}; bd[i] = (BQ){0.1f,-0.05f,0.02f,-0.55f,0.22f,0,0};
    for(k=0;k<RING;k++) ring[i][k]=0; for(k=0;k<2*HIST;k++) hist[i][k]=0; } hp=0; }
EXPORT("sk_in") float *sk_in(void){ return inbuf; }
EXPORT("sk_out") float *sk_out(void){ return outbuf; }
EXPORT("sk_block") void sk_block(void){ int t,i,k; float sc[128];
  for(t=0;t<128;t++) outbuf[t]=0.0f;
  for(i=0;i<gN;i++){ float *r = ring[i], *h = hist[i]; BQ q = bs[i], p = bd[i];
    for(t=0;t<128;t++){ int ww = (w + t) & MASK; float pp, fr; int i0;
      r[ww] = inbuf[t];
      pp = (float)(w + t) - dly[i]; if (pp < 0) pp += RING; i0 = (int)pp; fr = pp - (float)i0;
      { float v = r[i0 & MASK]*(1.0f-fr) + r[(i0+1) & MASK]*fr; h[hp + t] = v; h[hp + HIST + t] = v; } }
    for(t=0;t<128;t++) sc[t]=0.0f;
    for(k=0;k<gK;k++){ const float a = amp[i][k]; const float *src = h + hp + HIST - off[i][k];
      for(t=0;t<128;t++) sc[t] += a*src[t]; }                     /* contiguous axpy -> SIMD */
    for(t=0;t<128;t++){ float x = h[hp+HIST+t], y, y2;
      y = q.b0*x + q.z1; q.z1 = q.b1*x - q.a1*y + q.z2; q.z2 = q.b2*x - q.a2*y;
      y2 = p.b0*sc[t] + p.z1; p.z1 = p.b1*sc[t] - p.a1*y2 + p.z2; p.z2 = p.b2*sc[t] - p.a2*y2;
      outbuf[t] += y + y2; }
    bs[i] = q; bd[i] = p; }
  w = (w + 128) & MASK; hp = (hp + 128) & (HIST-1); }
