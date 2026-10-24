# 옵션 (어느 스타일에나 켜고 끄기)

스타일(01·02·03)은 영상 형식을 정하고, 옵션은 그 위에 얹는 장식이에요. 모두 plan.json으로 정하고, 편집 화면에서도 바꿀 수 있어요.

## 1. 팔로우 카드 — 기본 켬
| 항목 | 값 |
|---|---|
| 모습 | 흰 알약 카드: 프로필 원 + **안양연세바로치과** / *교정 궁금증, 매주 답해 드려요* + [팔로우] |
| 시각 | 기본 끝 2.5초 전 (마무리 3단이 있으면 그 뒤 0.9초) |
| 바꾸기 | `"follow": {"text": "계정명", "sub": "소개 한 줄", "start": 초}` · 끄기 `"follow": false` |
| 결정 | 2026-10-22 원장님: 팔로우 카드 좋음, 소개 한 줄 추가 |
| 겹침 방지 | 카드가 보이는 동안 그 자리를 차지한 자막·마무리·패널은 **자동으로 위로 올리고(최대 80px), 그래도 겹치면 글자를 줄여요** (2026-10-22, ep04에서 자막과 겹친 문제 수정) |

## 2. 핵심어 디자인 — `keyword.design`
통념을 깨는 한 단어("나이?", "6~7세")를 어떻게 보여 줄지. 영상당 1회.

| design | 모습 | 쓸 때 | 조건 |
|---|---|---|---|
| `pop` (기본) | 머리 위 큰 흰 글자 팝 + 펀치인 + '붐' 효과음 | 대부분 | — |
| `hand` | 손글씨로 한 글자씩 써짐 (나눔손글씨 펜) + 타이핑 효과음 | 아이 교정·상담 권유처럼 따뜻한 주제 | 2026-10-22 원장님: 나쁘지 않음 |
| `behind` | 머리카락 뒤로 아래쪽이 숨는 큰 글자 | 입체감이 필요할 때 | **삼각대 촬영 + 머리 위 여백 350px 이상**. `pipeline.py masks`로 사람 마스크(rembg, CPU 프레임당 약 40초) 먼저. 마스크 시험(머리카락 깜빡임 평균 3/255 이하) 통과해야 함 |

- 위치는 `keyword.top`(기본 230, 위 띠 밖), 크기 `keyword.size`(기본 310, 가로 800px 넘으면 자동 축소)
- `behind`는 글자 아래 끝이 머리카락에 50~100px 걸치고 이마보다 위에 오게 `top`을 정해요
- 손글씨 문구를 핵심어 말고도 더 쓰려면 `hand[]`에 직접 추가 (`{text, start, end, x, y, size, color, rotate, per}`, 영상당 2~3개까지). 색: 갈색 선반 앞 `white`, 흰 벽 앞 `navy`

## 3. 효과음 — 기본 켬
| 시점 | 소리 | 음량 |
|---|---|---|
| 제목 | 07_제목등장_통 | −11dB |
| 핵심어 | `pop`: 16_충격_붐 −10dB · `hand`: 18_타이핑 −16dB | |
| 기준 패널 항목마다 | 10_패널단계_선택 | −6dB |
- 목소리 피크보다 크면 자동으로 줄여요. 영상당 3~5개. 추가는 `sfx[]`, 기본 끄기 `"sfx_default": false`
- 소리 목록: `assets/sfx/ready/` (22개, Kenney CC0 + Mixkit)

## 4. 시청자 질문 말풍선 (Chat drop) — 선택
| 항목 | 값 |
|---|---|
| 모습 | 흰 말풍선이 위에서 떨어져 살짝 튕기며 멈춤. 왼쪽 위 "시청자 질문"(사람 아이콘), 오른쪽 위 "교정 Q&A"(말풍선 아이콘, Tabler Icons MIT) |
| 자리 | 머리 위 y 250 (위 띠 밖). 핵심어(`pop`)와 겹치지 않게 핵심어 전에 끝냄 |
| 소리 | 닿는 순간 `01_사진등장_뽁` −12dB. 제목과 같이 나오면 제목 '통'은 생략 |
| 쓰기 | `"chat": {"text": "성인인데 지금 교정, // **너무 늦은** 걸까요?", "start": 0.15, "end": 5.2}` (`**강조**` 코랄, `//` 줄바꿈, `top`·`who`·`tag` 바꿀 수 있음) |
| 규칙 | **실제 환자 채팅·DM 캡처 금지.** 직접 쓴 예시 질문만, 이름·프로필 사진 없이 |
| 언제 | 원장님이 시청자 질문을 그대로 읽으며 시작하는 영상 ("~이런 질문 많이 받아요") |

## 5. 자막 테두리 — 자동
`"outline": "auto"`(기본)면 자막 자리 배경이 복잡할 때(복잡도 4.0 이상)만 검정 테두리. `true`/`false`로 고정.

## 6. 머리 위 자막 — 선택
`"subs_layout": "top"` (+ `"subs_color": "navy"`): 자막을 머리 위 작은 한 줄로. 머리 위 손글씨·핵심어와 같이 쓰면 겹쳐서 둘 중 하나만.

## 7. 끝 지점 · SRT
- `"end": 초` — 촬영 종료 동작(팔 뻗기) 자르기
- `"srt_skip": [...]` — SRT·자동 자막에서 뺄 단어 (애매한 말, 말 고침)

## 8. 사진 카드 (`photos[]`) — 선택 (2026-10-24, ep06)
| 항목 | 값 |
|---|---|
| 모습 | 흰 카드에 사진 + 이름표. 옆에서 날아와 살짝 기울어 붙음. 2장이면 왼쪽·오른쪽 나란히 비교 |
| 쓰기 | `"photos": [{"src": "photos/bracket.jpg", "label": "브라켓 교정", "side": "left", "start", "end"}, ...]` (`side`: left/right/center, `tag` 작은 코랄 글, `dim` 이후 흐려짐, `top` 기본 1100) · 위 제목 `"photos_title": {"text": "**장단점이 다른 케이스**", "start", "end"}` |
| 소리 | `sfx[]`에 `01_사진등장_뽁` −12dB를 카드마다 |
| 규칙 | 사진은 작업 폴더 `photos/`에 메타데이터 지워 복사. **얼굴·이름이 보이는 사진 금지.** 원장님이 준 구내 사진은 **게시 전 환자 동의 확인**. 웹 사진은 라이선스·출처 기록 |
| 자막 | 카드가 자막 자리(y 1100~1490)를 차지하니 그 구간은 자막 대신 제목 한 줄 |

## 9. 레퍼런스 효과 15가지 (`fx[]` 그래픽 · `vfx[]` 영상) — 선택 (2026-10-24 설치)
이름은 [effects-catalog.md](effects-catalog.md)의 레퍼런스 표기. **한 영상에 새 효과는 1~2개**, 내용에 맞을 때만. 자료가 필요하면 추천할 때 먼저 요청 ([recommend.md](recommend.md) 2-1).
시험 영상: `output/fx_test/fx_test_all15_v1_hq.mp4` (ep06 영상에 15개를 차례로).

### 그래픽 효과 `fx[]` — 각 항목 `{type, start, end, ...}`
| type | 효과 (레퍼런스 이름) | 언제 | 필요한 자료 | 주요 값 |
|---|---|---|---|---|
| `ui_card` | UI world / Apple UI key cards | 단계·확인 항목을 앱 화면처럼 | — | `title`, `rows:[{icon, label, value}]`(icon: check·tooth·calendar·clock·chat·file·star·info), `step`, `top` |
| `phone` | Phone mockup | 예약·상담 방법 안내 | 직접 만든 화면 캡처(선택) | `src` 또는 `lines:[...]`(말풍선), `side` left/right |
| `freebie` | Freebie doc | 마무리에 나눠 줄 자료 | **실제 자료 제목** | `badge`, `title`, `sub` |
| `orbit` | Orbit | 도입 훅, 사례 나열 | 장치·모형 사진 2~4장 | `srcs`, `period`, `center`, `rx`, `ry` |
| `headline_wall` | Headline wall | "흔한 오해들" 나열 | — (가짜 기사 금지, 질문·통념 문장만) | `items`(최대 6), `step` |
| `chart` | Chart grow / Velocity graph | 기간·비율 비교 | **병원 확정 수치 + 출처** | `title`, `data:[{label, value}]`, `unit`, `source` |
| `iris` | Iris effect | 시작·끝 전환 | — | `mode` open/close, `dur`, `center` |
| `paper_cut` | Paper cut | 가벼운 주제, 아이 교정 | — | `stickers:[{text, x, y, rotate}]`, `step` |
| `cursor` | Cursor tracker | 화면 녹화·폰 목업 위 클릭 안내 | 화면 녹화(선택) | `path:[[초, x, y]...]`, `clicks:[초]` |
| `couch_wall` | Couch wall | 진료실 벽에 사진 액자 | 사진 + 삼각대 촬영 | `frames:[{src, x, y, w, h, rotate}]` |

### 영상 효과 `vfx[]`
| type | 효과 | 언제 | 조건 | 주요 값 |
|---|---|---|---|---|
| `pull_back` | Pull-back reveal | 마무리 "전체 보기" | — | `to`(작아질 크기, 0.68), `y` |
| `green_screen` | Green screen | 짧은 구간 배경 바꾸기 | **사람 마스크** | `bg`: 색(`#DDEBE7`) 또는 사진 경로 |
| `frame_break` | Frame break | 반전·결론 직전 | **사람 마스크**, 삼각대 | `scale`, `cut`(액자 윗변 위치) |
| `doodle` | Doodle boil | 아이·청소년, 부드러운 분위기 | **사람 마스크** | `color`, `width`, `boil` |
| `pixelate` | Pixelated close up | 화면 녹화의 한 부분 확대 | 화면 녹화가 있을 때 의미 있음 | `box:[x,y,w,h]`, `block` |

- 사람 마스크: `pipeline.py masks work/<작업> --step 3` (3프레임마다 만들고 가까운 것을 씀, CPU 프레임당 약 40초 → 1.4초 구간 하나에 약 10분). 백그라운드로.
- 촬영이 필요한 5개(Zoom-through cut, Match cut, Over the shoulder, Product demo, Vertigo)는 코드로 대신하지 않음 — 촬영본이 생기면 추가.
