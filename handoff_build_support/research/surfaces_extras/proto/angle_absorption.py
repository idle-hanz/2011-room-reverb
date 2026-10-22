#!/usr/bin/env python3
"""Prototype (research only): angle-dependent absorption of a porous layer on rigid backing, with
and without an air gap. Miki (1990) impedance model, locally vs extended reaction, Paris random
incidence integral. Also plasterboard / plywood panel mass-air resonance, and incidence-angle stats
of low-order image sources in the reference 6 x 3 x 8 m room.
MODEL OUTPUTS, NOT MEASUREMENTS. Material parameters (sigma, thickness) are typical values, ASSUMED.
"""
import json, math
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1]
rho, c = 1.204, 343.0; Z0 = rho * c

def miki(f, sigma):
    """Miki 1990 (e^{+jwt} convention): characteristic impedance and wavenumber."""
    X = f / sigma
    Zc = Z0 * (1 + 0.070 * X ** -0.632 - 1j * 0.107 * X ** -0.632)
    k = (2 * np.pi * f / c) * (1 + 0.109 * X ** -0.618 - 1j * 0.160 * X ** -0.618)
    return Zc, k

def alpha(f, sigma, d, gap, theta_deg, reaction='local'):
    th = np.radians(theta_deg); Zc, k = miki(f, sigma); k0 = 2 * np.pi * f / c
    s2 = np.sin(th) ** 2
    if reaction == 'local':
        kz, kz0 = k, k0 * np.ones_like(f)
    else:  # extended reaction: tangential wavenumber conserved in every layer
        kz = np.sqrt(k ** 2 - k0 ** 2 * s2 + 0j); kz0 = k0 * np.sqrt(1 - s2) + 0j
    Zl = Zc * k / kz                       # layer normal impedance factor
    Zg = Z0 * k0 / kz0 if reaction != 'local' else Z0 * np.ones_like(f)
    if gap > 0:
        Zb = -1j * Zg / np.tan(kz0 * gap)     # air gap on rigid wall
        Zs = Zl * (-1j * Zb / np.tan(kz * d) + Zl) / (Zb - 1j * Zl / np.tan(kz * d))
    else:
        Zs = -1j * Zl / np.tan(kz * d)
    R = (Zs * np.cos(th) - Z0) / (Zs * np.cos(th) + Z0)
    return 1 - np.abs(R) ** 2, R

def paris(f, sigma, d, gap, reaction='local', thmax=90.0, n=180):
    ths = np.linspace(0, thmax, n + 1)[:-1] + thmax / n / 2
    A = np.array([alpha(f, sigma, d, gap, t, reaction)[0] for t in ths])
    w = np.sin(2 * np.radians(ths))
    return (A * w[:, None]).sum(0) / w.sum()

f = np.geomspace(63, 8000, 200); oct_f = np.array([125, 250, 500, 1000, 2000, 4000, 8000.])
SIG = 15000.0        # typical rigid mineral wool / fibreglass panel flow resistivity, Pa s/m^2 (ASSUMED)
res = {'model': 'Miki 1990, sigma=15 kPa s/m^2 (ASSUMED typical), rho=1.204, c=343', 'cases': {}}
fig, ax = plt.subplots(2, 2, figsize=(12, 8))
for j, (d, gap, lab) in enumerate([(0.05, 0.0, '50 mm on rigid'), (0.05, 0.05, '50 mm + 50 mm air gap')]):
    a = ax[0, j]
    for th, ls in ((0, '-'), (45, '--'), (75, ':')):
        a.semilogx(f, alpha(f, SIG, d, gap, th, 'local')[0], 'C0' + ls, label=f'local {th} deg')
        a.semilogx(f, alpha(f, SIG, d, gap, th, 'ext')[0], 'C1' + ls, label=f'extended {th} deg')
    ar = paris(f, SIG, d, gap, 'local'); ae = paris(f, SIG, d, gap, 'ext')
    a.semilogx(f, ar, 'k', lw=2, label='Paris random-inc (local)')
    a.semilogx(f, ae, 'k--', lw=1.5, label='Paris random-inc (ext)')
    if gap == 0:
        tb = [0.28, 0.7, 0.88, 0.92, 0.94, 0.92, 0.95]
        a.semilogx(oct_f, tb, 'rs', label='preset absorber_panel_2in (textbook)')
    a.set_title(f'porous {lab}: alpha(f, theta)'); a.set_ylim(0, 1.05); a.grid(alpha=.3, which='both'); a.legend(fontsize=7)
    res['cases'][lab] = {
        'octave_hz': oct_f.tolist(),
        'alpha_0deg_local': np.round(alpha(oct_f, SIG, d, gap, 0, 'local')[0], 3).tolist(),
        'alpha_45deg_local': np.round(alpha(oct_f, SIG, d, gap, 45, 'local')[0], 3).tolist(),
        'alpha_75deg_local': np.round(alpha(oct_f, SIG, d, gap, 75, 'local')[0], 3).tolist(),
        'alpha_75deg_ext': np.round(alpha(oct_f, SIG, d, gap, 75, 'ext')[0], 3).tolist(),
        'alpha_paris_local': np.round(paris(oct_f, SIG, d, gap, 'local'), 3).tolist(),
        'alpha_paris_ext': np.round(paris(oct_f, SIG, d, gap, 'ext'), 3).tolist(),
    }
# |R| in dB vs angle
a = ax[1, 0]; ths = np.arange(0, 89.5, 1.0)
for fc, col in ((125, 'C3'), (250, 'C0'), (500, 'C1'), (1000, 'C2'), (4000, 'C4')):
    Rl = np.array([abs(alpha(np.array([fc]), SIG, 0.05, 0.0, t, 'local')[1][0]) for t in ths])
    ar = paris(np.array([fc * 1.0]), SIG, 0.05, 0.0, 'local')[0]
    a.plot(ths, 20 * np.log10(Rl), col, label=f'{fc} Hz (random-inc |R| {10*np.log10(1-ar):.1f} dB)')
    a.axhline(10 * np.log10(1 - ar), color=col, ls=':', lw=.8)
a.set_xlabel('incidence angle (deg)'); a.set_ylabel('|R| dB'); a.set_title('50 mm porous on rigid, local: per-bounce |R| vs angle\n(dotted = what a random-incidence card applies at every angle)')
a.grid(alpha=.3); a.legend(fontsize=7); a.set_ylim(-25, 0)
# panel resonances
a = ax[1, 1]
panels = [('12.5 mm plasterboard (~9 kg/m2) on 75 mm studs', 9.0, 0.075), ('2x12.5 mm plasterboard (~18 kg/m2), 75 mm', 18.0, 0.075),
          ('6 mm plywood (~3.5 kg/m2), 50 mm gap', 3.5, 0.05), ('18 mm plywood/MDF (~11 kg/m2), 25 mm battens', 11.0, 0.025)]
rows = []
for lab, m, dd in panels:
    f0 = 60.0 / math.sqrt(m * dd)           # common mass-air-mass rule, empty cavity (normal incidence)
    f0p = 50.0 / math.sqrt(m * dd)          # with porous fill in the cavity (rule of thumb)
    rows.append({'panel': lab, 'm_kg_m2': m, 'cavity_m': dd, 'f0_empty_hz': round(f0, 1), 'f0_filled_hz': round(f0p, 1)})
    a.barh(lab, f0, color='C0', alpha=.6); a.plot([f0p], [lab], 'ko')
a.set_xscale('log'); a.set_xlabel('Hz'); a.set_title('panel mass-air resonance f0 = 60/sqrt(m d) (bar), 50/sqrt(m d) with fill (dot)')
a.grid(alpha=.3, which='both'); res['panels'] = rows
fig.tight_layout(); fig.savefig(OUT / 'plots' / 'angle_absorption_and_panels.png', dpi=90)

# incidence angles of image sources, 6x3x8 room, source/mic like the rebuild default-ish (ASSUMED positions)
W, H, L = 6.0, 3.0, 8.0; S = np.array([3.0, 1.5, 6.5]); M = np.array([3.0, 1.5, 1.5])
angs = {1: [], 2: [], 3: []}
for nx in range(-3, 4):
    for ny in range(-3, 4):
        for nz in range(-3, 4):
            o = abs(nx) + abs(ny) + abs(nz)
            if o == 0 or o > 3: continue
            def img(n, s, Lx):
                return n * Lx + (s if n % 2 == 0 else Lx - s)
            I = np.array([img(nx, S[0], W), img(ny, S[1], H), img(nz, S[2], L)])
            v = I - M; r = np.linalg.norm(v)
            for ax_i, n in enumerate((nx, ny, nz)):     # every wall hit along this axis has the same angle
                if n != 0:
                    angs[o] += [math.degrees(math.acos(abs(v[ax_i]) / r))] * abs(n)
res['image_hit_angles_deg'] = {str(o): {'n_hits': len(a_), 'median': round(float(np.median(a_)), 1),
                                        'frac_over_60': round(float(np.mean(np.array(a_) > 60)), 2),
                                        'frac_over_75': round(float(np.mean(np.array(a_) > 75)), 2)} for o, a_ in angs.items()}
json.dump(res, open(OUT / 'proto' / 'angle_absorption_results.json', 'w'), indent=1)
print(json.dumps(res, indent=1))
