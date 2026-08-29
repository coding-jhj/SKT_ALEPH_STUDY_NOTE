#!/usr/bin/env python3
"""학습 노트 -> 책(HTML) 빌드.

원본 노트는 notes/ 에 그대로 두고 book/ 에는 연결 자료만 둡니다.
같은 내용을 두 곳에 복사하지 않기 위해 ORDER 목록으로 조립만 합니다.

모든 장을 한 파일에 합치면 43만자·1MB가 넘어 브라우저가 렌더링하지 못합니다(실측).
그래서 **장마다 별도 HTML**을 만들고 index.html은 목차만 갖습니다.

실행: python build.py
결과: site/index.html + site/ch01.html ...
"""
from __future__ import annotations

import html
import io
import os
import re
import sys

import markdown

import make_index

ROOT = os.path.dirname(os.path.abspath(__file__))

# 책의 장 순서. (파일경로, 부(部) 제목 또는 None)
ORDER: list[tuple[str, str | None]] = [
    ("book/00-이-책의-사용법.md", "들어가기"),
    ("book/01-커리큘럼-지도.md", None),
    ("slides/0-과정개요-이미지슬라이드.md", None),
    ("notes/2026-08-18_라우팅-ACL-NAT-VPN.md", "1부 · 네트워크"),
    ("notes/네트워크보안-통합Lab-결과보고서.md", None),
    ("notes/RockyLinux9_개인서버랩.md", "2부 · 리눅스 서버"),
    ("notes/2026-08-25_NFS-Samba-SELinux-rsyslog.md", None),
    ("notes/2026-08-27_보강-vi-프로토콜-IIS.md", None),
    ("notes/2026-08-28_리눅스메모리-커널-MariaDB계정-Kali.md", None),
    ("notes/2026-08-27_MariaDB-SQL-백업-복제.md", "3부 · 데이터베이스"),
    ("notes/2026-08-28_팀웹-원격MariaDB연동.md", None),
    ("slides/1-네트워크-1.md", "핵심키워드 · 네트워크"),
    ("slides/1-네트워크-2.md", None),
    ("slides/1-네트워크-3.md", None),
    ("slides/2-리눅스서버-1.md", "핵심키워드 · 리눅스 서버"),
    ("slides/2-리눅스서버-2.md", None),
    ("slides/3-윈도우서버.md", "핵심키워드 · 윈도우 서버"),
    ("slides/4-데이터베이스.md", "핵심키워드 · 데이터베이스"),
    ("slides/5-모니터링운영.md", "핵심키워드 · 모니터링 · 운영"),
    ("slides/6-파이썬자동화.md", "핵심키워드 · 파이썬 · 자동화"),
    ("slides/7-보안모의해킹-1.md", "핵심키워드 · 보안 실습 · 모의해킹"),
    ("slides/7-보안모의해킹-2.md", None),
    ("slides/7-보안모의해킹-3.md", None),
    ("slides/7-보안모의해킹-4.md", None),
    ("book/90-중복과-상충-정리.md", "부록"),
    ("book/91-명령어-색인.md", None),
    ("book/99-용어집.md", None),
]

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


def demote(md_text: str) -> tuple[str, str]:
    """장 제목(첫 h1)을 뽑아내고 나머지 제목 단계를 한 칸 내립니다."""
    title = ""
    out: list[str] = []
    in_fence = False
    for line in md_text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            if level == 1 and not title:
                title = text
                continue
            out.append("#" * min(level + 1, 6) + " " + text)
            continue
        out.append(line)
    return title, "\n".join(out)


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
.toclist .m{color:var(--muted); font-size:12.5px; font-family:ui-sans-serif,system-ui,sans-serif}
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
    make_index.generate(ROOT, read)

    md = markdown.Markdown(extensions=MD_EXT, extension_configs=MD_CFG)
    chapters: list[dict] = []

    for path, part in ORDER:
        if not os.path.exists(os.path.join(ROOT, path)):
            print(f"  건너뜀 (없음): {path}", file=sys.stderr)
            continue
        raw = read(path)
        title, demoted = demote(raw)
        md.reset()
        rendered = md.convert(demoted)
        rendered, items = anchor_headings(rendered)
        rendered = rendered.replace("<table>", '<div class="tablewrap"><table>')
        rendered = rendered.replace("</table>", "</table></div>")
        no = len(chapters) + 1
        chapters.append({
            "no": no,
            "file": f"ch{no:02d}.html",
            "title": title or os.path.basename(path),
            "part": part,
            "html": rendered,
            "items": items,
            "chars": len(raw),
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

    site = os.path.join(ROOT, "site")
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
            f'<li><a href="{c["file"]}"><span class="t">{c["no"]:02d}. {html.escape(c["title"])}</span>'
            f'<span class="m">소제목 {len(c["items"])}개 · {c["chars"]:,}자</span></a></li>'
        )
    toc.append("</ul>")
    with io.open(os.path.join(site, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(page("목차", chapter_list(None), "".join(toc)))

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
            f.write(page(c["title"], chapter_list(c["no"]), body))

    total = sum(c["chars"] for c in chapters)
    biggest = max(os.path.getsize(os.path.join(site, c["file"])) for c in chapters)
    print(f"빌드 완료: index.html + 장 {len(chapters)}개 (가장 큰 장 {biggest // 1024} KB)")
    for c in chapters:
        print(f"  {c['no']:>2}. {c['title'][:50]:<52} 소제목 {len(c['items']):>3}개 · {c['chars']:>7,}자")
    print(f"  합계 {total:,}자")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
