#!/usr/bin/env python3
"""YouTube 영상의 메타데이터와 자막을 받아 타임스탬프 전사본으로 만든다.

stdlib + yt-dlp(자동 설치)만 쓴다. 영상·오디오는 받지 않고 자막만 받는다.

사용:
    python3 fetch_transcript.py <URL> [--out DIR] [--langs ko,en] [--json]

종료 코드:
    0  성공
    2  자막 없음 (영상은 접근 가능)
    3  접근 불가 (멤버십 전용·비공개·삭제·연령 제한 등)
    4  yt-dlp 설치 실패
"""

import argparse
import json
import os
import re
import subprocess
import sys
import venv
from pathlib import Path

VENV_DIR = Path.home() / ".rp-youtube" / "venv"
# web/tv 클라이언트는 SABR 강제·"page needs to be reloaded"로 자주 실패한다.
CLIENTS = ["ios", "android", "tv", "web"]
GATED_AVAILABILITY = {
    "subscriber_only": "채널 멤버십 전용 영상",
    "premium_only": "YouTube Premium 전용 영상",
    "needs_auth": "로그인이 필요한 영상",
    "private": "비공개 영상",
}
BLOCKED_PATTERNS = [
    ("members", "멤버십 전용 영상"),
    ("Private video", "비공개 영상"),
    ("Video unavailable", "영상 이용 불가"),
    ("has been removed", "삭제된 영상"),
    ("age", "연령 제한 영상"),
    ("Sign in to confirm", "로그인 요구 (봇 차단 또는 연령 제한)"),
]


def log(msg):
    print(msg, file=sys.stderr)


def ensure_ytdlp():
    """PATH의 yt-dlp를 쓰고, 없으면 ~/.rp-youtube/venv에 설치한다."""
    from shutil import which

    found = which("yt-dlp")
    if found:
        return found

    exe = VENV_DIR / "bin" / "yt-dlp"
    if exe.exists():
        return str(exe)

    log(f"yt-dlp가 없어 {VENV_DIR}에 설치합니다...")
    VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
    venv.create(VENV_DIR, with_pip=True)
    pip = VENV_DIR / "bin" / "pip"
    r = subprocess.run([str(pip), "install", "-q", "--upgrade", "yt-dlp"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not exe.exists():
        log("yt-dlp 설치 실패:\n" + r.stderr[-1500:])
        sys.exit(4)
    return str(exe)


def video_id(url):
    for pat in (r"[?&]v=([A-Za-z0-9_-]{11})",
                r"youtu\.be/([A-Za-z0-9_-]{11})",
                r"/(?:shorts|live|embed)/([A-Za-z0-9_-]{11})"):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return re.sub(r"[^A-Za-z0-9_-]", "", url)[:11] or "video"


def run_ytdlp(exe, url, extra, client=None, timeout=180):
    cmd = [exe, "--skip-download", "--no-warnings", "--ignore-no-formats-error"]
    if client:
        cmd += ["--extractor-args", f"youtube:player_client={client}"]
    cmd += extra + [url]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def blocked_reason(stderr):
    for needle, label in BLOCKED_PATTERNS:
        if needle.lower() in stderr.lower():
            return label
    return None


def fetch_meta(exe, url):
    """클라이언트를 바꿔 가며 메타데이터(JSON)를 받는다. (client, meta) 반환."""
    last_err = ""
    for client in CLIENTS:
        r = run_ytdlp(exe, url, ["--dump-single-json"], client)
        if r.returncode == 0 and r.stdout.strip():
            return client, json.loads(r.stdout)
        last_err = r.stderr
        reason = blocked_reason(r.stderr)
        # 접근 자체가 막힌 경우는 클라이언트를 바꿔도 뚫리지 않는다. 다만
        # "Video unavailable"은 클라이언트 한정 오류일 수 있어 계속 시도한다.
        if reason and "멤버십" in reason:
            log(f"접근 불가: {reason}")
            log("⛔ 유료·비공개 콘텐츠는 우회하지 않습니다. 접근 권한이 있는 계정으로 직접 확인하세요.")
            sys.exit(3)
    reason = blocked_reason(last_err) or "알 수 없는 오류"
    log(f"메타데이터 조회 실패: {reason}\n{last_err[-1200:]}")
    sys.exit(3)


def pick_lang(meta, wanted):
    """(kind, lang) 반환. kind는 'manual' 또는 'auto'. 없으면 (None, None)."""
    manual = {k: v for k, v in (meta.get("subtitles") or {}).items() if k != "live_chat"}
    auto = meta.get("automatic_captions") or {}

    def match(table, langs):
        for want in langs:
            # 원어(`-orig`)를 정확히 같은 코드보다 먼저 본다. 번역본은 기계번역이라
            # 용어가 뭉개지고 사실이 왜곡된다.
            for key in (f"{want}-orig", want):
                if key in table:
                    return key
            for key in table:
                if key.startswith(f"{want}-"):
                    return key
        return None

    # 우선순위: 사용자 지정 → 영상 원어 → 한국어 → 영어
    order = list(wanted) or [x for x in [meta.get("language")] if x] + ["ko", "en"]
    orig = next((k for k in auto if k.endswith("-orig")), None)

    for table, kind in ((manual, "manual"), (auto, "auto")):
        hit = match(table, order)
        if hit:
            return kind, hit
    if manual:
        return "manual", sorted(manual)[0]
    if orig:
        return "auto", orig
    if auto:
        return "auto", sorted(auto)[0]
    return None, None


def download_subs(exe, url, client, kind, lang, stem):
    flag = "--write-subs" if kind == "manual" else "--write-auto-subs"
    r = run_ytdlp(exe, url, [
        flag, "--sub-langs", lang, "--sub-format", "json3/vtt/best",
        "-o", f"{stem}.%(ext)s",
    ], client, timeout=300)
    hits = sorted(Path(stem).parent.glob(f"{Path(stem).name}.{lang}.*"))
    if not hits:
        log(f"자막 다운로드 실패:\n{r.stderr[-1200:]}")
        return None
    return hits[0]


def parse_json3(path, chunk_chars):
    events = json.loads(Path(path).read_text(encoding="utf-8")).get("events", [])
    lines = []
    for ev in events:
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text or (lines and lines[-1][1] == text):
            continue
        lines.append((ev.get("tStartMs", 0), text))

    blocks, buf, start = [], [], lines[0][0] if lines else 0
    for ms, text in lines:
        buf.append(text)
        if len(" ".join(buf)) > chunk_chars:
            blocks.append((start, " ".join(buf)))
            buf, start = [], ms
    if buf:
        blocks.append((start, " ".join(buf)))
    return blocks


def parse_vtt(path, chunk_chars):
    raw = Path(path).read_text(encoding="utf-8").splitlines()
    lines, cur_ms = [], 0
    for line in raw:
        m = re.match(r"(\d+):(\d+):(\d+)\.(\d+)\s+-->", line)
        if m:
            h, mi, s, _ = map(int, m.groups())
            cur_ms = (h * 3600 + mi * 60 + s) * 1000
            continue
        text = re.sub(r"<[^>]+>", "", line).strip()
        if not text or text.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        if lines and lines[-1][1] == text:
            continue
        lines.append((cur_ms, text))

    blocks, buf, start = [], [], lines[0][0] if lines else 0
    for ms, text in lines:
        buf.append(text)
        if len(" ".join(buf)) > chunk_chars:
            blocks.append((start, " ".join(buf)))
            buf, start = [], ms
    if buf:
        blocks.append((start, " ".join(buf)))
    return blocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default=".", help="산출물 디렉터리")
    ap.add_argument("--langs", default="", help="선호 언어 (쉼표 구분, 예: ko,en)")
    ap.add_argument("--chunk", type=int, default=300, help="블록당 목표 글자 수")
    ap.add_argument("--json", action="store_true", help="결과 경로를 JSON으로 출력")
    args = ap.parse_args()

    exe = ensure_ytdlp()
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    vid = video_id(args.url)

    client, meta = fetch_meta(exe, args.url)

    gate = GATED_AVAILABILITY.get(meta.get("availability"))
    if gate:
        log(f"접근 불가: {gate} — 「{meta.get('title')}」")
        log("⛔ 유료·비공개 콘텐츠는 우회하지 않습니다. 권한이 있는 계정으로 직접 보거나 다른 영상을 지정하세요.")
        sys.exit(3)

    info = {
        "id": meta.get("id", vid),
        "title": meta.get("title"),
        "channel": meta.get("channel") or meta.get("uploader"),
        "upload_date": meta.get("upload_date"),
        "duration_sec": meta.get("duration"),
        "view_count": meta.get("view_count"),
        "webpage_url": meta.get("webpage_url", args.url),
        "description": meta.get("description", ""),
        "chapters": [{"start": c.get("start_time"), "title": c.get("title")}
                     for c in (meta.get("chapters") or [])],
        "client": client,
    }
    meta_path = out / f"{vid}.meta.json"
    meta_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    wanted = [x.strip() for x in args.langs.split(",") if x.strip()]
    kind, lang = pick_lang(meta, wanted)
    if not lang:
        log("자막이 없습니다. 이 영상은 전사본을 만들 수 없습니다.")
        print(json.dumps({"meta": str(meta_path), "transcript": None}, ensure_ascii=False))
        sys.exit(2)

    sub_path = download_subs(exe, args.url, client, kind, lang, str(out / vid))
    if not sub_path:
        sys.exit(2)

    blocks = (parse_json3 if sub_path.suffix == ".json3" else parse_vtt)(sub_path, args.chunk)
    tr_path = out / f"{vid}.transcript.txt"
    with tr_path.open("w", encoding="utf-8") as f:
        f.write(f"# {info['title']}\n")
        f.write(f"# {info['channel']} · {info['upload_date']} · "
                f"{(info['duration_sec'] or 0)//60}분 {(info['duration_sec'] or 0)%60}초\n")
        f.write(f"# {info['webpage_url']}\n")
        f.write(f"# 자막: {kind}/{lang} (auto면 STT 오인식 있음 — 정규화 필요)\n\n")
        for ms, text in blocks:
            s = ms // 1000
            f.write(f"[{s//60:02d}:{s%60:02d}] {text}\n")

    result = {
        "meta": str(meta_path), "transcript": str(tr_path),
        "subtitle_kind": kind, "subtitle_lang": lang,
        "blocks": len(blocks), "client": client,
        "title": info["title"], "channel": info["channel"],
        "duration_sec": info["duration_sec"],
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        log(f"제목: {info['title']}")
        log(f"채널: {info['channel']} · {info['upload_date']} · {info['duration_sec']}초")
        log(f"자막: {kind}/{lang} · {len(blocks)}블록")
        print(tr_path)


if __name__ == "__main__":
    main()
