import json, requests, hashlib, sys
sys.path.insert(0,'scripts')
from engine_sanity import BASE
U='http://127.0.0.1:7860'
def lp(over):
    P=dict(BASE); P.update(over); r=requests.post(U+'/api/live_params',json=P,timeout=120)
    try: j=r.json()
    except Exception: return r.status_code, None
    j.pop('colour',None)
    return r.status_code, j
def h(j): return hashlib.md5(json.dumps(j,sort_keys=True,default=str).encode()).hexdigest()[:10] if j else None
s0,j0=lp({})
print('base',s0,h(j0))
for name,over in [('my_l=0.3, align off',dict(my_l=0.3,my_r=2.5,align_horizontal=False)),('my_c=2.5',dict(my_c=2.5)),('centre_dz=0.3',dict(centre_dz=0.3,align_horizontal=False)),
                  ('source_size_m 0.3 omni',dict(source_size_m=0.3)),('source_size 0.3 talking',dict(source_radiation='talking_head',source_size_m=0.3)),('talking',dict(source_radiation='talking_head')),
                  ('capsule_mm 25 MEAS',dict(capsule_mm=25)),('mic_response 20k MEAS',dict(mic_response_hz=20000)),('lambda 0.5',dict(lambda_ref=0.5)),('seed 5',dict(diffusion_seed=5)),
                  ('colour_impl fir',dict(colour_impl='fir')),('ir_length 500',dict(ir_length_ms=500)),('head_yaw ortf',dict(head_yaw_deg=40)),
                  ('W NaN',dict(W=float('nan'))),('W 0',dict(W=0)),('W -5',dict(W=-5)),('decay 0',dict(decay_s=0)),('decay 1e6',dict(decay_s=1e6)),('hadamard 7',dict(hadamard_n=7)),('W str',dict(W='abc')),('fdn_g 5',dict(fdn_g=5,decay_lock=False)),
                  ('binaural MEAS vs BYPASS',dict(mic_setup='binaural',colour_mode='BYPASS')),('binaural base',dict(mic_setup='binaural')),('binaural side preset U87',dict(mic_setup='binaural',mic_preset_l='NeumannU87AiCardioid',mic_preset_r='NeumannU87AiCardioid')),('mono_c base',dict(mic_setup='mono_c',space=0,yaw_l_deg=0,yaw_r_deg=0)),('mono_c L muted',dict(mic_setup='mono_c',space=0,yaw_l_deg=0,yaw_r_deg=0,mic_gain_l=0)),('mic outside room',dict(mcx=50,mcz=-3,my=-1)),('src==mic',dict(sx=3,sz=1.5,sy=1.5))]:
    try:
        body=json.dumps(dict(BASE,**over),allow_nan=True)
        r=requests.post(U+'/api/live_params',data=body,headers={'Content-Type':'application/json'},timeout=120)
        try: j=r.json(); j.pop('colour',None)
        except Exception: j=None
        extra=''
        if j and not j.get('ok',True): extra=str(j.get('error'))[:120]
        if j and j.get('ok'):
            bad=[k for k,v in j.items() if isinstance(v,float) and (v!=v or abs(v)==float('inf'))]
            extra=f"g={j.get('g')} makeup={j.get('makeup')} decay={j.get('decay_s')} nonfinite={bad}"
        print(f'{name:28} http={r.status_code} hash={h(j)} same_as_base={h(j)==h(j0)} {extra}')
    except Exception as e: print(name,'EXC',e)
