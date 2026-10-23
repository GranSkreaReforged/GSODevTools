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

# Where the original server put the player (Scr_InteractableHandler's forcePlayerPosition). Every typed door
# has one, so the guess above is only a fallback. Type 14's is where it led once quest 6 is done; during the
# quest, content.json's scene 5 triggers move the player on to the battle scenes, as the original's door did.
ORIGINAL_ARRIVALS = {
    # (fromType, fromLevel): toPos
    (9, 1): [0.8, 44.2, 3.18],          # into the Yorkhill mining cave
    (10, 2): [651.7, 16.0, 1441.3],     # out of it
    (11, 5): [556.3, 23.1, 1203.7],     # Roke's dungeon out to the ruins
    (12, 1): [442.5, 108.5, 1593.4],    # the ruins into Roke's dungeon
    (13, 5): [719.6, 33.9, 1566.2],     # Roke's dungeon up to the monastery
    (13, 11): [719.6, 33.9, 1566.2],
    (14, 1): [760.5, 131.4, 1860.4],    # the monastery hatch down to Roke's dungeon
    (15, 1): [482.5, 118.7, 1778.8],    # the forest into Roke's dungeon
    (16, 5): [505.2, 3.4, 1169.7],      # Roke's dungeon out to the forest
    (22, 1): [260.9, 17.5, 410.4],      # into the silk crab cave
    (23, 16): [485.5, 3.5, 1631.6],     # out of it
    (24, 1): [688.5, 33.7, 1551.3],     # into the Yorkhill monastery
    (25, 1): [664.7, 33.8, 1542.6],     # out of it
    (33, 8): [76.4, 70.3, 33.6],        # into Ulan's dungeon
    (34, 25): [880.9, 12.6, 1439.8],    # out of Ulan's dungeon
    (38, 26): [85.0, 16.6, -185.9],     # Cave Dragons back up to Ulan's dungeon
}

result = []
for ft, fl, tt, tl in MANUAL:
    src = [d for d in doors if d["typeId"] == ft and d["level"] == fl]
    dst = [d for d in doors if d["typeId"] == tt and d["level"] == tl]
    if not src or not dst:
        print("missing", ft, fl, tt, tl)
        continue
    for s in src:
        to = ORIGINAL_ARRIVALS.get((ft, fl)) or arrival(tl, dst[0]["pos"])
        result.append({"type": ft, "scene": fl, "pos": s["pos"], "toScene": tl,
                       "toPos": to, "note": dst[0]["goName"]})

# The Coral dungeon, from the original's house door table: the coral door in the silk crab cave (16) opens onto
# the dungeon's first hall (27), whose double door leads back out; its other double door goes up to the boss
# room (28) and back. The boss room's second door has no destination in the original: it stays locked.
CORAL_DOOR, CORAL_HALL, CORAL_UP, CORAL_BOSS = (80.39, 5.62, 72.69), (210.34, 157.0, 239.19), (19.39, 157.0, 21.05), (264.61, 208.19, 414.01)
for t, fs, fpos, ts, tpos, note in [(42, 16, CORAL_DOOR, 27, CORAL_HALL, "Coral dungeon"),
                                    (37, 27, CORAL_HALL, 16, CORAL_DOOR, "Coral dungeon (out)"),
                                    (37, 27, CORAL_UP, 28, CORAL_BOSS, "Coral dungeon boss room"),
                                    (37, 28, CORAL_BOSS, 27, CORAL_UP, "Coral dungeon boss room (out)")]:
    result.append({"type": t, "scene": fs, "pos": list(fpos), "toScene": ts, "toPos": arrival(ts, tpos), "note": note})

# The Snowy portal in Yorkhill takes the player to Ruteran (34), by the portal there (Scr_AbilitiesHandler's
# UsePortal; "portal" below); clicking that one (type 43, the original's default interactable 18) comes back.
SNOW_PORTAL = (-412.68, 51.08, -608.89)
result.append({"type": 43, "scene": 34, "pos": list(SNOW_PORTAL), "toScene": 8, "toPos": [960.0, 22.5, 1330.0],
               "note": "Snowy portal back to Yorkhill"})

# Two-way links through generic doors, gates, hatches and ladders (type 37), whose names carry no
# destination. Each side is (scene id, door marker, where a player stands to use it); going through one side
# lands on the other side's standing spot. Standing spots were recorded by a player (/pos) in front of each
# door. Scene ids are the game's (the file number), not marker levels: Scene_38PoacherDungeon is level 37.
LINKS = [
    ("poacher dungeon", (13, (1241.34, 19.8, 509.46), (1242.34, 19.9, 509.41)),
                        (38, (-149.64, 55.99, 142.1), (-151.15, 56.1, 141.76))),
    ("Yorkhill sewers", (8, (824.02, 17.75, 1341.73), (822.39, 17.91, 1342.83)),     # hatch
                        (4, (-85.65, 64.84, -14.82), (-83.91, 64.82, -13.21))),      # ladder
    ("Bir Amez crypts", (7, (1010.48, 6.81, -229.99), (1009.64, 5.68, -230.09)),
                        (29, (49.34, 200.66, -32.73), (49.88, 199.52, -32.69))),
    ("Bal Sardan town", (7, (817.92, 5.71, 477.62), (818.54, 5.72, 477.18)),
                        (31, (821.65, 5.71, 478.02), (821.01, 5.72, 476.55))),
]


def beyond(door, other, metres=2.5):
    """A spot `metres` past `door`, on the far side from `other` (the twin door on the other side of a wall)."""
    dx, dz = door[0] - other[0], door[2] - other[2]
    n = math.hypot(dx, dz) or 1.0
    return (round(door[0] + metres * dx / n, 2), door[1], round(door[2] + metres * dz / n, 2))


# Yorkhill's city gates: West Athagos (1) outside the walls, Yorkhill City (8) inside. Each gate is an
# interactable in both scenes, a few metres apart on either side of the wall, so the pair says which way is in.
for outer, inner in [((863.04, 17.37, 1306.42), (862.57, 17.57, 1309.83)),     # south
                     ((823.02, 10.54, 1433.96), (826.3, 10.74, 1433.23)),      # west, by the harbour
                     ((1006.15, 9.95, 1412.06), (1006.5, 10.2, 1408.92))]:     # north-east
    LINKS.append(("Yorkhill gate", (1, outer, beyond(outer, inner)), (8, inner, beyond(inner, outer))))
# Its south and south-east gates open onto East Athagos (13), not West Athagos: the original's "East Athagos -
# Yorkhill" doors. East Athagos also has a copy of the south-west gate, which led nowhere in the original.
for outer, inner in [((947.76, 21.26, 1303.66), (947.57, 20.9, 1306.42)),      # south
                     ((1097.19, 8.69, 1261.4), (1095.99, 9.09, 1264.94))]:     # south-east
    LINKS.append(("Yorkhill gate (East Athagos)", (13, outer, beyond(outer, inner)), (8, inner, beyond(inner, outer))))

for note, a, b in LINKS:
    for (fs, fpos, _), (ts, _, tstand) in ((a, b), (b, a)):
        result.append({"type": 37, "scene": fs, "pos": list(fpos), "toScene": ts,
                       "toPos": [tstand[0], round(tstand[1] + 0.5, 2), tstand[2]], "note": note})

# Inns (type 29). Without an entry here a type 29 door opens its scene's interior scene at the first room
# found; these pick the room. Each is (scene, door marker, interior scene, a point in the room by its exit).
INNS = [
    ("lighthouse inn", 1, (566.84, 11.83, 927.07), 23, (100.09, 101.91, 1.19)),   # the Innkeeper's room
    # Yorkhill's harbour inn: the only inn door on the harbour, present in both West Athagos and Yorkhill City
    # (the harbour is in both scenes); it gets the one unclaimed inn room, the Tavern keeper's.
    ("harbour inn", 1, (1023.58, 7.9, 1441.86), 20, (256.71, 100.17, 294.05)),
    ("harbour inn", 8, (1023.58, 7.9, 1441.86), 20, (256.71, 100.17, 294.05)),
]
for note, scene, door, room_scene, room in INNS:
    result.append({"type": 29, "scene": scene, "pos": list(door), "toScene": room_scene,
                   "toPos": arrival(room_scene, room), "note": note})

# The Mages Guild (21) behind the giant gate on East Athagos' west ridge (Arthos: "Head over to the west ridge and
# there you'll find a giant gate that leads to the Mages guild"). Outside it's a generic door (type 37), inside the
# guild's "Exit" (type 28), so the names don't pair; checked in-game, it's the same gate on both sides. A door entry
# for the exit also sends a player who came by wayshrine out of the gate, not to their home wayshrine.
MAGES_GATE, MAGES_EXIT = (830.92, 13.86, 1045.73), (226.81, 10.25, 114.01)
result.append({"type": 37, "scene": 13, "pos": list(MAGES_GATE), "toScene": 21, "toPos": [223.8, 10.5, 114.0],
               "note": "Mages Guild gate"})
result.append({"type": 28, "scene": 21, "pos": list(MAGES_EXIT), "toScene": 13, "toPos": [834.0, 14.36, 1045.73],
               "note": "Mages Guild gate (out)"})

# Deepheart (35) was never released, and every door there stays locked on purpose. markers.json has none of
# its doors (the extraction missed that scene's interactables; GSOOffline's `interactables 37` lists them
# live). Tried in-game and dropped: nothing ties its town's doors to the rooms of Scene_39DeepheartInteriors;
# its towers (a door at the foot, a hatch in the roof) let a player fall through the roof; its two tunnels
# lead to Scene_40DeepheartCave1, which is empty (no creatures, no resources) and drops you down a slope.

# Yorkhill's bank is a room under the city, in Yorkhill City itself; the door at the bottom of its stairs
# goes back up. From the original server's house door table, like the buildings below. Inside, face the
# banker; outside, the square (the guard on it).
LINKS.append(("Yorkhill bank", (8, (939.15, 21.5, 1355.87), (937.85, 21.5, 1358.0)),
                               (8, (954.05, 10.02, 848.98), (954.47, 10.02, 846.52))))
# The governor's room opens off the manor's hall, both in the interiors scene.
LINKS.append(("governor's room", (20, (1332.29, 107.29, 656.68), (1330.27, 107.29, 658.15)),
                                 (20, (1317.8, 107.17, 678.78), (1320.2, 107.17, 679.48))))

for note, a, b in LINKS[-2:]:
    for (fs, fpos, _), (ts, _, tstand) in ((a, b), (b, a)):
        result.append({"type": 37, "scene": fs, "pos": list(fpos), "toScene": ts,
                       "toPos": [tstand[0], round(tstand[1] + 0.5, 2), tstand[2]], "note": note})

# Yorkhill's shops and houses: generic doors (type 37) in Yorkhill City (8) and on the harbour (West
# Athagos, 1) open rooms in Scene_20YorkhillInteriors (20); Myra's hut and the Hunters Guild (East Athagos, 13) are
# in Athagos' interiors (23). The original's last door table also has a troll cave in East Athagos (for an
# unreleased quest, empty in the client) and a Poacher dungeon "tower" door with no door object; both are left out.
# Which door opens which room is the original server's house door table (Scr_InteractableHandler's
# SetupHouseDoors). Each room is (scene, exit door inside, a point in the room to face, or None to arrive
# at the door).
ROOMS = {
    "general":    (20, (828.24, 100.15, 1332.6), (823.95, 100.15, 1340.89)),  # general store, two doors
    "general_2":  (20, (821.04, 100.15, 1339.33), (823.95, 100.15, 1340.89)),
    "jeweller":   (20, (800.04, 114.4, 226.18),  (801.34, 114.55, 220.24)),
    "fineblades": (20, (1042.81, 100.15, 1333.71), (1043.15, 100.15, 1340.16)),  # weapons
    "gems":       (20, (924.26, 100.15, 1333.71), (924.6, 100.15, 1340.16)),
    "food":       (20, (845.04, 100.2, 1438.22), (851.36, 100.15, 1436.13)),  # food market, two doors
    "food_2":     (20, (857.42, 100.2, 1433.97), (851.36, 100.15, 1436.13)),
    "bows":       (20, (999.51, 15.83, 1610.02), (1002.63, 15.8, 1601.5)),
    "armor":      (20, (775.45, 117.75, -325.7), (774.07, 117.89, -334.69)),  # light, heavy armor and robes
    "surgeon":    (20, (1410.21, 121.14, -95.96), (1411.66, 121.1, -93.69)),  # appearance change
    "healer":     (20, (1615.2, 105.75, 561.73), (1617.46, 105.82, 555.27)),  # Valeria
    "manor":      (20, (1325.01, 107.28, 654.32), (1329.22, 107.28, 658.91)), # Lingard's kitchen
    "artisans":   (20, (479.07, 100.21, -289.38), (478.82, 100.13, -297.68)), # Percy Dyster, workbenches
    "library":    (20, (479.06, 100.16, -1.74),  (462.89, 100.16, -3.16)),    # Flora of Keshk (quest 26)
    "auction":    (20, (867.66, 98.53, 1130.38), (877.61, 97.35, 1144.54)),   # auction hall, entered by a gate
    "kombra":     (20, (199.07, 99.88, 1.65),   (199.64, 100.02, -6.25)),
    "ulan":       (20, (101.31, 99.94, 1.29),   (95.53, 100.08, -6.74)),      # Ulan at home
    # The harbour's. The original sent its bank door to a room the client's interiors scene no longer has;
    # the client's other bank room (banker, insurance advisor) is the one nothing else leads to.
    "harbour bank":     (20, (2288.04, 114.4, 168.7), (2289.0, 114.4, 162.91)),
    "harbour general":  (20, (727.5, 100.1, 1368.07), (725.95, 100.25, 1376.02)),  # two doors
    "harbour general_2": (20, (720.3, 100.1, 1374.8), (725.95, 100.25, 1376.02)),
    "harbour fish":     (20, (596.85, 100.06, 1414.02), (591.99, 100.2, 1413.15)),  # two doors
    "harbour fish_2":   (20, (589.65, 100.06, 1420.75), (591.99, 100.2, 1413.15)),
    "harbour tavern":   (20, (256.71, 100.17, 294.05), (260.27, 100.28, 297.24)),   # two doors
    "harbour tavern_2": (20, (267.76, 100.17, 290.41), (260.27, 100.28, 297.24)),
    "harbour tavern upstairs": (20, (267.76, 100.17, 222.79), None),
    "myra":       (23, (200.1, 100.16, 0.14),   (198.14, 100.28, 1.93)),
    # The Hunters Guild in East Athagos (Trout): the original's door needs the Porter's leave (unique requirement 2).
    "hunters guild": (23, (103.36, 139.37, 464.21), (108.0, 139.5, 447.0)),
}

# (scene, door marker position, room).
YORKHILL = [
    (8, (921.97, 21.37, 1354.14), "gems"),       # under the Bank sign, but the bank is the next door
    (8, (911.36, 21.39, 1367.57), "general"),
    (8, (897.74, 21.44, 1374.78), "general_2"),
    (8, (907.0, 21.06, 1387.16), "jeweller"),
    (8, (947.63, 21.59, 1359.46), "fineblades"),
    (8, (998.24, 15.71, 1366.26), "bows"),
    (8, (1010.5, 13.38, 1376.6), "armor"),
    (8, (966.67, 17.88, 1406.9), "artisans"),
    (8, (891.46, 21.39, 1341.48), "auction"),     # a gate
    (8, (879.35, 21.54, 1362.44), "library"),
    (8, (929.41, 21.32, 1391.43), "manor"),
    (8, (933.32, 18.08, 1431.42), "healer"),
    (8, (848.73, 18.81, 1348.19), "food"),
    (8, (829.54, 18.75, 1350.2), "food_2"),
    (8, (982.33, 20.94, 1338.45), "surgeon"),
    (8, (851.93, 18.78, 1322.7), "kombra"),
    (8, (863.54, 10.75, 1425.0), "ulan"),
    (1, (983.69, 6.49, 1462.26), "harbour bank"),
    (1, (976.93, 6.49, 1485.46), "harbour general"),
    (1, (961.45, 6.49, 1485.55), "harbour general_2"),
    (1, (992.05, 6.56, 1508.77), "harbour fish"),
    (1, (978.63, 6.56, 1516.18), "harbour fish_2"),
    (1, (955.83, 6.57, 1514.18), "harbour tavern"),
    (1, (974.84, 6.57, 1509.54), "harbour tavern_2"),
    # The original gave the upstairs room the fish store's door (so it never opened); the only door frame
    # left on the tavern is the upper one.
    (1, (964.94, 10.52, 1506.91), "harbour tavern upstairs"),
    (1, (451.34, 14.35, 1373.73), "myra"),
    (13, (1447.5, 18.13, 869.8), "hunters guild"),
]


def inward(door, toward, metres=2.5):
    if toward is None:
        return [door[0], round(door[1] + 0.5, 2), door[2]]
    dx, dz = toward[0] - door[0], toward[2] - door[2]
    n = math.hypot(dx, dz) or 1.0
    return [round(door[0] + metres * dx / n, 2), round(door[1] + 0.5, 2), round(door[2] + metres * dz / n, 2)]


buildings = [{"scene": scene, "pos": list(pos), "toScene": ROOMS[room][0], "toPos": inward(*ROOMS[room][1:]),
              "note": room} for scene, pos, room in YORKHILL]
# Yorkhill's Hall of Heroes, entered through the door under its sign. Its markers are level 36 (build
# order) but the game's scene id is the file's number, Scene_37YorkhillHallOfFame: 37.
# Arrive where the original put players, by its gate.
buildings.append({"scene": 8, "pos": [938.8, 22.72, 1377.44], "toScene": 37,
                  "toPos": [30.25, 14.9, 111.2], "note": "hall of heroes"})

# The rat cellar (quest 27) opens off Lingard's kitchen in the manor, through door frames (type 43).
CELLAR_KITCHEN, CELLAR = (1320.26, 107.28, 659.07), (1099.51, 121.18, 786.47)
result.append({"type": 43, "scene": 20, "pos": list(CELLAR_KITCHEN), "toScene": 20,
               "toPos": inward(CELLAR, (1115.16, 119.71, 765.0)), "note": "rat cellar"})
for d in doors:
    if d["level"] == 20 and d["typeId"] == 43 and "DoorFrame" in d["goName"] and d["pos"][1] > 120:
        result.append({"type": 43, "scene": 20, "pos": d["pos"], "toScene": 20,
                       "toPos": inward(CELLAR_KITCHEN, ROOMS["manor"][2]), "note": "manor kitchen"})

json.dump({"doors": result,
           # generic doors (type 37) into rooms; any type 37 door in the room scene leads back out
           "buildings": buildings,
           # building door scene -> interior scene (type 29 in, type 28 out). Yorkhill City's other type 29
           # doors aren't in the original's table: they stay locked.
           "interiors": [{"scene": 1, "interior": 23}, {"scene": 21, "interior": 22}],
           # interior exits for each interior scene (arrival spots)
           "interiorSpawns": [{"scene": l, "pos": arrival(l, d["pos"])}
                              for d in doors if d["typeId"] == 28 for l in [d["level"]]],
           "portal": {"scene": 34, "pos": [-412.0, 50.5, -609.0]}},   # the original's landing spot
          open(out_path, "w", encoding="utf-8"), indent=1)
print(len(result), "door links written")
