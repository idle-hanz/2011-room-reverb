"""Physical reference model: specular image-source method (Allen & Berkley 1979) for the same estimated
shoebox, energy domain per octave band, 1/r^2 energy (i.e. 1/r pressure), |R|^2 = 1 - alpha (BRAS fitted
alphas with the ASSUMED layout from scene.py), ISO 9613-1 air attenuation, c = 343.1 m/s, all image orders
up to T_MAX. No scattering, no source/receiver directivity. It separates 'shoebox + specular assumption'
error from '2011 model' error."""
import numpy as np, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene as S, bras_cr2 as B, analysis as A

T_MAX = 1.6
BIN = 0.0005


def ism_energy(ls, mp, bands=A.OCT, t_max=T_MAX, c=B.C_AIR):
    m = S.to_model(ls, mp)
    src = np.array([m["sx"], m["sy"], m["sz"]]); rec = np.array([m["mcx"], m["my"], m["mcz"]])
    dims = np.array([S.W, S.H, S.L])
    surf = S.surfaces(m["flip"])
    # wall order per axis: (low wall, high wall) -> x: A (x=0), C (x=W); y: E floor, F ceiling; z: D (z=0), B (z=L)
    walls = [("A", "C"), ("E", "F"), ("D", "B")]
    rmax = c * t_max
    nb = int(t_max / BIN) + 1
    out = {int(b): np.zeros(nb) for b in bands}
    axes = []
    for ax in range(3):
        M = int(np.ceil(rmax / (2 * dims[ax]))) + 1
        mm = np.arange(-M, M + 1)
        ent = []
        for p in (0, 1):
            pos = (1 - 2 * p) * src[ax] + 2 * mm * dims[ax]
            n_lo = np.abs(mm - p); n_hi = np.abs(mm)
            ent.append((pos - rec[ax], n_lo, n_hi))
        dx = np.concatenate([e[0] for e in ent]); lo = np.concatenate([e[1] for e in ent]); hi = np.concatenate([e[2] for e in ent])
        keep = np.abs(dx) <= rmax
        axes.append((dx[keep], lo[keep], hi[keep]))
    (dx, lx, hx), (dy, ly, hy), (dz, lz, hz) = axes
    for bi, b in enumerate(bands):
        R2 = {k: 1.0 - surf[k]["absorb"][bi] for k in surf}
        lnx = lx * np.log(R2["A"]) + hx * np.log(R2["C"])
        lny = ly * np.log(R2["E"]) + hy * np.log(R2["F"])
        lnz = lz * np.log(R2["D"]) + hz * np.log(R2["B"])
        mair = S.air_m(b)
        for i in range(len(dx)):  # loop over x images, vectorise y,z
            d2 = dx[i] ** 2 + dy[:, None] ** 2 + dz[None, :] ** 2
            d = np.sqrt(d2)
            ok = d <= rmax
            e = np.exp(lnx[i] + lny[:, None] + lnz[None, :] - mair * d) / (4 * np.pi * d2)
            k = (d[ok] / c / BIN).astype(int)
            np.add.at(out[int(b)], k, e[ok])
    return out


def params_from_energy(e, t_direct):
    """EDT/T20/T30/C50/C80 from a band energy histogram (onset = direct bin)."""
    i0 = int(t_direct / BIN)
    e = e[i0:]
    edc = np.cumsum(e[::-1])[::-1]; edc = 10 * np.log10(edc / edc[0] + 1e-300)
    sr_eff = 1.0 / BIN
    n50, n80 = int(0.05 / BIN) + 1, int(0.08 / BIN) + 1
    return dict(EDT=A.decay_time(edc, sr_eff, 0, -10), T20=A.decay_time(edc, sr_eff, -5, -25),
                T30=A.decay_time(edc, sr_eff, -5, -35),
                C50=10 * np.log10(e[:n50].sum() / e[n50:].sum()), C80=10 * np.log10(e[:n80].sum() / e[n80:].sum()),
                D50=e[:n50].sum() / e.sum(), edc=edc)


if __name__ == "__main__":
    import time; t = time.time()
    en = ism_energy(1, 1)
    m = S.to_model(1, 1)
    dd = np.linalg.norm([m["sx"] - m["mcx"], m["sy"] - m["my"], m["sz"] - m["mcz"]])
    for b, e in en.items():
        p = params_from_energy(e, dd / B.C_AIR)
        print(b, {k: round(v, 3) for k, v in p.items() if k != "edc"})
    print("secs", round(time.time() - t, 1))
