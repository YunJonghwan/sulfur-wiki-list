import { useEffect, useState } from 'react'
import { CATEGORIES, UI, t } from './i18n.js'
import DataTable from './components/DataTable.jsx'

const BASE = import.meta.env.BASE_URL

function useLang() {
  const [lang, setLang] = useState(() => localStorage.getItem('lang') || 'ko')
  useEffect(() => {
    localStorage.setItem('lang', lang)
    document.documentElement.lang = lang
  }, [lang])
  return [lang, setLang]
}

export default function App() {
  const [lang, setLang] = useLang()
  const [active, setActive] = useState(CATEGORIES[0].kind)
  const [cache, setCache] = useState({})
  const [status, setStatus] = useState('idle')

  useEffect(() => {
    if (cache[active]) return
    let cancelled = false
    setStatus('loading')
    fetch(`${BASE}data/${active}.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((json) => {
        if (cancelled) return
        setCache((c) => ({ ...c, [active]: json }))
        setStatus('ready')
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [active, cache])

  const data = cache[active]

  return (
    <div className="app">
      <header className="app-header">
        <h1>💀 {t(UI.title, lang)}</h1>
        <div className="lang-switch" role="group" aria-label="language">
          <button
            className={lang === 'ko' ? 'active' : ''}
            onClick={() => setLang('ko')}
          >
            {t(UI.langKo, lang)}
          </button>
          <button
            className={lang === 'en' ? 'active' : ''}
            onClick={() => setLang('en')}
          >
            {t(UI.langEn, lang)}
          </button>
        </div>
      </header>

      <nav className="tabs">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.kind}
            className={cat.kind === active ? 'tab active' : 'tab'}
            onClick={() => setActive(cat.kind)}
          >
            {t(cat, lang)}
          </button>
        ))}
      </nav>

      <main>
        {status === 'loading' && !data && (
          <p className="notice">{t(UI.loading, lang)}</p>
        )}
        {status === 'error' && !data && (
          <p className="notice error">{t(UI.error, lang)}</p>
        )}
        {data && <DataTable key={data.kind} data={data} lang={lang} />}
      </main>

      {data && (
        <footer className="app-footer">
          <span>
            {t(UI.source, lang)}{' '}
            <a href="https://sulfur.wiki.gg" target="_blank" rel="noreferrer">
              sulfur.wiki.gg
            </a>{' '}
            · CC BY-SA 4.0
          </span>
          <span>
            {t(UI.updated, lang)}: {new Date(data.generated).toLocaleDateString()}
          </span>
        </footer>
      )}
    </div>
  )
}
