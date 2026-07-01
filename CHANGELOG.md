# Changelog

## [0.6.1] - 2026-07-02

### Changed
- 대상 레포는 `.rp-deck.json` 또는 이번 실행 명시 입력으로만 지정 — git remote·대화 맥락·추측 등 **어떤 유추·자동 지정도 금지**. 명시 입력 없으면 로컬 모드
- SKILL.md에서 예시 레포명(document-center) 제거

## [0.6.0] - 2026-07-02

### Changed
- 레포 모드: **작업 시작 전 원격 강제 최신화** 규칙화 — `git fetch && git reset --hard origin/<기본브랜치>`로 캐시를 원격 SSOT에 일치시킨 뒤에만 기존 문서 확인·생성 시작 (stale 캐시로 보강/신규 오판 방지)
- 각 실행은 커밋 후 **push 성공까지 확인**, 실패 시 중단·보고 (로컬에만 커밋 남기지 않음)

## [0.5.0] - 2026-07-02

### Added
- 생성 전 기존 문서 확인 → **보강 vs 신규** 자동 판단
  - 대상 루트(레포 캐시/로컬)의 title·category·summary 종합 + 내용으로 같은 주제 여부 판단
  - 같은 주제 명확 → 기존 파일 그 자리 편집(슬라이드 추가·수정, date만 갱신, 파일명·경로 유지)
  - 새 주제 명확 → 신규 생성 / 애매 → 사용자에게 보강·신규 확인
  - SKILL.md §보강 vs 신규 + 워크플로우 4단계 추가 + 절대 규칙 반영

`rp-plugins` 플러그인 버전 이력. [SemVer](https://semver.org/lang/ko/) 준수.
스킬 변경 시 `rp-plugins/.claude-plugin/plugin.json`의 `version`과 이 파일을 함께 갱신한다.

## [0.4.0] - 2026-07-02

### Added
- 타깃 GitHub 레포 적재 — 생성 문서를 환경별로 지정한 레포에 push
  - 프로젝트 루트 `.rp-deck.json`(`{"repo":"owner/name"}`)에 대상 저장
  - 미등록 환경이면 대상 레포를 한 번 물어봄. 등록하면 캐시(`~/.rp-deck/repos/<owner>__<name>`) clone/pull → 4레벨 배치 → index 갱신 → commit·push
  - **미등록·거부 시 로컬 모드**: `<cwd>/docs/decks`에 생성·인덱스만, push 없음 (생성은 항상 수행). 묻지 않고 임의 레포 push 금지
  - SKILL.md 워크플로우(타깃 레포 확인 단계 추가)·절대 규칙 반영

### Changed
- 문서·매니페스트 노출 텍스트에서 조직명 표기 제거 (GitHub 링크 경로는 유지)

### Fixed
- SKILL.md 자가 린트 참조 섹션 번호 정정 (§8 → §10)

## [0.3.0] - 2026-07-02

### Added
- 심화 컴포넌트를 `template.html` SSOT에 정식 등록 (데모 슬라이드 포함)
  - `단계(steps)` — 동작·시나리오 분해, `key`(파랑)·`bad`(빨강)·`ok`(초록) 변형
  - `코드블록(code)`·인라인 `mono`, `공식강조(formula)`
- `design-rules.md` §9 "깊이와 분량" — 이해에 필요한 내용은 줄이지 않기, 복잡도에 맞게 슬라이드 확장, 메커니즘은 단계로, 과소·과대 지양 (린트 항목 추가)
- SKILL.md 구조 설계 단계에 컴포넌트·깊이 지침 반영

## [0.2.0] - 2026-07-02

### Added
- 용어 각주(`.gloss`) — 낯선 전문용어를 해당 슬라이드 하단에 짧게 설명
  - 슬라이드당 1~3개, 약어는 풀텍스트 병기(예: `TTL(Time To Live)`), 한 줄 `·` 구분
  - `template.html` 컴포넌트 + `design-rules.md` §8 규칙 + 자가 린트 항목 추가
  - SKILL.md 워크플로우·절대 규칙에 반영

## [0.1.0] - 2026-07-02

### Added
- `rp-deck` 스킬 — 작업 산출물·문서·주제를 토스 스타일 HTML 슬라이드 장표로 변환
  - 입력 3모드 (컨텍스트 / 파일 / 주제·deep-research)
  - 의존성 없는 단일 HTML, 슬라이드형 네비게이션 (키보드·스와이프·진행바)
  - `docs/decks/` 4레벨 자동 분류 저장 + `index.html` 자동 갱신
  - 디자인·전달력 규칙 SSOT (`reference/template.html`, `reference/design-rules.md`)
  - 인덱스 생성 스크립트 (`scripts/update_index.py`, stdlib only)
