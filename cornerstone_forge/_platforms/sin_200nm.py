"""SiN_200nm — Cornerstone visible-band SiN platform (520/638/780 nm)."""
from __future__ import annotations

import photonforge as pf
import photonforge.typing as pft

from .._platform_loader import PlatformConfig, build_technology
from . import _media as M


CONFIG = PlatformConfig(
    platform="SiN_200nm",
    name="Cornerstone SiN_200nm",
    version="0.1.1",
    media={
        "SiN":    M.SIN,
        "SiO2":   M.SIO2,
        "metal1": M.TIN,
        "metal2": M.AL,
    },
    target_neff={
        "strip_520nm": 1.85,  # SiN at visible has higher n_eff
        "strip_638nm": 1.80,
        "strip_780nm": 1.75,
    },
)


@pf.parametric_technology
def sin200(
    *,
    sin_thickness: pft.PositiveDimension = 0.200,
    box_thickness: pft.PositiveDimension = 2.0,  # SiN_200nm uses BOX 2.0 (vs 3.0 for telecom)
    top_oxide_thickness: pft.PositiveDimension = 2.0,
    metal_si_separation: pft.PositiveDimension = 2.0,
    heater_thickness: pft.PositiveDimension = 0.150,
    pad_thickness: pft.PositiveDimension = 0.220,
    sidewall_angle: pft.Angle = 0.0,
    include_substrate: bool = False,
) -> pf.Technology:
    return build_technology(CONFIG, include_substrate=include_substrate)
