"""Technology factories for the Cornerstone PDK.

Currently implemented platforms:
    * Si_220nm_passive — SOI 220 nm process with heaters

The factories read the vendored YAMLs in ``cornerstone_forge/library/<platform>/``
to produce a ``photonforge.Technology``. The mapping from foundry layers /
cross-sections / stack to PhotonForge ``LayerSpec`` / ``ExtrusionSpec`` /
``PortSpec`` is hand-tuned per platform; the YAML provides ground-truth
numbers (thicknesses, layer numbers, DRC) but PhotonForge needs additional
choices (z placement of metals in the cladding, materials, port-spec port
widths) that aren't in the vendored data.
"""

from __future__ import annotations

import tidy3d as td
import photonforge as pf
import photonforge.typing as pft

from . import _yaml_loader as _yl


# ---------- shared media -------------------------------------------------- #

_SI = {
    "optical": td.material_library["cSi"]["Li1993_293K"],
    "electrical": td.Medium(permittivity=11.7, name="Si"),
}
_SIO2 = {
    "optical": td.material_library["SiO2"]["Palik_Lossless"],
    "electrical": td.Medium(permittivity=3.9, name="SiO2"),
}
# TiN is not in tidy3d.material_library; substitute Ti as a layout-only stand-in
# for the heater filament. The Cornerstone process lists TiN at ~0.15 um for
# thermo-optic phase shifters; refining this medium is a v0.2.0 task.
_TIN = {
    "optical": td.material_library["Ti"]["Werner2009"],
    "electrical": td.LossyMetalMedium(
        conductivity=2.5,
        frequency_range=[0.1e9, 200e9],
        fit_param=td.SurfaceImpedanceFitterParam(max_num_poles=16),
    ),
}
_AL = {
    "optical": td.material_library["Al"]["Rakic1995"],
    "electrical": td.LossyMetalMedium(
        conductivity=37.7,
        frequency_range=[0.1e9, 200e9],
        fit_param=td.SurfaceImpedanceFitterParam(max_num_poles=16),
    ),
}


# ---------- Si_220nm_passive --------------------------------------------- #

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

    Stack (z=0 at the top of the BOX):
        BOX (SiO2)               z = -box_thickness  ..  0
        Waveguide Si             z =  0  ..  si_thickness         where (3,0)
        Rib slab                 z =  0  ..  rib_slab_thickness   where (5,0)
        EBL grating Si           z =  0  ..  ebl_grating_remaining (where (3,0)*(60,0))
        DUV grating Si           z =  0  ..  duv_grating_remaining (where (3,0)*(6,0))
        Top oxide (SiO2)         z =  si_thickness  ..  si_thickness + top_oxide_thickness
        Heater filament (TiN)    z = z_heater       ..  z_heater + heater_thickness
        Contact pads (Al)        z = z_pad          ..  z_pad + pad_thickness

    Heater placement above the Si surface is parametrized via
    ``metal_si_separation``. The default (2.0 um) places the TiN filament
    at the top of the TOX cladding — Cornerstone's process diagram puts the
    metal stack on top of TOX, with the filament forming the heating element
    and the Al pads providing electrical contact.
    """
    layers = {
        "Si_Etch0_EBL_DF_94nm": pf.LayerSpec((60, 0), "Etch", "#ff800018", "/"),
        "Si_Etch1_DUV_DF_70nm": pf.LayerSpec((6, 0), "Etch", "#ff444418", "/"),
        "Si_Etch2_LF_120nm":    pf.LayerSpec((3, 0), "Waveguide", "#0080ff18", "\\"),
        "Si_Etch2_DF_120nm":    pf.LayerSpec((4, 0), "Waveguide", "#80c0ff18", "\\\\"),
        "Si_Etch3_LF_100nm_to_BOX": pf.LayerSpec((5, 0), "Waveguide", "#a080ff18", ":"),
        "Heat_Fil_LF":          pf.LayerSpec((39, 0), "Metal", "#ebc63418", "xx"),
        "Heat_CP_LF":           pf.LayerSpec((41, 0), "Metal", "#c0c0c018", "xx"),
        "Floorplan":            pf.LayerSpec((99, 0), "Misc", "#80808018", "hollow"),
        "Label_Etch_DF":        pf.LayerSpec((100, 0), "Misc", "#a0a0a018", "/"),
    }

    wg_lf = pf.MaskSpec((3, 0))
    rib   = pf.MaskSpec((5, 0))
    g_ebl = pf.MaskSpec((60, 0))
    g_duv = pf.MaskSpec((6, 0))

    full_si_mask     = (wg_lf - g_ebl) - g_duv          # full 220 nm Si
    ebl_grating_mask = wg_lf * g_ebl                     # 125 nm Si remains
    duv_grating_mask = wg_lf * g_duv                     # 150 nm Si remains
    slab_only_mask   = rib - wg_lf                       # 100 nm Si in slab outside core

    z_heater = si_thickness + metal_si_separation
    z_pad    = z_heater + heater_thickness + 0.1         # 100 nm dielectric gap

    extrusion_specs = [
        pf.ExtrusionSpec(full_si_mask,     _SI,  (0.0, si_thickness),         sidewall_angle),
        pf.ExtrusionSpec(ebl_grating_mask, _SI,  (0.0, ebl_grating_remaining), sidewall_angle),
        pf.ExtrusionSpec(duv_grating_mask, _SI,  (0.0, duv_grating_remaining), sidewall_angle),
        pf.ExtrusionSpec(slab_only_mask,   _SI,  (0.0, rib_slab_thickness),    sidewall_angle),
        pf.ExtrusionSpec(pf.MaskSpec((39, 0)), _TIN, (z_heater, z_heater + heater_thickness)),
        pf.ExtrusionSpec(pf.MaskSpec((41, 0)), _AL,  (z_pad,    z_pad + pad_thickness)),
    ]
    if include_substrate:
        extrusion_specs.insert(
            0, pf.ExtrusionSpec(pf.MaskSpec(), _SI, (-pf.Z_INF, -box_thickness))
        )

    # Port specs. Path profiles tuple = (width, offset, layer).
    # For rib XSes, BOTH core and slab profiles must be present (CLAUDE.md rule).
    z_port_lo = -1.0
    z_port_hi = 1.0 + si_thickness

    ports = {
        "strip_1310nm": pf.PortSpec(
            description="Strip TE/TM 1310 nm, w=400 nm",
            width=2.0,
            limits=(z_port_lo, z_port_hi),
            num_modes=2,
            polarization=None,
            target_neff=2.8,
            path_profiles=((0.4, 0.0, (3, 0)),),
        ),
        "strip_1550nm": pf.PortSpec(
            description="Strip TE/TM 1550 nm, w=450 nm",
            width=2.5,
            limits=(z_port_lo, z_port_hi),
            num_modes=2,
            polarization=None,
            target_neff=2.5,
            path_profiles=((0.45, 0.0, (3, 0)),),
        ),
        "rib_1310nm_TE": pf.PortSpec(
            description="Rib TE 1310 nm, w=400 nm core / 10.4 um slab",
            width=4.0,
            limits=(z_port_lo, z_port_hi),
            num_modes=1,
            polarization="TE",
            target_neff=3.0,
            path_profiles=(
                (0.4, 0.0, (3, 0)),
                (10.4, 0.0, (5, 0)),
            ),
        ),
        "rib_1550nm_TE": pf.PortSpec(
            description="Rib TE 1550 nm, w=450 nm core / 10.45 um slab",
            width=4.0,
            limits=(z_port_lo, z_port_hi),
            num_modes=1,
            polarization="TE",
            target_neff=2.7,
            path_profiles=(
                (0.45, 0.0, (3, 0)),
                (10.45, 0.0, (5, 0)),
            ),
        ),
    }
    # Note: heater electrical contacts are exposed as ``pf.Terminal``
    # objects (see ``component.py``), not as PortSpecs — Terminals are the
    # PhotonForge analog of contact-pad routing nodes.

    tech = pf.Technology(
        "Cornerstone Si_220nm_passive",
        "0.1.0",
        layers,
        extrusion_specs,
        ports,
        _SIO2,
    )
    # Process tolerances from process_overview.yaml (Waveguide thickness ±20 nm,
    # rib slab ±20 nm) are recorded for downstream Monte Carlo.
    tech.random_variables = [
        pf.monte_carlo.RandomVariable("si_thickness", value=si_thickness, stdev=0.020 / 6),
        pf.monte_carlo.RandomVariable("rib_slab_thickness", value=rib_slab_thickness, stdev=0.020 / 6),
        pf.monte_carlo.RandomVariable("box_thickness", value=box_thickness, stdev=0.06 / 6),
    ]
    return tech


def _drc_metadata(platform: str = "Si_220nm_passive") -> dict:
    """Return per-layer DRC rules from the vendored YAML, for use by the
    DRC checker. Not attached to the Technology object but importable for
    the agent loop scripts."""
    proc = _yl.load_process_overview(platform)
    out = {}
    for entry in proc.get("gds_layers", []):
        layer = tuple(entry["layer"])
        drc = entry.get("drc")
        if drc is None:
            continue
        if isinstance(drc, dict):
            rules = [drc]
        else:
            rules = list(drc)
        out[layer] = {
            "name": entry["name"],
            "alias": entry.get("alias"),
            "is_info_only": entry.get("is_info_only", False),
            "rules": rules,
        }
    return out
