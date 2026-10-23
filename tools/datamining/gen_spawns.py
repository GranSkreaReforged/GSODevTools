"""Build GSOOffline's src/GSOOffline/Data/spawns.json: the original server's NPC and harvestable spawns the client's
scene markers lack.

GSOOffline populates each scene from the Scr_NPCDummy / Scr_HarvestableDummy markers the client ships (the final,
2020 state of the game) plus content.json's hand-placed NPCs. The original server's npcData_<scene> and
harvestableData_<scene> files (its develop branch, which matches the client's markers almost everywhere) list what
it spawned. Where a marker of the same type is
nearby the client is trusted (2020 moves stay). An NPC is taken from the original only when its scene has no
marker or content.json spawn of that type at all (creatures wander, and 2020 rearranged some herds); a harvestable
when no marker of its type is within NODE_RANGE metres (nodes stay put: Deepheart's mines have no markers, while
trees moved a few metres in 2020 stay where the client has them). Marker levels are build
indices, mapped to scene ids through extracted/scenes.txt (next to markers.json). Scene 6 is the developers' test scene.

Usage:
  python -I gen_spawns.py <XMLs folder> <markers.json> <content.json> <spawns.json>
  e.g. gen_spawns.py ../UpdatedOldServerArchive/Server/Assets/Resources/XMLs extracted/markers.json ../GSOOffline/src/GSOOffline/Data/content.json ../GSOOffline/src/GSOOffline/Data/spawns.json
"""
import collections
import json
import math
import pathlib
import re
import sys

SKIP_SCENES = {6}
NODE_RANGE = 50.0
# Deepheart (scene 38) ore the 2020 client buried in rock (about 2 m under its surface; GSOOffline's `spawnground`
# dev command found them, and standing there puts the camera inside the rock): (x, z), left out.
BURIED = {38: {
    (-133.7, 136.6), (-132.6, 152.7), (-123.0, 150.5), (-122.4, 136.6), (-115.9, 137.0), (-89.2, 151.0),
    (-85.4, 152.6), (-84.4, 167.4), (-75.8, 166.9), (-71.4, 178.6), (-67.1, 184.9), (-49.9, 151.6),
    (-44.4, 153.0), (-35.7, 167.8), (-29.9, 168.2), (609.6, -109.8), (614.2, -103.9), (616.1, -110.5),
    (873.9, -715.2), (882.2, -723.1), (976.1, -668.5),
}}


def vec(s):
    return [round(float(x), 2) for x in s.replace(" ", "").split(",")]


def original(xmls, kind):
    """{scene: [(type, pos)]}; a .txt file wins over an .xml one, as only one was loaded per scene."""
    base, tag = ("npcData_", "npc") if kind == "npc" else ("harvestableData_", "harvestable")
    out = {}
    for f in sorted(pathlib.Path(xmls).glob(base + "*.*"), key=lambda p: p.suffix != ".txt"):
        m = re.fullmatch(base + r"(\d+)\.(txt|xml)", f.name)
        if not m or int(m.group(1)) in out:
            continue
        out[int(m.group(1))] = [(int(t), vec(p)) for t, p in
                                re.findall(rf'<{tag} typeid="(\d+)"[^>]*pos="([^"]*)"', f.read_text(encoding="utf-8", errors="replace"))]
    return out


def scene_ids(markers_path):
    """Marker level (build index) -> the game's scene id, the number in the scene's file name (they differ from 36 on)."""
    ids = {}
    for line in (pathlib.Path(markers_path).parent / "scenes.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"(\d+) .*/Scene_(\d+)", line)
        if m:
            ids[int(m.group(1))] = int(m.group(2))
    return ids


def build(xmls, markers_path, content_path, out_path):
    markers = json.loads(pathlib.Path(markers_path).read_text(encoding="utf-8"))
    ids = scene_ids(markers_path)
    content = json.loads(pathlib.Path(content_path).read_text(encoding="utf-8"))
    have = collections.defaultdict(set)   # (kind, scene) -> types the client or content.json already spawns
    nodes = collections.defaultdict(list)   # (scene, type) -> harvestable marker positions
    for m in markers:
        scene = ids.get(m["level"], m["level"])
        if m["cls"] == "Scr_NPCDummy":
            have[("npc", scene)].add(m["typeId"])
        elif m["cls"] == "Scr_HarvestableDummy":
            nodes[(scene, m["typeId"])].append(m["pos"])
    for r in content["npcs"]:
        if r.get("scene") is not None and r.get("spawn"):
            have[("npc", r["scene"])].add(r["type"])
    result = {}
    for kind in ("npc", "harvestable"):
        rows = []
        for scene, spawns in sorted(original(xmls, kind).items()):
            if scene in SKIP_SCENES:
                continue
            if kind == "npc":
                rows += [{"type": t, "scene": scene, "pos": p} for t, p in spawns if t not in have[(kind, scene)]]
            else:
                rows += [{"type": t, "scene": scene, "pos": p} for t, p in spawns
                         if all(math.dist(p, q) > NODE_RANGE for q in nodes[(scene, t)])
                         and (p[0], p[2]) not in BURIED.get(scene, set())]
        result[kind + "s"] = rows
    lines = ["{",
             ' "source": "the original Gran Skrea Online server\'s npcData_<scene> and harvestableData_<scene> files (sent by the game\'s developer): the spawns the client has no markers for",',
             ' "generator": "GSODevTools tools/datamining/gen_spawns.py",']
    for kind in ("npcs", "harvestables"):
        rows = result[kind]
        lines.append(f' "{kind}": [')
        lines += ["  " + json.dumps(r) + ("," if i < len(rows) - 1 else "") for i, r in enumerate(rows)]
        lines.append(" ]" + ("," if kind == "npcs" else ""))
    lines.append("}")
    text = "\n".join(lines)
    json.loads(text)
    pathlib.Path(out_path).write_text(text + "\n", encoding="utf-8")
    for kind in ("npcs", "harvestables"):
        c = collections.Counter((r["scene"], r["type"]) for r in result[kind])
        print(f"{len(result[kind])} {kind}: " + ", ".join(f"scene {s} type {t} x{n}" for (s, t), n in sorted(c.items())))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    build(*sys.argv[1:])
