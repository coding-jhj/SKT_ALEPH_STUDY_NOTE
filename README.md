<div align="center">

# SKT ALEPH STUDY NOTE

### IT 인프라 · 네트워크 · Linux · DB · 보안 실습 교재

한 번 읽고 끝나는 메모가 아니라, **순서대로 읽고 직접 재현하는 한 권의 학습 교재**입니다.

[📖 HTML 웹 교재](https://coding-jhj.github.io/SKT_ALEPH_STUDY_NOTE/)
　·　[📘 Markdown 책](book/README.md)
　·　[🧭 전체 순서](book/ORDER.md)

</div>

<br>

## 먼저 읽기

| 목적 | 바로가기 | 읽는 이유 |
|---|---|---|
| 처음부터 시작 | [Markdown 책 목차](book/README.md) | GitHub에서 장별 Markdown을 책처럼 읽습니다 |
| 네트워크 공부 | [네트워크·Cisco Packet Tracer](book/chapters/04-Cisco-Packet-Tracer-네트워크-심화.md) | 개념, IOS 명령, Packet Tracer, 라우팅·보안 흐름을 연결합니다 |
| 서버 공부 | [Rocky Linux 개인 서버](book/chapters/06-Rocky-Linux-개인-서버.md) | 설치부터 DNS·APM·공유·로그까지 실습합니다 |
| 보안 공부 | [보안·모의해킹 1](book/chapters/21-핵심키워드-보안-모의해킹-1.md) | 네트워크 보안, 웹 취약점, 도구 실습을 단계별로 봅니다 |
| 원문 확인 | [제공 Markdown 5개](book/chapters/originals/README.md) | 변환·편집된 장과 원래 받은 파일을 대조합니다 |

## 전체 학습 여정

```text
00  시작하기
 │
01  네트워크 · Cisco Packet Tracer
 │
02  Linux · 서버 · Windows
 │
03  DB · 웹
 │
04  운영 · 자동화
 │
05  보안 · 모의해킹
 │
부록  상충 정리 · 공식 기준 · 명령어 · 용어
```

각 장은 원본 노트를 다시 복사하지 않고, GitHub에서 바로 열 수 있는 **장 지도**로 연결합니다. 장 지도에서 원문, 코드블록, 앞뒤 이동 경로를 확인할 수 있습니다.

## 1부 · 네트워크 · Cisco Packet Tracer

네트워크는 다음 순서로 읽습니다. 아래 04장은 기존 Cisco 실습 기록과 네트워크 개념 원고를 한 장에 이어 붙인 핵심 장입니다.

1. [네트워크·Cisco Packet Tracer](book/chapters/04-Cisco-Packet-Tracer-네트워크-심화.md) — 패킷 흐름, IPv4, 서브네팅, IOS CLI, 스위칭, 라우팅, DHCP, NAT/PAT, ACL, HSRP, VPN, IPv6
2. [네트워크 핵심키워드 1](book/chapters/12-핵심키워드-네트워크-1.md) — TCP/UDP, 이더넷, IP 체계, 기본 장비
3. [네트워크 핵심키워드 2](book/chapters/13-핵심키워드-네트워크-2.md) — VLAN, VTP, DHCP, OSPF, ACL·NAT·VPN
4. [네트워크 핵심키워드 3](book/chapters/14-핵심키워드-네트워크-3.md) — IPv6, ASAv·ZFW, GNS3, Wireshark
5. [네트워크 보안 통합 Lab](book/chapters/05-네트워크-보안-통합-Lab.md) — 구성 검증, 허용·차단 정책, 결과 기록

실습 명령은 장비 이미지와 IOS 버전에 따라 달라질 수 있습니다. 반드시 `show` 명령으로 현재 상태를 확인하고, 보안 실습은 승인된 격리 환경에서만 실행합니다.

## 2부 · Linux · 서버 · Windows

- [Rocky Linux 개인 서버](book/chapters/06-Rocky-Linux-개인-서버.md)
- [NFS·Samba·SELinux·rsyslog·LogAnalyzer](book/chapters/07-NFS-Samba-SELinux-rsyslog-LogAnalyzer.md)
- [vi·프로토콜·Windows IIS](book/chapters/08-vi-프로토콜-Windows-IIS.md)
- [Linux 메모리·커널·MariaDB 계정·Kali](book/chapters/09-Linux-메모리-커널-MariaDB-계정-Kali.md)
- [Linux 서버 핵심키워드 1](book/chapters/15-핵심키워드-Linux-서버-1.md)
- [Linux 서버 핵심키워드 2](book/chapters/16-핵심키워드-Linux-서버-2.md)
- [Windows Server 핵심키워드](book/chapters/17-핵심키워드-Windows-Server.md)

## 3부 · DB · 웹

- [MariaDB SQL·백업·복제](book/chapters/10-MariaDB-SQL-백업-복제.md)
- [팀 웹·원격 MariaDB 연동](book/chapters/11-팀-웹-원격-MariaDB-연동.md)
- [데이터베이스 핵심키워드](book/chapters/18-핵심키워드-데이터베이스.md)

## 4부 · 운영 · 자동화

- [모니터링·운영·클라우드](book/chapters/19-핵심키워드-모니터링-운영.md)
- [Python·자동화](book/chapters/20-핵심키워드-Python-자동화.md)

## 5부 · 보안 · 모의해킹

- [보안·모의해킹 1](book/chapters/21-핵심키워드-보안-모의해킹-1.md)
- [보안·모의해킹 2](book/chapters/22-핵심키워드-보안-모의해킹-2.md)
- [보안·모의해킹 3](book/chapters/23-핵심키워드-보안-모의해킹-3.md)
- [보안·모의해킹 4](book/chapters/24-핵심키워드-보안-모의해킹-4.md)

Nmap, Metasploit, Snort3, DVWA·bWAPP·Juice Shop·WebGoat, XSS·SQLi·Command Injection·BOF, 웹셸, ARP 스푸핑, SSL, ModSecurity WAF, CTF를 포함합니다. 공격 기법은 허가된 실습 대상과 격리된 네트워크에서만 검증합니다.

## 부록 · 자료 보관

- [책 사용법](book/chapters/01-이-책의-사용법.md)
- [전체 커리큘럼 지도](book/chapters/02-커리큘럼-지도.md)
- [과정 개요](book/chapters/03-과정-개요.md)
- [중복과 상충 정리](book/chapters/25-중복과-상충-정리.md)
- [공식 문서 대조](book/chapters/26-원문과-공식-문서-대조.md)
- [명령어 색인](book/chapters/27-명령어-색인.md) — Linux 135개 · Cisco IOS 14개
- [용어집](book/chapters/28-용어집.md)
- [제공 Markdown 5개 원문](book/chapters/originals/README.md)
- [공식 출처 목록](book/chapters/SOURCES.md)

## 읽는 방법

| 표기 | 뜻 |
|---|---|
| `✅` | 실행과 출력까지 확인한 항목 |
| `⚠️` | 실제 오류 또는 빠지기 쉬운 함정 |
| `📘` | 공식 문서·표준과 대조한 설명 |
| `확인 필요` | 장비·OS·버전에 따라 다시 검증할 항목 |

수업 기록과 공식 기준이 충돌하는 부분은 부록 25·26장에 모았습니다. 모르는 내용을 추측으로 채우지 않고 `확인 필요`로 남깁니다.

## 웹 교재와 Markdown 책

- HTML은 [GitHub Pages 웹 교재](https://coding-jhj.github.io/SKT_ALEPH_STUDY_NOTE/)에서 사이드바, 검색, 소제목 이동, 인쇄용 레이아웃으로 읽습니다.
- Markdown은 [전체 과정 Markdown 책](book/README.md)에서 상대 링크를 따라가며 읽습니다.
- GitHub에는 원본 Markdown을 보존하고, Notion에는 같은 순서의 native page로 옮깁니다. HTML 파일을 Notion에 첨부하지 않습니다.

## 저장소 관리

```text
notes/       직접 작성한 수업·실습 원고
slides/      핵심키워드 188강 Markdown 원고
book/        목차, 장 지도, 공식 출처, 원문 보관
docs/        build.py가 만든 HTML 웹 교재
```

목차의 기준은 [`book/manifest.json`](book/manifest.json)입니다. 장을 추가하거나 순서를 바꿀 때 manifest, Markdown 장 지도, Notion native 계층을 함께 확인합니다.

```bash
python build.py
python -m http.server 8899 --bind 127.0.0.1 --directory docs
```

`python build.py`는 장별 HTML, 원문 보존 HTML 5개, 소제목 앵커, 이전·다음 이동, 명령어 색인을 갱신합니다. 원본 `notes/`와 `slides/`는 직접 덮어쓰지 않습니다.

## Markdown 책 목차

- [전체 과정 Markdown 책 열기](book/README.md)
- [공통 장 순서](book/ORDER.md)
- [제공받은 원문 5개](book/chapters/originals/README.md)
- [공식 출처](book/chapters/SOURCES.md)
