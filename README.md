# harness-agent-extensions

Ryan-papa 하네스용 Claude Code 플러그인·스킬 모음.

## 플러그인

### rp-plugins

`rp-*` 스킬 모음.

현재 버전 `0.1.0` ([CHANGELOG](CHANGELOG.md)).

| 스킬 | 역할 |
|------|------|
| `rp-deck` | 작업 산출물·문서·주제를 토스 스타일 HTML 슬라이드 장표로 변환. `docs/decks/` 4레벨 자동 분류 + index.html 갱신 |

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
```

## 구조

```
harness-agent-extensions/
├── .claude-plugin/marketplace.json   # 마켓플레이스 선언
└── rp-plugins/
    ├── .claude-plugin/plugin.json
    └── skills/rp-deck/
        ├── SKILL.md                  # 스킬 정의
        ├── reference/
        │   ├── template.html         # 디자인·컴포넌트 SSOT
        │   └── design-rules.md       # 구조·전달력·토스 톤 규칙
        └── scripts/update_index.py   # 인덱스 생성 (stdlib only)
```
