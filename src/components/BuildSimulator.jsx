import { Fragment, useEffect, useMemo, useState } from 'react'
import { UI, COLUMN_KO, t, groupLabel } from '../i18n.js'
import {
  computeWeapon, computePlayerStats, computeGearExtras, computeHitboxDamage,
  isAttachmentCompatible,
} from '../build.js'
import ItemPicker from './ItemPicker.jsx'

const BASE = import.meta.env.BASE_URL
const DATASETS = ['weapon', 'oil', 'scroll', 'equipment', 'passive', 'attachment', 'chisel']

// Attachment slot -> the attachment.json "type" group it holds.
const ATTACHMENT_SLOTS = [
  { key: 'muzzle', type: 'Muzzle Attachment' },
  { key: 'sight', type: 'Sight' },
  { key: 'laser', type: 'Laser Sight' },
  { key: 'chamber', type: 'Chamber Attachment' },
]

export default function BuildSimulator({ lang }) {
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading')

  const [weapon, setWeapon] = useState(null)
  const [level, setLevel] = useState(5)
  const [enchants, setEnchants] = useState(Array(5).fill(null))
  const [attachments, setAttachments] = useState({ muzzle: null, sight: null, laser: null, chamber: null })
  const [chisel, setChisel] = useState(null)
  const [head, setHead] = useState(null)
  const [chest, setChest] = useState(null)
  const [feet, setFeet] = useState([null, null])
  const [passives, setPassives] = useState([null, null, null, null])

  useEffect(() => {
    let cancelled = false
    Promise.all(
      DATASETS.map((k) => fetch(`${BASE}data/${k}.json`).then((r) => r.json())),
    )
      .then((results) => {
        if (cancelled) return
        const map = {}
        DATASETS.forEach((k, i) => (map[k] = results[i]))
        setData(map)
        setStatus('ready')
      })
      .catch(() => !cancelled && setStatus('error'))
    return () => {
      cancelled = true
    }
  }, [])

  // A weapon's accepted attachment types/items (and available calibers)
  // differs from the last one — drop any picks that might no longer apply.
  useEffect(() => {
    setAttachments({ muzzle: null, sight: null, laser: null, chamber: null })
    setChisel(null)
  }, [weapon])

  const labelMap = useMemo(() => {
    const m = {}
    if (data) {
      for (const k of DATASETS) {
        for (const c of data[k].columns) m[c.key] = c.label
      }
    }
    return m
  }, [data])

  const labelFor = (key) =>
    (lang === 'ko' && COLUMN_KO[key]) || labelMap[key] || key

  const byName = (ds) => (name) =>
    data[ds].items.find((it) => it.name === name) || null

  const equipmentByType = useMemo(() => {
    const g = { Headwear: [], Chestwear: [], Footwear: [] }
    if (data) {
      for (const it of data.equipment.items) {
        const tp = it.groups?.type
        if (g[tp]) g[tp].push(it)
      }
    }
    return g
  }, [data])

  if (status === 'loading') return <p className="notice">{t(UI.loading, lang)}</p>
  if (status === 'error') return <p className="notice error">{t(UI.error, lang)}</p>

  const activeEnchants = enchants.slice(0, level)
  const gearItems = [head, chest, feet[0], feet[1], ...passives]
  const attachmentItems = ATTACHMENT_SLOTS.map((s) => attachments[s.key])
  const result = computeWeapon(weapon, activeEnchants, gearItems, attachmentItems, chisel)
  const playerStats = computePlayerStats(gearItems)
  const gearExtras = computeGearExtras(gearItems)

  const compatibleAttachments = (type) =>
    weapon ? data.attachment.items.filter((it) => it.groups?.type === type && isAttachmentCompatible(weapon, it)) : []

  // Only chisels this weapon's own Caliber Modding table actually lists.
  const compatibleChisels = weapon
    ? data.chisel.items.filter((c) =>
        weapon.caliberModding?.some(
          (r) => r.caliber.replace(/\s+/g, '').toLowerCase() === (c.fields.ChamberAmmo || '').replace(/\s+/g, '').toLowerCase(),
        ),
      )
    : []

  // Names already used, to prevent duplicate oils / multiple scrolls.
  const usedOils = new Set(
    activeEnchants.filter((e) => e?.type === 'oil').map((e) => e.item.name),
  )

  const weaponSections = [
    { key: 'weapon', items: data.weapon.items, axes: data.weapon.axes },
  ]
  const enchantSections = [
    {
      key: 'scroll',
      label: t(UI.scrollOpt, lang),
      items: data.scroll.items,
      axes: data.scroll.axes,
    },
    { key: 'oil', label: t(UI.oilOpt, lang), items: data.oil.items, axes: data.oil.axes },
  ]

  function enchantDisabled(item, sectionKey, idx) {
    if (sectionKey === 'oil') {
      const current = activeEnchants[idx]?.item?.name
      return usedOils.has(item.name) && current !== item.name
    }
    if (sectionKey === 'scroll') {
      // Only one scroll total across all slots — but freely swappable within
      // the slot that already holds it.
      return activeEnchants.some((e, i) => i !== idx && e?.type === 'scroll')
    }
    return false
  }

  function setEnchant(idx, encoded) {
    setEnchants((prev) => {
      const next = [...prev]
      if (!encoded) next[idx] = null
      else {
        const [type, ...rest] = encoded.split(':')
        const name = rest.join(':')
        const item = byName(type === 'scroll' ? 'scroll' : 'oil')(name)
        next[idx] = item ? { type, item } : null
      }
      return next
    })
  }

  const fmtStat = (s) => {
    if (s.value == null) return '—'
    const sign = s.value > 0 ? '+' : ''
    return `${sign}${s.value}${s.percent ? '%' : ''}${s.cap && s.value >= s.cap ? ' (max)' : ''}`
  }

  return (
    <div className="build">
      <section className="build-loadout">
        {/* Weapon + enchantments */}
        <div className="slot-group">
          <h3>{t(UI.weaponSlot, lang)}</h3>
          <div className="slot">
            <ItemPicker
              lang={lang}
              value={weapon}
              sections={weaponSections}
              onSelect={(item) => setWeapon(item)}
              onClear={() => setWeapon(null)}
              labelFor={labelFor}
            />
          </div>

          <label className="level-row">
            {t(UI.level, lang)}:
            <select value={level} onChange={(e) => setLevel(Number(e.target.value))}>
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>

          <div className="enchant-label">{t(UI.enchantSlots, lang)}</div>
          {activeEnchants.map((e, i) => (
            <div className="slot" key={i}>
              <ItemPicker
                lang={lang}
                value={e?.item || null}
                sections={enchantSections}
                isDisabled={(item, sectionKey) => enchantDisabled(item, sectionKey, i)}
                onSelect={(item, sectionKey) => setEnchant(i, `${sectionKey}:${item.name}`)}
                onClear={() => setEnchant(i, '')}
                labelFor={labelFor}
              />
            </div>
          ))}
        </div>

        {/* Attachments — only shown as pickable once a weapon is chosen,
            since which types/items fit depends on the weapon itself. */}
        <div className="slot-group">
          <h3>{t(UI.attachmentSlots, lang)}</h3>
          {ATTACHMENT_SLOTS.map((s) => (
            <GearSlot
              key={s.key}
              label={groupLabel(s.type, s.type, lang)}
              items={compatibleAttachments(s.type)}
              value={attachments[s.key]}
              onChange={(v) => setAttachments((prev) => ({ ...prev, [s.key]: v }))}
              lang={lang}
              labelFor={labelFor}
            />
          ))}
          <GearSlot
            label={t(UI.chamberChisel, lang)}
            items={compatibleChisels}
            value={chisel}
            onChange={setChisel}
            lang={lang}
            labelFor={labelFor}
          />
        </div>

        {/* Armor */}
        <div className="slot-group">
          <h3>{t(UI.armorSlots, lang)}</h3>
          <GearSlot
            label={t(UI.head, lang)}
            items={equipmentByType.Headwear}
            value={head}
            onChange={setHead}
            lang={lang}
            labelFor={labelFor}
          />
          <GearSlot
            label={t(UI.chest, lang)}
            items={equipmentByType.Chestwear}
            value={chest}
            onChange={setChest}
            lang={lang}
            labelFor={labelFor}
          />
          {[0, 1].map((i) => (
            <GearSlot
              key={i}
              label={`${t(UI.foot, lang)} ${i + 1}`}
              items={equipmentByType.Footwear}
              value={feet[i]}
              onChange={(v) =>
                setFeet((prev) => prev.map((x, j) => (j === i ? v : x)))
              }
              lang={lang}
              labelFor={labelFor}
            />
          ))}
        </div>

        {/* Passives */}
        <div className="slot-group">
          <h3>{t(UI.passiveSlots, lang)}</h3>
          {[0, 1, 2, 3].map((i) => (
            <GearSlot
              key={i}
              label={`${t(UI.passive, lang)} ${i + 1}`}
              items={data.passive.items}
              value={passives[i]}
              onChange={(v) =>
                setPassives((prev) => prev.map((x, j) => (j === i ? v : x)))
              }
              lang={lang}
              labelFor={labelFor}
            />
          ))}
        </div>
      </section>

      {/* Results */}
      <section className="build-results">
        <div className="result-card">
          <h3>{t(UI.weaponResult, lang)}</h3>
          {!weapon ? (
            <p className="notice">{t(UI.pickWeapon, lang)}</p>
          ) : (
            <>
              <table className="result-table">
                <thead>
                  <tr>
                    <th></th>
                    <th>{t(UI.base, lang)}</th>
                    <th>{t(UI.final, lang)}</th>
                  </tr>
                </thead>
                <tbody>
                  {result.stats.map((s) => (
                    <Fragment key={s.key}>
                      <tr>
                        <td>{labelFor(s.key)}</td>
                        <td>{s.base ?? '—'}</td>
                        <td className={diffClass(s)}>{s.final ?? '—'}</td>
                      </tr>
                      {s.key === 'Damage' && result.projectileCount != null && (
                        <tr className="derived-stat-row">
                          <td>{t(UI.projectileCount, lang)}</td>
                          <td>{result.baseProjectiles}</td>
                          <td className={diffClass({ base: result.baseProjectiles, final: result.projectileCount, key: 'Damage' })}>
                            {result.projectileCount}
                          </td>
                        </tr>
                      )}
                      {s.key === 'Damage' && result.totalDamage != null && (
                        <tr className="derived-stat-row">
                          <td>{t(UI.totalDamage, lang)}</td>
                          <td>{result.totalDamageBase ?? '—'}</td>
                          <td className={diffClass({ base: result.totalDamageBase, final: result.totalDamage, key: s.key })}>
                            {result.totalDamage}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                  <tr>
                    <td>{t(UI.durabilityPerShot, lang)}</td>
                    <td>1</td>
                    <td>{result.durability}</td>
                  </tr>
                </tbody>
              </table>

              {result.extras.length > 0 && (
                <div className="extras">
                  <div className="extras-title">{t(UI.otherEffects, lang)}</div>
                  <ExtraGroups extras={result.extras} labelFor={labelFor} lang={lang} />
                </div>
              )}
            </>
          )}
        </div>

        <div className="result-card">
          <h3>{t(UI.hitboxTitle, lang)}</h3>
          {!weapon ? (
            <p className="notice">{t(UI.pickWeapon, lang)}</p>
          ) : (
            <table className="result-table">
              <thead>
                <tr>
                  <th>{t(UI.hitboxPart, lang)}</th>
                  <th>{t(UI.hitboxMult, lang)}</th>
                  <th>{t(UI.hitboxPerHit, lang)}</th>
                  {result.projectileCount != null && <th>{t(UI.hitboxTotal, lang)}</th>}
                </tr>
              </thead>
              <tbody>
                {computeHitboxDamage(result).map((h) => (
                  <tr key={h.key}>
                    <td>{groupLabel(h.key, h.key, lang)}</td>
                    <td>×{h.mult}</td>
                    <td>{h.perHit}</td>
                    {result.projectileCount != null && <td>{h.total}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="result-card">
          <h3>{t(UI.playerResult, lang)}</h3>
          {playerStats.length === 0 && gearExtras.length === 0 ? (
            <p className="notice">—</p>
          ) : (
            <>
              {playerStats.length > 0 && (
                <table className="result-table">
                  <tbody>
                    {playerStats.map((s) => (
                      <tr key={s.key}>
                        <td>{labelFor(s.key)}</td>
                        <td className={s.value >= 0 ? 'pos' : 'neg'}>{fmtStat(s)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {gearExtras.length > 0 && (
                <div className="extras">
                  <div className="extras-title">{t(UI.otherEffects, lang)}</div>
                  <div className="chips">
                    {gearExtras.map((x, i) => (
                      <span key={i} className={`chip ${tone(x.value)}`}>
                        <b>
                          {x.from} · {labelFor(x.key)}
                        </b>
                        {x.value}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </section>
    </div>
  )
}

const DIRECTION_ORDER = ['buff', 'debuff', 'constraint']
const DIRECTION_TONE = { buff: 'pos', debuff: 'neg', constraint: '' }

// Splits weapon extras into buff/debuff/constraint sections instead of one
// flat list colored purely by +/- sign — a stat like Recoil or Spread is a
// buff when it goes DOWN, so a naive sign check shows it backwards.
function ExtraGroups({ extras, labelFor, lang }) {
  return (
    <>
      {DIRECTION_ORDER.map((dir) => {
        const items = extras.filter((x) => x.direction === dir)
        if (items.length === 0) return null
        return (
          <div className="extras-group" key={dir}>
            <div className={`extras-subtitle ${dir}`}>{groupLabel(dir, dir, lang)}</div>
            <div className="chips">
              {items.map((x, i) => (
                <span key={i} className={`chip ${DIRECTION_TONE[dir]}`}>
                  <b>{labelFor(x.key)}</b>
                  {x.value}
                </span>
              ))}
            </div>
          </div>
        )
      })}
    </>
  )
}

function GearSlot({ label, items, value, onChange, lang, labelFor }) {
  return (
    <div className="slot">
      <label className="slot-label">{label}</label>
      <ItemPicker
        lang={lang}
        value={value}
        sections={[{ key: 'item', items }]}
        onSelect={(item) => onChange(item)}
        onClear={() => onChange(null)}
        labelFor={labelFor}
      />
    </div>
  )
}

function diffClass(s) {
  if (s.base == null || s.final == null) return ''
  // Damage/RPM/Durability: higher is better; Spread/Recoil: lower is better.
  const higherBetter = s.key === 'Damage' || s.key === 'RPM' || s.key === 'Durability'
  if (s.final === s.base) return ''
  const better = higherBetter ? s.final > s.base : s.final < s.base
  return better ? 'pos' : 'neg'
}

function tone(raw) {
  if (typeof raw !== 'string') return ''
  if (/^\+/.test(raw)) return 'pos'
  if (/^-/.test(raw) || /^−/.test(raw)) return 'neg'
  return ''
}
