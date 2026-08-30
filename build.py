#!/usr/bin/env python3
"""학습 노트 -> 책(HTML) 빌드.

원본 노트는 notes/ 에 그대로 두고 book/ 에는 연결 자료만 둡니다.
같은 내용을 두 곳에 복사하지 않기 위해 ORDER 목록으로 조립만 합니다.

모든 장을 한 파일에 합치면 43만자·1MB가 넘어 브라우저가 렌더링하지 못합니다(실측).
그래서 **장마다 별도 HTML**을 만들고 index.html은 목차만 갖습니다.

실행: python build.py
결과: docs/index.html + docs/ch01.html ... (GitHub Pages 소스 폴더)
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import sys

import markdown

import make_index

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))

MANIFEST = os.path.join(ROOT, "book", "manifest.json")

MD_EXT = ["extra", "sane_lists", "admonition", "codehilite", "toc"]
MD_CFG = {
    "codehilite": {"guess_lang": False, "noclasses": False},
    "toc": {"anchorlink": False, "permalink": False},
}


def slug(text: str) -> str:
    """한글을 살린 앵커 id. 중복은 호출부에서 번호를 붙입니다."""
    t = re.sub(r"[`*_~\[\]()]", "", text).strip()
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"[^0-9A-Za-z가-힣\-]", "", t)
    return t.strip("-").lower() or "s"


def read(path: str) -> str:
    with io.open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def read_manifest() -> dict:
    with io.open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


# 노트 본문의 태그는 전부 글자입니다. 실행되면 노트 자체가 취약점이 됩니다(XSS 실습 페이로드 수록).
# 표 생성기가 넣는 <br> 만 진짜 HTML로 남깁니다. 여는 꺾쇠만 막으면 태그가 성립하지 않습니다.
LT = re.compile(r"<(?!/?br\s*/?>)", re.I)
# 홀로 선 <https://...> 는 마크다운 자동 링크입니다. 실행 위험이 없어 링크로 살립니다.
AUTOLINK = re.compile(r"(?<![\"'=\w])<(https?://[^<>\s]+)>")
# 본문 목록이 번호 제목으로 잘못 승격된 것들. 화살표 설명이나 문장 끝맺음이 있으면 제목이 아닙니다.
NOT_HEADING = re.compile(r"←|[가-힣A-Za-z0-9)\]]\.$")


def demote(md_text: str) -> tuple[str, str]:
    """장 제목(첫 h1)을 뽑아내고 나머지 제목 단계를 한 칸 내립니다.

    첫 h1 뒤에 나오는 우물정(`#`)은 제목이 아니라 본문입니다. PDF·노트에서
    코드블록 밖으로 새어 나온 셸 주석(`# 설명`), C 전처리기(`#include`) 따위입니다.
    글자는 그대로 두고 마크다운이 제목으로 읽지 않게 escape 만 합니다.
    """
    title = ""
    out: list[str] = []
    in_fence = False
    # 인용부호(`> `)를 앞에 달고 오는 줄도 같은 규칙을 받습니다.
    head = re.compile(r"^((?:\s*>)*\s*)(#{1,6})(\s+)?(.*)$")
    for line in md_text.split(chr(10)):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        keep: list[str] = []
        line = AUTOLINK.sub(lambda t: keep.append(t.group(0)) or f"@@AL{len(keep) - 1}@@", line)
        line = LT.sub("&lt;", line)
        for i, held in enumerate(keep):
            line = line.replace(f"@@AL{i}@@", held)
        m = head.match(line)
        if not m:
            out.append(line)
            continue
        quote, level, spaced, text = m.group(1), len(m.group(2)), m.group(3), m.group(4).strip()
        if level >= 2 and spaced and NOT_HEADING.search(text):
            out.append(quote + text)
            continue
        if level == 1 and spaced and not title and not quote.strip():
            title = text
            continue
        if level == 1 or not spaced:
            out.append(quote + "\\" + line[len(quote):].lstrip())
            continue
        out.append(quote + "#" * min(level + 1, 6) + " " + text)
    return title, chr(10).join(out)


def anchor_headings(html_text: str) -> tuple[str, list[tuple[int, str, str]]]:
    """h2~h4에 고유 id를 달고 목차 항목을 뽑습니다."""
    items: list[tuple[int, str, str]] = []
    seen: dict[str, int] = {}

    def repl(m: re.Match) -> str:
        level = int(m.group(1))
        inner = m.group(3)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        base = slug(text)
        seen[base] = seen.get(base, 0) + 1
        aid = base if seen[base] == 1 else f"{base}-{seen[base]}"
        items.append((level, aid, text))
        return f'<h{level} id="{aid}">{inner}</h{level}>'

    # toc 확장이 이미 id를 넣어 두므로 속성까지 받아 낸 뒤 우리 id로 덮어씁니다.
    html_text = re.sub(r"<h([2-4])([^>]*)>(.*?)</h\1>", repl, html_text, flags=re.S)
    return html_text, items


def code_block_labels(md_text: str) -> list[str]:
    """Fenced code를 읽어 HTML/Notion에서 보여 줄 언어 라벨을 추론합니다."""
    blocks: list[tuple[str, str]] = []
    in_fence = False
    language = ""
    body: list[str] = []
    for line in md_text.splitlines():
        if line.lstrip().startswith("```"):
            if in_fence:
                blocks.append((language, "\n".join(body)))
                language = ""
                body = []
            else:
                language = line.lstrip()[3:].strip()
            in_fence = not in_fence
        elif in_fence:
            body.append(line)

    labels: list[str] = []
    cisco = re.compile(
        r"(^|\n)\s*(?:Router(?:\([^)]*\))?[>#]|conf t|configure terminal|interface |"
        r"router (?:ospf|eigrp|rip)|show (?:ip |ipv6 |interfaces|running|startup|access|crypto|standby|vlan|spanning)|"
        r"(?:no )?(?:shutdown|router |ip address|network |access-list|vlan )|"
        r"(?:permit|deny) (?:ip|tcp|udp|icmp))",
        re.I,
    )
    shell = re.compile(
        r"(^|\n)\s*(?:\$|#|sudo |dnf |yum |systemctl |firewall-cmd |nmcli |semanage |"
        r"chmod |chown |cp |mv |mkdir |grep |awk |sed |cat |journalctl |ssh |scp |curl |wget )",
        re.I,
    )
    sql = re.compile(r"\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|GRANT|SHOW)\b", re.I)
    for raw, body_text in blocks:
        key = raw.lower().replace("_", " ").strip()
        if cisco.search(body_text):
            labels.append("Cisco IOS")
        elif key in {"bash", "sh", "shell", "zsh", "console"} or shell.search(body_text):
            labels.append("Shell")
        elif key in {"sql", "mysql", "mariadb"} or sql.search(body_text):
            labels.append("SQL")
        elif key in {"python", "py"}:
            labels.append("Python")
        elif key in {"javascript", "js"}:
            labels.append("JavaScript")
        elif key in {"c", "c++", "cpp"}:
            labels.append("C")
        elif key in {"plain text", "plaintext", "text", "txt", "output", ""}:
            labels.append("Text")
        else:
            labels.append(raw.strip().replace("-", " ").title() or "Code")
    return labels


def decorate_code_blocks(html_text: str, labels: list[str]) -> str:
    """codehilite 출력을 Notion식 코드 카드로 감싸고 복사 버튼을 붙입니다."""
    block_re = re.compile(r'<div class="codehilite">.*?</div>', re.S)
    index = 0

    def repl(match: re.Match) -> str:
        nonlocal index
        label = labels[index] if index < len(labels) else "Code"
        index += 1
        safe_label = html.escape(label)
        return (
            f'<div class="code-shell" data-language="{safe_label}">'
            f'<div class="code-toolbar"><span class="code-mark">⌘</span>'
            f'<span class="code-label">{safe_label}</span>'
            '<button class="code-copy" type="button">복사</button></div>'
            f'{match.group(0)}</div>'
        )

    return block_re.sub(repl, html_text)


CSS = """
:root{
  --paper:#f7f7f5; --paper-strong:#ffffff; --ink:#252525; --muted:#787774; --rule:#e8e8e6;
  --accent:#3d7188; --accent-soft:#e9f3f6; --code-bg:#1f2937; --code-ink:#e5edf4;
  --code-border:#334454; --side:#f1f1ef; --mark:#fff0b8; --shadow:0 14px 36px rgba(37,37,37,.08);
}
@media (prefers-color-scheme: dark){
  :root{
    --paper:#191919; --paper-strong:#202020; --ink:#e7e7e5; --muted:#a6a6a0; --rule:#383836;
    --accent:#8fc1d2; --accent-soft:#213238; --code-bg:#111827; --code-ink:#e5edf4;
    --code-border:#405466; --side:#141414; --mark:#514614; --shadow:none;
  }
}
*{box-sizing:border-box}
html{scroll-behavior:smooth; scroll-padding-top:16px}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"Noto Sans KR","Apple SD Gothic Neo","Malgun Gothic",sans-serif;
  font-size:16px; line-height:1.9; word-break:keep-all; overflow-wrap:anywhere;
}
.layout{display:grid; grid-template-columns:276px minmax(0,1fr); min-height:100vh}
aside{
  position:sticky; top:0; align-self:start; height:100vh; overflow:auto;
  background:var(--side); border-right:1px solid var(--rule); padding:24px 14px 60px;
  font-family:ui-sans-serif,system-ui,"Malgun Gothic",sans-serif; font-size:13px; line-height:1.5;
}
aside .brand{font-size:15px; font-weight:700; margin:0 0 2px}
aside .brand a{color:inherit; text-decoration:none}
aside .sub{color:var(--muted); font-size:11px; margin-bottom:14px}
#q{width:100%; padding:7px 9px; font:inherit; margin-bottom:12px;
   border:1px solid var(--rule); border-radius:6px; background:var(--paper); color:var(--ink)}
aside a{display:block; color:inherit; text-decoration:none; padding:3px 6px; border-radius:5px}
aside a:hover{background:var(--accent-soft)}
aside a.cur{background:var(--accent-soft); color:var(--accent); font-weight:700}
aside a.on{color:var(--accent); font-weight:700}
aside .part{margin:16px 0 6px; font-size:10px; letter-spacing:.16em; color:var(--muted); font-weight:700}
aside .lv3{padding-left:16px; color:var(--muted)}
aside .lv4{padding-left:28px; color:var(--muted); font-size:12px}
aside .inchap{margin:6px 0 10px; padding:8px 0 4px; border-top:1px dashed var(--rule); border-bottom:1px dashed var(--rule)}

main{margin:32px 40px 120px; padding:42px 50px 100px; max-width:920px; background:var(--paper-strong);
     border:1px solid var(--rule); border-radius:16px; box-shadow:var(--shadow)}
h1,h2,h3,h4{font-family:ui-sans-serif,system-ui,"Malgun Gothic",sans-serif; line-height:1.35; letter-spacing:-.02em}
h1{font-size:32px; margin:0 0 8px}
h2{font-size:23px; margin:52px 0 14px; padding:12px 0 10px 15px; border-bottom:1px solid var(--rule); position:relative}
h2::before{content:""; position:absolute; left:0; top:11px; bottom:10px; width:4px; border-radius:4px; background:var(--accent)}
h3{font-size:18px; margin:34px 0 9px; color:var(--accent)}
h4{font-size:15px; margin:24px 0 7px; color:var(--muted)}
.chapter-no{font-family:ui-sans-serif,system-ui,sans-serif; font-size:11px; letter-spacing:.18em; color:var(--muted); font-weight:700}
p{max-width:78ch; margin:0 0 16px}
ul,ol{margin:0 0 14px; padding-left:22px}
li{margin:3px 0}
a{color:var(--accent); text-underline-offset:3px}
blockquote{margin:20px 0; padding:14px 18px; border:1px solid var(--rule); border-left:5px solid var(--accent);
           border-radius:8px; background:var(--accent-soft)}
blockquote p:last-child{margin:0}
hr{border:0; border-top:1px solid var(--rule); margin:28px 0}
mark{background:var(--mark); color:inherit}
code{font-family:ui-monospace,"Cascadia Mono",Consolas,monospace; font-size:.88em; background:var(--accent-soft); padding:2px 5px; border-radius:4px}
pre{background:var(--code-bg); color:var(--code-ink); border:1px solid var(--code-border); border-radius:10px; padding:16px 18px;
     overflow-x:auto; line-height:1.65; font-size:13.5px; white-space:pre; tab-size:2}
pre code{background:none; padding:0; font-size:inherit}
.code-shell{margin:22px 0 26px; border:1px solid var(--code-border); border-radius:12px; overflow:hidden;
            background:var(--code-bg); box-shadow:0 8px 22px rgba(15,23,42,.12)}
.code-toolbar{display:flex; align-items:center; gap:8px; min-height:38px; padding:0 12px;
              background:#263646; color:#cbd8e2; font:12px/1 ui-sans-serif,system-ui,"Malgun Gothic",sans-serif}
.code-mark{display:grid; place-items:center; width:20px; height:20px; border-radius:5px; background:#3d7188; color:#fff; font-weight:700}
.code-label{font-weight:700; letter-spacing:.02em}
.code-copy{margin-left:auto; border:1px solid #597081; border-radius:6px; padding:6px 9px; background:transparent; color:#dbe7ee;
           font:inherit; cursor:pointer}
.code-copy:hover{background:#385064}
.codehilite{background:var(--code-bg); color:var(--code-ink); overflow-x:auto}
.codehilite pre{border:0; border-radius:0; margin:0; background:transparent}
.codehilite .c,.codehilite .ch,.codehilite .cm,.codehilite .c1{color:#94a3b8}
.codehilite .k,.codehilite .kc,.codehilite .kd,.codehilite .kn,.codehilite .kp,.codehilite .kr{color:#93c5fd}
.codehilite .s,.codehilite .sa,.codehilite .sb,.codehilite .sc,.codehilite .dl{color:#86efac}
.codehilite .nf,.codehilite .nc{color:#f9a8d4}
.codehilite .m,.codehilite .mi,.codehilite .mf{color:#fcd34d}
.tablewrap{overflow-x:auto; margin:0 0 18px}
table{border-collapse:collapse; width:100%; font-size:14.5px; font-family:ui-sans-serif,system-ui,sans-serif}
th,td{border:1px solid var(--rule); padding:8px 10px; text-align:left; vertical-align:top}
th{background:var(--accent-soft); font-weight:700}
table tr:first-child td{background:var(--accent-soft); font-weight:700}
tbody tr:nth-child(even) td{background:var(--side)}
@supports (background:color-mix(in srgb, white 50%, black)){tbody tr:nth-child(even) td{background:color-mix(in srgb, var(--paper-strong) 88%, var(--accent-soft))}}
.admonition{border:1px solid var(--rule); border-left:5px solid var(--accent); border-radius:6px; padding:12px 16px; margin:18px 0; background:var(--accent-soft)}
.admonition-title{font-weight:700; margin:0 0 6px !important}
.nav{display:flex; justify-content:space-between; gap:12px; margin-top:60px; padding-top:20px; border-top:1px solid var(--rule);
     font-family:ui-sans-serif,system-ui,sans-serif; font-size:13px}
.nav a{display:block; max-width:46%; text-decoration:none; padding:10px 14px; border:1px solid var(--rule); border-radius:8px}
.nav a:hover{background:var(--accent-soft)}
.nav .lbl{display:block; color:var(--muted); font-size:11px; letter-spacing:.1em}
.cover{border:1px solid var(--rule); border-radius:10px; padding:26px 28px; background:var(--accent-soft); margin-bottom:34px}
.cover h1{font-size:34px; margin:0 0 6px}
.cover p{margin:0; color:var(--muted)}
.chapter-head{margin-bottom:30px; padding-bottom:22px; border-bottom:1px solid var(--rule)}
.toclist{list-style:none; padding:0; margin:0}
.toclist li{margin:0 0 6px}
.toclist .part{margin:26px 0 10px; font-size:11px; letter-spacing:.2em; color:var(--accent); font-weight:700;
               font-family:ui-sans-serif,system-ui,sans-serif}
.toclist a{display:block; padding:11px 15px; border:1px solid var(--rule); border-radius:8px; text-decoration:none; background:var(--paper)}
.toclist a:hover{background:var(--accent-soft)}
.toclist .t{display:block; font-weight:700; margin-bottom:2px}
#top{position:fixed; right:22px; bottom:22px; padding:9px 13px; border:1px solid var(--rule); border-radius:999px;
     background:var(--side); color:var(--ink); text-decoration:none; font-size:12px;
     font-family:ui-sans-serif,system-ui,sans-serif; box-shadow:0 2px 10px rgba(0,0,0,.12)}
@media (max-width:900px){
  .layout{grid-template-columns:1fr}
  aside{position:static; height:auto; border-right:0; border-bottom:1px solid var(--rule)}
  main{margin:0; padding:30px 20px 90px; max-width:none; border:0; border-radius:0; box-shadow:none}
}
@media print{
  aside,#top,.nav{display:none}
  .layout{display:block}
  main{max-width:none; margin:0; padding:0; border:0; box-shadow:none}
  pre,table,.admonition,.code-shell{break-inside:avoid}
  h2,h3{break-after:avoid}
}
"""

JS = """
const q=document.getElementById('q');
if(q){
  const links=[...document.querySelectorAll('aside a')];
  q.addEventListener('input',()=>{
    const v=q.value.trim().toLowerCase();
    links.forEach(a=>{a.style.display = !v || a.textContent.toLowerCase().includes(v) ? '' : 'none';});
    document.querySelectorAll('aside .part').forEach(p=>{p.style.display = v ? 'none' : '';});
  });
}
document.querySelectorAll('.code-copy').forEach(button=>{
  button.addEventListener('click', async ()=>{
    const code=button.closest('.code-shell')?.querySelector('code');
    if(!code) return;
    const value=code.innerText;
    try{
      await navigator.clipboard.writeText(value);
    }catch(e){
      const area=document.createElement('textarea');
      area.value=value; document.body.appendChild(area); area.select();
      document.execCommand('copy'); area.remove();
    }
    const old=button.textContent; button.textContent='복사됨';
    setTimeout(()=>{button.textContent=old;},1200);
  });
});
const inchap=[...document.querySelectorAll('aside .inchap a')];
if(inchap.length){
  const byId=Object.fromEntries(inchap.map(a=>[a.hash.slice(1),a]));
  const obs=new IntersectionObserver(es=>{
    es.forEach(e=>{ if(!e.isIntersecting) return;
      inchap.forEach(a=>a.classList.remove('on'));
      const a=byId[e.target.id]; if(a){a.classList.add('on'); a.scrollIntoView({block:'nearest'});}
    });
  },{rootMargin:'0px 0px -80% 0px'});
  document.querySelectorAll('main h2[id],main h3[id]').forEach(t=>obs.observe(t));
}
"""


def page(title: str, sidebar: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · SKT ALEPH 학습 노트</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head><body>
<div class="layout">
<aside>
  <div class="brand"><a href="index.html">SKT ALEPH 학습 노트</a></div>
  <div class="sub">IT 인프라 · 보안 과정</div>
  <input id="q" type="search" placeholder="목차 검색" aria-label="목차 검색">
  <nav>{sidebar}</nav>
</aside>
<main>{body}</main>
</div>
<a id="top" href="#">▲ 맨 위</a>
<script>{JS}</script>
</body></html>"""


def main() -> int:
    manifest = read_manifest()
    make_index.generate(ROOT, read)

    md = markdown.Markdown(extensions=MD_EXT, extension_configs=MD_CFG)
    chapters: list[dict] = []

    for entry in manifest["chapters"]:
        sources = entry["sources"]
        missing = [path for path in sources if not os.path.exists(os.path.join(ROOT, path))]
        if missing:
            for path in missing:
                print(f"  건너뜀 (없음): {path}", file=sys.stderr)
            continue
        parts: list[str] = []
        total_chars = 0
        labels = entry.get("source_labels", [])
        for index, path in enumerate(sources):
            raw = read(path)
            total_chars += len(raw)
            source_title, demoted = demote(raw)
            if len(sources) > 1:
                label = labels[index] if index < len(labels) else source_title or os.path.basename(path)
                demoted = f"## {label}\n\n{demoted}"
            parts.append(demoted)
        combined = "\n\n---\n\n".join(parts)
        md.reset()
        rendered = md.convert(combined)
        rendered, items = anchor_headings(rendered)
        rendered = rendered.replace("<table>", '<div class="tablewrap"><table>')
        rendered = rendered.replace("</table>", "</table></div>")
        rendered = decorate_code_blocks(rendered, code_block_labels(combined))
        no = len(chapters) + 1
        chapters.append({
            "no": no,
            "file": entry.get("file", f"ch{no:02d}.html"),
            "title": entry["title"],
            "part": entry.get("part"),
            "html": rendered,
            "items": items,
            "chars": total_chars,
        })

    def chapter_list(current: int | None) -> str:
        out: list[str] = []
        for c in chapters:
            if c["part"]:
                out.append(f'<div class="part">{html.escape(c["part"])}</div>')
            cls = "cur" if c["no"] == current else ""
            out.append(
                f'<a class="{cls}" href="{c["file"]}">{c["no"]:02d}. {html.escape(c["title"])}</a>'
            )
            if c["no"] == current and c["items"]:
                inner = "".join(
                    f'<a class="lv{lv}" href="#{aid}">{html.escape(t)}</a>'
                    for lv, aid, t in c["items"]
                )
                out.append(f'<div class="inchap">{inner}</div>')
        return "".join(out)

    archives: list[dict] = []
    for index, entry in enumerate(manifest.get("archives", []), start=1):
        path = entry["source"]
        if not os.path.exists(os.path.join(ROOT, path)):
            print(f"  원문 건너뜀 (없음): {path}", file=sys.stderr)
            continue
        raw = read(path)
        _, demoted = demote(raw)
        md.reset()
        rendered = md.convert(demoted)
        rendered, items = anchor_headings(rendered)
        rendered = rendered.replace("<table>", '<div class="tablewrap"><table>')
        rendered = rendered.replace("</table>", "</table></div>")
        rendered = decorate_code_blocks(rendered, code_block_labels(demoted))
        archives.append({
            "no": index,
            "file": entry.get("file", f"archive-{index:02d}.html"),
            "title": entry["title"],
            "html": rendered,
            "items": items,
            "chars": len(raw),
        })

    def archive_list(current: int | None) -> str:
        if not archives:
            return ""
        out: list[str] = ['<div class="part">원문 보존</div>']
        for a in archives:
            cls = "cur" if a["no"] == current else ""
            out.append(f'<a class="{cls}" href="{a["file"]}">원문 {a["no"]:02d}. {html.escape(a["title"])}</a>')
        return "".join(out)

    site = os.path.join(ROOT, "docs")
    os.makedirs(site, exist_ok=True)

    # 목차 페이지
    toc: list[str] = [
        '<div class="cover"><h1>SKT ALEPH 학습 노트</h1>'
        "<p>IT 인프라 · 보안 과정 · 수업이 진행되는 대로 장을 추가합니다</p></div>",
        '<ul class="toclist">',
    ]
    for c in chapters:
        if c["part"]:
            toc.append(f'<li class="part">{html.escape(c["part"])}</li>')
        toc.append(
            f'<li><a href="{c["file"]}"><span class="t">{c["no"]:02d}. {html.escape(c["title"])}</span></a></li>'
        )
    toc.append("</ul>")
    if archives:
        toc.append('<li class="part">원문 보존</li>')
        for a in archives:
            toc.append(
                f'<li><a href="{a["file"]}"><span class="t">원문 {a["no"]:02d}. {html.escape(a["title"])}</span></a></li>'
            )
    with io.open(os.path.join(site, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(page("목차", chapter_list(None) + archive_list(None), "".join(toc)))

    # 장별 페이지
    for i, c in enumerate(chapters):
        nav: list[str] = ['<div class="nav">']
        if i > 0:
            p = chapters[i - 1]
            nav.append(f'<a href="{p["file"]}"><span class="lbl">이전</span>{html.escape(p["title"])}</a>')
        else:
            nav.append("<span></span>")
        if i < len(chapters) - 1:
            n = chapters[i + 1]
            nav.append(f'<a href="{n["file"]}"><span class="lbl">다음</span>{html.escape(n["title"])}</a>')
        nav.append("</div>")
        body = (
            f'<header class="chapter-head"><div class="chapter-no">CHAPTER {c["no"]:02d}</div>'
            f'<h1>{html.escape(c["title"])}</h1></header>{c["html"]}{"".join(nav)}'
        )
        with io.open(os.path.join(site, c["file"]), "w", encoding="utf-8", newline="\n") as f:
            f.write(page(c["title"], chapter_list(c["no"]) + archive_list(None), body))

    for i, a in enumerate(archives):
        nav: list[str] = ['<div class="nav">']
        if i > 0:
            previous = archives[i - 1]
            nav.append(f'<a href="{previous["file"]}"><span class="lbl">이전 원문</span>{html.escape(previous["title"])}</a>')
        else:
            nav.append("<span></span>")
        if i < len(archives) - 1:
            following = archives[i + 1]
            nav.append(f'<a href="{following["file"]}"><span class="lbl">다음 원문</span>{html.escape(following["title"])}</a>')
        else:
            nav.append('<a href="index.html"><span class="lbl">목차</span>전체 목차</a>')
        nav.append("</div>")
        body = (
            f'<header class="chapter-head"><div class="chapter-no">ORIGINAL {a["no"]:02d}</div>'
            f'<h1>{html.escape(a["title"])}</h1></header>{a["html"]}{"".join(nav)}'
        )
        with io.open(os.path.join(site, a["file"]), "w", encoding="utf-8", newline="\n") as f:
            f.write(page(a["title"], chapter_list(None) + archive_list(a["no"]), body))

    total = sum(c["chars"] for c in chapters) + sum(a["chars"] for a in archives)
    output_files = [c["file"] for c in chapters] + [a["file"] for a in archives]
    biggest = max(os.path.getsize(os.path.join(site, path)) for path in output_files)
    print(f"빌드 완료: index.html + 장 {len(chapters)}개 + 원문 {len(archives)}개 (가장 큰 파일 {biggest // 1024} KB)")
    for c in chapters:
        print(f"  {c['no']:>2}. {c['title'][:50]:<52} 소제목 {len(c['items']):>3}개 · {c['chars']:>7,}자")
    print(f"  합계 {total:,}자")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
