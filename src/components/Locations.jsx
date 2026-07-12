import { useMemo, useState } from 'react'
import { UI, t, nameKo } from '../i18n.js'

const BASE = import.meta.env.BASE_URL

function imageUrl(icon) {
  if (!icon) return null
  return BASE + icon
}

const ACT_LABEL = {
  I: { en: 'Act I', ko: '1막' },
  II: { en: 'Act II', ko: '2막' },
  III: { en: 'Act III', ko: '3막' },
  IV: { en: 'Act IV', ko: '4막' },
}

const HEADINGS = {
  enemies: { en: 'Enemies', ko: '등장 적' },
  vendors: { en: 'Vendors', ko: '벤더' },
  loot: { en: 'Notable Loot', ko: '주요 루팅' },
  subareas: { en: 'Sub-areas', ko: '하위 지역' },
  pois: { en: 'Points of Interest', ko: '주요 지점' },
  tips: { en: 'Tips', ko: '팁' },
}

const STAGES_LABEL = { en: 'Stages', ko: '스테이지 수' }
const CHECKPOINT_LABEL = { en: 'Amulet checkpoint', ko: '아뮬렛 충전' }
const BOSS_STAGE_LABEL = { en: 'Boss stage', ko: '보스 스테이지' }
const STAGE_OF = { en: 'stage {n}', ko: '{n}번째' }

function stageOf(n, lang) {
  return t(STAGE_OF, lang).replace('{n}', n)
}

function LinkChip({ item, lang, withIcon }) {
  return (
    <a className="loc-chip" href={item.page} target="_blank" rel="noreferrer">
      {item.boss && <span className="boss-badge loc-chip-badge">{lang === 'ko' ? '보스' : 'BOSS'}</span>}
      {item.areaBoss && !item.boss && (
        <span className="area-boss-badge loc-chip-badge">{lang === 'ko' ? '지역 보스' : 'AREA BOSS'}</span>
      )}
      {withIcon && imageUrl(item.icon) && (
        <img className="item-icon recipe-icon" src={imageUrl(item.icon)} alt="" width="20" height="20" />
      )}
      <span>
        {item.name}
        {withIcon && nameKo(item.name, lang) && (
          <span className="item-name-ko"> ({nameKo(item.name, lang)})</span>
        )}
      </span>
    </a>
  )
}

function LocationCard({ loc, lang }) {
  const desc = loc.description?.trim()
  return (
    <section className="loc-card">
      <h3 className="loc-card-title">
        {loc.hub && <span className="loc-step-badge loc-hub-badge">{lang === 'ko' ? '허브' : 'HUB'}</span>}
        {loc.step != null && <span className="loc-step-badge">{loc.step}</span>}
        {loc.special && <span className="boss-badge loc-special-badge">{lang === 'ko' ? '도전' : 'CHALLENGE'}</span>}
        <a href={loc.page} target="_blank" rel="noreferrer">
          {loc.name}
        </a>
      </h3>
      {desc && (
        <div className="loc-desc">
          {desc.split('\n').filter(Boolean).map((para, i) => (
            <p key={i}>{para}</p>
          ))}
        </div>
      )}

      {loc.stages && (
        <div className="loc-stage-info">
          <span className="loc-chip">
            {t(STAGES_LABEL, lang)}: {loc.stages.stages}
          </span>
          <span className="loc-chip">
            {t(CHECKPOINT_LABEL, lang)}: {stageOf(loc.stages.checkpointStage, lang)}
          </span>
          <span className="loc-chip">
            {t(BOSS_STAGE_LABEL, lang)}: {stageOf(loc.stages.bossStage, lang)}
          </span>
        </div>
      )}

      {loc.enemies.length > 0 && (
        <div className="loc-section">
          <div className="loc-section-label">{t(HEADINGS.enemies, lang)}</div>
          <div className="loc-chips">
            {loc.enemies.map((e) => (
              <LinkChip key={e.name} item={e} lang={lang} withIcon />
            ))}
          </div>
        </div>
      )}

      {loc.loot.length > 0 && (
        <div className="loc-section">
          <div className="loc-section-label">{t(HEADINGS.loot, lang)}</div>
          <div className="loc-chips">
            {loc.loot.map((l) => (
              <LinkChip key={l.name} item={l} lang={lang} withIcon />
            ))}
          </div>
        </div>
      )}

      {loc.vendors.length > 0 && (
        <div className="loc-section">
          <div className="loc-section-label">{t(HEADINGS.vendors, lang)}</div>
          <div className="loc-chips">
            {loc.vendors.map((v) => (
              <LinkChip key={v.name} item={v} lang={lang} />
            ))}
          </div>
        </div>
      )}

      {loc.subareas.length > 0 && (
        <div className="loc-section">
          <div className="loc-section-label">{t(HEADINGS.subareas, lang)}</div>
          <div className="loc-chips">
            {loc.subareas.map((s) => (
              <LinkChip key={s.name} item={s} lang={lang} />
            ))}
          </div>
        </div>
      )}

      {loc.pois.length > 0 && (
        <div className="loc-section">
          <div className="loc-section-label">{t(HEADINGS.pois, lang)}</div>
          <ul className="loc-notes">
            {loc.pois.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </div>
      )}

      {loc.tips.length > 0 && (
        <div className="loc-section">
          <div className="loc-section-label">{t(HEADINGS.tips, lang)}</div>
          <ul className="loc-notes">
            {loc.tips.map((tip, i) => (
              <li key={i}>{tip}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

export default function Locations({ data, lang }) {
  const acts = useMemo(() => {
    const seen = []
    for (const loc of data.locations) {
      if (loc.act && !seen.includes(loc.act)) seen.push(loc.act)
    }
    return seen
  }, [data.locations])

  const [actFilter, setActFilter] = useState('')

  const shown = actFilter ? data.locations.filter((l) => l.act === actFilter) : data.locations

  return (
    <div className="loc-panel">
      <div className="group-pills">
        <button className={actFilter === '' ? 'pill active' : 'pill'} onClick={() => setActFilter('')}>
          {t(UI.all, lang)} ({data.locations.length})
        </button>
        {acts.map((act) => (
          <button
            key={act}
            className={actFilter === act ? 'pill active' : 'pill'}
            onClick={() => setActFilter(act)}
          >
            {t(ACT_LABEL[act] || { en: act, ko: act }, lang)} (
            {data.locations.filter((l) => l.act === act).length})
          </button>
        ))}
      </div>

      <div className="loc-list">
        {shown.map((loc) => (
          <LocationCard key={loc.name} loc={loc} lang={lang} />
        ))}
      </div>
    </div>
  )
}
