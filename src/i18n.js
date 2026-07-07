// UI strings and manual Korean overrides.
//
// Item DATA values (numbers, effect text) always come straight from the wiki in
// English, because fan translations sometimes differ from the actual in-game
// Korean text. Only the interface chrome and column headers are localized here.
// Add/adjust Korean terms freely — anything missing falls back to English.

export const CATEGORIES = [
  { kind: 'weapon', en: 'Weapons', ko: '무기' },
  { kind: 'oil', en: 'Oils', ko: '오일' },
  { kind: 'attachment', en: 'Attachments', ko: '부착물' },
  { kind: 'equipment', en: 'Equipment', ko: '장비' },
  { kind: 'consumable', en: 'Consumables', ko: '소비품' },
]

export const UI = {
  title: { en: 'SULFUR Data List', ko: 'SULFUR 데이터 목록' },
  search: { en: 'Search…', ko: '검색…' },
  itemColumn: { en: 'Item', ko: '아이템' },
  count: { en: 'items', ko: '개' },
  loading: { en: 'Loading…', ko: '불러오는 중…' },
  error: { en: 'Failed to load data.', ko: '데이터를 불러오지 못했습니다.' },
  noResults: { en: 'No matching items.', ko: '일치하는 항목이 없습니다.' },
  updated: { en: 'Updated', ko: '갱신' },
  source: { en: 'Data from', ko: '데이터 출처' },
  langEn: { en: 'EN', ko: 'EN' },
  langKo: { en: '한글', ko: '한글' },
}

// Korean labels for column keys. Missing keys fall back to the English label
// provided by the scraper.
export const COLUMN_KO = {
  GridSize: '크기',
  SubType: '종류',
  Ammo: '탄약',
  Mode: '발사 모드',
  Mag: '탄창',
  Weight: '무게',
  Damage: '데미지',
  RPM: '연사 속도',
  Spread: '탄퍼짐',
  Recoil: '반동',
  Durability: '내구도',
  CritChance: '치명타 확률',
  CritADS: '조준 시 치명타',
  RldSpeed: '재장전 속도',
  BltSpeed: '탄속',
  BltDrop: '탄 낙차',
  BltPen: '관통',
  BltSize: '탄 크기',
  BltBounces: '탄 튕김 횟수',
  BltBounciness: '탄 탄성',
  Drag: '드래그 배율',
  AimDisabled: '조준 불가',
  ProjecAmnt: '투사체 수',
  AmmoConsume: '탄약 소모 확률',
  AmmoExConsume: '추가 탄약 소모 확률',
  MaxDrb: '최대 내구도',
  Speed: '이동 속도',
  JumpPwr: '점프력',
  LootChance: '전리품 확률',
  MoveAccuracy: '이동 중 명중률',
  Armor: '방어구',
  Sprint: '질주 보너스',
  SwimSpeed: '수영 속도',
  WpnWeight: '무기 무게',
  ExtraJumps: '추가 점프',
  Coyote: '코요테 타임',
  Charisma: '카리스마',
  Luck: '행운',
  CharmRst: '매혹 저항',
  ExplRst: '폭발 저항',
  FireRst: '화염 저항',
  FrostRst: '냉기 저항',
  PsnRst: '독 저항',
  ElecRst: '전기 저항',
  LightRst: '빛 저항',
  Heal: '회복',
  RmvFire: '화염 제거',
  RmvFrost: '냉기 제거',
  RmvPsn: '독 제거',
  RmvVD: '부두 제거',
  Theme: '테마',
  Recipes: '포함 레시피',
  SellVal: '판매 가격',
  BuyVal: '구매 가격',
  SoldBy: '판매처',
}

export function t(entry, lang) {
  if (!entry) return ''
  return entry[lang] || entry.en || ''
}
