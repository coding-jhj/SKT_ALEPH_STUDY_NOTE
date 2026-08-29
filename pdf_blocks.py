#!/usr/bin/env python3
"""PDF 한 쪽을 제목·본문·코드·표로 나눠 읽고 마크다운으로 바꿉니다.

이 꾸러미의 슬라이드는 글자 크기가 곧 구조입니다. 크기만 보면 무엇이 제목이고
무엇이 코드인지 정확히 갈립니다(188강 전체 동일).

    30pt  쪽마다 반복되는 문서 제목      버림 (장 제목은 파일 이름에서 가져옵니다)
    18pt  대제목  `1. ...`               ###
    15pt  소제목  `1-1. ...`             ####
    12pt  본문                            문단
    10.5pt 표 안 글자                     표에서 처리
    8~9pt DejaVuSansMono  터미널 화면     ``` 코드블록
    7.5pt 머리말·쪽번호                   버림

표는 `find_tables(strategy="lines_strict")`로 찾습니다. 기본값 `lines`는 칸을
그린 선이 아니라 글자 배치까지 선으로 쳐서 없는 열을 만들고 줄바꿈된 칸을
딴 행으로 흘립니다(실측: 4열 5행 표가 6열 7행으로 깨짐).

PDF는 글자의 위치만 담고 있어 어디가 문단이고 어디가 단순 줄바꿈이었는지,
줄바꿈 자리에 공백이 있었는지는 남아 있지 않습니다. 세 규칙으로 복원합니다.

  1. 덩어리(block)가 바뀌면 새 문단, 안에서는 한 줄로 잇는다
  2. 줄이 잘린 자리는 **문서 전체 어휘**로 판단한다
     — 붙여 만든 낱말이 문서 어딘가에 온전히 나오면 붙이고, 아니면 공백을 넣는다
  3. 영문 하이픈 분철은 붙인다
"""
from __future__ import annotations

import re
from collections import Counter

import fitz  # PyMuPDF

SENTENCE_END = ("다.", "요.", "다", ".", ":", "!", "?", ")", "]", ";")

# 어휘 사전을 만들 때 낱말 양끝에서 떼어 낼 문자
STRIP = " \t·,.:;!?()[]{}<>\"'`“”‘’/|"

# 터미널 화면을 그리는 고정폭 글꼴. 크기까지 작으면 코드블록입니다.
MONO = ("Mono", "WenQuanYi", "Courier")

HEAD_MIN = 13.5   # 이보다 크면 제목
TITLE_MIN = 25.0  # 쪽마다 반복되는 문서 제목
NOISE_MAX = 8.0   # 머리말·쪽번호. 코드(8.3pt)보다 작습니다


def cell(value) -> str:
    """표 칸 하나를 마크다운 셀로. 줄바꿈은 <br>, 파이프는 이스케이프."""
    text = (value or "").strip().replace("|", r"\|")
    return re.sub(r"\s*\n\s*", "<br>", text)


def table_to_markdown(rows: list[list]) -> list[str]:
    """find_tables() 결과를 마크다운 표로. 아무 행에도 내용이 없는 열은 뺍니다."""
    rows = [r for r in rows if any((c or "").strip() for c in r)]
    if len(rows) < 2:
        return []
    width = max(len(r) for r in rows)
    rows = [list(r) + [""] * (width - len(r)) for r in rows]
    keep = [i for i in range(width) if any((r[i] or "").strip() for r in rows)]
    if len(keep) < 2:
        return []

    head = [cell(rows[0][i]) for i in keep]
    if not any(head):
        head = [f"열 {i + 1}" for i in range(len(keep))]

    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(keep)]
    for row in rows[1:]:
        out.append("| " + " | ".join(cell(row[i]) for i in keep) + " |")
    return out


def _is_code(spans: list[dict], size: float) -> bool:
    if size >= HEAD_MIN:
        return False
    marked = [s for s in spans if s["text"].strip()]
    return bool(marked) and all(any(m in s["font"] for m in MONO) for s in marked)


def page_items(page) -> list[tuple[float, int, str, object]]:
    """한 쪽을 (세로위치, 덩어리번호, 종류, 내용) 목록으로.

    종류는 table · code · h3 · h4 · para 입니다.
    """
    tables = list(page.find_tables(strategy="lines_strict").tables)
    boxes = [fitz.Rect(t.bbox) for t in tables]
    items: list[tuple[float, int, str, object]] = []

    for table, box in zip(tables, boxes):
        items.append((box.y0, -1, "table", table.extract()))

    for bno, block in enumerate(page.get_text("dict")["blocks"]):
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            rect = fitz.Rect(line["bbox"])
            area = rect.get_area()
            # 표 영역과 절반 넘게 겹치는 줄은 이미 표로 들어갔습니다.
            if area and any(rect.intersects(b) and (rect & b).get_area() / area > 0.5 for b in boxes):
                continue
            size = max(s["size"] for s in spans)
            if size <= NOISE_MAX or size >= TITLE_MIN:
                continue  # 머리말·쪽번호, 그리고 쪽마다 반복되는 문서 제목
            text = "".join(s["text"] for s in line["spans"]).rstrip()
            if _is_code(spans, size):
                kind = "code"
            elif size >= 16.5:
                kind = "h3"
            elif size >= HEAD_MIN:
                kind = "h4"
            else:
                kind = "para"
                text = text.strip()
            if text.strip():
                items.append((rect.y0, bno, kind, text))

    items.sort(key=lambda item: (round(item[0], 1), item[1]))
    return items


def build_vocab(texts: list[str], min_count: int = 2) -> set[str]:
    """문서 전체에서 낱말 사전을 만듭니다.

    줄 끝에서 잘린 낱말인지 판단하는 근거가 됩니다. 한 번만 나온 낱말은
    그 자체가 잘린 조각일 수 있으므로 기본 2회 이상만 담습니다.
    """
    counter: Counter[str] = Counter()
    for text in texts:
        for raw in text.split():
            word = raw.strip(STRIP)
            if len(word) >= 2:
                counter[word] += 1
    return {w for w, c in counter.items() if c >= min_count}


HANGUL_RUN = re.compile(r"^[가-힣]+")

# 낱말 첫머리에 올 수 없는 어미·조사. 줄이 여기서 잘렸다면 앞말에 붙여야 합니다.
ENDINGS = (
    "이다", "입니다", "이며", "이고", "이라", "이란", "인다", "한다", "합니다", "하는", "하고",
    "하여", "되어", "된다", "됩니다", "되는", "에서", "에게", "으로", "까지", "부터", "이나",
    "라도", "지만", "면서", "므로", "처럼", "보다", "마다", "밖에",
)


def _glue(tail: str, head: str, vocab: set[str]) -> bool:
    """줄이 잘린 자리를 붙여야 하는지 판단합니다.

    근거 두 가지입니다.
      1. 붙여 만든 낱말이 문서 어휘에 있으면 붙인다
      2. 뒷조각이 낱말 첫머리에 올 수 없는 어미·조사면 붙인다
    """
    tail_parts, head_parts = tail.split(), head.split()
    if not tail_parts or not head_parts:
        return False
    last = tail_parts[-1].strip(STRIP)
    first = head_parts[0].strip(STRIP)
    if not last or not first:
        return False

    lead = HANGUL_RUN.match(first)
    lead_text = lead.group(0) if lead else first

    if lead_text in ENDINGS:
        return True

    for candidate in (last + first, last + lead_text):
        if candidate in vocab:
            # 앞뒤 모두 홀로 쓰이는 낱말이고 앞이 한 글자면 띄웁니다 ("수 있다")
            return not (len(last) <= 1 and last in vocab and first in vocab)
    return False


def join_wrapped(lines: list[str], vocab: set[str] | None = None) -> str:
    """PDF가 잘라 놓은 줄을 한 문단으로 되붙입니다."""
    vocab = vocab or set()
    out = ""
    for raw in lines:
        piece = raw.strip()
        if not piece:
            continue
        if not out:
            out = piece
        elif out.endswith("-"):                 # 영문 하이픈 분철
            out = out[:-1] + piece
        elif _glue(out, piece, vocab):          # 어절이 통째로 잘린 자리
            out += piece
        else:
            out += " " + piece
    return out


def trim_code(lines: list[str]) -> list[str]:
    """코드블록의 빈 줄과 공통 들여쓰기를 정리합니다. 글자는 바꾸지 않습니다."""
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return []
    pad = min(len(l) - len(l.lstrip(" ")) for l in lines if l.strip())
    return [l[pad:].rstrip() for l in lines]
