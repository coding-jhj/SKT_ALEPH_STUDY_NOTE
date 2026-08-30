# 📘 SKT ALEPH IT 인프라·보안 학습 교재

GitHub에서 원본 Markdown을 **한 권의 순서**로 읽기 위한 목차입니다. 각 장 지도는 원본 파일, 학습 목적, 앞뒤 이동을 연결합니다.

[← 저장소 첫 화면](../README.md)　·　[📖 HTML 웹 교재](https://coding-jhj.github.io/SKT_ALEPH_STUDY_NOTE/)　·　[🧭 전체 순서표](ORDER.md)

> [!TIP]
> 장 지도는 책의 본문 목차이고, `notes/`·`slides/`는 원문 자료입니다. 먼저 장 지도를 읽고 필요한 실습 블록과 원문으로 내려가십시오.

## 이 책의 흐름

| 부 | 학습 목표 | 장 |
|---|---|---:|
| 00. 시작하기 | 책 사용법, 전체 지도, 과정 개요 | 01–03 |
| 1부. 네트워크·Cisco Packet Tracer | 패킷 흐름부터 IOS·Packet Tracer·라우팅·네트워크 보안까지 | 04–08 |
| 2부. Linux·서버·Windows | Rocky Linux, 서비스 운영, 공유, 로그, Windows Server | 09–15 |
| 3부. DB·웹 | MariaDB, 백업·복제, PHP 원격 연동 | 16–18 |
| 4부. 운영·자동화 | 모니터링, 클라우드 기초, Python 자동화 | 19–20 |
| 5부. 보안·모의해킹 | 네트워크·웹 보안, 도구, 취약점 검증, WAF·CTF | 21–24 |
| 부록·자료 보관 | 상충 정리, 공식 기준, 색인, 용어, 원문 | 25–28 |

## 00. 시작하기

| 순서 | 장 | 장 지도 |
|---:|---|---|
| 01 | 책 사용법 | [읽기](chapters/01-이-책의-사용법.md) |
| 02 | 전체 커리큘럼 지도 | [읽기](chapters/02-커리큘럼-지도.md) |
| 03 | 과정 개요 | [읽기](chapters/03-과정-개요.md) |

## 1부. 네트워크·Cisco Packet Tracer

| 순서 | 장 | 장 지도 |
|---:|---|---|
| 04 | 네트워크·Cisco Packet Tracer | [읽기](chapters/04-Cisco-Packet-Tracer-네트워크-심화.md) |
| 05 | 네트워크 핵심키워드 1 | [읽기](chapters/12-핵심키워드-네트워크-1.md) |
| 06 | 네트워크 핵심키워드 2 | [읽기](chapters/13-핵심키워드-네트워크-2.md) |
| 07 | 네트워크 핵심키워드 3 | [읽기](chapters/14-핵심키워드-네트워크-3.md) |
| 08 | 네트워크 보안 통합 Lab | [읽기](chapters/05-네트워크-보안-통합-Lab.md) |

04장에는 기존 Cisco 실습 기록과 네트워크 개념 원고가 함께 연결됩니다. Packet Tracer 구성은 개념을 읽은 뒤 `show` 명령으로 상태를 확인하면서 진행합니다.

> [!IMPORTANT]
> 네트워크 장은 `주소 체계 → IOS CLI → Switching/VLAN → Routing → 서비스/보안 → 검증` 흐름입니다. 명령어를 먼저 복사하지 말고 토폴로지와 인터페이스 역할부터 확인하십시오.

## 2부. Linux·서버·Windows

| 순서 | 장 | 장 지도 |
|---:|---|---|
| 09 | Rocky Linux 개인 서버 | [읽기](chapters/06-Rocky-Linux-개인-서버.md) |
| 10 | NFS·Samba·SELinux·rsyslog·LogAnalyzer | [읽기](chapters/07-NFS-Samba-SELinux-rsyslog-LogAnalyzer.md) |
| 11 | vi·프로토콜·Windows IIS | [읽기](chapters/08-vi-프로토콜-Windows-IIS.md) |
| 12 | Linux 메모리·커널·MariaDB 계정·Kali | [읽기](chapters/09-Linux-메모리-커널-MariaDB-계정-Kali.md) |
| 13 | Linux 서버 핵심키워드 1 | [읽기](chapters/15-핵심키워드-Linux-서버-1.md) |
| 14 | Linux 서버 핵심키워드 2 | [읽기](chapters/16-핵심키워드-Linux-서버-2.md) |
| 15 | Windows Server 핵심키워드 | [읽기](chapters/17-핵심키워드-Windows-Server.md) |

## 3부. DB·웹

| 순서 | 장 | 장 지도 |
|---:|---|---|
| 16 | MariaDB SQL·백업·복제 | [읽기](chapters/10-MariaDB-SQL-백업-복제.md) |
| 17 | 팀 웹·원격 MariaDB 연동 | [읽기](chapters/11-팀-웹-원격-MariaDB-연동.md) |
| 18 | 데이터베이스 핵심키워드 | [읽기](chapters/18-핵심키워드-데이터베이스.md) |

## 4부. 운영·자동화

| 순서 | 장 | 장 지도 |
|---:|---|---|
| 19 | 모니터링·운영·클라우드 | [읽기](chapters/19-핵심키워드-모니터링-운영.md) |
| 20 | Python·자동화 | [읽기](chapters/20-핵심키워드-Python-자동화.md) |

## 5부. 보안·모의해킹

| 순서 | 장 | 장 지도 |
|---:|---|---|
| 21 | 보안·모의해킹 1 | [읽기](chapters/21-핵심키워드-보안-모의해킹-1.md) |
| 22 | 보안·모의해킹 2 | [읽기](chapters/22-핵심키워드-보안-모의해킹-2.md) |
| 23 | 보안·모의해킹 3 | [읽기](chapters/23-핵심키워드-보안-모의해킹-3.md) |
| 24 | 보안·모의해킹 4 | [읽기](chapters/24-핵심키워드-보안-모의해킹-4.md) |

허가된 실습 대상과 격리된 환경에서만 보안 도구를 실행합니다. 명령 실행 전 대상 범위와 원복 방법을 먼저 기록합니다.

> [!WARNING]
> 보안·모의해킹 장의 명령은 승인된 실습 대상에서만 실행합니다. 외부 시스템에 대한 스캔·공격·인증 우회는 이 교재의 학습 범위가 아닙니다.

## 부록·자료 보관

| 순서 | 자료 | 장 지도 |
|---:|---|---|
| 25 | 중복과 상충 정리 | [읽기](chapters/25-중복과-상충-정리.md) |
| 26 | 공식 문서 대조 | [읽기](chapters/26-원문과-공식-문서-대조.md) |
| 27 | 명령어 색인 | [읽기](chapters/27-명령어-색인.md) |
| 28 | 용어집 | [읽기](chapters/28-용어집.md) |

## 원문·공식 기준

- [제공받은 Markdown 5개 원문](chapters/originals/README.md)
- [공식 출처 목록](chapters/SOURCES.md)
- [목차의 단일 기준 manifest](manifest.json)

원문은 별도 보관 영역에 두었습니다. 장 지도는 학습 순서를 위한 안내이고, 원문은 내용 대조와 출처 확인을 위한 자료입니다.

## 표기

- `✅` 실행·출력 확인
- `⚠️` 실제 오류·함정
- `📘` 공식 문서·표준과 대조
- `확인 필요` 버전·장비 차이로 재검증

Notion에서는 이 구조를 native page, heading, table, callout, code block으로 옮깁니다. HTML 파일을 첨부하거나 embed하지 않습니다.
