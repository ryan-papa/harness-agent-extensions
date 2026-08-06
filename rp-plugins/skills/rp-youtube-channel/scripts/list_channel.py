#!/usr/bin/env python3
"""유튜브 채널의 공개 영상을 최신순으로 훑어, 장표로 만들 수 있는 후보만 추린다.

목록 조회는 ID·제목만 주므로, 이미 처리했거나 제외된 영상을 건너뛰고 남은 것만
앞에서부터 개별 조회(프로브)해 --limit 개를 채우면 멈춘다.

상태는 대상 루트(장표 레포)에 둔다. 로컬에만 두면 기기·캐시 초기화로 유실된다.
  <root>/.rp-youtube/salt                   장표 메타용 해시 솔트 (레포 밖으로 나가지 않음)
  <root>/.rp-youtube/registry.json          채널 별칭 등록부
  <root>/.rp-youtube/channels/<slug>.json   채널별 제외·보류 기록
  <root>/**/*.html 의 deck-source-ref       이미 장표로 만든 영상 (솔트 해시, 역산 불가)

사용:
    python3 list_channel.py <채널> --root <대상루트> [--limit 10] [--out DIR] [--json]
    python3 list_channel.py --root <대상루트> --list
    python3 list_channel.py --root <대상루트> --ref <영상ID>

종료 코드:
    0  후보를 하나 이상 찾음
    2  후보 없음 (전부 처리·제외됨)
    3  채널을 해석하지 못함
    4  yt-dlp 설치 실패
"""

import argparse
import hashlib
import json
import re
import secrets
import subprocess
import sys
import time
import venv
from datetime import datetime, timezone
from pathlib import Path

VENV_DIR = Path.home() / ".rp-youtube" / "venv"
CLIENTS = ["ios", "android", "tv", "web"]

# 장표로 만들 수 없는 상태. 다시 프로브해도 결과가 같으므로 영구 제외한다.
GATED = {
    "subscriber_only": "멤버십 전용",
    "premium_only": "Premium 전용",
    "needs_auth": "로그인 필요",
    "private": "비공개",
}
# 나중에 자막이 생길 수 있으므로 보류로 두고, --retry-deferred 로 되살린다.
DEFER_NO_SUBS = "자막 없음"
# 연속으로 이만큼 조회에 실패하면 레이트리밋으로 보고 멈춘다. 일시적 실패를
# 상태로 굳히면 멀쩡한 영상이 영영 후보에서 빠진다.
ERROR_STREAK_STOP = 3

# 기존 영상을 이어 붙인 모음편은 개별 영상과 내용이 겹친다. 채널마다 표기가
# 다르므로 기본값일 뿐이고, registry.json 의 exclude_title 로 덮어쓴다.
DEFAULT_EXCLUDE_TITLE = r"연속재생|몰아보기|모아보기|다시보기|풀영상|풀버전|compilation|marathon"
SHORT_MAX_SEC = 90


def log(msg):
    print(msg, file=sys.stderr)


def ensure_ytdlp():
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
    r = subprocess.run([str(VENV_DIR / "bin" / "pip"), "install", "-q", "--upgrade", "yt-dlp"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not exe.exists():
        log("yt-dlp 설치 실패:\n" + r.stderr[-1200:])
        sys.exit(4)
    return str(exe)


def ytdlp(exe, url, extra, client=None, timeout=300):
    cmd = [exe, "--skip-download", "--no-warnings", "--ignore-no-formats-error"]
    if client:
        cmd += ["--extractor-args", f"youtube:player_client={client};lang=ko"]
    cmd += extra + [url]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


# ── 상태 파일 ────────────────────────────────────────────────────────────────

def state_dir(root):
    return Path(root) / ".rp-youtube"


def load_salt(root):
    """장표 메타용 솔트. 없으면 만든다.

    장표 HTML은 공개 사이트로 나가지만 이 솔트는 레포 안에만 있다. 솔트 없이
    해시만 쓰면 채널을 짐작한 사람이 그 채널 영상 ID를 전부 해시해 맞춰볼 수
    있으므로, 솔트로 그 경로를 막는다.
    ⛔ 솔트가 바뀌면 기존 장표의 해시와 대조되지 않아 전부 미처리로 보인다.
    """
    p = state_dir(root) / "salt"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    p.parent.mkdir(parents=True, exist_ok=True)
    salt = secrets.token_hex(16)
    p.write_text(salt + "\n", encoding="utf-8")
    log(f"해시 솔트를 새로 만들었습니다: {p} (⛔ 잃어버리면 기존 장표와 대조가 끊깁니다)")
    return salt


def source_ref(salt, video_id):
    """장표 `deck-source-ref`에 넣을 값. 영상 ID가 HTML에 그대로 드러나지 않게 한다."""
    return hashlib.sha256(f"{salt}:{video_id}".encode()).hexdigest()[:16]


def load_registry(root):
    p = state_dir(root) / "registry.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"channels": {}}


def save_registry(root, reg):
    p = state_dir(root) / "registry.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_channel_state(root, slug):
    p = state_dir(root) / "channels" / f"{slug}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"excluded": {}, "deferred": {}}


def save_channel_state(root, slug, st):
    p = state_dir(root) / "channels" / f"{slug}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def published_refs(root):
    """장표 HTML의 deck-source-ref 메타를 훑어 이미 만든 영상의 해시를 모은다."""
    done = {}
    pat = re.compile(r'name="deck-source-ref"\s+content="([0-9a-f]{8,64})"')
    title_pat = re.compile(r'name="deck-title"\s+content="([^"]*)"')
    for f in Path(root).rglob("*.html"):
        if f.name == "index.html" or ".rp-youtube" in f.parts:
            continue
        try:
            head = f.read_text(encoding="utf-8", errors="ignore")[:4000]
        except OSError:
            continue
        m = pat.search(head)
        if m:
            t = title_pat.search(head)
            done[m.group(1)] = t.group(1) if t else f.stem
    return done


# ── 채널 해석 ────────────────────────────────────────────────────────────────

def resolve_channel(exe, spec, reg):
    """(slug, videos_url, label) 반환. 별칭·핸들·채널URL·영상URL을 모두 받는다."""
    spec = spec.strip()

    # 1) 등록된 별칭·슬러그
    for slug, info in reg.get("channels", {}).items():
        if spec in (slug, info.get("alias"), info.get("handle")):
            return slug, info["videos_url"], info.get("alias") or slug

    # 2) 핸들
    if spec.startswith("@"):
        h = spec[1:]
        return h, f"https://www.youtube.com/@{h}/videos", spec

    m = re.search(r"youtube\.com/@([A-Za-z0-9._-]+)", spec)
    if m:
        return m.group(1), f"https://www.youtube.com/@{m.group(1)}/videos", "@" + m.group(1)

    # 3) 채널 URL
    m = re.search(r"youtube\.com/channel/(UC[A-Za-z0-9_-]{20,})", spec)
    if m:
        return m.group(1), f"https://www.youtube.com/channel/{m.group(1)}/videos", m.group(1)

    # 4) 영상 URL — 그 영상의 업로더로 역산
    if re.search(r"youtu\.be/|youtube\.com/watch", spec):
        for client in CLIENTS:
            r = ytdlp(exe, spec, ["--dump-single-json"], client)
            if r.returncode == 0 and r.stdout.strip():
                d = json.loads(r.stdout)
                url = d.get("uploader_url") or d.get("channel_url") or ""
                hm = re.search(r"@([A-Za-z0-9._-]+)", url)
                if hm:
                    return hm.group(1), f"https://www.youtube.com/@{hm.group(1)}/videos", "@" + hm.group(1)
                cid = d.get("channel_id")
                if cid:
                    return cid, f"https://www.youtube.com/channel/{cid}/videos", cid
        log("영상에서 채널을 역산하지 못했습니다.")
        sys.exit(3)

    known = ", ".join(sorted(reg.get("channels", {}))) or "(등록된 채널 없음)"
    log(f"채널을 해석하지 못했습니다: {spec}")
    log(f"핸들(@name)·채널 URL·영상 URL 또는 등록된 별칭을 주세요. 등록됨: {known}")
    sys.exit(3)


def list_videos(exe, videos_url):
    """videos 탭을 최신순으로 훑는다. 쇼츠는 별도 탭이라 여기 포함되지 않는다."""
    for client in CLIENTS:
        r = ytdlp(exe, videos_url, ["--flat-playlist", "--print", "%(id)s\t%(title)s"], client)
        if r.returncode == 0 and r.stdout.strip():
            out = []
            for line in r.stdout.splitlines():
                if "\t" in line:
                    vid, title = line.split("\t", 1)
                    if len(vid) == 11:
                        out.append((vid, title))
            if out:
                return out
    log(f"채널 목록을 가져오지 못했습니다: {videos_url}")
    sys.exit(3)


def probe(exe, vid):
    """(status, info) 반환. status는 ok / gated:<사유> / no_subs / error."""
    url = f"https://www.youtube.com/watch?v={vid}"
    meta = None
    for client in CLIENTS:
        r = ytdlp(exe, url, ["--dump-single-json"], client, timeout=180)
        if r.returncode == 0 and r.stdout.strip():
            meta = json.loads(r.stdout)
            break
    if meta is None:
        return "error", {}

    gate = GATED.get(meta.get("availability"))
    if gate:
        return f"gated:{gate}", {"title": meta.get("title")}

    manual = {k: v for k, v in (meta.get("subtitles") or {}).items() if k != "live_chat"}
    auto = meta.get("automatic_captions") or {}
    lang = None
    if manual:
        lang = sorted(manual)[0]
    elif auto:
        lang = next((k for k in auto if k.endswith("-orig")), None) or \
               next((k for k in ("ko", "en") if k in auto), None) or sorted(auto)[0]

    info = {
        "title": meta.get("title"),
        "upload_date": meta.get("upload_date"),
        "duration": meta.get("duration"),
        "view_count": meta.get("view_count"),
        "subtitle_kind": "manual" if manual else ("auto" if auto else None),
        "subtitle_lang": lang,
        "url": meta.get("webpage_url", url),
    }
    if not lang:
        return "no_subs", info
    return "ok", info


def hhmm(sec):
    if not sec:
        return "-"
    return f"{sec // 60}:{sec % 60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("channel", nargs="?", help="핸들(@name)·채널 URL·영상 URL·등록 별칭")
    ap.add_argument("--root", required=True, help="상태·장표가 있는 대상 루트")
    ap.add_argument("--limit", type=int, default=10, help="찾을 후보 개수 (기본 10)")
    ap.add_argument("--out", default=".", help="후보 JSON을 쓸 디렉터리")
    ap.add_argument("--alias", help="이 채널을 이 이름으로 등록")
    ap.add_argument("--list", action="store_true", help="등록된 채널만 출력")
    ap.add_argument("--ref", metavar="VIDEO_ID", help="장표에 넣을 deck-source-ref 해시만 출력")
    ap.add_argument("--retry-deferred", action="store_true", help="보류(자막 없음)도 다시 프로브")
    ap.add_argument("--max-probe", type=int, default=60, help="한 실행의 프로브 상한")
    ap.add_argument("--sleep", type=float, default=1.0, help="프로브 사이 대기 초 (레이트리밋 완화)")
    ap.add_argument("--json", action="store_true", help="결과를 stdout에 JSON으로")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        log(f"대상 루트가 없습니다: {root}")
        sys.exit(3)
    reg = load_registry(root)

    if args.ref:
        print(source_ref(load_salt(root), args.ref))
        return

    if args.list:
        chans = reg.get("channels", {})
        if not chans:
            print("등록된 채널이 없습니다.")
        for slug, info in sorted(chans.items()):
            print(f"{info.get('alias') or slug}\t{info.get('handle') or slug}\t{info.get('videos_url')}")
        return

    if not args.channel:
        ap.error("채널을 지정하거나 --list 를 쓰세요")

    exe = ensure_ytdlp()
    slug, videos_url, label = resolve_channel(exe, args.channel, reg)

    entry = reg.setdefault("channels", {}).setdefault(slug, {})
    entry["videos_url"] = videos_url
    if args.alias:
        entry["alias"] = args.alias
    entry.setdefault("handle", label if label.startswith("@") else None)
    entry.setdefault("exclude_title", DEFAULT_EXCLUDE_TITLE)
    label = entry.get("alias") or label

    st = load_channel_state(root, slug)
    excluded, deferred = st.setdefault("excluded", {}), st.setdefault("deferred", {})
    if args.retry_deferred:
        deferred.clear()

    salt = load_salt(root)
    done = published_refs(root)
    title_re = re.compile(entry["exclude_title"], re.I) if entry.get("exclude_title") else None

    videos = list_videos(exe, videos_url)
    log(f"{label}: 목록 {len(videos)}개 · 완료 {sum(1 for v, _ in videos if source_ref(salt, v) in done)} · "
        f"제외 {len(excluded)} · 보류 {len(deferred)}")

    candidates, probes, skipped_title = [], 0, 0
    errors, streak, throttled = 0, 0, False
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for vid, title in videos:
        if len(candidates) >= args.limit or probes >= args.max_probe:
            break
        if source_ref(salt, vid) in done or vid in excluded or vid in deferred:
            continue
        if title_re and title_re.search(title):
            skipped_title += 1
            continue

        if probes and args.sleep:
            time.sleep(args.sleep)
        probes += 1
        status, info = probe(exe, vid)

        if status == "error":
            # ⛔ 상태로 기록하지 않는다. 레이트리밋·일시 장애로 실패한 영상을
            # 영구 보류로 굳히면 다음 실행에서도 영영 후보에 오르지 않는다.
            errors += 1
            streak += 1
            if streak >= ERROR_STREAK_STOP:
                throttled = True
                log(f"조회가 {streak}건 연속 실패했습니다. 레이트리밋으로 보고 중단합니다.")
                break
            continue
        streak = 0

        if status.startswith("gated:"):
            excluded[vid] = {"reason": status.split(":", 1)[1], "title": title, "at": now}
            continue
        if status == "no_subs":
            deferred[vid] = {"reason": DEFER_NO_SUBS, "title": title, "at": now}
            continue
        if (info.get("duration") or 0) <= SHORT_MAX_SEC:
            excluded[vid] = {"reason": "쇼츠(90초 이하)", "title": title, "at": now}
            continue
        candidates.append({"id": vid, "source_ref": source_ref(salt, vid), **info})

    st["last_listed"] = now
    st["video_count"] = len(videos)
    save_channel_state(root, slug, st)
    save_registry(root, reg)

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}-candidates.json"
    payload = {
        "channel": slug,
        "alias": entry.get("alias"),
        "videos_url": videos_url,
        "listed_at": now,
        "total": len(videos),
        "done": len(done),
        "excluded": len(excluded),
        "deferred": len(deferred),
        "probed": probes,
        "probe_errors": errors,
        "throttled": throttled,
        "candidates": candidates,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"## {label} — 후보 {len(candidates)}건 "
              f"(전체 {len(videos)} · 완료 {len(done)} · 제외 {len(excluded)} · 보류 {len(deferred)})")
        print()
        print("| # | 제목 | 공개일 | 길이 | 자막 | 링크 |")
        print("|--:|------|--------|------|------|------|")
        for i, c in enumerate(candidates, 1):
            d = c.get("upload_date") or ""
            d = f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 else "-"
            print(f"| {i} | {c['title'].replace('|', '｜')} | {d} | {hhmm(c.get('duration'))} | "
                  f"{c.get('subtitle_kind')}/{c.get('subtitle_lang')} | https://youtu.be/{c['id']} |")
        print()
        note = f"프로브 {probes}건"
        if skipped_title:
            note += f" · 제목 규칙으로 건너뜀 {skipped_title}건"
        if errors:
            note += f" · 조회 실패 {errors}건(기록하지 않음)"
        if throttled:
            note += " · 레이트리밋으로 중단 — 잠시 뒤 다시 실행하세요"
        print(note)
        print(f"후보 JSON: {out_path}")

    sys.exit(0 if candidates else 2)


if __name__ == "__main__":
    main()
