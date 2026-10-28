# plan.json 형식 (01 바로 모션 템플릿 기준)

`work/<작업>/plan.json`. **모든 시각은 컷·1.1배속 이후 출력 시각(초)** 이다. `pipeline.py cut`이 출력하는 "컷 받아쓰기(출력 시각)"와 "음성 구간"을 보고 정한다. 받아쓰기 시각은 일찍 잡히는 경우가 있어 문장 시작은 음성 구간 시작에 맞춘다.

```json
{
 "style": "01",   // 01 바로 모션 · 02 바로 자막 · 03 바로 데일리(설계만)
 "series": "안양연세바로치과 교정 Q&A",
 "title":   {"badge": "안양연세바로치과 교정 Q&A", "lines": ["나이가 많으면", "**교정** 늦었을까?"], "start": 0, "end": 2.6},
 "subs": [
  {"start": 2.65, "end": 4.24, "text": "교정이 **어려울까?**", "motion": "shake"},
  {"start": 6.76, "end": 8.15, "text": "**나이**_만으로_ // 정해지지 않아요", "size": "impact"},
  {"start": 11.7, "end": 13.7, "text": "이 기준에 따라", "motion": "converge"}
 ],
 "keyword": {"text": "나이", "mark": "?", "start": 5.67, "end": 6.7},
 "panel": {"title": "교정 계획에서 함께 보는 기준", "start": 8.22, "end": 11.69,
   "items": [{"label": "잇몸 상태", "at": 8.22, "icon": "gum"},
             {"label": "치아 위치", "at": 9.67, "icon": "pos"},
             {"label": "삐뚤어진 정도", "at": 10.32, "icon": "tilt"}]},
 "cta": {"label": "시작 전", "keyword": "정밀 진단", "tail": "먼저 받아보세요", "start": 17.4},
 "anchor": [540, 800],
 "zoom": [{"start": 0, "end": 0.1, "from": 2.0, "scale": 1.0, "ramp": 0.1},
          {"start": 2.65, "end": 5.67, "from": 1.15, "scale": 1.15, "ramp": 0},
          {"start": 5.67, "end": 8.22, "scale": 1.25, "ramp": 0.12}],
 "sfx": [],
 "sfx_default": true
}
```

| 필드 | 뜻 |
|---|---|
| `title` | 앞 무음 구간의 배지 + 사선 제목. `lines`의 `**단어**`는 코랄 강조. 첫 대사가 시작되면 끝낸다 (`end`) |
| `subs[].text` | `**강조**` 코랄 굵게 · `_작게_` 작은 글씨 · `//` 줄바꿈. 1~2줄, 한 줄 15자 안팎 |
| `subs[].size` | `body`(56px, 기본) / `impact`(104px, 결론·주의 환기) |
| `subs[].motion` | 없음(즉시 교체) / `pop`(0→125→96→100%) / `shake`(약한 흔들림 정착, 질문) / `bounce`(글자별 바운스) / `converge`(자간 수렴). `bounce`·`converge`는 강조 표기를 쓰지 않는다. 추가: `flicker` `focus` `soft` `rise` `highlight` `colorKeys` `weight` ([options.md](options.md) 10번) |
| `keyword` | 얼굴 앞 큰 핵심어 팝 (머리 위쪽, 310px). 영상당 1회, 약 1초. 보통 결론 펀치인과 같은 시각 |
| `panel` | 화면 40% 어둡게 + 하단 기준 패널 (y 1150~1530). `items[].at`에 그 항목이 켜지고, 지금 말하는 항목만 틸 배경 + 팝. `end`는 그 문장이 끝날 때. `icon`: `gum`(잇몸) `pos`(치아 위치) `tilt`(기울어진 치아) `check`(체크) `none` |
| `cta` | 마무리 3단: 작은 라벨 → 0.30초 뒤 큰 키워드 팝 → 0.85초 뒤 타자기 꼬리 문구. 영상 끝까지 |
| `end` | 영상 끝 지점(출력 시각). 촬영 종료 동작 등을 잘라 낸다. 비우면 컷 결과 끝까지 |
| `keyword.design` | `pop`(기본) / `hand`(손글씨로 써짐) / `behind`(사람 뒤, `masks` 단계 필요). 옛 `keyword.layer: "behind"`도 behind로 읽음 |
| `keyword.top`, `keyword.size` | 핵심어 윗선 y(px)와 글자 크기(px). 기본 230 / 310 (위 띠 12% 밖). 가로 832px를 넘으면 자동으로 줄어요 |
| `chat` | 시청자 질문 말풍선 `{text, start, end, top?, who?, tag?}` — options.md 4번 |
| `headline` | (안 씀, 원장님: 별로) 위쪽 후킹 헤드라인 `{"lines": [...], "start", "end"}`. `**코랄**` `__민트__` `~~회색 취소선~~` |
| `word_captions` | (02) `true` 또는 `{"highlight": [...], "skip": [...], "from", "to"}` — 컷 받아쓰기로 한두 단어 자막 자동 생성 |
| `insets[]` | (02) 사진 인셋 `{"src": "작업폴더 기준 경로", "start", "end"}` — 환자 사진 금지 |
| `follow` | 팔로우 카드 — **기본 켬** (`false`로 끔) `{"text": "계정 이름", "sub": "소개 한 줄", "start"}`. 기본 소개: "교정 궁금증, 매주 답해 드려요" |
| `srt_skip` | SRT·한두 단어 자막에서 뺄 단어 (애매한 말·말 고침) |
| `word_fix` | 받아쓰기 오인식 고치기 `{"암호와": "안모와"}` — SRT·자동 자막에 적용 |
| `hand[]` | 손글씨 문구 추가 `{text, start, end, x, y, size, color, rotate, per}` — options.md 참고 |
| `subs_layout`, `subs_color` | (옵션) `"top"` → 자막을 머리 위 작은 한 줄로, `"navy"` → 남색 글자 |
| `outline` | 글자 테두리. `"auto"`(기본: 자막 자리 배경이 복잡할 때만) / `true` / `false` |
| `anchor` | 줌 기준점(얼굴 중심, 출력 좌표). 장면 시트로 확인해서 정한다 |
| `zoom[]` | 인물 레이어만 확대. `from`→`scale`, `ramp`초 동안 (0이면 즉시 = 크롭 컷). 결론 펀치인 1.16~1.25, 크롭 컷 1.15 |
| `sfx_default` | `true`면 기본 배치 자동: 제목 '통'(−11dB), 핵심어 '붐'(−10dB), 패널 항목마다 '선택'(−6dB) |
| `sfx[]` | 추가 효과음 `{"t": 초, "file": "assets/sfx/ready의 파일명", "gain_db": -10, "why": "…"}`. 35ms 앞당김은 자동 |

## 자리 규칙 (템플릿에 들어 있음)
- 자막 y≈1190, 제목 y≈1110, 패널 y 1150~1500, CTA y 1090~1420: 모두 입 아래, 안전구역 아래 끝(y 1500) 위
- 핵심어는 머리 위쪽(y 230~540, 위 띠 12% 밖). 얼굴이 화면 위쪽에 붙은 촬영본이면 장면 시트로 확인하고 템플릿의 `#kw` top을 조정한다
