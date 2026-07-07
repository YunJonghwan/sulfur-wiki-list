import { useEffect, useMemo, useState } from 'react'
import { UI, COLUMN_KO, t } from '../i18n.js'
import { computeWeapon, computePlayerStats } from '../build.js'

const BASE = import.meta.env.BASE_URL
const DATASETS = ['weapon', 'oil', 'scroll', 'equipment', 'passive']

function imageUrl(icon) {
  return icon ? BASE + icon : null
}

function Icon({ item }) {
  const url = imageUrl(item?.icon)
  if (!url) return null
  return (
    <img
      className="item-icon"
      src={url}
      alt=""
      width="24"
      height="24"
      loading="lazy"
      onError={(e) => {
        e.currentTarget.style.visibility = 'hidden'
      }}
    />
  )
}

export default function BuildSimulator({ lang }) {
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading')

  const [weapon, setWeapon] = useState(null)
  const [level, setLevel] = useState(5)
  const [enchants, setEnchants] = useState(Array(5).fill(null))
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
  const result = computeWeapon(weapon, activeEnchants, gearItems)
  const playerStats = computePlayerStats(gearItems)

  // Names already used, to prevent duplicate oils / multiple scrolls.
  const usedOils = new Set(
    activeEnchants.filter((e) => e?.type === 'oil').map((e) => e.item.name),
  )
  const hasScroll = activeEnchants.some((e) => e?.type === 'scroll')

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
            <Icon item={weapon} />
            <select
              value={weapon?.name || ''}
              onChange={(e) => setWeapon(byName('weapon')(e.target.value))}
            >
              <option value="">{t(UI.empty, lang)}</option>
              {data.weapon.items.map((it) => (
                <option key={it.name} value={it.name}>
                  {it.name}
                </option>
              ))}
            </select>
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
          {activeEnchants.map((e, i) => {
            const encoded = e ? `${e.type}:${e.item.name}` : ''
            return (
              <div className="slot" key={i}>
                <Icon item={e?.item} />
                <select value={encoded} onChange={(ev) => setEnchant(i, ev.target.value)}>
                  <option value="">{t(UI.empty, lang)}</option>
                  <optgroup label={t(UI.scrollOpt, lang)}>
                    {data.scroll.items.map((it) => (
                      <option
                        key={it.name}
                        value={`scroll:${it.name}`}
                        disabled={hasScroll && e?.item?.name !== it.name}
                      >
                        {it.name}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label={t(UI.oilOpt, lang)}>
                    {data.oil.items.map((it) => (
                      <option
                        key={it.name}
                        value={`oil:${it.name}`}
                        disabled={usedOils.has(it.name) && e?.item?.name !== it.name}
                      >
                        {it.name}
                      </option>
                    ))}
                  </optgroup>
                </select>
              </div>
            )
          })}
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
          />
          <GearSlot
            label={t(UI.chest, lang)}
            items={equipmentByType.Chestwear}
            value={chest}
            onChange={setChest}
            lang={lang}
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
                    <tr key={s.key}>
                      <td>{labelFor(s.key)}</td>
                      <td>{s.base ?? '—'}</td>
                      <td className={diffClass(s)}>{s.final ?? '—'}</td>
                    </tr>
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
                  <div className="chips">
                    {result.extras.map((x, i) => (
                      <span key={i} className={`chip ${tone(x.value)}`}>
                        <b>{labelFor(x.key)}</b>
                        {x.value}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="result-card">
          <h3>{t(UI.playerResult, lang)}</h3>
          {playerStats.length === 0 ? (
            <p className="notice">—</p>
          ) : (
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
        </div>
      </section>
    </div>
  )
}

function GearSlot({ label, items, value, onChange, lang }) {
  return (
    <div className="slot">
      <Icon item={value} />
      <label className="slot-label">{label}</label>
      <select
        value={value?.name || ''}
        onChange={(e) =>
          onChange(items.find((it) => it.name === e.target.value) || null)
        }
      >
        <option value="">{t(UI.empty, lang)}</option>
        {items.map((it) => (
          <option key={it.name} value={it.name}>
            {it.name}
          </option>
        ))}
      </select>
    </div>
  )
}

function diffClass(s) {
  if (s.base == null || s.final == null) return ''
  // Damage/RPM: higher is better; Spread/Recoil: lower is better.
  const higherBetter = s.key === 'Damage' || s.key === 'RPM'
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
