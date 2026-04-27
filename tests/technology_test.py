import photonforge as pf

import cornerstone_forge as cf


def test_export(tmp_path):
    """Export the technology to a .phf file and reload — round-trip
    must preserve layers, ports, extrusion specs, and background medium."""
    tech = cf.si220_passive()
    tech_file = tmp_path / "tech.phf"
    pf.write_phf(tech_file, tech)
    tech_loaded = pf.load_phf(tech_file)["technologies"][0]
    assert tech_loaded.name == tech.name
    assert tech_loaded.version == tech.version
    assert tech_loaded.layers == tech.layers
    assert tech_loaded.ports == tech.ports
    assert tech_loaded.extrusion_specs == tech.extrusion_specs
    assert tech_loaded.background_medium == tech.background_medium
    assert tech_loaded == tech


def test_layer_yaml_alignment():
    """Every layer name in the technology must match the foundry YAML's
    `name` field exactly."""
    from cornerstone_forge import _yaml_loader as _yl

    tech = cf.si220_passive()
    proc = _yl.load_process_overview("Si_220nm_passive")
    yaml_names = {e["name"] for e in proc["gds_layers"]}
    tech_names = set(tech.layers.keys())
    missing = yaml_names - tech_names
    assert not missing, f"YAML layers missing from Technology: {missing}"


def test_port_specs_present():
    """The four PortSpecs in cross_sections.yaml that have a
    waveguide cross_section type must be in tech.ports."""
    tech = cf.si220_passive()
    expected = {"strip_1310nm", "strip_1550nm", "rib_1310nm_TE", "rib_1550nm_TE"}
    assert expected.issubset(set(tech.ports.keys()))
