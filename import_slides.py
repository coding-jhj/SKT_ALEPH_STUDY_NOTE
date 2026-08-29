#!/usr/bin/env python3
"""강사 배포 「핵심키워드」 PDF 188강 -> 마크다운 장 파일.

PDF에서 뽑은 본문을 그대로 옮깁니다. 내용을 요약하거나 바꾸지 않습니다.
글자 크기로 구조를 알아냅니다(자세한 규칙은 pdf_blocks 참고).

  1. 쪽마다 반복되는 문서 제목·쪽번호 제거
  2. 제목 / 문단 / 코드블록 / 표로 나누기
  3. 주제별로 묶고 한 장이 너무 커지지 않게 나누기

실행: python import_slides.py <핵심키워드 zip 경로>
결과: slides/*.md
"""
from __future__ import annotations

import io
import os
import re
import sys
import zipfile

import fitz  # PyMuPDF

from pdf_blocks import (
    SENTENCE_END,
    build_vocab,
    join_wrapped,
    page_items,
    table_to_markdown,
    trim_code,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "slides")

# 한 장에 넣을 최대 강의 수. 너무 크면 브라우저가 버거워집니다(실측 305KB까지는 문제 없음).
MAX_PER_CHAPTER = 20

# 주제 분류 — 앞 규칙이 이깁니다. 커리큘럼 지도와 같은 규칙을 씁니다.
RULES: list[tuple[str, str]] = [
    ("보안 실습 · 모의해킹", r"DDoS|IDS|IPS|Snort|Suricata|OSSEC|CTF|Nmap|msf|Metasploit|DVWA|XSS|"
     r"SQL Injection|CSRF|WebGoat|OWASP|악성코드|PE |버퍼 오버플로|Set UID|해킹|ISMS-P|WAF|"
     r"ModSecurity|ZAP|Redis|Base64|SSL 취약점|BEAST|Brute Force|Captcha|Command Injection|"
     r"File Inclusion|File Upload|Deface|Natas|beebox|Juice Shop|b374k|ARP|SNMP|WebDAV|XST|"
     r"Heartbleed|Shell Shock|SSRF|XXE|Drupal|인가|취약|리버싱|디스어셈|FLARE|Wazuh|Graylog|"
     r"칼리|모의|플래그|스크립트 파일 분석"),
    ("파이썬 · 자동화", r"파이썬|Tkinter"),
    ("모니터링 · 운영 · 클라우드", r"Zabbix|NMS|PMM|Nagios|GoAccess|보안 솔루션|클라우드|Docker|저장소\(Repository\)"),
    ("데이터베이스", r"MariaDB|리플리케이션|데이터베이스"),
    ("윈도우 서버", r"Windows|IIS|이벤트 뷰어"),
    ("리눅스 서버", r"Rocky|VirtualBox|Apache|APM|PHP|DNS|FTP|vsftpd|NFS|Samba|rsyslog|Syslog|"
     r"LogAnalyzer|권한|VIM|패키지|umask|Salt|PAM|패스워드 정책|우분투|쉘 스크립트|셸|리눅스|"
     r"시스템 로그|웹 Document|존 파일|네임서버|HTTP|파일 조작"),
    ("네트워크", r"VTP|VLAN|트렁|라우터|라우팅|RIP|EIGRP|OSPF|DHCP|ACL|NAT|VPN|IPSec|GRE|IPv6|"
     r"서브넷|TCP|HSRP|L3|GNS3|ZFW|ASAv|PFSense|Wireshark|네트워크|시스코|firewalld|iptables|IT 인프라"),
]
PART_ORDER = [
    "네트워크", "리눅스 서버", "윈도우 서버", "데이터베이스",
    "모니터링 · 운영 · 클라우드", "파이썬 · 자동화", "보안 실습 · 모의해킹",
]
SLUG = {
    "네트워크": "1-네트워크",
    "리눅스 서버": "2-리눅스서버",
    "윈도우 서버": "3-윈도우서버",
    "데이터베이스": "4-데이터베이스",
    "모니터링 · 운영 · 클라우드": "5-모니터링운영",
    "파이썬 · 자동화": "6-파이썬자동화",
    "보안 실습 · 모의해킹": "7-보안모의해킹",
}

def classify(title: str) -> str:
    for name, pat in RULES:
        if re.search(pat, title, re.I):
            return name
    return "리눅스 서버"  # 남는 것은 기본 명령어 계열이었습니다


def main(zip_path: str) -> int:
    z = zipfile.ZipFile(zip_path)
    names = sorted(n for n in z.namelist() if n.lower().endswith(".pdf"))
    if not names:
        print("PDF가 없습니다", file=sys.stderr)
        return 1

    # 1차: 전체 본문을 한 번 읽어 낱말 사전을 만듭니다.
    #      줄 끝에서 잘린 어절을 붙일지 띄울지 판단하는 근거입니다.
    raw_texts: dict[str, str] = {}
    for name in names:
        doc = fitz.open(stream=z.read(name), filetype="pdf")
        raw_texts[name] = chr(10).join(page.get_text() for page in doc)
        doc.close()
    vocab = build_vocab(list(raw_texts.values()))
    print(f"낱말 사전 {len(vocab):,}개")

    buckets: dict[str, list[tuple[str, str, list[str]]]] = {p: [] for p in PART_ORDER}

    for name in names:
        base = os.path.basename(name)[:-4]
        m = re.match(r"^(\d{3})_(.*)$", base)
        no, title = (m.group(1), m.group(2).strip()) if m else ("---", base)

        doc = fitz.open(stream=z.read(name), filetype="pdf")
        body: list[str] = []
        para: list[str] = []      # 이어붙이는 중인 문단의 줄들
        code: list[str] = []      # 이어붙이는 중인 코드블록의 줄들
        para_block = (-1, -1)     # (쪽, 덩어리) — 바뀌면 새 문단

        def flush_para() -> None:
            if not para:
                return
            text = join_wrapped(para, vocab)
            para.clear()
            if not text:
                return
            # 쪽이 넘어가며 문장 도중에 끊긴 것은 앞 문단에 잇습니다.
            if body and body[-1] and not body[-1].rstrip().endswith(SENTENCE_END):
                body[-1] = body[-1].rstrip() + " " + text
                return
            body.append(text)
            body.append("")

        def flush_code() -> None:
            lines = trim_code(code)
            code.clear()
            if not lines:
                return
            body.append("```")
            body.extend(lines)
            body.append("```")
            body.append("")

        for pno, page in enumerate(doc):
            for _, bno, kind, payload in page_items(page):
                if kind != "code":
                    flush_code()
                if kind != "para":
                    flush_para()

                if kind == "table":
                    md = table_to_markdown(payload)
                    if md:
                        body.append("")
                        body.extend(md)
                        body.append("")
                elif kind == "code":
                    code.append(payload)
                elif kind == "para":
                    if (pno, bno) != para_block:
                        flush_para()
                        para_block = (pno, bno)
                    para.append(payload)
                else:
                    body.append(("### " if kind == "h3" else "#### ") + payload.strip())
                    body.append("")
        flush_code()
        flush_para()
        doc.close()
        buckets[classify(title)].append((no, title, body))

    os.makedirs(OUT_DIR, exist_ok=True)
    # 이 스크립트가 만든 파일만 지웁니다. 이미지 슬라이드 판독본처럼
    # 다른 경로로 들어온 장이 같은 폴더에 있습니다.
    prefixes = tuple(SLUG[p] for p in PART_ORDER)
    for old in os.listdir(OUT_DIR):
        if old.endswith(".md") and old.startswith(prefixes):
            os.remove(os.path.join(OUT_DIR, old))

    made: list[tuple[str, int, int]] = []
    for part in PART_ORDER:
        items = buckets[part]
        if not items:
            continue
        chunks = [items[i:i + MAX_PER_CHAPTER] for i in range(0, len(items), MAX_PER_CHAPTER)]
        for idx, chunk in enumerate(chunks, start=1):
            suffix = f"-{idx}" if len(chunks) > 1 else ""
            fname = f"{SLUG[part]}{suffix}.md"
            head = f"핵심키워드 · {part}"
            if len(chunks) > 1:
                head += f" ({idx}/{len(chunks)})"

            lines = [
                f"# {head}",
                "",
            ]
            for no, title, body in chunk:
                lines.append(f"## {no}. {title}")
                lines.append("")
                lines.extend(body)
                lines.append("")
                lines.append("---")
                lines.append("")
            text_out = "\n".join(lines).rstrip() + "\n"
            with io.open(os.path.join(OUT_DIR, fname), "w", encoding="utf-8", newline="\n") as f:
                f.write(text_out)
            made.append((fname, len(chunk), len(text_out)))

    print(f"슬라이드 {len(names)}강 -> 파일 {len(made)}개")
    for fname, cnt, size in made:
        print(f"  {fname:<28} {cnt:>3}강 · {size:>7,}자")
    print(f"  합계 {sum(s for _, _, s in made):,}자")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python import_slides.py <핵심키워드 zip 경로>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
