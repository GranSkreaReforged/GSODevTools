"""Build GSOOffline's src/GSOOffline/Data/droptables.json from the original server's Loot.xml and NPCInfo.xml.

The game's developer sent the original server; its Loot.xml holds the real drop tables (the develop-branch
snapshot in UpdatedOldServerArchive, which has everything the final client has). Each table lists NPC type ids and drops; the server rolled every drop on its own,
1 in `rate`, with an amount from minamount to maxamount (default 1). Item 0 is silver. The NPC ids in the
original NPCInfo.xml are written out too: an NPC the original knew but gave no table dropped nothing from one,
while NPCs added after the snapshot keep GSOOffline's wiki tables (loot.json).

Usage:
  python -I gen_droptables.py <XMLs folder> <textassets> <droptables.json>
  e.g. gen_droptables.py ../UpdatedOldServerArchive/Server/Assets/Resources/XMLs extracted/textassets ../GSOOffline/src/GSOOffline/Data/droptables.json
"""
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET


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
        tables.append(entry)
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
