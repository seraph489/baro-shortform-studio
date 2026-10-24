# 효과 15가지 분류 (@corbinsylk 레퍼런스) — 무엇을 만들 수 있나

출처: [ref_corbinsylk_15effects.md](ref_corbinsylk_15effects.md) (https://www.instagram.com/p/DekGFjDhWgp/). 2026-10-22 정리.
목표: 우리 릴스에 **한 편당 하나** 정도 더할 효과를 고르기.

## 분류
| 분류 | 효과 | 우리 쪽 상태 | 필요한 것 |
|---|---|---|---|
| **A. 이미 있음** | Person pop out | 옵션 `keyword.design: behind` (사람 뒤 글자) | rembg (보관 중) |
| | Dynamic checklist | 01 기준 패널 (①②③ + 체크 아이콘) | — |
| **B. 코드로 바로 만들 수 있음** | **Chat drop** — 채팅 말풍선이 위에서 떨어짐 | ✅ **구현됨** (옵션 `chat`, ep04 v3) | Tabler 아이콘(말풍선) ✅ 받음 |
| | Apple UI key cards — 설정 앱 같은 UI 카드 | 새 요소 | Tabler 아이콘 ✅ |
| | Freebie doc — 자료 표지 카드 (예: "상담 전 체크리스트") | 새 요소 | Tabler 아이콘(file-text) ✅ |
| | Velocity line graph — 선 그래프가 그려짐 | 새 요소 (SVG로 직접 그림) | **병원 확정 수치** 필요 |
| | Iris effect — 원형으로 열리고 닫히는 전환 | 새 요소 (CSS 원형 마스크) | — |
| | Image collage — 사진이 콜라주로 붙음 | 06 인셋 확장 | 모형·장비 **사진** 필요 |
| | Cursor tracker — 화면 녹화 위 커서 강조 | 새 요소 | 화면 녹화 영상 + Tabler pointer ✅ |
| | Pixelated screen close up — 화면 픽셀 질감 확대 | 새 요소 (캔버스) | 화면 녹화 영상 |
| **C. 촬영이 필요** | Over the shoulder zoom | — | 어깨 너머 각도로 따로 촬영 |
| | Match cut | — | 같은 구도로 두 번 촬영 |
| | Zoom through cut | FFmpeg로 가능 | 이어 붙일 두 번째 장면 |
| | Product demo | — | 장비·제품 촬영본 |
| **D. 우리 영상에 안 맞음** | Cinematic grade (어두운 영화 색감) | 쓰지 않음 | 진료실은 밝고 깨끗한 톤 |

## 받아 둔 오픈소스
| 자료 | 위치 | 라이선스 | 용도 |
|---|---|---|---|
| Tabler Icons 3.49.0 (5,184개 outline + 1,054개 filled) | `assets/icons/tabler/` (shortform-studio) | MIT | 말풍선, 체크리스트, 치아(`dental`), 달력, 그래프, 포인터, 문서, 휴대폰 등 UI 카드·패널 아이콘 |
| (이미 있음) rembg · Pretendard · 나눔손글씨 펜 · 효과음 22개 | 기존 위치 | MIT · OFL · CC0/Mixkit | 사람 분리 · 글꼴 · 효과음 |

- 나머지(그래프, 원형 전환, 픽셀 질감, 말풍선 애니메이션)는 HTML/CSS로 직접 만들 수 있어서 따로 받을 게 없어요.
- 받지 않은 것: 영화 색감 LUT(안 씀), Lottie 애니메이션 묶음(라이선스가 제각각이라 필요할 때 개별 확인).

## 추천: 먼저 하나 만든다면 **Chat drop**
- **왜:** 우리 시리즈가 "교정 Q&A"라서, 첫 2초에 **시청자 질문 말풍선**("성인인데 지금 교정해도 될까요?")이 툭 떨어지면 질문형 훅이 바로 살아요. 원장님 답변으로 자연스럽게 이어져요.
- **어디에:** 01·02 둘 다. 제목 자리(0~1.5초) 대신 또는 제목 바로 뒤.
- **규칙:** 실제 환자 채팅·DM 캡처는 금지. **직접 쓴 예시 질문**만 쓰고, 이름·프로필 사진 없이 "시청자 질문"으로 표시.
- 두 번째 후보: **Freebie doc** (마무리에 "상담 전 체크리스트" 자료 카드, 팔로우 카드와 같이)
