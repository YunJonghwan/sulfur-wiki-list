// Hand-translated Korean text for the Locations tab's freeform prose
// (description / POIs / tips) — unlike short item stat labels, this is full
// sentences scraped straight from the wiki, so it needs real translation
// rather than a lookup table of single words. Keyed by the location's
// display name (see LOCATION_DISPLAY_NAME / build_locations in scrape.py).
// Paragraph breaks in `description` are marked with \n, matching how the
// English source splits into <p> tags. `pois`/`tips` arrays line up 1:1
// with the English arrays in location.json by index.

export const LOCATION_KO = {
  'The Church': {
    description:
      '교회는 신도 모두가 어떤 식으로든 죄인이라는 것을 상기시키는 뜻에서 \'오리지널 신(The Original Sin)\'이라 불린다. 오리지널 신은 과거가 어떻든 누구에게나 열려 있으며, 그래서 신도 대부분이 \'순수함과는 거리가 먼\' 이들이다. 살롱 문은 \'문은 언제나 열려 있다\'는 것을 상징하지만, 바로 이 개방적인 방침이 결국 그들을 파멸로 이끌었다.',
  },
  Caves: {
    description:
      '동굴은 SULFUR의 시작 지역으로, 교회 왼쪽에 있는 동굴 입구를 통해 들어갈 수 있다.\n동굴은 총 7개의 스테이지로 구성되어 있다. 4번째 스테이지에는 항상 아뮬렛을 충전할 수 있는 체크포인트가 있으며, 7번째 스테이지에는 지역 보스 Cousin이 등장한다. Cousin을 처치하면 마을이 해금된다.\n이 지역은 천장이 높은 넓은 방, 좁은 다리, 절벽 지형이 특징이다. 절벽 아래로 떨어지면 큰 피해를 입으며, 체력이 낮을 경우 즉사할 수도 있다.',
    pois: [
      '동굴 4번째 스테이지에는 아뮬렛을 충전할 수 있는 체크포인트가 있다.',
      '5번째 스테이지에는 미니보스전이 있으며, \'마트료시카 몬스트로시티\' 속성이 붙은 Goblin Barrel Boy를 처치해야 한다. 처치 보상으로 스크롤이나 오일을 얻을 수 있다.',
      '7번째 스테이지에는 지역 보스 Cousin이 등장한다. 처치 후에는 나무로 된 화물 엘리베이터를 타고 교회로 돌아간다.',
    ],
    tips: [
      '동굴은 빠르게 돌파할 수 있고 적들이 가깝게 모여 있는 경우가 많아, 무기 랭크를 올리기에 좋은 지역이다.',
      '전리품 상자가 물속이나 접근하기 어려운 곳에 등장할 수 있으므로, 구석구석 탐색하면 보상을 받을 확률이 높다.',
    ],
  },
  Town: {
    description:
      '마을은 SULFUR의 두 번째 지역으로, 동굴에서 Cousin을 처치한 후 교회 왼쪽에 있는 마을 입구를 통해 들어갈 수 있다.',
    tips: ['마을은 밀가루, 설탕, 계란 등 음식 재료를 구하기 좋은 지역이다.'],
  },
  Sewers: {
    description:
      '하수도는 SULFUR의 세 번째 지역으로, 마을에서 Black Guild Cardinal들을 처치한 후 마을 입구 오른쪽에 있는 입구를 통해 들어갈 수 있다.\n하수도는 구불구불한 통로와 물에 잠긴 구간이 얽혀 있는 지역으로, 적이 매우 자주 등장한다. 많은 구역이 수영으로만 통과할 수 있어, 수영 속도나 수중 시야를 높여주는 장비가 큰 도움이 된다.',
    tips: [
      'Diving Fin, Diving Mask 같은 장비를 착용하면 물에 잠긴 구역을 훨씬 수월하게 이동할 수 있다.',
      'Oxygen Tank, Extra Lung 같은 패시브 아이템을 사용하면 장시간 수중 수영이 훨씬 안전해지며, 익사 피해 없이 물에 잠긴 구역을 통과할 수 있다.',
      'Corrupted Lurk가 자주 걸어오는 중독 상태이상은 물속에 들어가면 해제할 수 있다.',
    ],
  },
  'Hedge Maze': {
    description:
      '산울타리 미로는 SULFUR의 네 번째 지역이다. 하수도를 한 번 클리어하면 미로 입구가 열린다.\n산울타리 미로를 지나면 지하감옥 입구로 이어지며, 한 번 들어간 뒤에는 성으로 가는 지름길도 열린다. 미로 출구에는 죽은 나무가 있는데, 그 아래에서 Craw Guano를 0~3개 획득할 수 있다.',
    pois: ['미로 곳곳에 다양한 상자가 흩어져 있으며, 오일이나 다른 귀중한 전리품이 자주 들어있다.'],
  },
  Dungeon: {
    description:
      '지하감옥은 다섯 번째 지역으로, 산울타리 미로를 클리어해야만 들어갈 수 있다.\n교회에서 지하감옥으로 직접 가는 길은 없으며, 산울타리 미로를 거쳐야 가장 빠르게 도달할 수 있다.',
  },
  Castle: {
    description:
      '성은 여섯 번째 지역으로, 지하감옥을 클리어해야만 들어갈 수 있다.\n교회에서 성으로 직접 가는 길은 없으며, 산울타리 미로를 거치는 것이 교회에서 가장 빠르게 도달하는 경로다.\n성에 한 번 들어간 뒤에는 지름길이 열리는데, 이 지름길은 교회가 아니라 산울타리 미로 끝에서 이어진다.',
  },
  Forest: {
    pois: [
      '묘지\n여러 마리의 Wraith가 출몰한다. 묘지 안 영묘에서 무기 상자를 찾을 수 있지만, 안으로 들어가면 앞쪽 무덤들에서 Wraith가 추가로 일어난다.\n\n집\n숲 속의 한 집으로, 화덕과 Pølse를 찾을 수 있다. 집 뒤편에는 지하실이 있으며, 그 안에서 다량의 Pølse와 인간 장기, 솥, 그리고 장비 상자를 발견할 수 있다.',
    ],
  },
  "Shav'Wani Bridge": {
    description:
      '샤브와니 다리는 숲과 요새를 잇는 연결 구역이다. 숲을 한 번 클리어하면 열리며, 교회에서 요새로 가는 경로가 된다.\n이 지역은 숲 지형으로 시작해서, 요새로 곧장 이어지는 큰 다리로 끝난다.',
    pois: ['숲과 요새를 잇는 커다란 다리.'],
  },
  Desert: {
    description: '사막은 4막(Chapter IV)에서 가장 먼저 공개된 지역이다.',
    tips: [
      '이 지역은 짙은 안개 같은 흙먼지가 있어, 배율이 있는 조준경(예: Assault Scope, Sniper Scope)을 사용하지 않으면 장거리 교전이 사실상 불가능하다. 배율 조준경을 사용하면 먼지 너머까지 시야가 확보되어 이 문제를 완화할 수 있다.',
    ],
  },
  'Trial of the Spirit': {
    description:
      'Trial of the Spirit는 사막 지역의 선택적 하위 스테이지로, 사막의 거의 모든 레벨에 등장한다(?). 다만 1레벨에서는 입구가 항상(?) 무너져 있고, 5레벨에서는 사막 보스와 싸우기 때문에 등장하지 않는다.\n입장하려면 Crypt Key가 필요하다. 도전 중 일부는 난이도가 매우 높으며, 실패하면 사망한다는 점에 유의해야 한다.',
  },
  'Beyond the Veil': {
    description: '베일 너머는 게임의 마지막 지역으로, 짧은 운전 구간을 지나면 다시 동굴로 이어진다.',
    tips: [
      '베일 너머에서는 아뮬렛으로 교회에 순간이동해서 나갈 수 없다. 따라서 사막에서 진입하기 전에 불필요한 짐을 정리하고 전리품을 미리 맡겨두는 것이 좋다. 진행 상황은 Desert Claus를 처치한 시점부터 저장된다.',
      '이 지역에는 Rödsopp가 20개 있으며, The Witch를 파밍할 경우 Health Potion이나 Rödsopp Paste를 만드는 데 모을 수 있다.',
      '대부분의 주요 보스전 전과 마찬가지로, 이 지역에도 Priest\'s Chest가 있다.',
    ],
  },
}
