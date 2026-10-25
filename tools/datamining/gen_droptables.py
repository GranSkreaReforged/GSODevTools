"""Build GSOOffline's src/GSOOffline/Data/droptables.json from the original server's Loot.xml and NPCInfo.xml.

The game's developer sent the original server; its Loot.xml holds the real drop tables (the develop-branch
snapshot in UpdatedOldServerArchive, which has everything the final client has). Each table lists NPC type ids and drops; the server rolled every drop on its own,
1 in `rate`, with an amount from minamount to maxamount (default 1). Item 0 is silver. The NPC ids in the
original NPCInfo.xml are written out too: an NPC the original knew but gave no table dropped nothing from one,
while NPCs added after the snapshot keep GSOOffline's wiki tables (loot.json).

Corrections on top: NPCID_FIXES mends a table filed under the wrong NPC and MADE_UP adds tables for bosses the
original gave none (named "(made up)" so they're never taken for the original's) (GSOOffline #116); ADDED_DROPS
gives items the original only handed out for titles a drop on an existing table (#125).

Usage:
  python -I gen_droptables.py <XMLs folder> <textassets> <droptables.json>
  e.g. gen_droptables.py ../UpdatedOldServerArchive/Server/Assets/Resources/XMLs extracted/textassets ../GSOOffline/src/GSOOffline/Data/droptables.json
"""
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET


# Tables Loot.xml files under the wrong NPC, by table name: (npc ids written, npc ids meant).
NPCID_FIXES = {
    # Filed under 297, the Elder Cave Dragon's id, so the dragons rolled the ghosts' drops and the ghosts (298) none.
    "Poacher dungeon aggressive ghost lvl 70": ([297], [298]),
}

# What every big boss's table ends with (Nirish, the Dark Tamer, the Supreme sea serpent): silver, an experience
# scroll, the salvation potions, teleport scrolls and potions. (item, rate, min, max)
BOSS_COMMON = [
    (0, 1, 200, 350), (10329, 20, 1, 1),
    (10640, 30, 1, 1), (10641, 150, 1, 1), (10639, 150, 1, 1), (10501, 150, 1, 1),
    (10395, 10, 1, 1), (10486, 10, 1, 1), (10465, 10, 1, 1), (10532, 10, 1, 1), (10472, 20, 1, 1),
    (10388, 30, 1, 1), (10390, 30, 1, 1), (10464, 30, 1, 1), (10389, 40, 1, 1), (10531, 50, 1, 1), (10538, 50, 1, 1),
    (10446, 10, 1, 1), (10447, 20, 1, 1), (10448, 30, 1, 1), (10069, 10, 1, 1), (10454, 10, 1, 1), (10456, 30, 1, 1),
    (10488, 15, 1, 1), (10483, 200, 1, 1), (10484, 200, 1, 1), (10485, 200, 1, 1),
]

# Bosses the original server gave no table (they dropped nothing), with tables made up from their neighbours'.
MADE_UP = [
    # Champion of the Cave Dragons (level 90): the Elder Cave Dragon's materials and shadow armour, and his own
    # tooth far more often than the Dark Tamer's 1 in 150.
    ([293], "Sytrax (made up: the original had no table)", BOSS_COMMON + [
        (10412, 2, 1, 6), (10420, 2, 1, 3), (10554, 8, 1, 2), (10418, 2, 1, 2), (10416, 1, 1, 2),
        (10250, 1, 3, 5), (10264, 4, 1, 1),
        (314, 10, 1, 1), (315, 10, 1, 1), (310, 15, 1, 1), (311, 15, 1, 1), (308, 15, 1, 1),
        (10753, 25, 1, 1), (10512, 30, 1, 1),
    ]),
    # The Keshk raid's snake (level 90): poison, serpent meat and scales, Nirish's venomous jewellery, and the
    # Snakeling pet the Supreme sea serpent drops.
    ([263], "Viper (made up: the original had no table)", BOSS_COMMON + [
        (10536, 1, 1, 4), (10413, 2, 1, 3), (10377, 2, 1, 5), (10433, 10, 1, 1),
        (10418, 3, 1, 2), (10416, 2, 1, 2),
        (405, 75, 1, 1), (406, 75, 1, 1), (469, 750, 1, 1),
    ]),
]


# Drops added to the original's tables, by table name: (item, rate, min, max). The original gave the mitres with
# the Bishop and Magus titles, which need PvP honor and darkness; offline they drop from the bosses that fit.
ADDED_DROPS = {
    "Elder Ent": [(419, 150, 1, 1)],   # Bishop's mitre
    "Zalranaz": [(421, 150, 1, 1)],    # Dark mitre
}


def load_items(textassets):
    text = (pathlib.Path(textassets) / "items.txt").read_text(encoding="utf-8", errors="replace")
    names = {}
    for m in re.finditer(r"<item ([^>]*)>", text):
        tid = re.search(r'TypeId="(\d+)"', m.group(1))
        name = re.search(r'Name="([^"]*)"', m.group(1))
        if tid:
            names[int(tid.group(1))] = name.group(1).strip() if name else ""
    return names


def build(xmls, textassets, out_path):
    xmls = pathlib.Path(xmls)
    names = load_items(textassets)
    # Some name attributes have a stray space before = ('name = "..."'); ElementTree accepts it.
    root = ET.fromstring((xmls / "Loot.xml").read_text(encoding="utf-8", errors="replace"))
    tables, unknown = [], []
    for t in root.findall("table"):
        entry = {"npcs": [int(s) for s in t.get("npcid").split(",") if s.strip()], "name": (t.get("name") or "").strip(), "drops": []}
        for d in t.findall("drop"):
            tid = int(d.get("item"))
            if tid != 0 and tid not in names:
                unknown.append((entry["name"], tid))
                continue
            entry["drops"].append({
                "typeId": tid,
                "name": "silver" if tid == 0 else names[tid],
                "rate": int(d.get("rate")),
                "min": int(d.get("minamount") or 1),
                "max": int(d.get("maxamount") or 1),
            })
        if entry["name"] in NPCID_FIXES:
            written, meant = NPCID_FIXES.pop(entry["name"])
            if entry["npcs"] != written:
                sys.exit(f"Loot.xml's '{entry['name']}' is for {entry['npcs']}, not {written}: check NPCID_FIXES")
            entry["npcs"] = meant
        for tid, rate, lo, hi in ADDED_DROPS.pop(entry["name"], []):
            if tid not in names:
                sys.exit(f"ADDED_DROPS: item {tid} isn't in the game's item data")
            entry["drops"].append({"typeId": tid, "name": names[tid], "rate": rate, "min": lo, "max": hi})
        tables.append(entry)
    if NPCID_FIXES:
        sys.exit(f"NPCID_FIXES names tables Loot.xml doesn't have: {list(NPCID_FIXES)}")
    if ADDED_DROPS:
        sys.exit(f"ADDED_DROPS names tables Loot.xml doesn't have: {list(ADDED_DROPS)}")
    covered = {n for t in tables for n in t["npcs"]}
    for npcs, name, drops in MADE_UP:
        if covered & set(npcs):
            sys.exit(f"{name}: Loot.xml has a table for {npcs} now; drop it from MADE_UP")
        for tid, *_ in drops:
            if tid != 0 and tid not in names:
                sys.exit(f"{name}: item {tid} isn't in the game's item data")
        tables.append({"npcs": npcs, "name": name, "drops": [
            {"typeId": tid, "name": "silver" if tid == 0 else names[tid], "rate": rate, "min": lo, "max": hi}
            for tid, rate, lo, hi in drops]})
    npc_ids = sorted({int(m) for m in re.findall(r'<npc id="(\d+)"', (xmls / "NPCInfo.xml").read_text(encoding="utf-8", errors="replace"))})
    out = {
        "source": "the original Gran Skrea Online server's Loot.xml and NPCInfo.xml (sent by the game's developer)",
        "generator": "GSODevTools tools/datamining/gen_droptables.py",
        "originalNpcs": npc_ids,
        "tables": tables,
    }
    # One table per few lines: its NPC ids on one line and one line per drop.
    lines = ["{", f' "source": {json.dumps(out["source"])},', f' "generator": {json.dumps(out["generator"])},',
             f' "originalNpcs": {json.dumps(npc_ids)},', ' "tables": [']
    for i, t in enumerate(tables):
        lines.append(f'  {{ "npcs": {json.dumps(t["npcs"])}, "name": {json.dumps(t["name"], ensure_ascii=False)}, "drops": [')
        lines += ["    " + json.dumps(d, ensure_ascii=False) + ("," if j < len(t["drops"]) - 1 else "") for j, d in enumerate(t["drops"])]
        lines.append("  ] }" + ("," if i < len(tables) - 1 else ""))
    lines += [" ]", "}"]
    text = "\n".join(lines)
    json.loads(text)   # fails loudly if the hand-made layout is broken
    pathlib.Path(out_path).write_text(text + "\n", encoding="utf-8")
    print(f"{len(tables)} tables, {sum(len(t['drops']) for t in tables)} drops, {len(npc_ids)} original NPC types -> {out_path}")
    if unknown:
        print("Item ids not in the game's item data (left out):", unknown)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2], sys.argv[3])
