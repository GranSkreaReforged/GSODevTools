"""Build GSOOffline's src/GSOOffline/Data/houseplots.json from the original server's HousePlots_<scene> files.

The original server (its develop branch, sent by the game's developer) kept one plot list per scene in Resources/XMLs,
as HousePlots_<scene>.xml or .txt (same XML inside). Scene 13 has both: the .txt is the full list and the .xml an
older subset, so a .txt wins over an .xml of the same scene. A plot's pos is its corner (lowest x and z); the
house stands at pos + size / 2. Plot ids are per scene.

Usage:
  python -I gen_houseplots.py <XMLs dir> <houseplots.json>
  e.g. gen_houseplots.py ../UpdatedOldServerArchive/Server/Assets/Resources/XMLs ../GSOOffline/src/GSOOffline/Data/houseplots.json
"""
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET


def build(xml_dir, out_path):
    files = {}
    for f in sorted(pathlib.Path(xml_dir).glob("HousePlots_*")):
        m = re.fullmatch(r"HousePlots_(\d+)\.(xml|txt)", f.name)
        if not m:
            continue
        scene = int(m.group(1))
        if scene in files and files[scene].suffix == ".txt":
            continue
        files[scene] = f
    plots = []
    for scene, f in sorted(files.items()):
        root = ET.fromstring(f.read_text(encoding="utf-8-sig", errors="replace"))
        for p in root.findall("plot"):
            if int(p.get("scene")) != scene:
                sys.exit(f"{f.name}: plot {p.get('id')} says scene {p.get('scene')}")
            sx, sz = (float(v) for v in p.get("size").split(","))
            x, y, z = (float(v) for v in p.get("pos").split(","))
            plots.append({"scene": scene, "id": int(p.get("id")), "size": [sx, sz], "pos": [x, y, z]})
    seen = set()
    for p in plots:
        key = (p["scene"], p["id"])
        if key in seen:
            sys.exit(f"duplicate plot {key}")
        seen.add(key)
    out = {
        "source": "the original Gran Skrea Online server's Resources/XMLs/HousePlots_<scene> (sent by the game's developer)",
        "generator": "GSODevTools tools/datamining/gen_houseplots.py",
        "plots": plots,
    }
    pathlib.Path(out_path).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"{len(plots)} plots in {len(files)} scenes -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
