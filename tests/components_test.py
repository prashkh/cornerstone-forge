"""Smoke tests: every shipped component loads, has ports / terminals
attached per its YAML, and round-trips to GDS without changing geometry."""
from __future__ import annotations

import tempfile
from pathlib import Path

import gdstk
import photonforge as pf

import cornerstone_forge as cf


def _load_polys_by_layer(path: Path):
    lib = gdstk.read_gds(str(path))
    cell = lib.cells[0]
    flat = cell.flatten()
    out = {}
    for p in flat.polygons:
        out.setdefault((p.layer, p.datatype), []).append(p)
    return out


def test_component_load():
    """Every YAML in the library directory loads without error and has
    at least one optical port or terminal attached."""
    tech = cf.si220_passive()
    pf.config.default_technology = tech
    for name in cf.list_components():
        c = cf.component(name)
        # Every cell except the Packaging Template should expose at least
        # one connection point (port or terminal).
        if name != "Cell0_SOI220_Full_1550nm_Packaging_Template":
            assert (len(c.ports) + len(c.terminals)) > 0, (
                f"{name}: no ports/terminals attached"
            )


def test_component_round_trip(tmp_path):
    """Write each component back to GDS and XOR against the source.
    Diff must be empty on every layer except Floorplan (99,0) and
    Label_Etch_DF (100,0) (info layers)."""
    tech = cf.si220_passive()
    pf.config.default_technology = tech
    info_layers = {(99, 0), (100, 0)}
    from cornerstone_forge import _yaml_loader as _yl

    for name in cf.list_components():
        c = cf.component(name)
        out = tmp_path / f"{name}.gds"
        c.write_gds(str(out))

        src_polys = _load_polys_by_layer(_yl.component_gds_path("Si_220nm_passive", name))
        dst_polys = _load_polys_by_layer(out)
        for layer in set(src_polys) | set(dst_polys):
            if layer in info_layers:
                continue
            src_join = gdstk.boolean(src_polys.get(layer, []), [], "or")
            dst_join = gdstk.boolean(dst_polys.get(layer, []), [], "or")
            diff = gdstk.boolean(src_join, dst_join, "xor")
            area = sum(abs(gdstk.Polygon.area(p)) for p in diff)
            assert area < 1e-6, (
                f"{name} layer {layer}: round-trip XOR area {area:.3f} um^2 != 0"
            )
