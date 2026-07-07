import { useMemo, useState } from 'react'
import { UI, COLUMN_KO, t, groupLabel, axisLabel } from '../i18n.js'

const BASE = import.meta.env.BASE_URL

// Non-ability meta fields — hidden from the compact "Abilities" chips so only
// real stat modifiers/effects show. Still visible in the full grid view.
const META_KEYS = new Set(['GridSize', 'SellVal', 'BuyVal', 'SoldBy'])

function imageUrl(icon) {
  if (!icon) return null
  return BASE + icon
}

// Extract a numeric value for sorting; returns NaN when none is present.
function numericValue(raw) {
  if (raw == null || raw === '') return NaN
  const m = String(raw).match(/-?\d+(?:\.\d+)?/)
  return m ? parseFloat(m[0]) : NaN
}

function compareValues(a, b) {
  const aEmpty = a == null || a === ''
  const bEmpty = b == null || b === ''
  if (aEmpty && bEmpty) return 0
  if (aEmpty) return 1 // empties always sink to the bottom
  if (bEmpty) return -1
  const na = numericValue(a)
  const nb = numericValue(b)
  if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb
  return String(a).localeCompare(String(b))
}

function columnLabel(col, lang) {
  if (lang === 'ko' && COLUMN_KO[col.key]) return COLUMN_KO[col.key]
  return col.label
}

// Mark positive/negative modifier values for color coding (oils, equipment…).
function valueTone(raw) {
  if (typeof raw !== 'string') return ''
  if (/^\+/.test(raw)) return 'pos'
  if (/^-/.test(raw) || /^−/.test(raw)) return 'neg'
  return ''
}

function ItemCell({ it }) {
  return (
    <a className="item-link" href={it.page} target="_blank" rel="noreferrer">
      {imageUrl(it.icon) && (
        <img
          className="item-icon"
          src={imageUrl(it.icon)}
          alt=""
          loading="lazy"
          width="32"
          height="32"
          onError={(e) => {
            e.currentTarget.style.visibility = 'hidden'
          }}
        />
      )}
      <span>{it.name}</span>
    </a>
  )
}

export default function DataTable({ data, lang }) {
  const columns = data.columns
  const axes = data.axes || []

  const [search, setSearch] = useState('')
  const [view, setView] = useState('compact') // 'compact' | 'grid'
  const [abilityKey, setAbilityKey] = useState('') // selected stat for sort/filter
  const [abilityDir, setAbilityDir] = useState('desc')
  const [onlyWith, setOnlyWith] = useState(false)
  const [gridSortKey, setGridSortKey] = useState('__name')
  const [gridSortDir, setGridSortDir] = useState('asc')
  const [axisKey, setAxisKey] = useState(axes[0]?.key || '')
  const [subMode, setSubMode] = useState('tabs') // 'tabs' | 'sections'
  const [selectedGroup, setSelectedGroup] = useState('')

  const currentAxis = axes.find((a) => a.key === axisKey) || axes[0] || null

  const searched = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return data.items
    return data.items.filter((it) => {
      if (it.name.toLowerCase().includes(q)) return true
      return Object.values(it.fields).some((v) =>
        String(v).toLowerCase().includes(q),
      )
    })
  }, [data.items, search])

  const base = useMemo(() => {
    if (!abilityKey || !onlyWith) return searched
    return searched.filter((it) => {
      const v = it.fields[abilityKey]
      return v != null && v !== ''
    })
  }, [searched, abilityKey, onlyWith])

  // Columns that at least one currently-visible row populates (hides blanks).
  const visibleColumns = useMemo(
    () => columns.filter((col) => base.some((it) => it.fields[col.key])),
    [columns, base],
  )

  const sortedBase = useMemo(() => {
    const items = [...base]
    if (view === 'grid') {
      items.sort((a, b) => {
        const res =
          gridSortKey === '__name'
            ? a.name.localeCompare(b.name)
            : compareValues(a.fields[gridSortKey], b.fields[gridSortKey])
        return gridSortDir === 'asc' ? res : -res
      })
    } else if (abilityKey) {
      items.sort((a, b) => {
        const res = compareValues(a.fields[abilityKey], b.fields[abilityKey])
        return abilityDir === 'asc' ? res : -res
      })
    } else {
      items.sort((a, b) => a.name.localeCompare(b.name))
    }
    return items
  }, [base, view, abilityKey, abilityDir, gridSortKey, gridSortDir])

  const groupOf = (it) => (currentAxis ? it.groups?.[currentAxis.key] : undefined)

  // Whether an item belongs to a group value (supports multi-membership axes).
  const hasGroup = (it, value) => {
    const g = groupOf(it)
    return Array.isArray(g) ? g.includes(value) : g === value
  }

  const tabItems = useMemo(() => {
    if (subMode !== 'tabs' || !selectedGroup) return sortedBase
    return sortedBase.filter((it) => hasGroup(it, selectedGroup))
  }, [sortedBase, subMode, selectedGroup, currentAxis])

  // Groups present in the current (filtered) data, preserving axis order.
  const presentGroups = useMemo(() => {
    if (!currentAxis) return []
    const counts = new Map()
    for (const it of sortedBase) {
      const g = groupOf(it)
      const vals = Array.isArray(g) ? g : g ? [g] : []
      for (const v of vals) counts.set(v, (counts.get(v) || 0) + 1)
    }
    return currentAxis.values
      .filter((v) => counts.has(v.value))
      .map((v) => ({ value: v.value, label: v.label, count: counts.get(v.value) }))
  }, [currentAxis, sortedBase])

  function toggleGridSort(key) {
    if (gridSortKey === key) {
      setGridSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setGridSortKey(key)
      setGridSortDir('asc')
    }
  }

  function gridIndicator(key) {
    if (gridSortKey !== key) return ''
    return gridSortDir === 'asc' ? ' ▲' : ' ▼'
  }

  function changeAxis(key) {
    setAxisKey(key)
    setSelectedGroup('')
  }

  function renderTable(items) {
    if (view === 'compact') {
      return (
        <table className="compact-table">
          <thead>
            <tr>
              <th className="col-item sticky-col">{t(UI.itemColumn, lang)}</th>
              <th>{t(UI.abilities, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.name}>
                <td className="col-item sticky-col">
                  <ItemCell it={it} />
                </td>
                <td>
                  <div className="chips">
                    {columns.map((col) => {
                      const raw = it.fields[col.key]
                      if (!raw || META_KEYS.has(col.key)) return null
                      const tone = valueTone(raw)
                      const sel = col.key === abilityKey ? ' sel' : ''
                      return (
                        <span key={col.key} className={`chip ${tone}${sel}`}>
                          <b>{columnLabel(col, lang)}</b>
                          {raw}
                        </span>
                      )
                    })}
                  </div>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td className="empty" colSpan={2}>
                  {t(UI.noResults, lang)}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )
    }
    return (
      <table>
        <thead>
          <tr>
            <th
              className="col-item sticky-col sortable"
              onClick={() => toggleGridSort('__name')}
            >
              {t(UI.itemColumn, lang)}
              {gridIndicator('__name')}
            </th>
            {visibleColumns.map((col) => (
              <th
                key={col.key}
                className="sortable"
                onClick={() => toggleGridSort(col.key)}
                title={col.label}
              >
                {columnLabel(col, lang)}
                {gridIndicator(col.key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.name}>
              <td className="col-item sticky-col">
                <ItemCell it={it} />
              </td>
              {visibleColumns.map((col) => {
                const raw = it.fields[col.key]
                return (
                  <td key={col.key} className={valueTone(raw)}>
                    {raw ?? ''}
                  </td>
                )
              })}
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td className="empty" colSpan={visibleColumns.length + 1}>
                {t(UI.noResults, lang)}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    )
  }

  const shownCount = subMode === 'tabs' ? tabItems.length : sortedBase.length

  return (
    <div className="table-panel">
      <div className="toolbar">
        <input
          className="search"
          type="search"
          placeholder={t(UI.search, lang)}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <div className="view-switch" role="group">
          <button
            className={view === 'compact' ? 'active' : ''}
            onClick={() => setView('compact')}
          >
            {t(UI.viewCompact, lang)}
          </button>
          <button
            className={view === 'grid' ? 'active' : ''}
            onClick={() => setView('grid')}
          >
            {t(UI.viewGrid, lang)}
          </button>
        </div>

        <div className="ability-control">
          <label>
            {t(UI.sortBy, lang)}:{' '}
            <select
              value={abilityKey}
              onChange={(e) => setAbilityKey(e.target.value)}
            >
              <option value="">{t(UI.none, lang)}</option>
              {columns.map((col) => (
                <option key={col.key} value={col.key}>
                  {columnLabel(col, lang)}
                </option>
              ))}
            </select>
          </label>
          {abilityKey && (
            <>
              <button
                className="dir-btn"
                title={t(abilityDir === 'asc' ? UI.asc : UI.desc, lang)}
                onClick={() =>
                  setAbilityDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                }
              >
                {abilityDir === 'asc' ? '▲' : '▼'}
              </button>
              <label className="only-with">
                <input
                  type="checkbox"
                  checked={onlyWith}
                  onChange={(e) => setOnlyWith(e.target.checked)}
                />
                {t(UI.onlyWith, lang)}
              </label>
            </>
          )}
        </div>

        <span className="count">
          {shownCount} {t(UI.count, lang)}
        </span>
      </div>

      {currentAxis && (
        <div className="subnav">
          {axes.length > 1 && (
            <div className="axis-switch" role="group">
              {axes.map((a) => (
                <button
                  key={a.key}
                  className={a.key === currentAxis.key ? 'active' : ''}
                  onClick={() => changeAxis(a.key)}
                >
                  {axisLabel(a.key, a.label, lang)}
                </button>
              ))}
            </div>
          )}

          <div className="submode-switch" role="group">
            <button
              className={subMode === 'tabs' ? 'active' : ''}
              onClick={() => setSubMode('tabs')}
            >
              {t(UI.subTabs, lang)}
            </button>
            <button
              className={subMode === 'sections' ? 'active' : ''}
              onClick={() => setSubMode('sections')}
            >
              {t(UI.subSections, lang)}
            </button>
          </div>

          {subMode === 'tabs' && (
            <div className="group-pills">
              <button
                className={selectedGroup === '' ? 'pill active' : 'pill'}
                onClick={() => setSelectedGroup('')}
              >
                {t(UI.all, lang)} ({sortedBase.length})
              </button>
              {presentGroups.map((g) => (
                <button
                  key={g.value}
                  className={selectedGroup === g.value ? 'pill active' : 'pill'}
                  onClick={() => setSelectedGroup(g.value)}
                >
                  {groupLabel(g.value, g.label, lang)} ({g.count})
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {subMode === 'sections' && currentAxis ? (
        <div className="sections">
          {presentGroups.map((g) => (
            <section key={g.value} className="group-section">
              <h3 className="group-heading">
                {groupLabel(g.value, g.label, lang)}{' '}
                <span className="g-count">({g.count})</span>
              </h3>
              <div className="table-scroll">
                {renderTable(sortedBase.filter((it) => hasGroup(it, g.value)))}
              </div>
            </section>
          ))}
          {presentGroups.length === 0 && (
            <p className="notice">{t(UI.noResults, lang)}</p>
          )}
        </div>
      ) : (
        <div className="table-scroll">{renderTable(tabItems)}</div>
      )}
    </div>
  )
}
