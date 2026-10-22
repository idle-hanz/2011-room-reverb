/* Box micro-benchmark: source-radiation per-line filter (gain -> RBJ shelf TDF-II -> 2x one-pole soft LP mix)
   Layout: SoA, lines inner loop (vectorisable across lines), 128-sample blocks, float32, no alloc in process. */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <string.h>
#define BLK 128
#define MAXL 1024
typedef struct { float g[MAXL], b0[MAXL], b1[MAXL], b2[MAXL], a1[MAXL], a2[MAXL], pg[MAXL], pm[MAXL];
                 float z1[MAXL], z2[MAXL], p1[MAXL], p2[MAXL];
                 float db0[MAXL], db1[MAXL], db2[MAXL], da1[MAXL], da2[MAXL], dg[MAXL]; } Bank;
static Bank B;
static float in[MAXL][BLK], out[MAXL][BLK];
static double now(){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec+t.tv_nsec*1e-9; }

/* static coefficients */
static void process(int n){
  for(int s=0;s<BLK;s++){
    for(int i=0;i<n;i++){
      float v=B.g[i]*in[i][s];
      float o=B.b0[i]*v+B.z1[i];
      B.z1[i]=B.b1[i]*v-B.a1[i]*o+B.z2[i];
      B.z2[i]=B.b2[i]*v-B.a2[i]*o;
      B.p1[i]+=B.pg[i]*(o-B.p1[i]);
      B.p2[i]+=B.pg[i]*(B.p1[i]-B.p2[i]);
      out[i][s]=o+B.pm[i]*(B.p2[i]-o);
    }
  }
}
/* lines outer, state in registers (scalar per line) */
static void process_lo(int n){
  for(int i=0;i<n;i++){
    float Z1=B.z1[i],Z2=B.z2[i],P1=B.p1[i],P2=B.p2[i];
    const float G=B.g[i],B0=B.b0[i],B1=B.b1[i],B2=B.b2[i],A1=B.a1[i],A2=B.a2[i],PG=B.pg[i],PM=B.pm[i];
    const float *x=in[i]; float *y=out[i];
    for(int s=0;s<BLK;s++){
      float v=G*x[s]; float o=B0*v+Z1; Z1=B1*v-A1*o+Z2; Z2=B2*v-A2*o;
      P1+=PG*(o-P1); P2+=PG*(P1-P2); y[s]=o+PM*(P2-o);
    }
    B.z1[i]=Z1;B.z2[i]=Z2;B.p1[i]=P1;B.p2[i]=P2;
  }
}
/* 8 lines per SIMD group: sample outer, 8-lane inner on local arrays (auto-vectorised: SSE/AVX, WASM simd128 = 4 lanes) */
#define W8 8
static void process_simd(int n){
  for(int i0=0;i0<n;i0+=W8){
    float Z1[W8],Z2[W8],P1[W8],P2[W8],G[W8],B0[W8],B1[W8],B2[W8],A1[W8],A2[W8],PG[W8],PM[W8];
    for(int j=0;j<W8;j++){int i=i0+j;Z1[j]=B.z1[i];Z2[j]=B.z2[i];P1[j]=B.p1[i];P2[j]=B.p2[i];G[j]=B.g[i];B0[j]=B.b0[i];B1[j]=B.b1[i];B2[j]=B.b2[i];A1[j]=B.a1[i];A2[j]=B.a2[i];PG[j]=B.pg[i];PM[j]=B.pm[i];}
    for(int s=0;s<BLK;s++){
      for(int j=0;j<W8;j++){
        float v=G[j]*in[i0+j][s]; float o=B0[j]*v+Z1[j]; Z1[j]=B1[j]*v-A1[j]*o+Z2[j]; Z2[j]=B2[j]*v-A2[j]*o;
        P1[j]+=PG[j]*(o-P1[j]); P2[j]+=PG[j]*(P1[j]-P2[j]); out[i0+j][s]=o+PM[j]*(P2[j]-o);
      }
    }
    for(int j=0;j<W8;j++){int i=i0+j;B.z1[i]=Z1[j];B.z2[i]=Z2[j];B.p1[i]=P1[j];B.p2[i]=P2[j];}
  }
}
/* per-sample linear coefficient ramp across the block (block-rate interpolation while dragging) */
static void process_ramp(int n){
  for(int s=0;s<BLK;s++){
    for(int i=0;i<n;i++){
      B.g[i]+=B.dg[i]; B.b0[i]+=B.db0[i]; B.b1[i]+=B.db1[i]; B.b2[i]+=B.db2[i]; B.a1[i]+=B.da1[i]; B.a2[i]+=B.da2[i];
      float v=B.g[i]*in[i][s];
      float o=B.b0[i]*v+B.z1[i];
      B.z1[i]=B.b1[i]*v-B.a1[i]*o+B.z2[i];
      B.z2[i]=B.b2[i]*v-B.a2[i]*o;
      B.p1[i]+=B.pg[i]*(o-B.p1[i]);
      B.p2[i]+=B.pg[i]*(B.p1[i]-B.p2[i]);
      out[i][s]=o+B.pm[i]*(B.p2[i]-o);
    }
  }
}
/* coefficient recompute for one (image,capsule): weight law + RBJ shelf + one-pole g */
static void coef(int i, float cx, float cy, float cz){
  const float lo=-4.6f, hi=-11.f, f0=1800.f, S=1.f, p=0.6f, q=0.14f, plo=4.f, dip=0.48f, lphz=555.f, fs=48000.f;
  float u=0.5f*(1.f-cx); float back=1.f-q*powf(u,8.f); float A=fmaxf(0.f,1.f-0.2f*cz);
  float khi=A*powf(u,p)*back, klo=A*((1-dip)*powf(u,plo)*back+dip*4*u*(1-u));
  float Ag=powf(10.f,khi*hi/40.f), w0=2*3.14159265f*f0/fs, cw=cosf(w0), sw=sinf(w0);
  float al=sw/2*sqrtf(fmaxf((Ag+1/Ag)*(1/S-1)+2,1e-9f)), sa=2*sqrtf(Ag)*al;
  float a0=(Ag+1)-(Ag-1)*cw+sa;
  B.b0[i]=Ag*((Ag+1)+(Ag-1)*cw+sa)/a0; B.b1[i]=-2*Ag*((Ag-1)+(Ag+1)*cw)/a0; B.b2[i]=Ag*((Ag+1)+(Ag-1)*cw-sa)/a0;
  B.a1[i]=2*((Ag-1)-(Ag+1)*cw)/a0; B.a2[i]=((Ag+1)-(Ag-1)*cw-sa)/a0;
  B.g[i]=powf(10.f,klo*lo/20.f); float fc=lphz/fmaxf(khi,1e-6f); B.pg[i]=fc<0.45f*fs?1.f-expf(-2*3.14159265f*fc/fs):0.f;
  B.pm[i]=0.99f; (void)cy;
}
int main(){
  srand(1);
  for(int i=0;i<MAXL;i++){ for(int s=0;s<BLK;s++) in[i][s]=(rand()/(float)RAND_MAX-0.5f)*1e-3f; coef(i,cosf(i*0.1f),0.f,sinf(i*0.1f)); }
  int Ns[]={32,64,128}; int reps=20000;
  printf("C box benchmark (per 128-sample block, 3 buses => lines = 3*N)\n");
  printf("N_images,lines,static_us,ramp_us,coef_recompute_us(all lines),x4_multipoint_static_us\n");
  for(int k=0;k<3;k++){
    int n=3*Ns[k]; double t0,t1,t2,t3,t4;
    for(int r=0;r<500;r++) process(n);
    t0=now(); for(int r=0;r<reps;r++) process(n); t1=now();
    for(int r=0;r<reps;r++){ memset(B.dg,0,sizeof B.dg); process_ramp(n);} t2=now();
    for(int r=0;r<reps/10;r++) for(int i=0;i<n;i++) coef(i,cosf(i*0.1f+r),0.f,sinf(i*0.1f)); t3=now();
    double u0=now(); for(int r=0;r<reps;r++) process_lo(n); double u1=now(); for(int r=0;r<reps;r++) process_simd(n); double u2=now();
    printf("#lines_outer_us=%.2f simd8_us=%.2f\n",(u1-u0)/reps*1e6,(u2-u1)/reps*1e6);
    int n4=4*n; if(n4>MAXL) n4=MAXL; for(int r=0;r<reps;r++) process(n4); t4=now();
    double s4 = (4*n>MAXL)? (t4-t3)/reps*1e6*(4.0*n/MAXL) : (t4-t3)/reps*1e6;
    printf("%d,%d,%.2f,%.2f,%.2f,%.2f\n",Ns[k],n,(t1-t0)/reps*1e6,(t2-t1)/reps*1e6,(t3-t2)/(reps/10)*1e6,s4);
  }
  float chk=0; for(int i=0;i<MAXL;i++) chk+=out[i][BLK-1]; fprintf(stderr,"chk %g\n",chk);
  return 0;
}
