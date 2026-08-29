#!/usr/bin/env python3
"""부록 「명령어 색인」 자동 생성.

손으로 유지하면 반드시 낡습니다. 빌드할 때마다 notes/ 를 다시 읽어 만듭니다.
"""
from __future__ import annotations

import io
import os
import re

NOTE_LABEL = {
    "2026-08-18_라우팅-ACL-NAT-VPN.md": "8/18 라우팅",
    "RockyLinux9_개인서버랩.md": "Rocky 서버랩",
    "2026-08-25_NFS-Samba-SELinux-rsyslog.md": "8/25 NFS·Samba",
    "2026-08-27_MariaDB-SQL-백업-복제.md": "8/27 MariaDB",
    "2026-08-28_리눅스메모리-커널-MariaDB계정-Kali.md": "8/28 메모리·계정",
    "2026-08-28_팀웹-원격MariaDB연동.md": "8/28 팀웹",
}

# 명령이 아닌 토큰 — 셸 제어문, 프롬프트, 너무 흔해서 색인 가치가 없는 것
SKIP = {
    "if", "then", "else", "elif", "fi", "for", "while", "do", "done", "case", "esac",
    "exit", "true", "false", "echo", "cd", "sudo", "su", "and", "or", "not",
}

# 시스코 IOS 설정 명령은 리눅스 명령과 성격이 달라 따로 모읍니다.
IOS_HINT = re.compile(
    r"^(interface|router|ip|access-list|network|no|switchport|vlan|enable|line|"
    r"crypto|username|hostname|clock|banner|shutdown|encapsulation|redistribute|"
    r"passive-interface|default-information|standby|show|debug|copy|write|configure)$"
)

PROMPT = re.compile(r"^[\w.@\-\[\]()]*\s*[#$>]\s+")
TOKEN_OK = re.compile(r"^[a-z][a-z0-9._\-]{1,24}$")


def _commands(text: str):
    """코드블록 안의 각 줄에서 첫 명령 토큰을 뽑습니다."""
    in_fence = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence or not stripped:
            continue
        stripped = PROMPT.sub("", stripped)
        if stripped.startswith(("#", "--", "//", "*", "+")):
            continue
        parts = stripped.split()
        if not parts:
            continue
        token = parts[0]
        if token == "sudo" and len(parts) > 1:
            token = parts[1]
        if not TOKEN_OK.match(token) or token in SKIP:
            continue
        yield token


def generate(root: str, read) -> None:
    notes_dir = os.path.join(root, "notes")
    if not os.path.isdir(notes_dir):
        return

    linux: dict[str, dict[str, int]] = {}
    ios: dict[str, dict[str, int]] = {}

    for fn in sorted(os.listdir(notes_dir)):
        if not fn.endswith(".md"):
            continue
        label = NOTE_LABEL.get(fn, fn.replace(".md", ""))
        for token in _commands(read(os.path.join("notes", fn))):
            bucket = ios if IOS_HINT.match(token) else linux
            bucket.setdefault(token, {}).setdefault(label, 0)
            bucket[token][label] += 1

    def table(data: dict[str, dict[str, int]]) -> tuple[list[str], int]:
        rows = [(k, v) for k, v in data.items() if sum(v.values()) >= 2]
        rows.sort(key=lambda kv: (-sum(kv[1].values()), kv[0]))
        lines = ["| 명령 | 나오는 노트 (등장 횟수) |", "|---|---|"]
        for token, where in rows:
            cells = ", ".join(
                f"{lbl} {cnt}" for lbl, cnt in sorted(where.items(), key=lambda x: -x[1])
            )
            lines.append(f"| `{token}` | {cells} |")
        return lines, len(rows)

    linux_rows, n_linux = table(linux)
    ios_rows, n_ios = table(ios)

    out = [
        "# 명령어 색인",
        "",
        "노트의 코드블록에서 뽑은 실행 명령입니다. **빌드할 때마다 다시 만들어지므로**",
        "노트를 고치면 이 표도 따라 바뀝니다. 손으로 고치지 마십시오.",
        "",
        "두 번 이상 나온 것만 실었습니다. 한 번뿐인 것은 오타나 일회성 문자열일 가능성이 큽니다.",
        "",
        f"## 리눅스·셸 명령 ({n_linux}개)",
        "",
        *linux_rows,
        "",
        f"## 시스코 IOS 설정 명령 ({n_ios}개)",
        "",
        "IOS는 `configure terminal` 아래에서 쓰는 설정 언어라 리눅스 명령과 성격이 다릅니다.",
        "따로 모았습니다.",
        "",
        *ios_rows,
        "",
    ]

    path = os.path.join(root, "book", "91-명령어-색인.md")
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"명령어 색인 재생성: 리눅스 {n_linux}개 · IOS {n_ios}개")
