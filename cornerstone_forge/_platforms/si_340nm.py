"""Si_340nm — Cornerstone SOI 340 nm passive process with heaters.

Stack: 340 nm Si waveguide / 200 nm rib slab (different from 220nm
where slab is 100 nm) / 200 nm DUV grating shallow etch / TOX 2 µm /
TiN heater / Al pad. Adds an Isolation_DF (46,0) layer that defines
heater isolation trenches in the BOX — ignored at the layout level.
"""
from __future__ import annotations

import photonforge as pf

from .._platform_loader import PlatformConfig, build_technology
from . import _media as M


CONFIG = PlatformConfig(
    platform="Si_340nm",
    name="Cornerstone Si_340nm",
    version="0.1.1",
    media={
        "Si":     M.SI,
        "SiO2":   M.SIO2,
        "metal1": M.TIN,
        "metal2": M.AL,
    },
    target_neff={
        "strip_1310nm":  3.0,
        "strip_1550nm":  2.7,
        "rib_1550nm_TE": 3.0,  # thicker Si raises n_eff
    },
    polarization={
        "rib_1550nm_TE": "TE",
    },
)


@pf.parametric_technology
def si340(*, include_substrate: bool = False) -> pf.Technology:
    return build_technology(CONFIG, include_substrate=include_substrate)
