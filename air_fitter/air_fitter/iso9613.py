"""ISO 9613-1:1993 atmospheric absorption α(f) in dB/m.

Equations match python-acoustics `acoustics.standards.iso_9613_1_1993`
(saturation vapour pressure, molar h, frO, frN, attenuation_coefficient).

RH is a fraction in [0, 1]. T in Kelvin internally; helpers accept °C.
Pressure defaults to ISA 101.325 kPa.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

import numpy as np

REFERENCE_TEMPERATURE = 293.15  # K
REFERENCE_PRESSURE = 101.325  # kPa
TRIPLE_TEMPERATURE = 273.16  # K


@dataclass(frozen=True)
class Climate:
    """Ambient conditions for ISO 9613-1."""

    temperature_c: float
    relative_humidity_pct: float  # 0..100
    pressure_kpa: float = REFERENCE_PRESSURE

    @property
    def temperature_k(self) -> float:
        return float(self.temperature_c) + 273.15

    @property
    def rh_fraction(self) -> float:
        return float(self.relative_humidity_pct) / 100.0


def saturation_vapour_pressure(
    temperature_k: float,
    reference_pressure: float = REFERENCE_PRESSURE,
    triple_temperature: float = TRIPLE_TEMPERATURE,
) -> float:
    """p_sat [kPa] from ISO 9613-1."""
    c = -6.8346 * (triple_temperature / temperature_k) ** 1.261 + 4.6151
    return reference_pressure * (10.0 ** c)


def molar_concentration_water_vapour(
    rh_fraction: float,
    p_sat: float,
    pressure_kpa: float,
) -> float:
    """Molar concentration of water vapour h, in percent (ISO 9613-1 note 3).

    ``rh_fraction`` is relative humidity as a fraction. h = rh_pct * p_sat / p.
    """
    return 100.0 * float(rh_fraction) * float(p_sat) / float(pressure_kpa)


def frO(pressure_kpa: float, h: float, reference_pressure: float = REFERENCE_PRESSURE) -> float:
    """Oxygen relaxation frequency f_r,O [Hz]."""
    return (pressure_kpa / reference_pressure) * (
        24.0 + 4.04e4 * h * (0.02 + h) / (0.391 + h)
    )


def frN(
    pressure_kpa: float,
    temperature_k: float,
    h: float,
    reference_pressure: float = REFERENCE_PRESSURE,
    reference_temperature: float = REFERENCE_TEMPERATURE,
) -> float:
    """Nitrogen relaxation frequency f_r,N [Hz]."""
    return (pressure_kpa / reference_pressure) * (temperature_k / reference_temperature) ** (-0.5) * (
        9.0
        + 280.0
        * h
        * np.exp(
            -4.170
            * ((temperature_k / reference_temperature) ** (-1.0 / 3.0) - 1.0)
        )
    )


def attenuation_coefficient(
    pressure_kpa: float,
    temperature_k: float,
    fr_n: float,
    fr_o: float,
    frequency: Union[float, np.ndarray],
    reference_pressure: float = REFERENCE_PRESSURE,
    reference_temperature: float = REFERENCE_TEMPERATURE,
) -> np.ndarray:
    """α(f) in dB/m (positive attenuation coefficient)."""
    f = np.asarray(frequency, dtype=float)
    t_ratio = temperature_k / reference_temperature
    classical = (
        1.84e-11
        * (reference_pressure / pressure_kpa)
        * (t_ratio ** 0.5)
    )
    oxygen = (
        0.01275
        * np.exp(-2239.1 / temperature_k)
        * (fr_o + (f ** 2) / fr_o) ** (-1.0)
    )
    nitrogen = (
        0.1068
        * np.exp(-3352.0 / temperature_k)
        * (fr_n + (f ** 2) / fr_n) ** (-1.0)
    )
    alpha = 8.686 * (f ** 2) * (classical + (t_ratio ** (-2.5)) * (oxygen + nitrogen))
    return alpha


def alpha_db_per_m(
    freqs_hz: Union[float, np.ndarray],
    climate: Climate,
) -> np.ndarray:
    """ISO 9613-1 α(f) in dB/m for the given climate (positive)."""
    t_k = climate.temperature_k
    p = climate.pressure_kpa
    rh = climate.rh_fraction
    p_sat = saturation_vapour_pressure(t_k)
    h = molar_concentration_water_vapour(rh, p_sat, p)
    f_o = frO(p, h)
    f_n = frN(p, t_k, h)
    return attenuation_coefficient(p, t_k, f_n, f_o, freqs_hz)


def path_loss_db(
    freqs_hz: Union[float, np.ndarray],
    distance_m: float,
    climate: Climate,
) -> np.ndarray:
    """A_db(f) = −α(f)·d  (attenuation ≤ 0 dB)."""
    return -alpha_db_per_m(freqs_hz, climate) * float(distance_m)
