"""Si_sus_bias / Si_sus_not_bias — Cornerstone suspended Si mid-IR (3.8 µm).

Stack: BOX 3 µm SiO2 (undercut by 8 µm after release), Si waveguide
0.45 µm where neither wg_df nor rib_slab is drawn, Si slab 0.15 µm
where rib_slab is drawn. Air cladding above (no top oxide).

The two variants differ only in DRC bias treatment by the foundry —
``bias`` adds a 35 nm bias to features, ``not_bias`` doesn't. The
PhotonForge geometry is identical in both cases.
"""
from __future__ import annotations

import photonforge as pf
import photonforge.typing as pft
import tidy3d as td

from .._platform_loader import PlatformConfig, build_technology
from . import _media as M


_AIR = {
    "optical": td.Medium(permittivity=1.0, name="air"),
    "electrical": td.Medium(permittivity=1.0, name="air"),
}


def _make_config(platform: str) -> PlatformConfig:
    return PlatformConfig(
        platform=platform,
        name=f"Cornerstone {platform}",
        version="0.1.1",
        media={
            "Si":   M.SI,
            "SiO2": M.SIO2,  # BOX is still SiO2; cladding above Si is air
        },
        # Suspended XSes are tagged via the loader's suspended_xs_types
        # so their PortSpec.properties.is_suspended = True downstream.
        target_neff={"sus_si_bias": 2.5, "sus_si_not_bias": 2.5},
        polarization={"sus_si_bias": "TE", "sus_si_not_bias": "TE"},
    )


@pf.parametric_technology
def si_sus_bias(
    *,
    si_thickness: pft.PositiveDimension = 0.45,
    rib_slab_thickness: pft.PositiveDimension = 0.15,
    box_thickness: pft.PositiveDimension = 3.0,
    sidewall_angle: pft.Angle = 0.0,
    include_substrate: bool = False,
) -> pf.Technology:
    return build_technology(_make_config("Si_sus_bias"), include_substrate=include_substrate)


@pf.parametric_technology
def si_sus_not_bias(
    *,
    si_thickness: pft.PositiveDimension = 0.45,
    rib_slab_thickness: pft.PositiveDimension = 0.15,
    box_thickness: pft.PositiveDimension = 3.0,
    sidewall_angle: pft.Angle = 0.0,
    include_substrate: bool = False,
) -> pf.Technology:
    return build_technology(_make_config("Si_sus_not_bias"), include_substrate=include_substrate)
