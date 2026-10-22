import csv, sys, numpy as np
R = list(csv.DictReader(open(sys.argv[1])))
for p in ['natural', 'room_crush', 'nuke', 'swell', 'glue']:
    rr = [r for r in R if r['preset'] == p]
    d = [(float(r['null_proto_EQ']) - float(r['null_current_uadFR']), r['prog']) for r in rr]
    dc = [float(r['null_proto_uadFR']) - float(r['null_protodyn_uadFR']) for r in rr]
    dd = [(float(r['null_protodyn_uadFR']) - float(r['null_current_uadFR']), r['prog']) for r in rr]
    worse = [f'{g}:{x:+.1f}' for x, g in d if x > 0]
    print(f"{p:10s} protoEQ vs current+UADFR: median {np.median([x for x,_ in d]):+.2f}, worst {max(d)[0]:+.2f} ({max(d)[1]}), rows worse {len(worse)}/{len(d)} {' '.join(worse)}")
    print(f"{'':10s} colour on-off (same dyn, UAD FR): median {np.median(dc):+.3f}, range {min(dc):+.3f}..{max(dc):+.3f} | dyn only vs current (UAD FR): median {np.median([x for x,_ in dd]):+.2f} worst {max(dd)[0]:+.2f}")
    if p == 'glue': print(f"{'':10s} glue proto+EQ range {min(float(r['null_proto_EQ']) for r in rr):.1f}..{max(float(r['null_proto_EQ']) for r in rr):.1f} dB")
