#!/usr/bin/env python3
"""강사 배포 「핵심키워드」 PDF 188강 -> 마크다운 장 파일.

PDF에서 뽑은 본문을 그대로 옮깁니다. 내용을 요약하거나 바꾸지 않습니다.
하는 일은 세 가지뿐입니다.

  1. 페이지마다 반복되는 제목·쪽번호 제거
  2. `1.` `1-1.` 같은 번호 제목을 마크다운 제목으로 승격
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

H2 = re.compile(r"^(\d{1,2})\.\s+(.+)$")          # 1. 제목
H3 = re.compile(r"^(\d{1,2}-\d{1,2})\.\s+(.+)$")  # 1-1. 제목


def classify(title: str) -> str:
    for name, pat in RULES:
        if re.search(pat, title, re.I):
            return name
    return "리눅스 서버"  # 남는 것은 기본 명령어 계열이었습니다


def clean(text: str, doc_title: str) -> list[str]:
    """페이지 머리말·쪽번호를 걷어 내고 줄 목록을 돌려줍니다."""
    out: list[str] = []
    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            if out and out[-1] != "":
                out.append("")
            continue
        # 페이지마다 반복되는 문서 제목
        if line.strip() == doc_title.strip():
            continue
        # 제목이 잘려 들어간 경우 (마지막 페이지에서 자주 발생)
        if len(line) > 4 and doc_title.startswith(line.strip()):
            continue
        # 쪽번호만 있는 줄
        if re.fullmatch(r"\d{1,3}", line.strip()):
            continue
        out.append(line)
    # 앞뒤 공백 줄 정리
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return out


def _looks_like_table(block: list[str]) -> bool:
    """PDF 표에서 칸 구분이 풀린 덩어리인지 판정합니다.

    표 칸은 짧고 문장 부호로 끝나지 않습니다. 어느 칸이 어느 열이었는지는
    복원할 수 없으므로 **열을 지어내지 않고** 줄 단위 목록으로만 바꿉니다.
    """
    if len(block) < 4:
        return False
    short = sum(1 for b in block if len(b.strip()) <= 30)
    ends = sum(1 for b in block if b.strip().endswith(("다.", "요.", "다", ".", "!", "?")))
    return short / len(block) >= 0.7 and ends / len(block) <= 0.3


def _flush(block: list[str], out: list[str]) -> None:
    if not block:
        return
    if _looks_like_table(block):
        out.extend(f"- {b.strip()}" for b in block)
    else:
        out.extend(block)
    out.append("")
    block.clear()


def to_markdown(lines: list[str]) -> list[str]:
    """번호 제목을 마크다운 제목으로 올리고, 표가 풀린 덩어리는 목록으로 바꿉니다.

    글자는 바꾸지 않습니다. 줄을 묶는 방식만 정합니다.
    """
    out: list[str] = []
    block: list[str] = []
    for line in lines:
        s = line.strip()
        m3 = H3.match(s)
        m2 = H2.match(s)
        if m3 or m2:
            _flush(block, out)
            if m3:
                out.append(f"#### {m3.group(1)}. {m3.group(2)}")
            else:
                out.append(f"### {m2.group(1)}. {m2.group(2)}")
            out.append("")
            continue
        if not s:
            _flush(block, out)
            continue
        block.append(line)
    _flush(block, out)
    return out


def main(zip_path: str) -> int:
    z = zipfile.ZipFile(zip_path)
    names = sorted(n for n in z.namelist() if n.lower().endswith(".pdf"))
    if not names:
        print("PDF가 없습니다", file=sys.stderr)
        return 1

    buckets: dict[str, list[tuple[str, str, list[str]]]] = {p: [] for p in PART_ORDER}

    for name in names:
        base = os.path.basename(name)[:-4]
        m = re.match(r"^(\d{3})_(.*)$", base)
        no, title = (m.group(1), m.group(2).strip()) if m else ("---", base)

        doc = fitz.open(stream=z.read(name), filetype="pdf")
        text = "\n".join(p.get_text() for p in doc)
        doc.close()

        body = to_markdown(clean(text, title))
        buckets[classify(title)].append((no, title, body))

    os.makedirs(OUT_DIR, exist_ok=True)
    for old in os.listdir(OUT_DIR):
        if old.endswith(".md"):
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
                f"강사 배포 「핵심키워드」 슬라이드 중 **{chunk[0][0]}~{chunk[-1][0]}강 {len(chunk)}편**입니다.",
                "원문을 그대로 옮겼습니다. 요약하거나 문장을 바꾸지 않았습니다.",
                "",
                "> PDF에서 뽑은 텍스트라 원문의 **표는 칸 구분이 풀려** 항목이 줄마다 나열됩니다.",
                "> 내용은 빠지지 않았으나 표 모양은 복원하지 못했습니다.",
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
