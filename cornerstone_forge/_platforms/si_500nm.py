"""Si_500nm — Cornerstone SOI 500 nm rib-only passive process.

The Si stack is unusual: a 200 nm slab Si layer is uniform across the
chip, and the 300 nm rib sits on top of it (total Si thickness 500 nm
where wg_lf is drawn, 200 nm everywhere else). Gratings are partial
etches that leave 140 nm of Si.

This stacking doesn't fit the "every Si layer extrudes from z=0"
convention used by the other passive platforms, so we provide an
explicit extrusion list rather than relying on the YAML-driven loader.
"""
from __future__ import annotations

import photonforge as pf
import photonforge.typing as pft

from .._platform_loader import PlatformConfig, build_technology
from . import _media as M


CONFIG = PlatformConfig(
    platform="Si_500nm",
    name="Cornerstone Si_500nm",
    version="0.1.1",
    media={
        "Si":     M.SI,
        "SiO2":   M.SIO2,
        "metal1": M.TIN,
        "metal2": M.AL,
    },
    target_neff={"rib_1550nm": 3.1},
    polarization={"rib_1550nm": "TE"},
)


@pf.parametric_technology
def si500(
    *,
    slab_thickness: pft.PositiveDimension = 0.20,
    rib_thickness: pft.PositiveDimension = 0.30,
    grating_remaining: pft.PositiveDimension = 0.14,
    box_thickness: pft.PositiveDimension = 3.0,
    top_oxide_thickness: pft.PositiveDimension = 2.0,
    metal_si_separation: pft.PositiveDimension = 2.0,
    heater_thickness: pft.PositiveDimension = 0.150,
    pad_thickness: pft.PositiveDimension = 0.220,
    sidewall_angle: pft.Angle = 0.0,
    include_substrate: bool = False,
) -> pf.Technology:
    """Build the Si_500nm Technology with explicit extrusion stack."""
    si_top = slab_thickness + rib_thickness  # 0.5
    z_heater = si_top + metal_si_separation
    z_pad = z_heater + heater_thickness + 0.1

    # Explicit extrusion stack — slab is full-bounds (uniform), rib sits
    # on top of the slab where wg_lf is drawn, grating etches into the
    # rib leaving ``grating_remaining`` of Si.
    extrusions = [
        # Uniform 200 nm Si slab everywhere on chip
        pf.ExtrusionSpec(
            pf.MaskSpec(),
            M.SI,
            (0.0, slab_thickness),
            sidewall_angle,
        ),
        # Rib core (300 nm) on top of slab where wg_lf drawn AND grating not
        pf.ExtrusionSpec(
            pf.MaskSpec((3, 0)) - pf.MaskSpec((6, 0)),
            M.SI,
            (slab_thickness, slab_thickness + rib_thickness),
            sidewall_angle,
        ),
        # Grating etch — replaces rib where (wg_lf AND grating) drawn,
        # leaving grating_remaining of Si below the etch surface
        pf.ExtrusionSpec(
            pf.MaskSpec((3, 0)) * pf.MaskSpec((6, 0)),
            M.SI,
            (slab_thickness, slab_thickness + grating_remaining - 0.06),
            sidewall_angle,
        ),
        # Heater filament
        pf.ExtrusionSpec(
            pf.MaskSpec((39, 0)),
            M.TIN,
            (z_heater, z_heater + heater_thickness),
            0.0,
        ),
        # Contact pads
        pf.ExtrusionSpec(
            pf.MaskSpec((41, 0)),
            M.AL,
            (z_pad, z_pad + pad_thickness),
            0.0,
        ),
    ]
    derived_z = {
        "box_thickness": box_thickness,
        "top_oxide_thickness": top_oxide_thickness,
        "si_top": si_top,
        "z_heater": z_heater,
        "z_pad": z_pad,
    }
    return build_technology(
        CONFIG,
        include_substrate=include_substrate,
        extrusions_override=extrusions,
        derived_z_override=derived_z,
    )
