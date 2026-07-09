# harness-agent-extensions

하네스용 Claude Code 플러그인·스킬 모음.

## 플러그인

### rp-plugins

`rp-*` 스킬 모음.

현재 버전 `0.12.0` ([CHANGELOG](CHANGELOG.md)).

| 스킬 | 역할 |
|------|------|
| `rp-deck` | 작업 산출물·문서·주제를 토스 스타일 HTML 슬라이드 장표로 변환. 환경별 지정 GitHub 레포에 4레벨 자동 분류 적재 + index.html 갱신 |
| `rp-post` | 소재·경험·작업 결과를 목적에 맞는 글 초안으로 변환. SNS는 실측 데이터(쓰레드 IT/개발 인기글 150개 분석) 기반 바이럴 아키타입 6종, 사내 공유는 지식 정리 아키타입 3종(존댓말·슬랙/위키 2형) → 변형 초안 2~3개 + 체크리스트 검증 |

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

/rp-post                       # 방금 끝낸 작업을 글 초안으로
/rp-post docs/retro.md         # 특정 문서를 소재로
/rp-post 사이드프로젝트 첫 배포 후기   # 텍스트를 소재로
```

생성 문서는 **환경별로 지정한 GitHub 레포**에 적재할 수 있다. 최초 실행 시 대상 레포를 한 번 물어보고, 알려주면 프로젝트 루트 `.rp-deck.json`(`{"repo":"owner/name"}`)에 저장돼 이후 자동으로 그 레포에 push된다. 등록하지 않으면 로컬(`docs/decks`)에만 생성된다.

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
        │   │   ├── template.html     # 디자인·컴포넌트 SSOT
        │   │   ├── design-rules.md   # 구조·전달력·토스 톤 규칙
        │   │   └── review.md         # 독립 에이전트 병렬 리뷰 프로토콜
        │   └── scripts/update_index.py  # 인덱스 생성 (stdlib only)
        └── rp-post/
            ├── SKILL.md              # 스킬 정의
            └── reference/
                ├── patterns.md       # 실측 통계 SSOT + 데이터 갱신 절차
                ├── archetypes.md     # 아키타입 공식 (바이럴 A1~A6 · 사내 K1~K3)
                ├── checklist.md      # 초안 검증 (바이럴용·사내용 각 7항목)
                ├── platforms.md      # 플랫폼 프로파일·변환 규칙
                └── review.md         # 독립 에이전트 병렬 리뷰 프로토콜
```
