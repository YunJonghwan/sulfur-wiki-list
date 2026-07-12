import { t } from '../i18n.js'

const BASE = import.meta.env.BASE_URL

// Hand-curated from https://sulfur.wiki.gg/wiki/Enemies#Elite_Enemies — this is
// static reference content (aura/modifier descriptions), not per-item scraped
// data, so it lives here instead of in the JSON pipeline.
const ELITE_ENEMIES = [
  {
    key: 'monstrosity',
    icon: 'icons/enemy/elite/Mutation_Monstrosity.png',
    name: { en: 'Monstrosity', ko: '몬스트로시티' },
    aura: {
      en: 'Brown aura with orange "mountain" icons, larger-than-normal size.',
      ko: '갈색 오라, 주황색 산 모양 아이콘. 일반보다 큰 크기.',
    },
    ability: {
      en: 'Triple health (+200%), double damage (+100%), and increased size.',
      ko: '체력 3배(+200%), 데미지 2배(+100%), 크기 증가.',
    },
  },
  {
    key: 'matryoshka',
    icon: 'icons/enemy/elite/Mutation_Matryoshka.png',
    name: { en: 'Matryoshka Monstrosity', ko: '마트료시카 몬스트로시티' },
    aura: {
      en: 'Brown aura with a red icon depicting a monster containing three heads within; significantly larger than normal.',
      ko: '갈색 오라, 몬스터 머리 3개가 들어있는 붉은 아이콘. 일반보다 훨씬 큰 크기.',
    },
    ability: {
      en: 'Up to quintuple health (+400%), double damage (+100%), and splits into three normal-sized versions of itself upon death.',
      ko: '체력 최대 5배(+400%), 데미지 2배(+100%), 사망 시 일반 크기 3마리로 분열.',
    },
  },
  {
    key: 'shapeshifter',
    icon: 'icons/enemy/elite/Mutation_Shapeshifter.png',
    name: { en: 'Shapeshifter', ko: '셰이프시프터' },
    aura: {
      en: 'Black aura with a white "mask" icon.',
      ko: '검은색 오라, 흰색 가면 아이콘.',
    },
    ability: {
      en: 'Double health (+100%) compared to its normal counterpart, and transforms into a random enemy with full health upon death.',
      ko: '체력 2배(+100%), 사망 시 체력이 가득 찬 무작위 적으로 변신.',
    },
  },
  {
    key: 'miniature',
    icon: 'icons/enemy/elite/Mutation_Miniature.png',
    name: { en: 'Miniature', ko: '미니어처' },
    aura: {
      en: 'Purple aura with "ladybug" icons; much smaller than normal.',
      ko: '보라색 오라, 무당벌레 아이콘. 일반보다 훨씬 작은 크기.',
    },
    ability: {
      en: 'Despite its small size, does not have decreased health.',
      ko: '크기는 작지만 체력 감소는 없음.',
    },
  },
  {
    key: 'bomb',
    icon: 'icons/enemy/elite/Mutation_Bomb.png',
    name: { en: 'Bomb', ko: '봄' },
    aura: {
      en: 'Red aura with a "bomb" icon that emits a faint ticking sound.',
      ko: '빨간색 오라, 희미한 똑딱 소리가 나는 폭탄 아이콘.',
    },
    ability: {
      en: 'Explodes on death.',
      ko: '사망 시 폭발.',
    },
  },
  {
    key: 'blink',
    icon: 'icons/enemy/elite/Mutation_Blink.png',
    name: { en: 'Blink', ko: '블링크' },
    aura: {
      en: 'White aura with a "static ball" icon.',
      ko: '흰색 오라, 정전기 구체 아이콘.',
    },
    ability: {
      en: 'Teleports a short distance when damaged, zapping the player with electricity if they are near the origin or destination point.',
      ko: '피격 시 짧은 거리를 순간이동하며, 이동 시작/도착 지점 근처에 있으면 플레이어를 감전시킴.',
    },
  },
  {
    key: 'elemental-frost',
    icon: 'icons/enemy/elite/Mutation_Frost.png',
    name: { en: 'Elemental — Frost', ko: '엘리멘탈 — 냉기' },
    aura: { en: 'Pale blue aura with a white frost icon.', ko: '옅은 하늘색 오라, 흰색 냉기 아이콘.' },
    ability: {
      en: 'Inflicts Frost on hit, and double health (+100%).',
      ko: '적중 시 냉기 부여, 체력 2배(+100%).',
    },
  },
  {
    key: 'elemental-poison',
    icon: 'icons/enemy/elite/Mutation_Poison.png',
    name: { en: 'Elemental — Poison', ko: '엘리멘탈 — 독' },
    aura: { en: 'Green aura with a green poison icon.', ko: '녹색 오라, 녹색 독 아이콘.' },
    ability: {
      en: 'Inflicts Poison on hit, and double health (+100%).',
      ko: '적중 시 독 부여, 체력 2배(+100%).',
    },
  },
  {
    key: 'elemental-fire',
    icon: 'icons/enemy/elite/Mutation_Fire.png',
    name: { en: 'Elemental — Fire', ko: '엘리멘탈 — 화염' },
    aura: { en: 'Pale yellow aura with an orange fire icon.', ko: '옅은 노란색 오라, 주황색 화염 아이콘.' },
    ability: {
      en: 'Inflicts Fire on hit, and double health (+100%).',
      ko: '적중 시 화염 부여, 체력 2배(+100%).',
    },
  },
  {
    key: 'elemental-surge',
    icon: 'icons/enemy/elite/Mutation_Surge.png',
    name: { en: 'Elemental — Surge', ko: '엘리멘탈 — 서지(전기)' },
    aura: { en: 'White aura with a pale yellow surge icon.', ko: '흰색 오라, 옅은 노란색 서지 아이콘.' },
    ability: {
      en: 'Inflicts Surge on hit, and double health (+100%).',
      ko: '적중 시 서지(전기) 부여, 체력 2배(+100%).',
    },
  },
]

const HEADING = { en: 'Elite Enemies', ko: '엘리트 적' }
const INTRO = {
  en: 'Normal enemies empowered with an aura-marked modifier. Some demand an entirely different strategy than the base enemy.',
  ko: '오라로 표시되는 강화 효과가 붙은 일반 적입니다. 일부는 기본 적과 완전히 다른 공략이 필요합니다.',
}
const AURA_LABEL = { en: 'Aura', ko: '오라' }
const ABILITY_LABEL = { en: 'Effect', ko: '효과' }

export default function EliteEnemies({ lang }) {
  return (
    <details className="elite-enemies">
      <summary>{t(HEADING, lang)}</summary>
      <p className="elite-intro">{t(INTRO, lang)}</p>
      <div className="elite-table-scroll">
        <table className="elite-table">
          <thead>
            <tr>
              <th>{lang === 'ko' ? '이름' : 'Name'}</th>
              <th>{t(AURA_LABEL, lang)}</th>
              <th>{t(ABILITY_LABEL, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {ELITE_ENEMIES.map((e) => (
              <tr key={e.key}>
                <td className="elite-name-cell">
                  <img className="item-icon" src={BASE + e.icon} alt="" width="28" height="28" />
                  <span>{t(e.name, lang)}</span>
                </td>
                <td>{t(e.aura, lang)}</td>
                <td>{t(e.ability, lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}
