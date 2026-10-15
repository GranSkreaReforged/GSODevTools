"""Build GSOOffline's src/GSOOffline/Data/shops.json from the original server's Shops.xml.

The game's developer sent the original server (2026-10-15); its Shops.xml lists what each shop sold. Shop ids
are the ones dialogue nodes open (openshop=N). Each item may carry its own price (else the item's price),
a stock cap (maxamount), a starting stock (currentamount) and a restock time (respawntime); the stock
fields are kept for later even though GSOOffline doesn't use them yet.

Usage:
  python -I gen_shops.py <Shops.xml> <textassets> <shops.json>
  e.g. gen_shops.py ../OldServerArchive/GSOServer/Server/Assets/Resources/XMLs/Shops.xml extracted/textassets ../GSOOffline/src/GSOOffline/Data/shops.json
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


def build(shops_xml, textassets, out_path):
    names = load_items(textassets)
    # The file has a stray space before = in some name attributes ('name = "..."'); ElementTree accepts it.
    root = ET.fromstring(pathlib.Path(shops_xml).read_text(encoding="utf-8", errors="replace"))
    shops, unknown = [], []
    for shop in root.findall("shop"):
        entry = {"id": int(shop.get("shopid")), "name": (shop.get("name") or "").strip(), "items": []}
        if shop.get("comment"):
            entry["comment"] = shop.get("comment")
        for it in shop.findall("item"):
            tid = int(it.get("id"))
            if tid not in names:
                unknown.append((entry["id"], tid))
                continue
            item = {"typeId": tid, "name": names[tid]}
            for attr, key in (("price", "price"), ("maxamount", "max"), ("currentamount", "stock"), ("respawntime", "restock")):
                if it.get(attr) is not None:
                    item[key] = int(it.get(attr))
            entry["items"].append(item)
        shops.append(entry)
    out = {
        "source": "the original Gran Skrea Online server's Shops.xml (sent by the game's developer)",
        "generator": "GSODevTools tools/datamining/gen_shops.py",
        "shops": shops,
    }
    pathlib.Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(shops)} shops, {sum(len(s['items']) for s in shops)} items -> {out_path}")
    if unknown:
        print("Item ids not in the game's item data (left out):", unknown)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2], sys.argv[3])
