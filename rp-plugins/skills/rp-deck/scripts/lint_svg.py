#!/usr/bin/env python3
"""덱 HTML의 인라인 SVG 좌표 린트 (stdlib only).

인라인 SVG는 레이아웃 엔진이 없어 좌표가 어긋나도 렌더 오류가 나지 않는다.
눈으로 놓치는 세 가지를 기계로 잡는다.

  OVERLAP  인접 text의 baseline 간격이 글자 크기보다 좁고 가로로 겹침
  CLIP     요소가 viewBox 밖 (SVG 루트는 overflow:hidden이라 잘림)
  INDENT   반복 행 블록(막대 트랙 등)이 x=0이 아닌 곳에서 시작 — 헤드라인과 어긋남

사용:
  python3 lint_svg.py <파일 또는 디렉터리> [...]
종료 코드: 지적 있으면 1, 없으면 0
"""
import re
import sys
import pathlib
from collections import defaultdict

SVG_RE = re.compile(r'<svg[^>]*viewBox="0 0 ([\d.]+) ([\d.]+)"(.*?)</svg>', re.S)
EL_RE = re.compile(r"<(text|rect)\b([^>]*)>")
TAG_RE = re.compile(r"<[^>]+>")

INDENT_TOLERANCE = 24  # 이 값 이하로 시작하면 좌단에 붙은 것으로 본다
MIN_REPEATED_ROWS = 3  # 반복 행으로 인정할 최소 개수


def attr(s, name, default=None):
    m = re.search(r'\b%s="(-?[\d.]+)"' % re.escape(name), s)
    return float(m.group(1)) if m else default


def text_width(s, fs):
    """한글은 약 1em, 라틴·숫자는 약 0.5em으로 어림한다."""
    return sum(fs * (0.95 if ord(c) > 0x1100 else 0.5) for c in s)


def parse_svg(body):
    texts, rects = [], []
    for m in EL_RE.finditer(body):
        tag, a = m.group(1), m.group(2)
        if tag == "rect":
            x, y = attr(a, "x"), attr(a, "y")
            w, h = attr(a, "width"), attr(a, "height")
            if None not in (x, y, w, h):
                rects.append({"x": x, "y": y, "w": w, "h": h})
            continue
        x, y = attr(a, "x"), attr(a, "y")
        if x is None or y is None:
            continue
        fs = attr(a, "font-size", 14)
        anchor_m = re.search(r'text-anchor="(\w+)"', a)
        anchor = anchor_m.group(1) if anchor_m else "start"
        end = body.find("</text>", m.end())
        raw = TAG_RE.sub("", body[m.end():end]) if end != -1 else ""
        w = text_width(raw, fs)
        x0 = x if anchor == "start" else (x - w / 2 if anchor == "middle" else x - w)
        texts.append({"x": x0, "y": y, "fs": fs, "w": w, "s": raw.strip()[:24]})
    return texts, rects


def check(vw, vh, texts, rects):
    found = []

    ordered = sorted(texts, key=lambda t: t["y"])
    for a, b in zip(ordered, ordered[1:]):
        gap = b["y"] - a["y"]
        h_overlap = not (a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"])
        if gap < max(a["fs"], b["fs"]) and h_overlap:
            found.append(
                ("OVERLAP", "y=%g «%s» ↔ y=%g «%s» 간격 %g < 글자 %g"
                 % (a["y"], a["s"], b["y"], b["s"], gap, max(a["fs"], b["fs"])))
            )

    for t in texts:
        if t["y"] + t["fs"] * 0.25 > vh or t["x"] + t["w"] > vw + 1:
            found.append(("CLIP", "text «%s» x=%g y=%g (viewBox %gx%g)" % (t["s"], t["x"], t["y"], vw, vh)))
    for r in rects:
        if r["y"] + r["h"] > vh + 1 or r["x"] + r["w"] > vw + 1:
            found.append(("CLIP", "rect x=%g y=%g %gx%g (viewBox %gx%g)" % (r["x"], r["y"], r["w"], r["h"], vw, vh)))

    # 반복 행 블록(막대 트랙·리스트) 옆에 빈 왼쪽 여백이 남았는지.
    # 그 행들이 걸친 y 구간에서 가장 왼쪽 요소마저 안쪽에 있으면 블록 전체가 들여쓰기된 것이다.
    spans = [(t["y"] - t["fs"], t["y"], t["x"]) for t in texts]
    spans += [(r["y"], r["y"] + r["h"], r["x"]) for r in rects]

    groups = defaultdict(list)
    for r in rects:
        groups[(r["x"], r["w"], r["h"])].append(r["y"])
    for (x, w, h), ys in sorted(groups.items()):
        if len(set(ys)) < MIN_REPEATED_ROWS or x <= INDENT_TOLERANCE:
            continue
        top, bottom = min(ys), max(ys) + h
        gutter = min(sx for sy0, sy1, sx in spans if sy1 >= top and sy0 <= bottom)
        if gutter > INDENT_TOLERANCE * 2.5:
            found.append(
                ("INDENT", "반복 행 %d개(x=%g, 폭 %g)의 y %g~%g 구간에서 가장 왼쪽 요소가 x=%g "
                           "— 왼쪽 여백이 비어 헤드라인 좌단과 어긋난다"
                 % (len(set(ys)), x, w, top, bottom, gutter))
            )
    return found


def scan(path):
    html = path.read_text(encoding="utf-8")
    results = []
    for i, m in enumerate(SVG_RE.finditer(html), 1):
        vw, vh = float(m.group(1)), float(m.group(2))
        line = html[: m.start()].count("\n") + 1
        texts, rects = parse_svg(m.group(3))
        for kind, msg in check(vw, vh, texts, rects):
            results.append((i, line, kind, msg))
    return results


def main(argv):
    targets = []
    for a in argv:
        p = pathlib.Path(a)
        targets.extend(sorted(p.rglob("*.html")) if p.is_dir() else [p])

    total = 0
    for p in targets:
        if p.name == "index.html":
            continue
        rows = scan(p)
        if rows:
            print("\n== %s" % p)
            for i, line, kind, msg in rows:
                print("  [%s] svg#%d (~L%d) %s" % (kind, i, line, msg))
            total += len(rows)

    print("\n검사 %d개 파일 · 지적 %d건" % (len(targets), total))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
