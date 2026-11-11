"""Export print meshes with OpenSCAD 2021.01+, then check them with trimesh.

Usage: python mechanical/export.py --openscad /path/to/openscad
No CAD/network tools are downloaded implicitly.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import hashlib
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MECH = ROOT / "mechanical"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--openscad", default=shutil.which("openscad"))
    ap.add_argument("--render", action="store_true", help="also export OpenGL preview PNG")
    ns = ap.parse_args()
    if not ns.openscad:
        ap.error("OpenSCAD not found; pass --openscad")
    import trimesh
    (MECH / "stl").mkdir(exist_ok=True)
    report = {"tool": subprocess.run([ns.openscad, "--version"], capture_output=True, text=True).stderr.strip(),
              "trimesh": trimesh.__version__, "parts": {}, "physical_fit_tested": False,
              "source_sha256": hashlib.sha256((MECH/'enclosure.scad').read_bytes()).hexdigest()}
    logs = []
    for part in ("base", "lid", "speaker_clamp"):
        target = MECH / "stl" / f"{part}.stl"
        cmd = [ns.openscad, "-o", str(target), "-D", f'part="{part}"', str(MECH / "enclosure.scad")]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        logs.append(f"$ {' '.join(cmd)}\n{proc.stdout}{proc.stderr}\nexit={proc.returncode}\n")
        if proc.returncode or "ERROR:" in proc.stderr or not target.exists():
            raise RuntimeError(f"OpenSCAD export failed: {part}\n{proc.stderr}")
        mesh = trimesh.load_mesh(target, process=True)
        components = len(mesh.split(only_watertight=False))
        checks = {
            "watertight": bool(mesh.is_watertight), "consistent_winding": bool(mesh.is_winding_consistent),
            "positive_volume": bool(mesh.volume > 0), "one_connected_solid": components == 1,
            "on_print_bed": abs(float(mesh.bounds[0, 2])) < 0.001,
        }
        report["parts"][part] = {"checks": checks, "triangles": len(mesh.faces),
            "volume_mm3": round(float(mesh.volume), 3), "bounds_mm": mesh.bounds.tolist(), "components": components,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    with tempfile.TemporaryDirectory(prefix='mesa-fit-') as td:
        target = pathlib.Path(td)/'collision.stl'
        proc = subprocess.run([ns.openscad, '-o', str(target), '-D', 'part="fitcheck"', str(MECH/'enclosure.scad')],
                              capture_output=True, text=True, timeout=240)
        logs.append(f'FITCHECK\n{proc.stdout}{proc.stderr}\nexit={proc.returncode}\n')
        # OpenSCAD returns 1 for a deliberately empty intersection, but also for
        # errors. Accept only its explicit empty-geometry message with no ERROR.
        clear = ('Current top level object is empty.' in proc.stderr and 'ERROR:' not in proc.stderr)
        volume = float(trimesh.load_mesh(target).volume) if target.exists() and target.stat().st_size else None
        report['nominal_component_fit'] = {'passed': clear, 'intersection_volume_mm3': volume,
            'scope': 'Component bounding volumes vs case, USB plug vs base, PCB screw heads vs modules',
            'limitations': 'Nominal envelope check; excludes flexible wiring, exact component tolerances and acoustics'}
    report["passed"] = all(all(p["checks"].values()) for p in report["parts"].values()) and clear
    (ROOT / "validation").mkdir(exist_ok=True)
    (ROOT / "validation" / "mechanical-meshes.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    (ROOT / "validation" / "mechanical-openscad.log").write_text("\n".join(logs), encoding="utf-8")
    if ns.render:
        for part in ("exploded", "base", "lid"):
            subprocess.run([ns.openscad, "-o", str(MECH / f"{part}.png"), "--imgsize=1400,1000",
                "--viewall", "--autocenter", "--projection=o", "-D", f'part="{part}"', str(MECH/"enclosure.scad")], check=True, timeout=120)
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
