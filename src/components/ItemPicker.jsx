import { useEffect, useMemo, useState } from 'react'
import { UI, COLUMN_KO, t, groupLabel, axisLabel } from '../i18n.js'

const BASE = import.meta.env.BASE_URL
const META_KEYS = new Set(['GridSize', 'SellVal', 'BuyVal', 'SoldBy'])

function imageUrl(icon) {
  return icon ? BASE + icon : null
}

function fieldsOf(item) {
  return item?.fields || {}
}

function matchesSearch(item, q) {
  if (!q) return true
  if (item.name.toLowerCase().includes(q)) return true
  return Object.values(fieldsOf(item)).some((v) => String(v).toLowerCase().includes(q))
}

function hasGroup(item, axisKey, value) {
  const g = item.groups?.[axisKey]
  return Array.isArray(g) ? g.includes(value) : g === value
}

function valueTone(raw) {
  if (typeof raw !== 'string') return ''
  if (/^\+/.test(raw)) return 'pos'
  if (/^-/.test(raw) || /^−/.test(raw)) return 'neg'
  return ''
}

// Icon-grid item picker used by the build simulator slots. Replaces native
// <select> so items can be browsed by icon + key stats instead of by
// memorizing names, with a search box and optional axis/group-pill filters
// (e.g. weapon class/ammo, oil ability) mirroring the main data tables.
export default function ItemPicker({ lang, value, sections, isDisabled, onSelect, onClear, labelFor }) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [sectionKey, setSectionKey] = useState(sections[0]?.key)
  const [axisKey, setAxisKey] = useState(sections[0]?.axes?.[0]?.key || '')
  const [groupValue, setGroupValue] = useState('')

  function switchSection(key) {
    setSectionKey(key)
    const sect = sections.find((s) => s.key === key)
    setAxisKey(sect?.axes?.[0]?.key || '')
    setGroupValue('')
  }

  useEffect(() => {
    if (!open) return
    setSearch('')
    switchSection(sections[0]?.key)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  useEffect(() => {
    if (!open) return
    function onKey(e) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  const activeSection = sections.find((s) => s.key === sectionKey) || sections[0]
  const axes = activeSection?.axes || []
  const axis = axes.find((a) => a.key === axisKey) || axes[0] || null

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    let items = activeSection ? activeSection.items : []
    if (q) items = items.filter((it) => matchesSearch(it, q))
    if (axis && groupValue) items = items.filter((it) => hasGroup(it, axis.key, groupValue))
    return items
  }, [activeSection, search, axis, groupValue])

  function labelText(key) {
    if (lang === 'ko' && COLUMN_KO[key]) return COLUMN_KO[key]
    return labelFor ? labelFor(key) : key
  }

  function pick(item) {
    onSelect(item, activeSection.key)
    setOpen(false)
  }

  return (
    <div className="picker">
      <button type="button" className="picker-trigger" onClick={() => setOpen(true)}>
        {value ? (
          <>
            {imageUrl(value.icon) && (
              <img className="item-icon" src={imageUrl(value.icon)} alt="" width="24" height="24" />
            )}
            <span className="picker-trigger-name">{value.name}</span>
          </>
        ) : (
          <span className="picker-placeholder">{t(UI.empty, lang)}</span>
        )}
      </button>

      {open && (
        <div
          className="picker-overlay"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setOpen(false)
          }}
        >
          <div className="picker-panel">
            <div className="picker-head">
              <input
                autoFocus
                className="picker-search"
                type="search"
                placeholder={t(UI.search, lang)}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              {value && (
                <button
                  type="button"
                  className="pill"
                  onClick={() => {
                    onClear?.()
                    setOpen(false)
                  }}
                >
                  {t(UI.empty, lang)}
                </button>
              )}
              <button type="button" className="picker-close" onClick={() => setOpen(false)}>
                ✕
              </button>
            </div>

            {sections.length > 1 && (
              <div className="axis-switch picker-tabs">
                {sections.map((s) => (
                  <button
                    key={s.key}
                    className={s.key === sectionKey ? 'active' : ''}
                    onClick={() => switchSection(s.key)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            )}

            {axes.length > 1 && (
              <div className="axis-switch picker-tabs">
                {axes.map((a) => (
                  <button
                    key={a.key}
                    className={a.key === axis?.key ? 'active' : ''}
                    onClick={() => {
                      setAxisKey(a.key)
                      setGroupValue('')
                    }}
                  >
                    {axisLabel(a.key, a.label, lang)}
                  </button>
                ))}
              </div>
            )}

            {axis && (
              <div className="group-pills picker-groups">
                <button
                  className={groupValue === '' ? 'pill active' : 'pill'}
                  onClick={() => setGroupValue('')}
                >
                  {t(UI.all, lang)}
                </button>
                {axis.values.map((v) => (
                  <button
                    key={v.value}
                    className={groupValue === v.value ? 'pill active' : 'pill'}
                    onClick={() => setGroupValue(v.value)}
                  >
                    {groupLabel(v.value, v.label, lang)}
                  </button>
                ))}
              </div>
            )}

            <div className="picker-grid">
              {filtered.map((it) => {
                const disabled = isDisabled?.(it, activeSection.key) && it.name !== value?.name
                return (
                  <button
                    type="button"
                    key={it.name}
                    className={`picker-tile${disabled ? ' disabled' : ''}${value?.name === it.name ? ' selected' : ''}`}
                    disabled={disabled}
                    onClick={() => pick(it)}
                  >
                    <div className="picker-tile-head">
                      {imageUrl(it.icon) && (
                        <img className="item-icon" src={imageUrl(it.icon)} alt="" width="32" height="32" />
                      )}
                      <span className="picker-tile-name">{it.name}</span>
                    </div>
                    <div className="chips">
                      {Object.entries(fieldsOf(it)).map(([k, v]) => {
                        if (!v || META_KEYS.has(k)) return null
                        return (
                          <span key={k} className={`chip ${valueTone(v)}`}>
                            <b>{labelText(k)}</b>
                            {v}
                          </span>
                        )
                      })}
                    </div>
                  </button>
                )
              })}
              {filtered.length === 0 && <p className="notice">{t(UI.noResults, lang)}</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
