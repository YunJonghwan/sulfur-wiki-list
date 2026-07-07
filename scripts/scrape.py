"""SULFUR Wiki data scraper.

Fetches every page that uses the {{Item Infobox}} template from
https://sulfur.wiki.gg, parses the infobox parameters, buckets items by
their `kind`, and writes structured JSON into ../public/data/.

Data is licensed CC BY-SA 4.0 (https://sulfur.wiki.gg). Run manually:

    python scripts/scrape.py

Only depends on the Python standard library.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://sulfur.wiki.gg/api.php"
WIKI = "https://sulfur.wiki.gg/wiki/"
USER_AGENT = "SulfurWikiList/1.0 (data aggregation; contact via GitHub YunJonghwan/sulfur-wiki-list)"

OUT_DIR = Path(__file__).resolve().parent.parent / "public" / "data"

# Kinds we generate a page/table for, in the requested display order.
TARGET_KINDS = ["weapon", "oil", "attachment", "equipment", "consumable"]

# Ordered stat columns per kind, taken from Template:Item Infobox.
# The frontend only shows columns that at least one item actually populates.
KIND_COLUMNS: dict[str, list[str]] = {
    "weapon": [
        "GridSize", "SubType", "Ammo", "Mode", "Mag", "Weight",
        "Damage", "RPM", "Spread", "Recoil", "Durability",
        "SellVal", "BuyVal", "SoldBy",
    ],
    "oil": [
        "Dmg", "RPM", "CritChance", "Spread", "Recoil", "RldSpeed",
        "BltSpeed", "BltPen", "BltSize", "BltBounces", "BltBounciness",
        "ProjecAmnt", "AmmoConsume", "MaxDrb", "BltDrop", "Drag",
        "AmmoExConsume", "Speed", "JumpPwr", "LootChance", "MoveAccuracy",
        "AimDisabled",
        # Effects
        "ConvertWpn", "RocketBlt", "Homing", "CrpsExpl", "Petrify", "Poison",
        "PsnCloud", "PsnPuddle", "Oily", "OilPuddle", "Wet", "Fire", "Lava",
        "Explosion", "Electrocution", "ElecArea", "SlowMo", "Charm",
        "MoreDmgOnHit", "Blind", "AreaBlind", "SelfBlind", "Blindfolded",
        "WearGoggles", "WearEarPro", "WearShades", "WearSJ", "Stun",
        "StunArea", "Swap", "Fear", "Frost", "Root", "NoMoney", "NoOrgans",
        "AlwaysOrgans", "SelfDmg", "LifeTime", "LessForceSpd", "FrostPuddle",
        "Freeze", "LinkBlt", "ShareDmg", "Frag", "Sticky", "NoDrb", "Proc",
        "Slide", "Summon", "TimeScale", "PrevDeath", "AirDmg", "LootRolls",
        "SingleUse",
        "SellVal", "BuyVal", "SoldBy",
    ],
    "attachment": [
        "GridSize", "SubType",
        "ModeChange", "CritADS", "MoveAccuracy", "SilFire", "Spread",
        "Recoil", "Dmg", "CritChance", "BltSpeed", "MaxDrb", "RPM", "Speed",
        "Charisma",
        "SellVal", "BuyVal", "SoldBy",
    ],
    "equipment": [
        "GridSize", "SubType", "Durability",
        "Armor", "Speed", "Sprint", "SwimSpeed", "MoveAccuracy", "WpnWeight",
        "CritADS", "JumpPwr", "ExtraJumps", "Coyote", "Charisma", "Luck",
        "CharmRst", "ExplRst", "FireRst", "FrostRst", "PsnRst", "ElecRst",
        "LightRst", "AutoDmg", "PistolDmg", "RevolDmg", "AssltDmg", "LMGDmg",
        "RifleDmg", "MeleeDmg", "SniperDmg", "ShotgunDmg",
        "SellVal", "BuyVal", "SoldBy",
    ],
    "consumable": [
        "GridSize", "SubType", "Theme", "Recipes",
        "Heal", "RmvFire", "RmvFrost", "RmvPsn", "RmvVD",
        "Charisma", "Coyote", "CritADS", "Sprint", "MoveAccuracy", "JumpPwr",
        "ExtraJumps", "Speed", "WpnWeight", "FireRst", "FrostRst", "PsnRst",
        "ElecRst", "LightRst", "MeleeDmg",
        "SellVal", "BuyVal", "SoldBy",
    ],
}

# Human-readable labels for parameter keys, from Template:Item Infobox.
LABELS: dict[str, str] = {
    "GridSize": "Grid Size",
    "SubType": "Type",
    "Ammo": "Ammunition",
    "Mode": "Mode",
    "Mag": "Magazine Size",
    "Weight": "Weight",
    "Damage": "Damage",
    "RPM": "Rate of Fire",
    "Spread": "Spread",
    "Recoil": "Recoil",
    "Durability": "Durability",
    "Theme": "Theme",
    "Recipes": "Recipes Included",
    "Area": "Effect Radius",
    "Frag": "Fragmentation",
    "ChamberAmmo": "Chamber into",
    "SilFire": "Silences Fire",
    "HSDmg": "Headshot Damage",
    "Dmg": "Damage",
    "DarkDmg": "Dark Damage",
    "ModeChange": "Change Firing Mode to",
    "MaxDrb": "Max Durability",
    "NoDrb": "Does not increase durability loss",
    "DrbConsume": "Durability Consumption",
    "Sprint": "Sprint Bonus",
    "Speed": "Movement Speed",
    "SwimSpeed": "Swim Speed",
    "CritChance": "Crit Chance",
    "CritADS": "Crit Chance down sight",
    "MoveAccuracy": "Accuracy while moving",
    "BltSpeed": "Bullet Speed",
    "BltDrop": "Bullet Drop",
    "BltPen": "Bullet Penetrations",
    "PenDmgMult": "Penetration Damage Multiplier",
    "BltSize": "Bullet Size",
    "BltBounces": "Bullet Bounces",
    "BltBounciness": "Bullet Bounciness",
    "Drag": "Drag Multiplier",
    "AimDisabled": "Disable Aim",
    "ProjecAmnt": "Projectile Amount",
    "RldSpeed": "Reload Speed",
    "JumpPwr": "Jump Power",
    "ExtraJumps": "Extra Jumps",
    "WpnWeight": "Weapon Weight",
    "AutoDmg": "Automatic Weapon Damage",
    "PistolDmg": "Pistol Damage",
    "RevolDmg": "Revolver Damage",
    "AssltDmg": "Assault Rifle Damage",
    "RifleDmg": "Rifle Damage",
    "MeleeDmg": "Melee Damage",
    "SniperDmg": "Sniper Damage",
    "ShotgunDmg": "Shotgun Damage",
    "LMGDmg": "LMG Damage",
    "WpnAreaDmg": "Weapon-Based Area Damage",
    "AreaBlind": "Blinds enemies in an area",
    "SelfBlind": "Blind Self",
    "CharmRst": "Charm Resistance",
    "FireRst": "Fire Resistance",
    "ExplRst": "Explosion Resistance",
    "FrostRst": "Frost Resistance",
    "PsnRst": "Poison Resistance",
    "ElecRst": "Electric Resistance",
    "LightRst": "Light Resistance",
    "RmvFire": "Removes Fire",
    "RmvFrost": "Removes Frost",
    "RmvPsn": "Removes Poison",
    "RmvVD": "Removes Voodoo",
    "Heal": "Healing",
    "LootChance": "Loot Chance",
    "LungCpty": "Lung Capacity",
    "Coyote": "Coyote Time",
    "Slide": "Crouch Slide",
    "ExpGain": "Experience",
    "Summon": "Summoned Ally",
    "TimeScale": "Time Scale Adjustment",
    "PrevDeath": "Prevents Death",
    "AirDmg": "Airborne Damage",
    "LootRolls": "Loot Rerolls",
    "SingleUse": "Single Use",
    "Poison": "Poison",
    "PsnCloud": "Poison Cloud",
    "PsnPuddle": "Poisonous Puddle",
    "FrostPuddle": "Frost Puddle",
    "OilPuddle": "Puddle of Oil",
    "Oily": "Oily",
    "Wet": "Wet",
    "Fire": "Fire",
    "Lava": "Lava",
    "Explosion": "Explosion",
    "Electrocution": "Electrocution",
    "Freeze": "Chance to Freeze Solid",
    "Frost": "Frost",
    "Root": "Root",
    "Fear": "Fear",
    "Stun": "Stun",
    "StunArea": "Stun Area",
    "Swap": "Swap places with target",
    "ElecArea": "Electrocution Area",
    "ShareDmg": "Damage Shared",
    "NoMoney": "No Money drops",
    "NoOrgans": "No Organs drop",
    "AlwaysOrgans": "Always drop Organs",
    "AmmoConsume": "Ammo Consume Chance",
    "AmmoExConsume": "Extra Ammo Consume Chance",
    "MoreDmgOnHit": "Additional Damage Taken per Stack",
    "SlowMo": "Slow Motion",
    "WearGoggles": "Wearing Goggles",
    "WearEarPro": "Wearing Ear Pro",
    "WearShades": "Wearing Shades",
    "WearSJ": "Straightjacketed",
    "Blindfolded": "Blindfolded",
    "SelfDmg": "Self Damage Per Bullet",
    "LifeTime": "Projectile Life Time",
    "LessForceSpd": "Less Force Speed",
    "ConvertWpn": "Convert Weapon into",
    "RocketBlt": "Convert Bullets into Rockets",
    "Homing": "Homing Bullets",
    "CrpsExpl": "Corpse Explosion Power",
    "Blind": "Blinding",
    "Petrify": "Petrification",
    "Charm": "Charm",
    "Sticky": "Sticky",
    "LinkBlt": "Bullet links Targets",
    "DrbPts": "Durability Restored",
    "Proc": "Proc Chance",
    "Luck": "Luck",
    "Armor": "Armor",
    "Charisma": "Charisma",
    "SellVal": "Selling Value",
    "BuyVal": "Buying Value",
    "SoldBy": "Sold By",
}


def api_get(params: dict) -> dict:
    params = {**params, "format": "json"}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def get_infobox_pages() -> list[str]:
    """Return all main-namespace page titles that transclude Item Infobox."""
    titles: list[str] = []
    cont: dict = {}
    while True:
        data = api_get({
            "action": "query",
            "list": "embeddedin",
            "eititle": "Template:Item Infobox",
            "einamespace": "0",
            "eilimit": "max",
            **cont,
        })
        titles.extend(p["title"] for p in data["query"]["embeddedin"])
        if "continue" in data:
            cont = data["continue"]
        else:
            break
    return titles


def fetch_wikitext_batch(titles: list[str]) -> dict[str, str]:
    """Fetch raw wikitext for up to 50 titles at once."""
    out: dict[str, str] = {}
    data = api_get({
        "action": "query",
        "prop": "revisions",
        "rvslots": "main",
        "rvprop": "content",
        "titles": "|".join(titles),
    })
    pages = data.get("query", {}).get("pages", {})
    normalized = {n["from"]: n["to"] for n in data.get("query", {}).get("normalized", [])}
    for page in pages.values():
        title = page.get("title")
        revs = page.get("revisions")
        if not revs:
            continue
        content = revs[0]["slots"]["main"].get("*", "")
        out[title] = content
    # Map normalized titles back so lookups by original title still work.
    for src, dst in normalized.items():
        if dst in out:
            out[src] = out[dst]
    return out


def extract_infobox(wikitext: str) -> str | None:
    """Return the raw contents of the first {{Item Infobox ...}} block."""
    start = wikitext.find("{{Item Infobox")
    if start == -1:
        return None
    depth = 0
    i = start
    while i < len(wikitext) - 1:
        pair = wikitext[i:i + 2]
        if pair == "{{":
            depth += 1
            i += 2
            continue
        if pair == "}}":
            depth -= 1
            if depth == 0:
                return wikitext[start + 2:i]
            i += 2
            continue
        i += 1
    return None


def split_top_level(body: str) -> list[str]:
    """Split infobox body on top-level | (ignoring nested [[ ]] and {{ }})."""
    parts: list[str] = []
    buf: list[str] = []
    depth_brace = 0
    depth_brack = 0
    i = 0
    while i < len(body):
        two = body[i:i + 2]
        if two == "{{":
            depth_brace += 1
            buf.append(two)
            i += 2
            continue
        if two == "}}":
            depth_brace -= 1
            buf.append(two)
            i += 2
            continue
        if two == "[[":
            depth_brack += 1
            buf.append(two)
            i += 2
            continue
        if two == "]]":
            depth_brack -= 1
            buf.append(two)
            i += 2
            continue
        ch = body[i]
        if ch == "|" and depth_brace == 0 and depth_brack == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
FILE_RE = re.compile(r"\[\[(?:File|Category):[^\]]*\]\]", re.IGNORECASE)
BOLD_RE = re.compile(r"'''?")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def clean_value(raw: str) -> str:
    v = raw.strip()
    v = COMMENT_RE.sub("", v)
    v = FILE_RE.sub("", v)

    def link_repl(m: re.Match) -> str:
        inner = m.group(1)
        return inner.split("|")[-1] if "|" in inner else inner

    v = LINK_RE.sub(link_repl, v)
    v = re.sub(r"<br\s*/?>", ", ", v, flags=re.IGNORECASE)
    v = TAG_RE.sub("", v)
    v = BOLD_RE.sub("", v)
    v = html.unescape(v)
    v = re.sub(r"\s*,\s*,\s*", ", ", v)
    v = re.sub(r"\s+", " ", v).strip()
    v = v.strip(", ")
    return v


# Some pages spell a few parameters inconsistently; normalize to canonical keys.
KEY_ALIASES = {
    "Grid Size": "GridSize",
}


def parse_infobox(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in split_top_level(body)[1:]:  # first chunk is the template name
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        key = key.strip()
        key = KEY_ALIASES.get(key, key)
        value = clean_value(value)
        if key and value:
            fields[key] = value
    return fields


def build() -> None:
    print("Fetching page list...")
    titles = get_infobox_pages()
    print(f"  {len(titles)} pages use Item Infobox")

    buckets: dict[str, list[dict]] = {k: [] for k in TARGET_KINDS}

    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        texts = fetch_wikitext_batch(batch)
        for title in batch:
            wikitext = texts.get(title)
            if not wikitext:
                continue
            body = extract_infobox(wikitext)
            if body is None:
                continue
            fields = parse_infobox(body)
            kind = fields.get("kind", "").strip().lower()
            if kind not in buckets:
                continue
            image = fields.get("image", f"{title}.png")
            item = {
                "name": title,
                "page": WIKI + urllib.parse.quote(title.replace(" ", "_")),
                "image": image,
                "fields": {k: v for k, v in fields.items()
                           if k not in ("kind", "image", "title")},
            }
            buckets[kind].append(item)
        print(f"  parsed {min(i + 50, len(titles))}/{len(titles)}")
        time.sleep(0.3)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat()

    for kind in TARGET_KINDS:
        items = sorted(buckets[kind], key=lambda it: it["name"].lower())
        # Only keep columns that at least one item populates, preserving order.
        present = {k for it in items for k in it["fields"]}
        columns = [
            {"key": key, "label": LABELS.get(key, key)}
            for key in KIND_COLUMNS.get(kind, [])
            if key in present
        ]
        # Include any populated keys not listed in KIND_COLUMNS at the end.
        listed = set(KIND_COLUMNS.get(kind, []))
        for key in sorted(present - listed):
            columns.append({"key": key, "label": LABELS.get(key, key)})

        payload = {
            "kind": kind,
            "generated": generated,
            "source": "https://sulfur.wiki.gg",
            "license": "CC BY-SA 4.0",
            "columns": columns,
            "items": items,
        }
        out_path = OUT_DIR / f"{kind}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"Wrote {out_path.relative_to(OUT_DIR.parent.parent)} "
              f"({len(items)} items, {len(columns)} columns)")


if __name__ == "__main__":
    build()
