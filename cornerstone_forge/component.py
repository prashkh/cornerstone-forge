"""Component loader for the Cornerstone PDK.

Each Cornerstone component is a fixed-geometry GDS cell paired with a YAML
metadata file (ports, cross-sections, modes). This module loads the GDS via
``pf.load_layout()`` and re-attaches ports from the YAML so that the resulting
``pf.Component`` is usable in PhotonForge layouts and netlists.

v0.1.0 attaches an empty ``pf.Tidy3DModel()`` (no compact / S-parameter model
yet — these will be added in a later version).
"""

from __future__ import annotations

import json
import math
from typing import List, Optional

import photonforge as pf

from . import _yaml_loader as _yl


# Layers we ignore when copying GDS cells into a PhotonForge component (these
# are info-only and don't participate in the device stack).
_INFO_LAYERS = {(99, 0), (100, 0)}

# YAML cross_section names that correspond to electrical contact pads
# (terminal-style ports rather than guided-mode optical ports).
_ELECTRICAL_LAYERS = {
    "dc": "Heat_CP_LF",  # Cornerstone Si_220nm_passive heater contact
}

# Default fiber-port z position (above the top oxide). Computed at load time
# from the active technology's parametric kwargs when available.
_DEFAULT_FIBER_Z = 2.32  # 220 nm Si + 2.0 µm TOX + 0.1 µm headroom


def list_components(platform: str = "Si_220nm_passive") -> List[str]:
    """Names of every component YAML vendored for ``platform``."""
    return [p.stem for p in _yl.list_component_yamls(platform)]


def component(
    name: str,
    platform: str = "Si_220nm_passive",
    technology: Optional[pf.Technology] = None,
) -> pf.Component:
    """Load a Cornerstone component into a ``pf.Component``.

    Args:
        name: Component name (matches the YAML/GDS stem in the vendored
            library — e.g. ``"SOI220nm_1550nm_TE_STRIP_2x1_MMI"``).
        platform: Platform directory under ``cornerstone_forge/library/``.
        technology: Optional technology override; defaults to the active
            global technology (the user is expected to have called e.g.
            ``cornerstone_forge.si220_passive()`` before this).

    Returns:
        A ``pf.Component`` whose name matches the YAML and whose ports are
        registered against the active technology's port specs.
    """
    meta = _yl.load_component_yaml(platform, name)
    gds_path = _yl.component_gds_path(platform, name)

    # Load every cell from the GDS into a single component
    loaded = pf.load_layout(str(gds_path), technology=technology)

    # Find the cell that matches the YAML name
    cell_name = meta["name"]
    if cell_name not in loaded:
        # Fall back to the first cell if naming drifts
        cell_name = next(iter(loaded.keys()))
    comp = loaded[cell_name]

    # Strip any pre-existing ports (foundry GDS shouldn't have any, but
    # pf.load_layout sometimes infers them from labels)
    # NOTE: pf.Component.remove_port API may differ; instead rebuild a fresh
    # component if ports leak in.

    # Resolve the fiber-port z position from the active technology's
    # parametric kwargs (Si thickness + top oxide + headroom).
    fiber_z = _fiber_port_z(technology or pf.config.default_technology)

    # Add ports from YAML
    for p in meta.get("ports", []):
        _add_port(comp, p, technology or pf.config.default_technology, fiber_z)

    # Attach a Tidy3D model. The default Tidy3D bounding box is derived
    # from the port windows, which can be too tight when the component
    # body is wider than the port spec width (e.g. MMI bodies).  We pad
    # the y/z bounds to fit the component bbox + a small margin so the
    # device geometry never touches the PML boundaries.
    bounds = _model_bounds_with_pad(comp)
    comp.add_model(pf.Tidy3DModel(bounds=bounds), "Tidy3D")
    return comp


_BOUNDS_PAD_UM = 1.0  # extra simulation-domain margin (µm) on each transverse side


def _model_bounds_with_pad(comp: pf.Component) -> tuple:
    """Return Tidy3D simulation bounds that fit the component bbox + pad.

    Only the y bounds are pinned (the propagation direction x and the
    out-of-plane z are left to PhotonForge's port-derived defaults via
    ``None``). Padding lets the FDTD PML sit outside the device body
    instead of clipping a wide MMI / multi-mode section.
    """
    (x0, y0), (x1, y1) = comp.bounds()
    pad = _BOUNDS_PAD_UM
    return (
        (None, float(y0) - pad, None),
        (None, float(y1) + pad, None),
    )


def _find_pad_bounds(
    comp: pf.Component,
    layer_tuple: tuple,
    point: tuple,
) -> Optional[tuple]:
    """Return the bounding box of the polygon on ``layer_tuple`` whose
    bbox contains ``point``. Used to size electrical Terminals to match
    the actual contact-pad shape in the foundry GDS.

    Returns ((x0, y0), (x1, y1)) or None if no pad polygon is found.
    """
    cx, cy = float(point[0]), float(point[1])
    shapes = comp.structures.get(layer_tuple, [])
    eps = 1e-3
    for shape in shapes:
        try:
            (x0, y0), (x1, y1) = shape.bounds()
        except Exception:
            continue
        if x0 - eps <= cx <= x1 + eps and y0 - eps <= cy <= y1 + eps:
            return ((float(x0), float(y0)), (float(x1), float(y1)))
    return None


def _fiber_port_z(tech: Optional[pf.Technology]) -> float:
    if tech is None:
        return _DEFAULT_FIBER_Z
    pk = getattr(tech, "parametric_kwargs", {}) or {}
    si = float(pk.get("si_thickness", 0.22))
    tox = float(pk.get("top_oxide_thickness", 2.0))
    return si + tox + 0.1


def _add_port(
    comp: pf.Component,
    port_meta: dict,
    tech: pf.Technology,
    fiber_z: float,
) -> None:
    """Add one port to ``comp`` based on a YAML port entry.

    Handles four kinds of YAML port_type values:
      * ``optical``                       → ``pf.Port`` on the named cross-section
      * ``electrical_dc`` / ``_rf``       → ``pf.Terminal`` on the contact-pad layer
      * ``vertical_te`` / ``vertical_tm`` → ``pf.GaussianPort`` representing fiber coupling
      * ``edge`` (and any unknown type)   → metadata recorded on ``component.properties``
    """
    port_type = port_meta.get("port_type", "optical")
    name = port_meta["name"]
    center = tuple(port_meta["center"])

    # PhotonForge's input_direction is the direction the incoming wave travels
    # INTO the device. The Cornerstone YAML's "orientation" is the OUTWARD
    # facing direction of the port (it points away from the device body).
    # Flip by 180° so the arrow visually enters the component.
    yaml_orientation = float(port_meta.get("orientation", 0.0))
    input_direction = (yaml_orientation + 180.0) % 360.0

    if port_type == "optical":
        spec_name = port_meta["cross_section"]
        comp.add_port(pf.Port(center, input_direction, spec_name), name)
        return

    if port_type in ("electrical_dc", "electrical_rf"):
        # Heaters and RF DC contacts are routed as Terminals (not guided-mode
        # ports). The contact-pad layer is implied by the YAML cross_section.
        # The terminal Rectangle should match the actual contact-pad polygon
        # in the GDS (so the terminal area equals the pad area), with a
        # fallback to a square marker when no pad is found.
        xs = port_meta.get("cross_section", "dc")
        layer_name = _ELECTRICAL_LAYERS.get(xs, "Heat_CP_LF")
        layer_tuple = tuple(int(v) for v in tech.layers[layer_name].layer)
        pad_bounds = _find_pad_bounds(comp, layer_tuple, center)
        if pad_bounds is not None:
            (x0, y0), (x1, y1) = pad_bounds
            rect_center = ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
            rect_size = (x1 - x0, y1 - y0)
        else:
            size_um = float(port_meta.get("width", 10.0))
            rect_center = center
            rect_size = (size_um, size_um)
        terminal = pf.Terminal(
            layer_tuple,
            pf.Rectangle(center=rect_center, size=rect_size),
        )
        comp.add_terminal(terminal, name)
        return

    if port_type in ("vertical_te", "vertical_tm"):
        # Fiber-side port for grating couplers. Convert the YAML coupling
        # angle + orientation to a 3D propagation vector pointing INTO the
        # chip (vz<0) with an in-plane tilt toward the grating's diffraction
        # direction.
        cx, cy = center
        coupling_angle_deg = float(port_meta.get("coupling_angle_cladding", 0.0))
        a = math.radians(coupling_angle_deg)
        o = math.radians(yaml_orientation)
        vx = math.sin(a) * math.cos(o)
        vy = math.sin(a) * math.sin(o)
        vz = -math.cos(a)
        waist = float(port_meta.get("width", 10.0)) / 2.0
        polarization = 90.0 if port_type == "vertical_te" else 0.0
        comp.add_port(
            pf.GaussianPort(
                (cx, cy, fiber_z),
                (vx, vy, vz),
                waist_radius=waist,
                polarization_angle=polarization,
            ),
            name,
        )
        return

    # Edge couplers and anything else: record metadata only.
    comp.properties[f"{port_type}_{name}"] = json.dumps(port_meta)
