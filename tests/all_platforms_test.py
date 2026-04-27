"""Smoke tests across every Cornerstone platform.

Walks the 9 platforms shipped in cornerstone-forge v0.2.0 and verifies:
  1. Each technology factory builds without error.
  2. Each platform's library/<platform>/components/*.yaml round-trips
     through ``cornerstone_forge.component()``.
  3. Round-trip XOR of geometry is empty on every non-info layer.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import gdstk
import photonforge as pf
import pytest

import cornerstone_forge as cf
from cornerstone_forge import _yaml_loader as _yl


PLATFORMS = {
    "Si_220nm_passive": cf.si220_passive,
    "Si_220nm_active":  cf.si220_active,
    "Si_340nm":         cf.si340,
    "Si_500nm":         cf.si500,
    "SiN_300nm":        cf.sin300,
    "SiN_200nm":        cf.sin200,
    "Ge_on_Si":         cf.ge_on_si,
    "Si_sus_bias":      cf.si_sus_bias,
    "Si_sus_not_bias":  cf.si_sus_not_bias,
}

INFO_LAYERS = {(99, 0), (100, 0)}


@pytest.mark.parametrize("platform,factory", PLATFORMS.items())
def test_factory_builds(platform, factory):
    """Every platform factory returns a Technology with at least one
    layer, one extrusion spec, and one port spec."""
    tech = factory()
    assert len(tech.layers) > 0, f"{platform}: no layers"
    assert len(tech.extrusion_specs) > 0, f"{platform}: no extrusion specs"
    assert len(tech.ports) > 0, f"{platform}: no port specs"


@pytest.mark.parametrize("platform,factory", PLATFORMS.items())
def test_components_load(platform, factory):
    """Every component in the platform library loads cleanly and (with
    the exception of packaging templates) carries at least one port or
    terminal."""
    tech = factory()
    pf.config.default_technology = tech
    names = cf.list_components(platform)
    assert len(names) > 0, f"{platform}: no components shipped"
    for name in names:
        c = cf.component(name, platform=platform, technology=tech)
        if "Packaging_Template" not in name:
            assert (len(c.ports) + len(c.terminals)) > 0, (
                f"{platform}/{name}: no ports/terminals"
            )


def _polys_by_layer(path: Path):
    lib = gdstk.read_gds(str(path))
    out = {}
    flat = lib.cells[0].flatten()
    for p in flat.polygons:
        out.setdefault((p.layer, p.datatype), []).append(p)
    return out


@pytest.mark.parametrize("platform,factory", PLATFORMS.items())
def test_round_trip(platform, factory, tmp_path):
    """Round-trip each component's GDS export through ``write_gds`` and
    XOR against the source. Must be empty on every non-info layer."""
    tech = factory()
    pf.config.default_technology = tech
    for name in cf.list_components(platform):
        c = cf.component(name, platform=platform, technology=tech)
        out = tmp_path / f"{platform}_{name}.gds"
        c.write_gds(str(out))
        src = _polys_by_layer(_yl.component_gds_path(platform, name))
        dst = _polys_by_layer(out)
        for layer in set(src) | set(dst):
            if layer in INFO_LAYERS:
                continue
            sj = gdstk.boolean(src.get(layer, []), [], "or")
            dj = gdstk.boolean(dst.get(layer, []), [], "or")
            diff = gdstk.boolean(sj, dj, "xor")
            area = sum(abs(gdstk.Polygon.area(p)) for p in diff)
            assert area < 1e-6, (
                f"{platform}/{name} layer {layer}: XOR area {area:.4f} um^2"
            )
