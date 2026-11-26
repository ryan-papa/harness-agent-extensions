---
name: rp-deck
description: 작업 산출물·문서·주제를 토스 스타일 HTML 슬라이드 장표로 변환. 의존성 없는 단일 HTML(슬라이드형)로 생성하고, 환경별로 지정한 GitHub 레포(owner/name 또는 사내 호스트 전체 URL)에 4레벨로 자동 분류 적재 후 index.html을 갱신한다. `.rp-deck.json`에 홈 링크(`home`)가 있으면 각 장표 우하단에 게시판 홈 버튼을 넣는다. 주제 조사(topic) 시 조사 원본·정리 노트를 옵시디언 vault(설정 시)에도 남긴다. 삭제도 이 스킬로 한다 — URL·경로·제목으로 지정하면 확인 후 파일 삭제 + index 갱신 + 푸시. "장표 만들어줘", "덱으로 정리해줘", "deck", "슬라이드로 만들어줘", "이 장표 지워줘", "덱 삭제해줘", 작업/회고/PRD/문서를 보기 좋게 정리하거나 올린 장표를 내려 달라고 할 때 사용.
---

# rp-deck — 토스 스타일 장표 생성

문서는 잘 안 읽힌다. 핵심을 한 장에 한 메시지로, 토스 느낌의 깔끔한 HTML 슬라이드로 바꿔 3초 안에 이해되게 만든다.

## 레퍼런스 (반드시 먼저 Read)

| 파일 | 역할 |
|------|------|
| [`reference/template.html`](reference/template.html) | 디자인·컴포넌트·네비게이션 SSOT. CSS·클래스를 그대로 재사용하고 내용만 채운다 |
| [`reference/design-rules.md`](reference/design-rules.md) | 독자 기준·구조·전달력·토스 톤·용어 각주·자가 린트 규칙 |
| [`reference/visual-patterns.md`](reference/visual-patterns.md) | **주제 → 시각 표현 매핑 SSOT.** 스키마·데이터흐름·값 변화·기술 비교·계층 구조를 무엇으로 그릴지 |
| [`reference/review.md`](reference/review.md) | 독립 서브에이전트 리뷰 프로토콜 (2라운드, 건당 10분 타임아웃, 작성자 셀프리뷰 금지) + **리뷰어 프롬프트 템플릿** |
| [`reference/operations.md`](reference/operations.md) | **운영·부가 모드 SSOT.** 타깃 레포(`.rp-deck.json`·캐시 동기화)·홈 버튼·옵시디언 적재(거절 영구 저장)·보강/신규 판정·삭제 모드 상세. **워크플로우 1단계 진입 전 및 삭제 모드 진입 즉시 필수 Read** |
| [`scripts/update_index.py`](scripts/update_index.py) | 덱 트리 스캔 → 게시판 index.html 생성: 좌측 디렉토리 트리(전체+뎁스 중첩) + 우측 리스트, 트리·검색 필터는 임베드 JSON 기반 클라이언트 렌더 (stdlib only) |
| [`scripts/delete_deck.py`](scripts/delete_deck.py) | 덱 삭제: URL·경로·제목으로 대상 해석 → dry-run 목록 → `--yes` 시 파일 삭제 + 빈 디렉터리 정리 + index 재생성 (stdlib only) |
| [`scripts/lint_svg.py`](scripts/lint_svg.py) | 인라인 SVG 좌표 린트: 텍스트 겹침(OVERLAP)·viewBox 이탈(CLIP)·왼쪽 여백 이탈(INDENT). 지적 있으면 종료 코드 1 (stdlib only) |

## 입력 모드 (인자로 자동 판단)

| 인자 | 모드 | 동작 |
|------|------|------|
| 없음 | **컨텍스트** | 방금 끝낸 작업/대화를 요약해 장표화 |
| 파일 경로 (`.md` 등 존재하는 경로) | **파일** | 그 문서를 읽어 장표화 |
| 그 외 텍스트 | **주제** | `deep-research` 스킬로 조사 후 장표화 |
| 삭제 지시 (URL·경로·제목 + "지워줘") | **삭제** | [`reference/operations.md`](reference/operations.md) §삭제 모드를 즉시 Read해 덱 삭제 + index 재생성 |

## 운영 규칙 (필수 Read)

일반 워크플로우 1단계(타깃 레포 확인) 진입 전 및 삭제 모드 진입 즉시 [`reference/operations.md`](reference/operations.md)를 Read한다 — 타깃 레포(`.rp-deck.json`·캐시 동기화)·홈 버튼·옵시디언 적재(거절 `false` 영구 저장)·보강/신규 판정·삭제 모드(dry-run 확인 1회 필수)의 상세 SSOT다.

## 워크플로우

1. **타깃 레포 확인·최신화** — [`reference/operations.md`](reference/operations.md)를 먼저 Read하고 `.rp-deck.json`을 읽는다.
   - 있으면 캐시를 **원격 최신으로 강제 동기화**(`git fetch origin && git reset --hard origin/<기본브랜치>`, 캐시 없으면 `git clone`) → **레포 모드**. ⛔ 이 동기화 전에는 기존 문서 확인·생성을 시작하지 않는다.
   - 없으면 대상 레포를 한 번 물어본다. 알려주면 저장 후 레포 모드, 원치 않으면 **로컬 모드**(푸시 없음)로 진행. ([`operations.md`](reference/operations.md) §타깃 레포)
2. **레퍼런스 로드** — `template.html` + `design-rules.md` + `visual-patterns.md`를 Read한다. (매 실행마다)
3. **입력 수집** — 모드 판별 후 원문 확보. 주제 모드는 `deep-research` 실행 결과를 원문으로 삼고, **조사 원본을 옵시디언에 남기므로 vault 타깃도 확인**한다([`operations.md`](reference/operations.md) §옵시디언; `obsidian`이 `false`면 **묻지 않고 스킵**, 키가 없을 때만 한 번 물어보고 거절 시 `false` 저장).
4. **기존 문서 확인 (보강/신규)** — 대상 루트(레포 캐시 또는 `<cwd>/docs/decks`)의 `index.html`·기존 덱 메타(title·category·summary)를 스캔해 같은 주제 문서가 있는지 본다. ([`operations.md`](reference/operations.md) §보강 vs 신규)
   - 같은 주제가 **명확**하면 → 그 파일을 **보강** 대상으로.
   - 새 주제가 **명확**하면 → **신규**.
   - **애매하면** 사용자에게 보강/신규를 물어본다. (명확하면 자동, 결정은 다음 단계 진행 중 한 줄로 알림)
5. **구조 설계 (자동)** — "이 독자에게 어떻게 하면 가장 잘 전달될까"를 먼저 설계한다.
   - **독자 기준**: 개발자만이 아니라 **기획자·비전공 대학 4학년이 읽어도 이해되게** 설계한다. 사전지식 0을 가정하고, "왜 필요한지"를 "어떻게 동작하는지"보다 앞에 둔다. ([`design-rules.md`](reference/design-rules.md) §0)
   - 결론 먼저(Minto), 도입은 SCQA, 목차·섹션은 주제 라벨이 아닌 **주장**으로.
   - 한 장 = 한 메시지. 주장이 2개 이상이면 장을 나눈다.
   - **헤드라인에 대상 이름**: 무슨 기술·제품 이야기인지 헤드라인 안에 넣어 제목만 봐도 주제가 잡히게 한다. "응답이 40% 빨라졌어요"(X) → "Redis 캐시를 거치니 응답이 40% 빨라졌어요"(O). ([`design-rules.md`](reference/design-rules.md) §2)
   - 각 장에 맞는 컴포넌트 선택은 [`visual-patterns.md`](reference/visual-patterns.md) §2 매핑표에서 고른다: 스키마카드 / 데이터흐름 / 레코드변화 / 비교매트릭스 / 계층구조 / 쉬운말풀이 / 큰숫자 KPI / 요약카드 / 2단대비 / 표 / 막대 / 선차트 / **타임라인 구간(timeline)** / **시스템 구성도(sysmap)** / 도넛 / 플로우 / 단계(steps) / 코드블록 / 공식강조 / 용어집(terms) / 한줄강조.
   - **서버·DB·캐시·큐·외부 연동이 2개 이상 나오면 `.sysmap`** — 경계(어디까지 우리 것인지)·타입·동기/비동기를 한 장에 담는다. `.flow`는 경로만 필요할 때. ⛔ 포트·내부 호스트·내부 IP는 적지 않는다. ([`visual-patterns.md`](reference/visual-patterns.md) §3)
   - **시각화 우선**: 데이터 저장·흐름·값 변화·기술 비교·구조·추세·구성비는 텍스트 나열 대신 전용 컴포넌트로 그린다. **그림 없는 슬라이드가 연속 3장을 넘으면 그 구간을 다시 설계한다.** 다이어그램에는 추상 라벨 대신 실제 컬럼명·값·데이터 조각을 넣는다.
   - **표·차트·공식을 먼저 떠올린다**: 항목이 둘 이상 비교되면 문장 대신 `table`, 비교 가능한 실측치가 2개 이상이면 `.bars`·`.linechart`·`.donut`, **시간·구간 값이 3개 이상 나열되면 `.timeline`**(어디서 시작해 어디까지인지·서로 품는지가 보이게), 실데이터가 없어도 계산으로 유도되는 값은 `.formula` 한 줄로 보여준다(가정은 각주). ([`design-rules.md`](reference/design-rules.md) §3)
   - **병기**: 시각 요소가 텍스트를 대체하지 않는다 — 핵심 해석·수치·용어 설명을 함께 둔다. 어려운 개념 바로 아래에는 `.plain`(쉬운 말 풀이)로 일상 비유를 한 문장 붙인다.
   - 실데이터가 있을 때만 차트, 예시값은 각주 명시.
   - 보강 모드면 기존 슬라이드는 두고 **추가·수정할 지점만** 설계한다.
   - **깊이·분량**: 이해에 필요한 내용은 줄이지 않는다. 주제 복잡도에 맞게 슬라이드를 늘리고, 동작·실패 과정은 단계(steps)로 분해(위험=bad/해소=ok/핵심=key), 근거·수치·코드·시나리오·흔한 오해를 충분히 담는다. 단, 뻔한 내용으로 장 수만 늘리지 않는다. ([`design-rules.md`](reference/design-rules.md) §9)
   - **높이 예산**: 한 장이 1280×720을 넘지 않게 설계 단계에서 더해본다. 본문 예산은 각주 있으면 488px·없으면 576px이고, 요소별 높이는 [`visual-patterns.md`](reference/visual-patterns.md) §7 표를 쓴다. 코드 블록 2개 + 각주는 거의 항상 넘치므로 처음부터 장을 나눈다.
   - **개요 + 심화 2단**: 복잡한 메커니즘은 개요 흐름 한 장 뒤에 심화 여러 장으로 쪼갠다. 흐름의 **중간 컴포넌트·단계를 생략하지 않는다**(A→Z로 뭉치기 금지).
   - **용어**: 비전공 독자에게 낯선 말은 전부 하단 각주로 푼다(슬라이드당 2~5개, 필요하면 더). **앞 장에서 이미 설명한 용어라도 어려우면 다시 나온 장에서 또 푼다** — 장 사이 거리와 무관하며, 같은 뜻풀이가 반복돼도 괜찮다. 한 줄로 안 끝나는 개념은 각주 대신 `.plain`이나 소개 장으로 올리고, 용어 많은 덱은 **마무리 직전 "용어 사전"(terms) 슬라이드**를 둔다. ([`design-rules.md`](reference/design-rules.md) §8)
6. **HTML 생성 / 보강** —
   - **신규**: `template.html`의 구조·CSS·JS를 그대로 쓰고 슬라이드 내용만 채운다.
   - **보강**: 기존 파일을 **그 자리에서 편집**해 슬라이드를 추가·수정한다. meta의 date만 오늘로 갱신, **파일명·경로 유지**.
   - 헤드라인은 완결 주장문(해요체), 카피는 [`design-rules.md`](reference/design-rules.md) §6 토스 톤 준수.
   - **코드는 복사돼 쓰인다**: 생성자·필드·import가 빠져 그대로는 컴파일되지 않는 예제를 싣지 않는다. 줄여야 하면 `.cmt`에 무엇을 줄였는지 적는다. 캡션이 주장하는 동작은 그 장 코드에 눈으로 보여야 한다. ([`design-rules.md`](reference/design-rules.md) §11)
   - 낯선 전문용어는 그 슬라이드 하단에 `.gloss` 각주로 짧게 설명한다. 약어는 풀텍스트 병기. **`.gloss`를 넣은 `<section>`에는 `has-gloss` 클래스를 함께 붙여** 본문과 겹치지 않게 한다. ([`design-rules.md`](reference/design-rules.md) §8)
   - `<meta name="deck-*">` 4종(title/date/category/summary)을 채운다(보강 시 date만 갱신).
   - `#counter`·`slides.length`는 실제 장 수에 맞춘다.
   - **홈 버튼**: `.rp-deck.json`에 `home`이 있으면 `#home`의 href를 그 값으로 채운다(같은 탭). 없으면 `<a id="home">`를 삭제한다. 보강 시 기존 덱에 `#home`(및 `#hud-br`)이 없고 `home`이 설정돼 있으면 우하단 HUD를 현재 `template.html` 구조(`#hud-br` > `#home` + `#counter`)로 맞춰 홈 버튼을 추가한다. ([`operations.md`](reference/operations.md) §홈 버튼)
7. **자동 분류 (신규만)** — 내용을 보고 최대 4레벨 경로를 정한다. 보강은 기존 경로를 그대로 유지한다.
   - 1레벨: 대분류(기술 / 기획 / 운영 …)
   - 2레벨: 세부(백엔드 / 프론트 …) · 3레벨: 스택/영역(스프링 …) · 4레벨: 선택
   - 필요 없는 레벨은 생략 가능(최소 1레벨).
8. **저장** — 신규: 대상 루트(레포 모드=캐시, 로컬 모드=`<cwd>/docs/decks`) 아래 `<1>/<2>/<3>/<4>/<제목>_<YYYY-MM-DD>.html`(공백→`-`, 특수문자 제거). 보강: 기존 파일 경로에 덮어쓰기.
9. **인덱스 갱신** — `python3 <스킬경로>/scripts/update_index.py <대상 루트>` 실행.
10. **자가 린트** — [`design-rules.md`](reference/design-rules.md) §10 체크리스트를 통과하는지 확인 후 위반 시 수정. **전 슬라이드가 1280×720 안에 들어가는지 반드시 확인한다** — 넘치면 글자가 잘리고 각주와 겹친다([`visual-patterns.md`](reference/visual-patterns.md) §7).
    - 손으로 그린 인라인 SVG가 있으면 `python3 <스킬경로>/scripts/lint_svg.py <생성한 HTML>`을 돌린다. **OVERLAP·NODE_OVERLAP·CLIP은 반드시 0건으로 고치고**, INDENT는 계층 표현인지 판단해 채택·보류한다([`visual-patterns.md`](reference/visual-patterns.md) §8).
11. **독립 리뷰 (2라운드)** — 작성 에이전트가 아닌 **진입 런타임의 새 서브에이전트**에 [`review.md`](reference/review.md) §3 프롬프트 템플릿을 그대로 넘겨 10개 항목 평가를 받는다(⛔ 매번 프롬프트를 새로 짓지 않는다). **호출 1건당 10분 상한**을 프롬프트에 명시하고, 초과하면 1줄 기록 후 스킵·재시도 없음. 수정 후 §4를 덧붙여 1회 더 요청(총 2라운드), 충돌은 `design-rules.md` 우선으로 메인이 판단해 반영. push 전에 완료.
12. **적재 (레포 모드만)** — 캐시에서 `git add -A` → 커밋 → `git push`. **push 성공까지 확인**하고, 실패하면 중단·보고(로컬에만 커밋 남기지 않음). 로컬 모드는 건너뛴다.
13. **옵시디언 Ingest (topic 모드만)** — vault가 설정/응답됐으면 원본→`sources/`, 정리→`wiki/<도메인>/`, `[[링크]]`, `index.md`·`log.md` 갱신. **vault `CLAUDE.md` 스키마 우선.** `obsidian: false`·미설정·비-topic이면 건너뛴다. ([`operations.md`](reference/operations.md) §옵시디언 지식베이스 적재)
14. **오픈** — 생성/보강된 HTML을 `open`으로 실행. 대상(레포/로컬)·경로·장 수·**보강/신규 여부**·**옵시디언 적재 여부**를 한 줄로 보고.

## 절대 규칙

- **외부 라이브러리 금지** — Pretendard 웹폰트 CDN link만 허용. 차트·다이어그램은 순수 CSS/SVG.
- **단일 HTML** — 인라인 CSS/JS, 파일 하나로 완결.
- **디자인 토큰 고정** — `template.html`의 CSS 변수·클래스를 임의로 바꾸지 않는다. 새 표현이 필요하면 기존 컴포넌트를 조합한다.
- **완전 자동** — 분류·구성은 확인 질문 없이 진행. 단, 원문이 비어 컨텍스트가 부족하면 무엇을 다룰지 사용자에게 확인한다.
- **토스 톤** — 모든 카피 해요체·문장형·긍정형. 헤드라인은 완결 주장문(명사 라벨·명사형 종결 금지).
- **독자는 비전공자 기준** — 개발자만이 아니라 **기획자·비전공 대학 4학년**이 읽어도 이해되게 쓴다. 사전지식 0을 가정하고, 용어는 첫 등장 자리에서 풀고, 어려운 개념엔 일상 비유(`.plain`)를 붙인다. "왜 필요한지"가 "어떻게 동작하는지"보다 앞. 이해에 필요하면 장 수를 늘린다. ([`design-rules.md`](reference/design-rules.md) §0)
- **헤드라인에 대상 이름 필수** — 무슨 기술·제품 이야기인지 헤드라인 안에 넣어 **제목만 봐도 주제가 잡히게** 한다. 대명사·추상어("이것","성능","구조")로 끝내지 않는다. ([`design-rules.md`](reference/design-rules.md) §2)
- **주제별 시각 표현은 매핑표를 따른다** — 데이터 저장(스키마)·흐름·값 변화·기술 비교·계층 구조는 [`visual-patterns.md`](reference/visual-patterns.md) §2가 지정한 전용 컴포넌트로 그린다. **그림 없는 슬라이드가 연속 3장을 넘지 않는다.** 다이어그램에는 추상 라벨 대신 실제 컬럼명·값을 넣는다.
- **용어 각주** — 낯선 용어는 슬라이드 하단에 짧게 설명(슬라이드당 2~5개, 필요하면 더, 약어는 풀텍스트 병기, 네 줄 이내). `.gloss` 쓰는 `<section>`에 `has-gloss` 클래스 필수.
- **타깃 레포·홈 버튼·vault는 명시 입력만 인정** — `.rp-deck.json` 또는 이번 실행 사용자 명시 답만 사용. ⛔ git remote·대화 맥락·추측 유추 금지. 레포 미등록 시 로컬(`<cwd>/docs/decks`) 생성. ([`operations.md`](reference/operations.md) §타깃 레포·§홈 버튼)
- **생성 전 기존 문서 확인** — 같은 주제면 보강, 새 주제면 신규, 애매하면 질문. ([`operations.md`](reference/operations.md) §보강 vs 신규)
- **⛔ 삭제는 확인 1회 필수** — `delete_deck.py` dry-run 제시·동의 후 `--yes` 실행. 모호·미매칭이면 중단, 옵시디언 노트는 유지. ([`operations.md`](reference/operations.md) §삭제 모드)
- **독립 리뷰 필수** — 생성·보강 후 push 전, **작성 에이전트가 아닌 진입 런타임의 새 서브에이전트**가 [`review.md`](reference/review.md) §3 템플릿으로 평가한다. ⛔ 작성자 셀프리뷰 금지, ⛔ 교차 런타임 리뷰 금지, 상한 2라운드, **호출 건당 상한 10분**(⛔ 연장·재시도 금지 — 초과 시 비차단 스킵).
- **시각 요소 병기** — 시각화를 넣어도 설명 텍스트·용어 각주를 줄이지 않는다. 시각 요소는 텍스트를 대체하지 않고 함께 둔다.
- **비교·수치는 표와 차트로** — 항목이 둘 이상 비교되면 문장 대신 표, 실측치가 2개 이상이면 차트, 계산으로 유도되는 값은 공식으로 옮긴다. 수치를 문장 안에 흘려보내지 않는다. ([`design-rules.md`](reference/design-rules.md) §3)
- **어려운 용어는 나올 때마다 다시 푼다** — 앞 장에서 설명했더라도 그 장에서 또 설명한다. 독자는 중간부터 볼 수도 있고, 각주는 본문을 밀지 않아 반복 비용이 거의 없다. ([`design-rules.md`](reference/design-rules.md) §8)
- **코드는 복붙 가능해야 한다** — 생성자·필드·import가 빠져 컴파일되지 않는 예제 금지. 줄였으면 `.cmt`에 명시. **캡션이 주장하는 동작은 그 장 코드에 실제로 보여야** 하고, 앞 장의 판정과 뒤 장의 해법이 모순되면 안 된다. 단정 앞에는 반례를 확인하고, 인용한 사례엔 출처와 결말을 적는다. ([`design-rules.md`](reference/design-rules.md) §11)
- **720px를 넘기지 않는다** — 설계 단계에서 높이 예산으로 더해보고, 만든 뒤 실제로 확인한다. 넘치면 눌리지 않고 잘린다. ([`visual-patterns.md`](reference/visual-patterns.md) §7)
- **손으로 그린 SVG는 블록 좌단이 x=0** — `viewBox="0 0 1104 H"`를 쓰면 x=0이 헤드라인 왼쪽 끝과 맞는다. 라벨 열을 오른쪽 맞춤할 땐 **가장 긴 라벨이 x=0**에 오게 앵커를 잡는다(짧은 라벨을 넉넉한 앵커에 붙이면 왼쪽이 이유 없이 빈다). 인접 `<text>`의 y 간격은 글자 크기 + 8 이상, 박스끼리 걸치기 금지(품는 건 정상), viewBox 밖 이탈 금지. push 전 `lint_svg.py`로 OVERLAP·NODE_OVERLAP·CLIP 0건 확인. ([`visual-patterns.md`](reference/visual-patterns.md) §8)
- **작업 전 원격 최신화·호스트 일반화·push 완료** — 레포 모드는 작업 전 캐시를 원격 최신으로 강제 동기화(`fetch`+`reset --hard`)하고, 전체 URL이면 그 호스트 그대로 쓰며(github.com 가정 금지), 커밋 후 push까지 완료한다. ([`operations.md`](reference/operations.md) §타깃 레포)
- **옵시디언은 topic 모드만·vault 컨벤션·질문 평생 한 번** — 원본 `sources/`·정리 `wiki/` 적재, vault 규칙 파일 스키마 우선, 민감정보 금지. `obsidian: false`면 다시 묻지 않고 스킵, 거절 시 `"obsidian": false` 즉시 저장. ([`operations.md`](reference/operations.md) §옵시디언 지식베이스 적재)

## 확장

`rp-deck`는 여러 입력 모드를 하나의 스킬로 처리한다. 새 입력원(예: URL, PDF)이 필요하면 3단계 입력 수집만 확장하고 이후 파이프라인은 공유한다.
