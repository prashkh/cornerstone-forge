"""Shared medium definitions used across Cornerstone platforms.

Each material gets a dict with ``optical`` and ``electrical`` Tidy3D
``Medium`` objects so PhotonForge can pick the right one for FDTD vs.
charge / heat simulations.

Where Cornerstone publishes refractive-index CSVs in their own repo
(``materials/Si.csv`` etc.), we still default to ``tidy3d.material_library``
for cross-platform consistency. v0.2.0 plans to optionally load from
the vendored CSVs.
"""
from __future__ import annotations

import tidy3d as td


_LOSSY_FIT = td.SurfaceImpedanceFitterParam(max_num_poles=16)


SI = {
    "optical": td.material_library["cSi"]["Li1993_293K"],
    "electrical": td.Medium(permittivity=11.7, name="Si"),
}

SIO2 = {
    "optical": td.material_library["SiO2"]["Palik_Lossless"],
    "electrical": td.Medium(permittivity=3.9, name="SiO2"),
}

SIN = {
    "optical": td.material_library["Si3N4"]["Luke2015PMLStable"],
    "electrical": td.Medium(permittivity=7.5, name="Si3N4"),
}

# Germanium for Ge_on_Si mid-IR. Icenogle1976 covers near-IR through
# 12 µm so it works well at the 3.8 µm Cornerstone design wavelength.
# Foundry-CSV integration is a v0.2.0 task.
GE = {
    "optical": td.material_library["Ge"]["Icenogle1976"],
    "electrical": td.Medium(permittivity=16.0, name="Ge"),
}

# TiN heater filament — not in tidy3d.material_library; substitute Ti
# (similar lossy refractive metal).
TIN = {
    "optical": td.material_library["Ti"]["Werner2009"],
    "electrical": td.LossyMetalMedium(
        conductivity=2.5,
        frequency_range=[0.1e9, 200e9],
        fit_param=_LOSSY_FIT,
    ),
}

AL = {
    "optical": td.material_library["Al"]["Rakic1995"],
    "electrical": td.LossyMetalMedium(
        conductivity=37.7,
        frequency_range=[0.1e9, 200e9],
        fit_param=_LOSSY_FIT,
    ),
}


# Cornerstone YAML uses the magic strings ``metal1`` and ``metal2`` for
# the heater filament and contact pad layers respectively (in passive
# platforms). For Si_220nm_active they're the RF electrode.
DEFAULT_PLATFORM_MEDIA = {
    "Si": SI,
    "SiO2": SIO2,
    "SiN": SIN,
    "Ge": GE,
    "metal1": TIN,
    "metal2": AL,
}
