// Round-3 CPU microbench v2: efficient polyphase halfband (linear double buffer, symmetric, zero taps skipped),
// nclip pre shaper, and full per-channel hybrid chains. ns/sample/channel, gcc -O2, double.
#include <stdio.h>
#include <math.h>
#include <time.h>
#include <string.h>
#define N 4800000
static double xin[N], yout[N];
static double now(){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
// ---- halfband: odd-length L=4K-1, h[c]=0.5, nonzero only at odd offsets from centre ----
#define K 12            // 47 taps -> 24 nonzero side taps (12 symmetric pairs)
static double hs[K];    // side taps h[c-(2k+1)] = h[c+(2k+1)]
static void design(){ for(int k=0;k<K;k++){ int n=2*k+1; double s=sin(M_PI*n/2)/(M_PI*n); int i=(4*K-1)/2+n; double w=0.42-0.5*cos(2*M_PI*i/(4*K-2))+0.08*cos(4*M_PI*i/(4*K-2)); hs[k]=s*w; } }
typedef struct { double bu[4*K]; int pu; double bd[4*K]; int pd; double d0[2*K]; int p0; } HB2;
// upsampler: polyphase; even output = delayed input * (2*0.5), odd output = sum pairs (x2 gain for zero-stuffing)
static inline void up2(HB2*h,double x,double*o0,double*o1){ h->bu[h->pu]=x; h->bu[h->pu+2*K]=x; double*b=&h->bu[h->pu+1];
  double acc=0; for(int k=0;k<K;k++) acc+=hs[k]*(b[K-1-k]+b[K+k]); h->pu=(h->pu+1)%(2*K);
  *o0=h->bu[(h->pu+K-1)%(2*K)]; *o1=2*acc; }
static inline double down2(HB2*h,double e,double od){ // e: even phase sample, od: odd phase sample
  h->bd[h->pd]=od; h->bd[h->pd+2*K]=od; double*b=&h->bd[h->pd+1]; double acc=0; for(int k=0;k<K;k++) acc+=hs[k]*(b[K-1-k]+b[K+k]);
  h->d0[h->p0]=e; double ed=h->d0[(h->p0+K)%(2*K)]; h->p0=(h->p0+1)%(2*K); h->pd=(h->pd+1)%(2*K); return 0.5*ed+acc; }
typedef struct { double a2,a3,dcx,dcy,R; } Poly;
static inline double sh(double v,double a2,double a3){ return v+a2*v*v+a3*v*v*v; }
static inline double nclip(double u,double n,double p1,double p2){ double s=u>=0?(1+p1):(1-p1); double z=u/s; return s*z/pow(1+pow(fabs(z),n),1/n)+p2*u*u; }
static inline double biquad(const double*c,double*z,double x){ double y=c[0]*x+z[0]; z[0]=c[1]*x-c[3]*y+z[1]; z[1]=c[2]*x-c[4]*y; return y; }
int main(){
  design(); for(int i=0;i<N;i++) xin[i]=0.6*sin(2*M_PI*997.0*i/48000)+0.2*sin(2*M_PI*61.0*i/48000);
  double t; HB2 A,B; memset(&A,0,sizeof A); memset(&B,0,sizeof B); Poly P={0.02,-0.03,0,0,0.99935};
  double eq[3][5]={{0.9998,-0.9998,0,-0.9996,0},{1.0001,-1.99,0.99,-1.99,0.99},{1.02,-1.6,0.65,-1.58,0.66}}, z[3][2]={{0}};
  double env=0, gr=0;
  #define RUN(name,...) t=now(); for(int i=0;i<N;i++){ double v=xin[i],y; __VA_ARGS__; yout[i]=y;} t=now()-t; printf("%-44s %7.2f ns/sample/ch  (%.2f us per 128-block, stereo %.2f us)\n",name,t/N*1e9,t/N*1e6*128,2*t/N*1e6*128);
  RUN("poly3 1x + DC block", y=sh(v,P.a2,P.a3); double o=y-P.dcx+P.R*P.dcy; P.dcx=y; P.dcy=o; y=o);
  RUN("2x FIR47 halfband up/down only", double a,b; up2(&A,v,&a,&b); y=down2(&B,a,b));
  RUN("2x FIR47 halfband + poly3", double a,b; up2(&A,v,&a,&b); y=down2(&B,sh(a,P.a2,P.a3),sh(b,P.a2,P.a3)));
  RUN("nclip (pow x2) 1x", y=nclip(v*1.5,8.8,-0.11,-0.007));
  RUN("2x FIR47 + nclip", double a,b; up2(&A,v,&a,&b); y=down2(&B,nclip(a,8.8,-0.11,-0.007),nclip(b,8.8,-0.11,-0.007)));
  RUN("EQ 3 biquads", y=biquad(eq[0],z[0],v); y=biquad(eq[1],z[1],y); y=biquad(eq[2],z[2],y));
  RUN("detector (log/exp, 2 one-poles) + gain", double l=20*log10(fabs(v)+1e-9); env+= (l>env?0.3:0.001)*(l-env); gr+=0.01*(fmax(0,(env+20)*0.75)-gr); y=v*pow(10,-gr/20));
  RUN("full comp hybrid 1x: det+poly3+DC+3EQ", double l=20*log10(fabs(v)+1e-9); env+=(l>env?0.3:0.001)*(l-env); gr+=0.01*(fmax(0,(env+20)*0.75)-gr); double w=v*pow(10,-gr/20); w=sh(w,P.a2,P.a3); double o=w-P.dcx+P.R*P.dcy; P.dcx=w; P.dcy=o; w=biquad(eq[0],z[0],o); w=biquad(eq[1],z[1],w); y=biquad(eq[2],z[2],w));
  RUN("full comp hybrid 2x FIR: det+2x poly3+3EQ", double l=20*log10(fabs(v)+1e-9); env+=(l>env?0.3:0.001)*(l-env); gr+=0.01*(fmax(0,(env+20)*0.75)-gr); double w=v*pow(10,-gr/20),a,b; up2(&A,w,&a,&b); w=down2(&B,sh(a,P.a2,P.a3),sh(b,P.a2,P.a3)); w=biquad(eq[0],z[0],w); w=biquad(eq[1],z[1],w); y=biquad(eq[2],z[2],w));
  { HB2 U[4],D[4]; memset(U,0,sizeof U); memset(D,0,sizeof D);
    // 8x = 3 cascaded halfband stages up, shaper at 8x, 3 down; recursion written out
    t=now(); for(int i=0;i<N/8;i++){ double v=xin[i]; double a[2],b[4],c[8],d[8];
      up2(&U[0],v,&a[0],&a[1]); for(int j=0;j<2;j++) up2(&U[1],a[j],&b[2*j],&b[2*j+1]); for(int j=0;j<4;j++) up2(&U[2],b[j],&c[2*j],&c[2*j+1]);
      for(int j=0;j<8;j++) d[j]=nclip(c[j],8.8,-0.11,-0.007);
      double e[4],f2[2]; for(int j=0;j<4;j++) e[j]=down2(&D[2],d[2*j],d[2*j+1]); for(int j=0;j<2;j++) f2[j]=down2(&D[1],e[2*j],e[2*j+1]); yout[i]=down2(&D[0],f2[0],f2[1]); }
    t=now()-t; printf("%-44s %7.2f ns/sample/ch  (%.2f us per 128-block, stereo %.2f us)\n","8x FIR47 cascade + nclip",t/(N/8)*1e9,t/(N/8)*1e6*128,2*t/(N/8)*1e6*128);
    t=now(); for(int i=0;i<N/8;i++){ double v=xin[i]; double a[2],b[4],c[8],d[8];
      up2(&U[0],v,&a[0],&a[1]); for(int j=0;j<2;j++) up2(&U[1],a[j],&b[2*j],&b[2*j+1]); for(int j=0;j<4;j++) up2(&U[2],b[j],&c[2*j],&c[2*j+1]);
      for(int j=0;j<8;j++) d[j]=c[j];
      double e[4],f2[2]; for(int j=0;j<4;j++) e[j]=down2(&D[2],d[2*j],d[2*j+1]); for(int j=0;j<2;j++) f2[j]=down2(&D[1],e[2*j],e[2*j+1]); yout[i]=down2(&D[0],f2[0],f2[1]); }
    t=now()-t; printf("%-44s %7.2f ns/sample/ch  (%.2f us per 128-block, stereo %.2f us)\n","8x FIR47 cascade filters only",t/(N/8)*1e9,t/(N/8)*1e6*128,2*t/(N/8)*1e6*128); }
  double s=0; for(int i=0;i<N;i+=97) s+=yout[i]; printf("chk %g\n",s);
  // halfband quality
  double H0=0.5,Hs; for(double f=0.0;f<=0.5;f+=0.01){ double r=H0; for(int k=0;k<K;k++) r+=2*hs[k]*cos(2*M_PI*f*(2*k+1)); if(fabs(f-0.40)<1e-9||fabs(f-0.45)<1e-9||fabs(f-0.20)<1e-9||fabs(f-0.60)<1e-9) printf("HB |H| at %.2f fs_os: %.2f dB\n",f,20*log10(fabs(2*r)+1e-20)); }
  printf("latency 2x FIR47 up+down: %d samples at 1x (approx)\n", (4*K-1)/2 /1 );
}
