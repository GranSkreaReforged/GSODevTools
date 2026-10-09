"""Build GSOOffline's src/GSOOffline/Data/loot.json from the Gran Skrea Online community wiki.

The old server's drop tables are lost; the client never had them. The fan wiki
(gran-skrea-online.fandom.com) recorded what monsters dropped: "Drops" tables on monster pages,
"Drop sources" tables on item pages, silver amounts on the Silver page, and the rule that upgrade and
grade stones drop from every monster by level band. This script turns that into item type ids and
chances. Rates are mostly unrecorded, so rarity words map to chances (RARITY below); those numbers are
reconstructions. Hand corrections go in ALIASES / SKIP.

Usage:
  python -I gen_loot.py fetch <pages.json>                     download every wiki page (wikitext)
  python -I gen_loot.py build <pages.json> <textassets> <loot.json>
  e.g. gen_loot.py fetch extracted/wiki/pages.json
       gen_loot.py build extracted/wiki/pages.json extracted/textassets ../GSOOffline/src/GSOOffline/Data/loot.json
"""
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API = "https://gran-skrea-online.fandom.com/api.php"
SOURCE = "Gran Skrea Online wiki (gran-skrea-online.fandom.com), CC BY-SA"

# Rarity words on the wiki -> chance per kill. Reconstructions: the wiki never gives numbers.
RARITY = {"always": 1.0, "common": 0.5, "common/uncommon": 0.3, "uncommon": 0.15, "rare": 0.04, "very rare": 0.005}
DEFAULT_CHANCE = 0.5   # listed with no rarity and no "0-N" amount

# Wiki names that differ from the game's item names (checked against items.txt by hand).
ALIASES = {
    "iridrium ingot": "Iridium ingot", "red berries": "Redberries", "copper ore": "Copper",
    "dragon skin": "Dragon leather", "medium experience roll": "Medium experience scroll",
    "crab(pet)": "Crab", "raw sea serpent meat": "Raw serpent meat", "furniture: hanging cage 1": "Furniture: Hanging cage",
    "verum armor": "Verum platebody", "steel armor": "Steel plate body", "spruce logs": "Spruce log",
}
# Ambiguous or not an item in the game data ("colored beetle shells" = one of four shell colours, see BEETLE).
SKIP = {"experience scroll", "bear cub", "monsters", "colored beetle shells", "shadow"}
# Upgrade and grade stones drop from every monster by level band (wiki: "Grade stone", "Upgrade stone").
GLOBAL = [
    (437, "Small upgrade stone", 1, 24, 0.02), (438, "Medium upgrade stone", 25, 49, 0.02), (439, "Large upgrade stone", 50, 999, 0.02),
    (440, "Small grade stone", 1, 24, 0.005), (441, "Medium grade stone", 25, 49, 0.005), (442, "Large grade stone", 50, 999, 0.005),
]


def fetch(out):
    def get(params):
        req = urllib.request.Request(f"{API}?{urllib.parse.urlencode(params)}", headers={"User-Agent": "GSO preservation research"})
        return json.load(urllib.request.urlopen(req, timeout=60))
    titles, cont = [], {}
    while True:
        r = get({"action": "query", "list": "allpages", "aplimit": "500", "format": "json", **cont})
        titles += [p["title"] for p in r["query"]["allpages"]]
        if "continue" not in r:
            break
        cont = r["continue"]
    pages = {}
    for i in range(0, len(titles), 50):
        r = get({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                 "titles": "|".join(titles[i:i + 50]), "format": "json", "formatversion": "2"})
        for p in r["query"]["pages"]:
            if p.get("revisions"):
                pages[p["title"]] = p["revisions"][0]["slots"]["main"]["content"]
        time.sleep(1)
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(out).write_text(json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(pages)} pages -> {out}")


def load_xml(path):
    text = pathlib.Path(path).read_text(encoding="utf-8-sig", errors="replace")
    return ET.fromstring(re.sub(r"&(?![a-zA-Z#]+;)", "&amp;", text))


def norm(s):
    return re.sub(r"\s+", " ", s.replace("_", " ").replace("'''", "")).strip().lower()


LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")


def clean(cell):
    """Cell text without wiki attributes and formatting; links become their target."""
    cell = re.sub(r'^\s*(?:[\w-]+\s*=\s*"[^"]*"\s*)+\|(?!\|)', "", cell)
    cell = LINK.sub(lambda m: m.group(1), cell)
    return re.sub(r"\s+", " ", cell.replace("'''", "").replace("''", "")).strip()


def first_link(cell):
    m = LINK.search(cell)
    return m.group(1).strip() if m else None


def tables(section):
    """Yield (headers, rows) for each {| ... |} table; cells keep their raw wikitext."""
    for t in re.findall(r"\{\|(.*?)\|\}", section, re.S):
        rows = []
        for raw in re.split(r"\n\|-[^\n]*", t):   # the header may sit before the first |- or after it
            cells = []
            for line in raw.split("\n"):
                line = line.strip()
                if line[:1] in ("|", "!") and not line.startswith(("|}", "|-")):
                    cells += re.split(r"\|\||!!", line[1:])
            if cells:
                rows.append(cells)
        if not rows:
            continue
        header = [clean(c).lower() for c in rows[0]]
        if any(h in ("item", "amount", "quantity", "rarity", "source", "monster") for h in header):
            yield header, rows[1:]
        else:
            yield [], rows


def col(header, *names):
    for i, h in enumerate(header):
        if any(n in h for n in names):
            return i
    return None


def parse_amount(text):
    m = re.search(r"(\d+)\s*[-~]\s*(\d+)", text or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\d+", text or "")
    return (int(m.group(0)), int(m.group(0))) if m else None


def parse_levels(text):
    return sorted({int(x) for x in re.findall(r"\d+", text or "")})


def section(text, *names):
    pat = "|".join(names)
    m = re.search(rf"(?is)==\s*(?:{pat})\s*==(.*?)(?:\n==[^=]|\[\[Category|\Z)", text)
    return m.group(1) if m else ""


def build(pages_path, textassets, out_path):
    pages = json.loads(pathlib.Path(pages_path).read_text(encoding="utf-8"))
    ta = pathlib.Path(textassets)
    items = {}
    for it in load_xml(ta / "items.txt"):
        if it.get("Name"):
            items.setdefault(norm(it.get("Name")), (int(it.get("TypeId")), it.get("Name").strip()))
    npc_names, npc_levels = {}, {}
    for n in load_xml(ta / "NPCInfo.txt"):
        if n.get("name"):
            npc_names.setdefault(norm(n.get("name")), n.get("name").strip())
            npc_levels.setdefault(norm(n.get("name")), set()).add(int(n.get("level") or 0))

    def item(name):
        n = norm(name)
        n = norm(ALIASES.get(n, n))
        if n in SKIP:
            return None
        for cand in (n, n[:-1] if n.endswith("s") else n, n + "s"):
            if cand in items:
                return items[cand]
        return None

    def npc(name):
        n = re.sub(r"\(.*?\)", "", norm(name)).strip()
        for cand in (n, n[:-1] if n.endswith("s") else n):
            if cand in npc_names:
                return npc_names[cand]
        return None

    monsters, unmatched_items, unmatched_npcs = {}, {}, set()

    def add(monster_page, item_name, amount=None, rarity=None, levels=None, chance=None, origin=""):
        m = npc(monster_page)
        if not m:
            unmatched_npcs.add(monster_page)
            return
        entry = monsters.setdefault(m.lower(), {"name": m, "wikiPages": [], "silver": None, "drops": {}})
        if monster_page not in entry["wikiPages"]:
            entry["wikiPages"].append(monster_page)
        if norm(item_name) == "silver":
            if amount and not entry["silver"]:
                entry["silver"] = list(amount)
            entry.setdefault("dropsSilver", True)
            entry["dropsSilver"] = True
            return
        found = item(item_name)
        if not found:
            if norm(item_name) not in SKIP:
                unmatched_items.setdefault(item_name, set()).add(monster_page)
            return
        type_id, real_name = found
        # A level filter only means something for families with several levels (Crab 2/6/10), and only when
        # it names levels the game data has: the wiki's levels are sometimes off (Red crab "55" is level 40).
        levels = sorted(set(levels or []) & npc_levels.get(norm(m), set()))
        lo, hi = amount if amount else (1, 1)
        rar = (rarity or "").lower().strip()
        if chance is None:
            chance = RARITY.get(rar, 1.0 if lo == 0 else DEFAULT_CHANCE)
        d = entry["drops"].get(type_id)
        if d is None:
            entry["drops"][type_id] = {"typeId": type_id, "name": real_name, "min": lo, "max": max(lo, hi),
                                       "chance": chance, "levels": levels or [], "from": origin}
        else:   # the item's own page can add a level filter or an explicit rate
            if levels and not d["levels"]:
                d["levels"] = levels
            if origin == "rate":
                d["chance"] = chance

    for title, text in pages.items():
        is_monster = bool(re.search(r"\{\{(?:Monsters|1templatemonster)|\[\[Category:Monsters\]\]", text)) or \
            (npc(title) and re.search(r"(?im)^\s*Drops\s*:", text))
        if is_monster and npc(title):
            body = section(text, "Drops?")
            for header, rows in tables(body):
                ci, cq, cr, cf = col(header, "item"), col(header, "amount", "quantity"), col(header, "rarity"), col(header, "from", "level")
                for cells in rows:
                    raw_item = cells[ci] if ci is not None and ci < len(cells) else next((c for c in cells if LINK.search(c)), None)
                    name = first_link(raw_item or "") or clean(raw_item or "")
                    if not name:
                        continue
                    get = lambda i: clean(cells[i]) if i is not None and i < len(cells) else ""
                    add(title, name, parse_amount(get(cq)), get(cr), parse_levels(get(cf)), origin="monster page")
            for line in re.findall(r"(?im)^\s*Drops\s*:\s*(.+)$", text):
                for part in re.split(r",", line):
                    name = first_link(part) or clean(part)
                    if name:
                        add(title, name, origin="monster page")
        # Item pages: "Drop sources" tables (Source / Level / Quantity / Rarity) and dropped_by = X.
        body = section(text, "Drop sources?", "Dropping monsters")
        for header, rows in tables(body):
            cs, cl, cq, cr = col(header, "source", "monster"), col(header, "level"), col(header, "quantity", "amount"), col(header, "rarity")
            if cs is None:
                continue
            for cells in rows:
                if cs >= len(cells):
                    continue
                src = first_link(cells[cs])
                if not src:
                    continue
                get = lambda i: clean(cells[i]) if i is not None and i < len(cells) else ""
                lv = parse_levels(get(cl)) or parse_levels(re.sub(r"\[\[.*?\]\]", "", cells[cs]))
                add(src, title, parse_amount(get(cq)), get(cr), lv, origin="item page")
        for src in re.findall(r"dropped_by\s*=\s*\[*([^|\]\n}]+)", text):
            add(src.strip(), title, origin="item page")
        rate = re.search(r"rate of 1\s*/\s*(\d+)", text)
        by = re.search(r"dropped_by\s*=\s*\[*([^|\]\n}]+)", text)
        if rate and by:
            add(by.group(1).strip(), title, chance=1.0 / int(rate.group(1)), origin="rate")

    out = {
        "source": SOURCE,
        "generator": "GSODevTools tools/datamining/gen_loot.py",
        "rarityChances": RARITY,
        "defaultChance": DEFAULT_CHANCE,
        "global": [{"typeId": t, "name": n, "minLevel": lo, "maxLevel": hi, "chance": c} for t, n, lo, hi, c in GLOBAL],
        "monsters": [],
    }
    for key in sorted(monsters):
        m = monsters[key]
        out["monsters"].append({"name": m["name"], "wikiPages": m["wikiPages"], "dropsSilver": m.get("dropsSilver", False),
                                "silver": m["silver"] or [], "drops": sorted(m["drops"].values(), key=lambda d: d["typeId"])})
    pathlib.Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    n = sum(len(m["drops"]) for m in out["monsters"])
    print(f"{len(out['monsters'])} monsters, {n} item drops -> {out_path}")
    if unmatched_items:
        print("Unmatched item names (add to ALIASES or SKIP):")
        for k, v in sorted(unmatched_items.items()):
            print(f"  {k}  <- {', '.join(sorted(v))}")
    if unmatched_npcs:
        print("Wiki sources with no NPC of that name (ignored):", ", ".join(sorted(unmatched_npcs)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) == 3 and sys.argv[1] == "fetch":
        fetch(sys.argv[2])
    elif len(sys.argv) == 5 and sys.argv[1] == "build":
        build(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)
