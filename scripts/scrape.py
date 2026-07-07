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
    "oil": ["ability"],
    "attachment": ["type"],
    "equipment": ["type"],
    "consumable": ["type"],
}

AXIS_LABELS = {
    "class": "Weapon Type",
    "ammo": "Ammunition",
    "ability": "Ability",
    "type": "Type",
}

# Axes where an item can belong to several groups at once (e.g. an oil that
# modifies both Damage and Recoil shows up under each ability).
AXIS_MULTI = {"ability"}

# Preferred display order for some axes; anything else is appended by count.
VALUE_ORDER = {
    "class": [
        "Pistol", "Revolver", "Shotgun", "Submachine Gun", "Assault Rifle",
        "Light Machine Gun", "Rifle", "Sniper Rifle", "Melee",
    ],
    "ammo": ["9mm", "5.56mm", "7.62mm", ".50 BMG", "12Ga", "Energy Cell"],
    # Oils split by individual ability, in the infobox stat order.
    "ability": KIND_COLUMNS["oil"],
}


def display_subtype(subtype: str) -> str:
    """Human-readable, consolidated subtype label (matches icon folders)."""
    if not subtype:
        return "Other"
    slug = subtype_slug(subtype)
    return slug.replace("-", " ").title()


def value_label(axis: str, value: str) -> str:
    if axis == "ability":
        return LABELS.get(value, value)
    return value


def oil_ability_keys(fields: dict[str, str]) -> list[str]:
    """Individual ability keys an oil has, in infobox order (no meta fields)."""
    return [
        k for k in KIND_COLUMNS["oil"]
        if k in fields and k not in IGNORE_FOR_GROUPING
    ]


def item_groups(kind: str, fields: dict[str, str]) -> dict[str, object]:
    if kind == "oil":
        return {"ability": oil_ability_keys(fields)}
    label = display_subtype(fields.get("SubType", ""))
    if kind == "weapon":
        return {"class": label, "ammo": fields.get("Ammo") or "—"}
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
        values = [
            {"value": v, "label": value_label(axis, v), "count": counts[v]}
            for v in ordered + rest
        ]
        axes.append({"key": axis, "label": AXIS_LABELS.get(axis, axis),
                     "multi": multi, "values": values})
    return axes


def load_pages(refresh: bool) -> dict[str, str]:
    """Return {title: wikitext} for all Item Infobox pages, using a local cache.

    Passing refresh=True (CLI --refresh) refetches everything from the wiki and
    rewrites the cache; otherwise the cached wikitext is reused with no network.
    """
    if CACHE_FILE.exists() and not refresh:
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        pages = cache.get("pages", {})
        print(f"Loaded {len(pages)} pages from cache "
              f"({cache.get('fetched', '?')}). Use --refresh to refetch.")
        return pages

    print("Fetching page list from wiki...")
    titles = get_infobox_pages()
    print(f"  {len(titles)} pages use Item Infobox")
    pages: dict[str, str] = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        texts = fetch_wikitext_batch(batch)
        for title in batch:
            if texts.get(title):
                pages[title] = texts[title]
        print(f"  fetched {min(i + 50, len(titles))}/{len(titles)}")
        time.sleep(0.3)

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps({"fetched": datetime.now(timezone.utc).isoformat(),
                    "pages": pages}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  cached {len(pages)} pages to {CACHE_FILE.name}")
    return pages


def build(refresh: bool = False) -> None:
    pages = load_pages(refresh)

    buckets: dict[str, list[dict]] = {k: [] for k in TARGET_KINDS}

    for title, wikitext in pages.items():
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
            "groups": item_groups(kind, fields),
            "fields": {k: v for k, v in fields.items()
                       if k not in ("kind", "image", "title")},
        }
        buckets[kind].append(item)

    download_icons(buckets)

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
