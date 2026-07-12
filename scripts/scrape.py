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
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://sulfur.wiki.gg/api.php"
WIKI = "https://sulfur.wiki.gg/wiki/"
USER_AGENT = "SulfurWikiList/1.0 (data aggregation; contact via GitHub YunJonghwan/sulfur-wiki-list)"

OUT_DIR = Path(__file__).resolve().parent.parent / "public" / "data"
IMG_DIR = Path(__file__).resolve().parent.parent / "public" / "icons"

# Raw wikitext is cached locally so re-runs that only change post-processing
# (e.g. how items are grouped) don't re-hit the wiki. Use --refresh to refetch.
CACHE_FILE = Path(__file__).resolve().parent / ".cache" / "wikitext.json"

# Icon thumbnail width to download (px). Displayed at 32px, 2x for sharpness.
ICON_WIDTH = 64

# Kinds we generate a page/table for, in the requested display order.
TARGET_KINDS = ["weapon", "oil", "attachment", "equipment", "consumable",
                "scroll", "passive", "misc", "chisel", "enemy"]

# Ordered stat columns per kind, taken from Template:Item Infobox.
# The frontend only shows columns that at least one item actually populates.
KIND_COLUMNS: dict[str, list[str]] = {
    "weapon": [
        "GridSize", "SubType", "Ammo",
        "Damage", "RPM", "Spread", "Recoil",
        "Mode", "Mag", "Weight", "Durability",
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
        "GridSize", "SubType", "Zoom",
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
    "scroll": [
        "GridSize", "SubType",
        "Dmg", "RPM", "DarkDmg", "WpnAreaDmg", "HSDmg", "Spread", "BltSpeed",
        "BltPen", "PenDmgMult", "BltSize", "BltBounces", "BltBounciness",
        "BltDrop", "Drag", "DrbConsume",
        "ConvertWpn", "RocketBlt", "Homing", "CrpsExpl", "Petrify", "Poison",
        "PsnCloud", "PsnPuddle", "Fire", "Lava", "Explosion", "Electrocution",
        "ElecArea", "Charm", "Blind", "Stun", "Fear", "Frost", "Freeze",
        "Root", "LinkBlt", "Frag", "Sticky",
        "SellVal", "BuyVal", "SoldBy",
    ],
    "passive": [
        "GridSize", "SubType",
        "Luck", "Speed", "LungCpty", "ExpGain",
        "AutoDmg", "PistolDmg", "RevolDmg", "AssltDmg", "LMGDmg", "RifleDmg",
        "MeleeDmg", "SniperDmg", "ShotgunDmg",
        "SellVal", "BuyVal", "SoldBy",
    ],
    "misc": [
        "GridSize", "SubType",
        "SellVal", "BuyVal", "SoldBy",
    ],
    "chisel": [
        "GridSize", "ChamberAmmo",
        "SellVal", "BuyVal", "SoldBy",
    ],
    "enemy": [
        "Faction", "HP", "Dmg", "DmgType", "Attack Type", "DmgRange", "Areas", "Exp",
    ],
}

# Human-readable labels for parameter keys, from Template:Item Infobox.
LABELS: dict[str, str] = {
    "GridSize": "Grid Size",
    "SubType": "Type",
    "Ammo": "Ammunition",
    "ChamberAmmo": "Converts To",
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
    "Faction": "Faction",
    "HP": "Health",
    "DmgType": "Damage Type",
    "Attack Type": "Attack Type",
    "DmgRange": "Damage Range",
    "Areas": "Areas Found In",
    "Exp": "Experience Given",
    "Bleed": "Bleed Resist",
    "Dark": "Dark Resist",
    "Earth": "Earth Resist",
    "Electric": "Electric Resist",
    "Frostbite": "Frostbite Resist",
    "Light": "Light Resist",
    "LungCapacity": "Lung Capacity",
    "Punish": "Punish Resist",
    "tabs": "Phases",
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
    "CritADS": "Crit Chance while Aiming (ADS)",
    "Zoom": "Zoom Factor",
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


def get_infobox_pages(template: str = "Template:Item Infobox") -> list[str]:
    """Return all main-namespace page titles that transclude the given template."""
    titles: list[str] = []
    cont: dict = {}
    while True:
        data = api_get({
            "action": "query",
            "list": "embeddedin",
            "eititle": template,
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


INFOBOX_START_RE = re.compile(r"\{\{\s*Item[ _]Infobox")
ENEMY_INFOBOX_START_RE = re.compile(r"\{\{\s*Enemy[ _]Infobox")


def extract_infobox(wikitext: str, start_re: "re.Pattern[str]" = INFOBOX_START_RE) -> str | None:
    """Return the raw contents of the first {{Item Infobox ...}} block.

    Matches both `{{Item Infobox}}` and `{{Item_Infobox}}` (MediaWiki treats
    spaces and underscores in template names as equivalent). Pass
    ENEMY_INFOBOX_START_RE to extract an {{Enemy Infobox ...}} block instead.
    """
    m = start_re.search(wikitext)
    if m is None:
        return None
    start = m.start()
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


def extract_all_templates(wikitext: str, start_re: "re.Pattern[str]") -> list[str]:
    """Return the raw body (template name + params) of every {{...}} block
    whose opening matches start_re, handling nested {{ }}. Same brace-depth
    walk as extract_infobox, but collects every match instead of the first.
    """
    bodies: list[str] = []
    pos = 0
    while True:
        m = start_re.search(wikitext, pos)
        if m is None:
            break
        start = m.start()
        depth = 0
        i = start
        end = None
        while i < len(wikitext) - 1:
            pair = wikitext[i:i + 2]
            if pair == "{{":
                depth += 1
                i += 2
                continue
            if pair == "}}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
                i += 2
                continue
            i += 1
        if end is None:
            break
        bodies.append(wikitext[start + 2:end])
        pos = end + 2
    return bodies


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
# "Lung" is renamed because it would otherwise collide with the "Lung" organ
# item's own display name in the Korean translation table.
KEY_ALIASES = {
    "Grid Size": "GridSize",
    "Lung": "LungCapacity",
}

# A few pages omit the infobox "kind" parameter entirely (a wiki typo, not
# a template variant) — e.g. every other organ has kind=misc, but Liver's
# infobox just leaves it out. Filled in by title since there's no field to
# read it from.
MISSING_KIND_BY_TITLE = {
    "Liver": "misc",
    "Hellshrew Eye": "misc",
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


# --- Consumable recipes ----------------------------------------------------
# A craftable consumable's own page has a "== Recipes ==" section with one
# {{Recipe row}} template per valid ingredient combo (often many — batch-size
# variants, alternate ingredients, bigger-stove bonuses…). One representative
# recipe is picked as the always-visible one; the rest are kept too so the UI
# can expand them in place instead of sending players out to the wiki.
RECIPE_ROW_START_RE = re.compile(r"\{\{\s*Recipe row")
# Stops only at the next *top-level* heading (== Foo ==), so legitimate
# "=== Sub Recipes ===" subsections (Omelette, Sashimi, Tori Ramen all
# organize variants this way) stay part of the captured section.
RECIPE_SECTION_RE = re.compile(r"==\s*Recipes\s*==([\s\S]*?)(?:\n==[^=]|\[\[Category)")
CATEGORY_INGREDIENT_RE = re.compile(r"^:?Category:", re.IGNORECASE)

# Wildcard labels sometimes carve out one excluded item, in several
# phrasings: "Any same skin except Shav'Wa", "Any Milk, except Buttermilk",
# "Any Flesh (Except for Craw Flesh)". Split that off so the UI can
# de-emphasize it instead of running it into the main label.
EXCEPT_RE = re.compile(r"^(.*?)\s*,?\s*\(?except(?:\s+for)?\s+(.+?)\)?\s*$", re.IGNORECASE)


def split_wildcard_exception(label: str) -> tuple[str, str | None]:
    m = EXCEPT_RE.match(label)
    if not m:
        return label, None
    return m.group(1).strip(), m.group(2).strip()


# "All other N types of X" is a completeness statement (the category minus
# whichever member is placed in another slot of the same row) — safe to
# normalize like an "except" label. A bare "X or Y" / "X/Y" listing (e.g.
# "Skimmed Milk/Low Fat Milk") is NOT the same thing: it names only some
# members of the category, so treating it as "Any <category>" would silently
# widen what the recipe actually accepts.
ALL_OTHER_RE = re.compile(r"^all\s+other\b", re.IGNORECASE)

# A handful of pages (Pölsa, Red Wine) have a "=== Hidden Recipes ===" block
# whose own text says the recipes only work via a quick-cook bug and are
# "expected to be removed in future updates" — not real recipes to teach
# players, so they're stripped out rather than counted/shown.
HIDDEN_RECIPES_RE = re.compile(r"===\s*Hidden Recipes\s*===[\s\S]*?(?=\n==|\Z)")


QTY_RANGE_RE = re.compile(r"^(\d+)\s*-\s*(\d+)$")


def parse_qty(qty_raw: str | None) -> tuple[int, str | None]:
    """Return (qty, qtyLabel). Some rows give a range like "1-3" meaning any
    amount in that range yields the same result — qty is the range's low end
    (used for sorting), qtyLabel carries the full range text for display.
    """
    if not qty_raw:
        return 1, None
    qty_raw = qty_raw.strip()
    if qty_raw.isdigit():
        return int(qty_raw), None
    m = QTY_RANGE_RE.match(qty_raw)
    if m:
        return int(m.group(1)), qty_raw
    return 1, None


def _row_ingredients(row: dict[str, str]) -> list[dict[str, object]]:
    ingredients = []
    # The wiki's Recipe row template renders slots highest-number-first
    # (i3, i2, i1 left to right, closest-to-result slot last) — confirmed
    # against the live pages for Banana Sulfs and Berry Milkshake, both of
    # which show the opposite of ascending i1..i6 order. Walk descending so
    # the scraped ingredient order already matches what's on the wiki.
    for n in range(6, 0, -1):
        val = (row.get(f"i{n}") or "").strip()
        label_raw = row.get(f"i{n}Label")
        filename_raw = row.get(f"i{n}Filename")
        if val == "(blank)":
            continue
        # Some wildcard rows leave i{n} itself empty and describe the slot
        # only via Filename/Label (e.g. Omelette's seasoning slot, Bark
        # Bread's beverage slot) — without this, they were silently dropped.
        if not val and not label_raw and not filename_raw:
            continue
        qty, qty_label = parse_qty(row.get(f"i{n}Qty"))
        is_category = bool(val) and bool(CATEGORY_INGREDIENT_RE.match(val))
        if is_category or (not val and (label_raw or filename_raw)):
            canonical = (
                "Any " + CATEGORY_INGREDIENT_RE.sub("", val).strip()
                if is_category else (label_raw or "Any")
            )
            label = label_raw or canonical
            name, exception = split_wildcard_exception(label)
            note = None
            # "All other N types" reads as a completeness statement (category
            # minus whatever's placed elsewhere in the row) — normalize it
            # like an except-label. A bare "X or Y" listing is left as-is
            # since it names a real subset, not the whole category.
            if not exception and not name.lower().startswith("any") and ALL_OTHER_RE.match(name):
                note = name
                name = canonical
            ing = {
                "name": name, "qty": qty, "wildcard": True,
                "filename": filename_raw,
            }
            # Kept as the bare excluded name (not a pre-built sentence) so
            # the UI can phrase it per language ("Shav'Wa 제외" vs "Except
            # Shav'Wa") instead of baking Korean into the data.
            if exception:
                ing["except"] = exception
            if note:
                ing["note"] = note
            if qty_label:
                ing["qtyLabel"] = qty_label
            ingredients.append(ing)
        else:
            ing = {"name": val, "qty": qty, "wildcard": False}
            if qty_label:
                ing["qtyLabel"] = qty_label
            ingredients.append(ing)
    return ingredients


# Sight/scope magnification isn't a structured infobox field — it's only
# mentioned in the description prose ("...with a 12x zoom factor...").
# Reflex/Holographic sights mention no zoom at all (they're unmagnified red
# dots), so those default to ×1 rather than being left blank.
ZOOM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*x\s+zoom factor", re.IGNORECASE)


def attachment_zoom(fields: dict[str, str], wikitext: str) -> str | None:
    if display_subtype(fields.get("SubType", "")) != "Sight":
        return None
    m = ZOOM_RE.search(wikitext)
    return f"×{m.group(1)}" if m else "×1"


# Which attachment types/items a weapon accepts, from its own "Available
# Attachments" section — a bullet list of wiki links, e.g.
# "• [[Muzzle Attachments]]", "• [[Sight|Sights]]", "• [[Gun Crank]]".
# Some pages pipe-link to the wrong target while the visible text is still
# correct (Blackwater/Chimera Rapid literally link "Chamber Chisels" text to
# the "Chamber Attachment" page), so the DISPLAY text is used when present,
# falling back to the link target only for un-piped links. The frontend
# matches this against an attachment's type (loosely — dropping a trailing
# "s", case-insensitive) or exact item name, since some entries name a
# category ("Sights") and others name one specific item ("Gun Crank").
ATTACHMENTS_SECTION_RE = re.compile(
    r"==\s*Available Attachments\s*==([\s\S]*?)(?:\n==[^=]|\Z)"
)
ATTACHMENT_BULLET_RE = re.compile(r"^•\s*\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", re.MULTILINE)


def weapon_attachment_compat(wikitext: str) -> list[str]:
    m = ATTACHMENTS_SECTION_RE.search(wikitext)
    if not m:
        return []
    return [
        (display or target).strip()
        for target, display in ATTACHMENT_BULLET_RE.findall(m.group(1))
    ]


# Weapons that accept a Chamber Chisel document the exact resulting stats
# per caliber in their own "Caliber Modding" wikitable (Beck 8 etc.) — real
# per-weapon values, not something derivable from the ammo type alone (two
# weapons on the same caliber can still differ). Row format (attribute
# prefix before the actual cell content is normal MediaWiki syntax):
#   |style="text-align: left;|[[9mm]]||60||&times;1||3||3
CALIBER_SECTION_RE = re.compile(r"==\s*Caliber Modding\s*==([\s\S]*?)(?:\n==[^=]|\Z)")
CALIBER_ROW_RE = re.compile(
    r"\[\[([^\]|]+)\]\]\|\|([^\n|]*)\|\|([^\n|]*)\|\|([^\n|]*)\|\|([^\n|]*)"
)


def weapon_caliber_modding(wikitext: str) -> list[dict[str, str]]:
    m = CALIBER_SECTION_RE.search(wikitext)
    if not m:
        return []
    rows = []
    for rm in CALIBER_ROW_RE.finditer(m.group(1)):
        caliber, dmg, proj, spread, recoil = (g.strip() for g in rm.groups())
        rows.append({
            "caliber": caliber,
            "damage": dmg,
            "projectiles": re.sub(r"[^\d.]", "", proj) or "1",
            "spread": spread,
            "recoil": recoil,
        })
    return rows


# A handful of consumables (Christmas Spice, Coffee, Flour, Karl-Oskar...)
# state their heal/status-removal effect only as bolded prose in the
# Description section ("'''Gives 5 health over 2.5 seconds.'''") instead of
# structured Heal=/Rmv*= infobox fields — most items give both, these give
# neither, so the ability column was rendering completely blank for them.
DESCRIPTION_SECTION_RE = re.compile(r"==\s*Description\s*==([\s\S]*?)(?:\n==|\Z)")
HEAL_PROSE_RE = re.compile(r"Gives\s+([\d.]+\s+[Hh]ealth(?:\s+over\s+[\d.]+\s+seconds)?)")
REMOVES_PROSE_RE = re.compile(r"Removes\s+(\w+)", re.IGNORECASE)
REMOVES_PROSE_MAP = {
    "frozen": "RmvFrost", "burning": "RmvFire",
    "poisoned": "RmvPsn", "voodoo": "RmvVD",
}


def consumable_prose_effects(wikitext: str) -> dict[str, str]:
    m = DESCRIPTION_SECTION_RE.search(wikitext)
    if not m:
        return {}
    section = m.group(1)
    effects: dict[str, str] = {}
    heal_m = HEAL_PROSE_RE.search(section)
    if heal_m:
        effects["Heal"] = heal_m.group(1)
    for rm in REMOVES_PROSE_RE.finditer(section):
        key = REMOVES_PROSE_MAP.get(rm.group(1).lower())
        if key:
            effects[key] = "✓"
    return effects


def consumable_recipe(wikitext: str) -> dict[str, object] | None:
    m = RECIPE_SECTION_RE.search(wikitext)
    if not m:
        return None
    section_text = HIDDEN_RECIPES_RE.sub("", m.group(1))
    variants = []
    for body in extract_all_templates(section_text, RECIPE_ROW_START_RE):
        row = parse_infobox(body)
        ingredients = _row_ingredients(row)
        if not ingredients:
            continue
        qty_raw = row.get("resultQty")
        result_qty = int(qty_raw) if qty_raw and qty_raw.isdigit() else 1
        variants.append({"ingredients": ingredients, "resultQty": result_qty})
    if not variants:
        return None
    # Prefer the simplest variant as the representative one: fewest
    # ingredient slots, then lowest total ingredient quantity. The rest are
    # kept as "others" so the UI can expand them instead of linking out.
    best_idx = min(
        range(len(variants)),
        key=lambda i: (
            len(variants[i]["ingredients"]),
            sum(x["qty"] for x in variants[i]["ingredients"]),
        ),
    )
    best = variants.pop(best_idx)
    best_names_key = ",".join(sorted(x["name"] for x in best["ingredients"]))
    # Group the remaining variants by their ingredient set (quantities
    # ignored) so every quantity/ratio version of "the same recipe" ends up
    # next to each other instead of scattered by result-size tier — e.g.
    # Lung+Bladder, Lung+Bladder×2, Lung×2+Bladder and Lung×2+Bladder×2 all
    # sort together, ordered by increasing result quantity.
    def variant_sort_key(v):
        by_name = sorted(v["ingredients"], key=lambda x: x["name"])
        names_key = ",".join(x["name"] for x in by_name)
        qty_key = tuple(x["qty"] for x in by_name)
        # Ingredient count first: a string-only name key would otherwise
        # scatter same-ingredient variants apart whenever an unrelated
        # variant's names happen to sort between them alphabetically (e.g.
        # "Banana,Sugar" landing after all "Banana,Solution,Sugar" entries
        # just because "Solution" < "Sugar"). Within a count tier, variants
        # sharing the main recipe's exact ingredient set (e.g. more Sugar+
        # Banana ratios) come first, ahead of other same-count combos, so
        # they read as a continuation of the recipe shown up top.
        matches_main = 0 if names_key == best_names_key else 1
        return (len(v["ingredients"]), matches_main, names_key, v["resultQty"], qty_key)

    variants.sort(key=variant_sort_key)
    return {
        "ingredients": best["ingredients"],
        "resultQty": best["resultQty"],
        "variantCount": len(variants) + 1,
        "others": variants,
    }


def download_wildcard_icons(file_names: set[str]) -> dict[str, str]:
    """Download wiki File images directly for wildcard ingredients whose
    representative image isn't itself a scraped item — e.g. "Any Flesh"
    points at File:Goblin Flesh.png, a generic category illustration with no
    matching "Goblin Flesh" item page, so it can't be found via name lookup.
    """
    if not file_names:
        return {}
    dest_dir = IMG_DIR / "consumable" / "_wildcard"
    # Recipe-row Filename hints are given without an extension (e.g. "Goblin
    # Flesh"), unlike infobox `image=` values — the wiki File: namespace
    # needs one to resolve, so default to .png like item images do.
    with_ext = {f: (f if "." in f else f"{f}.png") for f in file_names}
    urls = resolve_thumb_urls(sorted(set(with_ext.values())))
    result: dict[str, str] = {}
    for file_name, queried in with_ext.items():
        local = local_icon_name(queried)
        dest = dest_dir / local
        rel = f"icons/consumable/_wildcard/{local}"
        if dest.exists():
            result[file_name] = rel
            continue
        url = urls.get(queried)
        if not url:
            continue
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                dest.write_bytes(resp.read())
            result[file_name] = rel
            time.sleep(0.1)
        except Exception as exc:  # noqa: BLE001 - keep going on any failure
            print(f"  ! failed wildcard icon {file_name}: {exc}")
    return result


def resolve_recipe_icons(buckets: dict[str, list[dict]]) -> None:
    """Attach icon/page to recipe ingredients that match a scraped item."""
    lookup = {
        it["name"]: {"icon": it.get("icon"), "page": it["page"]}
        for kind_items in buckets.values()
        for it in kind_items
    }
    all_ingredient_lists = []
    for it in buckets.get("consumable", []):
        recipe = it.get("recipe")
        if not recipe:
            continue
        all_ingredient_lists.append(recipe["ingredients"])
        all_ingredient_lists.extend(v["ingredients"] for v in recipe.get("others", []))

    unresolved_filenames: set[str] = set()
    for ingredients in all_ingredient_lists:
        for ing in ingredients:
            ref = lookup.get(ing.get("filename") or ing["name"])
            if ref:
                ing["icon"] = ref["icon"]
                ing["page"] = ref["page"]
            elif ing.get("filename"):
                unresolved_filenames.add(ing["filename"])

    wildcard_icons = download_wildcard_icons(unresolved_filenames)
    for ingredients in all_ingredient_lists:
        for ing in ingredients:
            if not ing.get("icon") and ing.get("filename"):
                icon = wildcard_icons.get(ing["filename"])
                if icon:
                    ing["icon"] = icon
            ing.pop("filename", None)


def attach_used_in(buckets: dict[str, list[dict]]) -> None:
    """For every consumable, list the other consumables it's a concrete
    (non-wildcard) ingredient of — the reverse of its own recipe. Lets a
    pure ingredient like Banana or Flour, which has no recipe of its own,
    still show what it can be turned into. Wildcard slots are skipped since
    the ingredient name there is a category label ("Any Milk"), not a real
    item, so it can't be matched back to a specific item.
    """
    used_in: dict[str, list[dict]] = {}
    for it in buckets.get("consumable", []):
        recipe = it.get("recipe")
        if not recipe:
            continue
        variants = [recipe["ingredients"]] + [v["ingredients"] for v in recipe.get("others", [])]
        credited: set[str] = set()
        for ingredients in variants:
            for ing in ingredients:
                if ing.get("wildcard") or ing["name"] in credited:
                    continue
                credited.add(ing["name"])
                used_in.setdefault(ing["name"], []).append(
                    {"name": it["name"], "icon": it.get("icon"), "page": it["page"]}
                )
    for it in buckets.get("consumable", []):
        targets = used_in.get(it["name"])
        if targets:
            it["usedIn"] = targets


UNSAFE_FILE_RE = re.compile(r'[\\/:*?"<>|]')


def local_icon_name(file_name: str) -> str:
    """Turn a wiki File name into a safe local filename (kept as .png)."""
    stem = file_name.rsplit(".", 1)[0]
    safe = UNSAFE_FILE_RE.sub("_", stem).strip()
    safe = re.sub(r"\s+", "_", safe)
    return safe + ".png"


def resolve_thumb_urls(file_names: list[str]) -> dict[str, str]:
    """Map wiki File names to a downloadable thumbnail URL (batches of 50)."""
    urls: dict[str, str] = {}
    for i in range(0, len(file_names), 50):
        batch = file_names[i:i + 50]
        titles = "|".join("File:" + n for n in batch)
        data = api_get({
            "action": "query",
            "titles": titles,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": str(ICON_WIDTH),
        })
        query = data.get("query", {})
        # Map any title normalization back to the requested names.
        norm = {n["to"]: n["from"] for n in query.get("normalized", [])}
        for page in query.get("pages", {}).values():
            title = page.get("title", "")
            info = page.get("imageinfo")
            if not info:
                continue
            url = info[0].get("thumburl") or info[0].get("url")
            if not url:
                continue
            requested = norm.get(title, title)
            key = requested[len("File:"):] if requested.startswith("File:") else requested
            urls[key] = url
        time.sleep(0.2)
    return urls


SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    s = SLUG_STRIP_RE.sub("-", text.strip().lower()).strip("-")
    return s or "etc"


# Oils have no SubType, so they are foldered by their primary effect. Each item
# is placed in the group of the FIRST of its stats (in wiki order) that maps
# below; anything unmatched goes to "misc". Tweak freely — this only affects
# how icon files are organized on disk, not the site.
OIL_STAT_GROUP: dict[str, str] = {
    # damage output
    "Dmg": "damage", "CritChance": "damage", "CritADS": "damage",
    "ProjecAmnt": "damage", "HSDmg": "damage", "AirDmg": "damage",
    # rate of fire / reload
    "RPM": "fire-rate", "RldSpeed": "fire-rate",
    # handling / accuracy
    "Spread": "handling", "Recoil": "handling", "MoveAccuracy": "handling",
    "AimDisabled": "handling",
    # projectile behaviour
    "BltSpeed": "bullet", "BltPen": "bullet", "BltSize": "bullet",
    "BltBounces": "bullet", "BltBounciness": "bullet", "BltDrop": "bullet",
    "Drag": "bullet", "PenDmgMult": "bullet", "LifeTime": "bullet",
    # ammo / durability / loot economy
    "AmmoConsume": "economy", "AmmoExConsume": "economy", "MaxDrb": "economy",
    "LootChance": "economy", "LootRolls": "economy", "NoDrb": "economy",
    "DrbConsume": "economy", "SingleUse": "economy",
    # movement
    "Speed": "mobility", "JumpPwr": "mobility", "ExtraJumps": "mobility",
    "Coyote": "mobility", "Slide": "mobility",
}

# Effect-style keys all collapse into the "effects" group.
OIL_EFFECT_KEYS = {
    "ConvertWpn", "RocketBlt", "Homing", "CrpsExpl", "Petrify", "Poison",
    "PsnCloud", "PsnPuddle", "Oily", "OilPuddle", "Wet", "Fire", "Lava",
    "Explosion", "Electrocution", "ElecArea", "SlowMo", "Charm", "MoreDmgOnHit",
    "Blind", "AreaBlind", "SelfBlind", "Blindfolded", "WearGoggles",
    "WearEarPro", "WearShades", "WearSJ", "Stun", "StunArea", "Swap", "Fear",
    "Frost", "Root", "NoMoney", "NoOrgans", "AlwaysOrgans", "SelfDmg",
    "LessForceSpd", "FrostPuddle", "Freeze", "LinkBlt", "ShareDmg", "Frag",
    "Sticky", "Proc", "Summon", "TimeScale", "PrevDeath",
}

IGNORE_FOR_GROUPING = {"GridSize", "SellVal", "BuyVal", "SoldBy"}


def oil_group(fields: dict[str, str]) -> str:
    for key in fields:
        if key in IGNORE_FOR_GROUPING:
            continue
        if key in OIL_STAT_GROUP:
            return OIL_STAT_GROUP[key]
        if key in OIL_EFFECT_KEYS:
            return "effects"
    return "misc"


# SubType values on the wiki are inconsistent (plurals, compound tags like
# "Food, Ingredient", "SMG" vs "Submachine Gun"). Take the first tag and map
# known variants to one canonical folder name.
SUBTYPE_SPLIT_RE = re.compile(r"\s*(?:,|/|;|&|\band\b)\s*", re.IGNORECASE)
SUBTYPE_ALIASES = {
    "smg": "submachine-gun",
    "muzzle-attachments": "muzzle-attachment",
    "laser-sights": "laser-sight",
    "sights": "sight",
    "beverages": "beverage",
    "sweets": "dessert",
    "remedy": "drug-remedy",
    "drug": "drug-remedy",
    "mushrooms": "mushroom",
    "nuts": "nut",
    "organs": "organ",
    "valuable": "valuables",
}


def subtype_slug(subtype: str) -> str:
    first = SUBTYPE_SPLIT_RE.split(subtype.strip())[0]
    s = slugify(first)
    return SUBTYPE_ALIASES.get(s, s)


def icon_subdir(kind: str, fields: dict[str, str]) -> str:
    """Return the icons/ subfolder (relative) for an item."""
    if kind == "oil":
        return f"oil/{oil_group(fields)}"
    subtype = fields.get("SubType")
    if subtype:
        return f"{kind}/{subtype_slug(subtype)}"
    return f"{kind}/_etc"


def download_icons(buckets: dict[str, list[dict]]) -> None:
    """Place each item's icon under icons/<category>/<subtype>/ and set it['icon'].

    Existing icons (flat, or from an earlier folder scheme) are MOVED into the
    current structure instead of being re-downloaded; only genuinely missing
    icons are fetched from the wiki API (avoids CORP blocks and 429 rate
    limiting at runtime).
    """
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    # Index every icon already on disk by filename, wherever it currently sits.
    existing: dict[str, Path] = {}
    for path in IMG_DIR.rglob("*.png"):
        if path.is_file():
            existing.setdefault(path.name, path)

    needed: set[str] = set()
    plans: list[tuple[dict, str, Path]] = []
    moved = 0

    for kind in TARGET_KINDS:
        for it in buckets[kind]:
            file_name = it.get("image")
            if not file_name:
                it["icon"] = None
                continue
            subdir = icon_subdir(kind, it["fields"])
            local = local_icon_name(file_name)
            dest = IMG_DIR / subdir / local
            it["icon"] = f"icons/{subdir}/{local}"
            plans.append((it, file_name, dest))

            if dest.exists():
                existing[local] = dest
                continue
            src = existing.get(local)
            if src and src.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                src.replace(dest)
                existing[local] = dest
                moved += 1
            else:
                needed.add(file_name)

    print(f"Organizing {len(plans)} icons into subfolders ({moved} relocated)...")

    thumb_urls: dict[str, str] = {}
    if needed:
        print(f"  {len(needed)} icons missing; resolving URLs...")
        thumb_urls = resolve_thumb_urls(sorted(needed))

    downloaded = 0
    missing = 0
    for it, file_name, dest in plans:
        if dest.exists():
            continue
        url = thumb_urls.get(file_name)
        if not url:
            it["icon"] = None
            missing += 1
            continue
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                dest.write_bytes(resp.read())
            downloaded += 1
            time.sleep(0.1)
        except Exception as exc:  # noqa: BLE001 - keep going on any failure
            print(f"  ! failed {file_name}: {exc}")
            it["icon"] = None
            missing += 1

    _prune_empty_dirs()
    print(f"  organized {len(plans)} icons, {moved} relocated, "
          f"{downloaded} downloaded, {missing} missing/failed")


def _prune_empty_dirs() -> None:
    """Delete leftover empty folders and stale flat icons under icons/."""
    for path in sorted(IMG_DIR.glob("*.png")):
        if path.is_file():
            path.unlink()
    # Remove now-empty directories, deepest first.
    for path in sorted(IMG_DIR.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


# --- Sub-group axes -------------------------------------------------------
# Each item gets a `groups` map (axis -> display value) so the frontend can
# offer sub-tabs / sections within a category. Weapons support two axes
# (class + ammunition); oils are grouped by their effect group.

OIL_GROUP_LABELS = {
    "damage": "Damage", "fire-rate": "Fire Rate", "handling": "Handling",
    "bullet": "Bullet", "economy": "Economy", "mobility": "Mobility",
    "effects": "Effects", "misc": "Misc",
}

AXIS_KEYS_BY_KIND = {
    "weapon": ["class", "ammo"],
    "oil": ["ability", "composition"],
    "scroll": ["stage"],
    "attachment": ["type"],
    "equipment": ["type"],
    "consumable": ["type", "craftable"],
    "misc": ["type", "organSource"],
    "enemy": ["faction", "role"],
}

AXIS_LABELS = {
    "class": "Weapon Type",
    "ammo": "Ammunition",
    "ability": "Ability",
    "composition": "Composition",
    "type": "Type",
    "stage": "Stage",
    "craftable": "Acquisition",
    "organSource": "Organ Source",
    "faction": "Faction",
    "role": "Role",
}

CRAFTABLE_LABELS = {"craftable": "Craftable", "farmed": "Found / Farmed"}

# Stage 1 scrolls are the 9 base elemental scrolls (random drops / vendors);
# every other scroll is Stage 2, made by combining two Stage 1 scrolls at
# the church (order doesn't matter) — see https://sulfur.wiki.gg/wiki/Enchantments
STAGE_1_SCROLLS = {
    "Scroll of Dark", "Scroll of Earth", "Scroll of Embers",
    "Scroll of Frostbite", "Scroll of Light", "Scroll of Nature",
    "Scroll of Plague", "Scroll of Surge", "Scroll of Water",
}

STAGE_LABELS = {"stage1": "Stage 1 (Base)", "stage2": "Stage 2 (Combined)"}


def scroll_stage(title: str) -> str:
    return "stage1" if title in STAGE_1_SCROLLS else "stage2"


# Axes where an item can belong to several groups at once (e.g. an oil that
# modifies both Damage and Recoil shows up under each ability).
AXIS_MULTI = {"ability"}

# English display labels for the oil composition axis values.
COMPOSITION_LABELS = {
    "buff": "Buff",
    "debuff": "Debuff",
    "constraint": "Constraint",
    "buff+constraint": "Buff + Constraint",
    "buff+debuff": "Buff + Debuff",
    "buff+debuff+constraint": "Buff + Debuff + Constraint",
    "debuff+constraint": "Debuff + Constraint",
}

# Preferred display order for some axes; anything else is appended by count.
VALUE_ORDER = {
    "class": [
        "Pistol", "Revolver", "Shotgun", "Submachine Gun", "Assault Rifle",
        "Light Machine Gun", "Rifle", "Sniper Rifle", "Melee",
    ],
    "ammo": ["9mm", "5.56mm", "7.62mm", ".50 BMG", "12Ga", "Energy Cell"],
    # Oils split by individual ability, in the infobox stat order.
    "ability": KIND_COLUMNS["oil"],
    "composition": [
        "buff", "buff+constraint", "buff+debuff", "buff+debuff+constraint",
        "debuff+constraint", "debuff", "constraint",
    ],
    # Combined (Stage 2) scrolls listed before base (Stage 1) ones.
    "stage": ["stage2", "stage1"],
    "craftable": ["craftable", "farmed"],
    "organSource": ["Common"],
}


# --- Oil buff / debuff / constraint classification ------------------------
# For each oil stat, which direction is beneficial. Used to label an oil's
# overall composition (buff-only, buff+debuff, buff+constraint, …).
OIL_BUFF_WHEN_UP = {
    "Dmg", "RPM", "CritChance", "CritADS", "RldSpeed", "BltSpeed", "BltPen",
    "BltSize", "BltBounces", "BltBounciness", "ProjecAmnt", "MaxDrb", "Speed",
    "JumpPwr", "LootChance", "MoveAccuracy", "PenDmgMult", "LootRolls",
}
OIL_BUFF_WHEN_DOWN = {
    "Spread", "Recoil", "Drag", "BltDrop", "AmmoConsume", "AmmoExConsume",
}
# Binary / toggle restrictions (제약).
OIL_CONSTRAINTS = {
    "AimDisabled", "NoMoney", "NoOrgans", "Blindfolded", "SelfBlind", "WearSJ",
    "WearGoggles", "WearShades", "WearEarPro",
}
# Scalar penalties that count as debuffs (불이익) regardless of sign.
OIL_DEBUFF_EFFECTS = {"SelfDmg", "LessForceSpd", "MoreDmgOnHit"}


def _sign(value: str) -> int:
    v = value.strip()
    if v.startswith("+"):
        return 1
    if v.startswith("-") or v.startswith("\u2212"):
        return -1
    return 0


def classify_ability(key: str, value: str) -> str:
    if key in OIL_CONSTRAINTS:
        return "constraint"
    if key in OIL_DEBUFF_EFFECTS:
        return "debuff"
    sign = _sign(value)
    if key in OIL_BUFF_WHEN_UP:
        return "buff" if sign >= 0 else "debuff"
    if key in OIL_BUFF_WHEN_DOWN:
        return "buff" if sign < 0 else "debuff"
    # Added capabilities (elemental, homing, "no extra durability loss", …).
    return "buff"


def oil_composition(fields: dict[str, str]) -> str:
    kinds = {classify_ability(k, fields[k]) for k in oil_ability_keys(fields)}
    parts = [p for p in ("buff", "debuff", "constraint") if p in kinds]
    return "+".join(parts) or "buff"


def display_subtype(subtype: str) -> str:
    """Human-readable, consolidated subtype label (matches icon folders)."""
    if not subtype:
        return "Other"
    slug = subtype_slug(subtype)
    return slug.replace("-", " ").title()


def value_label(axis: str, value: str) -> str:
    if axis == "ability":
        return LABELS.get(value, value)
    if axis == "composition":
        return COMPOSITION_LABELS.get(value, value)
    if axis == "stage":
        return STAGE_LABELS.get(value, value)
    if axis == "craftable":
        return CRAFTABLE_LABELS.get(value, value)
    return value


def oil_ability_keys(fields: dict[str, str]) -> list[str]:
    """Individual ability keys an oil has, in infobox order (no meta fields)."""
    return [
        k for k in KIND_COLUMNS["oil"]
        if k in fields and k not in IGNORE_FOR_GROUPING
    ]


def oil_buff_ability_keys(fields: dict[str, str]) -> list[str]:
    """Ability keys this oil actually buffs (correct direction per stat) —
    e.g. a Recoil +50% oil (a debuff) is excluded from the "Recoil" group,
    since picking "Recoil" is meant to surface oils that reduce it."""
    return [
        k for k in oil_ability_keys(fields)
        if classify_ability(k, fields[k]) == "buff"
    ]


# The infobox SubType field is unreliable for organs — several pages
# (Bone, Bladder, Brain, Liver) leave it blank or just say "Ingredient",
# while the page's own [[Category:Organs]] tag is consistently present.
# That category tag is the source of truth for "is this an organ" instead.
ORGAN_CATEGORY_RE = re.compile(r"\[\[\s*Category\s*:\s*Organs\s*\]\]", re.IGNORECASE)

# Within organs, Skin/Eye/Flesh types only ever exist as enemy-specific drops
# (no generic "Skin"/"Eye"/"Flesh" item exists at all), and a couple of
# otherwise-common organ types have one named-enemy special variant
# (Cultist Heart, Shav'Wa Bladder next to the plain Heart/Bladder). Every
# other organ (Kidney, Lung, Liver, Bone, Brain, Intestines, Thyroid,
# Spleen, Pancreas, Tongue, Heart, Bladder) is a common, non-enemy-specific
# drop. There's no structured "drops from" field on the wiki to derive this
# from, so it's hand-mapped from the Category:Organs member list.
ORGAN_SOURCE_BY_TITLE = {
    "Goblin Skin": "Goblin", "Human Skin": "Human", "Dog Skin": "Dog",
    "Craw Skin": "Craw", "Hellshrew Skin": "Hellshrew", "Shav'Wa Skin": "Shav'Wa",
    "Human Eye": "Human", "Dog Eye": "Dog", "Goblin Eye": "Goblin",
    "Shav'Wa Eye": "Shav'Wa", "Hellshrew Eye": "Hellshrew",
    "Human Flesh": "Human", "Craw Flesh": "Craw", "Hellshrew Flesh": "Hellshrew",
    "Cultist Heart": "Cultist", "Shav'Wa Bladder": "Shav'Wa",
}

# Enemy pages don't carry a structured "is this a boss" field — it's only
# conveyed by a [[Category:Bosses]] tag at the bottom of the page.
ENEMY_BOSS_RE = re.compile(r"\[\[\s*Category\s*:\s*Bosses\s*\]\]", re.IGNORECASE)

# A handful of pages spell their own faction inconsistently (plural vs
# singular, with/without a leading "The") — normalize so they group together
# instead of splintering into near-duplicate faction buckets.
FACTION_ALIASES = {
    "The Goblins": "Goblins",
    "Hellshrew": "Hellshrews",
}


def item_groups(
    kind: str, fields: dict[str, str], title: str, wikitext: str,
    recipe: dict[str, object] | None = None,
) -> dict[str, object]:
    if kind == "oil":
        return {
            "ability": oil_buff_ability_keys(fields),
            "composition": oil_composition(fields),
        }
    if kind == "scroll":
        return {"stage": scroll_stage(title)}
    label = display_subtype(fields.get("SubType", ""))
    if kind == "weapon":
        return {"class": label, "ammo": fields.get("Ammo") or "—"}
    if kind == "consumable":
        # Whether an item actually has a parsed recipe is a much more
        # reliable "can this be combined?" signal than the wiki's
        # Category:Cookables tag, which several craftable items (Pizza
        # Slice, Sulf Cola, Salted Fish...) simply don't carry despite
        # having a full "== Recipes ==" section.
        return {"type": label, "craftable": "craftable" if recipe else "farmed"}
    if kind == "misc":
        is_organ = bool(ORGAN_CATEGORY_RE.search(wikitext))
        groups: dict[str, object] = {"type": "Organ" if is_organ else label}
        if is_organ:
            groups["organSource"] = ORGAN_SOURCE_BY_TITLE.get(title, "Common")
        return groups
    if kind == "enemy":
        faction = fields.get("Faction") or "Other"
        faction = FACTION_ALIASES.get(faction, faction)
        return {
            "faction": faction,
            "role": "Boss" if ENEMY_BOSS_RE.search(wikitext) else "Normal",
        }
    return {"type": label}


def compute_axes(kind: str, items: list[dict]) -> list[dict]:
    axes = []
    for axis in AXIS_KEYS_BY_KIND.get(kind, []):
        multi = axis in AXIS_MULTI
        counts: dict[str, int] = {}
        for it in items:
            val = it.get("groups", {}).get(axis)
            if multi:
                for v in val or []:
                    counts[v] = counts.get(v, 0) + 1
            elif val:
                counts[val] = counts.get(val, 0) + 1
        order = VALUE_ORDER.get(axis, [])
        ordered = [v for v in order if v in counts]
        rest = sorted((v for v in counts if v not in order),
                      key=lambda v: (-counts[v], str(v).lower()))
        value_keys = ordered + rest
        values = [
            {"value": v, "label": value_label(axis, v), "count": counts[v]}
            for v in value_keys
        ]
        axis_obj = {"key": axis, "label": AXIS_LABELS.get(axis, axis),
                    "multi": multi, "values": values}
        # Oil's "ability" axis has ~15 selectable stats — cluster them into
        # the same damage/fire-rate/handling/bullet/economy categories
        # already used to organize oil icon folders, so the picker can show
        # them as labeled sections instead of one long flat pill row.
        if kind == "oil" and axis == "ability":
            for val_entry, v in zip(values, value_keys):
                val_entry["group"] = OIL_STAT_GROUP.get(v, "misc")
            seen_groups: list[str] = []
            for v in value_keys:
                g = OIL_STAT_GROUP.get(v, "misc")
                if g not in seen_groups:
                    seen_groups.append(g)
            axis_obj["groups"] = [
                {"key": g, "label": OIL_GROUP_LABELS.get(g, g)} for g in seen_groups
            ]
        axes.append(axis_obj)
    return axes


def _fetch_all(titles: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        texts = fetch_wikitext_batch(batch)
        for title in batch:
            if texts.get(title):
                out[title] = texts[title]
        print(f"  fetched {min(i + 50, len(titles))}/{len(titles)}")
        time.sleep(0.3)
    return out


def load_pages(refresh: bool) -> tuple[dict[str, str], dict[str, str]]:
    """Return ({title: wikitext} for Item Infobox pages, same for Enemy
    Infobox pages), using a local cache.

    Passing refresh=True (CLI --refresh) refetches everything from the wiki
    and rewrites the cache; otherwise cached wikitext is reused with no
    network. A cache saved before enemies were added is missing
    "enemy_pages" — that's fetched on its own (without redoing the much
    larger item fetch) rather than forcing a full --refresh.
    """
    cache: dict = {}
    if CACHE_FILE.exists() and not refresh:
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        pages = cache.get("pages", {})
        print(f"Loaded {len(pages)} pages from cache "
              f"({cache.get('fetched', '?')}). Use --refresh to refetch.")
    else:
        print("Fetching page list from wiki...")
        titles = get_infobox_pages()
        print(f"  {len(titles)} pages use Item Infobox")
        pages = _fetch_all(titles)

    enemy_pages = cache.get("enemy_pages", {})
    if not enemy_pages or refresh:
        print("Fetching enemy page list from wiki...")
        enemy_titles = get_infobox_pages("Template:Enemy Infobox")
        print(f"  {len(enemy_titles)} pages use Enemy Infobox")
        enemy_pages = _fetch_all(enemy_titles)

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps({"fetched": datetime.now(timezone.utc).isoformat(),
                    "pages": pages, "enemy_pages": enemy_pages}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  cached {len(pages)} item pages + {len(enemy_pages)} enemy pages to {CACHE_FILE.name}")
    return pages, enemy_pages


CUT_CONTENT_RE = re.compile(r"\[\[\s*Category\s*:\s*Cut[ _]Content\s*\]\]", re.IGNORECASE)


def build(refresh: bool = False) -> None:
    pages, enemy_pages = load_pages(refresh)

    buckets: dict[str, list[dict]] = {k: [] for k in TARGET_KINDS}

    for title, wikitext in pages.items():
        # Skip items removed from the live game (e.g. old demo-only oils) —
        # their infobox is usually incomplete since the effect text lives in
        # free-form prose instead of structured fields.
        if CUT_CONTENT_RE.search(wikitext):
            continue
        body = extract_infobox(wikitext)
        if body is None:
            continue
        fields = parse_infobox(body)
        kind = fields.get("kind", "").strip().lower()
        if not kind and title in MISSING_KIND_BY_TITLE:
            kind = MISSING_KIND_BY_TITLE[title]
        if kind not in buckets:
            continue
        if kind == "attachment":
            zoom = attachment_zoom(fields, wikitext)
            if zoom:
                fields["Zoom"] = zoom
        if kind == "consumable":
            for prose_key, prose_val in consumable_prose_effects(wikitext).items():
                fields.setdefault(prose_key, prose_val)
        image = fields.get("image") or fields.get("Image") or f"{title}.png"
        recipe = consumable_recipe(wikitext) if kind == "consumable" else None
        item = {
            "name": title,
            "page": WIKI + urllib.parse.quote(title.replace(" ", "_")),
            "image": image,
            "groups": item_groups(kind, fields, title, wikitext, recipe),
            "fields": {k: v for k, v in fields.items()
                       if k not in ("kind", "image", "Image", "title")},
        }
        if recipe:
            item["recipe"] = recipe
        if kind == "weapon":
            compat = weapon_attachment_compat(wikitext)
            if compat:
                item["attachmentCompat"] = compat
            caliber_modding = weapon_caliber_modding(wikitext)
            if caliber_modding:
                item["caliberModding"] = caliber_modding
        buckets[kind].append(item)

    for title, wikitext in enemy_pages.items():
        if CUT_CONTENT_RE.search(wikitext):
            continue
        body = extract_infobox(wikitext, ENEMY_INFOBOX_START_RE)
        if body is None:
            continue
        fields = parse_infobox(body)
        image = fields.get("image") or fields.get("Image") or f"{title}.png"
        item = {
            "name": title,
            "page": WIKI + urllib.parse.quote(title.replace(" ", "_")),
            "image": image,
            "groups": item_groups("enemy", fields, title, wikitext),
            "fields": {k: v for k, v in fields.items()
                       if k not in ("kind", "image", "Image", "title")},
        }
        buckets["enemy"].append(item)

    download_icons(buckets)
    resolve_recipe_icons(buckets)
    attach_used_in(buckets)

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
            "axes": compute_axes(kind, items),
            "items": items,
        }
        out_path = OUT_DIR / f"{kind}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"Wrote {out_path.relative_to(OUT_DIR.parent.parent)} "
              f"({len(items)} items, {len(columns)} columns)")


if __name__ == "__main__":
    build(refresh="--refresh" in sys.argv)
