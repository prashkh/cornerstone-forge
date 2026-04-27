"""Si_220nm_passive — Cornerstone SOI 220 nm passive process with heaters."""
from __future__ import annotations

import photonforge as pf

from .._platform_loader import PlatformConfig, build_technology
from . import _media as M


CONFIG = PlatformConfig(
    platform="Si_220nm_passive",
    name="Cornerstone Si_220nm_passive",
    version="0.1.0",
    media={
        "Si":     M.SI,
        "SiO2":   M.SIO2,
        "metal1": M.TIN,
        "metal2": M.AL,
    },
    target_neff={
        "strip_1310nm":  2.8,
        "strip_1550nm":  2.5,
        "rib_1310nm_TE": 3.0,
        "rib_1550nm_TE": 2.7,
    },
    polarization={
        "rib_1310nm_TE": "TE",
        "rib_1550nm_TE": "TE",
    },
)


@pf.parametric_technology
def si220_passive(*, include_substrate: bool = False) -> pf.Technology:
    """Build the Si_220nm_passive Technology."""
    return build_technology(CONFIG, include_substrate=include_substrate)
