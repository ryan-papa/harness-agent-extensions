# harness-agent-extensions

하네스용 Claude Code 플러그인·스킬 모음.

## 플러그인

### rp-plugins

`rp-*` 스킬 모음.

현재 버전 `0.28.0` ([CHANGELOG](CHANGELOG.md)).

| 스킬 | 역할 |
|------|------|
| `rp-deck` | 작업 산출물·문서·주제를 토스 스타일 HTML 슬라이드 장표로 변환. 환경별 지정 GitHub 레포에 4레벨 자동 분류 적재 + index.html 갱신. 올린 장표 삭제(URL·경로·제목 지정 → 확인 → index 재생성)도 지원 |
| `rp-post` | 소재·경험·작업 결과를 목적에 맞는 글 초안으로 변환. SNS는 실측 데이터(쓰레드 IT/개발 인기글 150개 분석) 기반 바이럴 아키타입 6종, 사내 공유는 지식 정리 아키타입 3종(존댓말·슬랙/위키 2형) → 변형 초안 2~3개 + 체크리스트 검증 |
| `rp-pr-review` | PR 링크 하나로 독립 리뷰어 둘(Claude 서브에이전트 ∥ Codex 서브프로세스)에게 동시 코드 리뷰 → 중복 병합 후 중요순 리스트로 터미널 출력. 파일 생성·PR 쓰기 없는 읽기 전용 |
| `rp-codebase-recap` | 커밋 제목 요약이 아니라 **실제 코드를 정독**해 레포 전모를 재구성. 5-pass(광역 스캔 → 정독 대상 선정 → 심층 정독 → 문제해결 케이스 스터디 → 종합)로 개요·기술스택·아키텍처·역할/기여도·정량수치·리스크를 `파일:라인` 근거와 함께 터미널 출력. 파일 저장 없는 읽기 전용 |
| `rp-youtube` | 유튜브 링크 하나로 자막(원어 우선)을 받아 타임스탬프 전사본을 만들고, 자동자막의 STT 오인식을 도메인 표기·숫자 교차검증으로 정규화한 뒤 구조·핵심 주장·수치·인용 출처를 타임스탬프 근거와 함께 터미널 출력. 자막만 받고 영상·오디오는 받지 않으며, 멤버십·비공개 영상은 우회하지 않고 중단 |
| `rp-youtube-channel` | 채널의 공개 영상을 최신순으로 훑어 **장표로 만들 수 있는 후보만** 추림. 이미 만든 영상(장표의 `deck-source-video` 메타)과 멤버십·자막없음으로 걸러진 영상을 건너뛰고 남은 것만 순차 프로브. 상태는 장표 레포에 두어 기기가 바뀌어도 유지. 터미널 표 + 후보 JSON 출력 |
| `rp-youtube-deck` | `rp-youtube` 분석 → 영상이 인용한 **원천 문서 직접 검증**(일치/보강/불일치/확인불가 대조표) → `rp-deck` 파이프라인으로 장표 생성·독립 리뷰·분류 적재·push. 원문이 영상과 다르면 원문을 싣고 차이를 명시 |

## 설치

이 레포는 Claude Code 플러그인 마켓플레이스다.

```
/plugin marketplace add ryan-papa/harness-agent-extensions
/plugin install rp-plugins@harness-agent-extensions
```

설치 후 스킬로 호출한다.

```
/rp-deck                       # 방금 끝낸 작업을 장표로
/rp-deck docs/retro.md         # 특정 문서를 장표로
/rp-deck 토스 디자인 시스템     # 주제를 조사(deep-research)해 장표로
/rp-deck 코루틴 장표 지워줘      # 올린 장표 삭제 (URL·경로·제목 지정, 확인 후 삭제)

/rp-post                       # 방금 끝낸 작업을 글 초안으로
/rp-post docs/retro.md         # 특정 문서를 소재로
/rp-post 사이드프로젝트 첫 배포 후기   # 텍스트를 소재로

/rp-pr-review https://github.com/owner/repo/pull/9   # PR을 두 리뷰어에게 병렬 리뷰

/rp-codebase-recap                            # 현재 레포를 심층 발굴
/rp-codebase-recap museum-finder              # 레포 이름으로 지정
/rp-codebase-recap https://github.com/owner/repo 작성자   # GitHub URL + 작성자 스코프

/rp-youtube https://youtu.be/VIDEOID          # 영상 자막 전사 → 분석 (터미널 출력)
/rp-youtube https://youtu.be/VIDEOID 성능 관점으로   # 분석 초점 지정

/rp-youtube-channel @handle                   # 채널에서 아직 안 다룬 후보 10건 추리기
/rp-youtube-channel @handle --limit 3         # 개수 지정
/rp-youtube-channel                           # 등록된 채널 목록

/rp-youtube-deck https://youtu.be/VIDEOID     # 영상 분석 → 원천 검증 → 장표 생성·push
/rp-youtube-deck https://youtu.be/VIDEOID 20장 실무 가이드로   # 분량·성격 지정
```

`rp-youtube` 계열은 [yt-dlp](https://github.com/yt-dlp/yt-dlp)로 **자막과 메타데이터만** 받는다. 설치돼 있지 않으면 최초 실행 시 `~/.rp-youtube/venv`에 자동 설치한다.

### 설정 — `.rp-deck.json`

`rp-deck` 산출물은 **환경별로 지정한 GitHub 레포**에 적재할 수 있다. 최초 실행 시 대상 레포를 한 번 물어보고, 알려주면 프로젝트 루트 `.rp-deck.json`에 저장돼 이후 자동으로 그 레포에 push된다. 등록하지 않으면 로컬(`docs/decks`)에만 생성된다.

| 키 | 값 | 효과 |
|----|----|------|
| `repo` | `owner/name` 또는 사내 호스트 전체 URL | 장표 적재 대상 레포. 4레벨 자동 분류 후 `index.html` 갱신 |
| `home` | 게시판 홈 URL | 각 장표 우하단에 게시판 홈 버튼 삽입 |
| `obsidian` | vault 경로 \| `false` | topic 모드의 조사 원본·정리 노트 적재 대상. `false`는 **사용자가 거절함** — 이후 다시 묻지 않는다 |

```json
{
  "repo": "owner/name",
  "home": "https://example.com/decks/",
  "obsidian": "/path/to/vault"
}
```

주제 조사(topic) 모드는 조사 원본·정리 노트를 옵시디언 vault(설정 시)에도 남긴다. vault를 한 번도 등록하지 않았으면 최초 1회만 물어보고, 필요 없다고 답하면 `"obsidian": false`로 기록해 **이후 실행에서 다시 묻지 않는다**.

## 구조

```
harness-agent-extensions/
├── .claude-plugin/marketplace.json   # 마켓플레이스 선언
└── rp-plugins/
    ├── .claude-plugin/plugin.json
    └── skills/
        ├── rp-deck/
        │   ├── SKILL.md              # 스킬 정의
        │   ├── reference/
        │   │   ├── template.html       # 디자인·컴포넌트 SSOT
        │   │   ├── design-rules.md     # 독자 기준·구조·전달력·토스 톤 규칙
        │   │   ├── visual-patterns.md  # 주제 → 시각 표현 매핑 SSOT
        │   │   └── review.md           # 독립 에이전트 병렬 리뷰 프로토콜
        │   └── scripts/
        │       ├── update_index.py    # 인덱스 생성 (stdlib only)
        │       └── delete_deck.py     # 덱 삭제 + 인덱스 재생성 (stdlib only)
        ├── rp-pr-review/
        │   └── SKILL.md              # 스킬 정의 (단일 파일)
        ├── rp-codebase-recap/
        │   └── SKILL.md              # 스킬 정의 (단일 파일)
        ├── rp-youtube/
        │   ├── SKILL.md              # 스킬 정의
        │   └── scripts/
        │       └── fetch_transcript.py  # 메타+자막 → 타임스탬프 전사본 (stdlib + yt-dlp)
        ├── rp-youtube-channel/
        │   ├── SKILL.md              # 스킬 정의
        │   └── scripts/
        │       └── list_channel.py      # 채널 목록 → 상태 대조 → 순차 프로브 (stdlib + yt-dlp)
        ├── rp-youtube-deck/
        │   └── SKILL.md              # 오케스트레이터 (rp-youtube → 원천 검증 → rp-deck)
        └── rp-post/
            ├── SKILL.md              # 스킬 정의
            └── reference/
                ├── patterns.md       # 실측 통계 SSOT + 데이터 갱신 절차
                ├── archetypes.md     # 아키타입 공식 (바이럴 A1~A6 · 사내 K1~K3)
                ├── checklist.md      # 초안 검증 (바이럴용·사내용 각 7항목)
                ├── platforms.md      # 플랫폼 프로파일·변환 규칙
                └── review.md         # 독립 에이전트 병렬 리뷰 프로토콜
```
