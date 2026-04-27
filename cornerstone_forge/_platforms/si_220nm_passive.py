"""Si_220nm_passive — Cornerstone SOI 220 nm passive process with heaters."""
from __future__ import annotations

import photonforge as pf
import photonforge.typing as pft

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
def si220_passive(
    *,
    si_thickness: pft.PositiveDimension = 0.220,
    rib_slab_thickness: pft.PositiveDimension = 0.100,
    ebl_grating_remaining: pft.PositiveDimension = 0.125,
    duv_grating_remaining: pft.PositiveDimension = 0.150,
    box_thickness: pft.PositiveDimension = 3.0,
    top_oxide_thickness: pft.PositiveDimension = 2.0,
    metal_si_separation: pft.PositiveDimension = 2.0,
    heater_thickness: pft.PositiveDimension = 0.150,
    pad_thickness: pft.PositiveDimension = 0.220,
    sidewall_angle: pft.Angle = 0.0,
    include_substrate: bool = False,
) -> pf.Technology:
    """Cornerstone Si_220nm_passive technology.

    The keyword arguments mirror the foundry's ``process_overview.yaml``
    nominal values so PhotonForge tools (mode solver, FDTD bound
    derivation) can read them via ``technology.parametric_kwargs``.
    Setting them to non-default values does not currently re-tune the
    extrusion stack — that's a v0.2.0 task.
    """
    return build_technology(CONFIG, include_substrate=include_substrate)
