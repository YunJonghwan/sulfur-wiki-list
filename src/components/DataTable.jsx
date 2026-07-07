import { useMemo, useState } from 'react'
import { UI, COLUMN_KO, t } from '../i18n.js'

const FILE_PATH = 'https://sulfur.wiki.gg/wiki/Special:FilePath/'

function imageUrl(fileName) {
  if (!fileName) return null
  return FILE_PATH + encodeURIComponent(fileName) + '?width=64'
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

export default function DataTable({ data, lang }) {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState('__name')
  const [sortDir, setSortDir] = useState('asc')

  const columns = data.columns

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return data.items
    return data.items.filter((it) => {
      if (it.name.toLowerCase().includes(q)) return true
      return Object.values(it.fields).some((v) =>
        String(v).toLowerCase().includes(q),
      )
    })
  }, [data.items, search])

  const sorted = useMemo(() => {
    const items = [...filtered]
    items.sort((a, b) => {
      let res
      if (sortKey === '__name') {
        res = a.name.localeCompare(b.name)
      } else {
        res = compareValues(a.fields[sortKey], b.fields[sortKey])
      }
      return sortDir === 'asc' ? res : -res
    })
    return items
  }, [filtered, sortKey, sortDir])

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  function sortIndicator(key) {
    if (sortKey !== key) return ''
    return sortDir === 'asc' ? ' ▲' : ' ▼'
  }

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
        <span className="count">
          {sorted.length} {t(UI.count, lang)}
        </span>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th
                className="col-item sticky-col sortable"
                onClick={() => toggleSort('__name')}
                aria-sort={sortKey === '__name' ? sortDir : 'none'}
              >
                {t(UI.itemColumn, lang)}
                {sortIndicator('__name')}
              </th>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="sortable"
                  onClick={() => toggleSort(col.key)}
                  aria-sort={sortKey === col.key ? sortDir : 'none'}
                  title={col.label}
                >
                  {columnLabel(col, lang)}
                  {sortIndicator(col.key)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((it) => (
              <tr key={it.name}>
                <td className="col-item sticky-col">
                  <a
                    className="item-link"
                    href={it.page}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {imageUrl(it.image) && (
                      <img
                        className="item-icon"
                        src={imageUrl(it.image)}
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
                </td>
                {columns.map((col) => {
                  const raw = it.fields[col.key]
                  return (
                    <td key={col.key} className={valueTone(raw)}>
                      {raw ?? ''}
                    </td>
                  )
                })}
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td className="empty" colSpan={columns.length + 1}>
                  {t(UI.noResults, lang)}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
