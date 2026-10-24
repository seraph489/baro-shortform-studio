---
name: baro-shortform
description: 안양연세바로치과 숏폼(릴스·쇼츠) 편집 스킬. 원장님 촬영본을 분석해 스타일(01 바로 모션 · 02 바로 자막 · 03 바로 데일리)과 옵션(팔로우 카드, 핵심어 디자인 팝·손글씨·사람 뒤, 효과음)을 추천하고, 컷편집·1.1배속·자막·모션그래픽·효과음·−14 LUFS·SRT·Reels 규격 검사까지 해서 MP4를 만든다. 사용자가 촬영본(input/raw의 mp4)을 주며 편집·숏폼·릴스·쇼츠·모션그래픽·자막·효과음을 말하거나, "바로 모션으로", "01로", "손글씨로", "어떤 스타일이 좋을까", "업로드본 만들어줘"처럼 스타일·옵션을 말하면 반드시 이 스킬을 쓴다.
---

# 바로 숏폼 편집

원장님 설명 영상을 병원 고유 스타일로 편집한다. 순서는 **분석 → 추천(스타일 1개 + 옵션) → 계획 승인 → 렌더 → 검수 → 최종 업로드본 결정**이다. 원장님은 1차본을 보고 피드백을 주는 방식을 선호하니, 계획은 짧게 보여 주고 빨리 1차본을 만든다.

## 스타일 3개

| 번호 | 이름 | 한 줄 | 상태 | 문서 |
|---|---|---|---|---|
| **01** | 바로 모션 | 컷+1.1배속, 펀치인, 핵심어, 말 순서대로 켜지는 ①②③ 기준 패널, 마무리 3단 | ✅ 기본값 (원장님 확정) | [references/01_바로모션.md](references/01_바로모션.md) |
| **02** | 바로 자막 | 한두 단어씩 바뀌는 큰 자막(자동), 패널·팝 없이 차분하게 | ⚠️ 원장님 비선호 (2026-10-24) — 추천·비교안으로 내지 않음, 요청할 때만 | [references/02_바로자막.md](references/02_바로자막.md) |
| **03** | 바로 데일리 | 말 없는 진료실 일상 컷 + 가운데 자막 + 음악 | 📝 설계만 | [references/03_바로데일리.md](references/03_바로데일리.md) |

## 옵션 (어느 스타일에나) — [references/options.md](references/options.md)

내용에 맞는 것만 골라 쓰고, **필요한 자료(사진·수치·화면 등)가 있으면 추천할 때 원장님께 먼저 요청**한다 ("이런 사진이 있으면 좋아요"). 레퍼런스 효과 15가지(`fx`·`vfx`)도 options.md에 있다.

| 옵션 | 값 | 기본 |
|---|---|---|
| 팔로우 카드 | 계정명 + "교정 궁금증, 매주 답해 드려요" | **켬** |
| 핵심어 디자인 `keyword.design` | `pop` 팝 / `hand` 손글씨로 써짐 / `behind` 사람 뒤 (삼각대 촬영본만, 마스크 필요) | `pop` |
| 효과음 | 제목 '통' · 핵심어 '붐'(손글씨면 타이핑) · 패널 '선택' | 켬 |
| 자막 테두리 | 배경이 복잡하면 자동 | 자동 |
| 머리 위 자막 | 자막을 머리 위 작은 한 줄로 | 끔 |
| 시청자 질문 말풍선 `chat` | 첫 몇 초 질문 말풍선이 위에서 떨어짐 (직접 쓴 예시 질문만) | 끔 |

모든 스타일에 공통인 규칙(원장님 결정, 금지사항, Reels 규격, 도구 위치)은 [references/common-rules.md](references/common-rules.md), 글자 자리는 [references/placement-guide.md](references/placement-guide.md)를 따른다. 특히 **환자 정보 금지, 원본 보존, 자막은 발화 그대로(애매하면 생략)** 세 가지는 항상 지킨다.

## 1. 분석

shortform-studio 폴더에서 실행한다. 작업 폴더는 `work/<영상이름>/`.

```bash
PY=../tools/.venv-rembg/bin/python
P=.claude/skills/baro-shortform/scripts/pipeline.py
$PY -I $P analyze "input/raw/<파일>.mp4" work/<작업>
```

길이·해상도·fps·채널·무음·받아쓰기·신뢰도 낮은 단어·다시 말한 문장(NG 후보)이 나온다. 이어서 프레임 4~6장을 뽑아(`ffmpeg -ss t -frames:v 1`) 얼굴 위치, 머리 위 여백, 흔들림, **환자·이름표·모니터 노출**, 시작 전 대기·끝의 팔 뻗기를 확인한다. 노출이 있으면 멈추고 원장님께 알린다.

## 2. 추천

[references/recommend.md](references/recommend.md)대로 **스타일 1개 + 옵션**을 이유와 함께 짧게 보여 준다. 비교가 필요하면 2개까지 1차본을 만든다.

## 3. 컷과 계획

```bash
$PY -I $P cut work/<작업>        # 옵션: --keep 17.3,18.9 (작게 말한 단어 살리기) --drop 3.2-7.9 (NG 테이크 빼기)
```

- NG 후보가 있으면 마지막 테이크만 남긴다 (`--drop`, 원본 시각). 확정 전 들어 보거나 원장님께 확인.
- "원본 대비 단어 차이"에 빠진 단어가 있으면 그 단어의 원본 시각을 `--keep`으로 준다 (전체 pad를 늘리면 템포가 느려진다).
- 영상 끝 무음 속 "감사합니다" 같은 단어는 대부분 받아쓰기 환각이다.
- 촬영 종료 동작(팔 뻗기)은 plan.json `end`(출력 시각)로 자른다. 끝음은 남긴다.

그다음 "컷 받아쓰기(출력 시각)"와 "음성 구간"을 보고 `work/<작업>/plan.json`을 쓴다 ([references/plan-schema.md](references/plan-schema.md)).
- 제목은 앞 무음(1~1.5초) 동안, 첫 대사에서 끊는다.
- 핵심어는 통념을 깨는 한 단어를 결론 펀치인 시각에 1회.
- 01의 패널 항목은 원장님이 그 단어를 **말하는 순간**에 켜고, 문장이 끝나면 내린다.
- 자막은 1~2줄, 의미가 바뀔 때만. 애매한 말·말 고침은 넣지 않는다.

장면표를 표로 보여 주고 승인받는다. "알아서"라고 하면 바로 렌더한다.

## 4. 렌더와 검수

```bash
$PY -I $P frames work/<작업>
$PY -I $P masks work/<작업>       # 핵심어 behind일 때만 (CPU 프레임당 약 40초, 백그라운드로)
$PY -I $P render work/<작업> <시리즈폴더>/<이름>_v1
```

`render`가 그래픽 → 합성 → 효과음 → 인코딩 → 규격 검사를 하고 `output/<이름>_hq.mp4`, `_phone.mp4`, `.srt`, 작업 폴더에 `report.json`·`sheet.png`를 만든다. 렌더 로그의 **"글자 요소 겹침"이 "없음"인지** 확인하고(남으면 시각·문구를 고쳐 다시 렌더), **장면 시트를 직접 본다**: 자막이 얼굴·입을 가리는지, 빨간 선 아래로 글자가 내려가는지, 핵심어가 이마에 닿는지. FAIL이 있으면 고치고 다시 렌더한다. 개별 단계는 `overlay` / `compose` / `sfx` / `encode`.

비교본을 만들 때는 작업 폴더를 따로 두고 `analysis.json`·`edl.json`·`audio_cut.wav`·`frames_src`·`words_cut.json`·`envelope.json`을 링크로 공유한다.

## 편집 화면 (원장님이 직접 고칠 때)

```bash
$PY -I .claude/skills/baro-shortform/scripts/editor_server.py work/<작업> 8765   # 백그라운드로
```

`http://127.0.0.1:8765`: 미리보기(컷 영상 + 실제 그래픽)를 보며 자막·핵심어(디자인 포함)·패널·마무리·줌·효과음·팔로우 카드·끝 지점을 고치고, 타임라인 막대를 끌어 시간을 바꾼다. **저장**은 plan.json(이전 버전은 `plan_history/`), **렌더**는 새 버전을 `output/`에 만든다.

## 5. 보고와 최종 업로드본

보고는 짧게: 결과 파일(고화질·폰용·SRT), 길이, 음량, 규격 검사 결과 / 원장님이 확인할 것(자막에서 뺀 말, 의료 표현, 화면 속 개인정보) / 확인하지 못한 것. 원장님이 최종본을 고르면:
1. **최종 표시 파일명:** 그 버전의 세 파일(`_hq.mp4`·`_phone.mp4`·`.srt`) 이름 앞에 `FINAL_`을 붙인다 (`mv -n`, 예: `output/ep05/FINAL_ep05_extraction_01_v1_hq.mp4`). 시리즈 폴더에서 이름순 맨 위에 오고, `FINAL_`은 폴더마다 한 세트만 둔다. 확정본을 바꾸면 이전 `FINAL_`을 떼고 새 버전에 붙인다. 다른 후보 파일은 이름 그대로 둔다(원장님이 직접 붙인 표시도 건드리지 않는다).
2. `work/<작업>/DECISION.md`에 확정 버전·파일 경로·길이·음량·구성·비교 후보를 기록한다.

게시는 원장님이 직접 한다.

## 폴더 구조
- `scripts/pipeline.py` · `render_overlay.mjs` · `editor_server.py` · `editor.html` · `templates/baro_overlay.html`(공통 그래픽 템플릿 하나)
- `references/` 지금 쓰는 문서 · `references/sources/` 레퍼런스 분석 기록(YSA, 효과 17·15, 다른 PD 비교) · `references/archive/` 정리하며 뺀 옛 스타일 문서
- `scripts/templates/archive/` 옛 스타일별 템플릿 (03 glass·cover 디자인 포함)
- 옛 plan.json의 `"style": "06"`은 02로, `"07"`·`"03"`은 01로 자동으로 읽는다

## 참고 결과물
- 01 + 사진 카드 확정본: `output/ep06/FINAL_ep06_clear-aligner_photo_v1_hq.mp4` (ep06, 장치 사진 비교)
- 01 확정본: `output/ep05/FINAL_ep05_extraction_01_v1_hq.mp4` (ep05, 말풍선·손글씨·패널), `output/ep04/FINAL_ep04_adult-age_01_v4_hq.mp4` (ep04, 말풍선·팔로우 카드), `output/ep03/FINAL_ep03_kids-timing_01_v3_hq.mp4` (ep03), `output/test-02/test02_age_v4c_sfx_hq.mp4` (test-02)
- 01 + 손글씨: `output/ep03/ep03_kids-timing_07_v2_hq.mp4` · 02: `output/ep04/ep04_adult-age_06_v3_hq.mp4`
- 효과 이름 통합 목록: [references/effects-catalog.md](references/effects-catalog.md)
- 효과 아이디어: [references/sources/effects-15_분류.md](references/sources/effects-15_분류.md) (만들 수 있는 것 분류 + 받아 둔 오픈소스), [effects-17.md](references/sources/effects-17.md)
- 아이콘: `assets/icons/tabler/` (Tabler Icons, MIT)
