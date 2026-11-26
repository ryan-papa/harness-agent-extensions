# Tasks: Antigravity 네이티브 플러그인 및 3런타임 스킬 지원

- PRD: [`prd/20261126_143754_antigravity-plugin-support_c8894603.md`](prd/20261126_143754_antigravity-plugin-support_c8894603.md)
- 작업 통합 브랜치: `feat/antigravity-plugin-support` (최종 PR base: `main`)
- 워크트리: `worktrees/feat-antigravity-plugin-support`

| ID | 설명 | 매핑 F-XX | 상태 | 브랜치 | 의존성 |
|----|------|-----------|------|--------|--------|
| T-01 | Antigravity 네이티브 매니페스트(`rp-plugins/.antigravity-plugin/plugin.json`) 생성, `.claude-plugin/plugin.json` `0.35.0` 동기화, 정적 검증 스크립트(`scripts/validate_plugin.py`) 및 격리 픽스처 단위 테스트(`tests/test_validate_plugin.py`) 작성 | F-01, F-04 | Done | `feat/T-01-antigravity-manifest-and-validator` | — |
| T-02 | `rp-deck/SKILL.md` 부가 운영 5섹션을 `rp-deck/reference/operations.md`로 무손실 분리(본문 ≤21,000 bytes), `rp-deck/SKILL.md`·`rp-youtube-deck/SKILL.md` 교차 참조 및 필수 Read 시점 동기화, 분리·교차 링크 회귀 테스트 추가 | F-02 | Done | `feat/T-02-rp-deck-split-and-cross-refs` | T-01 |
| T-03 | 3런타임(Claude Code·Codex CLI·Antigravity) 리뷰어(`rp-deck`/`rp-post` `review.md`·`rp-post/SKILL.md`), 주체 분리·`send_message` 회신, 도구·`deep-research`·vault·스크래치 fallback 보완, `rp-codebase-recap` 미사용 `Agent` 제거 및 회귀 테스트 추가 | F-03 | Todo | `feat/T-03-three-runtime-adapters` | T-02 |
| T-04 | `CHANGELOG.md`(`0.35.0`)·`README.md`(버전·Antigravity 설치/업데이트/복구·구조 트리)·`.gitignore`(`worktrees/`)·`.github/workflows/ci.yml` 갱신 및 실레포 통합 정합 테스트 추가 | F-05, F-06, F-08 | Todo | `feat/T-04-docs-ci-and-release` | T-01, T-02, T-03 |
| T-05 | `agy plugin validate --strict --json ./rp-plugins` 통과, `agy plugin install ./rp-plugins` 연속 2회(최초+재설치) 및 `agy plugin list --json` 6스킬 활성화 검증 + 전체 테스트 최종 회귀 확인 | F-07 | Todo | `feat/T-05-local-install-verification` | T-04 |

## F-XX 커버리지 매핑

- `F-01` → T-01
- `F-02` → T-02
- `F-03` → T-03
- `F-04` → T-01, T-04
- `F-05` → T-04
- `F-06` → T-04
- `F-07` → T-05
- `F-08` → T-04
