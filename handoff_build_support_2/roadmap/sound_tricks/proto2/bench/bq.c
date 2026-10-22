#include <stdio.h>
#include <time.h>
#include <stdlib.h>
/* 192 lines (2 sources x 3 FDNs x 32) x K biquads, 128-sample blocks, double state (as Play). */
int main(int argc,char**argv){int K=atoi(argv[1]);int N=192,B=128,REP=4000;
double *c=malloc(sizeof(double)*N*K*5),*z1=calloc(N*K,8),*z2=calloc(N*K,8),*x=malloc(8*N);
for(int i=0;i<N*K*5;i++)c[i]=0.1+0.001*(i%7);for(int i=0;i<N;i++)x[i]=1e-3*i;
struct timespec a,b;clock_gettime(CLOCK_MONOTONIC,&a);double acc=0;
for(int r=0;r<REP;r++)for(int t=0;t<B;t++){for(int i=0;i<N;i++){double v=x[i]+1e-9*t;for(int k=0;k<K;k++){int j=i*K+k;double*q=c+5*j;double y=q[0]*v+z1[j];z1[j]=q[1]*v-q[3]*y+z2[j];z2[j]=q[2]*v-q[4]*y;v=y*0.5;}acc+=v;}}
clock_gettime(CLOCK_MONOTONIC,&b);double ms=((b.tv_sec-a.tv_sec)*1e3+(b.tv_nsec-a.tv_nsec)/1e6)/REP;
printf("K=%d  %.4f ms per 128-sample block (native -O2), acc=%g\n",K,ms,acc);return 0;}
