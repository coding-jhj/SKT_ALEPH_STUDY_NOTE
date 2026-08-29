#!/usr/bin/env python3
"""PDF 한 페이지를 본문과 표로 나눠 읽고 마크다운으로 바꿉니다.

PyMuPDF의 `find_tables()`가 표의 칸 구조를 그대로 돌려줍니다.
표 영역에 걸친 글자는 본문에서 빼야 같은 내용이 두 번 나오지 않습니다.

PDF는 글자의 위치만 담고 있어서, 원래 어디가 문단이고 어디가 단순 줄바꿈이었는지는
남아 있지 않습니다. 아래 두 규칙으로 복원합니다.

  - 문장 부호로 끝나지 않은 채 덩어리가 끊기면(대개 페이지가 넘어간 것) 이어 붙인다
  - 줄바꿈 자리는 공백으로 잇는다 (한글 조판은 대부분 띄어쓰기에서 줄을 바꾼다)
"""
from __future__ import annotations

import re

import fitz  # PyMuPDF

H2 = re.compile(r"^(\d{1,2})\.\s+(.+)$")          # 1. 제목
H3 = re.compile(r"^(\d{1,2}-\d{1,2})\.\s+(.+)$")  # 1-1. 제목

SENTENCE_END = ("다.", "요.", "다", ".", ":", "!", "?", ")", "]", ";")


def cell(value) -> str:
    """표 칸 하나를 마크다운 셀로. 줄바꿈은 <br>, 파이프는 이스케이프."""
    text = (value or "").strip().replace("|", r"\|")
    return re.sub(r"\s*\n\s*", "<br>", text)


def table_to_markdown(rows: list[list]) -> list[str]:
    """find_tables() 결과를 마크다운 표로. 열 수는 원문 그대로 둡니다."""
    rows = [r for r in rows if any((c or "").strip() for c in r)]
    if len(rows) < 2:
        return []
    width = max(len(r) for r in rows)

    head = [cell(c) for c in rows[0]] + [""] * (width - len(rows[0]))
    if not any(head):
        head = [f"열 {i + 1}" for i in range(width)]

    out = ["| " + " | ".join(head) + " |", "|" + "---|" * width]
    for row in rows[1:]:
        cells = [cell(c) for c in row] + [""] * (width - len(row))
        out.append("| " + " | ".join(cells) + " |")
    return out


def page_blocks(page) -> list[tuple[float, str, object]]:
    """한 페이지를 (세로위치, 종류, 내용) 목록으로. 종류는 table 또는 text."""
    tables = list(page.find_tables().tables)
    boxes = [fitz.Rect(t.bbox) for t in tables]
    items: list[tuple[float, str, object]] = []

    for table, box in zip(tables, boxes):
        items.append((box.y0, "table", table.extract()))

    for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
        rect = fitz.Rect(x0, y0, x1, y1)
        area = rect.get_area()
        # 표 영역과 절반 넘게 겹치는 글자 덩어리는 이미 표로 들어갔습니다.
        if area and any(rect.intersects(b) and (rect & b).get_area() / area > 0.5 for b in boxes):
            continue
        if text.strip():
            items.append((y0, "text", text))

    items.sort(key=lambda item: item[0])
    return items


def merge_payloads(blocks: list[str]) -> str:
    """텍스트 덩어리들을 하나의 본문으로 잇습니다.

    덩어리는 대개 문단 하나지만, 페이지가 바뀌면 문장 도중에도 끊깁니다.
    앞 덩어리가 문장 부호로 끝나지 않으면 같은 문단으로 이어 붙입니다.
    """
    paragraphs: list[str] = []
    for block in blocks:
        text = block.strip()
        if not text:
            continue
        if paragraphs and not paragraphs[-1].rstrip().endswith(SENTENCE_END):
            paragraphs[-1] = paragraphs[-1].rstrip() + chr(10) + text
        else:
            paragraphs.append(text)
    return (chr(10) * 2).join(paragraphs)


def join_wrapped(lines: list[str]) -> str:
    """PDF가 잘라 놓은 줄을 한 문단으로 되붙입니다.

    줄바꿈 자리에 원래 공백이 있었는지는 PDF에 남아 있지 않습니다. 한글 조판은
    대부분 띄어쓰기에서 줄을 바꾸므로 공백을 넣어 잇는 쪽을 기본으로 둡니다.
    긴 어절이 통째로 잘린 드문 경우에는 공백이 하나 더 들어갑니다.
    영문 하이픈 분철만 붙여서 잇습니다.
    """
    out = ""
    for raw in lines:
        piece = raw.strip()
        if not piece:
            continue
        if not out:
            out = piece
        elif out.endswith("-"):
            out = out[:-1] + piece
        else:
            out += " " + piece
    return out


def clean_lines(text: str, doc_title: str) -> list[str]:
    """페이지마다 반복되는 문서 제목과 쪽번호를 걷어 냅니다."""
    out: list[str] = []
    title = doc_title.strip()
    for raw in text.split(chr(10)):
        line = raw.strip()
        if not line:
            out.append("")
            continue
        if line == title:
            continue
        if len(line) > 4 and title.startswith(line):
            continue
        if re.fullmatch(r"\d{1,3}", line):
            continue
        out.append(line)
    return out


def text_to_markdown(text: str, doc_title: str) -> list[str]:
    """본문을 제목과 문단으로 나눕니다. 글자는 바꾸지 않습니다."""
    out: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            joined = join_wrapped(buf)
            if joined:
                out.append(joined)
                out.append("")
            buf.clear()

    for line in clean_lines(text, doc_title):
        m3 = H3.match(line)
        m2 = H2.match(line)
        if m3 or m2:
            flush()
            out.append(f"#### {m3.group(1)}. {m3.group(2)}" if m3
                       else f"### {m2.group(1)}. {m2.group(2)}")
            out.append("")
            continue
        if not line:
            flush()
            continue
        buf.append(line)
    flush()
    return out
