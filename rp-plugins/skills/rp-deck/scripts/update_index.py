#!/usr/bin/env python3
"""docs/decks/ 트리를 스캔해 토스 스타일 index.html을 생성·갱신한다.

의존성 없음(표준 라이브러리만). 사용법:
    python3 update_index.py <decks_root>
각 덱 HTML의 <meta name="deck-*"> 태그(title/date/category/summary)를 파싱한다.
분류는 실제 폴더 경로(decks_root 기준 상대 경로)로 그룹핑한다.
"""
import html
import os
import re
import sys

META_RE = {k: re.compile(r'<meta\s+name="deck-%s"\s+content="([^"]*)"' % k, re.I)
           for k in ("title", "date", "category", "summary")}
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)


def parse_deck(path):
    try:
        head = open(path, encoding="utf-8").read(8192)
    except OSError:
        return None
    meta = {k: (r.search(head).group(1).strip() if r.search(head) else "") for k, r in META_RE.items()}
    if not meta["title"]:
        m = TITLE_RE.search(head)
        meta["title"] = m.group(1).strip() if m else os.path.basename(path)
    return meta


def collect(root):
    decks = []
    for dirpath, _, files in os.walk(root):
        for f in sorted(files):
            if not f.endswith(".html") or f == "index.html":
                continue
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, root)
            cat = os.path.dirname(rel).replace(os.sep, " / ") or "미분류"
            meta = parse_deck(full)
            if meta is None:
                continue
            decks.append({"href": rel.replace(os.sep, "/"), "cat": cat, **meta})
    # 날짜 내림차순, 없으면 제목
    decks.sort(key=lambda d: (d["date"], d["title"]), reverse=True)
    return decks


def group_by_cat(decks):
    groups = {}
    for d in decks:
        groups.setdefault(d["cat"], []).append(d)
    return dict(sorted(groups.items()))


def render(decks):
    e = html.escape
    total = len(decks)
    groups = group_by_cat(decks)
    cards = []
    for cat, items in groups.items():
        rows = "".join(
            '<a class="deck" href="{href}">'
            '<div class="dt">{title}</div>'
            '<div class="ds">{summary}</div>'
            '<div class="dm">{date}</div></a>'.format(
                href=e(d["href"]), title=e(d["title"]),
                summary=e(d["summary"] or ""), date=e(d["date"] or ""))
            for d in items)
        cards.append(
            '<section class="group"><h2 class="cat">{cat}'
            '<span class="cnt">{n}</span></h2><div class="grid">{rows}</div></section>'.format(
                cat=e(cat), n=len(items), rows=rows))
    body = "".join(cards) or '<p class="empty">아직 만든 장표가 없어요.</p>'
    return TEMPLATE.replace("{{TOTAL}}", str(total)).replace("{{BODY}}", body)


TEMPLATE = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>장표 모음 · rp-deck</title>
<link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
:root{--blue:#3182F6;--g50:#F9FAFB;--g100:#F2F4F6;--g200:#E5E8EB;--g500:#8B95A1;--g600:#6B7684;--g700:#4E5968;--g900:#191F28;
--font:"Pretendard",-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--font);background:var(--g50);color:var(--g900);letter-spacing:-.01em;
-webkit-font-smoothing:antialiased;padding:64px 24px 96px}
.wrap{max-width:1080px;margin:0 auto}
.head{margin-bottom:48px}
.eyebrow{font-size:16px;font-weight:700;color:var(--blue)}
h1{font-size:40px;font-weight:700;margin-top:12px}
.sub{font-size:17px;color:var(--g600);margin-top:12px}
.group{margin-top:44px}
.cat{font-size:15px;font-weight:700;color:var(--g600);display:flex;align-items:center;gap:10px;
padding-bottom:14px;border-bottom:1px solid var(--g200);margin-bottom:20px}
.cnt{background:var(--g100);color:var(--g500);font-size:13px;padding:2px 10px;border-radius:9999px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.deck{display:block;background:#fff;border:1px solid var(--g200);border-radius:16px;padding:24px;
text-decoration:none;color:inherit;transition:transform .15s ease,box-shadow .15s ease}
.deck:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.08);border-color:var(--blue)}
.dt{font-size:19px;font-weight:700;line-height:1.4;word-break:keep-all}
.ds{font-size:15px;color:var(--g700);line-height:1.5;margin-top:8px;word-break:keep-all}
.dm{font-size:13px;color:var(--g500);margin-top:16px;font-weight:600}
.empty{color:var(--g500);font-size:17px;margin-top:40px}
</style></head><body><div class="wrap">
<div class="head"><div class="eyebrow">rp-deck</div><h1>장표 모음</h1>
<p class="sub">총 {{TOTAL}}개의 장표가 있어요.</p></div>
{{BODY}}
</div></body></html>
"""


def main():
    if len(sys.argv) != 2:
        print("usage: update_index.py <decks_root>", file=sys.stderr)
        sys.exit(1)
    root = sys.argv[1]
    os.makedirs(root, exist_ok=True)
    decks = collect(root)
    out = os.path.join(root, "index.html")
    open(out, "w", encoding="utf-8").write(render(decks))
    print("wrote %s (%d decks)" % (out, len(decks)))


if __name__ == "__main__":
    main()
