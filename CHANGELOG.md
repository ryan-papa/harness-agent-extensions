# Changelog

`rp-plugins` 플러그인 버전 이력. [SemVer](https://semver.org/lang/ko/) 준수.
스킬 변경 시 `rp-plugins/.claude-plugin/plugin.json`의 `version`과 이 파일을 함께 갱신한다.

## [0.1.0] - 2026-07-02

### Added
- `rp-deck` 스킬 — 작업 산출물·문서·주제를 토스 스타일 HTML 슬라이드 장표로 변환
  - 입력 3모드 (컨텍스트 / 파일 / 주제·deep-research)
  - 의존성 없는 단일 HTML, 슬라이드형 네비게이션 (키보드·스와이프·진행바)
  - `docs/decks/` 4레벨 자동 분류 저장 + `index.html` 자동 갱신
  - 디자인·전달력 규칙 SSOT (`reference/template.html`, `reference/design-rules.md`)
  - 인덱스 생성 스크립트 (`scripts/update_index.py`, stdlib only)
