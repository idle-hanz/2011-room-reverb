/* Box-only prototype: engine-like 32-line FDN (allpass-in-line Dffs, Hadamard, Jot loss,
   one-sample feedback) with optional delay modulation. NOT the engine. */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#define N 32
#define SR 48000.0
#define CAP 8192
static void fwht(double *a){ for(int h=1;h<N;h<<=1) for(int i=0;i<N;i+=2*h) for(int j=i;j<i+h;j++){double x=a[j],y=a[j+h];a[j]=x+y;a[j+h]=x-y;} }
static unsigned long long rs=88172645463325252ULL; static double urand(){ rs^=rs<<13; rs^=rs>>7; rs^=rs<<17; return (rs>>11)*(1.0/9007199254740992.0); }
int main(int argc,char**argv){
  /* args: params.txt T60 seconds out.f32 depth_samples rate_hz kind(0 none,1 sine,2 random) interp(0 lin,1 cubic,2 allpass) frac_lines(0..1) [input.raw] */
  FILE*f=fopen(argv[1],"r"); double d[N],inj[N],gd[N]; for(int i=0;i<N;i++) fscanf(f,"%lf %lf %lf",&d[i],&inj[i],&gd[i]); fclose(f);
  double T60=atof(argv[2]), secs=atof(argv[3]); const char*out=argv[4]; double A=atof(argv[5]), rate=atof(argv[6]); int kind=atoi(argv[7]), interp=atoi(argv[8]); double frac=atof(argv[9]);
  const char* inpath = argc>10? argv[10]:NULL;
  int ns=(int)(secs*SR); float *inbuf=NULL; int nin=0;
  if(inpath){ FILE*fi=fopen(inpath,"rb"); fseek(fi,0,SEEK_END); nin=ftell(fi)/4; fseek(fi,0,SEEK_SET); inbuf=malloc(4*nin); fread(inbuf,4,nin,fi); fclose(fi); if(nin+ (int)(T60*1.5*SR) > ns) ns = nin + (int)(T60*1.5*SR); }
  static double ring[N][CAP]; memset(ring,0,sizeof ring); int w=0;
  double dly[N],k[N],ph[N],fr[N],rw[N],rwv[N],apz[N]; int mod[N];
  for(int i=0;i<N;i++){ dly[i]=d[i]*SR/1000.0; k[i]=pow(10.0,-3.0*dly[i]/(SR*T60)); ph[i]=2*M_PI*urand(); fr[i]=rate*(0.6+0.8*urand()); mod[i]= (urand()<frac); rw[i]=0; rwv[i]=0; apz[i]=0; }
  double tgA[N],tgB[N]; for(int i=0;i<N;i++){tgA[i]=urand()*2-1;tgB[i]=urand()*2-1;rw[i]=-1;}
  double fb[N]; memset(fb,0,sizeof fb); double g=1.0/sqrt((double)N);
  float *o=malloc(sizeof(float)*ns);
  /* random: smoothed noise (2nd-order lowpass at rate) normalised to ~unit rms */
  double rc=exp(-2*M_PI*rate/SR);
  for(int t=0;t<ns;t++){
    double x = inpath ? (t<nin? inbuf[t]:0.0) : (t==0?1.0:0.0);
    double y[N], acc=0;
    for(int i=0;i<N;i++){
      double D=dly[i];
      if(A>0 && mod[i]){
        if(kind==1) D += A*sin(ph[i]+2*M_PI*fr[i]*t/SR);
        else if(kind==2){ double per=SR/fr[i]; long seg=(long)((t+ph[i]/(2*M_PI)*per)/per); double pos=fmod(t+ph[i]/(2*M_PI)*per,per)/per;
          if(seg!=(long)rw[i]){ rw[i]=(double)seg; tgA[i]=tgB[i]; tgB[i]=urand()*2-1; }
          D += A*(tgA[i]+(tgB[i]-tgA[i])*0.5*(1-cos(M_PI*pos))); }
      }
      int di=(int)floor(D); double fx=D-di; double r;
      #define RD(m) ring[i][(w-(m)+CAP*4)%CAP]
      if(interp==0){ r=(1-fx)*RD(di)+fx*RD(di+1); }
      else if(interp==1){ double ym1=RD(di-1),y0=RD(di),y1=RD(di+1),y2=RD(di+2); double c0=y0,c1=0.5*(y1-ym1),c2=ym1-2.5*y0+2*y1-0.5*y2,c3=0.5*(y2-ym1)+1.5*(y0-y1); r=((c3*fx+c2)*fx+c1)*fx+c0; }
      else { if(fx<0.1){di-=1;fx+=1;} double a=(1-fx)/(1+fx); r=a*RD(di)+RD(di+1)-a*apz[i]; apz[i]=r; }
      double delayed=k[i]*r;
      double s=x*inj[i]+fb[i];
      double yy=-gd[i]*s+delayed;
      ring[i][w]=s+gd[i]*yy;
      y[i]=yy; acc+=yy;
    }
    fwht(y); for(int i=0;i<N;i++) fb[i]=g*y[i];
    o[t]=(float)acc;
    w=(w+1)%CAP;
  }
  FILE*fo=fopen(out,"wb"); fwrite(o,4,ns,fo); fclose(fo); return 0;
}
