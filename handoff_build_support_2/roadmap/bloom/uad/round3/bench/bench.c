#include <stdio.h>
#include <math.h>
#include <time.h>
#include <string.h>
#define N 4800000
static double xin[N], yout[N];
static double now(){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
/* halfband FIR, 2x: taps h (odd length L), only even-offset taps non-zero + centre 0.5 */
#define HB 47
static double hb[HB];
static void design_hb(){ int c=HB/2; for(int i=0;i<HB;i++){int n=i-c; double s=(n==0)?0.5:sin(M_PI*n/2)/(M_PI*n); double w=0.42-0.5*cos(2*M_PI*i/(HB-1))+0.08*cos(4*M_PI*i/(HB-1)); hb[i]=s*w;} }
typedef struct { double z1,a2,a3,dcx,dcy,R; } Poly;
static inline double poly3(Poly*p,double v){ double y=v+p->a2*v*v+p->a3*v*v*v; double o=y-p->dcx+p->R*p->dcy; p->dcx=y; p->dcy=o; return o;}
static inline double F1(double v,double a2,double a3){return 0.5*v*v+a2*v*v*v/3+a3*v*v*v*v/4;}
typedef struct { double xp,Fp,a2,a3,dcx,dcy,R; } Adaa;
static inline double poly3_adaa(Adaa*p,double v){ double F=F1(v,p->a2,p->a3); double d=v-p->xp,y;
  if(fabs(d)>1e-9) y=(F-p->Fp)/d; else { double m=0.5*(v+p->xp); y=m+p->a2*m*m+p->a3*m*m*m; }
  p->xp=v; p->Fp=F; double o=y-p->dcx+p->R*p->dcy; p->dcx=y; p->dcy=o; return o;}
static inline double btanh(double v,double b,double tb,double is2){ return (tanh(v+b)-tb)*is2; }
/* 2x oversampled shaper with polyphase halfband: up (zero-stuff + HB), shape, down (HB + decimate) */
typedef struct { double up[HB], dn[HB]; int ui, di; Poly s; } OS2;
static inline double fir(double*buf,int idx){ double acc=0; for(int k=0;k<HB;k++){ acc+=hb[k]*buf[(idx+k)%HB]; } return acc; }
static inline double os2_poly(OS2*o,double v){
  double out=0;
  for(int ph=0;ph<2;ph++){
    o->ui=(o->ui+HB-1)%HB; o->up[o->ui]= ph==0? 2*v:0; double u=fir(o->up,o->ui);
    double s=poly3(&o->s,u);
    o->di=(o->di+HB-1)%HB; o->dn[o->di]=s; if(ph==1) out=fir(o->dn,o->di);
  }
  return out;}
/* efficient polyphase version: only nonzero taps (HB has ~ HB/4+1 nonzero per phase) */
static int nzi[HB]; static double nzh[HB]; static int nnz;
static void prep_nz(){ nnz=0; for(int i=0;i<HB;i++) if(fabs(hb[i])>1e-15){nzi[nnz]=i;nzh[nnz]=hb[i];nnz++;} }
static inline double firnz(double*buf,int idx){ double acc=0; for(int k=0;k<nnz;k++) acc+=nzh[k]*buf[(idx+nzi[k])%HB]; return acc; }
static inline double os2_poly_nz(OS2*o,double v){
  double out=0;
  for(int ph=0;ph<2;ph++){
    o->ui=(o->ui+HB-1)%HB; o->up[o->ui]= ph==0? 2*v:0; double u=firnz(o->up,o->ui);
    double s=poly3(&o->s,u);
    o->di=(o->di+HB-1)%HB; o->dn[o->di]=s; if(ph==1) out=firnz(o->dn,o->di);
  }
  return out;}
/* IIR 2x: 2-path allpass polyphase halfband (Valenzuela/Constantinides), 3 sections per path */
typedef struct { double a[3],b[3]; double sa[3][2], sb[3][2]; } AP;
static const double CA[3]={0.0798664262,0.5453236337,0.8975696686}, CB[3]={0.2838273830,0.7612089932,0.9707342813};
static inline double apchain(const double*c,double (*s)[2],double x){ for(int i=0;i<3;i++){ double y=c[i]*(x-s[i][1])+s[i][0]; s[i][0]=x; s[i][1]=y; x=y;} return x; }
typedef struct { double su[3][2], sv[3][2], du[3][2], dv[3][2]; double dprev; Poly s; } OSI;
static inline double osi_poly(OSI*o,double v){
  double e0=apchain(CA,o->su,v), e1=apchain(CB,o->sv,v);   /* two output phases */
  double s0=poly3(&o->s,e0), s1=poly3(&o->s,e1);
  double d=0.5*(apchain(CA,o->du,s1)+apchain(CB,o->dv,o->dprev)); o->dprev=s0; return d; }
static inline double biquad(double*c,double*z,double x){ double y=c[0]*x+z[0]; z[0]=c[1]*x-c[3]*y+z[1]; z[1]=c[2]*x-c[4]*y; return y; }
int main(){
  design_hb(); prep_nz();
  for(int i=0;i<N;i++) xin[i]=0.3*sin(i*0.37)+0.1*sin(i*0.011);
  double t; Poly P={0,-0.01,-0.004,0,0,0.9993}; Adaa A={0,0,-0.01,-0.004,0,0,0.9993}; OS2 O; memset(&O,0,sizeof O); O.s=P; OSI I; memset(&I,0,sizeof I); I.s=P;
  double bq[5]={0.99,-1.98,0.99,-1.979,0.98}, z[2]={0,0}, z2[2]={0,0};
  #define RUN(name,expr) t=now(); for(int i=0;i<N;i++){ double v=xin[i]; yout[i]=(expr);} t=now()-t; printf("%-34s %7.2f ns/sample  (%.1f us per 128-sample block)\n",name,t/N*1e9,t/N*1e6*128);
  RUN("copy (baseline)", v)
  RUN("biquad x1", biquad(bq,z,v))
  RUN("poly3 + DC blocker 1x", poly3(&P,v))
  RUN("poly3 + DC 1x + ADAA1", poly3_adaa(&A,v))
  RUN("biased tanh 1x (libm tanh)", btanh(v,0.26,tanh(0.26),1.0/(1-0.065)))
  RUN("poly3 2x FIR halfband 47 (naive)", os2_poly(&O,v))
  RUN("poly3 2x FIR halfband 47 (nz taps)", os2_poly_nz(&O,v))
  RUN("poly3 2x IIR allpass halfband", osi_poly(&I,v))
  RUN("detector log10+pow10 per sample", pow(10.0,-0.05*fmax(0,20*log10(fabs(v)+1e-12)+20)))
  double s=0; for(int i=0;i<N;i+=97) s+=yout[i]; printf("chk %g nz=%d\n",s,nnz);
}
