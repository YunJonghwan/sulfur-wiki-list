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

// Some shotguns encode their pellet count right in the Damage field instead
// of a separate stat — "40×8" (8 pellets at 40 each), "40×8×3" (Arbiter 2:
// 8 pellets × 3 barrels fired at once — confirmed on its wiki page), "50×3×3"
// (Augusta: 3 pellets × 3 cells/shot). All the "×N" factors multiply
// together for the base projectile count; a trailing "(×1-8)" variable-charge
// range (Breacher 8) is dropped rather than guessed at, leaving its normal
// pellet count.
export function parseDamageField(raw) {
  if (typeof raw !== 'string') return null
  const m = raw.match(/^(\d+(?:\.\d+)?)((?:\s*×\s*\d+(?:\.\d+)?)*)/)
  if (!m) return null
  const perProjectile = parseFloat(m[1])
  const factors = [...m[2].matchAll(/×\s*(\d+(?:\.\d+)?)/g)].map((x) => parseFloat(x[1]))
  const count = factors.length ? factors.reduce((a, b) => a * b, 1) : 1
  return { perProjectile, count }
}

// Mirrors classify_ability() in scripts/scrape.py (same stat-direction
// tables) — used there to label an oil's overall composition, used here to
// sort each individual "other effect" chip into buff/debuff/constraint
// instead of coloring purely off the +/- sign, which gets stats where lower
// is better (Spread, Recoil, ...) backwards.
const BUFF_WHEN_UP = new Set([
  'Dmg', 'RPM', 'CritChance', 'RldSpeed', 'BltSpeed', 'BltPen', 'BltSize',
  'BltBounces', 'BltBounciness', 'ProjecAmnt', 'MaxDrb', 'Speed', 'JumpPwr',
  'LootChance', 'MoveAccuracy', 'PenDmgMult', 'LootRolls',
])
const BUFF_WHEN_DOWN = new Set(['Spread', 'Recoil', 'Drag', 'BltDrop', 'AmmoConsume', 'AmmoExConsume'])
const CONSTRAINTS = new Set([
  'AimDisabled', 'NoMoney', 'NoOrgans', 'Blindfolded', 'SelfBlind', 'WearSJ',
  'WearGoggles', 'WearShades', 'WearEarPro',
])
const DEBUFF_EFFECTS = new Set(['SelfDmg', 'LessForceSpd', 'MoreDmgOnHit'])

function signOf(value) {
  const v = String(value).trim()
  if (v.startsWith('+')) return 1
  if (v.startsWith('-') || v.startsWith('−')) return -1
  return 0
}

// For stats like Spread/Recoil where a bigger number is worse, "best first"
// means ascending (most negative reduction on top), not descending.
export function isLowerBetter(key) {
  return BUFF_WHEN_DOWN.has(key)
}

export function classifyAbility(key, value) {
  if (CONSTRAINTS.has(key)) return 'constraint'
  if (DEBUFF_EFFECTS.has(key)) return 'debuff'
  const sign = signOf(value)
  if (BUFF_WHEN_UP.has(key)) return sign >= 0 ? 'buff' : 'debuff'
  if (BUFF_WHEN_DOWN.has(key)) return sign < 0 ? 'buff' : 'debuff'
  return 'buff'
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
export function computeWeapon(weapon, enchants, gearItems, attachmentItems = []) {
  if (!weapon) return null
  const wf = fieldsOf(weapon)
  const enchItems = enchants.filter((e) => e && e.item)
  // Attachments modify weapon stats the same way oils do, but — unlike
  // enchant slots — don't cost extra durability per shot, so they're kept
  // out of enchItems (used below for the durability calc) and only merged
  // in for the stat/extras math.
  const attachEnch = attachmentItems.filter(Boolean).map((item) => ({ type: 'attachment', item }))
  const modItems = [...enchItems, ...attachEnch]
  const gear = gearItems.filter(Boolean)
  const weaponClass = weapon.groups?.class
  const isAuto = (wf.Mode || '').toLowerCase().includes('auto')

  // Gather flat/percent modifiers per weapon stat from oils + scroll + attachments.
  const flat = {}
  const pct = {}
  for (const s of WEAPON_STATS) {
    flat[s] = 0
    pct[s] = 0
  }
  for (const { item } of modItems) {
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

  // A shotgun's own Damage field already bakes in a pellet count ("40×8"),
  // so its "Damage" stat above is per-pellet, not per-trigger-pull — and an
  // oil trading Damage for more projectiles (e.g. -30% Damage, +200%
  // Projectile Amount) makes that per-pellet row alone look like a pure
  // nerf. Surface the actual projectile count and the resulting per-shot
  // total, so it's clear whether the net change is really a loss.
  const dmgField = parseDamageField(wf.Damage)
  const baseProjectiles = dmgField ? dmgField.count : 1
  let projecPct = 0
  for (const { item } of modItems) {
    const p = parseNum(fieldsOf(item).ProjecAmnt)
    if (p && p.percent) projecPct += p.num
  }
  const projectileCount =
    baseProjectiles > 1 || projecPct !== 0
      ? Math.round(baseProjectiles * (1 + projecPct / 100) * 100) / 100
      : null
  const damageStat = stats.find((s) => s.key === 'Damage')
  const totalDamage =
    projectileCount != null && damageStat && damageStat.final != null
      ? Math.round(damageStat.final * projectileCount * 100) / 100
      : null
  // Vanilla (no-enchant) total, for coloring totalDamage by the build's real
  // net effect instead of against the misleading single-pellet base.
  const totalDamageBase =
    projectileCount != null && damageStat && damageStat.base != null
      ? Math.round(damageStat.base * baseProjectiles * 100) / 100
      : null

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

  // Every oil/scroll modifier, listed per-effect under buff/debuff/constraint
  // — including the core weapon stats (Dmg/RPM/Spread/Recoil/MaxDrb) that
  // are ALSO summarized in the base/final table above. The table shows the
  // combined end result; this shows which oil did what, individually.
  // Same-stat combining: two oils hitting the same key (e.g. Bullet Bounces
  // +4 and +2) used to show as two separate chips — combined here into one
  // "+6" when they're both plain numeric modifiers of the same unit (both
  // flat or both %); anything that can't be summed (flags, mixed
  // flat/percent) is still listed as distinct entries.
  const META = new Set(['GridSize', 'SellVal', 'BuyVal', 'SoldBy', 'SubType'])
  const byExtraKey = new Map()
  for (const { item } of modItems) {
    const f = fieldsOf(item)
    for (const [k, v] of Object.entries(f)) {
      if (META.has(k)) continue
      if (!byExtraKey.has(k)) byExtraKey.set(k, [])
      byExtraKey.get(k).push({ from: item.name, value: v, num: parseNum(v) })
    }
  }
  const extras = []
  for (const [k, entries] of byExtraKey) {
    // Single source: keep the raw value untouched (no risk of losing a "×N"
    // multiplier or other formatting by round-tripping it through parseNum).
    if (entries.length === 1) {
      const value = entries[0].value
      extras.push({ from: entries[0].from, key: k, value, direction: classifyAbility(k, value) })
      continue
    }
    // "×N" multipliers stack multiplicatively, not additively — only sum
    // when every entry is a plain +/- flat or percent modifier.
    const multiplicative = entries.some((e) => /[×x]/i.test(e.value))
    const sameUnit =
      !multiplicative &&
      entries.every((e) => e.num) &&
      entries.every((e) => e.num.percent === entries[0].num.percent)
    if (sameUnit) {
      const total = entries.reduce((sum, e) => sum + e.num.num, 0)
      const rounded = Math.round(total * 100) / 100
      const value = `${rounded >= 0 ? '+' : ''}${rounded}${entries[0].num.percent ? '%' : ''}`
      const from = entries.map((e) => e.from).join(' + ')
      extras.push({ from, key: k, value, direction: classifyAbility(k, value) })
    } else {
      const seenVals = new Set()
      for (const e of entries) {
        if (seenVals.has(e.value)) continue
        seenVals.add(e.value)
        extras.push({ from: e.from, key: k, value: e.value, direction: classifyAbility(k, e.value) })
      }
    }
  }

  return {
    stats, durability, extras, gearDmgPct,
    totalDamage, totalDamageBase, baseProjectiles, projectileCount,
  }
}

// Weapon compatibility list entries are wiki link targets, some naming an
// attachment type category ("Muzzle Attachments", plural) and some naming
// one specific item ("Gun Crank", "Priming Bolt" — chamber attachments
// apparently aren't universally interchangeable, per-weapon).
function stripTrailingS(s) {
  return s.endsWith('s') ? s.slice(0, -1) : s
}

export function isAttachmentCompatible(weapon, attachment) {
  const compat = weapon?.attachmentCompat
  if (!compat) return false
  return compat.some((c) => stripTrailingS(c) === attachment.groups?.type || c === attachment.name)
}

// Hitbox damage multipliers — a single table shared by every weapon/enemy,
// not weapon-specific (https://sulfur.wiki.gg/wiki/Gameplay, "Hitboxes").
export const HITBOXES = [
  { key: 'Head', mult: 1 },
  { key: 'Eye', mult: 1.5 },
  { key: 'Throat', mult: 0.75 },
  { key: 'Body', mult: 0.5 },
  { key: 'Limb', mult: 0.25 },
]

// Per-hit (single projectile) and per-shot (every projectile, e.g. a
// shotgun's full pellet spread) damage for each hitbox, given a
// computeWeapon() result.
export function computeHitboxDamage(result) {
  const damageStat = result.stats.find((s) => s.key === 'Damage')
  if (!damageStat || damageStat.final == null) return []
  const perProjectile = damageStat.final
  const projectiles = result.projectileCount ?? result.baseProjectiles ?? 1
  return HITBOXES.map((h) => ({
    key: h.key,
    mult: h.mult,
    perHit: Math.round(perProjectile * h.mult * 100) / 100,
    total: Math.round(perProjectile * h.mult * projectiles * 100) / 100,
  }))
}
