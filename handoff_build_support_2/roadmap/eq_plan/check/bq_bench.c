#include <stdio.h>
#include <time.h>
typedef struct { double c[5]; double z[2]; } BQ;
static inline double step(BQ *f, double x){ double y=f->c[0]*x+f->z[0]; f->z[0]=f->c[1]*x-f->c[3]*y+f->z[1]; f->z[1]=f->c[2]*x-f->c[4]*y; return y; }
static double now(){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec+t.tv_nsec*1e-9; }
int main(){
  enum{PART=128, BLOCKS=20000};
  static BQ surf[128][4]; static BQ out[2][5];
  for(int i=0;i<128;i++)for(int k=0;k<4;k++){BQ b={{0.99,-1.9,0.91,-1.9,0.9},{0,0}}; surf[i][k]=b;}
  for(int i=0;i<2;i++)for(int k=0;k<5;k++){BQ b={{0.99,-1.9,0.91,-1.9,0.9},{0,0}}; out[i][k]=b;}
  double acc=0, x=1e-3;
  double t0=now();
  for(int b=0;b<BLOCKS;b++) for(int t=0;t<PART;t++){ for(int i=0;i<128;i++){ double v=x+i*1e-6; for(int k=0;k<4;k++) v=step(&surf[i][k],v); acc+=v;} }
  double t1=now();
  for(int b=0;b<BLOCKS;b++) for(int t=0;t<PART;t++){ for(int c=0;c<2;c++){ double v=x+c*1e-6; for(int k=0;k<5;k++) v=step(&out[c][k],v); acc+=v;} }
  double t2=now();
  printf("SURF-like 128 lanes x K4 per block: %.4f ms\n",(t1-t0)/BLOCKS*1e3);
  printf("Output EQ 2 ch x 5 biquads per block: %.5f ms\n",(t2-t1)/BLOCKS*1e3);
  printf("ratio %.4f  (acc %g)\n",(t2-t1)/(t1-t0),acc);
}
