"""Si_220nm_active — Cornerstone SOI 220 nm active process.

Adds RF/implant layers on top of the 220-passive stack: P/N implants
(7,0)/(8,0)/(9,0)/(11,0), Via (12,0), Electrode (13,0), Detector
implant (23,0). Components include MZI modulators, photodetectors,
plus the same passive components as the 220-passive variant.

This v0.1 release is **layout-only**: charge/optical coupled
simulation for the modulators and photodetectors is not modelled —
implants are declared as LayerSpec entries but don't participate in
the extrusion stack (they're doping metadata, not geometry).
"""
from __future__ import annotations

import photonforge as pf
import photonforge.typing as pft

from .._platform_loader import PlatformConfig, build_technology
from . import _media as M


CONFIG = PlatformConfig(
    platform="Si_220nm_active",
    name="Cornerstone Si_220nm_active",
    version="0.1.1",
    media={
        "Si":     M.SI,
        "SiO2":   M.SIO2,
        "metal1": M.AL,  # Electrode_LF is Al on this platform (not TiN)
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
def si220_active(
    *,
    si_thickness: pft.PositiveDimension = 0.220,
    rib_slab_thickness: pft.PositiveDimension = 0.100,
    grating_remaining: pft.PositiveDimension = 0.150,
    box_thickness: pft.PositiveDimension = 3.0,
    top_oxide_thickness: pft.PositiveDimension = 2.0,
    metal_si_separation: pft.PositiveDimension = 2.0,
    electrode_thickness: pft.PositiveDimension = 1.6,
    sidewall_angle: pft.Angle = 0.0,
    include_substrate: bool = False,
) -> pf.Technology:
    """Cornerstone Si_220nm_active technology (layout-only)."""
    return build_technology(CONFIG, include_substrate=include_substrate)
