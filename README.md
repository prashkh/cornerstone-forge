# Cornerstone Forge

This Python module implements the open-source [Cornerstone PDK](https://github.com/cornerstone-uos/cornerstone-pdk)
(University of Southampton silicon photonics MPW foundry) as components and
technology specifications for
[PhotonForge](https://docs.flexcompute.com/projects/photonforge/).

The current release ships the **Si_220nm_passive** platform:

- 9 GDS layers (Si etches, heater filament, contact pads, info)
- 4 PortSpecs (strip 1310 / strip 1550 / rib 1310 TE / rib 1550 TE)
- 6 ExtrusionSpecs covering the full Si stack including grating shallow etches
- 29 fixed-geometry GDS components (waveguides, MMIs, bends, crossings,
  grating couplers, MZIs, heater, packaging template) loaded with ports
  attached from the foundry's YAML metadata

Additional Cornerstone platforms (`Si_220nm_active`, `Si_340nm`, `Si_500nm`,
`SiN_300nm`, `SiN_200nm`, `Ge_on_Si`, `Si_sus_*`) are planned for a future
release.

## Installation

### Python interface

```
pip install cornerstone-forge
```

## Usage

```python
import photonforge as pf
import cornerstone_forge as cf

# Activate the Si_220nm_passive technology
tech = cf.si220_passive()
pf.config.default_technology = tech

# List the components shipped with the PDK
print(cf.list_components())

# Load a foundry GDS cell with ports attached from its YAML metadata
mmi = cf.component("SOI220nm_1550nm_TE_STRIP_2x1_MMI")

# Layout-only in this release: an empty Tidy3DModel is attached and
# component.s_matrix(...) will run FDTD on demand. Pre-baked compact /
# S-parameter models are planned for a future release.
```

The included `notebooks/technology_demo.ipynb` walks through layers,
extrusions, port specs, and stack-up cross sections. `notebooks/component_demo.ipynb`
shows GDS loading, port inspection, cross sections, and 3D rendering.

## What's loaded vs. what isn't

The Cornerstone PDK ships **fixed-geometry GDS cells with YAML metadata** (no
parametric APIs). Each component carries:

- **Optical ports**: `pf.Port` on the strip / rib cross-section spec named in
  the YAML, with `input_direction` flipped from the YAML's `orientation` so
  the port arrow points into the device (the direction light enters).
- **Heater contacts**: `pf.Terminal` on the contact-pad layer, sized to match
  the actual contact-pad polygon in the GDS.
- **Grating-coupler fiber side**: `pf.GaussianPort` placed above the top
  oxide, tilted by the `coupling_angle_cladding` from the YAML.

The `Si_Etch2_DF_120nm` and `Floorplan` / `Label_Etch_DF` info layers are
declared in the technology but pass through round-trip without participating
in the Si extrusion stack.

## Limitations

- `Si_220nm_passive` only — other Cornerstone platforms not yet implemented.
- Layout-only; no foundry-curated S-parameter models attached.
- Cornerstone publishes refractive-index data for Si and SiO2 in the source
  repo. The default media here come from `tidy3d.material_library` (Li1993 Si,
  Palik SiO2) for compatibility with other PhotonForge PDKs; using the
  Cornerstone CSVs directly is on the roadmap.
- TiN heater filament uses Ti from the material library as a placeholder.

## License

MIT — see [LICENSE](LICENSE).
