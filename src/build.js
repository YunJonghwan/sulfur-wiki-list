// Build simulator calculations.
//
// Game rules (from the SULFUR wiki):
// - A weapon has up to 5 enchant slots (= weapon level). Slots hold oils
//   (unique, no duplicates) or a single scroll.
// - Oil/scroll stat changes apply flat (base) values first, then percentages:
//     final = (base + sumFlat) * (1 + sumPercent/100)
// - Each enchant adds +1 durability cost per shot (max 6), except oils with the
//   "Does not increase durability loss" trait. Some scrolls add a % multiplier.
// - Equipment/passives grant weapon-class damage bonuses and player stats.

export function parseNum(value) {
  if (typeof value !== 'string') return null
  const m = value.match(/([+-]?\d+(?:\.\d+)?)/)
  if (!m) return null
  return { num: parseFloat(m[1]), percent: value.includes('%') }
}

// Oil/scroll stat key -> base weapon stat key.
const MOD_TO_WEAPON = { Dmg: 'Damage', RPM: 'RPM', Spread: 'Spread', Recoil: 'Recoil', MaxDrb: 'Durability' }

export const WEAPON_STATS = ['Damage', 'RPM', 'Spread', 'Recoil', 'Durability']

// Weapon class -> the equipment/passive damage-bonus key that applies.
const CLASS_DMG_KEY = {
  Pistol: 'PistolDmg',
  Revolver: 'RevolDmg',
  'Assault Rifle': 'AssltDmg',
  'Light Machine Gun': 'LMGDmg',
  Rifle: 'RifleDmg',
  Sniper: 'SniperDmg',
  'Sniper Rifle': 'SniperDmg',
  Shotgun: 'ShotgunDmg',
  'Submachine Gun': 'AutoDmg',
}

// Player stats to aggregate from equipment + passives (key + whether it's a %).
export const PLAYER_STATS = [
  { key: 'Armor', percent: false, cap: 55 },
  { key: 'Speed', percent: true },
  { key: 'Sprint', percent: true },
  { key: 'SwimSpeed', percent: true },
  { key: 'JumpPwr', percent: true },
  { key: 'ExtraJumps', percent: false },
  { key: 'Coyote', percent: false },
  { key: 'MoveAccuracy', percent: true },
  { key: 'Luck', percent: false },
  { key: 'Charisma', percent: false },
  { key: 'LungCpty', percent: false },
  { key: 'FireRst', percent: false, cap: 100 },
  { key: 'FrostRst', percent: false, cap: 100 },
  { key: 'PsnRst', percent: false, cap: 100 },
  { key: 'ElecRst', percent: false, cap: 100 },
  { key: 'LightRst', percent: false, cap: 100 },
  { key: 'ExplRst', percent: false, cap: 100 },
  { key: 'CharmRst', percent: false, cap: 100 },
]

const DURABILITY_MAX = 6

function fieldsOf(item) {
  return item && item.fields ? item.fields : {}
}

// True for values that are just a number (+ optional short unit like "s")
// with no extra condition attached, e.g. "+0.5s" or "+20%". False for
// conditional text like "+100% while crouching" or "+20% after eating" —
// those aren't safe to fold into a flat sum, since they don't always apply.
function isPlainModifier(raw) {
  if (typeof raw !== 'string') return false
  const m = raw.match(/^[+-]?\d+(?:\.\d+)?%?/)
  if (!m) return false
  const rest = raw.slice(m[0].length).trim()
  return rest === '' || /^[a-z]{1,3}$/i.test(rest)
}

// Aggregate a numeric stat across a list of items (sums the parsed numbers).
// Conditional values (see isPlainModifier) are skipped here and surfaced
// as-is via computeGearExtras instead, so their condition stays visible.
function sumStat(items, key) {
  let total = 0
  let found = false
  for (const it of items) {
    const raw = fieldsOf(it)[key]
    if (!isPlainModifier(raw)) continue
    const p = parseNum(raw)
    if (p) {
      total += p.num
      found = true
    }
  }
  return found ? total : null
}

export function computePlayerStats(gearItems) {
  const items = gearItems.filter(Boolean)
  const out = []
  for (const stat of PLAYER_STATS) {
    let value = sumStat(items, stat.key)
    if (value == null) continue
    if (stat.cap != null) value = Math.min(value, stat.cap)
    out.push({ key: stat.key, value, percent: stat.percent, cap: stat.cap })
  }
  return out
}

const GEAR_META = new Set([
  'GridSize', 'SellVal', 'BuyVal', 'SoldBy', 'Durability', 'SubType', 'Type',
])
const PLAYER_STAT_KEYS = new Set(PLAYER_STATS.map((s) => s.key))

// Equipment/passive fields that aren't one of the aggregated PLAYER_STATS
// (weapon-class damage bonuses, on-hit effects, flavor flags…) — shown
// as-is so every selected gear piece's effect is visible somewhere.
//
// The same item can be equipped in more than one slot (e.g. two identical
// boots in both footwear slots), and its effect really does apply twice —
// so instead of collapsing duplicates into a single entry, plain numeric
// modifiers are stacked (×2 the value) and non-numeric ones keep a "×N"
// count, rather than silently hiding the repeat.
export function computeGearExtras(gearItems) {
  const items = gearItems.filter(Boolean)
  const groups = new Map()
  for (const it of items) {
    const f = fieldsOf(it)
    for (const [k, v] of Object.entries(f)) {
      if (!v || GEAR_META.has(k)) continue
      // Player-stat keys are already summed into the flat total above —
      // unless the value is conditional (e.g. "while crouching"), in which
      // case it was deliberately left out of the sum and belongs here.
      if (PLAYER_STAT_KEYS.has(k) && isPlainModifier(v)) continue
      const gkey = `${it.name}::${k}::${v}`
      const existing = groups.get(gkey)
      if (existing) existing.count += 1
      else groups.set(gkey, { from: it.name, key: k, value: v, count: 1 })
    }
  }

  const extras = []
  for (const g of groups.values()) {
    if (g.count === 1) {
      extras.push({ from: g.from, key: g.key, value: g.value })
      continue
    }
    const from = `${g.from} ×${g.count}`
    const m = g.value.match(/^([+-]?)(\d+(?:\.\d+)?)(%?)/)
    if (m && isPlainModifier(g.value)) {
      const signed = (m[1] === '-' ? -1 : 1) * parseFloat(m[2])
      const total = Math.round(signed * g.count * 100) / 100
      const suffix = g.value.slice(m[0].length)
      extras.push({ from, key: g.key, value: `${total >= 0 ? '+' : ''}${total}${m[3]}${suffix}` })
    } else {
      extras.push({ from, key: g.key, value: g.value })
    }
  }
  return extras
}

// Compute final weapon stats given enchants (oils/scroll) and gear bonuses.
export function computeWeapon(weapon, enchants, gearItems) {
  if (!weapon) return null
  const wf = fieldsOf(weapon)
  const enchItems = enchants.filter((e) => e && e.item)
  const gear = gearItems.filter(Boolean)
  const weaponClass = weapon.groups?.class
  const isAuto = (wf.Mode || '').toLowerCase().includes('auto')

  // Gather flat/percent modifiers per weapon stat from oils + scroll.
  const flat = {}
  const pct = {}
  for (const s of WEAPON_STATS) {
    flat[s] = 0
    pct[s] = 0
  }
  for (const { item } of enchItems) {
    const f = fieldsOf(item)
    for (const [modKey, weaponKey] of Object.entries(MOD_TO_WEAPON)) {
      const p = parseNum(f[modKey])
      if (!p) continue
      if (p.percent) pct[weaponKey] += p.num
      else flat[weaponKey] += p.num
    }
  }

  // Weapon-class damage bonus from gear/passives adds to Damage percent.
  const classKey = CLASS_DMG_KEY[weaponClass]
  let gearDmgPct = 0
  for (const it of gear) {
    const f = fieldsOf(it)
    if (classKey) {
      const p = parseNum(f[classKey])
      if (p && p.percent) gearDmgPct += p.num
    }
    if (isAuto) {
      const a = parseNum(f.AutoDmg)
      if (a && a.percent && classKey !== 'AutoDmg') gearDmgPct += a.num
    }
  }
  pct.Damage += gearDmgPct

  const stats = WEAPON_STATS.map((s) => {
    const bp = parseNum(wf[s])
    const base = bp ? bp.num : null
    if (base == null) return { key: s, base: null, final: null }
    const final = (base + flat[s]) * (1 + pct[s] / 100)
    return {
      key: s,
      base,
      final: Math.round(final * 100) / 100,
      flat: flat[s],
      pct: pct[s],
    }
  })

  // Durability per shot.
  let durInc = 0
  let scroll = null
  for (const e of enchItems) {
    if (e.type === 'scroll') scroll = e.item
    const f = fieldsOf(e.item)
    const noDrb = 'NoDrb' in f
    if (!noDrb) durInc += 1
  }
  let durability = Math.min(1 + durInc, DURABILITY_MAX)
  if (scroll) {
    const dc = parseNum(fieldsOf(scroll).DrbConsume)
    if (dc && dc.percent) durability = durability * (1 + dc.num / 100)
  }
  durability = Math.round(durability * 100) / 100

  // Other oil/scroll modifiers that aren't one of the base weapon stats.
  const extras = []
  const seen = new Set()
  const META = new Set(['GridSize', 'SellVal', 'BuyVal', 'SoldBy', 'SubType'])
  for (const { item } of enchItems) {
    const f = fieldsOf(item)
    for (const [k, v] of Object.entries(f)) {
      if (k in MOD_TO_WEAPON || META.has(k)) continue
      const tag = `${k}:${v}`
      if (seen.has(tag)) continue
      seen.add(tag)
      extras.push({ from: item.name, key: k, value: v })
    }
  }

  return { stats, durability, extras, gearDmgPct }
}
