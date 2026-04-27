"""Data-driven Technology builder.

Each Cornerstone platform ships a ``process_overview.yaml`` with the
authoritative layer list, layer stack, and DRC rules; a
``cross-sections/cross_sections.yaml`` with the waveguide cross sections;
and (optionally) ``materials/<name>.csv`` with foundry-published n(λ).

This module turns those into a ``photonforge.Technology`` with minimal
per-platform Python — only the medium dictionary and a couple of
z-position knobs need to be supplied by the platform module.

Public entry point:

    from cornerstone_forge._platform_loader import build_technology, PlatformConfig
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import photonforge as pf
import tidy3d as td

from . import _yaml_loader as _yl


# --------------------------------------------------------------------- #
# Platform configuration (passed in from per-platform modules)
# --------------------------------------------------------------------- #

@dataclass
class PlatformConfig:
    """Knobs that vary per Cornerstone platform.

    The data-driven loader handles the rest — layer specs, port specs,
    extrusion specs are all derived from the vendored YAML files.
    """

    platform: str
    """Library directory name, e.g. ``"Si_220nm_passive"``."""

    name: str
    """Human-readable technology name."""

    version: str
    """Technology version (matches the package version typically)."""

    media: Dict[str, Dict[str, Any]]
    """Map ``yaml material name → {"optical": Medium, "electrical": Medium}``.

    Cornerstone YAML uses ``Si``, ``SiO2``, ``SiN``, ``Ge``, ``metal1``,
    ``metal2``. Provide entries for every material that appears in
    ``process_overview.yaml``'s layer_stack."""

    target_neff: Dict[str, float] = field(default_factory=dict)
    """Map cross-section name → target_neff for PortSpec. If absent, a
    sensible default is picked from the cross-section's material."""

    polarization: Dict[str, str] = field(default_factory=dict)
    """Map cross-section name → ``"TE"``, ``"TM"``, or ``""`` (auto)."""

    metal_extra_z_above_tox: float = 0.0
    """Extra z gap added on top of TOX before the first metal layer."""

    inter_metal_gap: float = 0.1
    """Vertical gap between successive metal layers (µm)."""

    fiber_z_above_tox: float = 0.1
    """Z headroom above the top of TOX for ``pf.GaussianPort`` placement."""

    sidewall_angle: float = 0.0

    info_layers: Tuple[Tuple[int, int], ...] = ((99, 0), (100, 0))
    """GDS layers excluded from the extrusion stack (Floorplan, Label)."""

    suspended_xs_types: Tuple[str, ...] = ("suspended",)
    """Cross-section types that are reported but not extruded (mid-IR
    suspended waveguides cannot be cleanly extruded for FDTD)."""

    port_z_pad: float = 1.0
    """Out-of-plane PortSpec ``limits`` extension above/below the Si stack."""


# --------------------------------------------------------------------- #
# YAML mask expression → pf.MaskSpec
# --------------------------------------------------------------------- #

# Cornerstone uses Python-keyword booleans in `gds_layer:` expressions,
# e.g. ``(wg_lf or not wg_df) and not (grating_ebl or grating_duv)``.
#
# Note on the ``or not <df_layer>`` clause: Cornerstone's process flow
# uses paired light-field (LF) / dark-field (DF) layers — the foundry's
# etcher etches where a DF layer is drawn, so "Si remains where wg_lf
# OR (not wg_df)" is correct *for fabrication*. For simulation we want
# only the explicitly drawn Si, so we strip out the ``or not <df>``
# clauses before parsing. PhotonForge simulates exactly the geometry
# the user draws.
_BOOL_TOKEN = re.compile(r"\b(and|or|not)\b")
_BOOL_MAP = {"and": "&", "or": "|", "not": "~"}
_OR_NOT_DF_PATTERN = re.compile(r"\s+or\s+not\s+\w*_df\b", re.IGNORECASE)


def _rewrite_yaml_expr(expr: str) -> str:
    # Drop "or not <something>_df" clauses so Si only extrudes where
    # the user explicitly drew on the LF layer.
    expr = _OR_NOT_DF_PATTERN.sub("", expr)
    return _BOOL_TOKEN.sub(lambda m: _BOOL_MAP[m.group(1)], expr)


class _MaskExprEvaluator(ast.NodeVisitor):
    def __init__(self, alias_to_layer: Dict[str, Tuple[int, int]]):
        self.aliases = alias_to_layer
        self.full = pf.MaskSpec()  # empty operands = full component bounds

    def visit_Name(self, node: ast.Name):
        if node.id not in self.aliases:
            raise ValueError(f"Unknown layer alias/name in mask expression: {node.id!r}")
        return pf.MaskSpec(self.aliases[node.id])

    def visit_BinOp(self, node: ast.BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.BitAnd):
            return left * right
        if isinstance(node.op, ast.BitOr):
            return left + right
        raise ValueError(f"Unsupported binary op in mask expression: {node.op}")

    def visit_UnaryOp(self, node: ast.UnaryOp):
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.Invert):
            return self.full - operand
        raise ValueError(f"Unsupported unary op in mask expression: {node.op}")

    def visit_Expression(self, node: ast.Expression):
        return self.visit(node.body)


def parse_mask_expression(
    expr: Any,
    alias_to_layer: Dict[str, Tuple[int, int]],
) -> pf.MaskSpec:
    """Convert a Cornerstone YAML ``gds_layer`` expression to a MaskSpec.

    Accepts a string (parsed via ast) or a single alias name (returned
    directly as a single-layer MaskSpec).
    """
    if expr is None:
        raise ValueError("gds_layer is None — caller should skip this entry")
    if isinstance(expr, list):
        # YAML sequence form: [(num, dt)]
        return pf.MaskSpec(tuple(expr))
    s = str(expr).strip()
    if s in alias_to_layer:
        return pf.MaskSpec(alias_to_layer[s])
    py = _rewrite_yaml_expr(s)
    tree = ast.parse(py, mode="eval")
    return _MaskExprEvaluator(alias_to_layer).visit(tree)


# --------------------------------------------------------------------- #
# Layer specs
# --------------------------------------------------------------------- #

# Deterministic palette (ROYGBIV-ish). Picked to be visually distinct in
# the LiveViewer and the dashboard table.
_PALETTE = [
    "#0080ff", "#80c0ff", "#a080ff", "#ff8000", "#ff4444", "#ebc634",
    "#c0c0c0", "#a6cee3", "#cea6e3", "#ffae00", "#3a027f", "#7000ff",
    "#5fa850", "#ff90c0",
]
_GROUP_PATTERN = {
    "Etch": "/", "Waveguide": "\\", "Slab": ":", "Metal": "xx",
    "Implant": ":", "RF": "xx", "Misc": "hollow",
}


def _classify_layer(entry: dict) -> str:
    """Pick a group string from the YAML alias / name."""
    alias = (entry.get("alias") or "").lower()
    name = entry.get("name", "").lower()
    if "grating" in alias or "grating" in name or "ebl" in alias or "duv" in alias:
        return "Etch"
    if alias in ("wg_lf", "wg_df") or "etch2" in name:
        return "Waveguide"
    if alias == "rib_slab" or "slab" in name or "etch3" in name:
        return "Slab"
    if "heat" in alias or "heat" in name or "electrode" in alias or "metal" in name:
        return "Metal"
    if "implant" in alias or "implant" in name:
        return "Implant"
    if alias.startswith("rf") or "rf" in name.lower():
        return "RF"
    if entry.get("is_info_only"):
        return "Misc"
    return "Misc"


def build_layer_specs(proc: dict) -> Dict[str, pf.LayerSpec]:
    """Build a ``LayerSpec`` dict keyed by the YAML ``name`` field.

    Each layer gets a deterministic color from the palette (so the same
    alias gets the same color across platforms when possible). Pattern
    is chosen by group classification.
    """
    layers: Dict[str, pf.LayerSpec] = {}
    for i, entry in enumerate(proc.get("gds_layers", [])):
        name = entry["name"]
        layer = (int(entry["layer"][0]), int(entry["layer"][1]))
        group = _classify_layer(entry)
        color = _PALETTE[i % len(_PALETTE)] + "18"  # 18 = ~9% alpha (KLayout-style)
        pattern = _GROUP_PATTERN.get(group, "\\")
        layers[name] = pf.LayerSpec(layer, group, color, pattern)
    return layers


def build_alias_map(proc: dict) -> Dict[str, Tuple[int, int]]:
    """alias OR name → (gds_layer, datatype). Lets mask expressions
    reference layers by alias or by full YAML name."""
    out: Dict[str, Tuple[int, int]] = {}
    for entry in proc.get("gds_layers", []):
        layer = (int(entry["layer"][0]), int(entry["layer"][1]))
        out[entry["name"]] = layer
        if entry.get("alias"):
            out[entry["alias"]] = layer
    return out


# --------------------------------------------------------------------- #
# Extrusion specs
# --------------------------------------------------------------------- #

def build_extrusions(
    proc: dict,
    aliases: Dict[str, Tuple[int, int]],
    config: PlatformConfig,
    *,
    include_substrate: bool = False,
) -> Tuple[List[pf.ExtrusionSpec], Dict[str, float]]:
    """Walk ``layer_stack`` in YAML order and emit ExtrusionSpecs.

    Returns (extrusion_specs, derived_z) where derived_z exposes named
    z-bounds (``box_thickness``, ``top_oxide_thickness``, ``z_heater``,
    ``z_pad`` etc.) for use by PortSpec construction and for downstream
    annotations.
    """
    extrusions: List[pf.ExtrusionSpec] = []
    derived: Dict[str, float] = {}

    z_si_top = 0.0     # tracks max top of Si plane (waveguide thickness)
    seen_box = False
    in_above_tox = False
    metal_z = None     # z at which the next metal layer starts

    for entry in proc.get("layer_stack", []):
        material = entry.get("material")
        thickness = float(entry["thickness"]["value"])
        gds_expr = entry.get("gds_layer")
        is_metal = bool(entry.get("is_metal_layer"))

        # SiO2 entries are background (BOX = first, TOX = second). v0.1
        # ignores any gds_layer expression on SiO2 (e.g. ``not Isolation_DF``
        # marking heater isolation trenches) — that's a charge-sim concern.
        if material == "SiO2":
            if not seen_box:
                derived["box_thickness"] = thickness
                seen_box = True
            else:
                derived["top_oxide_thickness"] = thickness
                in_above_tox = True
                metal_z = z_si_top + thickness + config.metal_extra_z_above_tox
            continue

        # Skip entries with no GDS layer that we didn't classify.
        if gds_expr is None:
            continue

        try:
            mask = parse_mask_expression(gds_expr, aliases)
        except Exception as e:
            raise ValueError(
                f"Could not parse layer_stack '{entry.get('name')}' "
                f"gds_layer expression {gds_expr!r}: {e}"
            )

        if material not in config.media:
            raise KeyError(
                f"Platform {config.platform}: layer_stack entry "
                f"{entry.get('name')!r} uses material {material!r} but "
                f"the platform config did not provide a medium for it. "
                f"Add it to PlatformConfig.media."
            )
        medium = config.media[material]

        if is_metal:
            if metal_z is None:
                # No TOX seen yet; default to half a µm above the Si top.
                metal_z = z_si_top + 0.5
            extrusions.append(
                pf.ExtrusionSpec(mask, medium, (metal_z, metal_z + thickness), 0.0)
            )
            # Record canonical z bindings for the first two metals
            if "z_heater" not in derived:
                derived["z_heater"] = metal_z
                derived["heater_thickness"] = thickness
            elif "z_pad" not in derived:
                derived["z_pad"] = metal_z
                derived["pad_thickness"] = thickness
            metal_z = metal_z + thickness + config.inter_metal_gap
            continue

        # Si / SiN / Ge etc. — extrudes from z=0 (top of BOX) upward.
        extrusions.append(
            pf.ExtrusionSpec(mask, medium, (0.0, thickness), config.sidewall_angle)
        )
        z_si_top = max(z_si_top, thickness)

    if include_substrate:
        si_medium = config.media.get("Si") or next(iter(config.media.values()))
        substrate_z = derived.get("box_thickness", 3.0)
        extrusions.insert(
            0, pf.ExtrusionSpec(pf.MaskSpec(), si_medium, (-pf.Z_INF, -substrate_z))
        )

    derived.setdefault("box_thickness", 3.0)
    derived.setdefault("top_oxide_thickness", 2.0)
    derived["si_top"] = z_si_top
    return extrusions, derived


# --------------------------------------------------------------------- #
# Port specs
# --------------------------------------------------------------------- #

def build_port_specs(
    xs_data: List[dict],
    aliases: Dict[str, Tuple[int, int]],
    derived_z: Dict[str, float],
    config: PlatformConfig,
) -> Dict[str, pf.PortSpec]:
    """Build PortSpec dict from ``cross_sections.yaml``.

    Only ``strip``, ``rib`` (and other guided-mode XS types) become
    PortSpecs — electrical / dc-like cross sections are handled at the
    component layer via ``pf.Terminal``. Suspended XSes are tagged via
    PortSpec.properties so downstream code can skip FDTD on them.
    """
    si_top = derived_z.get("si_top", 0.22)
    z_lo = -config.port_z_pad
    z_hi = si_top + config.port_z_pad

    ports: Dict[str, pf.PortSpec] = {}
    for xs in xs_data:
        xs_type = xs.get("xs_type")
        # Skip electrical / DC cross sections — they are Terminals.
        if xs_type in ("dc", "png"):
            continue

        name = xs["name"]
        width = float(xs["width"])
        modes = xs.get("modes", []) or []
        # num_modes = number of distinct (polarisation, wavelength) entries
        seen_modes = set()
        for m in modes:
            seen_modes.add((m.get("polarisation", "TE"), m.get("wavelength")))
        num_modes = max(1, len(seen_modes))

        # Heuristic polarization: if all modes are TE/TM → fix; else None.
        pols = {m.get("polarisation", "TE") for m in modes}
        if len(pols) == 1:
            polarization = pols.pop() if pols else None
        else:
            polarization = None
        polarization = config.polarization.get(name, polarization)

        # path_profiles from layers[]
        path_profiles = []
        for layer_entry in xs.get("layers", []):
            layer_tuple = (int(layer_entry["layer"][0]), int(layer_entry["layer"][1]))
            offset = float(layer_entry.get("offset", 0.0))
            w = float(layer_entry["width"])
            path_profiles.append((w, offset, layer_tuple))

        if not path_profiles:
            continue

        # Port window width:
        #   strip: 5x core width (mode + 2x mode area on each side),
        #          minimum 2.5 µm.
        #   rib  : ~5x core width, but capped well below the slab width
        #          so the slab gets clipped at the port boundary. Without
        #          clipping, the slab supports a continuous quasi-1D mode
        #          that the mode solver finds instead of the core mode.
        narrow = min(p[0] for p in path_profiles)
        widest = max(p[0] for p in path_profiles)
        if xs_type == "strip":
            port_width = max(5.0 * narrow, 2.5)
        else:
            # Slab is the widest path_profile. Port must clip it.
            slab_clip = widest * 0.5  # ~half the slab width
            port_width = max(5.0 * narrow, 4.0)
            port_width = min(port_width, slab_clip)

        target_neff = config.target_neff.get(
            name, _default_neff_for(xs.get("materials", "Si"))
        )

        spec = pf.PortSpec(
            description=f"{xs_type} {xs.get('materials','?')} {name}, w={width:.3f} um",
            width=port_width,
            limits=(z_lo, z_hi),
            num_modes=max(num_modes, 2 if polarization is None else 1),
            polarization=polarization,
            target_neff=target_neff,
            path_profiles=tuple(path_profiles),
        )
        # Tag suspended XSes so component / dashboard code can skip FDTD.
        if xs_type in config.suspended_xs_types or xs.get("is_suspended"):
            spec.properties["is_suspended"] = True
            spec.properties["suspended_note"] = (
                f"{name} is a suspended XS — FDTD extrusion is skipped."
            )
        ports[name] = spec
    return ports


def _default_neff_for(material: str) -> float:
    return {
        "Si": 2.5,
        "SiN": 1.9,
        "Ge": 3.4,
    }.get(material, 2.0)


# --------------------------------------------------------------------- #
# Top-level builder
# --------------------------------------------------------------------- #

def build_technology(
    config: PlatformConfig,
    *,
    include_substrate: bool = False,
    **_kwargs,  # accept and ignore extra parametric kwargs for now
) -> pf.Technology:
    """Build a ``photonforge.Technology`` for the given platform.

    Reads the vendored ``process_overview.yaml`` and
    ``cross-sections/cross_sections.yaml`` and constructs the layer /
    extrusion / port specs from the platform config.
    """
    proc = _yl.load_process_overview(config.platform)
    xs = _yl.load_cross_sections(config.platform)

    aliases = build_alias_map(proc)
    layers = build_layer_specs(proc)
    extrusions, derived = build_extrusions(
        proc, aliases, config, include_substrate=include_substrate
    )
    ports = build_port_specs(xs, aliases, derived, config)

    bg = config.media.get("SiO2") or next(iter(config.media.values()))

    tech = pf.Technology(
        config.name,
        config.version,
        layers,
        extrusions,
        ports,
        bg,
    )
    # Stash derived numbers so dashboard / annotations can read them.
    for k, v in derived.items():
        tech.properties[f"derived_{k}"] = float(v)
    return tech
