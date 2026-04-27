"""YAML parsers for the vendored Cornerstone PDK files.

These helpers turn the YAML dumps from cornerstone-uos/cornerstone-pdk into
plain Python dicts shaped for the PhotonForge factories. They do not depend
on photonforge, so they can be unit-tested standalone.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple
import yaml

LIBRARY_ROOT = Path(__file__).parent / "library"


def library_path(platform: str) -> Path:
    p = LIBRARY_ROOT / platform
    if not p.is_dir():
        raise FileNotFoundError(f"Vendored library missing for platform {platform!r}: {p}")
    return p


def load_process_overview(platform: str) -> Dict[str, Any]:
    """Parse ``<platform>/process_overview.yaml``."""
    with (library_path(platform) / "process_overview.yaml").open() as f:
        return yaml.safe_load(f)


def load_cross_sections(platform: str) -> List[Dict[str, Any]]:
    """Parse ``<platform>/cross-sections/cross_sections.yaml``."""
    with (library_path(platform) / "cross-sections" / "cross_sections.yaml").open() as f:
        return yaml.safe_load(f)


def load_floorplans(platform: str) -> List[Dict[str, Any]]:
    with (library_path(platform) / "floorplans" / "floorplans.yaml").open() as f:
        return yaml.safe_load(f)


def list_component_yamls(platform: str) -> List[Path]:
    return sorted((library_path(platform) / "components").glob("*.yaml"))


def load_component_yaml(platform: str, name: str) -> Dict[str, Any]:
    path = library_path(platform) / "components" / f"{name}.yaml"
    with path.open() as f:
        return yaml.safe_load(f)


def component_gds_path(platform: str, name: str) -> Path:
    return library_path(platform) / "components" / f"{name}.gds"


def layer_alias_map(process_overview: Dict[str, Any]) -> Dict[str, Tuple[int, int]]:
    """Return alias -> (gds_layer, datatype). Handy for boolean expressions later."""
    out: Dict[str, Tuple[int, int]] = {}
    for entry in process_overview.get("gds_layers", []):
        alias = entry.get("alias")
        if alias:
            out[alias] = tuple(entry["layer"])
    return out
