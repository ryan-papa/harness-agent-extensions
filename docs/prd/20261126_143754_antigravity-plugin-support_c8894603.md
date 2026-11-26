# PRD: Antigravity 네이티브 플러그인 및 3런타임 스킬 지원

**ID:** 20261126_143754_antigravity-plugin-support_c8894603
**날짜:** 2026-11-26
**상태:** Approved

---

## 문제·맥락

- **배경:** `harness-agent-extensions` (`rp-plugins`, v0.34.0)는 현재 Claude Code 플러그인 마켓플레이스(`.claude-plugin/`) 형식으로만 패키징되어 있다. Antigravity(CLI · App · IDE) 사용자가 6개 스킬(`rp-deck`, `rp-post`, `rp-codebase-recap`, `rp-youtube`, `rp-youtube-channel`, `rp-youtube-deck`)을 그대로 설치·실행하기 어렵다.
- **원인:** 현재 워크트리 정적 스캔과 임시 디렉터리 드라이런(`agy plugin validate --strict`)으로 4가지 구조적 결손이 확인되었다.
  1. **네이티브 매니페스트 부재:** `rp-plugins/`에 `.antigravity-plugin/plugin.json`이 없어 현재 워크트리에서 `agy plugin validate`가 매니페스트 부재 에러 1건으로 즉시 종료된다.
  2. **`rp-deck/SKILL.md` 본문 크기 한도 초과:** 임시 매니페스트 드라이런(`agy plugin validate --strict`)에서 `rp-deck/SKILL.md` 본문이 **28,959 bytes**(정적 UTF-8 측정 28,961 bytes)로 Antigravity 로더 상한(24,000 bytes)을 초과해 뒷부분(§절대 규칙 등 약 5KB)이 절단 로드되는 경고가 발생한다.
  3. **3런타임(Antigravity) 리뷰어·도구 표기 누락:** `rp-deck/reference/review.md`, `rp-post/reference/review.md`, `rp-post/SKILL.md`가 Claude Code(`Agent`)와 Codex CLI(`spawn_agent`)만 명시하고 Antigravity(`invoke_subagent`, `TypeName: "self"`, `send_message` 텍스트 회신) 규칙과 3런타임 교차 금지 범위를 누락했다. 또한 `rp-deck`의 `deep-research`·`CLAUDE.md` 단일 표기, `rp-post`·`rp-youtube-deck`의 `WebSearch`/`WebFetch` 단일 표기, `rp-codebase-recap`의 `scratchpad` fallback 누락 및 미사용 `allowed-tools: Agent` 잔재가 존재한다.
  4. **문서·버전 정합 드리프트:** `README.md`가 `0.28.0`으로 6버전 밀려 있고(현재 `0.34.0`), `CI`가 `README.md` 버전·Antigravity 매니페스트·24KB 상한을 검증하지 않는다.
- **왜 지금:** v0.32.0에서 이미 진입 런타임 단독 리뷰 원칙을 도입했다. Antigravity를 3번째 정식 지원 런타임으로 편입하고 네이티브 플러그인 규격을 충족하면 Claude Code·Codex CLI·Antigravity 모두 단일 스킬 소스로 운영할 수 있다.

## 타깃 사용자와 사용 맥락

| 항목 | 내용 |
|------|------|
| 대상 사용자 | Antigravity CLI·App·IDE 또는 Claude Code를 단독·병행 사용해 `rp-*` 확장 스킬을 실행하는 개발자(본 레포 관리자 및 팀원) |
| 사용 맥락 | Antigravity 세션에서 `/rp-deck`, `/rp-post`, `/rp-codebase-recap`, `/rp-youtube*`를 호출하고, Claude Code와 병행 시 기존 설정(`.rp-deck.json`)·캐시(`~/.rp-deck/repos/`)·로컬 작업·venv(`~/.rp-youtube/`)·채널 상태(`<대상루트>/.rp-youtube/`)를 그대로 공유하며, 레포 업데이트 후 `agy plugin install ./rp-plugins`로 재설치하는 상황 |
| 핵심 동기 | 별도 변환 사본이나 수동 복붙 없이 로컬 클론 후 `agy plugin install ./rp-plugins` 한 번으로 6개 스킬을 절단 없이 설치하고, Claude Code 환경과 동일한 품질(독립 리뷰·설정/캐시 공유 포함)을 유지하는 것 |

## 핵심 시나리오

| # | 장면 | 사용자 행동 | 시스템 반응 |
|---|------|-----------|-----------|
| 1 | 플러그인 검증 및 설치 | 레포 클론 후 `agy plugin validate --strict ./rp-plugins` 및 `agy plugin install ./rp-plugins` 실행 | 에러 0건·경고 0건으로 검증 통과 후 `~/.gemini/config/plugins/rp-plugins`에 6개 스킬이 활성화되고 `agy plugin list --json`에 표시됨(재실행 시 업데이트 반영) |
| 2 | 장표 생성 및 독립 리뷰 | Antigravity에서 `/rp-deck` 실행 | 24,000 bytes 이하 `SKILL.md` 전문이 절단 없이 로드되고, `reference/operations.md`를 Read해 저장·옵시디언·삭제 규칙을 적용하며, 독립 리뷰 시 `invoke_subagent`(`TypeName: "self"`) + `send_message` 텍스트 회신으로 2라운드 검수 수행 |
| 3 | 오케스트레이터 스킬 실행 | Antigravity에서 `/rp-youtube-deck <URL>` 실행 | 형제 스킬(`../rp-youtube`, `../rp-deck`, `../rp-deck/reference/operations.md`, `../rp-youtube-channel`)을 동일 플러그인 디렉터리에서 상대경로로 로드하고, 웹 검색·원문 조회 후 장표 생성·독립 리뷰·적재 완료 |
| 4 | PR 회귀 방지 CI | 스킬·문서 수정 후 PR 생성 | GitHub Actions가 매니페스트 2종·`CHANGELOG.md`·`README.md` 4자 버전 정합, 스키마, 전 `SKILL.md` 본문 ≤24,000 bytes, `name`==폴더명, 플러그인 내부 상대 링크, 민감정보·로컬 경로 스캔을 자동 검사 |

**실패 모드 테이블 (코드경로 × 시나리오 × 감지 × UX):**

| 코드경로 | 시나리오 | 감지 방법 (테스트) | UX 대응 |
|----------|----------|------------------|---------|
| `agy plugin install ./rp-plugins` | 기설치·`import claude` 충돌 또는 덮어쓰기 실패 / 권한 없음 | QA 실측: 연속 2회 `agy plugin install ./rp-plugins` 실행 및 `agy plugin list --json` 확인, 비정상 종료 코드로 감지 | 충돌·실패 시 오류 원문 출력 후 `agy plugin uninstall rp-plugins && agy plugin install ./rp-plugins` 복구 명령 안내 |
| `rp-deck/SKILL.md` (topic 모드) | Antigravity 환경에 `deep-research` 스킬 미설치 | 스킬 존재 확인 불가(또는 호출 실패) 시 분기 | 웹 검색 도구(`search_web` 등)로 공식 문서·원천 자료를 직접 심층 조사하는 fallback으로 진행 |
| `rp-deck`·`rp-post` `reference/review.md` | Antigravity `invoke_subagent` 호출 실패 · 10분 타임아웃 · `send_message` 미회신 | 비동기 대기 중 오류/타임아웃/미회신 발생 시 메인이 감지 | 재시도·연장 없이 1줄 로그(`타임아웃/실패: 스킵`) 기록 후 비차단으로 다음 단계 진행 |
| `agy plugin validate --strict` | F-01 적용 후 타 도구 파일(`.claude-plugin` 등) 또는 frontmatter 경고 발생 | QA 실측: `agy plugin validate --strict --json ./rp-plugins` 실행 | Antigravity 파일 경고는 즉시 수정; 타 도구 파일 전용 경고 발생 시 공식 `--json` 필터링 기준 적용 및 사유 문서화 |
| `scripts/validate_plugin.py` | 빈 `skills/` · 깨진 JSON/스키마 · 4자 버전 불일치 · 24,001B 초과 · `rp-plugins/` 경로 탈출 · 로컬 경로/시크릿 포함 | 단위 테스트(`unittest`): 각 시나리오 격리 픽스처(`--repo-root`)로 exit code 1 및 오류 메시지 검증 | 위반 파일 경로·사유·기준값(예: 바이트 상한/기대 버전)을 출력하고 CI 실패 |

## 대안 탐색 (A/B/C/D)

| 대안 | 요약 | 장점 | 단점 | 공수 | 판단 근거 유형 |
|------|------|------|------|------|--------------|
| A | `rp-plugins/.antigravity-plugin/plugin.json` 추가 + 단일 `rp-plugins/skills/` 공유 + `rp-deck/SKILL.md` ≤21KB 분리 + 3런타임 어댑터·CI 검증 | Antigravity 공식 멀티 프로바이더 표준, 스킬 사본·드리프트 0, `agy plugin validate --strict` 0건, 형제 스킬 상대경로 보존 | `rp-deck` 부가 운영 섹션이 `reference/operations.md`로 1단계 분리됨 | 소(1일 이내) | 제품 가설 |
| B | 별도 변환 스크립트로 `.agents/skills/` 변환 사본 생성·커밋 | 런타임별 독립 본문 커스터마이징 가능 | 스킬 2벌 관리·드리프트 위험, `agy plugin` 매니저 이점 상실 | 중 | 엔지니어 선호 |
| C | `rp-plugins/plugin.json`만 추가하고 `SKILL.md`·`review.md` 현행 유지 | 변경 파일 최소화 | `rp-deck` 뒷부분 5KB 절단 로드, Antigravity 독립 리뷰 호출 규칙 누락 | 극소 | 엔지니어 선호 |
| D (현상 유지) | Claude Code 전용 유지, 로컬에서 `agy plugin import claude` 수동 사용 | 레포 변경 0 | `rp-deck` 절단·리뷰어 누락 미해결, 기기 변경마다 수동 마이그레이션 필요 | 없음 | 창업자 직감 |

**선택:** **A**
**선택 근거:** 공식 Antigravity 멀티 프로바이더 가이드가 `.claude-plugin/plugin.json` 공존 시 루트 `plugin.json` 대신 대칭 위치인 `.antigravity-plugin/plugin.json`(우선순위 상위)을 권장하며, `agy plugin validate` 실측(24,000 bytes 상한) 제약을 단일 SSOT 유지로 해소하는 제품 가설에 부합한다.

## 톤·정체성 (Voice)

| 항목 | 정의 |
|------|------|
| 톤 | 담백·실용적·규칙 중심(기존 `rp-plugins` 문서 스타일 계승) |
| 어투 | 문서·규칙은 간결한 평서체(`~한다`), 표·리스트 우선. 기술 용어·명령어 원어 유지 |
| 금칙어 | 특정 런타임만의 도구명을 유일 수단으로 강제하는 표현, 내부 호스트·개인정보·로컬 절대경로 |
| 레퍼런스 | 기존 `rp-plugins/skills/rp-deck/reference/review.md`, `CHANGELOG.md` v0.32.0 |
| 샘플 카피 | 1) "진입 런타임의 새 서브에이전트 1인을 띄운다." 2) "`agy plugin validate --strict ./rp-plugins`로 0 errors·0 warnings를 확인한다." 3) "세부 운영 규칙(타깃 레포·홈 버튼·옵시디언·보강/신규·삭제 모드)은 [`reference/operations.md`](reference/operations.md)를 Read한다." |

## 스코프 & 비-스코프

| 포함 (In) | 비포함 (Out) |
|-----------|-------------|
| `rp-plugins/.antigravity-plugin/plugin.json` 신규 생성 (v0.35.0) 및 `.claude-plugin/plugin.json` 버전 `0.35.0` 동기화 | Antigravity 공식 Partner Marketplace 외부 제출·심사 |
| `rp-deck/SKILL.md` 부가 운영 상세를 `rp-deck/reference/operations.md`로 분리(목표 ≤21,000 bytes) + `rp-deck`·`rp-youtube-deck` 교차 참조 동기화 | 본 레포 자체의 Antigravity 원격 `marketplace.json` 카탈로그 구성 (로컬 클론 후 `agy plugin install ./rp-plugins` 설치 지원; `.claude-plugin/marketplace.json`은 Claude Code 전용 현행 유지) |
| 3런타임(Claude Code · Codex CLI · Antigravity) 리뷰어·도구·fallback 보완 (`rp-deck`, `rp-post`, `rp-youtube-deck`, `rp-codebase-recap`, `review.md` 2종) | 6개 스킬의 핵심 비즈니스 로직(장표 디자인 토큰·바이럴 아키타입·유튜브 파이썬 스크립트 동작) 변경 |
| 정적 검증 스크립트(`scripts/validate_plugin.py`) + 단위 테스트(`tests/test_validate_plugin.py`) + CI(`.github/workflows/ci.yml`) 연동 | 별도 로고 이미지 제작(Note 수준 비차단), MCP 서버·훅(`hooks.json`)·커스텀 에이전트(`agents/`) 신규 추가 |
| `README.md`·`CHANGELOG.md`·`.gitignore`(`worktrees/`) 갱신 및 로컬 `agy plugin install ./rp-plugins` 전역 설치 | `docs/posts/` 기존 포스트 수정 및 Codex CLI 전역 설치 자동화 |

## 성공 기준 & 실패 기준

| 구분 | 지표 | 목표값 |
|------|------|--------|
| 성공 | `agy plugin validate --strict --json ./rp-plugins` 결과 | `components.skills == 6`, Error 0건, Warning 0건 (exit code 0) |
| 성공 | 6개 `SKILL.md` 본문 UTF-8 바이트 크기 | 전 파일 ≤ 24,000 bytes (`rp-deck/SKILL.md` 목표 ≤ 21,000 bytes) |
| 성공 | 로컬 전역 설치 및 재설치 업데이트 | `agy plugin install ./rp-plugins` 연속 2회 정상 통과, `agy plugin list --json`에 `rp-plugins` `enabled: true` 및 6개 스킬 전부 노출 |
| 성공 | CI·단위 테스트 통과 | `scripts/validate_plugin.py` 및 `python3 -m unittest discover -s tests` 100% 통과, 4자 버전 정합 및 기존 Claude Code CI 체크 무회귀 |
| 실패 (접을 기준) | `agy plugin validate` 에러 잔존, 24KB 절단 미해소, 또는 기존 Claude `.claude-plugin/` 호환성 파괴 | 1건이라도 발생 시 즉시 수정 또는 `git revert` 롤백 |

## 사용자 검증 게이트

| 검증 대상 | 대상 기능 (F-XX) | 검증 방법 | 합격선 | 확인 시점 | 실패 시 조치 |
|-----------|-----------------|-----------|--------|-----------|-------------|
| Antigravity CLI 검증·설치·재설치 및 6스킬 노출 | F-01, F-02, F-07 | 내부 시범 사용 (`agy plugin validate --strict --json`, `agy plugin install` 연속 2회, `agy plugin list --json`) | Error 0·Warning 0, `enabled: true`, 6스킬 전부 노출 | 배포 전 (QA 단계 워크트리) 및 머지 직후 (`main` 최종 재설치) | 매니페스트·SKILL 분리 수정 후 재검증 (머지 후 실패 시 `git revert`) |
| Antigravity 실세션 스킬 호출·교차 참조·독립 리뷰 | F-02, F-03 | 내부 시범 사용 (실제 Antigravity 세션에서 `/rp-deck`·`/rp-post`·`/rp-youtube-deck` 각 1회 이상 호출) | 절단 0건, `operations.md` 및 형제 스킬(`../rp-*`) 경로 오류 0건, `invoke_subagent`+`send_message` 리뷰 표 반환·셀프리뷰 0건 | 배포 후 (7일 이내) | 해당 스킬 문서·레퍼런스 핫픽스 PR 또는 `git revert` 롤백 |

> 참고: `F-04`·`F-05`는 자동화 검증 게이트(GitHub Actions CI 및 로컬 `unittest`)로 매 커밋/PR에서 검증한다.

## 가정 · 리스크 · 열린 질문

| 유형 | 내용 | 검증 방법 |
|------|------|----------|
| 가정 | `가정:` 6개 스킬 전체를 변환 대상에 포함하고 기존 Claude Code 플러그인 호환성(`.claude-plugin/`)을 유지한다. | `.claude-plugin/plugin.json` 검증 및 CI 실행 |
| 가정 | `가정:` 임시 드라이런에서 `rp-codebase-recap/SKILL.md`의 `argument-hint`·`allowed-tools`는 `--strict` 무경고로 관측되었으나, F-01 적용 직후 실제 워크트리에서 재검증한다(경고 발생 시 필드 조정 또는 공식 필터 적용). | F-01 적용 직후 `agy plugin validate --strict --json ./rp-plugins` 실측 |
| 가정 | `자동 선택(9.5):` `rp-plugins/.antigravity-plugin/plugin.json` 네이티브 매니페스트로 단일 `rp-plugins/skills/`를 공유한다. | `agy plugin validate --strict` + `agy plugin list --json` |
| 가정 | `자동 선택(9.0):` `rp-deck/SKILL.md`의 부가 운영 섹션(타깃 레포·홈 버튼·옵시디언·보강/신규·삭제 모드)을 `reference/operations.md`로 분리해 본문을 ≤21,000 bytes(상한 24,000 bytes)로 축소한다. | `scripts/validate_plugin.py` + `agy plugin validate --strict` |
| 요청 번복 | 해당 없음 — 사용자 발화·결정과 상충한 번복 없음 | (해당 없음 — 사용자 확정) |
| 리스크 | `rp-deck/SKILL.md`에서 `reference/operations.md`로 분리한 규칙을 `rp-deck` 또는 형제 오케스트레이터 `rp-youtube-deck`이 건너뛸 가능성 | `rp-deck/SKILL.md` §레퍼런스 표·워크플로우 1단계·삭제 모드 진입 시 `operations.md` 필수 Read 명시 및 `rp-youtube-deck/SKILL.md` 레퍼런스 로드·섹션 참조 동기화 + 상대 링크 검증 |
| 리스크 | GitHub Actions(`ubuntu-latest`)에 `agy` 바이너리 미설치로 `agy plugin validate` 직접 실행 불가 | `scripts/validate_plugin.py`로 스키마(`additionalProperties: false`)·4자 버전·24KB 상한·경로 탈출·민감정보를 동등 구현하고 로컬 QA에서 `agy plugin validate --strict` 병행 검증 |
| 리스크 | `agy plugin install ./rp-plugins`는 복사형 설치라 이후 레포 수정 시 재설치 필요, `disable` 상태는 `config.json`에 영속 유지 | `README.md`에 업데이트 재설치 및 `agy plugin enable rp-plugins` 복구 명령 명시 |
| 열린 질문 | 없음 — Q1(원본 레포 + 로컬 전역 설치), Q4(`agy plugin install` 공식 매니저) 모두 사용자 확정 완료 | — |

---

## 기능 요구사항

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| F-01 | `rp-plugins/.antigravity-plugin/plugin.json` 생성 (`$schema`, `name: "rp-plugins"`, `displayName: "RP Harness Extensions"`, `version: "0.35.0"`, `description`, `author`, `repository`, `keywords`, 대표 3개 시나리오 `/rp-deck`·`/rp-post`·`/rp-youtube-deck` 기반 `suggestedPrompts` 3건) 및 `.claude-plugin/plugin.json` 버전 `0.35.0` 동기화 | Must |
| F-02 | `rp-deck/SKILL.md`의 부가 운영 5섹션(`§타깃 레포`, `§홈 버튼`, `§옵시디언 지식베이스 적재`, `§보강 vs 신규`, `§삭제 모드`)을 `rp-deck/reference/operations.md`로 무손실 분리(본문 목표 ≤21,000 bytes, 하드 상한 ≤24,000 bytes). `rp-deck/SKILL.md`의 모든 분리 대상 `§...` 참조를 `reference/operations.md` 링크로 치환하고 일반 1단계·삭제 모드 진입 시 필수 Read를 명시하며, 형제 스킬 `rp-youtube-deck/SKILL.md`의 레퍼런스 로드 및 `§보강 vs 신규`·`§옵시디언` 참조를 `../rp-deck/reference/operations.md`로 동기화 | Must |
| F-03 | 3런타임(Claude Code · Codex CLI · Antigravity) 리뷰어·도구·경로 호환 보완: (1) `rp-deck/reference/review.md`·`rp-post/reference/review.md`에 Antigravity(`invoke_subagent`, `TypeName: "self"`, `send_message` 텍스트 회신 필수, `swarm`·이전 리뷰어 재호출 금지, 비동기 대기/10분 타임아웃 비차단 스킵) 추가 및 `rp-deck/reference/review.md`·`rp-post/reference/review.md`·`rp-post/SKILL.md`(§절대 규칙) 3런타임 교차 금지 확장; (2) 리뷰어 서브에이전트의 대상 파일 수정·결과 파일/artifact 생성 금지와 `rp-post` 메인의 입력 임시 파일(`<스크래치 디렉터리>/rp-post-review.md`, 레포 외부 임시 경로) 허용 경계 명확 분리; (3) `rp-post/SKILL.md`·`rp-youtube-deck/SKILL.md`의 웹 검색/조회 도구 표기 중립화, `rp-deck/SKILL.md`의 `deep-research` 미설치 시 웹 검색 fallback 및 vault 규칙 파일(`CLAUDE.md`/`GEMINI.md`/`AGENTS.md`/`README.md`) 중립화, `rp-codebase-recap/SKILL.md`의 스크래치 경로 임시 디렉터리 fallback 추가 및 v0.32.0 미사용 `allowed-tools: Agent` 제거 | Must |
| F-04 | 플러그인 정적 검증 스크립트 `scripts/validate_plugin.py`(stdlib only, `--repo-root` 지원) 및 단위 테스트 `tests/test_validate_plugin.py` 작성: (1) JSON 유효성 및 Antigravity `schemas/v1/plugin.json` 검증(허용 키 화이트리스트 `additionalProperties: false`, `name` kebab-case, `displayName` 금지 접두 `Antigravity`/`Gemini`/`Claude`/`Cursor` 및 금지 접미 `Plugin`/`Plugins`/`MCP`, `suggestedPrompts` ≤3, `repository` `https://`, `author` 구조); (2) `.claude-plugin/plugin.json`·`.antigravity-plugin/plugin.json`·`CHANGELOG.md`·`README.md` 4자 버전 정합; (3) 멀티라인 블록 스칼라(`|`/`>`) 지원 stdlib YAML frontmatter 파서로 `name`==폴더명(`1~64자`)·`description`(`1~1,024자`) 검증; (4) frontmatter 종료 `---` 직후 개행 제거 본문 `len(body.encode("utf-8"))` ≤24,000 bytes 하드 실패 및 >22,000 bytes 마진 경고; (5) 코드 펜스 제외 `SKILL.md`·`reference/*.md` 상대 링크 존재 및 `rp-plugins/` 루트 내부(`is_relative_to`) 경로 탈출 차단; (6) 배포·공개 산출물(`rp-plugins/`, `.claude-plugin/`, `README.md`, `CHANGELOG.md`) 대상 로컬 절대경로(`/Users/`, `/home/`) 및 단어 경계+최소 길이 고신뢰 시크릿 패턴(`ghp_[A-Za-z0-9]{20,}`, `github_pat_[A-Za-z0-9_]{20,}`, `sk-(?:proj-|live-|test-)?[A-Za-z0-9_-]{16,}`, `age1[a-z0-9]{50,}`) 정적 스캔(`docs/prd/`·검증기 본체·단위 테스트 픽스처 제외, 테스트는 동적 조립 픽스처 사용) | Must |
| F-05 | `.github/workflows/ci.yml` 갱신: 기존 체크(JSON·frontmatter·버전·Python 문법)를 유지하면서 `python3 scripts/validate_plugin.py` 및 `python3 -m unittest discover -s tests` 실행 추가 | Must |
| F-06 | 릴리스 문서 갱신: `CHANGELOG.md` `[0.35.0]` 항목 기록, `README.md` 현재 버전 `0.35.0` 현행화 및 Antigravity 설치·업데이트·비활성화/재활성화 안내 추가 | Must |
| F-07 | 로컬 Antigravity 전역 설치 및 검증: `agy plugin validate --strict --json ./rp-plugins` 통과 후 `agy plugin install` 연속 2회(최초 설치 + 재설치 덮어쓰기) 검증 및 `agy plugin list --json` 6개 스킬 활성화 확인 | Must |
| F-08 | 부수 레포 정비: `README.md` 디렉터리 구조 트리 현행화(`lint_svg.py`·`operations.md`·`.antigravity-plugin/plugin.json` 반영) 및 `.gitignore`에 `worktrees/` 추가 | Should |

## 비기능 요구사항

| 항목 | 요구사항 |
|------|----------|
| 성능 | `scripts/validate_plugin.py` 및 전체 단위 테스트 실행 시간 ≤ 2초(외부 네트워크·외부 패키지 의존 0건, Python stdlib only) |
| 보안 | 민감 정보(내부 호스트·IP·인증서 경로·개인 식별 정보·API 키·시크릿) 및 로컬 절대경로(`/Users/`, `/home/`) 기재 금지(`scripts/validate_plugin.py`로 자동 회귀 검증). 상대 링크의 `rp-plugins/` 루트 탈출 차단. 기존 접근 게이트·명시 타깃 가드레일 무훼손 |
| 확장성 | `scripts/validate_plugin.py`는 `rp-plugins/skills/*`를 동적 스캔하므로 신규 스킬 추가 시 하드코딩 수정 없이 자동 검증. 신규·수정 일반 문서는 500줄 이하 유지(단, 누적 변경이력 `CHANGELOG.md`는 500줄 도달 시 아카이브 분리 전까지 예외 허용) |

## 운영 계획

| 항목 | 내용 |
|------|------|
| 배포 순서 · 선행 외부 작업 | 선행 외부 작업 없음(정적 플러그인 레포). 배포 순서: (1) 워크트리에서 구현·단위 테스트·`agy plugin validate --strict --json` 및 QA 설치(연속 2회 재설치 포함) 검증 → (2) PR 생성 → (3) GitHub Actions CI 통과 및 `main` 머지 → (4) 메인 클론 `git pull` 후 `agy plugin install ./rp-plugins` 최종 재설치(실패 시 `agy plugin uninstall rp-plugins && agy plugin install ./rp-plugins`) 및 `agy plugin list --json` 최종 확인 |
| 양방향 롤백 경로 | **롤백:** `git revert <merge-sha>`로 `main` 복귀(Claude `.claude-plugin/` 구조는 이전 버전과 100% 하위 호환되며 DB 스키마 없음), 로컬은 `agy plugin uninstall rp-plugins`로 즉시 제거. **롤포워드:** 수정 PR 머지 후 `agy plugin install ./rp-plugins` 재실행(필요 시 `agy plugin enable rp-plugins`)으로 갱신 |
| 끄는 방법 | 로컬 Antigravity 환경에서 재배포 없이 `agy plugin disable rp-plugins`로 즉시 비활성화 가능(Claude Code는 `/plugin disable`). 주의: 비활성화 상태는 `~/.gemini/config/config.json`에 영속 저장되어 재설치 후에도 유지되므로 재활성화 시 `agy plugin enable rp-plugins`를 명시 실행 |
| 볼 지표 | (1) GitHub Actions `PR Check` 통과율 100%, (2) `agy plugin validate --strict --json ./rp-plugins` 오류·경고 0건(`components.skills == 6`), (3) `agy plugin list --json` 기준 `enabled: true` 및 `skills` 6건. 하나라도 미달 시 이상 판정 |

## 공개 전환 시나리오

본 레포(`ryan-papa/harness-agent-extensions`)는 공개 GitHub 저장소다.

| 점검 항목 | 조치 |
|-----------|------|
| 개인 경로·환경 식별자 | 배포·공개 산출물(`rp-plugins/`, `.claude-plugin/`, `README.md`, `CHANGELOG.md`) 어디에도 로컬 절대경로(`/Users/`, `/home/`), 사내 호스트, 개인 이메일, 내부 IP를 기재하지 않으며 `scripts/validate_plugin.py`로 PR마다 자동 검증한다(테스트 픽스처는 실제 개인경로·토큰 미기재 및 동적 문자열 조립 사용) |
| 시크릿·토큰 | 배포·공개 산출물 대상 `scripts/validate_plugin.py` 단어 경계+최소 길이 고신뢰 시크릿 패턴 스캔 및 [9] 리뷰 전 staged diff 스캔을 이중 적용한다 |
| 레포 외부 링크 | `plugin.json`의 `repository`는 공개 GitHub HTTPS URL만 기재한다 |

## AI 기능 검증 (AI 포함 기능만 작성)

해당 없음 — 본 변경은 LLM API 호출·프롬프트 평가 파이프라인·모델 추론 코드를 추가하지 않으며, 정적 플러그인 매니페스트·마크다운 스킬 문서 정리·정적 Python 검증 스크립트만 포함한다.

## 기술 스택 · 제약사항

| 항목 | 내용 |
|------|------|
| 기술 스택 | Markdown(SKILL.md), JSON(Plugin Manifest), Python 3 stdlib(`scripts/validate_plugin.py`, `unittest`), GitHub Actions, Antigravity CLI(`agy plugin`) |
| 기술 제약 | Antigravity 로더는 `SKILL.md` 본문 앞 24,000 bytes(UTF-8 기준; 본 프로젝트 측정 기준 = frontmatter 닫는 `---` 직후 개행 제거 본문 `len(body.encode("utf-8"))`)만 로드; `plugin.json`은 `https://antigravity.google/schemas/v1/plugin.json` (`additionalProperties: false`) 준수 필요; `SKILL.md` `name`은 부모 디렉터리명과 일치 필수; GitHub Actions `ubuntu-latest`에는 `agy` CLI 미설치 |
| 비즈니스 제약 | 기존 Claude Code 플러그인(`.claude-plugin/marketplace.json`, `rp-plugins/.claude-plugin/plugin.json`) 및 CI 계약(매니페스트·`CHANGELOG.md`·`README.md` 버전 정합) 하위 호환 100% 유지 필수 |
