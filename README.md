# SULFUR Data List

[SULFUR](https://store.steampowered.com/app/2124120/SULFUR/) 게임의 무기 · 오일 · 부착물 · 장비 · 소비품 데이터를
**한 화면에서 표로** 보고 **정렬 · 검색**할 수 있는 사이트입니다.

데이터는 [SULFUR Wiki (sulfur.wiki.gg)](https://sulfur.wiki.gg)에서 가져오며,
오일처럼 개별 페이지에 흩어져 있던 버프/디버프도 **한 표 안에서 색으로 구분해** 보여줍니다.
(초록 = 상승/버프, 빨강 = 하락/디버프)

## 구조

```
sulfur-wiki-list/
├─ scripts/scrape.py     # 위키 → JSON 수집기 (Python 표준 라이브러리만 사용)
├─ public/data/*.json    # 수집된 카테고리별 데이터 (weapon, oil, attachment, ...)
├─ src/                  # React + Vite 프론트엔드
│  ├─ App.jsx            # 카테고리 탭 · 언어 · 데이터 로딩
│  ├─ components/DataTable.jsx  # 정렬 · 검색 · 색상 표시 테이블
│  └─ i18n.js            # UI 문자열 · 컬럼 한글 라벨 (직접 수정 가능)
└─ .github/workflows/deploy.yml # GitHub Pages 자동 배포
```

## 개발

```powershell
npm install
npm run dev      # http://localhost:5173
```

## 데이터 갱신

위키가 업데이트되면 수동으로 다시 수집합니다.

```powershell
npm run scrape   # = python scripts/scrape.py
```

`public/data/*.json` 이 갱신되며, 커밋/푸시하면 배포에 반영됩니다.

## 배포 (GitHub Pages)

`main` 브랜치에 푸시하면 GitHub Actions가 빌드 후 Pages에 배포합니다.
저장소 **Settings → Pages → Source** 를 **GitHub Actions** 로 설정하세요.

프로젝트 사이트 경로(`/sulfur-wiki-list/`)는 [vite.config.js](vite.config.js)의 `base` 에 설정되어 있습니다.
저장소 이름이 다르면 이 값을 맞춰 주세요.

## 한글 표기

게임 내 실제 한글 번역과 팬 위키 번역이 다를 수 있어, **데이터 값(숫자·효과)은 영어 원문을 그대로** 유지합니다.
UI와 컬럼 헤더의 한글은 [src/i18n.js](src/i18n.js)에서 직접 추가/수정할 수 있습니다.

## 라이선스

- 코드: 이 저장소 소유자 라이선스
- 게임 데이터: [SULFUR Wiki](https://sulfur.wiki.gg) — CC BY-SA 4.0
