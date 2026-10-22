/* CPU cost of the Play colour stage: same TDF-II double loop as live_stereo.c run_sos,
 * PART = 128 blocks. Reports ns per biquad per sample and the per-block cost for the
 * filter counts measured on the default scene. Box CPU, gcc -O2 (not the user's PC, not wasm). */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#define PART 128
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+1e-9*t.tv_nsec;}
typedef struct { double c[6*5]; double z[6][2]; int k; } F;
static void run(F *f, const double *in, double *out){
  double buf[PART]; int i,s; for(i=0;i<PART;i++) buf[i]=in[i];
  for(s=0;s<f->k;s++){ double b0=f->c[5*s],b1=f->c[5*s+1],b2=f->c[5*s+2],a1=f->c[5*s+3],a2=f->c[5*s+4];
    double z1=f->z[s][0], z2=f->z[s][1];
    for(i=0;i<PART;i++){ double x=buf[i]; double y=b0*x+z1; z1=b1*x-a1*y+z2; z2=b2*x-a2*y; buf[i]=y; }
    f->z[s][0]=z1; f->z[s][1]=z2; }
  for(i=0;i<PART;i++) out[i]=buf[i];
}
int main(int argc,char**argv){
  int nf = argc>1?atoi(argv[1]):40, k = argc>2?atoi(argv[2]):6, blocks = argc>3?atoi(argv[3]):20000;
  F *fs = calloc(nf,sizeof(F)); double in[PART], out[PART]; int i,b,j; double acc=0;
  for(j=0;j<nf;j++){ fs[j].k=k; for(i=0;i<k;i++){ fs[j].c[5*i]=0.9; fs[j].c[5*i+1]=-1.7; fs[j].c[5*i+2]=0.8; fs[j].c[5*i+3]=-1.75; fs[j].c[5*i+4]=0.78; } }
  for(i=0;i<PART;i++) in[i]=(double)rand()/RAND_MAX-0.5;
  double t0=now();
  for(b=0;b<blocks;b++) for(j=0;j<nf;j++){ run(&fs[j],in,out); acc+=out[b%PART]; }
  double dt=now()-t0; double per=dt/((double)blocks*nf*k*PART)*1e9;
  double blk_us = dt/blocks*1e6;
  printf("filters=%d K=%d: %.3f ns/biquad/sample, %.2f us per %d-sample block, %.3f%% of one core at 48 kHz (acc %g)\n",
         nf,k,per,blk_us,PART, 100.0*blk_us/(PART/48000.0*1e6), acc);
  return 0;
}
