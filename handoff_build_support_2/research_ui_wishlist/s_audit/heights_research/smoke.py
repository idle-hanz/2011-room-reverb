import json, subprocess, sys
PY='/workspace/scratch_er_dropout/venv/bin/python'; SW='/workspace/audit_1852/software'; LIB='/workspace/build_support_2/3_phase_acceptance_tests/harness/lib'
base=json.load(open('/workspace/build_support_2/roadmap/s4_verify_1140/measure/client_body_1140.json')); base.update(direct_wet=1.0,early_wet=1.0,fdn_wet=1.0)
cases={'flat':{}, 'pair_up_0p5':dict(my_l=2.0,my_r=2.0,my_c=1.5), 'tilt_lr_0p6':dict(my_l=1.2,my_r=1.8,my_c=1.5), 'pair_up_1p0':dict(my_l=2.5,my_r=2.5,my_c=1.5)}
out={}
subprocess.run([PY,LIB+'/dump_params.py',SW,json.dumps(base),'/workspace/audit_1852/heights/p_orig.json','48000'],check=True,capture_output=True)
for n,o in cases.items():
    b=dict(base,**o); f=f'/workspace/audit_1852/heights/p_{n}.json'
    r=subprocess.run([PY,'dump_params_h.py',SW,json.dumps(b),f,'48000'],capture_output=True,text=True)
    if r.returncode: print(r.stderr[-800:]); sys.exit(1)
P0=json.load(open('/workspace/audit_1852/heights/p_orig.json'))
def walk(a,b,path,res):
    if isinstance(a,dict):
        for k in a: walk(a[k],b.get(k) if isinstance(b,dict) else None,path+'.'+k,res)
    elif isinstance(a,list) and a and isinstance(a[0],(int,float)):
        if not isinstance(b,list) or len(b)!=len(a): res['shape'].append(path); return
        d=max(abs(x-y) for x,y in zip(a,b)); 
        if d>0: res['diff'][path]=d
    elif isinstance(a,list):
        if not isinstance(b,list) or len(a)!=len(b): res['shape'].append(path); return
        for i,(x,y) in enumerate(zip(a,b)): walk(x,y,f'{path}[{i}]',res)
    elif isinstance(a,(int,float)) and not isinstance(a,bool):
        if a!=b: res['diff'][path]=abs(a-(b or 0))
for n in cases:
    P=json.load(open(f'/workspace/audit_1852/heights/p_{n}.json')); res={'shape':[],'diff':{}}; walk(P0,P,'',res)
    top=sorted(res['diff'].items(),key=lambda kv:-kv[1])[:12]
    print(n,'shape_changes',res['shape'][:5],'n_diff',len(res['diff']))
    for k,v in top: print('   ',k[:70],round(v,5))
