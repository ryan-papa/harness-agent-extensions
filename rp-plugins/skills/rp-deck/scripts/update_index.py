#!/usr/bin/env python3
"""decks_root 트리를 스캔해 토스 스타일 게시판 index.html을 생성·갱신한다.

의존성 없음(표준 라이브러리만). 사용법:
    python3 update_index.py <decks_root>
각 덱 HTML의 <meta name="deck-*"> 태그(title/date/category/summary)를 파싱한다.
분류는 실제 폴더 경로(decks_root 기준 상대 경로)로 트리를 만든다.

레이아웃: 좌측 디렉토리 트리(전체 + 뎁스별 중첩) + 우측 게시판 리스트.
덱 데이터는 JSON으로 임베드하고, 트리·필터·검색은 클라이언트 JS가 렌더한다.
메타는 원본 그대로 임베드하되 <,>,& 등을 유니코드 이스케이프해 <script> 안전성을
확보하고, DOM 주입은 클라이언트 esc()로 이스케이프한다. (HTML 이스케이프해서
넣으면 data-path 왕복 시 엔티티 디코딩으로 디렉토리 필터가 깨진다.)
"""
import json
import os
import re
import sys

META_RE = {k: re.compile(r'<meta\s+name="deck-%s"\s+content="([^"]*)"' % k, re.I)
           for k in ("title", "date", "category", "summary")}
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)


def parse_deck(path):
    try:
        head = open(path, encoding="utf-8").read(8192)
    except (OSError, UnicodeDecodeError):
        return None  # 읽기 실패·비 UTF-8 파일은 건너뛴다 (1개가 전체 빌드를 막지 않도록)
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
            segs = [s for s in os.path.dirname(rel).split(os.sep) if s]
            meta = parse_deck(full)
            if meta is None:
                continue
            decks.append({
                "href": rel.replace(os.sep, "/"),
                "path": segs,
                "title": meta["title"],
                "date": meta["date"],
                "summary": meta["summary"],
            })
    # 날짜 내림차순, 없으면 제목
    decks.sort(key=lambda d: (d["date"], d["title"]), reverse=True)
    return decks


def render(decks):
    data = [{
        "p": d["path"],
        "t": d["title"],
        "s": d["summary"] or "",
        "d": d["date"] or "",
        "h": d["href"],
    } for d in decks]
    # 원본을 그대로 임베드하고 <script> 안전성만 유니코드 이스케이프로 확보한다.
    # (여기서 HTML 이스케이프하면 data-path 왕복 시 엔티티 디코딩으로 필터가 깨진다.
    #  DOM 주입 시의 이스케이프는 클라이언트 esc()가 담당한다.)
    payload = json.dumps(data, ensure_ascii=False)
    for a, b in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"),
                 (" ", "\\u2028"), (" ", "\\u2029")):
        payload = payload.replace(a, b)
    return (TEMPLATE
            .replace("{{TOTAL}}", str(len(decks)))
            .replace("{{DATA}}", payload))


TEMPLATE = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>장표 모음 · rp-deck</title>
<link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
:root{
  --accent:#3182F6; --accent-weak:#E8F3FF; --accent-ink:#1B64DA;
  --bg:#F7F8FA; --surface:#FFFFFF; --surface-2:#F2F4F6;
  --border:#E8EBED; --border-strong:#DDE1E6;
  --text:#191F28; --text-2:#4E5968; --text-3:#6B7684; --muted:#8B95A1;
  --shadow:0 1px 2px rgba(0,0,0,.04), 0 6px 20px rgba(17,24,39,.05);
  --radius:16px;
  --font:"Pretendard",-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;
}
@media (prefers-color-scheme:dark){
  :root{
    --accent:#4593FC; --accent-weak:#182B48; --accent-ink:#9FC4FF;
    --bg:#14171C; --surface:#1B2026; --surface-2:#232932;
    --border:#2A313B; --border-strong:#38414D;
    --text:#EDEFF2; --text-2:#C2C9D2; --text-3:#9AA2AD; --muted:#79818C;
    --shadow:0 1px 2px rgba(0,0,0,.5), 0 8px 24px rgba(0,0,0,.35);
  }
}
:root[data-theme="dark"]{
  --accent:#4593FC; --accent-weak:#182B48; --accent-ink:#9FC4FF;
  --bg:#14171C; --surface:#1B2026; --surface-2:#232932;
  --border:#2A313B; --border-strong:#38414D;
  --text:#EDEFF2; --text-2:#C2C9D2; --text-3:#9AA2AD; --muted:#79818C;
  --shadow:0 1px 2px rgba(0,0,0,.5), 0 8px 24px rgba(0,0,0,.35);
}
:root[data-theme="light"]{
  --accent:#3182F6; --accent-weak:#E8F3FF; --accent-ink:#1B64DA;
  --bg:#F7F8FA; --surface:#FFFFFF; --surface-2:#F2F4F6;
  --border:#E8EBED; --border-strong:#DDE1E6;
  --text:#191F28; --text-2:#4E5968; --text-3:#6B7684; --muted:#8B95A1;
  --shadow:0 1px 2px rgba(0,0,0,.04), 0 6px 20px rgba(17,24,39,.05);
}
*{margin:0;padding:0;box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{font-family:var(--font);background:var(--bg);color:var(--text);
  letter-spacing:-.01em;-webkit-font-smoothing:antialiased;line-height:1.5}
a{color:inherit;text-decoration:none}
svg{display:block}

/* ── Search (board header, right) ── */
.search{position:relative;flex:0 0 260px}
.search input{width:100%;height:42px;border:1px solid var(--border-strong);background:var(--surface);
  color:var(--text);border-radius:12px;padding:0 14px 0 40px;font:inherit;font-size:14px;outline:none;
  box-shadow:var(--shadow);transition:border-color .15s,box-shadow .15s}
.search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-weak)}
.search input::placeholder{color:var(--muted)}
.search .ico{position:absolute;left:13px;top:50%;transform:translateY(-50%);color:var(--muted)}

/* ── Shell ── */
.shell{max-width:1240px;margin:0 auto;padding:32px 24px 80px;
  display:grid;grid-template-columns:264px minmax(0,1fr);gap:28px;align-items:start}

/* ── Sidebar / directory ── */
.side{position:sticky;top:28px}
.side-h{display:flex;align-items:center;justify-content:space-between;
  padding:0 8px 10px;font-size:12px;font-weight:800;letter-spacing:.04em;color:var(--muted)}
.side-h button{font:inherit;font-size:12px;font-weight:700;color:var(--text-3);background:none;
  border:none;cursor:pointer;padding:2px 6px;border-radius:6px}
.side-h button:hover{background:var(--surface-2);color:var(--accent)}
.tree{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:8px;box-shadow:var(--shadow)}
.tree ul{list-style:none}
.tree .kids{position:relative;margin-left:15px;padding-left:11px;
  border-left:1.5px solid var(--border);display:none}
.tree .kids.root{margin-left:0;padding-left:0;border-left:none;display:block}
.tree li.open>.kids{display:block}
.node{display:flex;align-items:center;gap:6px;width:100%;border:none;background:none;
  font:inherit;color:var(--text-2);cursor:pointer;text-align:left;
  padding:7px 9px;border-radius:9px;line-height:1.3;transition:background .12s,color .12s}
.node:hover{background:var(--surface-2)}
.node .tw{flex:0 0 16px;height:16px;display:grid;place-items:center;color:var(--muted);
  transition:transform .15s;border-radius:5px}
.node .tw.spacer{visibility:hidden}
li.open>.node .tw{transform:rotate(90deg)}
.node .nm{flex:1 1 auto;font-size:14px;font-weight:600;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.node .ct{flex:0 0 auto;font-size:11px;font-weight:700;color:var(--muted);
  background:var(--surface-2);border-radius:999px;padding:1px 8px;font-variant-numeric:tabular-nums}
.node.d1 .nm{font-weight:700;color:var(--text)}
.node.sel{background:var(--accent-weak)}
.node.sel .nm,.node.sel .tw{color:var(--accent-ink)}
.node.sel .ct{background:color-mix(in srgb,var(--accent) 18%,transparent);color:var(--accent-ink)}

/* standalone 전체 button */
.allbtn{display:flex;align-items:center;gap:10px;width:100%;text-align:left;
  padding:13px 16px;margin-bottom:14px;font:inherit;font-size:15px;font-weight:800;
  color:var(--text);background:var(--surface);border:1px solid var(--border);
  border-radius:14px;cursor:pointer;box-shadow:var(--shadow);
  transition:background .15s,color .15s,border-color .15s,box-shadow .15s}
.allbtn:hover{border-color:var(--border-strong)}
.allbtn .ai{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;
  background:var(--accent-weak);color:var(--accent-ink);flex:0 0 auto;transition:inherit}
.allbtn .al{flex:1 1 auto}
.allbtn .ct{flex:0 0 auto;font-size:12px;font-weight:800;color:var(--muted);
  background:var(--surface-2);border-radius:999px;padding:2px 10px;font-variant-numeric:tabular-nums}
.allbtn.sel{background:var(--accent);color:#fff;border-color:transparent;
  box-shadow:0 6px 16px rgba(49,130,246,.32)}
.allbtn.sel .ai,.allbtn.sel .ct{background:rgba(255,255,255,.22);color:#fff}

/* ── Board ── */
.board-h{display:flex;align-items:center;justify-content:space-between;gap:14px 20px;
  padding:2px 4px 18px;flex-wrap:wrap}
.board-h-l{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;min-width:0}
.crumb{font-size:22px;font-weight:800;letter-spacing:-.02em;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.crumb .sep{color:var(--border-strong);font-weight:400}
.crumb .dim{color:var(--muted);font-weight:700}
.board-h .n{font-size:14px;color:var(--muted);font-weight:600}
.board-h .n b{color:var(--accent);font-variant-numeric:tabular-nums}

.list{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  overflow:hidden;box-shadow:var(--shadow)}
.list-head{display:grid;grid-template-columns:1fr 96px;gap:14px;padding:12px 22px;
  border-bottom:1px solid var(--border);background:var(--surface-2);
  font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.02em}
.list-head .r{text-align:right}
.row{display:grid;grid-template-columns:1fr 96px;gap:14px;align-items:center;
  padding:17px 22px;border-bottom:1px solid var(--border);transition:background .12s}
.row:last-child{border-bottom:none}
.row:hover{background:var(--surface-2)}
.cell-path{display:flex;align-items:center;gap:6px;margin-bottom:6px;flex-wrap:wrap}
.tag{font-size:11.5px;font-weight:700;color:var(--text-3);background:var(--surface-2);
  border:1px solid var(--border);padding:2px 9px;border-radius:7px;cursor:pointer;
  transition:color .12s,background .12s,border-color .12s}
.row:hover .tag{border-color:var(--border-strong)}
.tag:hover,.tag:focus-visible{color:var(--accent-ink);background:var(--accent-weak);
  border-color:transparent;outline:none}
.tag.lead{color:var(--accent-ink);background:var(--accent-weak);border-color:transparent}
.ttl{font-size:16px;font-weight:700;color:var(--text);line-height:1.4;word-break:keep-all;
  display:flex;align-items:center;gap:7px}
.row:hover .ttl{color:var(--accent)}
.ttl .go{opacity:0;color:var(--accent);transition:opacity .12s,transform .12s;transform:translateX(-3px)}
.row:hover .ttl .go{opacity:1;transform:translateX(0)}
.sum{font-size:13.5px;color:var(--text-3);line-height:1.55;margin-top:5px;word-break:keep-all;
  display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
.date{text-align:right;font-size:13px;color:var(--muted);font-weight:600;font-variant-numeric:tabular-nums}
.empty{padding:64px 20px;text-align:center;color:var(--muted);font-size:15px}

/* mobile dir toggle */
.dirtoggle{display:none}
@media (max-width:860px){
  .shell{grid-template-columns:1fr;gap:16px}
  .side{position:static}
  .dirtoggle{display:flex;align-items:center;gap:8px;width:100%;justify-content:space-between;
    font:inherit;font-weight:700;font-size:14px;color:var(--text);background:var(--surface);
    border:1px solid var(--border);border-radius:12px;padding:12px 16px;cursor:pointer;box-shadow:var(--shadow)}
  .side.collapsed .side-h,.side.collapsed .tree{display:none}
  .board-h{align-items:stretch}
  .search{flex:1 1 100%;order:2}
  .list-head,.row{grid-template-columns:1fr 76px}
  .list-head,.row{padding-left:16px;padding-right:16px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style></head><body>

<div class="shell">
  <aside class="side" id="side">
    <button class="dirtoggle" id="dirToggle">디렉토리
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="m6 9 6 6 6-6"/></svg>
    </button>
    <button class="allbtn sel" id="allBtn" type="button">
      <span class="ai"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg></span>
      <span class="al">전체</span><span class="ct" id="allCt">{{TOTAL}}</span>
    </button>
    <div class="side-h"><span>디렉토리</span><button id="toggleAll">모두 접기</button></div>
    <nav class="tree" id="tree"></nav>
  </aside>

  <main>
    <div class="board-h">
      <div class="board-h-l">
        <h1 class="crumb" id="crumb"><span class="dim">전체</span></h1>
        <span class="n"><b id="count">{{TOTAL}}</b>개의 장표</span>
      </div>
      <div class="search">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></svg></span>
        <input id="q" type="search" placeholder="제목·설명 검색" autocomplete="off">
      </div>
    </div>
    <div class="list" id="list"></div>
  </main>
</div>

<script>
const DECKS = {{DATA}};
DECKS.sort((a,b)=> a.d<b.d?1: a.d>b.d?-1 : (a.t<b.t?-1:1));
const ESC={"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"};
const esc=s=>String(s).replace(/[&<>"']/g,c=>ESC[c]);  // innerHTML/속성 주입 이스케이프

const CHEV='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>';
const GO='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>';

/* build tree */
function buildTree(){
  const root={name:"전체",path:[],kids:new Map(),count:0};
  for(const d of DECKS){
    let n=root; root.count++;
    d.p.forEach((seg,i)=>{
      if(!n.kids.has(seg)) n.kids.set(seg,{name:seg,path:d.p.slice(0,i+1),kids:new Map(),count:0});
      n=n.kids.get(seg); n.count++;
    });
  }
  return root;
}
const TREE=buildTree();
let selected=[];

function key(a){return a.join("/");}
function renderTree(){
  document.getElementById("allCt").textContent=TREE.count;
  document.getElementById("tree").innerHTML=renderKids(TREE,1);
  syncAll();
}
function syncAll(){
  document.getElementById("allBtn").classList.toggle("sel",selected.length===0);
}
/* 공용 선택: 트리 노드·전체 버튼·행 태그가 공유 */
function selectPath(pathArr){
  selected=pathArr.slice();
  document.querySelectorAll(".node.sel").forEach(n=>n.classList.remove("sel"));
  const want=key(pathArr);
  const node=[...document.querySelectorAll(".node")].find(n=>n.dataset.path===want);
  if(node){
    node.classList.add("sel");
    let li=node.closest("li");
    while(li){li.classList.add("open");li=li.parentElement.closest("li");}
  }
  syncAll();
  resetSearch();
  renderList();
}
function renderKids(node,depth){
  if(!node.kids.size) return "";
  let out=`<ul class="kids${depth===1?' root':''}">`;
  for(const child of node.kids.values()){
    const hasKids=child.kids.size>0;
    const sel=key(child.path)===key(selected)?" sel":"";
    const tw=hasKids?`<span class="tw">${CHEV}</span>`:`<span class="tw spacer">${CHEV}</span>`;
    const kp=esc(key(child.path));
    out+=`<li class="open" data-path="${kp}">
      <button class="node d${depth}${sel}" data-path="${kp}" type="button">
        ${tw}<span class="nm">${esc(child.name)}</span><span class="ct">${child.count}</span>
      </button>${renderKids(child,depth+1)}</li>`;
  }
  out+="</ul>";
  return out;
}

/* board list */
let query="";
function resetSearch(){
  clearTimeout(searchTimer);
  query="";
  const q=document.getElementById("q");
  if(q) q.value="";
}
function renderList(){
  const el=document.getElementById("list");
  const pre=key(selected);
  let items=DECKS.filter(d=> pre===""? true : key(d.p.slice(0,selected.length))===pre);
  if(query){const q=query.toLowerCase();
    items=items.filter(d=>(d.t+" "+d.s+" "+d.p.join(" ")).toLowerCase().includes(q));}
  document.getElementById("count").textContent=items.length;
  const cr=document.getElementById("crumb");
  cr.innerHTML= selected.length===0
    ? '<span class="dim">전체</span>'
    : selected.map((s,i)=> (i? '<span class="sep">›</span>':'')+`<span${i===selected.length-1?'':' class="dim"'}>${esc(s)}</span>`).join("");
  if(!items.length){el.innerHTML='<div class="empty">해당 디렉토리에 장표가 없어요.</div>';return;}
  const head='<div class="list-head"><span>제목</span><span class="r">작성일</span></div>';
  const rows=items.map(d=>{
    const tags=d.p.map((s,i)=>`<span class="tag${i===0?' lead':''}" data-path="${esc(d.p.slice(0,i+1).join("/"))}" role="button" tabindex="0">${esc(s)}</span>`).join("");
    return `<a class="row" href="${esc(d.h)}">
      <div>
        <div class="cell-path">${tags}</div>
        <div class="ttl">${esc(d.t)}<span class="go">${GO}</span></div>
        <div class="sum">${esc(d.s)}</div>
      </div>
      <div class="date">${esc(d.d)}</div>
    </a>`;
  }).join("");
  el.innerHTML=head+rows;
}

/* events */
document.getElementById("tree").addEventListener("click",e=>{
  const tw=e.target.closest(".tw");
  const node=e.target.closest(".node");
  if(!node) return;
  if(tw && !tw.classList.contains("spacer")){
    e.stopPropagation();
    const li=node.closest("li"); if(li) li.classList.toggle("open"); return;
  }
  selectPath(node.dataset.path? node.dataset.path.split("/"):[]);
});
document.getElementById("allBtn").addEventListener("click",()=>selectPath([]));

/* 행의 경로 태그 클릭 → 해당 디렉토리 선택 (행 링크 이동은 막음) */
const listEl=document.getElementById("list");
function tagSelect(e){
  const tag=e.target.closest(".tag");
  if(!tag||!listEl.contains(tag)) return;
  e.preventDefault();
  selectPath(tag.dataset.path? tag.dataset.path.split("/"):[]);
}
listEl.addEventListener("click",tagSelect);
listEl.addEventListener("keydown",e=>{ if(e.key==="Enter"||e.key===" ") tagSelect(e); });
let searchTimer;
document.getElementById("q").addEventListener("input",e=>{
  const v=e.target.value.trim();
  clearTimeout(searchTimer);
  searchTimer=setTimeout(()=>{query=v;renderList();},500);
});
let collapsed=false;
document.getElementById("toggleAll").addEventListener("click",e=>{
  collapsed=!collapsed;
  document.querySelectorAll("#tree li").forEach(li=>li.classList.toggle("open",!collapsed));
  e.target.textContent=collapsed?"모두 펼치기":"모두 접기";
});
document.getElementById("dirToggle").addEventListener("click",()=>{
  document.getElementById("side").classList.toggle("collapsed");
});
if(window.matchMedia("(max-width:860px)").matches)
  document.getElementById("side").classList.add("collapsed");

renderTree();
renderList();
</script>
</body></html>
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
