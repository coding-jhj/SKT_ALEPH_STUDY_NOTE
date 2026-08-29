<div align="center">

# SKT ALEPH 학습 노트

IT 인프라 · 보안 과정에서 다룬 내용을 한 권으로 묶은 온라인 교재입니다.

### [📖 교재 열기](https://coding-jhj.github.io/SKT_ALEPH_STUDY_NOTE/)

</div>

<br>

## 두 갈래로 되어 있습니다

**수업 노트** — 직접 실습하며 쓴 기록입니다.
실행한 명령, 나온 출력, 실제로 난 에러와 그 원인까지 그대로 남겼습니다.
따라 하면 같은 결과가 나오는 것을 목표로 썼습니다.

**핵심키워드** — 과정에서 배포된 슬라이드 188강의 본문입니다.
요약하지 않고 옮겼습니다. 수업 때 설명이 어떻게 나갔는지 확인하는 용도입니다.

둘이 어긋나는 곳이 있습니다. 부록 「중복과 상충 정리」와
「원문과 공식 문서가 어긋나는 곳」에 모아 뒀습니다.

<br>

## 어디에 무엇이 있나

### 1부 · 네트워크 &nbsp;`04–05`

Packet Tracer로 라우팅부터 방화벽까지. OSPF(Area·Virtual Link·DR/BDR),
ACL 순서와 라인 번호, NAT/PAT, GRE·IPSec VPN, HSRP 게이트웨이 이중화.
5장은 팀 통합 Lab 결과보고서 — 구성 검증부터 FTP 허용·차단까지 실제 검증 절차.

### 2부 · 리눅스 서버 &nbsp;`06–09`

Rocky Linux 9로 서버를 처음부터 올립니다.
VirtualBox 토폴로지 → BIND DNS → APM → NFS·Samba 공유 → SELinux →
rsyslog 로그 중앙 수집 → MariaDB 적재 → LogAnalyzer 웹 조회.
`free`·`sysctl`·`/proc`으로 메모리와 커널 파라미터를 읽는 법, Kali 초기 설정.

> SELinux 컨텍스트, rsyslog 3003 에러처럼 **실제로 막혔던 지점**을 원인과 함께 적었습니다.

### 3부 · 데이터베이스 &nbsp;`10–11`

MariaDB SQL 기초 → 문자셋 → 논리 백업·복원 → 마스터/슬레이브 복제.
계정은 이름이 아니라 `이름@호스트`라는 것, GRANT/REVOKE 권한 설계.
11장은 팀 웹사이트에서 원격 MariaDB로 붙이는 전 과정 — PHP 연동, 회원가입·로그인
데이터 확인, 그 과정에서 난 오류와 해결.

### 핵심키워드 &nbsp;`12–24`

| 분야 | 강 | 장 | 다루는 것 |
|---|---:|---|---|
| 네트워크 | 52 | `12–14` | TCP/UDP·IP 체계, 시스코 CLI, VTP/VLAN, DHCP, OSPF, ACL·NAT·VPN, IPv6, ASAv·ZFW, GNS3, Wireshark |
| 리눅스 서버 | 35 | `15–16` | 설치·패키지·권한, APM, DNS, FTP, NFS·Samba, 셸 스크립트, rsyslog·LogAnalyzer |
| 윈도우 서버 | 6 | `17` | 설치·초기 설정, IIS 웹·FTP, DNS 역할, 이벤트 뷰어, 로컬 보안 정책 |
| 데이터베이스 | 9 | `18` | MariaDB 초기 보안, CRUD, 필드 조작, 리플리케이션 |
| 모니터링 · 운영 | 8 | `19` | Zabbix NMS, PMM, Docker, 저장소, 보안 솔루션 분류, 클라우드 |
| 파이썬 · 자동화 | 4 | `20` | 설치·가상환경, 자동화 예제, Tkinter GUI |
| 보안 실습 · 모의해킹 | 74 | `21–24` | Nmap·Metasploit, DDoS(Hping3), Snort3 IDS/IPS, DVWA·bWAPP·Juice Shop·WebGoat, XSS·SQLi·Command Injection·BOF, 웹셸·ARP 스푸핑, SSL 취약점, ModSecurity WAF, CTF |

### 부록 &nbsp;`25–28`

- **중복과 상충 정리** — 수업 노트와 슬라이드가 다르게 말하는 곳
- **원문과 공식 문서가 어긋나는 곳** — 공식 문서로 대조해 바로잡은 8건
- **명령어 색인** — 리눅스 130개 · 시스코 IOS 10개. 어느 장에 나오는지까지
- **용어집**

<br>

## 찾는 법

| | |
|---|---|
| 🔍 | 사이드바 검색창에 단어를 넣으면 목차가 걸러집니다 |
| 🧭 | 보고 있는 장은 소제목까지 펼쳐지고, 읽는 위치가 따라옵니다 |
| 📇 | 명령어가 기억나는데 어느 장인지 모르겠다면 **27장 명령어 색인** |
| 🗺️ | 188강 중 무엇이 어디로 갔는지는 **2장 커리큘럼 지도** |
| 🖨️ | 인쇄하면 사이드바가 빠지고 본문만 나옵니다 |

<br>

## 본문 표기

| | |
|---|---|
| ✅ | 실행하고 출력까지 확인함 |
| ⚠️ | 실제로 난 오류, 빠지기 쉬운 함정 |
| 📘 | 수업 밖에서 공식 문서로 보강함 |
| ★ | 자주 틀리는 지점 |

출처가 불확실하면 적지 않습니다. 기억으로 채우지 않고 `확인 필요`로 남깁니다.

<br>

---

<details>
<summary><b>🛠 만드는 쪽</b> — 저장소를 고칠 사람만 보면 됩니다</summary>

<br>

### 폴더

```
notes/       수업 노트 — 사람이 쓴 마크다운
slides/      핵심키워드 188강 — PDF 자동 추출 (직접 고치지 마십시오)
book/        사용법 · 커리큘럼 지도 · 부록
docs/        빌드 결과. GitHub Pages가 이 폴더를 서비스합니다

build.py            notes + slides + book  →  docs/*.html
import_slides.py    핵심키워드 PDF zip     →  slides/*.md
pdf_blocks.py       PDF 한 쪽 → 제목·본문·코드·표
make_index.py       부록 「명령어 색인」 자동 생성
```

`notes/`와 `slides/`가 원본, `docs/`는 조립 결과입니다. 같은 내용을 두 곳에 두지 않습니다.

### 빌드

```bash
python build.py
python -m http.server 8899 --bind 127.0.0.1 --directory docs   # 로컬 확인
```

푸시하면 Pages가 1분 안에 반영합니다.

### 수업이 끝날 때마다

```bash
# 1) notes/2026-09-01_주제.md 추가
# 2) build.py 의 ORDER 에 한 줄
# 3) make_index.py 의 NOTE_LABEL 에 짧은 이름 (색인 표기용)
python build.py && git add -A && git commit -m "9/1 수업 노트" && git push
```

`build.py`가 알아서 하는 것 — 장 제목 승격, 한글 앵커 id, 사이드바 목차,
이전/다음 이동, 인쇄 배치, 명령어 색인 재생성.
그리고 **본문의 HTML 태그를 전부 글자로 막습니다.** 노트에 XSS 실습
페이로드가 실려 있어서, 막지 않으면 노트를 여는 순간 실행됩니다.

한 파일로 합치지 않고 장마다 나누는 이유 — 전부 합치면 1MB가 넘어
브라우저가 렌더링하지 못합니다(실측).

### 슬라이드 다시 가져오기

```bash
python import_slides.py "<핵심키워드 zip 경로>" && python build.py
```

PDF에는 무엇이 제목이고 무엇이 코드인지 표시가 없습니다. 이 꾸러미는
**글자 크기가 곧 구조**라서 그것으로 복원합니다.

| 크기 | 정체 | → |
|---|---|---|
| `30pt` | 쪽마다 반복되는 문서 제목 | 버림 |
| `18pt` | 대제목 `1.` | `###` |
| `15pt` | 소제목 `1-1.` | `####` |
| `12pt` | 본문 | 문단 |
| `8~9pt` DejaVuSansMono | 터미널 화면 | 코드블록 |
| `7.5pt` | 머리말 · 쪽번호 | 버림 |

표는 `find_tables(strategy="lines_strict")`. 기본값 `lines`는 칸 선이 아니라
글자 배치까지 선으로 쳐서 4열 5행 표를 6열 7행으로 깨뜨립니다.

줄바꿈은 문서 전체 낱말 사전으로 복원합니다. 붙여 만든 낱말이 문서 어딘가에
온전히 나오면 붙이고, 아니면 공백을 넣습니다.

### 한계

- **그림 없음** — 이 꾸러미 188강 PDF에는 이미지가 0개입니다
- **강의 번호가 건너뜁니다** — 주제별로 묶은 탓. 001~188강 전부 들어 있습니다

</details>
