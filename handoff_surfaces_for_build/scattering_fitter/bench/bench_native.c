#include <stdio.h>
#include <time.h>
#include "scatter_kernel.c"
int main(void){ int Ns[3]={32,64,128}, Ks[4]={0,8,16,24}, a,b,t,n;
  for(a=0;a<3;a++) for(b=0;b<4;b++){ struct timespec s,e; double ms; sk_init(Ns[a],Ks[b]);
    for(t=0;t<128;t++) inbuf[t]=rnd()-0.5f;
    for(n=0;n<300;n++) sk_block();
    ms=1e9; for(int rep=0;rep<7;rep++){ double m; clock_gettime(CLOCK_MONOTONIC,&s); for(n=0;n<1500;n++) sk_block(); clock_gettime(CLOCK_MONOTONIC,&e);
    m=((e.tv_sec-s.tv_sec)*1e3+(e.tv_nsec-s.tv_nsec)/1e6)/1500.0; if(m<ms) ms=m; }
    printf("native N=%3d K=%2d  %.4f ms/128-block  (%.2f%% of 2.667 ms)  chk=%g\n",Ns[a],Ks[b],ms,ms/2.6667*100,outbuf[5]); }
  return 0; }
