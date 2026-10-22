#!/usr/bin/env python3
"""K3 repro: count distinct FDN line delays (Play live_fdn_params and Render fdn_delays_from_taps)
for the default room, and show which symmetry causes the duplicates."""
from common import params, dump, CLIENT_ORTF
from render_pipeline import live_fdn_params
res = {}
cases = {
  'server_defaults': {},
  'client_defaults (ORTF 0.17, hum .35, lock 1.8)': dict(CLIENT_ORTF, humidity=0.35, decay_lock=True, decay_s=1.8),
  'source x off-centre (sx=2.6)': dict(sx=2.6),
  'heights differ (sy=1.2, my=1.5)': dict(sy=1.2),
  'both (sx=2.6, sy=1.2)': dict(sx=2.6, sy=1.2),
  'mic x off-centre (mcx=2.8)': dict(mcx=2.8),
}
for name, over in cases.items():
    p = params(**over, sample_rate=48000)
    out = live_fdn_params(p)
    row = {}
    for ch in ('l', 'c', 'r'):
        d = out['buses'][ch]['delay_ms']
        row[ch] = {'unique': len(set(round(x, 6) for x in d)), 'n': len(d)}
    row['c_delays_ms'] = [round(x, 3) for x in out['buses']['c']['delay_ms']]
    res[name] = row
    print(f"{name:48s} unique L/C/R = {row['l']['unique']}/{row['c']['unique']}/{row['r']['unique']} of 32")
dump(res, 'k3_unique_delays.json')
