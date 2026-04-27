"""Ge_on_Si — Cornerstone Germanium-on-Silicon mid-IR platform (3.8 µm).

Stack: 500 µm Si substrate, 1.2 µm Ge slab (uniform), 1.8 µm Ge rib
where wg_lf is drawn. No top oxide — air cladding above the Ge rib.
"""
from __future__ import annotations

import photonforge as pf
import photonforge.typing as pft
import tidy3d as td

from .._platform_loader import PlatformConfig, build_technology
from . import _media as M


# Air cladding (no oxide on this platform)
_AIR = {
    "optical": td.Medium(permittivity=1.0, name="air"),
    "electrical": td.Medium(permittivity=1.0, name="air"),
}


CONFIG = PlatformConfig(
    platform="Ge_on_Si",
    name="Cornerstone Ge_on_Si",
    version="0.1.1",
    media={
        "Si":   M.SI,
        "Ge":   M.GE,
        "SiO2": _AIR,  # background medium — air, not oxide
    },
    target_neff={
        "rib_Ge_3800nm_TE": 3.5,
        "ec_xs":            3.0,
    },
    polarization={"rib_Ge_3800nm_TE": "TE"},
)


@pf.parametric_technology
def ge_on_si(
    *,
    ge_slab_thickness: pft.PositiveDimension = 1.2,
    ge_rib_thickness: pft.PositiveDimension = 1.8,
    box_thickness: pft.PositiveDimension = 0.0,  # no BOX on this platform
    top_oxide_thickness: pft.PositiveDimension = 0.0,
    sidewall_angle: pft.Angle = 0.0,
    include_substrate: bool = False,
) -> pf.Technology:
    """Build the Ge_on_Si Technology with stacked Ge slab + rib."""
    # Ge slab (uniform full bounds) at z=(0, 1.2)
    # Ge rib at z=(1.2, 1.2+1.8) where wg_lf drawn AND wg_df NOT (after the
    # `or not wg_df` strip).
    extrusions = [
        pf.ExtrusionSpec(pf.MaskSpec(), M.GE, (0.0, ge_slab_thickness), sidewall_angle),
        pf.ExtrusionSpec(
            pf.MaskSpec((303, 0)),
            M.GE,
            (ge_slab_thickness, ge_slab_thickness + ge_rib_thickness),
            sidewall_angle,
        ),
    ]
    if include_substrate:
        # Si substrate at z=(-500, 0) — Ge sits directly on Si (no BOX)
        extrusions.insert(
            0,
            pf.ExtrusionSpec(pf.MaskSpec(), M.SI, (-pf.Z_INF, 0.0)),
        )
    derived_z = {
        "box_thickness": 0.0,
        "top_oxide_thickness": 0.0,
        "si_top": ge_slab_thickness + ge_rib_thickness,
    }
    return build_technology(
        CONFIG,
        include_substrate=False,  # we already added it manually
        extrusions_override=extrusions,
        derived_z_override=derived_z,
    )
