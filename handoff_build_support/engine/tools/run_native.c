/* Native runner for live_stereo.c (the Play C kernel), no wasm needed.
 * Build: gcc -O3 -msse2 -I. -DLS_SRC='"path/live_stereo.c"' run_native.c -o run_native -lm
 * Usage: run_native <prefix> <mode> [args]
 *   mode ir    <seconds> <out.f32>          impulse (L=R=1 at t=0), stereo interleaved f32
 *   mode noise <burst_s> <total_s> <out.f32> white noise 0.3 rms-ish burst then silence
 *   mode bench <burst_s> <total_s> <ftz 0|1> timing per 5 s window (ms/128-block)
 *   mode sine  <hz> <seconds> <out.f32>      steady sine (level sanity)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <xmmintrin.h>
#include <pmmintrin.h>
#include LS_SRC
static void *rd(const char *p, long *n){FILE*f=fopen(p,"rb");if(!f){*n=0;return NULL;}fseek(f,0,2);*n=ftell(f);fseek(f,0,0);void*b=malloc(*n+4);if(*n)fread(b,1,*n,f);fclose(f);return b;}
static double now_ms(void){struct timespec a;clock_gettime(CLOCK_MONOTONIC,&a);return a.tv_sec*1e3+a.tv_nsec/1e6;}
int main(int argc,char**argv){
  if(argc<3){fprintf(stderr,"usage\n");return 2;}
  char p[512];long nb,ni,nl,nr;const char*pre=argv[1],*mode=argv[2];
  snprintf(p,512,"%s.blob",pre);float*blob=rd(p,&nb);
  snprintf(p,512,"%s.irs",pre);float*irs=rd(p,&ni);
  snprintf(p,512,"%s.lens",pre);int*lens=rd(p,&nl);
  snprintf(p,512,"%s.route",pre);int*route=rd(p,&nr);
  int sr=48000,bytes=live_bytes(sr);void*mem=aligned_alloc(64,(bytes+63)/64*64);memset(mem,0,bytes);
  LiveStereo*st=live_bind(mem,bytes,sr);if(!st){fprintf(stderr,"bind fail\n");return 1;}
  memcpy(live_blob_ptr(st),blob,nb);live_load_room(st,nb/4);
  if(nl>0){memcpy(live_ir_ptr(st),irs,ni);memcpy(live_len_ptr(st),lens,nl);live_load_irs(st,nl/4);}
  if(nr>=230*4){memcpy(live_route_ptr(st),route,230*4);live_load_route(st);}
  float*il=live_in_l(st),*ir=live_in_r(st),*ol=live_out_l(st),*orr=live_out_r(st);
  const int B=128,bps=375; unsigned s=7;
  if(!strcmp(mode,"bench")){
    double burst=atof(argv[3]),tot=atof(argv[4]);int ftz=atoi(argv[5]);
    if(ftz){_MM_SET_FLUSH_ZERO_MODE(_MM_FLUSH_ZERO_ON);_MM_SET_DENORMALS_ZERO_MODE(_MM_DENORMALS_ZERO_ON);}
    int nblk=(int)(tot*bps),nb_burst=(int)(burst*bps);double acc=0,mx=0;int n=0;
    for(int b=0;b<nblk;b++){int on=b<nb_burst;
      for(int i=0;i<B;i++){s=s*1103515245u+12345u;float v=on?((s/4294967296.0f)-0.5f)*0.6f:0.f;il[i]=v;ir[i]=v;}
      double a=now_ms();live_stereo(st,il,ir,ol,orr,B);double c=now_ms()-a;acc+=c;if(c>mx)mx=c;n++;
      if((b+1)%(5*bps)==0||b==nblk-1){printf("t=%5.1fs %s mean %.4f ms/block max %.3f\n",(b+1)/(double)bps,(b<nb_burst)?"play   ":"silence",acc/n,mx);acc=0;mx=0;n=0;}}
    return 0;}
  const char*out=NULL;int total=0,burstN=0;double hz=0;
  if(!strcmp(mode,"ir")){total=(int)(atof(argv[3])*sr);out=argv[4];}
  else if(!strcmp(mode,"noise")){burstN=(int)(atof(argv[3])*sr);total=(int)(atof(argv[4])*sr);out=argv[5];}
  else if(!strcmp(mode,"sine")){hz=atof(argv[3]);total=(int)(atof(argv[4])*sr);out=argv[5];}
  FILE*fo=fopen(out,"wb");float buf[256];
  for(int t0=0;t0<total;t0+=B){
    for(int i=0;i<B;i++){int t=t0+i;float v=0;
      if(!strcmp(mode,"ir"))v=(t==0)?1.f:0.f;
      else if(!strcmp(mode,"noise")){s=s*1103515245u+12345u;v=(t<burstN)?((s/4294967296.0f)-0.5f)*0.6f:0.f;}
      else v=0.5f*(float)sin(2*M_PI*hz*t/sr);
      il[i]=v;ir[i]=v;}
    live_stereo(st,il,ir,ol,orr,B);
    for(int i=0;i<B;i++){buf[2*i]=ol[i];buf[2*i+1]=orr[i];}
    fwrite(buf,sizeof(float),2*B,fo);}
  fclose(fo);return 0;}
