"""Per-platform Technology factories for the Cornerstone PDK.

Each factory is a thin wrapper around the data-driven loader in
``_platform_loader``. The platform-specific knobs (media, target n_eff,
metal placement) live in ``_platforms/<platform>.py``.

Public API:

    cornerstone_forge.si220_passive    # SOI 220 nm passive (heaters)

Future platforms (planned):

    .si220_active, .si340, .si500,
    .sin300, .sin200, .ge_on_si,
    .si_sus_bias, .si_sus_not_bias

To inspect the per-layer DRC rules from the foundry YAML for a given
platform, use ``cornerstone_forge.drc_metadata(platform)``.
"""
from __future__ import annotations

from typing import Any, Dict

from . import _yaml_loader as _yl
from ._platforms.si_220nm_passive import si220_passive
from ._platforms.si_220nm_active import si220_active
from ._platforms.si_340nm import si340
from ._platforms.si_500nm import si500
from ._platforms.sin_300nm import sin300
from ._platforms.sin_200nm import sin200
from ._platforms.ge_on_si import ge_on_si
from ._platforms.si_sus import si_sus_bias, si_sus_not_bias

__all__ = [
    "si220_passive", "si220_active", "si340", "si500",
    "sin300", "sin200", "ge_on_si",
    "si_sus_bias", "si_sus_not_bias", "drc_metadata",
]


def drc_metadata(platform: str = "Si_220nm_passive") -> Dict[Any, Any]:
    """Return the per-layer DRC rules from ``process_overview.yaml``.

    Keyed by ``(gds_layer, datatype)``. Each value has the layer name,
    alias, ``is_info_only`` flag, and a list of rule dicts (with keys
    ``min_feature_size``, ``min_gap``, ``max_feature_length`` etc.).
    """
    proc = _yl.load_process_overview(platform)
    out = {}
    for entry in proc.get("gds_layers", []):
        layer = (int(entry["layer"][0]), int(entry["layer"][1]))
        drc = entry.get("drc")
        if drc is None:
            continue
        rules = [drc] if isinstance(drc, dict) else list(drc)
        out[layer] = {
            "name": entry["name"],
            "alias": entry.get("alias"),
            "is_info_only": bool(entry.get("is_info_only", False)),
            "rules": rules,
        }
    return out


# Backwards compat: agent_loop scripts import this from technology
_drc_metadata = drc_metadata
