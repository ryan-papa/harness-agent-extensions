# Changelog

`rp-plugins` 플러그인 버전 이력. [SemVer](https://semver.org/lang/ko/) 준수.
스킬 변경 시 `rp-plugins/.claude-plugin/plugin.json`의 `version`과 이 파일을 함께 갱신한다.

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
