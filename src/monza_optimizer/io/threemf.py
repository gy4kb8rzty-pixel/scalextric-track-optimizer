"""Verified 3MF loader — reads mesh packages for catalog validation and export."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import zipfile
from pathlib import Path


@dataclass
class ThreeMFMesh:
    object_id: str
    name: str
    vertices: list[tuple[float, float, float]] = field(default_factory=list)
    triangles: list[tuple[int, int, int]] = field(default_factory=list)

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)

    def bounding_box(self) -> tuple[float, float, float, float, float, float]:
        if not self.vertices:
            return (0, 0, 0, 0, 0, 0)
        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        zs = [v[2] for v in self.vertices]
        return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)


class ThreeMFLoader:
    """Load triangle meshes from a .3mf package."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)

    def load(self) -> list[ThreeMFMesh]:
        with zipfile.ZipFile(self.path, "r") as zf:
            model_names = [n for n in zf.namelist() if n.endswith(".model")]
            if not model_names:
                raise ValueError(f"no .model part in {self.path}")
            # Prefer 3D/3dmodel.model
            model_name = next(
                (n for n in model_names if "3dmodel" in n.lower()), model_names[0]
            )
            xml = zf.read(model_name).decode("utf-8", errors="replace")
        return self._parse_model(xml)

    def _parse_model(self, xml: str) -> list[ThreeMFMesh]:
        meshes: list[ThreeMFMesh] = []
        # Split on object tags that contain a mesh
        for m in re.finditer(
            r'<object\s+id="(\d+)"([^>]*)>\s*<mesh>(.*?)</mesh>',
            xml,
            re.DOTALL,
        ):
            oid, attrs, body = m.group(1), m.group(2), m.group(3)
            name_m = re.search(r'name="([^"]*)"', attrs)
            name = name_m.group(1) if name_m else f"object_{oid}"
            verts = [
                (float(x), float(y), float(z))
                for x, y, z in re.findall(
                    r'<vertex\s+x="([^"]+)"\s+y="([^"]+)"\s+z="([^"]+)"', body
                )
            ]
            tris = [
                (int(a), int(b), int(c))
                for a, b, c in re.findall(
                    r'<triangle\s+v1="([^"]+)"\s+v2="([^"]+)"\s+v3="([^"]+)"', body
                )
            ]
            if verts:
                meshes.append(ThreeMFMesh(oid, name, verts, tris))
        return meshes


def load_3mf_meshes(path: str | Path) -> list[ThreeMFMesh]:
    return ThreeMFLoader(path).load()
