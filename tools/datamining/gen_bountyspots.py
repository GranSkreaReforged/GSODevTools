"""Build GSOOffline's src/GSOOffline/Data/bountyspots.json: where bounty-board targets can wait (GSOOffline #67).

A spot is a group of hostile creatures in an open-world zone, from the client's scene markers (extracted/markers.json)
and the original server's extra spawns (GSOOffline's Data/spawns.json). Each spot records the creatures' level range,
so a bounty only waits among creatures near its own level. Spots near a boss, a house plot or town guards are left
out. Each also names a landmark (a wayshrine or an entrance to another area), with the distance and direction from it,
for the board's "last seen" line.

Usage:
  python -I gen_bountyspots.py <extracted> <GSOOffline Data dir>
  e.g. gen_bountyspots.py extracted ../GSOOffline/src/GSOOffline/Data
"""
import json
import math
import pathlib
import re
import statistics
import sys

# Deepheart (35) is left out: it was never released, and GSOOffline keeps its doors locked.
ZONES = {1: "West Athagos", 7: "Bal Sardan", 13: "East Athagos", 18: "Goldon", 19: "The Blue Sea", 34: "Ruteran"}
SPOT_RADIUS = 35.0        # creatures this close belong to one spot
BOSS_CLEARANCE = 120.0
HOUSE_CLEARANCE = 50.0
GUARD_CLEARANCE = 60.0
MIN_CREATURES = 1
UNFLAGGED_BOSSES = {358}   # Argus: a boss GSOOffline's GameData.UnflaggedBosses knows, without boss="1"

# Entrances worth naming, by the scene they lead to (doors.json toScene).
PLACES = {2: "the Yorkhill mining cave", 4: "the Yorkhill sewers", 5: "the Evil monk's dungeon", 8: "the Yorkhill city gate",
          16: "the Silk crab cave", 21: "the Mages' guild", 25: "Ulan's dungeon", 27: "the Coral cave", 29: "the Sardanian dungeon",
          31: "Bal Sardan town", 32: "Lakhmu's dungeon", 38: "the Poacher dungeon", 40: "the Deepheart cave"}


def attrs(s):
    return dict(re.findall(r'(\w+)="([^"]*)"', s))


def compass(dx, dz):
    a = (math.degrees(math.atan2(dx, dz)) + 360) % 360   # 0 = north (+z), 90 = east (+x)
    return ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"][int((a + 22.5) // 45) % 8]


def build(extracted, data_dir):
    extracted, data_dir = pathlib.Path(extracted), pathlib.Path(data_dir)
    npcs = {}
    for m in re.finditer(r"<npc ([^>]*)>", (extracted / "textassets" / "NPCInfo.txt").read_text(encoding="utf-8", errors="replace")):
        a = attrs(m.group(1))
        if "id" in a:
            npcs[int(a["id"])] = a
    spawns = []   # (scene, typeId, x, y, z)
    for m in json.loads((extracted / "markers.json").read_text(encoding="utf-8")):
        if m.get("cls") == "Scr_NPCDummy" and m.get("level") in ZONES:
            spawns.append((m["level"], m["typeId"], *m["pos"]))
    for s in json.loads((data_dir / "spawns.json").read_text(encoding="utf-8"))["npcs"]:
        if s["scene"] in ZONES:
            spawns.append((s["scene"], s["type"], *s["pos"]))
    # Bosses and quest NPCs content.json places where the scene has no marker.
    for r in json.loads((data_dir / "content.json").read_text(encoding="utf-8")).get("npcs", []):
        for p in r.get("spawn") or []:
            if r.get("scene") in ZONES:
                spawns.append((r["scene"], r["type"], *(float(v) for v in p.split(","))))

    def info(t):
        return npcs.get(t, {})

    def hostile(t):
        a = info(t)
        return a.get("aggressive") == "1" and a.get("canfight") == "1" and int(a.get("level", "0") or 0) > 0

    bosses = [s for s in spawns if info(s[1]).get("boss") == "1" or s[1] in UNFLAGGED_BOSSES]
    guards = [s for s in spawns if "guard" in info(s[1]).get("name", "").lower()]
    creatures = [s for s in spawns if hostile(s[1]) and s not in bosses and s not in guards]
    plots = [p for p in json.loads((data_dir / "houseplots.json").read_text(encoding="utf-8"))["plots"] if p["scene"] in ZONES]

    landmarks = []   # (scene, name, x, z)
    for m in re.finditer(r"<wayshrine ([^>]*)>", (extracted / "textassets" / "Wayshrines.txt").read_text(encoding="utf-8")):
        a = attrs(m.group(1))
        sc = int(a["scene"])
        if sc in ZONES:
            x, _, z = (float(v) for v in a["pos"].split(","))
            landmarks.append((sc, "the " + a["name"] + " wayshrine", x, z))
    for d in json.loads((data_dir / "doors.json").read_text(encoding="utf-8"))["doors"]:
        if d["scene"] in ZONES and d.get("toScene") in PLACES:
            landmarks.append((d["scene"], PLACES[d["toScene"]], d["pos"][0], d["pos"][2]))

    def dist2(ax, az, bx, bz):
        return math.hypot(ax - bx, az - bz)

    centres = []
    for c in sorted(creatures, key=lambda s: (s[0], s[2], s[4])):
        if not any(sc == c[0] and dist2(x, z, c[2], c[4]) < SPOT_RADIUS for sc, x, y, z in centres):
            centres.append((c[0], c[2], c[3], c[4]))

    spots, skipped = [], {"boss": 0, "house": 0, "guard": 0, "few": 0, "landmark": 0}
    for sc, x, y, z in centres:
        near = [c for c in creatures if c[0] == sc and dist2(x, z, c[2], c[4]) < SPOT_RADIUS]
        if len(near) < MIN_CREATURES:
            skipped["few"] += 1
            continue
        if any(b[0] == sc and dist2(x, z, b[2], b[4]) < BOSS_CLEARANCE for b in bosses):
            skipped["boss"] += 1
            continue
        if any(g[0] == sc and dist2(x, z, g[2], g[4]) < GUARD_CLEARANCE for g in guards):
            skipped["guard"] += 1
            continue
        if any(p["scene"] == sc and dist2(x, z, p["pos"][0] + p["size"][0] / 2, p["pos"][2] + p["size"][1] / 2) < HOUSE_CLEARANCE for p in plots):
            skipped["house"] += 1
            continue
        lm = [l for l in landmarks if l[0] == sc]
        if not lm:
            skipped["landmark"] += 1
            continue
        best = min(lm, key=lambda l: dist2(l[2], l[3], x, z))
        levels = [int(info(c[1])["level"]) for c in near]
        names = {}
        for c in near:
            n = info(c[1]).get("name", "?")
            names[n] = names.get(n, 0) + 1
        top = [n for n, _ in sorted(names.items(), key=lambda kv: -kv[1])][:2]
        spots.append({
            "scene": sc, "zone": ZONES[sc], "pos": [round(x, 1), round(y, 1), round(z, 1)],
            "level": int(statistics.median(levels)), "minLevel": min(levels), "maxLevel": max(levels),
            "creatures": top, "landmark": best[1], "distance": int(round(dist2(best[2], best[3], x, z), -1)),
            "direction": compass(x - best[2], z - best[3]),
        })
    out = {
        "source": "the client's scene markers and the original server's spawns (GSOOffline Data/spawns.json), with NPCInfo levels",
        "generator": "GSODevTools tools/datamining/gen_bountyspots.py",
        "spots": spots,
    }
    (data_dir / "bountyspots.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"{len(spots)} spots from {len(creatures)} creatures; left out: {skipped}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
