# Rocky Linux 9 개인 서버랩 학습 노트

> **문서 성격**: 4대 가상서버(DNS / Web / NFS / FTP)로 구성한 개인 과제 실습을, 처음부터 끝까지 다시 따라 할 수 있게 정리한 교재입니다.
> **작성 시점**: 2026-08-26 (모든 버전·기본값 정보는 이 날짜 기준. 이후 변경 가능)
> **기준 자료**: 사용자가 제공한 두 건의 실습 대화 기록(실행 결과 포함) + 아래 「33. 공식 참고자료」의 1차 공식 문서
> **대상 OS**: Rocky Linux 9 계열 (RHEL 9 호환)
> **접속 계정**: 실습자는 각 서버에 **root**로 로그인한 상태입니다. 그래서 이 문서의 서버 명령에는 `sudo`를 붙이지 않습니다. 일반 사용자로 실행해야 하는 구간은 별도로 `su - hwanju` 또는 `runuser`로 명시합니다.

---

## 사실 표기 규칙 (문서 전체 공통)

이 노트는 "실제로 확인된 것"과 "안내만 된 것"을 반드시 구분합니다. 각 항목 앞에 다음 표기를 씁니다.

| 표기 | 의미 |
|---|---|
| ✅ **확인됨** | 대화 기록에 실행 결과·출력·성공 메시지가 실제로 남아 있는 항목 |
| 🟡 **안내됨(결과 미확인)** | 명령어나 설정은 제시되었으나, 실행 결과가 기록에 없는 항목 |
| ❓ **확인 필요** | 현재 자료만으로 판단할 수 없는 항목. 추측으로 채우지 않음 |
| 📘 **공식 문서 근거** | Red Hat / rsyslog / Samba / WordPress 등 1차 문서로 검증한 내용 |
| 🧪 **실습 관찰** | 공식 문서에는 없고 이번 실습에서 관찰된 동작 |
| ⚠️ **보안 주의** | 실습에서는 허용되나 운영환경에서는 위험한 설정 |

> **비밀번호 표기**: 이 문서에는 실제 비밀번호를 넣지 않습니다. `[LAB_ROOT_PASSWORD]`, `[HWANJU_PASSWORD]`, `[SAMBA_PASSWORD]`, `[LAB_DB_PASSWORD]`, `[WORDPRESS_DB_PASSWORD]` 자리에 **본인이 정한 값을 직접 입력**하십시오. 어느 위치에 어떤 값을 넣는지는 각 절에서 설명합니다.

---

## 목차

1. [이 과제의 전체 목적](#1-이-과제의-전체-목적)
2. [최종 네트워크 토폴로지](#2-최종-네트워크-토폴로지)
3. [서버별 역할·IP·hostname·접속 정보](#3-서버별-역할iphostname접속-정보)
4. [사용 프로토콜과 포트](#4-사용-프로토콜과-포트)
5. [VirtualBox NAT와 Host-only 네트워크](#5-virtualbox-nat와-host-only-네트워크)
6. [PuTTY 접속과 hostname](#6-putty-접속과-hostname)
7. [Rocky Linux 공통 초기 설정](#7-rocky-linux-공통-초기-설정)
8. [/etc/hosts, DNS resolver, NetworkManager](#8-etchosts-dns-resolver-networkmanager)
9. [BIND DNS 개념과 구축](#9-bind-dns-개념과-구축)
10. [DNS zone 파일 해석](#10-dns-zone-파일-해석)
11. [DNS 검증 명령어](#11-dns-검증-명령어)
12. [Apache Web Server](#12-apache-web-server)
13. [HTTP와 HTTPS](#13-http와-https)
14. [OpenSSL 자체 서명 인증서](#14-openssl-자체-서명-인증서)
15. [PHP와 Apache 연동](#15-php와-apache-연동)
16. [MariaDB와 SQL](#16-mariadb와-sql)
17. [Samba와 Windows 공유](#17-samba와-windows-공유)
18. [SELinux context와 troubleshooting](#18-selinux-context와-troubleshooting)
19. [NFS Server](#19-nfs-server)
20. [NFS Client와 /etc/fstab](#20-nfs-client와-etcfstab)
21. [root_squash와 UID/GID](#21-root_squash와-uidgid)
22. [vsftpd FTP](#22-vsftpd-ftp)
23. [SFTP와 SSH](#23-sftp와-ssh)
24. [rsyslog 원격 로그](#24-rsyslog-원격-로그)
25. [LogAnalyzer](#25-loganalyzer)
26. [중앙 로그 흐름](#26-중앙-로그-흐름)
27. [홈페이지 대시보드](#27-홈페이지-대시보드)
28. [WordPress 설치](#28-wordpress-설치)
29. [실제 과제 진행 상태](#29-실제-과제-진행-상태)
30. [오류·원인·해결책 표](#30-오류원인해결책-표)
31. [최종 검증 체크리스트](#31-최종-검증-체크리스트)
32. [제출용 캡처 목록](#32-제출용-캡처-목록)
33. [공식 참고자료](#33-공식-참고자료)
34. [부록: 잘못된 명령과 올바른 명령 비교](#34-부록-잘못된-명령과-올바른-명령-비교)

---

## 1. 이 과제의 전체 목적

이 과제는 **가상머신 4대로 소규모 사내 네트워크를 통째로 구성**해 보는 것이 목적입니다. 단일 서버에 모든 것을 몰아넣지 않고 역할을 나눈 이유가 핵심입니다.

| 학습 목표 | 어떤 서비스로 배우는가 |
|---|---|
| 이름 해석(name resolution)의 원리 | BIND DNS — IP가 아니라 도메인으로 서로를 부르게 만든다 |
| 웹 서비스 스택 구축 | Apache + PHP + MariaDB (LAMP) |
| 파일 공유의 두 계열 | Windows 계열 = Samba(SMB), UNIX 계열 = NFS |
| 파일 전송 프로토콜 | FTP(vsftpd)와 SFTP(SSH subsystem)의 차이 |
| 중앙 로그 수집 | rsyslog 원격 전송 + LogAnalyzer 웹 뷰어 |
| 리눅스 보안 모델 | SELinux context / boolean, NFS root_squash, 방화벽 |
| 애플리케이션 배포 | WordPress를 기존 사이트와 분리해 서브디렉터리에 설치 |

**설계상의 핵심 아이디어 하나**: `nfs.kload81.com`을 FTP 서버가 `/mnt/nfs`로 마운트하고, vsftpd의 `local_root`를 그 `/mnt/nfs`로 지정합니다. 그러면 **FTP로 업로드한 파일이 실제로는 NFS 서버의 디스크에 저장**됩니다. 즉 "전송 프로토콜"과 "저장 위치"를 분리하는 구조를 실습하게 됩니다. 이 구조 때문에 뒤에서 `root_squash`와 UID/GID 일치 문제가 반드시 등장합니다.

---

## 2. 최종 네트워크 토폴로지

```text
                     ┌──────────────────────────────┐
                     │  Windows 호스트 PC            │
                     │  Ethernet     192.168.16.40  │  ← 실제 사내/공유기 LAN
                     │  VBox Host-Only 192.168.16.1 │  ← 가상 네트워크 게이트웨이
                     │  브라우저 / PuTTY / 탐색기     │
                     └───────────────┬──────────────┘
                                     │ Host-Only Adapter (192.168.16.0/24)
     ┌───────────────┬───────────────┼───────────────┬────────────────┐
     │               │               │               │                │
┌────┴─────┐   ┌─────┴─────┐   ┌─────┴──────┐  ┌─────┴──────┐         │
│  dns     │   │   web     │   │   nfs      │  │   ftp      │         │
│ .16.77   │   │ .16.131   │   │ .16.136    │  │ .16.137    │         │
│ BIND     │   │ httpd     │   │ nfs-server │  │ vsftpd     │         │
│          │   │ PHP/Maria │   │ /srv/nfs/  │  │ sshd(SFTP) │         │
│          │   │ Samba     │   │   hwanju   │  │ NFS client │         │
│          │   │LogAnalyzer│   │            │  │ /mnt/nfs   │         │
└────┬─────┘   └─────┬─────┘   └─────┬──────┘  └─────┬──────┘         │
     │               ▲               │ NFS export    │                │
     │  rsyslog UDP  │               └───────────────┘ mount          │
     └───────────────┤                               ┌────────────────┘
                     │  rsyslog UDP 514  ◀───────────┘
                     │
              /var/log/remote.log + /var/log/messages
                     │
              LogAnalyzer (Diskfile 소스)
```

읽는 법:

- **모든 VM은 Host-Only 어댑터 하나로 같은 192.168.16.0/24에 있습니다.** 그래서 서로 IP로 직접 통신합니다.
- **인터넷(dnf 패키지 설치, WordPress 다운로드)은 NAT 어댑터로 나갑니다.** 즉 VM마다 어댑터가 2개인 구성이 일반적입니다(5장 참고).
- **로그는 한 방향**입니다: dns / nfs / ftp → web(.131). Web 서버는 자기 로그 + 남의 로그를 함께 가집니다.
- **NFS는 반대 방향**입니다: nfs(.136)가 서버, ftp(.137)가 클라이언트입니다. 이 방향을 헷갈리면 `exportfs`를 클라이언트에서 치는 실수를 하게 됩니다.

---

## 3. 서버별 역할·IP·hostname·접속 정보

### 3-1. 최종 확정 환경 (이 문서의 기준)

| VirtualBox VM 이름 | Linux hostname | IP | 주요 역할 | 확인 근거 |
|---|---|---|---|---|
| HwanjuLinux | `dns` | 192.168.16.77 | BIND DNS (`kload81.com` 권한 서버), rsyslog 송신 | ✅ 확인됨 |
| HwanjuLinux 복제1 | `web` | 192.168.16.131 | Apache HTTP/HTTPS, PHP 8.1.32, MariaDB 10.5.29, Samba, LogAnalyzer 5.0.2, rsyslog 수신 | ✅ 확인됨 |
| HwanjuLinux 복제2 | `nfs` | 192.168.16.136 | NFS 서버 (`/srv/nfs/hwanju` export), rsyslog 송신 | ✅ 확인됨 |
| HwanjuLinux 복제3 | `ftp` | 192.168.16.137 | vsftpd, sshd(SFTP), NFS 클라이언트(`/mnt/nfs`), rsyslog 송신 | ✅ 확인됨 |

공통 기준값:

| 항목 | 값 |
|---|---|
| 도메인 | `kload81.com` |
| 권한 DNS 서버 | `192.168.16.77` |
| 리눅스 실습 계정 | `hwanju` |
| hwanju UID / GID | `2001` / `2001` (**4대 전부 동일해야 함** — 21장) |
| Windows 호스트 Ethernet | 192.168.16.40 |
| Windows VirtualBox Host-Only 어댑터 | 192.168.16.1 |

### 3-2. ⚠️ 초기 예시 IP와 최종 실제 IP의 구분

**이 부분을 반드시 구분해서 기억하십시오.** 실습 초반에는 아직 VM 정보가 없어서 아래와 같은 **가상의 예시 주소**로 설명이 진행되었습니다.

| 역할 | 초기 예시 IP (❌ 실제 아님) | 최종 실제 IP (✅ 사용할 값) |
|---|---|---|
| DNS | 192.168.16.81 | **192.168.16.77** |
| Web | 192.168.16.82 | **192.168.16.131** |
| NFS | 192.168.16.83 | **192.168.16.136** |
| FTP | 192.168.16.84 | **192.168.16.137** |

> **왜 문제가 되는가**
> 초기 예시 IP가 들어간 설정을 그대로 복사해 붙이면 다음이 전부 깨집니다.
> - zone 파일의 A 레코드 → 존재하지 않는 호스트를 가리킴
> - `named.conf`의 `listen-on` → 서버에 없는 주소라 named가 뜨지 못함
> - `/etc/exports`의 클라이언트 주소 → 실제 클라이언트가 거부됨
> - `pasv_address` → FTP passive 모드 데이터 연결 실패
>
> **점검 방법**: 설정을 끝낸 뒤 4대 전 서버에서 아래를 실행해 `.81`~`.84`가 하나도 안 나오는지 확인하십시오.
>
> ```bash
> grep -rn '192\.168\.16\.8[1-4]' /etc/named.conf /var/named/ /etc/exports /etc/samba/smb.conf /etc/vsftpd/vsftpd.conf /etc/rsyslog.conf /etc/rsyslog.d/ /etc/hosts 2>/dev/null
> ```
>
> 아무 출력도 없으면 정상입니다. (실행 서버: **4대 모두**)

### 3-3. PuTTY 저장 세션 정리표

| PuTTY Saved Session 이름 | Host Name (or IP address) | Port | 접속 후 프롬프트(정상) |
|---|---|---|---|
| `rocky-dns` | `192.168.16.77` | 22 | `[root@dns ~]#` |
| `rocky-web` | `192.168.16.131` | 22 | `[root@web ~]#` |
| `rocky-nfs` | `192.168.16.136` | 22 | `[root@nfs ~]#` |
| `rocky-ftp` | `192.168.16.137` | 22 | `[root@ftp ~]#` |

저장 방법: PuTTY 첫 화면에서 Host Name에 IP 입력 → Saved Sessions에 이름 입력 → **Save**. 다음부터는 이름 더블클릭.

---

## 4. 사용 프로토콜과 포트

| 서비스 | 프로토콜/포트 | 실행 서버 | firewalld 서비스명 | 브라우저로 접속? |
|---|---|---|---|---|
| SSH / SFTP | TCP 22 | 전 서버 | `ssh` (기본 허용) | ❌ 아니오 (PuTTY/WinSCP) |
| DNS | UDP 53, TCP 53 | dns .77 | `dns` | ❌ 아니오 |
| HTTP | TCP 80 | web .131 | `http` | ✅ 예 |
| HTTPS | TCP 443 | web .131 | `https` | ✅ 예 |
| FTP 제어 | TCP 21 | ftp .137 | `ftp` | ❌ 아니오 (FileZilla/`ftp`) |
| FTP passive 데이터 | TCP 40000–40010 | ftp .137 | 포트 직접 개방 | ❌ 아니오 |
| SMB (Samba) | TCP 445 | web .131 | `samba` | ❌ 아니오 (파일 탐색기 UNC) |
| NetBIOS (nmbd, 선택) | UDP 137/138, TCP 139 | web .131 | `samba` 에 포함 | ❌ 아니오 |
| NFS | TCP 2049 (NFSv4) | nfs .136 | `nfs`, (`rpc-bind`,`mountd`는 v3 병용 시) | ❌ 아니오 |
| MariaDB | TCP 3306 (localhost 전용 권장) | web .131 | 개방하지 않음 ⚠️ | ❌ 아니오 |
| rsyslog 원격 | **UDP 514** | 수신: web .131 | 포트 직접 개방 `514/udp` | ❌ 아니오 |
| LogAnalyzer | HTTP 80 (`/loganalyzer/`) | web .131 | `http` | ✅ 예 |
| WordPress | HTTP 80 (`/wordpress/`) | web .131 | `http` | ✅ 예 |

> **가장 자주 하는 착각**: "서버에 올렸으니 크롬 주소창에 치면 나오겠지."
> **브라우저로 여는 것은 HTTP/HTTPS 뿐입니다.** FTP·SFTP·NFS·SMB는 각각 전용 클라이언트로 접속합니다. 이 과제에서 크롬으로 여는 대상은 **홈페이지, LogAnalyzer, WordPress 세 가지뿐**입니다.

방화벽 상태 확인 (실행 서버: 각 서버):

```bash
firewall-cmd --state
firewall-cmd --list-all
```

정상 예상 결과: `running`이 출력되고, 해당 서버에 필요한 service/port가 `services:` 또는 `ports:` 줄에 보입니다.
실패 시 확인: `systemctl status firewalld --no-pager`

---

## 5. VirtualBox NAT와 Host-only 네트워크

### 5-1. 두 어댑터의 역할

| 어댑터 종류 | 방향 | 용도 | 이 과제에서 |
|---|---|---|---|
| **NAT** | VM → 인터넷 (단방향) | `dnf` 패키지 설치, WordPress 다운로드 | 필요 |
| **Host-Only Adapter** | VM ↔ Windows 호스트 ↔ 다른 VM | PuTTY 접속, 서버 간 통신 | 필수 |

- **NAT만 있으면**: 인터넷은 되지만 Windows에서 PuTTY로 VM에 못 들어갑니다(포트 포워딩을 따로 하지 않는 한).
- **Host-Only만 있으면**: VM끼리·호스트와는 통신되지만 `dnf install`이 안 됩니다.
- 그래서 **어댑터 2개(NAT + Host-Only)** 구성이 실습의 표준입니다.

VM에서 어댑터 확인 (실행 서버: 각 서버):

```bash
ip -brief addr
nmcli device status
ip route
```

정상 예상 결과: 인터페이스 두 개가 보이고, 하나에 `192.168.16.x/24`가, `ip route`의 `default via`는 NAT 쪽 게이트웨이(보통 `10.0.2.2`)를 가리킵니다.

### 5-2. ⚠️ 이 실습 환경의 실제 위험 요소 — 대역 중복

기록된 사실:

- Windows **실제 Ethernet**: `192.168.16.40`
- Windows **VirtualBox Host-Only 어댑터**: `192.168.16.1`

즉 **물리 LAN과 가상 Host-Only 네트워크가 둘 다 `192.168.16.0/24`** 입니다.

| 항목 | 설명 |
|---|---|
| 왜 위험한가 | 같은 목적지 대역에 경로가 둘이 되어 Windows가 어느 인터페이스로 보낼지 라우팅 메트릭에 따라 결정합니다. 우연히 동작할 수 있지만 재현성이 없습니다. |
| 어떤 증상으로 나타나는가 | 어떤 날은 `ping 192.168.16.131`이 되고 어떤 날은 안 됨, 특정 IP만 물리 LAN 장비와 충돌 |
| 권장 설계 📘 | Host-Only는 물리 LAN과 **겹치지 않는 대역**(예: `192.168.56.0/24` — VirtualBox 기본값)으로 분리 |
| 이번 과제에서는 | 과제가 `192.168.16.x`를 요구한다면 **주소를 임의로 바꾸지 마십시오.** 대신 이 위험을 문서에 기록하고, 라우팅 우선순위를 확인합니다. |

Windows에서 경로 확인 (실행 위치: **Windows 명령 프롬프트**):

```cmd
route print -4
ipconfig /all
```

`192.168.16.0` 대상 경로가 두 줄 이상 나오고 Metric이 다르면 대역 중복이 실재하는 것입니다. ❓ **확인 필요** — 이번 대화에는 `route print` 결과가 없어서 실제 우선순위는 확인되지 않았습니다.

---

## 6. PuTTY 접속과 hostname

### 6-1. `localhost` 혼동 정리

실습 중 "PuTTY에 `localhost`라고 뜨는데 서버가 잘못된 것 아닌가?"라는 혼동이 있었습니다. **아닙니다.**

| 보이는 곳 | 정체 | 신뢰도 |
|---|---|---|
| PuTTY **창 제목** (`root@localhost: ~`) | 서버가 보낸 터미널 타이틀 문자열. hostname이 기본값(`localhost.localdomain`)이면 이렇게 보입니다 | 참고용 |
| Windows 작업표시줄 이름 | 위와 같음 | 참고용 |
| **셸 프롬프트** `[root@web ~]#` | 셸이 실제 hostname으로 만든 문자열 | 신뢰 가능 |
| `hostname` / `hostnamectl` 출력 | 커널·systemd가 보유한 실제 hostname | **가장 확실** |

즉 **접속이 잘못된 것이 아니라, 리눅스 hostname을 아직 안 바꾼 상태**였던 것입니다.

### 6-2. hostname 확인과 변경

실행 서버: **각 서버(4대 각각)**

```bash
hostname
hostnamectl status
```

정상 예상 결과 (변경 전): `localhost.localdomain`
변경 (각 서버에서 자기 이름 하나만 실행):

```bash
hostnamectl set-hostname dns      # 192.168.16.77 에서
hostnamectl set-hostname web      # 192.168.16.131 에서
hostnamectl set-hostname nfs      # 192.168.16.136 에서
hostnamectl set-hostname ftp      # 192.168.16.137 에서
```

변경 후 현재 셸의 프롬프트를 갱신:

```bash
exec bash
```

> `exec bash`는 재부팅이나 재접속 없이 **현재 셸을 새 셸로 교체**해 프롬프트 문자열을 다시 만들게 하는 명령입니다. hostname 자체는 `hostnamectl` 시점에 이미 바뀌어 있습니다. PuTTY 창 제목은 재접속해야 갱신될 수 있습니다.

정상 예상 결과: 프롬프트가 `[root@web ~]#` 형태로 바뀝니다.
실패 시 확인:

```bash
hostnamectl status
cat /etc/hostname
```

> ⚠️ **VirtualBox 복제 VM 주의**: 복제 직후에는 4대의 hostname이 모두 같습니다. hostname을 바꾸지 않으면 뒤의 rsyslog 중앙 로그에서 **어느 서버가 보낸 로그인지 구분되지 않습니다.** 실제로 원격 로그가 `nfs nfs-forward-test: ...`, `ftp ftp-forward-test: ...`로 서버 이름과 함께 찍힌 것은 hostname을 제대로 설정했기 때문입니다.

### 6-3. PuTTY 접속 절차

1. PuTTY 실행 → **Host Name (or IP address)** 에 **서버 IP**를 입력 (예: `192.168.16.131`). `localhost`를 넣으면 Windows 자기 자신에 접속하려다 실패합니다.
2. Port `22`, Connection type `SSH`
3. Saved Sessions에 이름 입력 후 **Save**
4. Open → 계정 `root` → 비밀번호 `[LAB_ROOT_PASSWORD]` 입력 (입력해도 화면에 아무 것도 안 보이는 것이 정상)

실패 시 확인 (Windows 명령 프롬프트):

```cmd
ping 192.168.16.131
```

응답이 없으면 리눅스 쪽에서:

```bash
ip -brief addr
systemctl status sshd --no-pager
firewall-cmd --list-all
```

---

## 7. Rocky Linux 공통 초기 설정

4대 서버에 공통으로 적용하는 기본 작업입니다. 실행 서버: **4대 모두 (root)**

### 7-1. 고정 IP 설정 (NetworkManager / nmcli)

Rocky Linux 9는 네트워크를 **NetworkManager**가 관리합니다. RHEL 9부터 `network-scripts`(`ifcfg-*`)는 기본으로 제공되지 않으므로 `nmcli`를 씁니다. 📘

현재 연결 이름 확인:

```bash
nmcli connection show
nmcli device status
```

Host-Only 어댑터에 해당하는 연결 이름(예: `enp0s8`)을 확인한 뒤 고정 IP 지정 — **web 서버(.131) 예시**:

```bash
nmcli connection modify enp0s8 \
  ipv4.method manual \
  ipv4.addresses 192.168.16.131/24 \
  ipv4.gateway 192.168.16.1 \
  ipv4.dns "192.168.16.77" \
  connection.autoconnect yes

nmcli connection up enp0s8
```

바꿔 넣어야 할 값:

| 자리 | 넣을 값 |
|---|---|
| `enp0s8` | `nmcli device status`에서 확인한 **Host-Only 쪽 인터페이스 이름** |
| `192.168.16.131/24` | 그 서버의 IP (dns=.77 / web=.131 / nfs=.136 / ftp=.137) |
| `ipv4.gateway` | Host-Only 어댑터 주소 `192.168.16.1` (Host-Only 전용 어댑터라면 게이트웨이를 비워도 됩니다) |
| `ipv4.dns` | 사내 DNS `192.168.16.77` |

정상 예상 결과: `Connection successfully activated` 후 `ip -brief addr`에 해당 IP가 보입니다.
실패 시 확인:

```bash
nmcli -f ipv4 connection show enp0s8
journalctl -u NetworkManager -n 30 --no-pager
```

> **NAT 어댑터에는 고정 IP를 주지 마십시오.** NAT는 DHCP(`ipv4.method auto`) 그대로 두어야 인터넷이 나갑니다.

### 7-2. resolv.conf는 직접 편집하지 않는다

`/etc/resolv.conf`는 NetworkManager가 **덮어씁니다.** DNS 서버를 바꾸려면 위처럼 `nmcli connection modify ... ipv4.dns`로 바꾸고 `nmcli connection up`을 해야 영구 적용됩니다.

```bash
cat /etc/resolv.conf
```

정상 예상 결과: `nameserver 192.168.16.77` 줄이 보입니다.

### 7-3. 시간 동기화 · 패키지 상태 기록

```bash
timedatectl
timedatectl set-timezone Asia/Seoul
chronyc sources
```

> ⚠️ **`dnf update` 주의**: 패키지 일괄 업데이트는 PHP/MariaDB/Samba의 동작을 바꿔 실습을 깨뜨릴 수 있습니다. 업데이트 전에 현재 상태를 반드시 기록하십시오.
>
> ```bash
> rpm -qa --qf '%{NAME} %{VERSION}-%{RELEASE}\n' | sort > /root/pkg-baseline-$(date +%F).txt
> ```
>
> 또한 VM 스냅샷을 먼저 찍는 것을 권장합니다 (VirtualBox → 스냅샷 → 만들기).

---

## 8. `/etc/hosts`, DNS resolver, NetworkManager

### 8-1. 이름 해석의 순서

리눅스에서 `web.kload81.com`이라는 이름이 IP로 바뀌는 경로는 **NSS(Name Service Switch)** 가 정합니다.

```bash
cat /etc/nsswitch.conf | grep '^hosts'
```

일반적인 출력: `hosts:      files dns myhostname`

읽는 법:

| 항목 | 의미 |
|---|---|
| `files` | `/etc/hosts` 파일을 **먼저** 본다 |
| `dns` | 없으면 `/etc/resolv.conf`의 nameserver에 질의한다 |
| `myhostname` | 자기 자신의 hostname을 해석한다 |

즉 `/etc/hosts`에 잘못된 줄이 있으면 **DNS가 아무리 정상이어도 그 잘못된 값이 이깁니다.** DNS 문제를 디버깅할 때 `/etc/hosts`를 먼저 보는 이유입니다.

### 8-2. `/etc/hosts` 최소 구성

실행 서버: **4대 모두**

```bash
cat /etc/hosts
```

기본 내용(지우지 말 것):

```text
127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
```

> **DNS 서버가 살아 있다면 `/etc/hosts`에 서버 목록을 중복해 넣을 필요는 없습니다.** 다만 DNS 장애 시에도 서버끼리 이름으로 통신해야 한다면 아래처럼 추가할 수 있습니다. 이 경우 **DNS zone 파일과 값이 어긋나면 매우 찾기 어려운 버그**가 되므로, 둘 중 하나만 관리하는 편이 안전합니다.

```text
192.168.16.77    dns.kload81.com   dns
192.168.16.131   web.kload81.com   web   www.kload81.com
192.168.16.136   nfs.kload81.com   nfs
192.168.16.137   ftp.kload81.com   ftp
```

### 8-3. `getent` — 실제로 시스템이 어떻게 해석하는지 보는 명령

❌ 실습 중 나온 잘못된 명령:

```bash
getnet hosts web.kload81.com
```

출력: `-bash: getnet: command not found`

✅ 올바른 명령:

```bash
getent hosts web.kload81.com
```

정상 예상 결과:

```text
192.168.16.131  web.kload81.com
```

| 명령 | 무엇을 보는가 |
|---|---|
| `getent hosts <이름>` | **NSS 전체 경로**(`/etc/hosts` → DNS 순서)를 거친 최종 결과. 애플리케이션이 실제로 받는 값과 같음 |
| `dig <이름>` | **DNS만** 질의. `/etc/hosts`는 무시 |
| `nslookup <이름>` | DNS 질의 (대화형/간이 도구) |

> **디버깅 요령**: `dig`는 되는데 프로그램은 엉뚱한 IP로 간다 → `getent hosts`로 확인하십시오. 십중팔구 `/etc/hosts`에 낡은 줄이 남아 있습니다.

---

## 9. BIND DNS 개념과 구축

실행 서버: **dns (192.168.16.77)**

### 9-1. 설치와 서비스

```bash
dnf install -y bind bind-utils
systemctl enable --now named
systemctl status named --no-pager
firewall-cmd --permanent --add-service=dns
firewall-cmd --reload
```

📘 RHEL 9 공식 문서 기준으로 패키지는 `bind`(서버) + `bind-utils`(`dig`, `nslookup` 등 도구)이고 서비스 이름은 `named`입니다. 방화벽 서비스명은 `dns`(TCP/UDP 53)입니다.

정상 예상 결과: `Active: active (running)`
실패 시 확인:

```bash
systemctl status named --no-pager -l
journalctl -u named -n 50 --no-pager
named-checkconf
```

### 9-2. `/etc/named.conf` — 반드시 이해해야 하는 구조

`/etc/named.conf`는 크게 **`options` 블록 1개 + `zone` 블록 여러 개**로 이루어집니다.

```conf
options {
        listen-on port 53 { 127.0.0.1; 192.168.16.77; };
        listen-on-v6 port 53 { ::1; };
        directory       "/var/named";
        dump-file       "/var/named/data/cache_dump.db";
        statistics-file "/var/named/data/named_stats.txt";
        memstatistics-file "/var/named/data/named_mem_stats.txt";
        secroots-file   "/var/named/data/named.secroots";
        recursing-file  "/var/named/data/named.recursing";

        allow-query     { localhost; 192.168.16.0/24; };
        recursion       yes;
        allow-recursion { localhost; 192.168.16.0/24; };

        forwarders      { 8.8.8.8; 8.8.4.4; };
        forward         first;

        dnssec-validation yes;

        managed-keys-directory "/var/named/dynamic";
        geoip-directory "/usr/share/GeoIP";
        pid-file "/run/named/named.pid";
        session-keyfile "/run/named/session.key";
        include "/etc/crypto-policies/back-ends/bind.config";
};
```

각 줄 읽는 법:

| 지시자 | 의미 | 이 실습에서 넣을 값 |
|---|---|---|
| `listen-on port 53` | named가 **어느 IP로 들어오는 질의를 받을지**. 기본값은 `127.0.0.1`뿐이라 외부에서 못 씁니다 | `127.0.0.1; 192.168.16.77;` ← **실제 DNS 서버 IP** |
| `allow-query` | 질의를 허용할 클라이언트 | `localhost; 192.168.16.0/24;` |
| `recursion` / `allow-recursion` | 이 서버가 다른 도메인까지 대신 찾아줄지 | 사내망만 `yes` ⚠️ 인터넷에 열면 DNS 증폭 공격에 악용됩니다 |
| `forwarders` | 내가 모르는 도메인(예: `google.com`)을 대신 물어볼 상위 DNS | `8.8.8.8; 8.8.4.4;` |
| `forward first` | 먼저 forwarder에게 묻고, 실패하면 직접 루트부터 찾음 (`forward only`는 forwarder만 사용) | `first` |
| `directory "/var/named"` | zone 파일의 **기준 디렉터리**. zone 블록의 `file "..."`은 이 경로 기준 상대경로 | 그대로 |
| `dnssec-validation` | 상위 DNS 응답의 서명 검증 | `yes` 유지 권장 |

> ### ⚠️ `options` 블록은 **정확히 하나만** 있어야 합니다
> 설정을 이어 붙이다 보면 `options { ... };` 를 두 번 쓰는 실수가 나옵니다. BIND는 이를 문법 오류로 처리하고 named가 기동하지 않습니다.
> 확인:
> ```bash
> grep -n '^options' /etc/named.conf
> ```
> 출력이 **한 줄**이어야 정상입니다.

### 9-3. ✅ 실제로 발생한 오류 — `zone "."` 안에 사용자 zone을 넣은 문제

```text
오류/증상:
  zone ./IN: NS 'dns.kload81.com' has no address records
  zone ./IN: not loaded due to errors
  _default/./IN: bad zone

원인:
  루트 힌트 zone인 zone "." 블록 안에 kload81.com 설정(NS/A 등)을 섞어 넣었다.
  zone "." 은 "인터넷 루트 서버 목록"을 캐시로 읽어들이는 특수 zone이며,
  사용자의 도메인과는 전혀 별개의 블록이다.

먼저 확인할 것:
  /etc/named.conf 에서 zone "." 블록과 zone "kload81.com" 블록이 분리되어 있는가?

실행 서버: dns (192.168.16.77)

명령어:
  grep -n 'zone' /etc/named.conf
  named-checkconf
  named-checkconf -z

정상 결과:
  named-checkconf 는 아무 것도 출력하지 않는다 (무소식이 정상)
  named-checkconf -z 는 zone kload81.com/IN: loaded serial <숫자> 를 출력한다

실패하면 다음 확인:
  journalctl -u named -n 50 --no-pager
  named-checkzone kload81.com /var/named/kload81.com.zone

주의할 점:
  zone "." 의 file "named.ca" 는 bind 패키지가 설치해 주는 루트 힌트 파일이다.
  직접 수정하지 않는다.
```

**올바른 분리 형태** — 두 블록은 완전히 독립입니다:

```conf
zone "." IN {
        type hint;
        file "named.ca";
};

zone "kload81.com" IN {
        type master;
        file "kload81.com.zone";
        allow-update { none; };
};
```

| 블록 | `type` | 의미 |
|---|---|---|
| `zone "."` | `hint` | 인터넷 루트 서버 힌트. 내 도메인과 무관 |
| `zone "kload81.com"` | `master` | **내가 이 도메인의 권한(authoritative) 서버**라는 선언 |
| `allow-update { none; }` | — | 동적 DNS 업데이트 금지 (실습·보안상 권장) |

> **역방향(reverse) zone**은 이번 실습에서 구성하지 않았습니다. 그래서 `nslookup` 결과의 `서버: Unknown`이 나타납니다 (11장 참고). 필요하면 `zone "16.168.192.in-addr.arpa"`를 별도로 추가합니다. 🟡 **안내됨(결과 미확인)**

---

## 10. DNS zone 파일 해석

파일 위치: `/var/named/kload81.com.zone` (실행 서버: **dns .77**)

```dns
$TTL 86400
@       IN      SOA     dns.kload81.com. root.kload81.com. (
                        2026082601      ; Serial
                        3600            ; Refresh
                        1800            ; Retry
                        604800          ; Expire
                        86400 )         ; Minimum TTL

@       IN      NS      dns.kload81.com.

dns     IN      A       192.168.16.77
web     IN      A       192.168.16.131
nfs     IN      A       192.168.16.136
ftp     IN      A       192.168.16.137

@       IN      A       192.168.16.131
www     IN      A       192.168.16.131
samba   IN      A       192.168.16.131
log     IN      A       192.168.16.131
```

### 10-1. 한 줄씩 읽는 법

| 요소 | 의미 | 실수하기 쉬운 점 |
|---|---|---|
| `$TTL 86400` | 레코드 기본 캐시 수명(초) | 값이 크면 수정해도 클라이언트가 오래 옛 값을 씁니다. 실습 중엔 300 정도로 낮춰도 됩니다 |
| `@` | zone 이름 자체(`kload81.com.`)를 뜻하는 축약 | — |
| `SOA` | 이 zone의 시작 권한 레코드 | 첫 필드=주 네임서버, 둘째=관리자 메일(`root@kload81.com` → `root.kload81.com.`) |
| **`Serial`** | zone 파일의 버전 번호 | **수정할 때마다 반드시 증가**시켜야 합니다. 관례: `YYYYMMDDnn` |
| `Refresh/Retry/Expire` | 보조(slave) DNS가 갱신을 확인하는 주기 | 이 실습은 master 1대라 실질 영향 적음 |
| `Minimum TTL` | 부정 응답(NXDOMAIN) 캐시 시간 | — |
| `NS` | 이 zone의 네임서버 | NS로 지정한 이름은 **반드시 A 레코드가 있어야** 합니다 (없으면 `has no address records` 오류) |
| `A` | 이름 → IPv4 주소 | 오른쪽에 IP, 왼쪽에 호스트명 |
| 끝의 마침표 `.` | FQDN(절대 이름) 표시 | `dns.kload81.com` 처럼 **점을 빼면** BIND가 `dns.kload81.com.kload81.com.` 으로 해석합니다. 가장 흔한 실수입니다 |
| `www`, `samba`, `log` | 같은 IP를 가리키는 추가 이름 | CNAME 대신 A로 둬도 무방합니다 |

### 10-2. SOA Serial을 반드시 올려야 하는 이유

BIND는 zone 파일을 다시 읽을 때 **Serial 번호를 보고 "바뀌었는지" 판단**합니다. 내용을 고쳐도 Serial이 그대로면 캐시/보조 서버가 갱신을 무시할 수 있습니다.

```bash
# 수정 → serial 증가 → 문법검사 → 반영
vi /var/named/kload81.com.zone
named-checkzone kload81.com /var/named/kload81.com.zone
systemctl reload named
```

정상 예상 결과 (`named-checkzone`):

```text
zone kload81.com/IN: loaded serial 2026082601
OK
```

### 10-3. 파일 권한과 SELinux

```bash
ls -lZ /var/named/kload81.com.zone
chown root:named /var/named/kload81.com.zone
chmod 640 /var/named/kload81.com.zone
restorecon -v /var/named/kload81.com.zone
```

정상 SELinux 타입: `named_zone_t` (또는 `named_conf_t`). 📘 `restorecon`이 `Relabeled ...`를 출력하면 **정상적으로 고쳐졌다는 뜻**이지 오류가 아닙니다 (18장).

### 10-4. `reload`와 `restart`의 차이

| 명령 | 동작 | 언제 |
|---|---|---|
| `systemctl reload named` | named 프로세스를 유지한 채 설정/zone만 다시 읽음. 캐시 유지, 서비스 중단 없음 | **zone 파일만 고쳤을 때** |
| `systemctl restart named` | 프로세스를 죽였다 다시 시작. 캐시 소실, 짧은 중단 | `named.conf`의 `options`/`listen-on` 등 기동 파라미터를 고쳤을 때 |

> 실습에서는 `restart`로도 문제가 없지만, 운영 서버에서는 `reload`를 우선합니다.

---

## 11. DNS 검증 명령어

### 11-1. 리눅스 쪽 검증

실행 서버: **dns .77 자신 + 나머지 서버 어디서든**

```bash
named-checkconf                                              # named.conf 문법만
named-checkconf -z                                           # zone 로딩까지 시뮬레이션
named-checkzone kload81.com /var/named/kload81.com.zone      # zone 파일 문법
dig @192.168.16.77 www.kload81.com
dig @192.168.16.77 kload81.com NS
dig @192.168.16.77 google.com                                # forwarder 동작 확인
getent hosts web.kload81.com
```

| 명령 | 검사 대상 | 정상 결과 |
|---|---|---|
| `named-checkconf` | `/etc/named.conf` **문법** | 출력 없음 |
| `named-checkconf -z` | 문법 + **zone 파일 실제 로딩** | `zone kload81.com/IN: loaded serial ...` |
| `named-checkzone` | 지정한 zone 파일 하나 | `OK` |
| `dig @서버 이름` | 그 서버에 직접 질의 | `ANSWER SECTION`에 A 레코드 |
| `getent hosts` | NSS 전체 경로 | IP + 이름 |

`dig` 출력에서 봐야 할 곳:

```text
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 12345
;; flags: qr aa rd ra; QUERY: 1, ANSWER: 1, ...

;; ANSWER SECTION:
www.kload81.com.  86400  IN  A  192.168.16.131
```

| 표시 | 의미 |
|---|---|
| `status: NOERROR` | 정상 응답 |
| `status: NXDOMAIN` | 그런 이름이 없음 → zone 파일에 레코드 누락 |
| `status: SERVFAIL` | 서버가 zone을 못 읽음 → `named-checkconf -z`로 확인 |
| **`aa` 플래그** | authoritative answer. 이 서버가 **권한 서버**임을 뜻함 |
| `ANSWER: 0` | 응답 레코드 없음 |

### 11-2. Windows 쪽 검증과 8.8.8.8 문제 ✅ 실제 발생

실행 위치: **Windows 명령 프롬프트**

```cmd
nslookup kload81.com 192.168.16.77
```
→ ✅ **성공했습니다.** 이는 **DNS 서버를 강제로 지정**한 테스트이며, "BIND 서버 자체는 정상"이라는 증거입니다.

```cmd
nslookup kload81.com
```
→ ✅ **실패했습니다.** 이 명령은 **Windows에 설정된 기본 DNS**를 씁니다. 기록된 `ipconfig /all` 결과:

| 어댑터 | IP | 설정된 DNS |
|---|---|---|
| 실제 Ethernet | 192.168.16.40 | 8.8.8.8, 8.8.4.4 |
| VirtualBox Host-Only | 192.168.16.1 | 192.168.16.77, 8.8.8.8 |

Google Public DNS(8.8.8.8)는 인터넷에 없는 사설 도메인 `kload81.com`을 알 리가 없으므로 실패가 **정상 동작**입니다.

```text
오류/증상:
  nslookup kload81.com  →  실패 / 응답 없음 / 존재하지 않는 도메인
  nslookup kload81.com 192.168.16.77  →  성공

원인:
  Windows가 질의를 보낸 기본 DNS가 8.8.8.8(구글)이었다.
  사설 도메인은 사내 DNS(192.168.16.77)만 알고 있다.

먼저 확인할 것:
  어느 어댑터가 이 질의의 경로로 선택되는가? 그 어댑터의 DNS는 무엇인가?

실행 위치: Windows 명령 프롬프트

명령어:
  ipconfig /all
  route print -4
  nslookup kload81.com 192.168.16.77

정상 결과:
  서버 지정 질의는 A 레코드를 반환한다.

실패하면 다음 확인:
  리눅스 dns 서버에서
    systemctl is-active named
    ss -lunp | grep ':53'
    firewall-cmd --list-all

주의할 점:
  ipconfig /flushdns 는 DNS 캐시를 지우는 명령이지, DNS 서버 주소를 바꾸는 명령이 아니다.
```

### 11-3. Windows 기본 DNS를 어디에 설정할 것인가 — 신중하게

| 선택지 | 장점 | 위험 |
|---|---|---|
| **Host-Only 어댑터에만** 192.168.16.77 설정 | 사내 도메인 조회 가능, 인터넷은 기존 DNS 유지 | 두 어댑터가 같은 대역이라 **어느 쪽이 선택될지 라우팅에 달림** (5-2 참고) ❓ 확인 필요 |
| Windows **전체 기본 DNS**를 192.168.16.77로 | 확실히 사내 도메인 해석됨 | 인터넷 도메인도 전부 BIND를 거칩니다. **BIND의 `forwarders` 설정이 반드시 정상**이어야 인터넷이 끊기지 않습니다 |
| 아무 것도 안 바꾸고 `nslookup ... 192.168.16.77`로만 검증 | 안전 | 브라우저로 `http://www.kload81.com` 접속은 안 됩니다 |

> **권장 절차**: (1) BIND의 `forwarders { 8.8.8.8; 8.8.4.4; };`가 동작하는지 `dig @192.168.16.77 google.com`으로 먼저 확인 → (2) 그 다음에 Windows DNS를 192.168.16.77로 변경 → (3) 인터넷과 사내 도메인이 **둘 다** 되는지 확인.

캐시 정리:

```cmd
ipconfig /flushdns
```

### 11-4. `서버: Unknown` 표시의 의미

```text
서버:    Unknown
Address: 192.168.16.77

이름:    kload81.com
Address: 192.168.16.131
```

- 위쪽 `Unknown`은 **DNS 서버 자신의 이름을 역방향 조회(PTR)** 하지 못했다는 뜻입니다. reverse zone(`in-addr.arpa`)을 만들지 않았기 때문입니다.
- 아래쪽 `이름 / Address`가 나왔다면 **정방향 A 레코드 조회는 성공한 것**입니다.
- 즉 이 메시지는 **오류가 아니며**, 과제 요구사항에 역방향 조회가 없다면 그대로 두어도 됩니다.

### 11-5. Chrome Secure DNS troubleshooting

브라우저에서만 `www.kload81.com`이 안 열린다면, 크롬의 **보안 DNS(DNS-over-HTTPS)** 가 시스템 DNS를 우회했을 가능성이 있습니다.

- 확인: 크롬 `설정 → 개인정보 보호 및 보안 → 보안 → 보안 DNS 사용` 항목의 현재 값 확인
- **처음부터 무조건 끄지 마십시오.** 먼저 `nslookup`·`ping`으로 OS 레벨은 정상인지 확인하고, OS는 되는데 크롬만 안 될 때 이 항목을 의심합니다.
- 임시 검증: 시크릿 창 또는 다른 브라우저(Edge)에서 같은 주소를 열어 비교합니다.

🧪 **실습 관찰** — 이번 대화에서 크롬 Secure DNS가 원인이었다는 결과는 **확인되지 않았습니다.** 가능성 있는 원인으로만 기록합니다.

---

## 12. Apache Web Server

실행 서버: **web (192.168.16.131)**

### 12-1. 설치·기동·방화벽

```bash
dnf install -y httpd
systemctl enable --now httpd
systemctl status httpd --no-pager

firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
firewall-cmd --list-all
```

✅ **확인됨**: 대화 기록상 web 서버의 `httpd`는 **active** 상태였습니다.

📘 RHEL 9 공식 문서는 방화벽을 `--add-port=80/tcp`, `--add-port=443/tcp`로 여는 예를 보여줍니다. firewalld의 미리 정의된 서비스 `http`/`https`를 쓰는 것도 동일한 결과이며 가독성이 좋습니다.

정상 예상 결과: `Active: active (running)` 이고 `firewall-cmd --list-all`의 `services:` 줄에 `http https`가 포함됩니다.

실패 시 확인:

```bash
httpd -t                       # 설정 문법 검사
journalctl -u httpd -n 50 --no-pager
ss -lntp | grep -E ':80|:443'
```

### 12-2. 주요 경로

| 경로 | 용도 |
|---|---|
| `/etc/httpd/conf/httpd.conf` | 메인 설정 |
| `/etc/httpd/conf.d/*.conf` | 추가 설정 (`ssl.conf`, `php.conf` 등) |
| `/var/www/html/` | 기본 DocumentRoot |
| `/var/log/httpd/access_log` | 접속 로그 |
| `/var/log/httpd/error_log` | 오류 로그 (문제 생기면 **여기부터**) |

### 12-3. 테스트 페이지

```bash
echo '<h1>kload81.com web server OK</h1>' > /var/www/html/index.html
curl -s http://localhost/ | head
curl -s -I http://192.168.16.131/
```

정상 예상 결과: `HTTP/1.1 200 OK`
실패 시 확인:

```bash
ls -lZ /var/www/html/index.html          # SELinux 타입이 httpd_sys_content_t 인가
tail -20 /var/log/httpd/error_log
```

> `/var/www/html` 아래에 파일을 새로 만들면 대부분 자동으로 `httpd_sys_content_t`가 붙습니다. 다른 곳에서 `mv`로 옮겨 왔다면 원래 타입이 따라오므로 `restorecon -Rv /var/www/html`을 실행하십시오.

---

## 13. HTTP와 HTTPS

| 항목 | HTTP | HTTPS |
|---|---|---|
| 포트 | TCP 80 | TCP 443 |
| 암호화 | 없음 (평문) | TLS로 암호화 |
| Apache 모듈 | 기본 | `mod_ssl` 필요 |
| 설정 파일 | `httpd.conf` / `conf.d/*.conf` | `/etc/httpd/conf.d/ssl.conf` |
| 인증서 | 불필요 | 서버 인증서 + 개인키 필요 |
| 이 실습 | ✅ 확인됨 (httpd active) | 🟡 안내됨 — 브라우저 접속 성공 화면은 기록에 없음 |

```bash
dnf install -y mod_ssl
systemctl restart httpd
ss -lntp | grep ':443'
```

`mod_ssl`을 설치하면 `/etc/httpd/conf.d/ssl.conf`가 함께 설치되고 443 리스너가 활성화됩니다.

---

## 14. OpenSSL 자체 서명 인증서

실행 서버: **web (.131)**

### 14-1. 개인키 + 자체 서명 인증서 생성

```bash
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout /etc/pki/tls/private/kload81.com.key \
  -out    /etc/pki/tls/certs/kload81.com.crt \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=kload81 Lab/CN=www.kload81.com" \
  -addext "subjectAltName=DNS:www.kload81.com,DNS:kload81.com,DNS:web.kload81.com,IP:192.168.16.131"

chown root:root /etc/pki/tls/private/kload81.com.key
chmod 600 /etc/pki/tls/private/kload81.com.key
```

옵션 해설:

| 옵션 | 의미 |
|---|---|
| `-x509` | CSR이 아니라 **인증서 자체**를 바로 만든다 = 자체 서명 |
| `-nodes` | 개인키에 암호를 걸지 않는다 (걸면 httpd 시작 때마다 암호 입력 필요) |
| `-newkey rsa:2048` | 2048비트 RSA 키를 새로 생성 |
| `-days 365` | 유효기간 |
| `-subj` | 대화형 질문을 건너뛰고 주체 정보를 한 줄로 지정. **`CN`에 실제 접속 도메인**을 넣습니다 |
| `-addext subjectAltName` | 현대 브라우저는 CN이 아니라 **SAN**을 봅니다. 접속에 쓸 이름을 모두 넣으십시오 |

📘 RHEL 9 공식 문서 기준 파일 위치: 개인키 `/etc/pki/tls/private/`, 인증서 `/etc/pki/tls/certs/`, 개인키 권한 `chmod 600`.

### 14-2. `ssl.conf` 반영

`/etc/httpd/conf.d/ssl.conf`의 `<VirtualHost _default_:443>` 안에서 아래 항목을 **찾아 수정**합니다 (파일을 통째로 지우지 마십시오):

```apache
ServerName www.kload81.com:443
SSLCertificateFile      /etc/pki/tls/certs/kload81.com.crt
SSLCertificateKeyFile   /etc/pki/tls/private/kload81.com.key
```

검사 후 반영:

```bash
httpd -t
systemctl restart httpd
curl -k -I https://192.168.16.131/
openssl s_client -connect 192.168.16.131:443 -servername www.kload81.com </dev/null 2>/dev/null | openssl x509 -noout -subject -dates
```

정상 예상 결과: `Syntax OK` → `HTTP/1.1 200 OK` → 인증서의 subject와 유효기간 출력
실패 시 확인:

```bash
tail -30 /var/log/httpd/error_log
ls -lZ /etc/pki/tls/private/kload81.com.key
```

### 14-3. ⚠️ 브라우저 경고는 "정상"입니다

자체 서명 인증서는 공인 CA가 보증하지 않으므로 크롬은 **"이 연결은 비공개 연결이 아닙니다 (NET::ERR_CERT_AUTHORITY_INVALID)"** 를 표시합니다.

| 구분 | 자체 서명 | 공인 인증서 |
|---|---|---|
| 발급자 | 나 자신 | 신뢰된 CA (Let's Encrypt 등) |
| 브라우저 경고 | 발생 | 없음 |
| 암호화 강도 | **동일** | 동일 |
| 신원 보증 | 없음 | 있음 |
| 용도 | 실습·내부망 | 공개 서비스 |

실습에서는 `고급 → 계속 진행`으로 넘어가면 됩니다. **운영 환경에서는 공인 인증서를 사용하십시오.**

---

## 15. PHP와 Apache 연동

실행 서버: **web (.131)**

### 15-1. ✅ 실제 확인된 버전과 그 의미

- 이 실습 서버의 PHP: **8.1.32** ✅ 확인됨
- 📘 RHEL 9 공식 문서 기준: **기본 `php` 패키지는 PHP 8.0**, 8.1과 8.2는 **모듈 스트림**으로 제공됩니다.

| 목표 버전 | 설치 명령 |
|---|---|
| PHP 8.0 (기본) | `dnf install php` |
| **PHP 8.1** | `dnf module install php:8.1` |
| PHP 8.2 | `dnf module install php:8.2` |

즉 이 실습에서 PHP 8.1이 깔려 있다는 것은 **모듈 스트림을 8.1로 전환했다는 뜻**입니다. 이는 LogAnalyzer 5.x가 **PHP 8.1 이상을 요구**하기 때문에 필요한 조치였습니다 (25장). 📘

버전 전환이 필요할 때:

```bash
php -v
dnf module list php
dnf module reset php
dnf module enable php:8.1 -y
dnf module install php:8.1 -y
systemctl restart php-fpm httpd
php -v
```

정상 예상 결과: `PHP 8.1.x (cli) ...`
실패 시 확인:

```bash
dnf module list php --enabled
journalctl -u php-fpm -n 30 --no-pager
```

### 15-2. RHEL 9에서 Apache는 mod_php가 아니라 php-fpm으로 동작합니다 📘

RHEL 9/Rocky 9에는 **mod_php가 없습니다.** `php` 모듈의 `common` 프로파일이 `php-fpm`을 함께 설치하고, Apache는 `/etc/httpd/conf.d/php.conf`를 통해 FastCGI로 php-fpm에 넘깁니다.

그래서 **PHP 설정을 바꾸면 httpd만 재시작해서는 반영되지 않습니다.**

```bash
systemctl enable --now php-fpm
systemctl restart php-fpm httpd
systemctl is-active php-fpm httpd
```

### 15-3. 동작 확인

```bash
cat > /var/www/html/info.php <<'EOF'
<?php phpinfo(); ?>
EOF
curl -s http://localhost/info.php | grep -m1 -o 'PHP Version [0-9.]*'
```

정상 예상 결과: `PHP Version 8.1.32`
실패 시 확인 (HTML 대신 PHP 소스가 그대로 보인다면 PHP 연동이 안 된 것):

```bash
ls /etc/httpd/conf.d/php.conf
systemctl status php-fpm --no-pager
tail -20 /var/log/httpd/error_log
```

> ⚠️ **확인이 끝나면 `info.php`는 반드시 삭제하십시오.** 서버 경로·모듈·버전 등 공격에 쓰일 정보를 그대로 노출합니다.
>
> ```bash
> rm -f /var/www/html/info.php
> ```

---

## 16. MariaDB와 SQL

실행 서버: **web (.131)**

### 16-1. 설치와 확인

```bash
dnf install -y mariadb-server
systemctl enable --now mariadb
systemctl status mariadb --no-pager
mariadb --version
```

✅ **확인됨**: MariaDB **10.5.29**, 서비스 **active**.
📘 RHEL 9 공식 문서 기준으로 **10.5가 RHEL 9의 기본(초기) 스트림**이므로 이 버전은 정상입니다. (10.11은 RHEL 9.4부터, 11.8은 9.8부터 모듈 스트림으로 제공)

### 16-2. 보안 초기화

```bash
mariadb-secure-installation
```

대화형 질문과 권장 답:

| 질문 | 권장 | 이유 |
|---|---|---|
| Enter current password for root | (초기엔 그냥 Enter) | 최초 설치 시 비어 있음 |
| Switch to unix_socket authentication? | `Y` | root는 OS root만 접속하게 하는 것이 안전 |
| Change the root password? | `Y` → `[LAB_ROOT_PASSWORD]` 와 **다른** DB 전용 값 사용 권장 | — |
| Remove anonymous users? | `Y` | 익명 접속 차단 |
| **Disallow root login remotely?** | **`Y`** ⚠️ | root 원격 로그인은 절대 허용하지 마십시오 |
| Remove test database? | `Y` | 불필요 |
| Reload privilege tables now? | `Y` | 즉시 반영 |

### 16-3. ✅ 실제 발생한 SQL 문법 오류

```text
오류/증상:
  create database labdb character utf8mb4 collate utf8mb4_unicode_ci;
  → ERROR 1064 (42000): You have an error in your SQL syntax ...

원인:
  문자셋 지정 구문은 CHARACTER SET (두 단어) 이다. character 한 단어만 쓰면 문법 오류.

먼저 확인할 것:
  구문에 SET 키워드가 빠져 있는지

실행 서버: web (.131), mariadb 클라이언트 안에서

명령어(올바른 문법):
  CREATE DATABASE labdb
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

정상 결과:
  Query OK, 1 row affected

실패하면 다음 확인:
  SHOW DATABASES;
  SELECT @@version;

주의할 점:
  세미콜론(;)을 빼먹으면 프롬프트가 -> 로 바뀌며 계속 입력을 기다린다. 세미콜론 입력 후 Enter.
```

📘 MariaDB 공식 문법:

```text
CREATE [OR REPLACE] DATABASE [IF NOT EXISTS] db_name
    [[DEFAULT] CHARACTER SET [=] charset_name]
    [[DEFAULT] COLLATE [=] collation_name]
```

`CHARACTER SET`은 **두 단어**입니다.

### 16-4. 실습 DB와 사용자 생성

```sql
-- 실행 서버: web (.131) / mariadb -u root -p 접속 후
CREATE DATABASE labdb
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'labuser'@'localhost' IDENTIFIED BY '[LAB_DB_PASSWORD]';

GRANT ALL PRIVILEGES ON labdb.* TO 'labuser'@'localhost';

FLUSH PRIVILEGES;

SHOW DATABASES;
SHOW GRANTS FOR 'labuser'@'localhost';
```

> `[LAB_DB_PASSWORD]` 자리에 **본인이 정한 DB 비밀번호**를 따옴표 안에 넣습니다. 이 값은 문서·HTML·공개 저장소 어디에도 남기지 마십시오.

각 구문의 역할:

| 구문 | 역할 |
|---|---|
| `CREATE DATABASE` | 빈 데이터베이스(스키마) 생성 |
| `CREATE USER 'labuser'@'localhost'` | 계정 생성. **`'사용자'@'호스트'` 두 부분이 합쳐져야 하나의 계정** |
| `GRANT ALL PRIVILEGES ON labdb.*` | `labdb` 안의 모든 테이블에 대한 전체 권한 부여. `*.*`(전체 DB)로 주지 마십시오 |
| `FLUSH PRIVILEGES` | 권한 테이블을 다시 읽어 즉시 반영. `GRANT`는 보통 자동 반영되지만 직접 테이블을 수정했을 때 필요 |

**`'user'@'localhost'`의 의미**:

| 표기 | 접속 가능 위치 | 안전도 |
|---|---|---|
| `'labuser'@'localhost'` | **서버 자신에서만** (유닉스 소켓/루프백) | ✅ 권장 — 웹앱이 같은 서버에 있으므로 이걸로 충분 |
| `'labuser'@'192.168.16.%'` | 사내망 대역에서 원격 접속 | 필요할 때만 |
| `'labuser'@'%'` | 어디서나 | ⚠️ 위험 |

### 16-5. `Query OK, 0 rows affected` 오해 풀기

```text
Query OK, 0 rows affected (0.001 sec)
```

- `Query OK` = **성공**입니다.
- `0 rows affected`는 "**행을 바꾸는 종류의 명령이 아니었다**"는 뜻입니다. `CREATE USER`, `GRANT`, `FLUSH PRIVILEGES` 같은 DDL/관리 명령은 정상이어도 0으로 나옵니다.
- 실패는 `ERROR <번호> (<SQLSTATE>): ...` 형태로 나옵니다. `ERROR`가 없으면 성공한 것입니다.

### 16-6. WordPress DB를 따로 만드는 이유

| 이유 | 설명 |
|---|---|
| 권한 격리 | WordPress가 털려도 `labdb`나 다른 앱 데이터에 접근하지 못함 |
| 백업/복구 단위 분리 | `mysqldump wordpress_db` 하나만 받고 복구 가능 |
| 문자셋·collation 독립 | 앱마다 요구가 다를 수 있음 |
| 삭제 용이 | WordPress를 걷어낼 때 DB 하나만 지우면 끝 |

이번 과제의 DB 구성:

| 용도 | DB | 사용자 | 상태 |
|---|---|---|---|
| 실습용 | `labdb` | `labuser`@`localhost` | 🟡 안내됨 |
| WordPress | `wordpress_db` | `wordpress_user`@`localhost` | ✅ 확인됨 (생성 성공) |
| LogAnalyzer | **불필요** — Diskfile 소스를 쓰므로 DB 없음 | — | ✅ 확인됨 (Diskfile 사용) |

> **LogAnalyzer의 두 가지 DB를 혼동하지 마십시오** (25장):
> ① **로그 데이터베이스** — 로그 자체를 MySQL에 넣는 방식. Diskfile을 쓰면 필요 없음
> ② **LogAnalyzer 사용자 DB** — 로그인/권한 기능을 쓸 때만 필요한 별도 DB

---

## 17. Samba와 Windows 공유

실행 서버: **web (192.168.16.131)**

### 17-1. 설치

```bash
dnf install -y samba samba-client
systemctl enable --now smb
systemctl status smb --no-pager
firewall-cmd --permanent --add-service=samba
firewall-cmd --reload
```

📘 RHEL 9 공식 문서: 독립형(standalone) 파일 서버는 **`smb` 서비스만 활성화**하면 됩니다. `nmb`(NetBIOS 이름 서비스)는 "현대 SMB 네트워크는 DNS로 이름을 해석하므로" **선택 사항**입니다.

| 서비스 | 포트 | 역할 | 이 실습 |
|---|---|---|---|
| `smb` (smbd) | **TCP 445** | 실제 파일 공유 (SMB2/SMB3 direct) | 필수 |
| `nmb` (nmbd) | UDP 137/138 | NetBIOS 이름/브라우징 (SMB1 시대 유산) | 선택 — `\\IP\공유`로 직접 접속하면 불필요 |

### 17-2. ✅ 실제 발생한 설정 오류 — `passdb backend` 위치

```text
오류/증상:
  Samba 접속 인증이 의도대로 동작하지 않음.
  testparm 실행 시 share section에 있는 passdb backend 가 무시되거나 경고.

원인:
  passdb backend = tdbsam 이 [hwanju] 공유 섹션 안에 들어가 있었다.
  이 파라미터는 서버 전체 설정(G, global-only)이며 공유별로 지정할 수 없다.

먼저 확인할 것:
  grep -n 'passdb backend' /etc/samba/smb.conf  →  [global] 아래에 있는가?

실행 서버: web (.131)

명령어:
  testparm -s

정상 결과:
  Loaded services file OK. 가 출력되고 [global] 아래에 passdb backend 가 표시된다.

실패하면 다음 확인:
  testparm            (경고 메시지 전문 확인)
  journalctl -u smb -n 50 --no-pager

주의할 점:
  smb.conf 파라미터는 man 페이지에 (G)=global 전용, (S)=공유(service)에 지정 가능 으로 표시된다.
```

📘 Samba `smb.conf(5)` 기준: `passdb backend`, `security`, `workgroup`, `map to guest` 는 모두 **(G) global 전용**입니다. `valid users`, `force user`, `create mask`, `path`, `browseable`, `read only` 는 **(S) 공유 단위** 파라미터입니다.

### 17-3. 올바른 `/etc/samba/smb.conf`

```conf
[global]
        workgroup = WORKGROUP
        security = user
        map to guest = never
        server min protocol = SMB2
        passdb backend = tdbsam
        log file = /var/log/samba/%m.log
        log level = 1

[hwanju]
        path = /srv/samba/hwanju
        browseable = yes
        read only = no
        valid users = hwanju
        force user = hwanju
        create mask = 0660
        directory mask = 0770
```

| 파라미터 | 구역 | 의미 |
|---|---|---|
| `workgroup` | G | Windows 작업 그룹 이름. Windows 기본값이 `WORKGROUP` |
| `security = user` | G | **접속 시 사용자/비밀번호로 인증**. 현대 Samba의 기본이자 권장값 |
| `map to guest = never` | G | 인증 실패를 게스트로 강등하지 않음 ⚠️ `bad user`로 두면 아무나 게스트로 붙습니다 |
| `server min protocol = SMB2` | G | SMB1(취약, EternalBlue 계열) 차단. ❓ 현재 Samba 기본값이 이미 SMB2인지는 서버에서 `testparm -v \| grep 'server min protocol'`로 확인하십시오 |
| `passdb backend = tdbsam` | G | Samba 비밀번호를 로컬 TDB 파일에 저장 (`/var/lib/samba/private/passdb.tdb`) |
| `path` | S | 공유할 실제 디렉터리 |
| `browseable = yes` | S | 네트워크 목록에 보임 |
| `read only = no` | S | 쓰기 허용 (= `writable = yes`) |
| `valid users = hwanju` | S | 이 사용자만 접속 허용 |
| `force user = hwanju` | S | 접속자가 누구든 **파일 소유자를 hwanju로 강제** |
| `create mask = 0660` / `directory mask = 0770` | S | 새로 만들 파일/디렉터리 권한 상한 |

### 17-4. 공유 디렉터리와 계정

```bash
# 실행 서버: web (.131)
groupadd -g 2001 hwanju 2>/dev/null
useradd -u 2001 -g 2001 -m hwanju 2>/dev/null
passwd hwanju                    # 리눅스 로그인 비밀번호 → [HWANJU_PASSWORD]

mkdir -p /srv/samba/hwanju
chown hwanju:hwanju /srv/samba/hwanju
chmod 2770 /srv/samba/hwanju

smbpasswd -a hwanju              # Samba 비밀번호 → [SAMBA_PASSWORD]
smbpasswd -e hwanju              # 계정 활성화
pdbedit -L -v                    # 등록된 Samba 계정 확인
```

> ### ⚠️ 리눅스 비밀번호와 Samba 비밀번호는 **별개**입니다
> Samba는 SMB 인증에 자체 해시(`passdb.tdb`)를 사용합니다. `passwd hwanju`로 바꾼 값은 **SSH/콘솔 로그인용**이고, `smbpasswd -a hwanju`로 넣은 값이 **Windows 탐색기에서 물어보는 비밀번호**입니다.
> 실습 편의상 같게 만들어도 되지만, **다르게 설정해도 정상 동작**합니다. 접속이 안 될 때 "리눅스 비밀번호를 넣고 있는 것은 아닌지" 먼저 의심하십시오.

📘 RHEL 9 문서는 파일 서버 전용 계정이라면 `useradd -M -s /sbin/nologin` 을 권장합니다. 다만 **이번 실습의 `hwanju`는 NFS 쓰기 테스트에서 `su - hwanju`로 로그인해야 하므로 셸이 필요**합니다. 그래서 위처럼 일반 계정으로 만듭니다.

### 17-5. SELinux 컨텍스트 — `samba_share_t`

```bash
semanage fcontext -a -t samba_share_t '/srv/samba(/.*)?'
restorecon -Rv /srv/samba
ls -ldZ /srv/samba/hwanju
```

정상 예상 결과 — 아래 출력은 **성공 메시지입니다**:

```text
Relabeled /srv/samba from unconfined_u:object_r:var_t:s0 to unconfined_u:object_r:samba_share_t:s0
```

`ls -ldZ` 결과에 `samba_share_t`가 보이면 완료입니다.

이미 규칙이 등록되어 있어 `-a`가 실패하는 경우:

```text
ValueError: File context for /srv/samba(/.*)? already defined
```

이때는 기존 규칙을 확인하고 **수정(`-m`)** 하십시오:

```bash
semanage fcontext -l | grep '/srv/samba'
semanage fcontext -m -t samba_share_t '/srv/samba(/.*)?'
restorecon -Rv /srv/samba
```

### 17-6. 검증과 Windows 접속

리눅스 쪽 (실행 서버: web .131):

```bash
testparm -s
systemctl restart smb
smbclient -L //192.168.16.131 -U hwanju
smbclient //192.168.16.131/hwanju -U hwanju -c 'ls'
ss -lntp | grep ':445'
smbstatus
```

Windows 쪽 — **파일 탐색기 주소창**에 입력:

```text
\\192.168.16.131\hwanju
\\samba.kload81.com\hwanju
```

> ### ❌ 하면 안 되는 것
> - **크롬 주소창**에 `\\192.168.16.131\hwanju` 입력 → 브라우저는 SMB를 지원하지 않습니다
> - **Windows 검색창(돋보기)** 에 입력 → 웹 검색으로 넘어갑니다
> - `http://192.168.16.131/hwanju` 형태로 접근 → SMB는 HTTP가 아닙니다
>
> 반드시 **파일 탐색기(Win+E)의 주소창** 또는 **실행창(Win+R)** 에 UNC 경로를 입력하십시오.

> **`Win + R`이 VirtualBox 창에 먹히는 문제**
> VM 화면에 포커스가 있으면 키 입력이 게스트(리눅스)로 갑니다. 먼저 **Host 키(기본값 오른쪽 Ctrl)** 를 눌러 마우스/키보드 포커스를 Windows로 되돌린 뒤 `Win + R`을 누르십시오. 또는 VM 창을 최소화하고 Windows 바탕화면에서 실행하십시오.

접속 시 자격 증명 창이 뜨면:

| 입력란 | 값 |
|---|---|
| 사용자 이름 | `hwanju` 또는 `192.168.16.131\hwanju` |
| 암호 | `[SAMBA_PASSWORD]` (smbpasswd로 설정한 값) |

### 17-7. `SMB1 disabled -- no workgroup available` 메시지

```text
SMB1 disabled -- no workgroup available
```

- `smbclient -L`로 목록을 조회할 때 자주 나옵니다.
- 의미: **SMB1(NetBIOS 브라우징)이 꺼져 있어서 "작업 그룹 목록"을 못 만든다**는 안내입니다.
- **SMB2/SMB3 direct access(`\\IP\공유`) 환경에서는 치명적 오류가 아닙니다.** 실제로 그 아래에 `Sharename` 목록이 정상 출력되면 접속에 문제가 없습니다.
- SMB1은 보안상 폐기된 프로토콜이므로 **다시 켜지 마십시오.**

### 17-8. `root@localhost` 혼동

PuTTY/터미널 창 제목의 `root@localhost`는 **6장에서 설명한 것과 같은 표시 문제**입니다. Samba 서버가 어느 장비인지는 창 제목이 아니라 다음으로 확인합니다.

```bash
hostname          # → web
hostname -I       # → 192.168.16.131 (그리고 NAT 쪽 주소)
smbstatus         # 실제 연결 중인 세션/공유 확인
```

---

## 18. SELinux context와 troubleshooting

### 18-1. 세 가지 모드

```bash
getenforce
sestatus
```

| 모드 | 동작 | 로그 |
|---|---|---|
| **Enforcing** | 정책 위반을 **차단** | audit.log에 AVC 기록 |
| **Permissive** | 차단하지 않고 **기록만** | audit.log에 AVC 기록 |
| **Disabled** | SELinux 자체가 꺼짐 | 기록 없음 |

임시 전환 (재부팅하면 원복):

```bash
setenforce 0     # Enforcing → Permissive
setenforce 1     # Permissive → Enforcing
```

영구 변경 — `/etc/selinux/config`:

```conf
SELINUX=disabled
```

> **이 변경은 재부팅해야 적용됩니다.** `setenforce`로는 Disabled로 갈 수 없습니다(Permissive까지만).

```bash
systemctl reboot
# 또는
/usr/sbin/reboot
```

재부팅 시 PuTTY 연결이 끊기는 것은 **정상**입니다. 잠시 후 다시 접속해 확인하십시오.

```bash
getenforce
sestatus
```

### 18-2. ⚠️ 실습용 Disabled vs 운영 권장

이번 실습에서는 수업 방식에 따라 **Web 서버의 SELinux를 Disabled로 변경**했습니다. ✅ 확인됨

| 구분 | 실습 환경 | 운영 환경 |
|---|---|---|
| 권장 모드 | 문제 재현·학습 목적이면 Permissive → 원인 확인 후 Enforcing 복귀 | **Enforcing 유지** |
| Disabled | 수업 진행상 허용될 수 있음 | ❌ 권장하지 않음. 정책 재활성화 시 전체 파일시스템 relabel이 필요해 부팅이 매우 길어짐 |
| 대안 | boolean 조정 + `semanage fcontext` + `restorecon` | 동일 |

> **Permissive를 먼저 쓰십시오.** Disabled와 달리 Permissive는 **무엇이 차단될 뻔했는지 로그를 남깁니다.** 그 로그가 곧 해결의 실마리입니다.

### 18-3. 표준 트러블슈팅 절차 📘

```bash
# 1) 최근 AVC 거부 기록 조회
ausearch -m AVC,USER_AVC,SELINUX_ERR,USER_SELINUX_ERR -ts recent

# 2) 사람이 읽을 수 있는 해설 (setroubleshoot-server 설치 시)
dnf install -y setroubleshoot-server
sealert -a /var/log/audit/audit.log
sealert -l "*"

# 3) 보조 확인
journalctl -t setroubleshoot -n 30 --no-pager
dmesg | grep -i -e type=1300 -e type=1400
```

원인별 조치:

| 원인 | 조치 |
|---|---|
| 파일 라벨이 잘못됨 | `semanage fcontext -a -t <타입> '<경로>(/.*)?'` → `restorecon -Rv <경로>` |
| 서비스 동작이 정책상 막힘 | `getsebool -a \| grep <서비스>` → `setsebool -P <boolean> on` |
| 비표준 포트 사용 | `semanage port -a -t <포트타입> -p tcp <번호>` |

### 18-4. `restorecon` / `semanage fcontext` 정확히 구분하기

| 명령 | 하는 일 | 지속성 |
|---|---|---|
| `chcon -t <타입> <파일>` | 파일 라벨을 **지금 당장** 바꿈 | ❌ relabel되면 사라짐 |
| `semanage fcontext -a -t <타입> '<경로>'` | "이 경로는 이 타입이다"라는 **규칙을 정책에 등록** | ✅ 영구 |
| `restorecon -Rv <경로>` | 등록된 규칙대로 **실제 파일에 적용** | 규칙이 있어야 의미 있음 |

즉 **`semanage fcontext`(규칙 등록) → `restorecon`(적용)** 순서가 정석이고, `chcon`은 임시 확인용입니다.

`Relabeled ... to ...` 출력은 **정상적인 성공 메시지**입니다. 오류로 오해하지 마십시오.

### 18-5. ⚠️ `/var/log/messages`에 Apache 컨텍스트를 지정하면 안 되는 이유

실습 중 "LogAnalyzer(Apache)가 `/var/log/messages`를 못 읽는다"는 이유로 이 파일에 `httpd_sys_content_t`를 지정하려는 시도가 있었습니다. **하지 마십시오.**

| 문제 | 설명 |
|---|---|
| rsyslog가 못 쓰게 됨 | `/var/log/messages`의 정상 타입은 `var_log_t`입니다. 이를 바꾸면 rsyslog(`syslogd_t`)의 쓰기가 SELinux에 의해 차단될 수 있습니다 |
| logrotate 실패 | 회전 후 새로 만든 파일에 정책 기본 타입이 다시 붙어, 라벨이 오락가락합니다 |
| 근본 해결이 아님 | Apache가 시스템 로그를 직접 읽는 것 자체가 정책적으로 비정상적인 접근입니다 |

**올바른 접근**:

1. 원래 타입으로 되돌립니다.

```bash
restorecon -v /var/log/messages
ls -lZ /var/log/messages          # var_log_t 인지 확인
```

2. LogAnalyzer가 로그를 읽어야 한다면, **Apache가 읽을 수 있는 별도 경로**로 로그를 복제/링크하거나, 로그를 DB에 넣는 방식(MySQL 소스)을 쓰거나, SELinux를 Permissive/Disabled로 두는 실습적 예외를 **명시적으로** 선택합니다.
3. 이번 실습에서는 **Web 서버 SELinux를 Disabled로 두어 우회**했습니다. ✅ 확인됨 / ⚠️ 운영 비권장

---

## 19. NFS Server

실행 서버: **nfs (192.168.16.136)** ← 이 절의 모든 명령은 **NFS 서버**에서 실행합니다.

### 19-1. 설치와 공유 디렉터리 준비

```bash
dnf install -y nfs-utils

groupadd -g 2001 hwanju 2>/dev/null
useradd -u 2001 -g 2001 -m hwanju 2>/dev/null
id hwanju

mkdir -p /srv/nfs/hwanju
chown hwanju:hwanju /srv/nfs/hwanju
chmod 2775 /srv/nfs/hwanju
ls -ld /srv/nfs/hwanju
```

정상 예상 결과:

```text
uid=2001(hwanju) gid=2001(hwanju) groups=2001(hwanju)
drwxrwsr-x. 2 hwanju hwanju 6 ... /srv/nfs/hwanju
```

> `chmod 2775`의 앞자리 `2`는 **setgid** 비트입니다. 이 디렉터리 안에 새로 만들어지는 파일은 그룹이 자동으로 `hwanju`가 되어, 클라이언트에서 만든 파일의 그룹이 흔들리지 않습니다.

### 19-2. `/etc/exports` — **NFS 전용 파일**

```bash
vi /etc/exports
```

내용:

```text
/srv/nfs/hwanju 192.168.16.137(rw,sync,root_squash,no_subtree_check)
```

> ### ⚠️ 파일을 헷갈리지 마십시오
> | 파일 | 서비스 | 실행 서버 |
> |---|---|---|
> | `/etc/exports` | **NFS** | nfs (.136) |
> | `/etc/samba/smb.conf` | Samba | web (.131) |
> | `/etc/named.conf` | BIND DNS | dns (.77) |
> | `/etc/vsftpd/vsftpd.conf` | FTP | ftp (.137) |
>
> 이름이 비슷해 보이지 않지만, 실습 중 "어느 서버의 어느 파일인지" 잃어버리는 일이 자주 생깁니다. 프롬프트(`[root@nfs ~]#`)를 항상 확인하십시오.

### 19-3. ⚠️ 공백 하나가 의미를 완전히 바꿉니다 📘

```text
/srv/nfs/hwanju 192.168.16.137(rw,sync,root_squash)     ← 올바름
/srv/nfs/hwanju 192.168.16.137 (rw,sync,root_squash)    ← 틀림!
```

📘 `exports(5)` man 페이지: **"No whitespace is permitted between a client and its option list."**

아래(공백이 있는) 형태는 다음 두 개로 해석됩니다.

1. `192.168.16.137` 에게 **기본 옵션(= 읽기 전용 `ro`)** 으로 export
2. **모든 호스트(`*`)** 에게 `(rw,sync,root_squash)` 로 export ⚠️ 전체 개방

즉 "왜 rw로 안 되지?" + "왜 아무나 붙지?"가 동시에 발생합니다.

### 19-4. 옵션 정확히 알기 📘 (`exports(5)` 기준)

| 옵션 | 의미 | **기본값** |
|---|---|---|
| `ro` / `rw` | 읽기 전용 / 읽기·쓰기 | **`ro`가 기본** — `rw`는 반드시 명시해야 함 |
| `sync` / `async` | 쓰기를 디스크에 반영한 뒤 응답 / 즉시 응답 | **`sync`가 기본** (1.0.0 이후). `async`는 빠르지만 장애 시 데이터 유실 |
| `root_squash` | 클라이언트 **uid/gid 0(root)** 요청을 익명 사용자로 매핑 | **`root_squash`가 기본** |
| `no_root_squash` | root 매핑을 하지 않음 (클라이언트 root = 서버 root) | ⚠️ 매우 위험 |
| `all_squash` | **모든** uid/gid를 익명으로 매핑 | 비활성 |
| `subtree_check` / `no_subtree_check` | 상위 디렉터리 경로 검사 여부 | **`no_subtree_check`가 기본** (1.1.0 이후). 성능·안정성 이유 |
| `anonuid=` / `anongid=` | 익명 매핑에 사용할 uid/gid 지정 | `nobody`/`nfsnobody` |

> 즉 위 예시의 `sync`, `root_squash`, `no_subtree_check`는 **기본값을 명시적으로 적어 둔 것**입니다. 의도를 문서화하는 좋은 습관입니다. 반면 `rw`는 **반드시 적어야만** 쓰기가 됩니다.

### 19-5. export 반영과 서비스

```bash
exportfs -rav
exportfs -v
systemctl enable --now nfs-server
systemctl status nfs-server --no-pager

firewall-cmd --permanent --add-service=nfs
firewall-cmd --permanent --add-service=rpc-bind
firewall-cmd --permanent --add-service=mountd
firewall-cmd --reload
firewall-cmd --list-all
```

| 명령 | 의미 |
|---|---|
| `exportfs -rav` | `-r` 재export(=`/etc/exports` 다시 읽기), `-a` 전체, `-v` 상세 |
| `exportfs -v` | **현재 실제로 export 중인 목록**과 적용된 옵션 전체를 출력 |

정상 예상 결과 (`exportfs -v`) — 기본값까지 모두 펼쳐서 보여줍니다:

```text
/srv/nfs/hwanju
        192.168.16.137(sync,wdelay,hide,no_subtree_check,sec=sys,rw,secure,root_squash,no_all_squash)
```

여기서 `rw`와 `root_squash`가 보이는지 반드시 확인하십시오.

📘 **NFSv4 / NFSv3 방화벽 차이**: RHEL 9 기준 NFSv4만 쓰면 **TCP 2049 하나**면 되고 `rpcbind`가 필요 없습니다. NFSv3를 함께 쓰면 `rpc-bind`, `mountd`가 필요합니다. NFSv4 전용으로 굳히려면 `/etc/nfs.conf`에 `vers3=n`을 설정하고 `systemctl mask --now rpc-statd.service rpcbind.service`를 적용합니다. 🟡 이번 실습에서 NFSv4 전용 설정을 적용한 기록은 없습니다.

### 19-6. 클라이언트에서 export 목록 확인

실행 서버: **ftp (192.168.16.137)** ← 클라이언트 쪽

```bash
showmount -e 192.168.16.136
```

정상 예상 결과:

```text
Export list for 192.168.16.136:
/srv/nfs/hwanju 192.168.16.137
```

실패 시 확인 (서버 .136에서):

```bash
systemctl status nfs-server --no-pager
exportfs -v
firewall-cmd --list-all
ss -lntp | grep 2049
```

> `showmount`는 NFSv3 계열 프로토콜(rpc)을 사용합니다. NFSv4 전용 서버라면 응답하지 않을 수 있으므로, 그때는 실제 `mount`로 확인하십시오.

### 19-7. 서버와 클라이언트의 경로가 다르다는 점

| 위치 | 경로 | 의미 |
|---|---|---|
| **NFS 서버 (.136)** | `/srv/nfs/hwanju` | 실제 데이터가 저장되는 디스크 경로 |
| **NFS 클라이언트 (.137)** | `/mnt/nfs` | 그 원격 디렉터리를 붙여 놓은 **마운트 지점** |

두 경로는 이름이 달라도 **같은 데이터**를 가리킵니다. 클라이언트에서 `/mnt/nfs/파일`을 만들면 서버의 `/srv/nfs/hwanju/파일`이 생깁니다. 이 관계를 확인하는 것이 뒤의 검증 절차입니다.

---

## 20. NFS Client와 `/etc/fstab`

실행 서버: **ftp (192.168.16.137)**

### 20-1. 패키지와 마운트 지점

```bash
dnf install -y nfs-utils
mkdir -p /mnt/nfs
```

### 20-2. 수동 마운트로 먼저 시험

```bash
getent hosts nfs.kload81.com
mount -t nfs nfs.kload81.com:/srv/nfs/hwanju /mnt/nfs
findmnt /mnt/nfs
df -hT /mnt/nfs
```

정상 예상 결과 (`findmnt`):

```text
TARGET   SOURCE                              FSTYPE OPTIONS
/mnt/nfs nfs.kload81.com:/srv/nfs/hwanju     nfs4   rw,relatime,vers=4.2,...
```

읽는 법:

| 필드 | 확인 포인트 |
|---|---|
| `SOURCE` | `서버이름:/서버경로` 형식이 맞는가 |
| `FSTYPE` | `nfs4`면 NFSv4로 붙은 것 |
| `OPTIONS`의 `rw` | 읽기 전용(`ro`)으로 붙었다면 `/etc/exports`에 `rw`가 빠진 것 |
| `vers=` | 협상된 NFS 버전 |

실패 시 확인:

```bash
showmount -e 192.168.16.136
ping -c2 192.168.16.136
dmesg | tail -20
journalctl -xe | tail -30
```

### 20-3. ✅ 실제 질문 — "`/etc/fstab` 내용을 다 지워야 하나요?"

**절대 아닙니다.** `/etc/fstab`은 이 시스템이 부팅할 때 마운트해야 할 **모든** 파일시스템 목록입니다.

```text
오류/증상:
  NFS 자동 마운트를 추가하려고 /etc/fstab 전체를 지우려 함

원인:
  fstab이 "이번에 추가할 마운트만 적는 파일"이라고 오해

먼저 확인할 것:
  현재 fstab에 /, /boot, swap 줄이 있는지

실행 서버: ftp (.137)

명령어:
  cp -a /etc/fstab /etc/fstab.bak-$(date +%F)
  cat /etc/fstab

정상 결과:
  UUID=... /      xfs   defaults 0 0
  UUID=... /boot  xfs   defaults 0 0
  ... swap 줄 등

실패하면 다음 확인:
  blkid
  lsblk -f

주의할 점:
  루트(/) 줄을 지우고 재부팅하면 시스템이 부팅되지 않습니다.
  반드시 맨 아래에 한 줄만 추가하십시오.
```

**추가할 한 줄** (기존 줄은 그대로 두고 파일 맨 끝에):

```text
nfs.kload81.com:/srv/nfs/hwanju /mnt/nfs nfs defaults,_netdev 0 0
```

필드 해설:

| 위치 | 값 | 의미 |
|---|---|---|
| 1 | `nfs.kload81.com:/srv/nfs/hwanju` | 원격 장치(서버:경로). **DNS 이름을 쓰려면 DNS가 반드시 동작해야 합니다** |
| 2 | `/mnt/nfs` | 마운트 지점 |
| 3 | `nfs` | 파일시스템 타입 (커널이 nfs4로 협상) |
| 4 | `defaults,_netdev` | 마운트 옵션 |
| 5 | `0` | dump 대상 아님 |
| 6 | `0` | 부팅 시 fsck 하지 않음 (원격 FS는 반드시 0) |

**`_netdev`가 필요한 이유**: 이 마운트는 **네트워크가 살아 있어야만** 가능합니다. `_netdev`를 붙이면 systemd가 이 마운트 유닛에 `network-online.target` 의존성을 걸어 **네트워크가 준비된 뒤에** 시도합니다. 없으면 부팅 초기에 마운트를 시도하다 실패하고, 최악의 경우 부팅이 지연되거나 emergency mode로 빠집니다.

반영과 검증:

```bash
systemctl daemon-reload      # fstab → systemd mount unit 재생성
mount -a
findmnt /mnt/nfs
mount | grep nfs
```

`mount -a`가 실패하는 흔한 원인:

| 원인 | 확인 |
|---|---|
| 이름 해석 실패 | `getent hosts nfs.kload81.com` — 값이 안 나오면 DNS/hosts 문제 |
| 마운트 지점 없음 | `ls -d /mnt/nfs` |
| 서버가 export하지 않음 | (서버에서) `exportfs -v` |
| 방화벽 | (서버에서) `firewall-cmd --list-all` |
| 오타 | `findmnt --verify --verbose` 로 fstab 문법 점검 |

> **안전 수칙**: fstab을 고친 뒤에는 **재부팅 전에 반드시 `mount -a`가 성공하는지 확인**하십시오. `mount -a`가 실패하는 fstab으로 재부팅하면 부팅 문제가 생길 수 있습니다.

---

## 21. `root_squash`와 UID/GID

이 절이 이번 실습에서 **개념적으로 가장 중요한 부분**입니다.

### 21-1. ✅ 실제 발생한 오류

```text
오류/증상:
  ls: cannot open directory '/mnt/nfs': 허가 거부
  (root로 실행했는데도 거부됨)

원인:
  NFS 서버의 export 옵션 root_squash 때문.
  클라이언트(.137)의 root(uid 0)가 보낸 요청을 NFS 서버(.136)가
  익명 사용자(nobody/nfsnobody)로 바꿔서 처리한다.
  디렉터리 소유자는 hwanju(2001)이므로 익명 사용자에게는 권한이 없다.

먼저 확인할 것:
  1) 지금 누구로 실행하고 있는가?  id
  2) 서버의 export 옵션은?          (서버에서) exportfs -v
  3) 양쪽 hwanju의 UID/GID가 같은가?

실행 서버: ftp (.137) — 클라이언트

명령어:
  id
  id hwanju
  findmnt /mnt/nfs
  ls -ln /mnt/nfs           # 소유자를 숫자로 표시

정상 결과:
  id hwanju → uid=2001(hwanju) gid=2001(hwanju)
  ls -ln /mnt/nfs 의 소유자 숫자가 2001 2001

실패하면 다음 확인:
  (서버에서) ls -ln /srv/nfs/hwanju
  (서버에서) exportfs -v
  (양쪽에서) getent passwd hwanju

주의할 점:
  sudo 를 붙여도 해결되지 않는다. sudo 는 "root가 되는" 명령이고,
  문제는 바로 그 root가 서버에서 익명으로 강등되는 것이기 때문이다.
  no_root_squash 로 바꾸는 것은 해결이 아니라 보안 구멍을 뚫는 것이다.
```

### 21-2. `root_squash`는 버그가 아니라 **보안 기능**입니다

NFS는 **클라이언트가 보낸 UID/GID 숫자를 그대로 믿는** 프로토콜(`sec=sys`)입니다. 만약 squash가 없다면:

> 공격자가 자기 노트북에서 root를 잡고 NFS 서버에 마운트 → 서버의 **모든 파일을 root 권한으로 읽고 씀** → setuid 바이너리를 심어 서버 전체 장악

`root_squash`는 이 시나리오를 막습니다. 그래서 **기본값이며, 꺼서는 안 됩니다.**

| 옵션 | 클라이언트 root의 서버상 신분 | 평가 |
|---|---|---|
| `root_squash` (기본) | 익명(nobody) | ✅ 안전 |
| `no_root_squash` | 서버의 root | ⚠️ 원격 root가 서버 파일을 마음대로 조작 가능. 실습에서도 권장하지 않음 |
| `all_squash` | 모두 익명 | 공개 읽기 공유용 |

### 21-3. 올바른 해결 — **일반 사용자로, 양쪽 UID/GID를 일치시켜서**

`sec=sys` NFS는 이름이 아니라 **숫자(UID/GID)로 신분을 판단**합니다. 그래서 양쪽에 `hwanju`가 있어도 UID가 다르면 남의 파일이 됩니다.

양쪽 확인:

```bash
# 실행 서버: nfs (.136)
id hwanju

# 실행 서버: ftp (.137)
id hwanju
```

양쪽 모두 정상 예상 결과:

```text
uid=2001(hwanju) gid=2001(hwanju) groups=2001(hwanju)
```

다르다면 클라이언트에서 맞춥니다 (⚠️ 기존 파일 소유자가 바뀌므로 실습 서버에서만):

```bash
# 실행 서버: 숫자가 다른 쪽
groupmod -g 2001 hwanju
usermod  -u 2001 -g 2001 hwanju
id hwanju
```

### 21-4. 검증 절차 — root가 아니라 hwanju로

실행 서버: **ftp (.137)**

```bash
su - hwanju
id
ls -la /mnt/nfs
echo "NFS test from ftp client" > /mnt/nfs/nfs-test.txt
ls -l /mnt/nfs/nfs-test.txt
cat /mnt/nfs/nfs-test.txt
exit
```

또는 셸을 바꾸지 않고 한 줄씩:

```bash
runuser -u hwanju -- touch /mnt/nfs/ftp-nfs-test.txt
runuser -u hwanju -- ls -l /mnt/nfs
```

그리고 **NFS 서버에서 실제로 파일이 생겼는지** 확인 — 이것이 진짜 증거입니다:

```bash
# 실행 서버: nfs (.136)
ls -l /srv/nfs/hwanju
cat /srv/nfs/hwanju/nfs-test.txt
```

정상 예상 결과: 클라이언트에서 만든 파일이 서버 디렉터리에 `hwanju hwanju` 소유로 보입니다.

실패 시 확인:

| 증상 | 확인 |
|---|---|
| `Permission denied` (hwanju인데도) | 서버의 `ls -ld /srv/nfs/hwanju` 권한이 `775` 이상인지, 소유자가 hwanju인지 |
| 소유자가 `nobody`로 보임 | UID/GID 불일치 또는 NFSv4 idmapping 문제. `ls -ln`으로 숫자 확인 |
| `Read-only file system` | export에 `rw`가 빠짐 → 서버에서 `exportfs -v` |

### 21-5. SELinux가 Enforcing일 때의 NFS boolean

NFS 서버 쪽에서 SELinux가 Enforcing이면 export 쓰기가 막힐 수 있습니다.

```bash
# 실행 서버: nfs (.136)
getenforce
getsebool nfs_export_all_rw
getsebool nfs_export_all_ro
```

| boolean | 의미 |
|---|---|
| `nfs_export_all_rw` | SELinux가 임의 경로의 **읽기·쓰기 NFS export**를 허용할지 |
| `nfs_export_all_ro` | 읽기 전용 export 허용 여부 |

필요할 때만 영구 활성화:

```bash
setsebool -P nfs_export_all_rw on
getsebool nfs_export_all_rw
```

> ⚠️ **먼저 `ausearch`로 실제 차단이 있었는지 확인한 뒤에 켜십시오.** 증상 없이 boolean부터 켜는 것은 권한을 불필요하게 넓히는 일입니다. 그리고 **SELinux를 끄거나 `no_root_squash`를 쓰는 것은 이 문제의 올바른 해법이 아닙니다.**

---

## 22. vsftpd FTP

실행 서버: **ftp (192.168.16.137)**

### 22-1. 설치

```bash
dnf install -y vsftpd
systemctl enable --now vsftpd
systemctl status vsftpd --no-pager
```

### 22-2. `/etc/vsftpd/vsftpd.conf` — **지우지 말고 고치십시오**

> 기본 설정 파일에는 주석으로 된 설명이 많습니다. **파일 전체를 지우고 새로 쓰지 마십시오.**
> 원칙: **같은 항목이 이미 있으면 그 줄을 수정**하고, **없으면 파일 끝에 추가**합니다.
>
> ```bash
> cp -a /etc/vsftpd/vsftpd.conf /etc/vsftpd/vsftpd.conf.bak-$(date +%F)
> grep -nE '^(#\s*)?(anonymous_enable|local_enable|write_enable|local_umask|chroot_local_user|allow_writeable_chroot|local_root|pasv_)' /etc/vsftpd/vsftpd.conf
> ```
>
> 위 `grep` 결과에 줄 번호가 나오면 그 줄을 고치고, 안 나오면 새로 추가합니다.

적용할 설정:

```conf
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
chroot_local_user=YES
allow_writeable_chroot=YES
local_root=/mnt/nfs
pasv_min_port=40000
pasv_max_port=40010
pasv_address=192.168.16.137
```

📘 `vsftpd.conf` 문서 기준 해설 (괄호 안은 **기본값**):

| 항목 | 의미 | 기본값 | 왜 이렇게 두는가 |
|---|---|---|---|
| `anonymous_enable=NO` | 익명 로그인 차단 | `YES` | ⚠️ 기본이 YES이므로 **반드시 NO로 바꿔야** 합니다 |
| `local_enable=YES` | 로컬 계정(hwanju) 로그인 허용 | `NO` | 명시 필요 |
| `write_enable=YES` | 업로드·삭제 등 쓰기 명령 허용 | `NO` | 업로드 실습에 필수 |
| `local_umask=022` | 업로드 파일 권한 마스크 | `077` | 022면 `644`로 생성됨. 077이면 소유자만 읽기 |
| `chroot_local_user=YES` | 로그인 후 홈(또는 `local_root`)에 **갇힘** | `NO` | 다른 시스템 경로를 보지 못하게 하는 보안 설정 |
| `allow_writeable_chroot=YES` | 쓰기 가능한 디렉터리를 chroot 루트로 허용 | — | ❓ upstream `vsftpd.conf` 문서에는 이 항목이 없습니다. vsftpd 3.0.x 계열에서 제공되는 옵션이며, 서버에서 `man 5 vsftpd.conf \| grep -A3 allow_writeable_chroot`로 확인하십시오 |
| `local_root=/mnt/nfs` | 로그인 후 이동할 디렉터리 | 없음 | **FTP 업로드가 NFS 서버 디스크에 저장되게 하는 핵심 설정** |
| `pasv_min_port` / `pasv_max_port` | passive 데이터 연결 포트 범위 | `0`(임의) | 방화벽에서 열 범위를 좁히기 위해 고정 |
| `pasv_address=192.168.16.137` | PASV 응답에 알려 줄 IP | 없음 | 클라이언트가 접속할 주소를 명시 |

### 22-3. FTP passive 모드를 이해해야 하는 이유

| 모드 | 데이터 연결 방향 | 문제 |
|---|---|---|
| **Active** | **서버 → 클라이언트** 로 접속 | 클라이언트 방화벽/NAT에 막힘 |
| **Passive** | **클라이언트 → 서버** 로 접속 | 서버가 임의의 고포트를 열어야 함 |

FTP는 **제어 연결(21)과 데이터 연결이 분리**된 특이한 프로토콜입니다. 그래서 21번만 열면 로그인은 되는데 `ls`가 멈추는 현상이 생깁니다. Passive 포트 범위를 고정하고 그 범위를 방화벽에서 열어야 목록 조회와 전송이 됩니다.

### 22-4. 방화벽

```bash
firewall-cmd --permanent --add-service=ftp
firewall-cmd --permanent --add-port=40000-40010/tcp
firewall-cmd --reload
firewall-cmd --list-all
```

반영:

```bash
systemctl restart vsftpd
systemctl status vsftpd --no-pager
ss -lntp | grep ':21'
```

정상 예상 결과: `LISTEN ... :21 ... users:(("vsftpd",...))`

### 22-5. ✅ 실제 발생한 계정 문제

```text
오류/증상:
  ftptest 계정으로 로그인 실패 (530 Login incorrect)

원인(가능성, 순서대로 확인):
  - 계정이 실제로 존재하지 않거나 비밀번호가 설정되지 않음
  - 계정의 셸이 /etc/shells 에 없음 (vsftpd 는 PAM 을 통해 유효 셸을 요구)
  - /etc/vsftpd/ftpusers 또는 user_list 에 의해 차단
  - local_enable=YES 가 아직 반영되지 않음

먼저 확인할 것:
  id ftptest
  getent passwd ftptest
  grep -n 'ftptest' /etc/vsftpd/ftpusers /etc/vsftpd/user_list

실행 서버: ftp (.137)

명령어:
  getent passwd hwanju
  grep -n "$(getent passwd hwanju | cut -d: -f7)" /etc/shells
  journalctl -u vsftpd -n 30 --no-pager
  tail -20 /var/log/secure

정상 결과:
  hwanju 의 셸(/bin/bash)이 /etc/shells 에 포함되어 있다.

실패하면 다음 확인:
  systemctl status vsftpd --no-pager
  grep -vE '^\s*#|^\s*$' /etc/vsftpd/vsftpd.conf

주의할 점:
  실제 실습에서는 ftptest 대신 hwanju 계정으로 진행하여 성공했다.
```

✅ **확인됨**: 최종적으로 **`hwanju` 계정으로 FTP 로그인·업로드에 성공**했습니다.

### 22-6. ❌ `passwd 1234` — 매우 흔한 치명적 오해

```bash
passwd 1234
```

이 명령은 **비밀번호를 `1234`로 바꾸는 명령이 아닙니다.** `passwd`의 인자는 **사용자 이름**이므로, 위 명령은 "`1234`라는 이름의 계정"의 비밀번호를 바꾸려는 시도입니다.

- 그런 계정이 없으면: `passwd: 사용자 '1234'이(가) 존재하지 않습니다`
- 우연히 있으면: **엉뚱한 계정의 비밀번호가 바뀝니다**

✅ 올바른 사용:

```bash
passwd hwanju
```

실행하면 **대화형으로** 새 비밀번호를 두 번 물어봅니다. 여기에 `[HWANJU_PASSWORD]` 값을 입력합니다. **입력 중 화면에 아무 것도 표시되지 않는 것이 정상입니다.**

> ⚠️ 실습에서 `1234` 같은 단순 비밀번호를 쓰더라도, **운영 환경에서는 절대 사용하지 마십시오.** root 비밀번호를 `1234`로 두면 SSH가 열려 있는 순간 사실상 무방비입니다.

### 22-7. FTP 동작 테스트

```bash
dnf install -y ftp
ftp 127.0.0.1
```

FTP 프롬프트 안에서:

```text
Name: hwanju
Password: [HWANJU_PASSWORD]
pwd
ls
put /etc/hostname ftp-test.txt
ls
bye
```

✅ 실제로 확인된 성공 메시지:

```text
230 Login successful.
226 Transfer complete.
```

FTP 응답 코드 읽는 법:

| 코드 | 의미 |
|---|---|
| `220` | 서비스 준비 완료 (접속 성공) |
| `230` | **로그인 성공** |
| `226` | **데이터 전송 완료** |
| `250` | 파일 동작 완료 |
| `530` | 로그인 실패 (계정/비밀번호/차단) |
| `500 OOPS: cannot change directory` | 지정한 디렉터리로 못 들어감 |
| `553 Could not create file` | 쓰기 권한 없음 |

### 22-8. 자주 나오는 FTP 오류 3종

```text
오류/증상:
  500 OOPS: cannot change directory: /mnt/nfs

원인:
  local_root 로 지정한 디렉터리가 없거나, 마운트가 풀렸거나, 접근 권한이 없거나,
  SELinux 가 vsftpd 의 NFS 접근을 차단함

먼저 확인할 것: 마운트가 살아 있는가?

실행 서버: ftp (.137)

명령어:
  findmnt /mnt/nfs
  ls -ld /mnt/nfs
  runuser -u hwanju -- ls /mnt/nfs
  getenforce

정상 결과:
  findmnt 에 nfs4 마운트가 보이고, hwanju 로 목록 조회가 된다.

실패하면 다음 확인:
  mount -a
  (NFS 서버에서) exportfs -v
  ausearch -m AVC -ts recent

주의할 점:
  마운트가 풀린 상태에서는 /mnt/nfs 가 로컬 빈 디렉터리로 보인다.
  이때 업로드하면 NFS 서버가 아니라 FTP 서버 로컬 디스크에 저장된다.
```

```text
오류/증상:
  500 OOPS: vsftpd: refusing to run with writable root inside chroot()

원인:
  chroot_local_user=YES 인데 chroot 루트 디렉터리에 쓰기 권한이 있어
  vsftpd 가 보안상 기동을 거부함

실행 서버: ftp (.137)

명령어(둘 중 택1):
  # 방법 A - 옵션 허용 (실습에서 사용)
  echo 'allow_writeable_chroot=YES' >> /etc/vsftpd/vsftpd.conf
  systemctl restart vsftpd

  # 방법 B - 운영 권장: chroot 루트는 읽기전용으로 두고 하위에 쓰기 디렉터리를 둔다
  #   local_root=/mnt/nfs   (루트는 555)
  #   업로드는 /mnt/nfs/upload (hwanju 소유, 755) 로 유도

정상 결과:
  systemctl status vsftpd 가 active (running)

주의할 점:
  allow_writeable_chroot 는 vsftpd 3.0.x 계열의 옵션이다.
  upstream vsftpd.conf 문서 목록에는 없으므로 서버의 man 페이지로 확인할 것. (확인 필요)
```

```text
오류/증상:
  553 Could not create file.

원인:
  write_enable=NO 이거나, 대상 디렉터리에 대한 유닉스 권한이 없거나,
  NFS root_squash / UID 불일치, 또는 SELinux 차단

먼저 확인할 것: 어떤 계정으로 로그인했고, 그 계정이 그 디렉터리에 쓸 수 있는가?

실행 서버: ftp (.137)

명령어:
  grep -n '^write_enable' /etc/vsftpd/vsftpd.conf
  runuser -u hwanju -- touch /mnt/nfs/perm-test.txt
  ls -ln /mnt/nfs
  getenforce
  getsebool ftpd_use_nfs ftpd_full_access

정상 결과:
  runuser 로 파일이 만들어지면 FTP 쪽 권한 문제는 아니다.

실패하면 다음 확인:
  ausearch -m AVC -ts recent
  (NFS 서버에서) ls -ln /srv/nfs/hwanju
```

### 22-9. FTP 관련 SELinux boolean 📘

```bash
getsebool -a | grep -i ftp
getsebool ftpd_use_nfs
getsebool ftpd_full_access
```

| boolean | 공식 설명 | 기본값 | 이 실습에서의 판단 |
|---|---|---|---|
| `ftpd_use_nfs` | "determine whether ftpd can use NFS used for public file transfer services" | off | **이 구성에 정확히 맞는 boolean입니다.** vsftpd가 NFS 마운트를 다뤄야 하므로 후보 1순위 |
| `ftpd_full_access` | "determine whether ftpd can login to local users and can read and write all files on the system, governed by DAC" | off | ⚠️ **허용 범위가 매우 넓습니다.** 시스템 전체 읽기·쓰기를 정책적으로 열어 줍니다. 실습용 마지막 수단(fallback)으로만 분류하십시오 |

권장 순서:

```bash
# 1) 정말 SELinux가 막았는지 먼저 확인
ausearch -m AVC -ts recent | grep -i ftp

# 2) 좁은 boolean 부터
setsebool -P ftpd_use_nfs on

# 3) 그래도 안 되면 원인을 다시 분석. ftpd_full_access 는 최후에만.
```

📘 참고: FTP 공개 공유용 파일 컨텍스트로는 `public_content_t`(읽기 전용 공유), `public_content_rw_t`(읽기·쓰기 공유, `ftpd_anon_write` boolean 필요)가 정의되어 있습니다. 이번 실습은 익명 FTP를 쓰지 않으므로 해당 없음입니다.

---

## 23. SFTP와 SSH

### 23-1. SFTP는 **설치하는 것이 아니라 이미 있는 것**입니다

SFTP는 FTP와 이름만 비슷할 뿐 **완전히 다른 프로토콜**입니다. FTP over SSL(FTPS)도 아닙니다. **SSH의 하위 시스템(subsystem)** 으로 동작합니다.

```bash
# 실행 서버: ftp (.137)
grep -n -i sftp /etc/ssh/sshd_config
```

일반적인 출력:

```text
Subsystem       sftp    /usr/libexec/openssh/sftp-server
```

즉 `sshd`가 이미 떠 있으면 **SFTP는 추가 설치·추가 포트 개방 없이 이미 동작합니다.** "sftp-server 패키지를 따로 설치해야 한다"는 설명은 틀렸습니다.

### 23-2. FTP와 SFTP 비교

| 항목 | FTP | SFTP |
|---|---|---|
| 서버 데몬 | `vsftpd` | `sshd` |
| 기본 포트 | **TCP 21** (+ passive 데이터 포트) | **TCP 22** |
| 암호화 | 기본적으로 없음 (**비밀번호도 평문**) ⚠️ | SSH로 전 구간 암호화 |
| 접속 프로그램 | FileZilla, `ftp`, WinSCP(FTP 모드) | WinSCP, FileZilla(SFTP 모드), `sftp` |
| 설정 파일 | `/etc/vsftpd/vsftpd.conf` | `/etc/ssh/sshd_config` |
| 데이터 연결 | 제어/데이터 분리 (active/passive) | 단일 SSH 연결 안에서 처리 |
| chroot | `chroot_local_user` | `Match User` + `ChrootDirectory` |
| NFS 경로 사용 | `local_root=/mnt/nfs` 로 강제 가능 | 계정의 홈/권한을 따름. 별도 지정하려면 `ChrootDirectory` 또는 심볼릭 링크 |
| 방화벽 | `ftp` 서비스 + passive 포트 범위 | `ssh` 하나 |
| 운영 권장 | ❌ 평문 | ✅ 권장 |

### 23-3. SFTP 접속 확인

리눅스에서:

```bash
# 실행 서버: 아무 서버에서나 (예: web .131)
sftp hwanju@192.168.16.137
```

sftp 프롬프트 안에서:

```text
pwd
ls
put /etc/hostname sftp-test.txt
ls
bye
```

Windows에서 (WinSCP):

| 입력란 | 값 |
|---|---|
| 파일 프로토콜 | **SFTP** |
| 호스트 이름 | `192.168.16.137` (또는 `ftp.kload81.com`) |
| 포트 번호 | `22` |
| 사용자 이름 | `hwanju` |
| 비밀번호 | `[HWANJU_PASSWORD]` |

🟡 **안내됨(결과 미확인)** — 이번 대화에서 SFTP 접속 성공 화면은 확인되지 않았습니다. 제출 전에 직접 접속해 캡처하십시오.

> **SFTP는 `local_root` 개념이 없습니다.** FTP로 접속하면 `/mnt/nfs`에서 시작하지만, SFTP로 접속하면 `hwanju`의 홈(`/home/hwanju`)에서 시작합니다. 같은 위치를 보고 싶다면 심볼릭 링크를 만드십시오.
>
> ```bash
> # 실행 서버: ftp (.137)
> runuser -u hwanju -- ln -s /mnt/nfs /home/hwanju/nfs
> ```

---

## 24. rsyslog 원격 로그

### 24-1. 구조

| 역할 | 서버 | 하는 일 |
|---|---|---|
| **수집 서버(collector)** | web **192.168.16.131** | UDP 514로 로그를 받아 `/var/log/remote.log`, `/var/log/messages`에 기록. LogAnalyzer로 열람 |
| **송신 서버(sender)** | dns .77, nfs .136, ftp .137 | 자기 로그를 web으로 전달 |

### 24-2. `@` 와 `@@` — 절대 헷갈리면 안 되는 표기

전통(legacy) 문법:

```conf
*.*  @192.168.16.131:514      # @  하나 → UDP
*.*  @@192.168.16.131:514     # @@ 둘   → TCP
```

| 표기 | 프로토콜 | 특징 |
|---|---|---|
| `@호스트:포트` | **UDP** | 가볍고 빠름. 전달 보장 없음(유실 가능), 수신측 방화벽 `514/udp` |
| `@@호스트:포트` | **TCP** | 연결 기반, 유실 적음. 수신측은 `imtcp` 모듈 + `514/tcp` |

이번 실습은 **UDP 514**를 사용했습니다. 따라서:

- 수신측에서 열어야 하는 것은 **`514/udp`** 입니다. `514/tcp`를 열어 봐야 소용없습니다.
- 확인 명령도 `ss -lunp`(**u** = UDP)입니다. `ss -lntp`(t = TCP)로 보면 안 보입니다.

📘 현대(RainerScript) 문법 — 운영 권장 형태:

```conf
*.* action(type="omfwd"
      target="192.168.16.131" port="514" protocol="udp"
      queue.type="linkedlist"
      queue.filename="fwd_web"
      queue.saveOnShutdown="on"
      action.resumeRetryCount="-1"
     )
```

| 파라미터 | 의미 |
|---|---|
| `queue.type="linkedlist"` | 메모리 큐 사용 — 수집 서버가 잠깐 죽어도 로그를 버리지 않음 |
| `queue.filename` | 디스크 백업 큐 파일 접두어 |
| `queue.saveOnShutdown="on"` | 종료 시 큐를 디스크에 저장 |
| `action.resumeRetryCount="-1"` | 무한 재시도 |

> 수업에서 사용한 `*.* @192.168.16.131:514` 한 줄 방식도 **문법적으로 유효하며 동작합니다.** 학습 단계에서는 간단한 쪽으로, 운영에서는 큐가 있는 `omfwd` 방식으로 가면 됩니다.

### 24-3. 송신 서버 설정

실행 서버: **dns (.77), nfs (.136), ftp (.137) — 3대 각각**

```bash
cat > /etc/rsyslog.d/10-forward-to-web.conf <<'CFG'
*.* @192.168.16.131:514
CFG

rsyslogd -N 1
systemctl restart rsyslog
systemctl status rsyslog --no-pager
```

`rsyslogd -N 1`은 **설정 문법 검사**입니다 (`-N` = config check, 레벨 1).
정상 예상 결과:

```text
rsyslogd: version ..., config validation run (level 1), master config /etc/rsyslog.conf
rsyslogd: End of config validation run. Bye.
```

오류가 있으면 파일명과 줄 번호가 표시됩니다.

> 📘 rsyslog는 `/etc/rsyslog.d/` 안의 파일을 **사전순(lexical order)** 으로 읽습니다. 그래서 `10-` 처럼 숫자 접두어를 붙여 순서를 통제합니다.

### 24-4. 수신 서버 설정

실행 서버: **web (192.168.16.131)**

```bash
vi /etc/rsyslog.conf     # 또는 /etc/rsyslog.d/00-remote.conf
```

**초기 설정(문제가 있었던 형태)**:

```conf
module(load="imudp")
input(type="imudp" port="514")

if ($fromhost-ip != "127.0.0.1" and $fromhost-ip != "::1") then {
        action(type="omfile" file="/var/log/remote.log")
        stop
}
```

한 줄씩 읽는 법:

| 줄 | 의미 |
|---|---|
| `module(load="imudp")` | UDP 수신 **모듈을 적재** |
| `input(type="imudp" port="514")` | 514/udp **리스너를 실제로 연다** |
| `$fromhost-ip` | 이 메시지를 보낸 **호스트의 IP** |
| `!= "127.0.0.1" and != "::1"` | 즉 "**자기 자신이 아닌 곳에서 온 것**" = 원격 로그 |
| `action(type="omfile" file=...)` | 지정한 파일에 기록 |
| **`stop`** | ⚠️ **이 메시지에 대한 rsyslog 규칙 처리를 여기서 완전히 중단** |

### 24-5. ⚠️ `stop`의 정확한 의미 — 이것이 문제의 핵심이었습니다

`stop`은 "이 파일에 쓰고 끝"이 **아닙니다.** **그 메시지에 대해 이후의 모든 rsyslog 규칙을 건너뛴다**는 뜻입니다.

기본 `/etc/rsyslog.conf`에는 아래와 같은 규칙이 뒤에 있습니다:

```conf
*.info;mail.none;authpriv.none;cron.none    /var/log/messages
```

`stop`을 만나면 이 규칙까지 도달하지 못하므로:

> **원격 로그는 `/var/log/remote.log`에는 있지만 `/var/log/messages`에는 없습니다.**

그리고 LogAnalyzer의 Diskfile 소스가 `/var/log/messages`를 보고 있다면:

> **LogAnalyzer 화면에는 Web 서버 자신의 로그만 보이고, DNS/NFS/FTP 로그는 안 보입니다.**

이것이 실습에서 겪은 증상의 정확한 인과입니다.

### 24-6. 해결책 두 가지 — 장단점 비교

**해결책 ①: LogAnalyzer의 로그 소스를 `/var/log/remote.log`로 변경** ⭐ 학습용 권장

| 장점 | 단점 |
|---|---|
| 로그가 한 파일에만 존재 → 중복 없음 | Web 서버 **자신의** 로그는 remote.log에 없으므로, 소스를 2개 등록하거나 로컬 로그도 자기 자신에게 전송해야 함 |
| 로컬/원격 분리가 명확해 관리·보존 정책 세우기 쉬움 | LogAnalyzer 설정을 다시 만져야 함 |
| `/var/log/messages`가 원래 용도(로컬 시스템 로그)를 유지 | |

**해결책 ②: 원격 로그를 `/var/log/messages`에도 함께 기록** ← **실제로 적용한 방식**

| 장점 | 단점 |
|---|---|
| LogAnalyzer 설정을 안 바꿔도 모든 서버 로그가 한 화면에 보임 | **같은 로그가 두 파일에 중복 저장** → 디스크 2배 |
| 구현이 한 줄 추가로 끝남 | logrotate 정책이 두 파일에 각각 필요 |
| | 로컬 로그와 원격 로그가 섞여, 사고 분석 시 출처 구분이 번거로움 |
| | 원격 호스트가 로그를 대량 전송하면 `/var/log/messages`가 폭주 (보안 관점: log flooding) |

> **가장 깔끔한 학습용 구조 추천**: **해결책 ①** — 원격은 `/var/log/remote.log`, 로컬은 `/var/log/messages`로 분리하고, LogAnalyzer에 **로그 소스를 두 개 등록**합니다. 출처가 분명해지고 중복도 없습니다.
>
> 다만 **이번 실습에서 실제로 채택한 것은 해결책 ②**이며, 그 결과 원격 로그가 두 파일 모두에 기록되었습니다. 아래에 그대로 기록합니다.

### 24-7. ✅ 실제 적용된 최종 수신 설정

```conf
module(load="imudp")
input(type="imudp" port="514")

if ($fromhost-ip != "127.0.0.1" and $fromhost-ip != "::1") then {
        action(type="omfile" file="/var/log/remote.log")
        action(type="omfile" file="/var/log/messages")
        stop
}
```

같은 `if` 블록 안에 `action`을 두 번 두면 **두 파일 모두에 기록한 뒤** `stop`으로 처리를 끝냅니다.

### 24-8. 반영과 검증

수신 서버 (web .131):

```bash
rsyslogd -N 1
systemctl restart rsyslog
systemctl status rsyslog --no-pager
ss -lunp | grep ':514'
firewall-cmd --permanent --add-port=514/udp
firewall-cmd --reload
firewall-cmd --list-ports
```

정상 예상 결과:

```text
UNCONN 0 0 0.0.0.0:514 0.0.0.0:*  users:(("rsyslogd",pid=...,fd=...))
514/udp
```

📘 참고: 514가 아닌 **비표준 포트**를 쓰려면 SELinux 포트 라벨이 필요합니다.

```bash
semanage port -a -t syslogd_port_t -p udp <포트번호>
```

송신 서버에서 테스트 로그 발생:

```bash
# 실행 서버: nfs (.136)
logger -t nfs-forward-test "NFS to Web forwarding test"

# 실행 서버: ftp (.137)
logger -t ftp-forward-test "FTP to Web forwarding test"

# 실행 서버: dns (.77)
logger -t dns-forward-test "DNS to Web forwarding test"
```

`logger -t <태그> "<메시지>"` — `-t`는 로그에 붙일 **태그(프로그램 이름)** 입니다. 나중에 `grep`으로 찾기 쉽게 하려고 씁니다.

수신 서버에서 확인 (web .131):

```bash
grep -nE 'nfs-forward-test|ftp-forward-test' /var/log/remote.log
grep -nE 'nfs-forward-test|ftp-forward-test' /var/log/messages
tail -f /var/log/remote.log        # 실시간 관찰 (Ctrl+C로 종료)
```

✅ **실제로 확인된 결과** — `/var/log/remote.log`에 다음이 기록되었습니다:

```text
nfs nfs-forward-test: NFS to Web forwarding test
ftp ftp-forward-test: FTP to Web forwarding test
```

읽는 법: 맨 앞의 `nfs` / `ftp`가 **송신 서버의 hostname**입니다. 이것이 서버별로 다르게 찍혔다는 것은 (1) hostname 설정이 정확했고 (2) 중앙 수집이 실제로 동작한다는 **직접적인 증거**입니다.

> ❓ **확인 필요**: `dns` 서버(.77)에서 보낸 로그가 수신되었다는 결과는 이번 기록에 없습니다. 위 `logger -t dns-forward-test` 를 실행해 직접 확인하십시오.

실패 시 확인 순서:

| 순서 | 어디서 | 명령 |
|---|---|---|
| 1 | 송신 서버 | `systemctl is-active rsyslog`, `rsyslogd -N 1` |
| 2 | 송신 서버 | `grep -rn '192.168.16.131' /etc/rsyslog.conf /etc/rsyslog.d/` |
| 3 | 네트워크 | 송신 서버에서 `ping -c2 192.168.16.131` |
| 4 | 수신 서버 | `ss -lunp \| grep 514` (리스너가 있는가) |
| 5 | 수신 서버 | `firewall-cmd --list-ports` (514/udp 있는가) |
| 6 | 수신 서버 | `getenforce` — Enforcing이면 `ausearch -m AVC -ts recent` |
| 7 | 수신 서버 | `tail -f /var/log/remote.log` 켜 놓고 송신 서버에서 `logger` 실행 |

---

## 25. LogAnalyzer

실행 서버: **web (192.168.16.131)**

### 25-1. 버전과 요구사항 📘

| 항목 | 값 | 근거 |
|---|---|---|
| 이 실습에서 설치한 버전 | **5.0.2** | ✅ 확인됨 |
| 작성 시점(2026-08-26) 최신 버전 | **5.0.2** (ChangeLog 기준 2026-05-07 릴리스) | 📘 GitHub `rsyslog/loganalyzer` ChangeLog |
| **PHP 요구사항** | **PHP 8.1 이상** | 📘 공식 설치 문서 |
| 웹서버 | Apache 또는 IIS | 📘 |
| MySQL/MariaDB | **선택 사항** | 📘 "Optional: MySQL database" |

> ### ✅ 이것이 PHP 8.0에서 막혔던 이유입니다
> 실습 중 PHP **8.0.30** 상태에서 LogAnalyzer 설치 화면이 진행되지 않았고, **PHP 8.1로 올린 뒤 진입에 성공**했습니다.
> 이는 버그가 아니라 **LogAnalyzer 5.x의 명시적 요구사항(PHP 8.1+)** 때문입니다. RHEL 9의 기본 PHP가 8.0이므로 (15장) 모듈 스트림 전환이 반드시 필요했습니다.

### 25-2. 공식 설치 순서 📘

공식 문서의 순서는 다음과 같습니다. **이 순서를 지키는 것이 핵심입니다.**

| 단계 | 내용 |
|---|---|
| 1 | 배포판 tarball 다운로드 후 압축 해제 |
| 2 | **`loganalyzer/src/` 폴더의 파일 전부**를 웹서버 디렉터리에 복사 |
| 3 | 웹서버가 쓰기 권한이 없다면, `contrib/` 폴더의 **`configure.sh`** 와 `secure.sh`를 함께 올리고 실행 권한 부여 후 **`./configure.sh` 실행 → `config.php` 생성** |
| 4 | 브라우저로 접속 → **웹 설치 마법사(install.php)** 진행 |
| 4.1 | Prerequisites — 파일 권한 확인 후 Next |
| 4.2 | Verify Permissions — **`config.php`가 쓰기 가능한지** 확인 |
| 4.3 | Basic Configuration — 페이지당 메시지 수(기본 50), 문자 수 제한(기본 80), 팝업 설정 |
| 4.4 | Advanced Options — 공식 문서상 "Not implemented yet" |
| 4.5 | **Data Source** — 첫 로그 소스 설정 (**diskfile / MySQL native / PDO** 중 선택) |
| 4.6 | Finish |
| 5 | 로그가 실제로 보이는지 확인 후 **`install.php` 삭제** |
| 6 | **`secure.sh` 실행** — 설치 완료 후 권한을 조여 보안 강화 |

### 25-3. ✅ 실제 발생한 순서 오류

```text
오류/증상:
  - secure.sh 를 먼저 실행함
  - 그 뒤 config.php 가 보이지 않음 / 설치 화면이 진행되지 않음

원인:
  configure.sh 와 secure.sh 의 역할을 반대로 이해했다.
    configure.sh : 설치 "전" 단계. 웹서버가 쓸 수 있는 빈 config.php 를 만든다.
    secure.sh    : 설치 "후" 단계. config.php 등의 권한을 조여 잠근다.
  설치가 끝나기 전에 secure.sh 를 돌리면 웹 마법사가 config.php 에 쓰지 못한다.

먼저 확인할 것:
  ls -l /var/www/html/loganalyzer/config.php
  ls -l /var/www/html/loganalyzer/install.php

실행 서버: web (.131)

명령어:
  cd /var/www/html/loganalyzer
  ls -l config.php
  chown apache:apache config.php
  chmod 666 config.php          # 설치 진행 중에만. 끝나면 secure.sh 로 되돌린다.

정상 결과:
  브라우저에서 install.php 마법사의 Step 2 에 "config.php ... writable" 로 표시된다.

실패하면 다음 확인:
  tail -30 /var/log/httpd/error_log
  getenforce
  ls -lZ config.php

주의할 점:
  secure.sh 는 config.php 를 "최초 생성"하는 스크립트가 아니다.
  설치 완료 후 권한을 강화하는 마무리 스크립트다.
```

| 스크립트 | 실행 시점 | 하는 일 |
|---|---|---|
| **`configure.sh`** | 설치 **전** | 웹서버가 쓸 수 있는 빈 `config.php` 생성 (권한 설정 포함) |
| **`secure.sh`** | 설치 **후** | `config.php` 권한 축소 등 보안 마무리 |

> **`touch config.php`는 공식 1차 방법이 아닙니다.** 공식 문서는 `configure.sh` 사용을 안내합니다. `contrib/`에 스크립트가 없을 때의 **fallback**으로만 쓰고, 이 경우 소유자·권한·SELinux 컨텍스트를 직접 맞춰 주어야 합니다.

### 25-4. 설치 절차 (실제 경로 기준)

```bash
# 실행 서버: web (.131)
cd /tmp
# 배포판 tarball 다운로드 (버전 번호는 작성 시점 최신 5.0.2)
# 공식 배포 페이지: https://loganalyzer.adiscon.com/downloads/
tar -xzf loganalyzer-5.0.2.tar.gz

mkdir -p /var/www/html/loganalyzer
cp -a /tmp/loganalyzer-5.0.2/src/. /var/www/html/loganalyzer/
cp -a /tmp/loganalyzer-5.0.2/contrib/configure.sh /var/www/html/loganalyzer/
cp -a /tmp/loganalyzer-5.0.2/contrib/secure.sh    /var/www/html/loganalyzer/

cd /var/www/html/loganalyzer
chmod +x configure.sh secure.sh
./configure.sh

chown -R apache:apache /var/www/html/loganalyzer
ls -l config.php
```

정상 예상 결과: `config.php`가 생성되어 있고 apache가 쓸 수 있는 권한입니다.

SELinux가 Enforcing이라면 (이 실습의 web 서버는 Disabled였습니다):

```bash
restorecon -Rv /var/www/html/loganalyzer
ls -lZ /var/www/html/loganalyzer/config.php     # httpd_sys_content_t
# config.php 에 쓰기가 필요한 동안만:
# semanage fcontext -a -t httpd_sys_rw_content_t '/var/www/html/loganalyzer/config\.php'
# restorecon -v /var/www/html/loganalyzer/config.php
```

브라우저 접속:

```text
http://192.168.16.131/loganalyzer/
http://log.kload81.com/loganalyzer/
```

### 25-5. Diskfile 로그 소스 설정

Step 4.5(Data Source)에서 선택할 값:

```text
Source Type : Diskfile
Log format  : Syslog / RSyslog
Log file    : /var/log/messages
```

또는 원격 로그를 분리해 운영한다면:

```text
Log file    : /var/log/remote.log
```

> ### ⚠️ `/var/log/syslog` 는 이 서버에 **없습니다**
> `/var/log/syslog`는 **Debian/Ubuntu** 계열의 파일명입니다. RHEL/Rocky 계열의 대응 파일은 **`/var/log/messages`** 입니다.
> 인터넷 예제를 그대로 붙여 넣다가 `/var/log/syslog`를 지정하면 LogAnalyzer가 "파일 없음"으로 아무 것도 못 보여 줍니다.

| 배포판 계열 | 일반 시스템 로그 파일 |
|---|---|
| RHEL / Rocky / CentOS | **`/var/log/messages`** |
| Debian / Ubuntu | `/var/log/syslog` |
| 이 실습의 원격 수집 로그 | `/var/log/remote.log` (직접 정의한 파일) |

확인:

```bash
ls -l /var/log/messages /var/log/syslog /var/log/remote.log
```

`/var/log/syslog`에 대해 `No such file or directory`가 나오는 것이 **정상**입니다.

### 25-6. LogAnalyzer의 두 가지 "데이터베이스" 구분

| 구분 | 언제 필요한가 | 이 실습 |
|---|---|---|
| **로그 데이터베이스** (MySQL native / PDO 소스) | 로그 자체를 DB 테이블에 저장하고 조회할 때 | ❌ 불필요 — **Diskfile 방식 사용** |
| **LogAnalyzer 사용자 DB** | 로그인/사용자별 권한/저장된 검색 기능을 쓸 때 | ❌ 사용 안 함 |

즉 **Diskfile 방식이면 MariaDB는 LogAnalyzer에 필수가 아닙니다.** 이 실습의 MariaDB는 `labdb`와 WordPress용입니다.

### 25-7. UI가 예전과 다른 문제

✅ 실습 중 "예전에 보던 LogAnalyzer 화면과 다르다"는 혼동이 있었습니다.

- 설치한 버전은 **5.0.2**로, 널리 퍼진 튜토리얼의 3.x/4.x 화면과 **레이아웃·버튼 위치가 다릅니다.**
- **특정 버튼의 위치를 절대적인 사실로 외우지 마십시오.** 버전이 오르면 바뀝니다.
- 판단 기준은 화면 모양이 아니라 **기능 이름**입니다: `Admin Center → Sources`, `Search`, `Statistics` 등.
- 본인이 설치한 버전을 항상 먼저 확인하십시오.

```bash
grep -rn "5\.0\." /var/www/html/loganalyzer/include/functions_common.php 2>/dev/null | head
# 또는 웹 화면 하단/About 표시 확인
```

### 25-8. `logger` 테스트가 화면에 바로 안 보이는 문제

```text
오류/증상:
  logger 로 메시지를 만들었는데 LogAnalyzer 화면에 안 보인다

원인(가능성, 확인 순서):
  1) LogAnalyzer 소스가 보고 있는 파일과 실제 기록된 파일이 다르다
     (예: 소스는 /var/log/messages, 실제 원격 로그는 /var/log/remote.log 에만)
  2) 화면 새로고침을 하지 않았다 / 시간 필터가 좁다
  3) Apache 가 그 로그 파일을 읽을 권한이 없다 (권한 또는 SELinux)
  4) 파일 자체에 기록되지 않았다 (rsyslog 규칙 문제)

먼저 확인할 것: 파일에는 실제로 들어갔는가?

실행 서버: web (.131)

명령어:
  logger -t hwanju-test "LogAnalyzer test message"
  grep -n "hwanju-test" /var/log/messages
  grep -n "hwanju-test" /var/log/remote.log
  grep -n '/var/log/' /var/www/html/loganalyzer/config.php
  ls -l /var/log/messages
  sudo -u apache head -c 100 /var/log/messages   # apache 가 읽을 수 있는가

정상 결과:
  grep 에 방금 넣은 메시지가 보이고,
  config.php 가 가리키는 파일과 그 파일이 일치한다.

실패하면 다음 확인:
  tail -30 /var/log/httpd/error_log
  getenforce ; ausearch -m AVC -ts recent
  systemctl status rsyslog --no-pager

주의할 점:
  LogAnalyzer 화면은 자동 갱신되지 않는 경우가 많다. 브라우저 새로고침 후 확인할 것.
  기본 파일 권한상 /var/log/messages 는 root 전용(0600)인 경우가 있어
  apache 사용자가 못 읽을 수 있다. 이때 권한을 무리하게 풀지 말고
  로그 소스를 apache 가 읽을 수 있는 별도 파일로 두는 편이 안전하다.
```

### 25-9. Web/NFS/FTP 로그를 LogAnalyzer에서 확인하기

LogAnalyzer 검색창에서 다음으로 필터링합니다:

| 찾고 싶은 것 | 검색어 예 |
|---|---|
| NFS 서버가 보낸 로그 | `nfs-forward-test` 또는 host `nfs` |
| FTP 서버가 보낸 로그 | `ftp-forward-test` 또는 host `ftp` |
| Web 서버 자신의 로그 | `hwanju-test` |
| DNS 서버 로그 | `dns-forward-test` (❓ 미확인) |

🟡 **안내됨(결과 미확인)** — LogAnalyzer **화면에서** NFS/FTP 로그가 실제로 표시된 캡처는 이번 기록에 없습니다. 파일 레벨(`grep`)에서는 ✅ 확인되었습니다. 제출 전에 화면 캡처를 남기십시오.

### 25-10. 설치 마무리 보안

```bash
cd /var/www/html/loganalyzer
./secure.sh
rm -f install.php          # 또는 chmod 000 install.php
ls -l config.php install.php 2>/dev/null
```

> `install.php`를 남겨 두면 **누구나 다시 설치 마법사를 실행해 설정을 덮어쓸 수 있습니다.** 반드시 삭제하거나 접근을 막으십시오.

---

## 26. 중앙 로그 흐름

전체 흐름을 한 장으로:

```text
[dns .77]  rsyslog  ──┐
[nfs .136] rsyslog  ──┼──  UDP 514  ──▶  [web .131]  rsyslog (imudp 리스너)
[ftp .137] rsyslog  ──┘                        │
                                               │  if $fromhost-ip 가 로컬이 아니면
                                               ├──▶ /var/log/remote.log
                                               ├──▶ /var/log/messages   (실습에서 추가)
                                               └──  stop  (이후 규칙 처리 중단)
                                                        │
[web .131] 자기 로그 ─────────────────────────────────▶ /var/log/messages
                                                        │
                                          LogAnalyzer (Diskfile 소스)
                                                        │
                                          브라우저: http://192.168.16.131/loganalyzer/
```

각 지점의 검증 명령 총정리:

| 확인 지점 | 실행 서버 | 명령 | 정상 결과 |
|---|---|---|---|
| 송신 rsyslog 문법 | dns/nfs/ftp | `rsyslogd -N 1` | `End of config validation run` |
| 송신 대상 설정 | dns/nfs/ftp | `grep -rn '192.168.16.131' /etc/rsyslog.conf /etc/rsyslog.d/` | 전달 줄이 보임 |
| 수신 리스너 | web | `ss -lunp \| grep ':514'` | `rsyslogd` 가 514 UDP LISTEN |
| 수신 방화벽 | web | `firewall-cmd --list-ports` | `514/udp` |
| 로그 도착 | web | `grep -nE 'nfs-forward-test\|ftp-forward-test' /var/log/remote.log` | ✅ 확인됨 |
| messages 병행 기록 | web | 같은 grep을 `/var/log/messages`에 | 실습 설정상 보여야 함 |
| LogAnalyzer 소스 | web | `grep -n '/var/log/' .../config.php` | 위 파일 중 하나를 가리킴 |
| 화면 표시 | 브라우저 | LogAnalyzer 검색 | 🟡 캡처 필요 |

> ⚠️ **UDP 514의 보안 한계**: UDP는 발신지 위조가 쉽고 인증이 없습니다. 즉 **같은 네트워크의 누구나 위조 로그를 밀어 넣을 수 있습니다.** 실습에서는 무방하지만, 운영에서는 (1) TCP + TLS(`imtcp` + `gtls`), (2) `AllowedSender` 제한, (3) `RateLimit.Interval`/`RateLimit.Burst`로 폭주 방지를 적용합니다. 📘

---

## 27. 홈페이지 대시보드

실행 서버: **web (192.168.16.131)** / 파일: `/var/www/html/index.html`

### 27-1. 대시보드에 넣을 내용과 원칙

| 원칙 | 이유 |
|---|---|
| **HTTP/HTTPS만 링크**로 만든다 | 브라우저가 열 수 있는 것은 웹뿐입니다 |
| FTP·SFTP·NFS·Samba는 **"접속 방법 안내"** 로 표시 | `http://ftp...` 같은 가짜 링크를 만들면 클릭 시 반드시 실패합니다 |
| **비밀번호를 절대 넣지 않는다** ⚠️ | 웹 페이지는 누구나 소스 보기가 가능합니다 |
| **"검증 예정", "추가 검증 필요" 같은 작업 중 문구를 최종 화면에 남기지 않는다** | 제출물의 완성도를 떨어뜨립니다. 대신 **완료/미완료 상태를 정확한 라벨로** 표시합니다 |
| 자체 서명 인증서 경고는 **정상 현상임을 안내** | 평가자가 오류로 오인하지 않도록 |

### 27-2. 예시 `index.html`

아래는 반응형 카드 + 주소 복사 버튼이 있는 최소 구현입니다. **비밀번호는 어디에도 없습니다.**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>kload81.com 서버 랩 대시보드</title>
<style>
  :root { --bg:#f7f8fa; --card:#fff; --line:#e3e6ea; --tx:#1c2024; --mut:#5b636b; --ok:#1a7f37; --warn:#9a6700; }
  @media (prefers-color-scheme: dark){
    :root { --bg:#14171a; --card:#1c2024; --line:#2c3238; --tx:#e6e9ec; --mut:#a0a8b0; --ok:#3fb950; --warn:#d29922; }
  }
  *{box-sizing:border-box}
  body{margin:0;padding:24px;background:var(--bg);color:var(--tx);
       font-family:system-ui,"Segoe UI","Malgun Gothic",sans-serif;line-height:1.6}
  h1{font-size:1.5rem;margin:0 0 4px}
  p.sub{color:var(--mut);margin:0 0 24px}
  .grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
  .card h2{font-size:1.05rem;margin:0 0 8px}
  .role{color:var(--mut);font-size:.85rem}
  code{background:rgba(127,127,127,.14);padding:2px 6px;border-radius:4px;
       font-family:ui-monospace,Consolas,monospace;font-size:.9em}
  .ok{color:var(--ok);font-weight:600}
  .warn{color:var(--warn);font-weight:600}
  button{margin-top:8px;padding:6px 10px;border:1px solid var(--line);border-radius:6px;
         background:transparent;color:var(--tx);cursor:pointer;font-size:.85rem}
  a{color:inherit}
</style>
</head>
<body>
  <h1>kload81.com 서버 랩</h1>
  <p class="sub">Rocky Linux 9 · 4대 구성 · 도메인 <code>kload81.com</code></p>

  <div class="grid">
    <div class="card">
      <h2>DNS</h2>
      <div class="role">BIND · 권한 네임서버</div>
      <p><code id="a1">192.168.16.77</code></p>
      <p>확인: <code>nslookup kload81.com 192.168.16.77</code></p>
      <p class="ok">동작 확인 완료</p>
      <button onclick="cp('a1')">주소 복사</button>
    </div>

    <div class="card">
      <h2>Web</h2>
      <div class="role">Apache · PHP · MariaDB · Samba · LogAnalyzer</div>
      <p><code id="a2">192.168.16.131</code></p>
      <p><a href="http://www.kload81.com/">http://www.kload81.com/</a></p>
      <p><a href="https://www.kload81.com/">https://www.kload81.com/</a>
         <span class="warn">자체 서명 인증서 — 브라우저 경고는 정상</span></p>
      <p class="ok">동작 확인 완료</p>
      <button onclick="cp('a2')">주소 복사</button>
    </div>

    <div class="card">
      <h2>LogAnalyzer</h2>
      <div class="role">중앙 로그 열람 (Diskfile 소스)</div>
      <p><a href="http://192.168.16.131/loganalyzer/">http://192.168.16.131/loganalyzer/</a></p>
      <p class="ok">설치 완료 · 버전 5.0.2</p>
    </div>

    <div class="card">
      <h2>NFS</h2>
      <div class="role">파일 공유 (UNIX) · 브라우저로 접속하지 않음</div>
      <p><code id="a3">192.168.16.136</code></p>
      <p>서버 경로 <code>/srv/nfs/hwanju</code></p>
      <p>클라이언트 마운트 <code>/mnt/nfs</code></p>
      <p class="ok">마운트 · 쓰기 확인 완료</p>
      <button onclick="cp('a3')">주소 복사</button>
    </div>

    <div class="card">
      <h2>FTP / SFTP</h2>
      <div class="role">파일 전송 · 브라우저로 접속하지 않음</div>
      <p><code id="a4">192.168.16.137</code></p>
      <p>FTP: FileZilla 등으로 <code>ftp://ftp.kload81.com</code> (TCP 21, passive 40000-40010)</p>
      <p>SFTP: WinSCP 등으로 호스트 <code>192.168.16.137</code> 포트 <code>22</code></p>
      <p class="ok">FTP 로그인 · 업로드 확인 완료</p>
      <button onclick="cp('a4')">주소 복사</button>
    </div>

    <div class="card">
      <h2>Samba</h2>
      <div class="role">Windows 파일 공유 · 브라우저로 접속하지 않음</div>
      <p>파일 탐색기 주소창에 입력:</p>
      <p><code id="a5">\\192.168.16.131\hwanju</code></p>
      <p><code>\\samba.kload81.com\hwanju</code></p>
      <button onclick="cp('a5')">경로 복사</button>
    </div>
  </div>

<script>
function cp(id){
  const t = document.getElementById(id).textContent;
  navigator.clipboard.writeText(t).then(function(){ alert('복사됨: ' + t); });
}
</script>
</body>
</html>
```

### 27-3. 배포와 확인

```bash
# 실행 서버: web (.131)
vi /var/www/html/index.html          # 위 내용 붙여넣기
curl -s http://localhost/ | head -5
ls -lZ /var/www/html/index.html
```

정상 예상 결과: `curl` 출력에 `<!DOCTYPE html>` 로 시작하는 내용이 보입니다.

> ❓ **서버 반영 확인 필요** — 이번 대화 기록에는 위 대시보드 HTML이 실제 web 서버에 배치되어 브라우저로 열린 결과가 **확인되지 않았습니다.** 배치 후 반드시 브라우저에서 직접 확인하고 캡처하십시오.

### 27-4. ⚠️ 대시보드에 넣으면 안 되는 것

| 넣지 말 것 | 이유 |
|---|---|
| 어떤 비밀번호든 (`[SAMBA_PASSWORD]` 실제 값 등) | 페이지 소스만 보면 전부 노출 |
| DB 접속 정보 | 같은 이유 |
| `http://ftp.kload81.com` 같은 **가짜 링크** | FTP는 HTTP가 아니므로 클릭 시 반드시 실패 |
| "검증 예정 / TODO / 확인 중" 문구 | 제출물에 작업 중 상태가 남음 |
| 검증 안 된 항목의 "완료" 표시 | 사실과 다름. 미검증이면 그 항목 자체를 빼거나 정확히 표기 |

---

## 28. WordPress 설치

실행 서버: **web (192.168.16.131)** ⚠️ **DNS 서버(.77)가 아닙니다.**

WordPress는 **PHP를 실행하고 DB에 접속**해야 하므로, Apache + PHP + MariaDB가 모두 있는 Web 서버에만 설치할 수 있습니다.

### 28-1. 기존 홈페이지를 보존하는 서브디렉터리 설치

```text
http://kload81.com/            → 기존 대시보드 (/var/www/html/index.html)
http://kload81.com/wordpress/  → WordPress    (/var/www/html/wordpress/)
```

이 방식은 📘 WordPress 공식 문서의 "Giving WordPress Its Own Directory" 패턴에 해당하며, 기존 사이트를 건드리지 않는다는 장점이 있습니다.

### 28-2. ✅ 실제로 진행된 파일 배치

```bash
# 실행 서버: web (.131)
cd /tmp
curl -LO https://wordpress.org/latest.tar.gz
tar -xzf latest.tar.gz

mkdir -p /var/www/html/wordpress
cp -a /tmp/wordpress/. /var/www/html/wordpress/

chown -R apache:apache /var/www/html/wordpress
find /var/www/html/wordpress -type d -exec chmod 755 {} \;
find /var/www/html/wordpress -type f -exec chmod 644 {} \;
```

명령 해설:

| 명령 | 의미 |
|---|---|
| `curl -LO` | `-L` 리다이렉트 따라감, `-O` 원격 파일명 그대로 저장 |
| `cp -a /tmp/wordpress/. <대상>/` | 끝의 `.` 덕분에 **숨김 파일(.htaccess 등)까지** 내용물만 복사 |
| `chown -R apache:apache` | Apache/php-fpm 실행 사용자가 읽고, 업로드 디렉터리에 쓸 수 있게 |
| `find ... -type d -exec chmod 755` | 디렉터리는 755 |
| `find ... -type f -exec chmod 644` | 파일은 644 |

📘 WordPress 공식 파일 권한 가이드도 **디렉터리 755 / 파일 644**를 기준으로 제시합니다.

SELinux가 Enforcing이라면 (이 서버는 Disabled였음):

```bash
restorecon -Rv /var/www/html/wordpress
# 업로드 디렉터리에 쓰기가 필요:
# semanage fcontext -a -t httpd_sys_rw_content_t '/var/www/html/wordpress/wp-content/uploads(/.*)?'
# restorecon -Rv /var/www/html/wordpress/wp-content/uploads
```

### 28-3. ✅ 실제로 성공한 DB 생성

```sql
-- 실행 서버: web (.131), mariadb -u root -p 접속 후
CREATE DATABASE wordpress_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'wordpress_user'@'localhost' IDENTIFIED BY '[WORDPRESS_DB_PASSWORD]';
GRANT ALL PRIVILEGES ON wordpress_db.* TO 'wordpress_user'@'localhost';
FLUSH PRIVILEGES;
```

`[WORDPRESS_DB_PASSWORD]` 자리에 **본인이 정한 WordPress 전용 DB 비밀번호**를 넣습니다. `labdb`나 root와 **다른 값**을 쓰십시오.

확인:

```sql
SHOW DATABASES;
SHOW GRANTS FOR 'wordpress_user'@'localhost';
```

### 28-4. `wp-config.php`

```bash
# 실행 서버: web (.131)
cd /var/www/html/wordpress
cp wp-config-sample.php wp-config.php
vi wp-config.php
```

바꿀 곳:

```php
define( 'DB_NAME',     'wordpress_db' );
define( 'DB_USER',     'wordpress_user' );
define( 'DB_PASSWORD', '[WORDPRESS_DB_PASSWORD]' );   // ← 실제 값 입력
define( 'DB_HOST',     'localhost' );
define( 'DB_CHARSET',  'utf8mb4' );
define( 'DB_COLLATE',  '' );
```

그리고 **인증 키(SALT)** 블록을 https://api.wordpress.org/secret-key/1.1/salt/ 에서 받은 값으로 교체합니다.

권한 정리:

```bash
chown apache:apache wp-config.php
chmod 640 wp-config.php
```

> ⚠️ **`wp-config.php`에는 DB 비밀번호가 평문으로 들어갑니다.**
> - 이 파일을 **웹으로 노출하거나, HTML에 붙여넣거나, GitHub 등 공개 저장소에 올리지 마십시오.**
> - 권한을 `644`보다 좁게(`640`) 두는 것이 안전합니다.
> - 과제 캡처를 찍을 때 이 파일 내용이 화면에 나오지 않게 하십시오.

### 28-5. 웹 설치 마법사

브라우저에서:

```text
http://kload81.com/wordpress/
http://192.168.16.131/wordpress/
```

진행: 언어 선택 → 사이트 제목/관리자 계정 → 설치 → 로그인

### 28-6. ✅ 실제 진행 상태 (정확히 이대로만 기록합니다)

| 단계 | 상태 |
|---|---|
| WordPress 파일 배치 | ✅ **완료 확인** |
| WordPress DB 생성 (`wordpress_db` / `wordpress_user`) | ✅ **완료 확인** |
| `wp-config.php` 생성 | ✅ **완료 안내 및 확인** |
| **WordPress 웹 설치 완료** | ❌ **확인되지 않음** |
| **WordPress 관리자 로그인** | ❌ **확인되지 않음** |

> 즉 **WordPress는 아직 "설치 완료" 상태가 아닙니다.** 대시보드나 제출물에 "완료"로 적지 마십시오. 마지막 웹 마법사를 끝낸 뒤에 상태를 갱신하십시오.

### 28-7. ⚠️ 버전 요구사항 — 현재 실습 환경과의 차이 📘

작성 시점(2026-08-26) 기준 WordPress 공식 요구사항:

| 항목 | WordPress 공식 권장 | 이 실습 환경 | 판정 |
|---|---|---|---|
| PHP | **8.3 이상 권장** (7.4+에서도 동작하지만 보안 취약 가능성 경고) | **8.1.32** ✅ 확인됨 | ⚠️ 권장보다 낮음 — 동작은 가능 |
| 데이터베이스 | **MariaDB 10.11+ 또는 MySQL 8.0+** | **MariaDB 10.5.29** ✅ 확인됨 | ⚠️ 권장보다 낮음 — 동작은 가능 |
| HTTPS | "모든 설치에 필수(Required for every install)" | 자체 서명 인증서로 구성 (🟡 브라우저 확인 미기록) | 실습 수준 충족 |
| 최신 WordPress 버전 | **7.1** (2026-08-19 릴리스) | `latest.tar.gz`로 받았으므로 최신 계열 | ❓ 실제 설치 버전은 관리자 화면에서 확인 필요 |

**해석**: PHP 8.1과 MariaDB 10.5는 **최소 요구는 넘지만 공식 권장 아래**입니다. 실습에서는 문제없이 동작할 가능성이 높으나, 일부 최신 플러그인/테마가 더 높은 버전을 요구할 수 있습니다.

> ⚠️ **버전을 올리기 전에**: PHP나 MariaDB 스트림을 바꾸면 **LogAnalyzer·기존 홈페이지·Samba 등 다른 실습이 깨질 수 있습니다.** 반드시 (1) VM 스냅샷, (2) `rpm -qa` 목록 백업, (3) 변경 후 전 서비스 재검증 순으로 진행하십시오.

---

## 29. 실제 과제 진행 상태

이 표는 **대화 기록에 남은 근거만**을 기준으로 작성했습니다. 근거가 없는 항목을 "완료"로 올리지 않았습니다.

| 항목 | 실행 위치 | 검증 명령/방법 | 실제 확인 여부 | 상태 |
|---|---|---|---|---|
| DNS 서비스 기동 | DNS .77 | `systemctl is-active named` | 🟡 서비스 상태 출력은 기록에 없음. 단, 외부 조회가 성공했으므로 동작 중으로 추정 | **확인 필요(직접 캡처)** |
| `zone "."` 오류 해결 | DNS .77 | `named-checkconf -z` | ✅ 오류 메시지가 기록되어 원인 특정됨. 수정 후 재검사 출력은 미기록 | **확인 필요** |
| 도메인 A 레코드 조회 | Windows → DNS .77 | `nslookup kload81.com 192.168.16.77` | ✅ **성공 확인됨** | **완료** |
| 기본 DNS 경유 조회 | Windows | `nslookup kload81.com` | ✅ **실패 확인됨** (8.8.8.8 사용) — 원인 규명 완료 | **완료(원인 파악)** |
| Web(Apache) | Web .131 | `systemctl status httpd` | ✅ **active 확인됨** | **완료** |
| HTTPS(자체 서명) | Web .131 | `httpd -t`, `curl -k` | 🟡 명령만 안내. 브라우저/`curl` 결과 미기록 | **확인 필요** |
| PHP | Web .131 | `php -v` | ✅ **8.1.32 확인됨** | **완료** |
| MariaDB 서비스 | Web .131 | `systemctl status mariadb` | ✅ **active 확인됨**, 버전 **10.5.29** | **완료** |
| `labdb` / `labuser` 생성 | Web .131 | `SHOW DATABASES;` | 🟡 SQL 문법 오류→수정까지는 확인. 최종 생성 결과 출력 미기록 | **확인 필요** |
| Samba 설정 오류(`passdb backend`) | Web .131 | `testparm` | ✅ 위치 오류 확인 및 수정 방향 확정 | **완료(원인 파악)** |
| Samba Windows 접속 | Windows → Web .131 | `\\192.168.16.131\hwanju` | 🟡 접속 성공 화면 미기록 | **확인 필요** |
| SELinux `samba_share_t` | Web .131 | `restorecon`, `ls -Z` | ✅ `Relabeled ...` 출력 확인됨(정상) | **완료** |
| NFS export | NFS .136 | `exportfs -v`, `showmount -e` | 🟡 명령 안내 중심. 출력 미기록 | **확인 필요** |
| NFS 마운트 | FTP .137 | `findmnt /mnt/nfs` | ✅ 마운트 후 접근 시도에서 `허가 거부` 발생 → 마운트 자체는 되어 있었음 | **완료(마운트)** |
| `root_squash` 권한 거부 | FTP .137 | `ls /mnt/nfs` (root) | ✅ **`허가 거부` 확인됨** → 원인 규명 완료 | **완료(원인 파악)** |
| hwanju 로 NFS 쓰기 | FTP .137 → NFS .136 | `su - hwanju` 후 파일 생성 | 🟡 절차는 확정. 실제 파일 생성 출력 미기록 | **확인 필요** |
| UID/GID 2001 일치 | NFS .136 / FTP .137 | `id hwanju` | ✅ 기준값 2001/2001 확정 | **완료(기준 확정)** |
| `/etc/fstab` NFS 자동 마운트 | FTP .137 | `mount -a`, `findmnt` | 🟡 한 줄 추가 방침 확정. `mount -a` 결과 미기록 | **확인 필요** |
| FTP 로그인·업로드 | FTP .137 | `ftp 127.0.0.1` → `put` | ✅ **`230 Login successful.` / `226 Transfer complete.` 확인됨** (hwanju 계정) | **완료** |
| `ftptest` 계정 로그인 | FTP .137 | `ftp` | ✅ **실패 확인됨** → hwanju로 전환 | **완료(전환 기록)** |
| SFTP 접속 | Windows/리눅스 → FTP .137 | WinSCP / `sftp` | ❌ 접속 결과 미확인 | **확인 필요** |
| rsyslog 송신 설정 | DNS/NFS/FTP | `rsyslogd -N 1` | 🟡 설정 확정. 검증 출력 미기록 | **확인 필요** |
| rsyslog 수신 리스너 | Web .131 | `ss -lunp \| grep 514` | 🟡 명령 안내. 출력 미기록 | **확인 필요** |
| **원격 로그 실제 수신** | Web .131 | `grep ... /var/log/remote.log` | ✅ **`nfs nfs-forward-test` / `ftp ftp-forward-test` 확인됨** | **완료** |
| DNS 서버 로그 전달 | DNS .77 → Web .131 | `logger` + `grep` | ❌ 기록 없음 | **확인 필요** |
| `stop` 으로 인한 messages 누락 | Web .131 | `grep ... /var/log/messages` | ✅ 원인 규명 및 `action` 2개 추가로 대응 | **완료(원인 파악)** |
| LogAnalyzer 설치 | Web .131 | 브라우저 설치 마법사 | ✅ **버전 5.0.2 설치, 설치 화면 진입 확인됨** (PHP 8.1 전환 후) | **완료** |
| LogAnalyzer 로그 표시 | 브라우저 | 화면에서 NFS/FTP 로그 확인 | ❌ 화면 캡처 미기록 (파일 레벨은 ✅) | **확인 필요** |
| `secure.sh` 최종 실행 | Web .131 | `./secure.sh` | ❌ 설치 완료 후 재실행 결과 미기록 | **확인 필요** |
| 홈페이지 대시보드 서버 반영 | Web .131 | 브라우저 접속 | ❌ **서버 반영 확인 필요** | **확인 필요** |
| WordPress 파일 배치 | Web .131 | `ls /var/www/html/wordpress` | ✅ **완료 확인** | **완료** |
| WordPress DB 생성 | Web .131 | `SHOW DATABASES;` | ✅ **완료 확인** | **완료** |
| `wp-config.php` 생성 | Web .131 | `ls -l wp-config.php` | ✅ **완료 안내 및 확인** | **완료** |
| **WordPress 웹 설치 완료** | 브라우저 | `/wordpress/` 마법사 | ❌ **확인되지 않음** | **미완료** |
| **WordPress 관리자 로그인** | 브라우저 | `/wordpress/wp-admin/` | ❌ **확인되지 않음** | **미완료** |
| SELinux 모드(Web) | Web .131 | `getenforce` | ✅ **Disabled 로 변경 확인됨** | **완료(⚠️ 운영 비권장)** |

---

## 30. 오류·원인·해결책 표

한눈에 보는 요약입니다. 각 항목의 상세는 본문 절 번호를 참고하십시오.

| # | 오류/증상 | 실행 위치 | 근본 원인 | 해결 | 상세 |
|---|---|---|---|---|---|
| 1 | `zone ./IN: bad zone`, `NS 'dns.kload81.com' has no address records` | DNS .77 | 루트 힌트 zone `"."` 안에 사용자 zone 설정을 넣음 | `zone "."`(type hint)과 `zone "kload81.com"`(type master)을 분리 | 9-3 |
| 2 | `getnet: command not found` | 전 서버 | 명령 오타 | `getent hosts <이름>` | 8-3 |
| 3 | `options` 블록 중복 | DNS .77 | 설정을 이어 붙이며 두 번 작성 | `grep -n '^options' /etc/named.conf` 결과가 1줄이 되게 | 9-2 |
| 4 | `nslookup kload81.com` 실패 | Windows | 기본 DNS가 8.8.8.8 (사설 도메인 모름) | 서버 지정 조회로 검증, 필요 시 Host-Only 어댑터 DNS를 .77로. BIND `forwarders` 선확인 | 11-2, 11-3 |
| 5 | `서버: Unknown` | Windows | reverse(PTR) zone 없음 | 오류 아님. A 레코드 조회 성공 여부로 판단 | 11-4 |
| 6 | MariaDB `character utf8mb4` 문법 오류 | Web .131 | `CHARACTER SET`은 두 단어 | `CREATE DATABASE ... CHARACTER SET utf8mb4 COLLATE ...` | 16-3 |
| 7 | `Query OK, 0 rows affected` 를 실패로 오해 | Web .131 | DDL/관리 명령은 행을 바꾸지 않음 | `ERROR`가 없으면 성공 | 16-5 |
| 8 | `root@localhost` 혼동 | 전 서버 | 터미널 창 제목일 뿐 | `hostname`, 프롬프트, `hostname -I`로 확인 | 6-1, 17-8 |
| 9 | Samba `passdb backend` 위치 오류 | Web .131 | (G) global 전용 파라미터를 공유 섹션에 배치 | `[global]`로 이동 후 `testparm` | 17-2 |
| 10 | Windows 탐색기에서 Samba 접근 불가 | Windows | 크롬 주소창/검색창에 UNC 입력 | **파일 탐색기 주소창**에 `\\192.168.16.131\hwanju` | 17-6 |
| 11 | `SMB1 disabled -- no workgroup available` | Web .131 | SMB1 브라우징 비활성 | SMB2/3 direct access에서는 치명적 아님. SMB1을 켜지 말 것 | 17-7 |
| 12 | `Win + R`이 VirtualBox에 잡힘 | Windows | VM 창에 키보드 포커스가 있음 | Host 키(기본 오른쪽 Ctrl)로 포커스 해제 후 실행 | 17-6 |
| 13 | NFS `허가 거부` (root인데도) | FTP .137 | `root_squash`가 클라이언트 root를 익명으로 매핑 | 일반 사용자(hwanju)로 접근 + 양쪽 UID/GID 2001 일치 | 21-1 |
| 14 | `no_root_squash`로 해결하려는 시도 | NFS .136 | 보안 기능을 끄는 잘못된 접근 | 사용하지 말 것 ⚠️ | 21-2 |
| 15 | `/etc/fstab` 전체 삭제 질문 | FTP .137 | fstab의 역할 오해 | 기존 줄 유지, **맨 끝에 NFS 한 줄만 추가** | 20-3 |
| 16 | `mount -a` 실패 | FTP .137 | 이름 해석/마운트지점/export/방화벽/오타 | `getent hosts`, `showmount -e`, `findmnt --verify` | 20-3 |
| 17 | FTP `530 Login incorrect` | FTP .137 | 계정 없음/셸 미등록/차단 목록/`local_enable` 미반영 | `hwanju` 계정으로 전환하여 성공 | 22-5 |
| 18 | `passwd 1234` 오해 | FTP .137 | `passwd`의 인자는 **사용자명** | `passwd hwanju` 후 대화형 입력 | 22-6 |
| 19 | `500 OOPS: cannot change directory` | FTP .137 | `local_root` 경로 부재/마운트 해제/권한/SELinux | `findmnt /mnt/nfs`, `runuser -u hwanju -- ls /mnt/nfs` | 22-8 |
| 20 | `500 OOPS: refusing to run with writable root inside chroot()` | FTP .137 | chroot 루트에 쓰기 권한 | `allow_writeable_chroot=YES` (실습) / 루트는 읽기전용 + 하위 쓰기 디렉터리 (운영) | 22-8 |
| 21 | `553 Could not create file` | FTP .137 | `write_enable`/유닉스 권한/NFS squash/SELinux | 단계별 절연 테스트 | 22-8 |
| 22 | `ftpd_use_nfs` / `ftpd_full_access` 혼용 | FTP .137 | boolean 범위 차이 미인지 | 좁은 `ftpd_use_nfs` 우선, `ftpd_full_access`는 최후 fallback ⚠️ | 22-9 |
| 23 | SELinux `Enforcing`으로 인한 차단 | 전 서버 | 정책상 접근 거부 | `ausearch`/`sealert`로 원인 확인 → fcontext/boolean으로 최소 허용 | 18-3 |
| 24 | `restorecon`의 `Relabeled` 출력을 오류로 오해 | 전 서버 | 성공 메시지임 | 정상. `ls -Z`로 결과 확인 | 18-4 |
| 25 | `/var/log/messages`에 Apache 컨텍스트 지정 | Web .131 | 시스템 로그 파일의 라벨을 변경 | `restorecon`으로 원복. 로그 파일 라벨은 유지 | 18-5 |
| 26 | `reboot` 후 PuTTY 연결 끊김 | 전 서버 | 재부팅 중 SSH 세션 종료 | 정상. 잠시 후 재접속 → `getenforce` 확인 | 18-1 |
| 27 | `config.php` 없음 | Web .131 | `configure.sh`를 실행하지 않음 | `contrib/configure.sh` 실행 (또는 fallback으로 수동 생성) | 25-3 |
| 28 | `secure.sh`를 너무 일찍 실행 | Web .131 | 두 스크립트의 순서를 반대로 이해 | `configure.sh`(설치 전) → 웹 마법사 → `secure.sh`(설치 후) | 25-3 |
| 29 | PHP 8.0에서 LogAnalyzer 설치 진행 불가 | Web .131 | LogAnalyzer 5.x는 **PHP 8.1+** 요구 | `dnf module install php:8.1` 후 `php-fpm`/`httpd` 재시작 | 25-1 |
| 30 | LogAnalyzer 화면이 예전과 다름 | 브라우저 | 설치 버전이 5.0.2 (튜토리얼은 3.x/4.x) | 버튼 위치가 아니라 **기능 이름** 기준으로 탐색 | 25-7 |
| 31 | `/var/log/syslog` 없음 | Web .131 | Debian/Ubuntu 파일명 | RHEL 계열은 `/var/log/messages` | 25-5 |
| 32 | `logger` 메시지가 LogAnalyzer에 안 보임 | Web .131 | 소스 파일 불일치 / 새로고침 / 읽기 권한 | `grep`으로 파일 확인 → `config.php`의 경로 대조 | 25-8 |
| 33 | 원격 로그가 `remote.log`에만 있고 `messages`에 없음 | Web .131 | rsyslog `stop`이 이후 규칙 처리를 중단 | 소스를 `remote.log`로 바꾸거나(권장), `action`을 두 개 두어 병행 기록(실습 채택) | 24-5, 24-6 |
| 34 | FTP/NFS/Samba를 브라우저로 접속 시도 | Windows | 프로토콜 오해 | 브라우저는 HTTP/HTTPS만. 각 전용 클라이언트 사용 | 4, 27-1 |
| 35 | WordPress 권장 버전과 실습 버전 차이 | Web .131 | PHP 8.1 / MariaDB 10.5 는 권장(8.3 / 10.11+) 미만 | 동작 가능하나 문서에 명시. 업그레이드는 스냅샷 후 | 28-7 |
| 36 | 초기 예시 IP(.81~.84) 잔존 | 전 서버 | 초반 예시를 그대로 복사 | `grep -rn '192\.168\.16\.8[1-4]'` 로 전수 점검 | 3-2 |
| 37 | `/etc/exports`에서 IP와 괄호 사이 공백 | NFS .136 | 공백이 있으면 "그 호스트는 기본옵션 + 모든 호스트에 그 옵션"으로 해석 | 공백 없이 `IP(opt,opt)` | 19-3 |

---

## 31. 최종 검증 체크리스트

제출 전에 **순서대로** 실행하십시오. 각 줄의 실행 서버를 확인하고, 출력이 예상과 다르면 해당 절로 돌아갑니다.

### 31-1. DNS (실행 서버: dns .77)

```bash
hostname                                   # dns
systemctl is-active named                  # active
named-checkconf                            # 출력 없음
named-checkconf -z                         # loaded serial ...
named-checkzone kload81.com /var/named/kload81.com.zone   # OK
dig +short @192.168.16.77 www.kload81.com  # 192.168.16.131
dig +short @192.168.16.77 nfs.kload81.com  # 192.168.16.136
dig +short @192.168.16.77 ftp.kload81.com  # 192.168.16.137
dig +short @192.168.16.77 google.com       # forwarder 동작 확인
firewall-cmd --list-services               # dns 포함
```

### 31-2. Web (실행 서버: web .131)

```bash
hostname                                   # web
systemctl is-active httpd php-fpm mariadb smb rsyslog
php -v                                     # 8.1.32
mariadb --version                          # 10.5.29
httpd -t                                   # Syntax OK
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/
curl -k -s -o /dev/null -w '%{http_code}\n' https://localhost/
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/loganalyzer/
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/wordpress/
testparm -s | head -20
ss -lntp | grep -E ':80|:443|:445'
ss -lunp | grep ':514'
firewall-cmd --list-all
getenforce
```

기대값: HTTP 코드는 `200`(또는 WordPress 미설치 시 리다이렉트 `30x`).

### 31-3. NFS (실행 서버: nfs .136)

```bash
hostname                                   # nfs
systemctl is-active nfs-server
exportfs -v                                # rw, root_squash 확인
id hwanju                                  # uid=2001 gid=2001
ls -ln /srv/nfs/hwanju
firewall-cmd --list-services               # nfs 포함
```

### 31-4. FTP / NFS Client (실행 서버: ftp .137)

```bash
hostname                                   # ftp
systemctl is-active vsftpd sshd rsyslog
findmnt /mnt/nfs                           # nfs4 마운트
id hwanju                                  # uid=2001 gid=2001
runuser -u hwanju -- touch /mnt/nfs/final-check.txt
runuser -u hwanju -- ls -l /mnt/nfs/final-check.txt
ss -lntp | grep -E ':21|:22'
firewall-cmd --list-all                    # ftp, 40000-40010/tcp
showmount -e 192.168.16.136
```

그리고 NFS 서버(.136)에서 파일이 보이는지 교차 확인:

```bash
ls -l /srv/nfs/hwanju/final-check.txt
```

### 31-5. 중앙 로그 (송신 3대 → web .131)

```bash
# dns .77 / nfs .136 / ftp .137 각각
logger -t final-check-$(hostname) "final verification from $(hostname)"

# web .131
grep -n 'final-check-' /var/log/remote.log
grep -n 'final-check-' /var/log/messages
```

기대값: `dns`, `nfs`, `ftp` 세 hostname이 모두 보여야 합니다.

### 31-6. Windows 쪽

```cmd
nslookup kload81.com 192.168.16.77
nslookup www.kload81.com 192.168.16.77
ping 192.168.16.131
```

- 파일 탐색기 주소창: `\\192.168.16.131\hwanju` → 로그인 후 파일 생성 테스트
- 브라우저: `http://192.168.16.131/`, `http://192.168.16.131/loganalyzer/`, `http://192.168.16.131/wordpress/`
- HTTPS: `https://192.168.16.131/` → 경고 화면 → 고급 → 계속

### 31-7. 보안 마무리 점검

```bash
# web .131
rm -f /var/www/html/info.php
ls -l /var/www/html/loganalyzer/install.php 2>/dev/null    # 없어야 함
ls -l /var/www/html/wordpress/wp-config.php                # 640 권장
grep -rn 'PASSWORD' /var/www/html/index.html               # 아무 것도 안 나와야 함
```

```sql
-- web .131
SELECT User, Host FROM mysql.user;   -- root 가 % 로 열려 있지 않은지 확인
```

---

## 32. 제출용 캡처 목록

각 캡처에 **프롬프트(`[root@web ~]#`)가 함께 보이게** 찍으십시오. 어느 서버에서 실행했는지가 증거가 됩니다.

| # | 캡처 대상 | 실행 위치 | 명령/화면 |
|---|---|---|---|
| 1 | 4대 hostname과 IP | 각 서버 | `hostname; hostname -I` |
| 2 | DNS 서비스와 zone 검사 | dns .77 | `systemctl is-active named; named-checkconf -z` |
| 3 | DNS 조회 성공 | dns .77 또는 타 서버 | `dig @192.168.16.77 www.kload81.com` |
| 4 | Windows DNS 조회 | Windows | `nslookup kload81.com 192.168.16.77` |
| 5 | 홈페이지 | 브라우저 | `http://192.168.16.131/` (또는 `http://www.kload81.com/`) |
| 6 | HTTPS 인증서 경고 + 접속 성공 | 브라우저 | `https://www.kload81.com/` 두 장(경고/접속 후) |
| 7 | PHP·MariaDB 버전 | web .131 | `php -v; mariadb --version` |
| 8 | DB/사용자 생성 결과 | web .131 | `SHOW DATABASES; SHOW GRANTS FOR 'wordpress_user'@'localhost';` |
| 9 | Samba 설정 검사 | web .131 | `testparm -s \| head -25` |
| 10 | Samba 접속 성공 | Windows | 파일 탐색기의 `\\192.168.16.131\hwanju` 내용 |
| 11 | SELinux 컨텍스트 | web .131 | `ls -ldZ /srv/samba/hwanju` |
| 12 | NFS export 목록 | nfs .136 | `exportfs -v` |
| 13 | NFS 마운트 | ftp .137 | `findmnt /mnt/nfs` |
| 14 | root_squash 재현과 해결 | ftp .137 | `ls /mnt/nfs`(root, 거부) → `runuser -u hwanju -- ls -l /mnt/nfs`(성공) 두 장 |
| 15 | NFS 서버에서 파일 확인 | nfs .136 | `ls -l /srv/nfs/hwanju` |
| 16 | fstab 한 줄 추가 | ftp .137 | `tail -3 /etc/fstab; findmnt /mnt/nfs` |
| 17 | FTP 로그인·업로드 | ftp .137 | `ftp 127.0.0.1` 세션의 `230`/`226` 메시지 |
| 18 | FTP 방화벽 | ftp .137 | `firewall-cmd --list-all` |
| 19 | SFTP 접속 | Windows | WinSCP 접속 후 파일 목록 |
| 20 | rsyslog 수신 리스너 | web .131 | `ss -lunp \| grep 514` |
| 21 | 원격 로그 수신 | web .131 | `grep -nE 'nfs-forward-test\|ftp-forward-test' /var/log/remote.log` |
| 22 | LogAnalyzer 메인 화면 | 브라우저 | `http://192.168.16.131/loganalyzer/` |
| 23 | LogAnalyzer에서 NFS/FTP 로그 | 브라우저 | 검색 결과 화면 |
| 24 | WordPress 설치 화면/완료 | 브라우저 | `http://kload81.com/wordpress/` |
| 25 | WordPress 관리자 대시보드 | 브라우저 | `/wordpress/wp-admin/` |

> ⚠️ **캡처에 비밀번호가 찍히지 않게 하십시오.** `wp-config.php` 열람 화면, `smbpasswd` 입력 화면, `mariadb-secure-installation` 진행 화면 등이 위험합니다.

---

## 33. 공식 참고자료

모든 링크는 **2026-08-26에 확인**했습니다. 버전·기본값은 이후 변경될 수 있습니다.

### Red Hat Enterprise Linux 9 (Rocky Linux 9 호환)

| 주제 | 문서 | URL | 확인일 |
|---|---|---|---|
| BIND DNS 서버 | Setting up and configuring a BIND DNS server | https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_networking_infrastructure_services/assembly_setting-up-and-configuring-a-bind-dns-server_networking-infrastructure-services | 2026-08-26 |
| Samba 서버 | Using Samba as a server | https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_using_network_file_services/assembly_using-samba-as-a-server_configuring-and-using-network-file-services | 2026-08-26 |
| NFS 서버 | Deploying an NFS server | https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_using_network_file_services/deploying-an-nfs-server_configuring-and-using-network-file-services | 2026-08-26 |
| SELinux 문제 해결 | Troubleshooting problems related to SELinux | https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/using_selinux/troubleshooting-problems-related-to-selinux_using-selinux | 2026-08-26 |
| 원격 로깅 | Configuring a remote logging solution | https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/security_hardening/assembly_configuring-a-remote-logging-solution_security-hardening | 2026-08-26 |
| PHP | Using the PHP scripting language | https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/installing_and_using_dynamic_programming_languages/assembly_using-the-php-scripting-language_installing-and-using-dynamic-programming-languages | 2026-08-26 |
| Apache | Setting up the Apache HTTP web server | https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/deploying_web_servers_and_reverse_proxies/setting-apache-http-server_deploying-web-servers-and-reverse-proxies | 2026-08-26 |
| MariaDB | Using MariaDB | https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_using_database_servers/using-mariadb_configuring-and-using-database-servers | 2026-08-26 |

**이 문서에서 실제로 인용한 확인 사실**

| 확인 내용 | 출처 |
|---|---|
| RHEL 9 기본 PHP는 **8.0**, 8.1/8.2는 모듈 스트림. Apache는 **php-fpm**으로 연동 | RHEL 9 PHP 문서 |
| RHEL 9 기본 MariaDB는 **10.5**, 10.11은 9.4부터, 11.8은 9.8부터 | RHEL 9 MariaDB 문서 |
| Samba 독립형 서버는 **`smb`만 활성화**, `nmbd`는 선택(현대 SMB는 DNS 사용) | RHEL 9 Samba 문서 |
| 인증서 `/etc/pki/tls/certs/`, 개인키 `/etc/pki/tls/private/` + `chmod 600` | RHEL 9 Apache 문서 |
| NFSv4 전용이면 rpcbind 불필요, 방화벽은 `nfs`,`rpc-bind`,`mountd` | RHEL 9 NFS 문서 |
| rsyslog 수신 `module(load="imudp")` + `input(type="imudp" port="514")`, 방화벽 `514/udp`, 비표준 포트는 `semanage port -a -t syslogd_port_t` | RHEL 9 Security Hardening |
| `restorecon`의 relabeled 출력은 라벨이 올바른 타입으로 변경되었다는 뜻 | RHEL 9 SELinux 문서 |

### rsyslog

| 주제 | URL | 확인일 |
|---|---|---|
| imudp 모듈 | https://docs.rsyslog.com/doc/configuration/modules/imudp.html | 2026-08-26 |
| omfwd 모듈 | https://docs.rsyslog.com/doc/configuration/modules/omfwd.html | 2026-08-26 |
| 원격 서버 튜토리얼 | https://docs.rsyslog.com/doc/getting_started/beginner_tutorials/06-remote-server.html | 2026-08-26 |
| 멀티 ruleset | https://docs.rsyslog.com/doc/concepts/multi_ruleset.html | 2026-08-26 |

확인 사실: 최소 수신 설정은 `module(load="imudp")` + `input(type="imudp" port="514")`이며 기본 포트는 514/UDP. `AllowedSender`, `RateLimit.Interval`/`RateLimit.Burst` 로 보안·폭주 대응 가능.

### LogAnalyzer

| 주제 | URL | 확인일 |
|---|---|---|
| 설치 가이드 (공식, 리다이렉트 후 주소) | https://doc.loganalyzer.adiscon.com/user-guide/chapters/install/ | 2026-08-26 |
| 원래 링크 (302 리다이렉트됨) | https://rsyslog.github.io/loganalyzer/user-guide/chapters/install/ | 2026-08-26 |
| 소스 저장소 | https://github.com/rsyslog/loganalyzer | 2026-08-26 |
| ChangeLog | https://github.com/rsyslog/loganalyzer/blob/master/ChangeLog | 2026-08-26 |

확인 사실: **최신 버전 5.0.2 (2026-05-07 릴리스)**, 요구사항 **PHP 8.1 이상**, MySQL은 선택. 설치 순서는 `src/` 배치 → `configure.sh`로 `config.php` 생성 → 웹 마법사(Prerequisites → Verify Permissions → Basic Configuration → Advanced(미구현) → Data Source → Finish) → `install.php` 삭제 → `secure.sh`.

### WordPress

| 주제 | URL | 확인일 |
|---|---|---|
| 요구사항 | https://wordpress.org/about/requirements/ | 2026-08-26 |
| 다운로드 | https://wordpress.org/download/ | 2026-08-26 |
| 릴리스 목록 | https://wordpress.org/download/releases/ | 2026-08-26 |
| 파일 권한 | https://developer.wordpress.org/advanced-administration/server/file-permissions/ | 2026-08-26 |
| 서브디렉터리 설치 | https://developer.wordpress.org/advanced-administration/server/wordpress-in-directory/ | 2026-08-26 |
| HTTPS | https://developer.wordpress.org/advanced-administration/security/https/ | 2026-08-26 |
| wp-config.php | https://developer.wordpress.org/advanced-administration/wordpress/wp-config/ | 2026-08-26 |

확인 사실: 권장 **PHP 8.3 이상**, **MariaDB 10.11+ 또는 MySQL 8.0+**, **HTTPS는 모든 설치에 필수**로 명시. PHP 7.4+/MySQL 5.5.5+ 에서도 동작하나 보안 취약 가능성 경고. 최신 릴리스는 **7.1 (2026-08-19)**.

### Samba / NFS / vsftpd / MariaDB man·공식 문서

| 주제 | URL | 확인일 |
|---|---|---|
| `smb.conf(5)` | https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html | 2026-08-26 |
| `exports(5)` | https://man7.org/linux/man-pages/man5/exports.5.html | 2026-08-26 |
| `vsftpd.conf` 옵션 | https://security.appspot.com/vsftpd/vsftpd_conf.html | 2026-08-26 |
| `ftpd_selinux(8)` | https://www.systutorials.com/docs/linux/man/8-ftpd_selinux/ | 2026-08-26 |
| MariaDB `CREATE DATABASE` | https://mariadb.com/docs/server/reference/sql-statements/data-definition/create/create-database | 2026-08-26 |
| MariaDB `CREATE USER` | https://mariadb.com/docs/server/reference/sql-statements/account-management-sql-statements/create-user | 2026-08-26 |
| MariaDB `GRANT` | https://mariadb.com/docs/server/reference/sql-statements/account-management-sql-statements/grant | 2026-08-26 |

확인 사실:

- `exports(5)`: **"No whitespace is permitted between a client and its option list."**, 기본값은 `ro`, `sync`(1.0.0 이후), `root_squash`, `no_subtree_check`(1.1.0 이후).
- `smb.conf(5)`: `passdb backend`/`security`/`workgroup`/`map to guest`는 **(G) global 전용**, `valid users`/`force user`/`create mask`는 **(S) 공유 단위**. `create mask` 기본값 `0744`.
- `vsftpd.conf`: 기본값 `anonymous_enable=YES`, `local_enable=NO`, `write_enable=NO`, `local_umask=077`, `chroot_local_user=NO`, `pasv_enable=YES`.
- `ftpd_selinux(8)`: `ftpd_use_nfs`= "ftpd can use NFS used for public file transfer services", `ftpd_full_access`= "ftpd can login to local users and can read and write all files on the system, governed by DAC". 둘 다 기본 off.
- MariaDB: `[DEFAULT] CHARACTER SET [=] charset_name`, `[DEFAULT] COLLATE [=] collation_name` — **CHARACTER SET은 두 단어**.

### Rocky Linux (참고 — 버전 확인 주의)

| 주제 | URL | 비고 |
|---|---|---|
| WordPress on LAMP | https://docs.rockylinux.org/10/guides/cms/wordpress-on-lamp/ | ⚠️ **Rocky 10 문서**입니다. 이 실습은 Rocky 9이므로 패키지 버전·모듈 스트림이 다를 수 있습니다. 적용 전 RHEL 9 문서와 대조하십시오 |
| PHP 가이드 | https://docs.rockylinux.org/10/guides/web/php/ | 위와 동일한 주의 |
| MariaDB 가이드 | https://docs.rockylinux.org/10/guides/database/database_mariadb-server/ | 위와 동일한 주의 |

### 출처가 서로 다른 경우

| 항목 | 차이 | 이 문서의 판단 |
|---|---|---|
| Apache 방화벽 개방 | RHEL 9 문서는 `--add-port=80/tcp` / firewalld는 `--add-service=http` 제공 | **둘 다 유효**. 서비스명이 가독성이 좋아 이 문서는 서비스명을 우선 표기 |
| `allow_writeable_chroot` | upstream `vsftpd.conf` 문서에 **항목 없음**. 배포판 vsftpd 3.0.x에서는 제공 | ❓ **확인 필요** — 서버에서 `man 5 vsftpd.conf`로 직접 확인하도록 안내 |
| Rocky 10 문서 vs RHEL 9 | 패키지 버전·모듈 스트림 상이 | **RHEL 9 문서를 우선** 적용 |
| LogAnalyzer 문서 위치 | `rsyslog.github.io`는 `doc.loganalyzer.adiscon.com`으로 302 리다이렉트 | 최종 주소를 정본으로 사용 |

### 공식 문서가 없어 "실습 관찰"로 분류한 것

- LogAnalyzer 화면 레이아웃이 5.x에서 3.x/4.x와 다르다는 점 (버전별 UI 차이는 문서화되어 있지 않음)
- 이 실습 환경의 물리 LAN과 Host-Only 대역 중복이 실제로 어떤 라우팅 우선순위를 갖는지 (❓ 확인 필요)

---

## 34. 부록: 잘못된 명령과 올바른 명령 비교

| # | ❌ 잘못된 것 | ✅ 올바른 것 | 무엇이 문제였나 |
|---|---|---|---|
| 1 | `getnet hosts web.kload81.com` | `getent hosts web.kload81.com` | 명령 이름 오타. `getent` = **get entries** from NSS |
| 2 | `passwd 1234` | `passwd hwanju` (이후 대화형 입력) | `passwd`의 인자는 **사용자명**이지 비밀번호가 아님 |
| 3 | `create database labdb character utf8mb4 ...` | `CREATE DATABASE labdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;` | `CHARACTER SET`은 **두 단어** |
| 4 | `zone "." { ... kload81.com 설정 ... };` | `zone "." { type hint; file "named.ca"; };` 와 `zone "kload81.com" { type master; ... };` **분리** | 루트 힌트 zone과 사용자 zone은 별개 |
| 5 | `options { ... }; options { ... };` | `options` 블록 **1개** | BIND 문법 오류로 기동 실패 |
| 6 | `listen-on port 53 { 127.0.0.1; 192.168.16.81; };` | `listen-on port 53 { 127.0.0.1; 192.168.16.77; };` | 초기 **예시 IP**를 실제 IP로 교체해야 함 |
| 7 | `[hwanju]` 섹션 안의 `passdb backend = tdbsam` | `[global]` 안에 배치 | (G) global 전용 파라미터 |
| 8 | 크롬 주소창에 `\\192.168.16.131\hwanju` | **파일 탐색기 주소창**에 입력 | 브라우저는 SMB를 지원하지 않음 |
| 9 | `http://ftp.kload81.com` 링크 만들기 | FileZilla/`ftp` 클라이언트로 `ftp.kload81.com:21` 접속 안내 | FTP는 HTTP가 아님 |
| 10 | `/srv/nfs/hwanju 192.168.16.137 (rw,sync,root_squash)` | `/srv/nfs/hwanju 192.168.16.137(rw,sync,root_squash,no_subtree_check)` | 호스트와 옵션 사이 **공백 금지** |
| 11 | `no_root_squash`로 권한 문제 해결 | 일반 사용자(hwanju)로 접근 + 양쪽 UID/GID 2001 일치 | 보안 기능을 끄는 것은 해결이 아님 ⚠️ |
| 12 | `sudo ls /mnt/nfs` (거부 해결 시도) | `su - hwanju` 후 `ls -la /mnt/nfs` | `sudo`는 root가 되는 것 — squash 대상이 바로 root |
| 13 | `/etc/fstab` 전체 삭제 후 NFS 줄만 작성 | 기존 줄 유지 + **맨 끝에 1줄 추가** | 루트/부트/스왑 줄을 지우면 부팅 불가 |
| 14 | `nfs.kload81.com:/srv/nfs/hwanju /mnt/nfs nfs defaults 0 0` | `... nfs defaults,_netdev 0 0` | 네트워크 준비 전 마운트 시도로 부팅 지연/실패 가능 |
| 15 | `/etc/vsftpd/vsftpd.conf` 전체 삭제 후 재작성 | 기존 항목 **수정**, 없는 항목만 추가 (백업 먼저) | 기본 주석·설정 손실 |
| 16 | `secure.sh` 먼저 실행 | `configure.sh` → 웹 설치 → `secure.sh` | 순서가 반대면 `config.php`에 쓰지 못함 |
| 17 | `touch config.php`를 1차 방법으로 사용 | `contrib/configure.sh` 실행 | 공식 방법이 아님. fallback으로만 |
| 18 | LogAnalyzer 로그 소스에 `/var/log/syslog` | `/var/log/messages` (또는 `/var/log/remote.log`) | `/var/log/syslog`는 Debian/Ubuntu 파일명 |
| 19 | `/var/log/messages`를 `httpd_sys_content_t`로 변경 | `restorecon`으로 `var_log_t` 유지 | rsyslog 기록·logrotate가 깨질 수 있음 |
| 20 | SELinux를 무조건 `disabled` | 먼저 `Permissive` + `ausearch`로 원인 파악 → boolean/fcontext로 최소 허용 | Disabled는 로그조차 남지 않아 학습에 불리 |
| 21 | `ss -lntp \| grep 514` 로 rsyslog 확인 | `ss -lunp \| grep 514` | UDP는 `-u`. `-t`는 TCP |
| 22 | `firewall-cmd --add-port=514/tcp` (UDP 전송인데) | `firewall-cmd --permanent --add-port=514/udp` | `@` 하나는 UDP |
| 23 | `*.* @@192.168.16.131:514` (수신은 imudp) | `*.* @192.168.16.131:514` | `@@`는 TCP → 수신측 `imtcp` 필요 |
| 24 | WordPress를 DNS 서버(.77)에 설치 | Web 서버(.131)에 설치 | PHP·MariaDB가 있는 서버여야 함 |
| 25 | `/var/www/html/` 에 WordPress를 덮어씀 | `/var/www/html/wordpress/` 서브디렉터리에 설치 | 기존 대시보드 보존 |
| 26 | 대시보드 HTML에 DB 비밀번호 기재 | 어떤 비밀번호도 넣지 않음 | 소스 보기로 즉시 노출 ⚠️ |
| 27 | 미검증 항목을 "완료"로 표기 | ✅/🟡/❓ 로 구분 표기 | 사실과 다른 제출물은 감점 요인 |

---

## 부록 B. 전체 실습 명령 시트 (복습용)

### 서버별 한 줄 요약

```bash
# ── dns (192.168.16.77) ──────────────────────────────
dnf install -y bind bind-utils
vi /etc/named.conf                 # options listen-on 192.168.16.77 / zone "kload81.com"
vi /var/named/kload81.com.zone     # SOA serial 증가 필수
named-checkconf -z && systemctl reload named
firewall-cmd --permanent --add-service=dns && firewall-cmd --reload

# ── web (192.168.16.131) ─────────────────────────────
dnf install -y httpd mod_ssl samba samba-client mariadb-server
dnf module install -y php:8.1
systemctl enable --now httpd php-fpm mariadb smb
mariadb-secure-installation
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout /etc/pki/tls/private/kload81.com.key \
  -out /etc/pki/tls/certs/kload81.com.crt \
  -subj "/CN=www.kload81.com"
vi /etc/samba/smb.conf             # passdb backend 는 [global] 에
smbpasswd -a hwanju && smbpasswd -e hwanju
firewall-cmd --permanent --add-service={http,https,samba}
firewall-cmd --permanent --add-port=514/udp
firewall-cmd --reload

# ── nfs (192.168.16.136) ─────────────────────────────
dnf install -y nfs-utils
mkdir -p /srv/nfs/hwanju && chown hwanju:hwanju /srv/nfs/hwanju
echo '/srv/nfs/hwanju 192.168.16.137(rw,sync,root_squash,no_subtree_check)' >> /etc/exports
exportfs -rav && systemctl enable --now nfs-server
firewall-cmd --permanent --add-service={nfs,rpc-bind,mountd} && firewall-cmd --reload

# ── ftp (192.168.16.137) ─────────────────────────────
dnf install -y nfs-utils vsftpd ftp
mkdir -p /mnt/nfs
echo 'nfs.kload81.com:/srv/nfs/hwanju /mnt/nfs nfs defaults,_netdev 0 0' >> /etc/fstab
systemctl daemon-reload && mount -a && findmnt /mnt/nfs
vi /etc/vsftpd/vsftpd.conf         # local_root=/mnt/nfs, pasv_*
systemctl enable --now vsftpd
firewall-cmd --permanent --add-service=ftp
firewall-cmd --permanent --add-port=40000-40010/tcp
firewall-cmd --reload

# ── 전 서버 공통: 로그 송신 (web 제외) ───────────────
echo '*.* @192.168.16.131:514' > /etc/rsyslog.d/10-forward-to-web.conf
rsyslogd -N 1 && systemctl restart rsyslog
```

### 장애 진단 순서 (어디가 막혔는지 좁혀 가는 법)

```text
1. 서비스가 살아 있나?        systemctl is-active <서비스>
2. 포트를 듣고 있나?          ss -lntp / ss -lunp
3. 방화벽이 열려 있나?        firewall-cmd --list-all
4. 이름이 풀리나?             getent hosts <이름>  /  dig @<DNS> <이름>
5. 네트워크가 닿나?           ping <IP>
6. 설정 문법이 맞나?          named-checkconf / httpd -t / testparm / rsyslogd -N 1 / exportfs -v
7. 권한(유닉스)이 맞나?       ls -ln, id
8. SELinux가 막았나?          getenforce ; ausearch -m AVC -ts recent
9. 로그에 뭐라고 나오나?      journalctl -u <서비스> -n 50 ; /var/log/httpd/error_log
```

이 9단계는 **위에서부터 순서대로** 확인하는 것이 요령입니다. 6번(설정 문법)부터 보기 시작하면, 실은 3번(방화벽)이 원인이었던 경우에 시간을 크게 낭비하게 됩니다.

---

## 부록 C. 보안 요약 — 실습용 vs 운영용

| 항목 | 실습에서 사용한 것 | 운영 권장 | 위험 |
|---|---|---|---|
| root 비밀번호 | 단순 값(예: `1234`) ⚠️ | 12자 이상 무작위, SSH는 키 인증 + `PermitRootLogin no` | SSH가 열린 순간 사실상 무방비 |
| FTP | vsftpd 평문 | **SFTP 또는 FTPS** | 계정·비밀번호가 네트워크에 평문 노출 |
| TLS 인증서 | 자체 서명 | 공인 CA (Let's Encrypt 등) | 신원 보증 없음, MITM 탐지 불가 |
| SELinux (web) | Disabled ⚠️ | **Enforcing** + boolean/fcontext로 최소 허용 | 정책 보호가 전부 사라짐 |
| NFS | `root_squash` ✅ 유지 | 동일 + 가능하면 Kerberos(`sec=krb5p`) | `no_root_squash`는 원격 root의 서버 장악 경로 |
| `ftpd_full_access` | 사용하지 않음(fallback으로만 분류) | 사용하지 않음 | 시스템 전역 읽기·쓰기를 정책적으로 허용 |
| Samba | `map to guest = never`, `security = user` ✅ | 동일 + SMB3, `smb encrypt = required` 검토 | `guest ok = yes`면 누구나 접근 |
| rsyslog | UDP 514 평문 | TCP + TLS(`imtcp`+`gtls`), `AllowedSender`, RateLimit | 로그 위조·도청·폭주 |
| MariaDB | `localhost` 계정만 | 동일 + root 원격 금지, 최소 권한 GRANT | `'user'@'%'`는 전 네트워크 노출 |
| `/var/log/messages` 라벨 | 원래 타입 유지 ✅ | 동일 | 변경 시 rsyslog·logrotate 파손 |
| `wp-config.php` | 640, 공개 금지 ✅ | 동일 + 문서 루트 밖 이동 검토 | DB 자격 증명 유출 |
| VM 삭제 전 | — | **스냅샷/백업 필수** | 복구 불가 |

