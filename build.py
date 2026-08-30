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


CSS = """
:root{
  --paper:#fbf8f3; --ink:#23201c; --muted:#6b6459; --rule:#e0d8cb;
  --accent:#8a5a2b; --accent-soft:#f3e9dc; --code-bg:#f4efe6; --side:#f6f1e8; --mark:#ffe8a3;
}
@media (prefers-color-scheme: dark){
  :root{
    --paper:#16181c; --ink:#e6e3dd; --muted:#9a958c; --rule:#2c3036;
    --accent:#d0a06a; --accent-soft:#241f18; --code-bg:#1c1f24; --side:#101215; --mark:#5a4a12;
  }
}
*{box-sizing:border-box}
html{scroll-behavior:smooth; scroll-padding-top:16px}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"Noto Serif KR","Apple SD Gothic Neo","Malgun Gothic",serif;
  font-size:17px; line-height:1.85; word-break:keep-all; overflow-wrap:anywhere;
}
.layout{display:grid; grid-template-columns:288px minmax(0,1fr); min-height:100vh}
aside{
  position:sticky; top:0; align-self:start; height:100vh; overflow:auto;
  background:var(--side); border-right:1px solid var(--rule); padding:20px 14px 60px;
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

main{padding:40px 40px 120px; max-width:860px}
h1,h2,h3,h4{font-family:ui-sans-serif,system-ui,"Malgun Gothic",sans-serif; line-height:1.35; letter-spacing:-.02em}
h1{font-size:30px; margin:0 0 8px}
h2{font-size:23px; margin:44px 0 12px; padding-bottom:8px; border-bottom:2px solid var(--rule)}
h3{font-size:18px; margin:30px 0 8px; color:var(--accent)}
h4{font-size:15px; margin:22px 0 6px}
.chapter-no{font-family:ui-sans-serif,system-ui,sans-serif; font-size:11px; letter-spacing:.18em; color:var(--muted); font-weight:700}
p{margin:0 0 14px}
ul,ol{margin:0 0 14px; padding-left:22px}
li{margin:3px 0}
a{color:var(--accent)}
blockquote{margin:16px 0; padding:10px 16px; border-left:4px solid var(--accent); background:var(--accent-soft)}
blockquote p:last-child{margin:0}
hr{border:0; border-top:1px solid var(--rule); margin:28px 0}
mark{background:var(--mark); color:inherit}
code{font-family:ui-monospace,"Cascadia Mono",Consolas,monospace; font-size:.88em; background:var(--code-bg); padding:1px 5px; border-radius:4px}
pre{background:var(--code-bg); border:1px solid var(--rule); border-radius:8px; padding:14px 16px; overflow-x:auto; line-height:1.6; font-size:13.5px}
pre code{background:none; padding:0; font-size:inherit}
.codehilite{background:var(--code-bg); border:1px solid var(--rule); border-radius:8px; overflow-x:auto}
.codehilite pre{border:0; margin:0; background:none}
.tablewrap{overflow-x:auto; margin:0 0 18px}
table{border-collapse:collapse; width:100%; font-size:14.5px; font-family:ui-sans-serif,system-ui,sans-serif}
th,td{border:1px solid var(--rule); padding:8px 10px; text-align:left; vertical-align:top}
th{background:var(--accent-soft); font-weight:700}
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
  main{padding:26px 18px 90px}
}
@media print{
  aside,#top,.nav{display:none}
  .layout{display:block}
  main{max-width:none; padding:0}
  pre,table,.admonition{break-inside:avoid}
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
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&display=swap" rel="stylesheet">
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
            f'<div class="chapter-no">CHAPTER {c["no"]:02d}</div>'
            f'<h1>{html.escape(c["title"])}</h1>{c["html"]}{"".join(nav)}'
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
            f'<div class="chapter-no">ORIGINAL {a["no"]:02d}</div>'
            f'<h1>{html.escape(a["title"])}</h1>{a["html"]}{"".join(nav)}'
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
