"""Build GSOOffline's src/GSOOffline/Data/doors.json from extracted/markers.json.

The old server mapped each door interactable to a destination; that table is lost. The scene
objects are named after their role ("Interactable_9EntranceToYorkhillMiningCave" /
"Interactable_10ExitFromYorkhillMiningCave"), so pairs are rebuilt from the names. Arrival points sit
a couple of metres off the destination door, toward where the rest of that scene's markers are
(i.e. into the walkable area rather than into the wall). That guess is only a starting point: GSOOffline
moves each arrival to clear ground in-game (OfflineServer.Arrival.cs), since some guesses land behind rocks.

Usage: python -I gen_doors.py <markers.json> <doors.json>
  e.g. gen_doors.py extracted/markers.json ../GSOOffline/src/GSOOffline/Data/doors.json
"""
import json, math, re, sys

markers = json.load(open(sys.argv[1], encoding="utf-8"))
out_path = sys.argv[2]

doors = [m for m in markers if m["cls"] == "Scr_Interactable" and m["pos"]]
by_level = {}
for m in markers:
    if m["pos"]:
        by_level.setdefault(m["level"], []).append(m["pos"])


def arrival(level, pos):
    near = [p for p in by_level.get(level, []) if 1.0 < math.dist(p, pos) < 40.0]
    if not near:
        return [round(pos[0], 2), round(pos[1] + 0.5, 2), round(pos[2], 2)]
    cx = sum(p[0] for p in near) / len(near) - pos[0]
    cz = sum(p[2] for p in near) / len(near) - pos[2]
    n = math.hypot(cx, cz) or 1.0
    return [round(pos[0] + 2.0 * cx / n, 2), round(pos[1] + 0.5, 2), round(pos[2] + 2.0 * cz / n, 2)]


NAME = re.compile(r"Interactable_(\d+)_?(Entrance|Exit)(?:To|From)?(\w+?)(?:To\w+|From\w+)?(?:\s*\(\d+\))?$")


def key(goname):
    m = NAME.search(goname or "")
    if not m:
        return None
    return m.group(2), m.group(3).replace("Entrance", "")


# Explicit pairings where names differ between the two sides (verified by hand against the markers).
MANUAL = [
    # (fromType, fromLevel, toType, toLevel)
    (9, 1, 10, 2), (10, 2, 9, 1),                 # Yorkhill mining cave
    (12, 1, 11, 5), (11, 5, 12, 1),               # Evil monk dungeon
    (15, 1, 16, 5), (16, 5, 15, 1),               # Roke dungeon <-> forest
    (14, 1, 13, 5), (13, 5, 14, 1), (13, 11, 14, 1),   # Roke dungeon <-> monastery hatch
    (22, 1, 23, 16), (23, 16, 22, 1),             # Silk crab cave
    (24, 1, 25, 1), (25, 1, 24, 1),               # Yorkhill monastery (same scene)
    (33, 8, 34, 25), (34, 25, 33, 8),             # Ulan's dungeon
    (35, 25, 38, 26), (38, 26, 35, 25),           # Ulan's 2nd floor
]

result = []
for ft, fl, tt, tl in MANUAL:
    src = [d for d in doors if d["typeId"] == ft and d["level"] == fl]
    dst = [d for d in doors if d["typeId"] == tt and d["level"] == tl]
    if not src or not dst:
        print("missing", ft, fl, tt, tl)
        continue
    for s in src:
        result.append({"type": ft, "scene": fl, "pos": s["pos"], "toScene": tl,
                       "toPos": arrival(tl, dst[0]["pos"]), "note": dst[0]["goName"]})

# Doors into a whole scene without a matching exit door: arrive at that scene's first marker cluster.
def scene_entry(level):
    pts = by_level.get(level, [])
    return arrival(level, pts[0]) if pts else [0, 50, 0]

for d in doors:
    if d["typeId"] == 42 and d["level"] == 16:   # Coral dungeon entrance
        result.append({"type": 42, "scene": 16, "pos": d["pos"], "toScene": 27, "toPos": scene_entry(27), "note": "Coral dungeon"})

# Yorkhill's shops and houses: generic doors (type 37) in Yorkhill City (8) open rooms laid out in
# Scene_20YorkhillInteriors (20). Each room is (exit door inside, a point in the room to face). The
# shop signs (Prefab_Object_Sign_*, see GSOOffline's `doorsigns` bridge command) name the building of
# most doors; quest texts place the manor, Valeria's shop and the library. Doors marked "guess" have no
# sign: they got the rooms left over, by what's around them.
ROOMS = {
    "bank":       ((2288.04, 114.4, 168.7),  (2289.0, 114.4, 162.91)),    # banker, insurance advisor
    "general":    ((828.24, 100.15, 1332.6), (823.95, 100.15, 1340.89)),  # general store
    "general2":   ((727.5, 100.1, 1368.07),  (725.95, 100.25, 1376.02)),  # another general store
    "jeweller":   ((800.04, 114.4, 226.18),  (801.34, 114.55, 220.24)),
    "fineblades": ((1042.81, 100.15, 1333.71), (1043.15, 100.15, 1340.16)),  # weapons
    "gems":       ((924.26, 100.15, 1333.71), (924.6, 100.15, 1340.16)),
    "food":       ((857.42, 100.2, 1433.97), (851.36, 100.15, 1436.13)),
    "fish":       ((596.85, 100.06, 1414.02), (591.99, 100.2, 1413.15)),  # harbor fish store
    "bows":       ((999.51, 15.83, 1610.02), (1002.63, 15.8, 1601.5)),
    "armor":      ((775.45, 117.75, -325.7), (774.07, 117.89, -334.69)),  # light, heavy armor and robes
    "surgeon":    ((1410.21, 121.14, -95.96), (1411.66, 121.1, -93.69)),
    "healer":     ((1615.2, 105.75, 561.73), (1617.46, 105.82, 555.27)),  # Valeria
    "manor":      ((1325.01, 107.28, 654.32), (1329.22, 107.28, 658.91)), # Lingard's kitchen, the governor
    "tavern":     ((256.71, 100.17, 294.05), (260.27, 100.28, 297.24)),
    "artisans":   ((479.07, 100.21, -289.38), (478.82, 100.13, -297.68)), # Percy Dyster, workbenches
    "library":    ((479.06, 100.16, -1.74),  (462.89, 100.16, -3.16)),    # Flora of Keshk (quest 26)
    "auction":    ((867.66, 98.53, 1130.38), (877.61, 97.35, 1144.54)),   # auction hall, entered by a gate
}

# Yorkhill City door (marker position) -> room.
YORKHILL = [
    ((922.0, 21.37, 1354.14), "bank"),        # sign Bank
    ((911.36, 21.39, 1367.57), "general"),    # sign Generalstore
    ((907.0, 21.06, 1387.16), "jeweller"),    # sign Jeweller
    ((947.63, 21.59, 1359.46), "fineblades"), # sign Blacksmithy
    ((998.24, 15.71, 1366.26), "bows"),       # sign Archery store
    ((1010.5, 13.38, 1376.6), "armor"),       # sign Clothing store
    ((966.67, 17.88, 1406.9), "artisans"),    # sign ArtisansGuild
    ((891.46, 21.39, 1341.48), "auction"),    # sign AuctionHouse (a gate)
    ((879.35, 21.54, 1362.44), "library"),    # sign Library
    ((929.41, 21.32, 1391.43), "manor"),      # Door_manor
    ((933.32, 18.08, 1431.42), "healer"),     # Door_manor (1): "her shop is located behind the governor's manor"
    ((939.15, 21.5, 1355.87), "gems"),        # guess: on the square, between the bank and the blacksmith
    ((863.54, 10.75, 1425.0), "fish"),        # guess: down by the harbour
    ((848.73, 18.81, 1348.19), "food"),       # guess
    ((829.54, 18.75, 1350.2), "general2"),    # guess
    ((851.93, 18.78, 1322.7), "surgeon"),     # guess
    ((897.74, 21.44, 1374.78), "tavern"),     # guess
]


def inward(door, toward, metres=2.5):
    dx, dz = toward[0] - door[0], toward[2] - door[2]
    n = math.hypot(dx, dz) or 1.0
    return [round(door[0] + metres * dx / n, 2), round(door[1] + 0.5, 2), round(door[2] + metres * dz / n, 2)]


buildings = [{"scene": 8, "pos": list(pos), "toScene": 20, "toPos": inward(*ROOMS[room]), "note": room}
             for pos, room in YORKHILL]
# Yorkhill's Hall of Heroes, entered through the door under its sign. Its markers are level 36 (build
# order) but the game's scene id is the file's number, Scene_37YorkhillHallOfFame: 37.
hall = [d for d in doors if d["level"] == 36 and d["typeId"] == 37]
if hall:
    buildings.append({"scene": 8, "pos": [938.8, 22.72, 1377.44], "toScene": 37,
                      "toPos": arrival(36, hall[0]["pos"]), "note": "hall of heroes"})

# The rat cellar (quest 27) opens off Lingard's kitchen in the manor, through door frames (type 43).
CELLAR_KITCHEN, CELLAR = (1320.26, 107.28, 659.07), (1099.51, 121.18, 786.47)
result.append({"type": 43, "scene": 20, "pos": list(CELLAR_KITCHEN), "toScene": 20,
               "toPos": inward(CELLAR, (1115.16, 119.71, 765.0)), "note": "rat cellar"})
for d in doors:
    if d["level"] == 20 and d["typeId"] == 43 and "DoorFrame" in d["goName"] and d["pos"][1] > 120:
        result.append({"type": 43, "scene": 20, "pos": d["pos"], "toScene": 20,
                       "toPos": inward(CELLAR_KITCHEN, ROOMS["manor"][1]), "note": "manor kitchen"})

json.dump({"doors": result,
           # generic doors (type 37) into rooms; any type 37 door in the room scene leads back out
           "buildings": buildings,
           # building door scene -> interior scene (type 29 in, type 28 out)
           "interiors": [{"scene": 1, "interior": 23}, {"scene": 8, "interior": 20}, {"scene": 21, "interior": 22}],
           # interior exits for each interior scene (arrival spots)
           "interiorSpawns": [{"scene": l, "pos": arrival(l, d["pos"])}
                              for d in doors if d["typeId"] == 28 for l in [d["level"]]],
           "portal": {"scene": 34, "pos": scene_entry(34)}},
          open(out_path, "w", encoding="utf-8"), indent=1)
print(len(result), "door links written")
