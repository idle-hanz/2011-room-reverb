import json,requests,threading,time
d=json.load(open('/workspace/audit_1852/data/place_full.json'))['a']
def rend():
    t=time.time()
    r=requests.post('http://127.0.0.1:7860/api/render',files={'file':('in.wav',open('/workspace/audit_1852/data/burst_mono.wav','rb'),'audio/wav')},data={'params_json':json.dumps(d)},timeout=300)
    print('render',r.status_code,round(time.time()-t,1),'s',r.text[:120])
th=threading.Thread(target=rend); th.start(); time.sleep(2)
for path in ['/api/defaults','/']:
    t=time.time(); r=requests.get('http://127.0.0.1:7860'+path,timeout=120); print('GET',path,r.status_code,round(time.time()-t,2),'s')
t=time.time(); r=requests.post('http://127.0.0.1:7860/api/live_params',json=d,timeout=120); print('live_params',r.status_code,round(time.time()-t,2),'s')
th.join()
t=time.time(); r=requests.get('http://127.0.0.1:7860/api/defaults',timeout=120); print('GET idle /api/defaults',round(time.time()-t,3),'s')
