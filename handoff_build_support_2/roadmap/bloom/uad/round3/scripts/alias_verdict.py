import csv, glob, sys
U={(r['unit'],r['f'],r['in_db']):r for r in csv.DictReader(open('/workspace/uad3/alias_uad_tones.csv'))}
rows={}
for fn in sys.argv[1:]:
    for r in csv.DictReader(open(fn)):
        if r['f']=='sweep': continue
        rows[(r['preset'],r['mode'],r['f'],r['L'])]=r
res={}
for (p,m,f,L),r in rows.items():
    u=U.get((r['unit'],f,L))
    if not u: continue
    for meth,k in (('M1','m1_worst_alias_dbfs'),('M2<16k','m2_peak_below16k_dbfs')):
        a=float(r[k]); b=float(u[k]); ok=(a<=b-10) or (a<-90)
        e=res.setdefault((p,m,meth),[0,0,-999,-999]); e[0]+=ok; e[1]+=1; e[3]=max(e[3],a)
        if not ok: e[2]=max(e[2],a-b)
for k in sorted(res): e=res[k]; print('%-10s %-4s %-6s pass %2d/%2d worst %.1f dBFS%s'%(k[0],k[1],k[2],e[0],e[1],e[3],'  worst failing margin %+.1f'%e[2] if e[2]>-999 else ''))
