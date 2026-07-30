#!/usr/bin/env python3
"""decks_root에서 덱을 삭제하고 index.html을 다시 만든다.

의존성 없음(표준 라이브러리만). 사용법:
    python3 delete_deck.py <decks_root> <대상...> [--yes]

대상은 세 가지를 모두 받는다 — 라이브 URL(퍼센트 인코딩 자동 해제) · decks_root 기준
상대 경로 · 제목/경로 키워드. 기본은 목록만 뽑고(dry-run), `--yes`가 붙을 때만 지운다.
키워드가 여러 덱에 걸리거나 하나도 안 걸리면 **아무것도 지우지 않고** 종료 코드 2로 끝낸다
(후보를 사용자에게 보여주고 다시 부르라는 뜻).

삭제 후 빈 디렉터리를 정리하고 update_index.py의 스캔·렌더로 index.html을 재생성한다.
"""
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from update_index import collect, render  # noqa: E402


def to_rel(target, root):
    """URL·절대경로·상대경로를 decks_root 기준 상대 경로로 정규화한다."""
    t = target.split("#")[0].split("?")[0].strip()
    t = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://[^/]+/", "", t)
    t = urllib.parse.unquote(t)
    if os.path.isabs(t):
        t = os.path.relpath(t, os.path.abspath(root))
    return t.lstrip("/")


def resolve(target, decks, root):
    """(확정 덱, 후보 목록) — 경로가 정확히 맞으면 확정, 키워드면 유일할 때만 확정."""
    rel = to_rel(target, root)
    exact = [d for d in decks if d["href"] == rel]
    if exact:
        return exact[0], []
    key = urllib.parse.unquote(target.split("#")[0]).strip().lower()
    hits = [d for d in decks if key and (key in d["title"].lower() or key in d["href"].lower())]
    if len(hits) == 1:
        return hits[0], []
    return None, hits


def prune(path, root):
    """비게 된 상위 디렉터리를 루트 전까지 정리한다."""
    root = os.path.abspath(root)
    d = os.path.dirname(os.path.abspath(path))
    while d != root and os.path.isdir(d) and not os.listdir(d):
        os.rmdir(d)
        d = os.path.dirname(d)


def main():
    args = [a for a in sys.argv[1:] if a != "--yes"]
    do_delete = "--yes" in sys.argv[1:]
    if len(args) < 2:
        print("usage: delete_deck.py <decks_root> <대상...> [--yes]", file=sys.stderr)
        sys.exit(1)
    root, targets = args[0], args[1:]
    decks = collect(root)

    plan, problems = [], []
    for t in targets:
        deck, cands = resolve(t, decks, root)
        if deck is None:
            problems.append((t, cands))
        elif deck not in plan:
            plan.append(deck)

    for d in plan:
        print("대상: %s\n      %s" % (d["title"], d["href"]))
    for t, cands in problems:
        if cands:
            print("모호함: %s — 후보 %d건" % (t, len(cands)))
            for c in cands:
                print("        %s  (%s)" % (c["title"], c["href"]))
        else:
            print("찾지 못함: %s" % t)
    if problems:
        print("→ 아무것도 지우지 않았다. 경로로 다시 지정할 것.", file=sys.stderr)
        sys.exit(2)
    if not do_delete:
        print("→ dry-run. 사용자 확인 후 --yes를 붙여 다시 실행할 것. (%d건)" % len(plan))
        return

    for d in plan:
        full = os.path.join(root, d["href"])
        os.remove(full)
        prune(full, root)
    left = collect(root)
    open(os.path.join(root, "index.html"), "w", encoding="utf-8").write(render(left))
    print("삭제 %d건 · index 갱신 (덱 %d → %d)" % (len(plan), len(decks), len(left)))


if __name__ == "__main__":
    main()
