# Air climate presets

Vendored from `air_fitter/presets/` so Play and Render can load a climate when that pack is not next to `software/`. `engine/air_iso.py` reads this folder first and falls back to the pack.

**Honesty:** FITTED_TO_ISO_9613_1 (not measured IRs).

ISO 9613-1:1993 α(f) in dB/m (python-acoustics equations):
saturation vapour pressure → molar h → frO / frN → attenuation_coefficient.

The equations in `air_iso.py` follow python-acoustics `acoustics.standards.iso_9613_1_1993` (BSD-3-Clause, Copyright (c) 2013, Python Acoustics). These JSON files are fitted shelf parameters, not the standard's tables.

**h is a percent.** ISO 9613-1 note 3: the molar concentration of water vapour is `h = rh_pct * p_sat / p`, not a fraction. The 23 Sep air_fitter pack used a fraction, so those shelves were about 13× too weak at 8 kHz and the 8–16 kHz humidity direction was inverted. Refit 2026-10-02. `params` is the analytic log-sigmoid. `rbj` is the realtime slope-1 pair. `index.json` `rbj_knots` fills the humidities between the four climates.

Geometric level stays 1/r (Idle 2026-10-10; the Structure Air Abs graph is still 1/r²). Humidity does not change it. Humidity 0 leaves the shelf off. Above 0 the slider sets relative humidity at this preset's temperature. Just above 0 is about 90 % RH. 0.35 is this preset's RH, unless that RH is drier than the treble-loss peak, in which case 0.35 sits on the peak. The right end is that peak (21.7 % at 20 °C, 19.2 % at 22 °C). The slider does not go drier, so 8–16 kHz loss stays monotonic. Right is drier.
