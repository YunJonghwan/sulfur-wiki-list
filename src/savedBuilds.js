// Local-only build save/load — persisted as a named list in localStorage.
// Only item NAMES are stored (not full item objects), so saves stay tiny
// and always resolve against whatever the current scraped data says, rather
// than freezing a stale copy of stats/icons from whenever it was saved.

const STORAGE_KEY = 'sulfur-builds'

export function loadSavedBuilds() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const list = raw ? JSON.parse(raw) : []
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

function writeSavedBuilds(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  } catch {
    // Storage full/unavailable (private browsing etc.) — silently no-op,
    // nothing here is critical enough to interrupt the user over.
  }
}

// React state -> a plain, JSON-safe record of names.
export function serializeBuild(name, state) {
  const { weapon, level, enchants, attachments, chisel, head, chest, feet, passives } = state
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name,
    savedAt: new Date().toISOString(),
    weapon: weapon?.name ?? null,
    level,
    enchants: enchants.map((e) => (e ? { type: e.type, name: e.item.name } : null)),
    attachments: Object.fromEntries(
      Object.entries(attachments).map(([k, v]) => [k, v?.name ?? null]),
    ),
    chisel: chisel?.name ?? null,
    head: head?.name ?? null,
    chest: chest?.name ?? null,
    feet: feet.map((f) => f?.name ?? null),
    passives: passives.map((p) => p?.name ?? null),
  }
}

export function saveBuild(name, state) {
  const list = loadSavedBuilds()
  list.push(serializeBuild(name, state))
  writeSavedBuilds(list)
  return list
}

export function deleteBuild(id) {
  const list = loadSavedBuilds().filter((b) => b.id !== id)
  writeSavedBuilds(list)
  return list
}

// Saved record (names) -> live item objects, looked up in the currently
// loaded datasets. Anything renamed/removed since the save just resolves to
// null instead of failing the whole load.
export function resolveBuild(record, data) {
  const byName = (kind, name) => (name ? data[kind]?.items.find((it) => it.name === name) ?? null : null)
  return {
    weapon: byName('weapon', record.weapon),
    level: record.level ?? 5,
    enchants: (record.enchants || []).map((e) =>
      e ? { type: e.type, item: byName(e.type === 'scroll' ? 'scroll' : 'oil', e.name) } : null,
    ),
    attachments: Object.fromEntries(
      Object.entries(record.attachments || {}).map(([k, name]) => [k, byName('attachment', name)]),
    ),
    chisel: byName('chisel', record.chisel),
    head: byName('equipment', record.head),
    chest: byName('equipment', record.chest),
    feet: (record.feet || [null, null]).map((name) => byName('equipment', name)),
    passives: (record.passives || []).map((name) => byName('passive', name)),
  }
}
