/* After burst+silence, count subnormal values in every live_stereo state group. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include LS_SRC
static void *rd(const char *p,long*n){FILE*f=fopen(p,"rb");if(!f){*n=0;return 0;}fseek(f,0,2);*n=ftell(f);fseek(f,0,0);void*b=malloc(*n+4);if(*n)fread(b,1,*n,f);fclose(f);return b;}
#define SUBD(x) (fpclassify(x)==FP_SUBNORMAL)
int main(int argc,char**argv){char p[512];long nb,ni,nl,nr;const char*pre=argv[1];double sil=atof(argv[2]);
 snprintf(p,512,"%s.blob",pre);float*blob=rd(p,&nb);snprintf(p,512,"%s.irs",pre);float*irs=rd(p,&ni);
 snprintf(p,512,"%s.lens",pre);int*lens=rd(p,&nl);snprintf(p,512,"%s.route",pre);int*route=rd(p,&nr);
 int sr=48000,bytes=live_bytes(sr);void*mem=calloc(1,bytes+64);LiveStereo*st=live_bind(mem,bytes,sr);
 memcpy(live_blob_ptr(st),blob,nb);live_load_room(st,nb/4);
 if(nl>0){memcpy(live_ir_ptr(st),irs,ni);memcpy(live_len_ptr(st),lens,nl);live_load_irs(st,nl/4);}
 if(nr>=920){memcpy(live_route_ptr(st),route,920);live_load_route(st);}
 float*il=live_in_l(st),*ir=live_in_r(st),*ol=live_out_l(st),*orr=live_out_r(st);unsigned s=7;
 int tot=(int)((2+sil)*375);
 for(int b=0;b<tot;b++){for(int i=0;i<128;i++){s=s*1103515245u+12345u;float v=b<750?((s/4294967296.0f)-0.5f)*0.6f:0;il[i]=v;ir[i]=v;}live_stereo(st,il,ir,ol,orr,128);}
 long air=0,shelf=0,peak=0,fb=0,ring=0,ringz=0,ringtot=0,fdl=0,fdltot=0,prev=0,ytmp=0;
 for(int b=0;b<3;b++){Bus*bu=&st->bus[b];for(int i=0;i<N;i++){Line*l=&bu->line[i];
   air+=SUBD(l->airZ)+SUBD(l->airZe)+SUBD(l->airZb)+SUBD(l->airZf);
   shelf+=SUBD(l->sz1)+SUBD(l->sz2)+SUBD(l->sz1e)+SUBD(l->sz2e)+SUBD(l->sz1b)+SUBD(l->sz2b)+SUBD(l->sz1f)+SUBD(l->sz2f);
   peak+=SUBD(l->pz1)+SUBD(l->pz2)+SUBD(l->pz1b)+SUBD(l->pz2b);fb+=SUBD(bu->fb[i])+SUBD(bu->fbB[i]);
   float*r=st->ring[b][i];for(int t=0;t<st->cap*LANES;t++){ringtot++;if(fpclassify(r[t])==FP_SUBNORMAL)ring++;else if(r[t]==0)ringz++;}}}
 for(int k=0;k<MAX_FILT*MAX_PART*FFTN;k++){if(st->filt[k/(MAX_PART*FFTN)].used){fdltot+=2;fdl+=(fpclassify(st->fdlRe[k])==FP_SUBNORMAL)+(fpclassify(st->fdlIm[k])==FP_SUBNORMAL);}}
 for(int f=0;f<MAX_FILT;f++)for(int t=0;t<PART;t++)prev+=fpclassify(st->filt[f].prev[t])==FP_SUBNORMAL;
 float mx=0;for(int i=0;i<128;i++)if(fabsf(ol[i])>mx)mx=fabsf(ol[i]);
 printf("after %.0fs silence: subnormal air1pole=%ld/384 shelf=%ld/768 peaking=%ld/384 fb=%ld/192 ring_f32=%ld/%ld (zeros %ld) fdl_f32=%ld/%ld fir_prev=%ld | out peak %.3e\n",sil,air,shelf,peak,fb,ring,ringtot,ringz,fdl,fdltot,prev,mx);
 return 0;}
