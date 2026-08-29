# 2026-08-25 학습 노트 — NFS · Samba · SELinux · rsyslog · MariaDB · LogAnalyzer

> **실습 환경**
> - OS: Rocky Linux 9.7 (Blue Onyx) / Kernel 5.14.0-611.5.1.el9_7.x86_64 / VirtualBox VM
> - MariaDB: 10.5.29 / LogAnalyzer: 4.1.13
> - Samba: 4.23.5 / rsyslog: 8.2506.0 → **8.2510.0** (실습 중 업그레이드)
> - 노드: **192.168.16.81 = NFS 서버 + Samba 서버 + rsyslog 서버(`server`)**, **192.168.16.92 = NFS 클라이언트(복제본)**, **192.168.16.40 = Windows Samba 클라이언트**
> - 오전: NFS → Samba → SELinux → hostname
> - 오후: rsyslog 서버/클라이언트 → MariaDB 로그 저장 → LogAnalyzer 웹 UI
>
> 본 노트의 기술적 사실은 Red Hat Enterprise Linux 9 / Rocky Linux 9 공식 문서, Samba 공식 man 페이지 및 4.23 릴리스 노트, Fedora SELinux 위키, rsyslog.conf(5) man 페이지를 대조 확인해 작성했습니다. (출처는 문서 맨 끝)

---

## 0. 오늘의 큰 그림

| 주제 | 목적 | 핵심 데몬 | 기본 포트 |
|---|---|---|---|
| NFS | Linux ↔ Linux 파일/디렉터리 공유 | `nfsd`(커널), `rpc.nfsd`, `rpc.mountd`, `rpc.statd`, `nfsdcld`, `rpcbind` | **TCP 2049** (NFSv4 단일) / v3는 +111, +mountd |
| Samba | Linux ↔ Windows 파일·프린터 공유 | `smbd`, `nmbd` | **TCP 445, 139** / **UDP 137, 138** |
| SELinux | 커널 레벨 강제 접근제어(MAC) | 커널 LSM | 없음 (정책 기반) |
| hostname | 시스템 이름 관리 | `systemd-hostnamed` | 없음 |
| **rsyslog** | **로그 중앙 수집 (client → server)** | `rsyslogd` | **UDP 514 / TCP 514** |
| **MariaDB** | **수집한 로그를 DB에 저장** | `mariadb` (mysqld) | **TCP 3306** |
| **httpd + LogAnalyzer** | **로그를 웹에서 검색·통계** | `httpd` | **TCP 80** |

**서버 서비스 구축 6단계 공통 패턴** — 이 순서를 몸에 익히면 어떤 데몬이든 동일하게 접근할 수 있습니다.

```
① 패키지 설치  →  ② 공유 디렉터리 생성 + 권한
→ ③ 설정 파일 편집(+문법 검증)  →  ④ 서비스 start/enable
→ ⑤ 방화벽 개방  →  ⑥ SELinux 컨텍스트 처리  →  ⑦ 클라이언트 접속 확인
```

오늘 실습에서 `/sambatest` 접근이 막혔던 원인이 정확히 **⑥번을 건너뛴 것**이었습니다. 이 패턴을 기억하세요.

---

## 1. 공유(Share) 개념 정리

메모의 "NFS / Samba : cd rom, device 공유 가능"은 방향은 맞지만 정확히는 이렇습니다.

- **공유되는 단위는 "파일시스템 경로(디렉터리)"** 입니다. CD-ROM이나 USB도 결국 `/mnt/cdrom` 같은 경로에 마운트된 뒤, 그 **경로**를 공유하는 방식입니다.
- 즉 장치 자체를 네트워크로 넘기는 게 아니라, 장치가 마운트된 디렉터리를 export/share 합니다.
- 블록 장치 자체를 원격으로 넘기려면 NFS/Samba가 아니라 **iSCSI**를 씁니다.

> **레벨 구분 (면접·시험 단골)**
> - **파일 레벨(NAS)**: NFS, SMB/CIFS — 서버가 파일시스템을 갖고, 클라이언트는 "파일"을 요청
> - **블록 레벨(SAN)**: iSCSI, FC — 클라이언트가 원격 디스크를 자기 로컬 디스크처럼 인식하고, 클라이언트가 직접 파일시스템을 생성(`mkfs`)
> - 그래서 iSCSI LUN은 여러 호스트가 동시에 쓰면 깨지지만(클러스터 FS 필요), NFS는 동시 접근이 정상 동작합니다.

### NFS vs Samba 비교

| 항목 | NFS | Samba (SMB/CIFS) |
|---|---|---|
| 주 용도 | UNIX/Linux 간 공유 | Windows ↔ Linux 공유 |
| 인증 단위 | 기본은 **호스트(IP/네트워크) 기반** | **사용자(계정) 기반** |
| 권한 모델 | UID/GID 숫자를 그대로 신뢰(v4는 이름 매핑 가능) | 사용자명 매핑 + ACL |
| 클라이언트 사용법 | `mount -t nfs` (파일시스템처럼) | 탐색기 `\\IP\공유명`, Linux는 `mount -t cifs` |
| 상태 | v3는 stateless, **v4는 stateful** | stateful |
| 현재 표준 | **NFSv4.2** (RHEL 9 기본, v3 호환 유지) | **SMB3.1.1** (SMB1은 기본 비활성) |
| 암호화 | v4.2 + `sec=krb5p`, RHEL 9.6+ `xprtsec=tls` | SMB3 자체 암호화 지원 |

---

## 2. NFS 심화

### 2-1. NFS를 구성하는 데몬 (메모 보강 + 공식 문서 대조)

메모의 "rpc / nfslock / rpcbind 세 가지로 동작"은 **NFSv3 기준 설명**입니다. Red Hat 9 문서 기준으로 정확히 풀면 다음 6개입니다.

| 구성요소 | 역할 | 필요 버전 |
|---|---|---|
| **`nfsd`** | 공유된 NFS 파일시스템 요청을 처리하는 **커널 모듈**. 실제 파일 I/O 담당 | v3, v4 |
| **`rpc.nfsd`** | 지원 NFS 버전을 광고하고 클라이언트 동적 연결을 관리하는 사용자 공간 프로세스 | v3, v4 |
| **`rpc.mountd`** | **NFSv3 클라이언트의 MOUNT 요청**을 처리하고 `/etc/exports` 규칙을 검사 | 주로 v3 |
| **`rpc.statd`** | 로컬 호스트 재부팅 시 다른 **NFSv3 클라이언트에 통지**(NSM). 락 복구 담당 | v3 |
| **`nfsdcld`** | **NFSv4 클라이언트 추적 데몬**. 재부팅 후 상태(state) 복구 | v4 |
| **`rpcbind`** | RPC 서비스의 동적 포트를 안내하는 "포트 안내소". **111번 포트** | **v3 전용** |

> **핵심 보강 — rpcbind는 NFSv4에 필수가 아닙니다.**
> Red Hat 9 공식 문서는 rpcbind를 "Required for NFSv3 (not needed for NFSv4-only)"로 명시합니다. NFSv4는 mount, lock, ACL을 모두 **2049 포트 하나로 통합**했기 때문입니다.
> RHEL/Rocky 9는 기본이 NFSv4.2이므로 rpcbind 없이 동작합니다. 수업에서 `systemctl start rpcbind`를 한 것은 **NFSv3 클라이언트 호환을 위한 관례**입니다. 그 자체가 틀린 건 아니지만 "이게 없으면 NFS가 안 돈다"는 이해는 정확하지 않습니다.
>
> 참고로 RHEL 9 클라이언트는 "서버가 제공하는 가장 최신 NFS 버전"을 자동 선택합니다. 즉 오늘 실습의 마운트도 실제로는 **NFSv4.2로 붙었을 가능성이 높습니다.** 확인 명령:
> ```bash
> mount | grep nfs        # vers=4.2 표시 확인
> nfsstat -m              # 클라이언트 마운트 상세
> ```

### 2-2. 서버 구축 절차 (81번)

```bash
# ① 패키지 설치
dnf install -y nfs-utils

# ② 공유 디렉터리 생성
mkdir /nfsserver
chmod 755 /nfsserver     # 메모의 756 → 아래 2-4 참고

# ③ export 규칙 작성
vi /etc/exports
```

`/etc/exports` 내용:

```
/nfsserver  192.168.16.92(rw,sync,no_root_squash)
```

**기본 문법 (Red Hat 9 문서 원문 형식)**
```
<directory> <host_or_network_1>(<options_1>) <host_or_network_n>(<options_n>)...
```

> ### ⚠️ 가장 위험한 문법 함정 — 공백
> Red Hat 문서 원문: *"Adding a space between a client and options, changes the behavior."*
>
> | 작성 | 실제 의미 |
> |---|---|
> | `/projects client.example.com(rw)` | 해당 호스트에만 **rw** 부여 (의도한 동작) |
> | `/projects client.example.com (rw)` | 해당 호스트는 **기본값(ro)**, 그리고 **그 외 모든 호스트에 rw** 부여 |
>
> 공백 하나로 "특정 호스트만 쓰기 허용"이 **"전 세계에 쓰기 허용"** 으로 뒤집힙니다. 실무에서 실제로 발생하는 사고 유형입니다. 작성 후 반드시 `exportfs -v`로 적용 결과를 눈으로 확인하세요.

**클라이언트 지정 방식 (다양하게 쓸 수 있음)**
```
/nfsserver  192.168.16.92(rw)                 # 단일 호스트
/nfsserver  192.168.16.0/24(rw)               # 네트워크 대역
/nfsserver  *.example.com(ro)                 # 와일드카드 도메인
/nfsserver  @devgroup(rw)                     # NIS 넷그룹
/nfsserver  *(ro)                             # 전체 (권장하지 않음)
/nfsserver  192.168.16.92(rw) 192.168.16.93(ro)   # 호스트별 다른 옵션
```

```bash
# ④ export 적용 및 확인
exportfs -a          # /etc/exports 전체 적용
exportfs -r          # 재적용 (reexport)
exportfs -ra         # 수정 후 권장 조합
exportfs -v          # 옵션까지 상세 확인 (중요)
exportfs -u 192.168.16.92:/nfsserver   # 특정 export 해제
exportfs             # 현재 목록 요약

# ⑤ 서비스 기동
systemctl enable --now nfs-server
systemctl enable --now rpcbind        # NFSv3 호환 시

# ⑥ 방화벽
firewall-cmd --permanent --add-port=2049/tcp
firewall-cmd --reload
firewall-cmd --list-all
```

> **더 정확한 방화벽 설정 (Red Hat 9 권장)**
> ```bash
> # NFSv4 전용
> firewall-cmd --permanent --add-service=nfs
>
> # NFSv3 병행 시 (rpcbind, mountd 포트도 필요)
> firewall-cmd --permanent --add-service={nfs,rpc-bind,mountd}
> firewall-cmd --reload
> ```
> 포트 번호를 직접 여는 방식(`--add-port=2049/tcp`)은 NFSv4만 쓸 때는 동작하지만, NFSv3를 쓰면 mountd/statd의 **동적 포트** 때문에 마운트가 실패합니다. 서비스 단위 개방이 안전합니다.

### 2-3. `/etc/exports` 옵션 완전 정리

| 옵션 | 의미 | 기본값 |
|---|---|---|
| `ro` | 읽기 전용으로 export | **기본값** |
| `rw` | 읽기/쓰기 허용 | |
| `sync` | 변경 사항이 **디스크에 기록된 후에야** 응답 | **기본값**, 안전 |
| `async` | 메모리에 받고 즉시 응답 | 빠르지만 정전 시 **데이터 유실** |
| `wdelay` | 다른 쓰기 요청이 곧 올 것 같으면 디스크 쓰기를 지연시켜 묶음 처리 | **기본값**(sync일 때) |
| `no_wdelay` | 지연 없이 즉시 기록 | 무작위 쓰기 많을 때 |
| `root_squash` | 클라이언트 root(UID 0) → 서버의 `nobody`로 매핑 | **기본값**, 보안 필수 |
| `no_root_squash` | 클라이언트 root를 **서버 root로 그대로 인정** | 실습 편의용, **운영 금지** |
| `all_squash` | **모든** 사용자를 익명 사용자로 강등 | 공개 읽기 공유용 |
| `no_all_squash` | 사용자 UID를 그대로 유지 | 기본값 |
| `anonuid=N` / `anongid=N` | 강등될 익명 UID/GID 지정 | `all_squash`와 짝 |
| `secure` | 클라이언트가 **1024번 미만(특권) 포트**에서 접속해야 허용 | **기본값** |
| `insecure` | **1024번 이상** 포트에서의 접속도 허용 | macOS·컨테이너 대응 |
| `subtree_check` | 상위 디렉터리 권한까지 검사 | 성능 저하로 비권장 |
| `no_subtree_check` | 하위 경로 검사 생략 | **현재 기본값** |

> **메모 수정 포인트 ①** — "secure : 1024포트 이상 이하, insecure 옵션"이 방향이 모호합니다.
> - **`secure`** = 클라이언트 소스 포트가 **1024 미만**이어야 허용 (기본값)
> - **`insecure`** = **1024 이상** 포트도 허용
>
> **왜 1024 미만이 "안전"한가?** 유닉스에서 1024번 미만 포트는 **root만 바인딩 가능**합니다. 즉 "이 요청은 클라이언트의 root 권한으로 만들어진 정상 마운트다"라는 최소한의 신뢰 근거가 됩니다. 일반 사용자가 임의로 NFS 요청을 위조하는 것을 막는 장치입니다.

> **`no_root_squash`가 위험한 구체적 시나리오**
> 클라이언트 장악자가 공유 디렉터리에 setuid 바이너리를 심으면:
> ```bash
> # 클라이언트(root)에서
> cp /bin/bash /nfsclient/rootshell
> chmod u+s /nfsclient/rootshell
> # → 서버에서 일반 사용자가 실행하면 root 셸 획득
> ```
> 방어: `root_squash`(기본) 유지 + `nosuid` 마운트 옵션 병행.
> ```bash
> mount -t nfs -o nosuid,nodev 192.168.16.81:/nfsserver /nfsclient
> ```

### 2-4. 디렉터리 권한 `chmod 756` 재검토

메모의 `chmod 756 /nfsserver`는 `rwx`(소유자) / `r-x`(그룹) / `rw-`(기타)입니다.

**문제**: 기타(other) 사용자에게 **`x`가 없습니다.** 디렉터리에서 `x`는 "실행"이 아니라 **"통과(진입) 권한"** 이므로, 소유자·그룹이 아닌 일반 사용자는 `cd /nfsserver`조차 실패합니다. `r`이 있어도 `x`가 없으면 `ls`는 이름만 보이고 상세 정보(`ls -l`)는 `?`로 나옵니다.

**실습에서 문제가 없었던 이유**: 클라이언트에서 **root**로 접근했고 `no_root_squash`가 걸려 있었기 때문입니다.

**권장**
```bash
chmod 755 /nfsserver     # 읽기 공유
chmod 1777 /nfsserver    # 모두 쓰기 (sticky bit — 자기 파일만 삭제 가능)
chmod 2775 /nfsserver    # 그룹 공유 (setgid — 새 파일이 그룹 상속)
```

**디렉터리 권한 비트 의미 (파일과 다름 — 반드시 구분)**

| 비트 | 파일에서 | **디렉터리에서** |
|---|---|---|
| `r` | 내용 읽기 | 목록 조회(`ls`) 가능 |
| `w` | 내용 쓰기 | **파일 생성/삭제/이름변경** 가능 |
| `x` | 실행 | **진입(`cd`) 및 내부 파일 접근** 가능 |

> 자주 헷갈리는 지점: **파일 삭제 권한은 그 파일이 아니라 "그 파일이 든 디렉터리"의 `w`가 결정합니다.** 읽기 전용 파일(`444`)도 디렉터리에 `w`가 있으면 지워집니다. sticky bit(`1777`)는 이 문제를 막아 "자기 소유 파일만 삭제 가능"하게 만듭니다. `/tmp`가 그 예입니다.

### 2-5. 클라이언트 마운트 (92번)

```bash
dnf install -y nfs-utils
mkdir /nfsclient
mount -t nfs 192.168.16.81:/nfsserver /nfsclient
df -h
```

> RHEL 9 문서 예시는 `-t nfs` 없이도 됩니다: `mount server.example.com:/nfs/projects/ /mnt/`
> `mount`가 콜론(`:`) 표기를 보고 NFS로 자동 판별하기 때문입니다. 다만 명시하는 습관이 안전합니다.

실습 출력:

```
Filesystem                Size  Used Avail Use% Mounted on
192.168.16.81:/nfsserver   17G  1.9G   16G  11% /nfsclient
```

> **읽는 법**: 용량이 서버의 `/`(17G)와 **동일**합니다. `/nfsserver`가 별도 파티션이 아니라 루트 파티션 안의 일개 디렉터리이기 때문입니다. NFS는 디렉터리를 export할 뿐 **용량을 따로 할당하지 않습니다.** 클라이언트가 파일을 채우면 서버의 `/`가 가득 차 시스템 전체가 위험해질 수 있습니다.
> → 실무 대응: 공유용 **별도 파티션/LVM 볼륨**을 만들어 export하거나, XFS 프로젝트 쿼터를 겁니다.

**동기화 확인 실습 해석**

```
서버:      touch test.html   → 즉시
클라이언트: ls                 → test.html 보임
클라이언트: rm test.html
서버:      ls                 → test.html 사라짐
```

> NFS는 **캐시된 복사본이 아니라 원격 파일시스템 그 자체**입니다. 양쪽이 같은 실체(inode)를 보고 있습니다. 이 점이 rsync/동기화 도구와 근본적으로 다릅니다.
>
> 단, 클라이언트는 성능을 위해 **속성(attribute) 캐시**를 유지합니다(기본 `ac`, `acregmin/acregmax` 등). 그래서 아주 짧은 지연이 있을 수 있고, 여러 클라이언트가 동시에 같은 파일을 쓸 때는 `noac` 옵션이나 파일 락이 필요합니다.

**주요 마운트 옵션**

| 옵션 | 의미 |
|---|---|
| `nfsvers=4.2` / `vers=3` | NFS 버전 강제 지정 |
| `hard` | 서버 응답이 없으면 **무한 재시도** (기본, 데이터 안전) |
| `soft` | 타임아웃 후 에러 반환 — 데이터 손상 위험, 읽기 전용에만 |
| `timeo=N` / `retrans=N` | 타임아웃(0.1초 단위) / 재전송 횟수 |
| `rsize=` / `wsize=` | 읽기·쓰기 블록 크기 |
| `nosuid,nodev,noexec` | 보안 강화 마운트 |
| `sec=krb5` / `krb5i` / `krb5p` | Kerberos 인증 / 무결성 / **암호화** |
| `xprtsec=tls` | **TLS 전송 암호화 (RHEL 9.6 이상)** |
| `_netdev` | 네트워크 장치임을 표시 (fstab 필수) |

> **최신 정보**: RHEL 9.6부터 `xprtsec=tls`로 **Kerberos 없이도 NFS 트래픽을 TLS로 암호화**할 수 있습니다. 기본 NFS는 평문이라 스니핑에 취약한데, 이 옵션이 실무적으로 큰 개선입니다.

### 2-6. 언마운트 — 메모의 오타

```
[root@localhost nfsclient]# unmonunt /nfsclient   ← ✗ 오타
```

정답은 **`umount`** 입니다. `unmount`도 `unmonunt`도 아니고 **n이 하나 빠진 `umount`** — 유닉스 전통적 명명입니다.

```bash
cd /                 # ① 마운트 지점 밖으로 먼저 나가야 함
umount /nfsclient
```

> **"target is busy" 에러가 나는 이유와 대처**
> ```bash
> lsof +D /nfsclient        # 어떤 프로세스가 쓰는지
> fuser -vm /nfsclient      # 사용 중인 PID
> umount -l /nfsclient      # lazy — 참조가 끝나면 해제 (마지막 수단)
> umount -f /nfsclient      # force — 서버가 죽어 응답 없을 때
> ```
> 가장 흔한 원인은 **본인 셸이 그 디렉터리 안에 있는 것**입니다. `cd /` 먼저 하세요.

### 2-7. 영구 마운트 — 수업에서 빠진 중요 부분

`mount` 명령은 **재부팅하면 사라집니다.** 영구 적용은 `/etc/fstab`:

```
192.168.16.81:/nfsserver   /nfsclient   nfs   defaults,_netdev   0 0
```

RHEL 9 문서 표기 형식:
```
<nfs_server_ip_or_hostname>:/<exported_share>   <mount point>   nfs   defaults   0 0
```

- `_netdev` : 네트워크가 올라온 뒤 마운트하라는 표시. **없으면 부팅이 멈출 수 있습니다.**
- 마지막 두 숫자 `0 0` = dump 여부 / fsck 순서. 네트워크 FS는 둘 다 0.
- **더 안전한 대안** — 실제 접근 시점에만 마운트:
  ```
  192.168.16.81:/nfsserver  /nfsclient  nfs  noauto,x-systemd.automount,_netdev  0 0
  ```
- 또는 `autofs` 서비스 사용 (RHEL 9 문서 권장 방식 중 하나).

> **반드시**: fstab 수정 후 재부팅 **전에** `mount -a`로 검증하세요. fstab 오타는 시스템이 emergency mode로 부팅되는 대표적 원인입니다.

### 2-8. 진단 명령

```bash
showmount -e 192.168.16.81      # 서버의 export 목록 조회
nfsstat -c                      # 클라이언트 통계
nfsstat -s                      # 서버 통계
nfsstat -m                      # 마운트별 상세(버전·옵션)
rpcinfo -p 192.168.16.81        # RPC 등록 서비스 확인
mount | grep nfs                # 실제 협상된 버전 확인
```

> **주의 — `showmount`는 NFSv4 전용 서버에서는 동작하지 않습니다.**
> `showmount`는 **rpc.mountd(NFSv3 프로토콜)** 에 질의합니다. NFSv4-only로 구성했거나 rpcbind/mountd 포트가 막혀 있으면 결과가 비어 있거나 타임아웃 납니다. **이때 "서버가 잘못됐다"고 오판하기 쉽습니다.** NFSv4 환경에서는 `showmount` 대신 그냥 마운트를 시도하거나 서버에서 `exportfs -v`로 확인하는 것이 정확합니다.

---

## 3. Samba 심화

### 3-1. 데몬과 포트 (메모 수정 — 공식 man 페이지 대조)

Samba 공식 man 페이지 원문 확인 결과:

| 데몬 | man 페이지 원문 | 포트 |
|---|---|---|
| **smbd** | *"The default ports are 139 (used for SMB over NetBIOS over TCP) and port 445 (used for plain SMB over TCP)."* | **TCP 139, TCP 445** |
| **nmbd** | *"changes the default UDP port number (normally 137) that nmbd responds to name queries on"* | **UDP 137**(이름 서비스), **UDP 138**(데이터그램) |

> ### ⚠️ 메모 수정 포인트 ②
> 메모: "nmbd => tcp 포트 139번, udp 포트 137, 138번"
> → **TCP 139는 nmbd가 아니라 smbd가 사용합니다.** nmbd는 UDP 137/138만 담당합니다.
> → 그리고 **현대 SMB의 주력 포트는 TCP 445**입니다. Windows 2000부터 NetBIOS를 거치지 않는 "direct-hosted SMB"가 도입되어 445가 표준이 됐고, 139는 레거시 호환 경로입니다.

**역할 구분**
- **smbd** — 파일·프린터 공유, 인증, 실제 데이터 전송. Samba의 본체.
- **nmbd** — NetBIOS 이름 해석, 브라우징(네트워크 컴퓨터 목록), WINS 서버/프록시 기능.

> **현실적 참고**: SMB2/3 + DNS 환경에서는 **nmbd 없이도 정상 동작**합니다. `\\서버이름\공유` 접속은 DNS로 해결됩니다. nmbd는 "네트워크 환경 목록에 자동으로 뜨게 하는" 레거시 편의 기능에 가깝습니다. 보안을 중시하면 nmbd를 끄고 137/138을 닫는 구성도 흔합니다.

### 3-2. 설치와 계정 준비

```bash
dnf install -y samba samba-common samba-client

mkdir /sambatest
chmod 777 /sambatest          # 실습용. 운영은 2770 + 그룹 기반 권장

useradd -s /sbin/nologin sambauser   # ① 리눅스 계정이 먼저 존재해야 함
smbpasswd -a sambauser               # ② 삼바 DB에 등록 + 비밀번호 설정
```

> ### 핵심 개념 — 왜 계정을 두 번 만드나?
> `smbpasswd -a`는 리눅스 비밀번호를 바꾸는 게 아닙니다. **`tdbsam`이라는 별도의 삼바 전용 비밀번호 DB**(`/var/lib/samba/private/passdb.tdb`)에 항목을 만듭니다.
>
> - **리눅스 계정** = UID/GID와 파일 소유권을 담당 → **파일시스템 권한의 주체**
> - **삼바 계정** = SMB 프로토콜 인증을 담당 → **네트워크 로그인의 주체**
>
> SMB는 Windows의 NTLM/Kerberos 해시 인증을 쓰기 때문에 유닉스의 crypt 해시를 그대로 쓸 수 없습니다. 그래서 별도 DB가 필요합니다. **결과적으로 리눅스 로그인 암호와 삼바 암호는 서로 달라도 됩니다.**
>
> 파일 공유 전용 계정이라면 `-s /sbin/nologin`으로 셸 로그인을 막는 것이 보안상 훨씬 낫습니다. (메모의 `useradd sambauser`는 SSH 로그인도 가능한 상태가 됩니다.)

**계정 확인**
```bash
pdbedit -L            # 삼바 사용자 목록
pdbedit -L -v         # 상세 (계정 플래그, 마지막 변경 시각 등)
```

### 3-3. `smbpasswd` 옵션 정리 (메모 오타 `smabauser` → `sambauser`)

공식 man 페이지 기준 (모두 **root만 실행 가능**):

| 명령 | man 원문 | 의미 |
|---|---|---|
| `smbpasswd -a 계정` | "add to the local smbpasswd file" | 삼바 사용자 **추가** |
| `smbpasswd -x 계정` | delete username from smbpasswd file | 삼바 사용자 **삭제** |
| `smbpasswd -d 계정` | "disable ... by writing a 'D' flag" | **비활성화** |
| `smbpasswd -e 계정` | "enable ... if previously disabled" | **활성화** |
| `smbpasswd -n 계정` | "password set to null ... writing the string 'NO PASSWORD'" | 비밀번호 **NULL로 설정** |
| `smbpasswd -s` | 표준입력에서 읽기 | **스크립트용** (무인 설정) |
| `smbpasswd -m 계정` | machine account | **컴퓨터 계정** 지정 |
| `smbpasswd -r 호스트 -U 계정` | remote machine | **원격 서버**의 비밀번호 변경 |
| `smbpasswd -c 파일` | alternate smb.conf | 설정 파일 경로 지정 |

> **`-n`은 단독으로 동작하지 않습니다.** man 페이지 원문:
> *"To allow users to logon to a Samba server once the password has been set to 'NO PASSWORD,' the administrator must set `null passwords = yes` in the [global] section of smb.conf"*
>
> 메모에 적힌 `null passwords = yes`가 바로 이 짝입니다. **다만 이 파라미터는 Samba에서 deprecated(사용 중단 예정)로 분류되어 있으며**, 설정하면 데몬 로그에 `WARNING: The "null passwords" option is deprecated` 경고가 남습니다. 운영 환경에서는 절대 사용하지 마세요. (Samba Bugzilla #10065)

**스크립트로 비밀번호 설정하기 (실무 팁)**
```bash
(echo 'P@ssw0rd'; echo 'P@ssw0rd') | smbpasswd -s -a sambauser
```

### 3-4. `/etc/samba/smb.conf` 구조 읽기

설정 파일은 `[섹션]` 단위이며, **섹션 이름이 곧 네트워크에 보이는 공유 이름**입니다. (`[global]`, `[homes]`, `[printers]`, `[print$]`는 예약 섹션)

#### `[global]` — 서버 전체 설정

```ini
[global]
    workgroup = SAMBA          # Windows 작업 그룹 이름
    security = user            # 사용자 계정 기반 인증 (현재 유일한 표준)
    passdb backend = tdbsam    # 계정 DB 방식
    printing = cups
    printcap name = cups
    load printers = yes
    cups options = raw
    include = /etc/samba/usershares.conf
```

| 항목 | 설명 |
|---|---|
| `workgroup` | Windows 작업 그룹명. AD 도메인 멤버라면 도메인의 NetBIOS 이름 |
| `security = user` | 접속 시 ID/PW 요구. 예전의 `share`, `server` 모드는 **폐기됨** |
| `passdb backend` | `tdbsam`(로컬 tdb 파일, 소규모), `ldapsam`(LDAP 연동, 대규모) |
| `printing`/`printcap`/`cups options` | CUPS 프린터 시스템 연동 |
| `include` | 다른 설정 파일 병합 |

**보안 강화용 추가 권장 항목**
```ini
[global]
    server min protocol = SMB2_10     # SMB1 차단 (RHEL9은 기본 차단)
    smb encrypt = required            # SMB3 암호화 강제
    hosts allow = 192.168.16.0/24     # 접속 허용 대역 제한
    log file = /var/log/samba/log.%m  # 클라이언트별 로그
    max log size = 5000
```

#### `[homes]` — 예약 섹션 (메모 보강)

```ini
[homes]
    comment = Home Directories
    valid users = %S, %D%w%S
    browseable = No
    read only = No
    inherit acls = Yes
```

> ### 메모 수정 포인트 ③
> 메모: "`[homes]` -> 공유폴더 이름"
> → `[homes]`는 임의로 지은 공유 이름이 아니라 **Samba가 특별 취급하는 예약 섹션**입니다.
>
> **동작 방식**: 사용자 `sambauser`가 접속하면, Samba가 요청받은 공유 이름이 실제 공유 목록에 없을 때 `[homes]`를 참조해 **그 사용자의 홈 디렉터리(`/home/sambauser`)를 즉석에서 공유로 만들어 줍니다.** 사용자 100명이 있어도 섹션 하나로 100개의 개인 공유가 생기는 셈입니다.

**변수(substitution) 이해**

| 변수 | 의미 |
|---|---|
| `%S` | 현재 서비스(공유) 이름 → `[homes]`에서는 **접속한 사용자명**으로 치환 |
| `%U` | 세션 사용자명 |
| `%D` | 사용자의 도메인/워크그룹 |
| `%w` | winbind 구분자 (보통 `\`) |
| `%m` | 클라이언트의 NetBIOS 이름 |
| `%I` | 클라이언트 IP |
| `%H` | 사용자의 홈 디렉터리 |

따라서 `valid users = %S, %D%w%S` = "자기 자신(`sambauser`), 또는 `DOMAIN\sambauser` 형태만 접근 허용" → **남의 홈에 못 들어가게 하는 안전장치**입니다.

> `browseable = No`의 의미: **목록에 안 보이지만 직접 경로로는 접근 가능**합니다(`\\IP\sambauser`). "숨김"이지 "차단"이 아닙니다. 차단은 `valid users` / `hosts allow` / `available = no`가 담당합니다.

#### `[printers]` / `[print$]`

```ini
[printers]
    comment = All Printers
    path = /var/tmp              # 스풀 임시 경로
    printable = Yes              # 프린터 공유임을 표시
    create mask = 0600
    browseable = No

[print$]
    comment = Printer Drivers
    path = /var/lib/samba/drivers   # Windows용 드라이버 자동 배포 경로
    write list = printadmin root
    force group = printadmin
    create mask = 0664
    directory mask = 0775
```

메모의 "all printers — 줘도 되고 안 줘도 됨"이 맞습니다. 프린터를 쓰지 않으면:
```ini
[global]
    load printers = no
    printing = bsd
    printcap name = /dev/null
    disable spoolss = yes
```
로 완전히 끄고 `[printers]`, `[print$]` 섹션을 주석 처리해도 됩니다. 불필요한 공유를 줄이는 것이 보안상 유리합니다.

#### `[sambashare]` — 이번 실습에서 추가한 공유

```ini
[sambashare]
    path = /sambatest
    browseable = yes           # 네트워크 목록에 표시
    writeable = yes            # 쓰기 허용
    guest ok = yes             # 인증 없이 접근 허용
    read only = no             # writeable과 동일 의미(반대 표현)
    create mask = 0777         # 새 파일 권한 상한
    directory mask = 0777      # 새 디렉터리 권한 상한
```

> ### 메모 수정 포인트 ④ — 중복 설정
> **`writeable = yes` 와 `read only = no` 는 완전히 같은 설정입니다.** (`writable`도 같은 별칭) 둘을 동시에 쓰면 파일에서 나중에 나온 값이 적용됩니다. 하나만 쓰세요.
> → 실습의 `testparm` 출력에 `read only = No` **하나만** 남은 이유가 이것입니다. Samba가 내부적으로 하나의 파라미터로 정규화하기 때문입니다.

> ### 메모 수정 포인트 ⑤ — mask의 정확한 의미
> `create mask = 0777`은 권한을 **"부여"하는 것이 아니라 "상한(마스크)"** 입니다.
> ```
> 실제 권한 = 클라이언트가 요청한 권한  AND  create mask
> ```
> 즉 `create mask = 0777`은 "최대 777까지 허용"이지 "무조건 777로 만들라"가 아닙니다. **강제로 특정 권한을 부여**하려면 `force create mode`를 씁니다.
> ```ini
> create mask = 0664
> force create mode = 0664     # 이 비트는 반드시 켬
> directory mask = 0775
> force directory mode = 0775
> ```

> ### ⚠️ `guest ok = yes`의 위험
> 인증 없이 누구나 읽고 쓸 수 있게 됩니다. 실습 외에는 계정 기반으로 제한하세요.
> ```ini
> [sambashare]
>     path = /sambatest
>     browseable = yes
>     read only = no
>     guest ok = no
>     valid users = @smbgroup       # 그룹 단위 허용
>     write list = @smbgroup
>     force group = smbgroup
>     create mask = 0664
>     directory mask = 0775
> ```
> 이때 디렉터리는 `chmod 2770 /sambatest` + `chgrp smbgroup /sambatest` (setgid로 그룹 상속)가 정석입니다.

### 3-5. 설정 검증 — `testparm`

```bash
testparm                    # 문법 검사 + 적용될 값 요약
testparm -v                 # 기본값까지 전부 출력
testparm -s                 # 프롬프트 없이 바로 덤프
```

- **설정 수정 후 재시작 전에 반드시 실행하는 습관을 들이세요.** 문법 오류가 있으면 smbd가 아예 못 뜨거나 공유가 사라집니다.
- 기본값과 동일한 항목은 출력에서 **생략**되고, 실제 적용될 값만 정리해 보여줍니다. → 그래서 `writeable`/`read only` 중복이 정리되어 보인 것입니다.

**실습 출력 해석**

| 출력 | 의미 |
|---|---|
| `Loaded services file OK.` | 문법 정상 |
| `Server role: ROLE_STANDALONE` | 독립 서버. (다른 값: `ROLE_DOMAIN_MEMBER`, `ROLE_ACTIVE_DIRECTORY_DC`) |
| `Weak crypto is allowed by GnuTLS (e.g. NTLM as a compatibility fallback)` | 구형 NTLM 인증을 호환용으로 허용 중이라는 **정보성 경고**. 에러 아님 |
| `idmap config * : backend = tdb` | 명시하지 않았지만 적용된 **기본값** |

### 3-6. 서비스 기동과 방화벽

```bash
firewall-cmd --permanent --add-service=samba
firewall-cmd --reload
firewall-cmd --list-all

systemctl enable --now smb nmb
```

> `--add-service=samba`는 **UDP 137/138 + TCP 139/445를 한 번에** 열어줍니다. 포트를 개별로 여는 것보다 정확하고 실수가 없습니다.
> 서비스 정의 확인: `firewall-cmd --info-service=samba`
>
> 참고: `samba-client` 서비스(UDP 137/138 아웃바운드)는 이 서버가 **클라이언트로 동작할 때** 필요합니다.

**systemd 서비스명 주의**: 유닛 이름은 `smb.service`, `nmb.service`입니다. `smbd`, `nmbd`가 아닙니다. (Debian/Ubuntu에서는 `smbd`, `nmbd`라 헷갈리기 쉽습니다.)

### 3-7. 접속 확인 — `smbstatus` 읽는 법

**접속 전 출력**
```
/var/lib/samba/lock/locking.tdb not initialised
This is normal if an SMB client has never connected to your server.
```
> **에러가 아닙니다.** 메시지 자체가 "This is normal"이라고 말하고 있습니다. 아직 아무 클라이언트도 붙지 않아 락 DB가 생성되지 않았다는 정상 안내입니다.

**접속 후 출력**
```
PID   Username    Group       Machine                                   Protocol  Encryption  Signing
4082  sambauser   sambauser   192.168.16.40 (ipv4:192.168.16.40:55322)  SMB3_11   -           partial(AES-128-GMAC)

Service      pid    Machine        Connected at
sambashare   4082   192.168.16.40  화 8월 25 12:13:29 2026 KST
IPC$         4082   192.168.16.40  화 8월 25 12:11:51 2026 KST
```

| 필드 | 해석 |
|---|---|
| `SMB3_11` | **SMB 3.1.1**로 협상됨. 현재 최신이자 가장 안전한 방언 |
| `IPC$` | Inter-Process Communication — 공유 목록 조회·인증 협상·RPC 통신용 **관리 숨김 공유**. 그래서 실제 공유(`sambashare`)보다 **먼저** 연결됨 (12:11:51 → 12:13:29) |
| `Encryption: -` | SMB3 암호화 **미적용** (활성화하려면 `smb encrypt = required`) |
| `Signing: partial(AES-128-GMAC)` | 패킷 서명(변조 방지) 부분 적용. SMB3.1.1의 기본 서명 알고리즘 |
| PID가 동일(4082) | 하나의 smbd 자식 프로세스가 한 클라이언트의 모든 연결을 처리 |

**Locked files 섹션 해석**
```
Pid   User(ID)  DenyMode   Access     R/W     Oplock       SharePath   Name   Time
1414  1000      DENY_NONE  0x100081   RDONLY  LEASE(RH)    /sambatest  music  ...
```

| 필드 | 의미 |
|---|---|
| `DENY_NONE` | 다른 사용자의 접근을 **막지 않음** (반대: `DENY_ALL`, `DENY_WRITE`) |
| `Access 0x100081` | 요청한 접근 마스크 (읽기 + 속성 읽기 등) |
| `RDONLY` | 읽기 전용으로 열림 |
| `Oplock: LEASE(RH)` | **Read + Handle 리스**. Windows 탐색기가 디렉터리를 열어두고 캐싱 중이라는 뜻 |
| `Oplock: NONE` | 리스 없음 — 매번 서버에 확인 |

> **Oplock/Lease란?** 클라이언트가 "이 파일은 나만 쓰고 있으니 로컬 캐시를 믿어도 된다"는 보증을 서버에서 받는 것입니다. 다른 클라이언트가 접근하면 서버가 리스를 회수(break)하고 캐시를 무효화시킵니다. 성능 최적화 장치이며, `music`·`.`(현재 디렉터리) 항목이 잡혀 있는 것은 **탐색기 창이 그 폴더를 열어둔 상태**라는 뜻입니다.

**Windows 클라이언트 접속**
```
탐색기 주소창 →  \\192.168.16.81\sambashare
자격증명    →  sambauser / (smbpasswd로 설정한 비밀번호)

# 명령 프롬프트에서 드라이브 매핑
net use Z: \\192.168.16.81\sambashare /user:sambauser
net use Z: /delete          # 해제
```

**Linux에서 접속 확인**
```bash
smbclient -L //192.168.16.81 -U sambauser              # 공유 목록 조회
smbclient //192.168.16.81/sambashare -U sambauser      # 대화형(FTP 유사) 접속
mount -t cifs //192.168.16.81/sambashare /mnt -o username=sambauser,vers=3.1.1

# 자격증명 파일 사용 (fstab에 비밀번호 노출 방지)
echo -e "username=sambauser\npassword=P@ssw0rd" > /root/.smbcred
chmod 600 /root/.smbcred
mount -t cifs //192.168.16.81/sambashare /mnt -o credentials=/root/.smbcred
```

### 3-8. Samba 4.23 최신 변경사항 (실습 버전과 직결)

`smbstatus` 출력의 **Samba version 4.23.5** — 이 4.23 계열에서 바뀐 주요 사항입니다.

| 변경 | 내용 |
|---|---|
| **SMB3 Unix Extensions 기본 활성화** | 4.23부터 기본값. Linux 클라이언트가 SMB3 위에서 **POSIX 권한·심볼릭 링크·하드 링크·특수 파일**을 제대로 다룰 수 있게 됨. 예전에 NFS를 써야 했던 상황 일부를 SMB로 대체 가능 |
| **SMB over QUIC** | `server smb transports = +quic`로 QUIC 전송 지원. 서버 측은 커널 모듈 필요, 클라이언트는 ngtcp2 사용자공간 폴백 가능. 방화벽·NAT 환경에서 445 없이 SMB 사용 가능 |
| **새 파라미터** | `client smb transports`(기본 tcp,nbt), `server smb transports`(기본 tcp,nbt), `smbd profiling share`(기본 no), `winbind varlink service`(기본 no) |
| **타임스탬프 즉시 갱신** | 기존 지연 갱신 방식에서 Windows Server 2016 이후와 동일한 **즉시 갱신** 방식으로 변경 |
| **Prometheus 메트릭** | `smb_prometheus_endpoint` 유틸로 Grafana 연동 모니터링 가능 |
| **공유별 프로파일링** | `smbstatus`로 공유 단위 성능 통계 수집 |

> 실습 관점에서의 실질적 영향은 **SMB3 POSIX 확장 기본 활성화**입니다. Linux ↔ Linux 간에도 SMB로 심볼릭 링크가 정상 동작합니다.

---

## 4. SELinux — 오늘 실습의 진짜 핵심

### 4-1. 이름과 개념

- **SE = Security Enhanced** (메모 확인 O)
- 미국 NSA가 개발해 리눅스 커널에 통합된 **MAC(Mandatory Access Control, 강제적 접근제어)** 시스템.

**DAC vs MAC — 반드시 구분할 것**

| 구분 | DAC (기존 리눅스 권한) | MAC (SELinux) |
|---|---|---|
| 정식 명칭 | Discretionary Access Control | Mandatory Access Control |
| 결정 주체 | **파일 소유자**가 임의로 결정 | **시스템 정책**이 강제 결정 |
| 예시 | `chmod 777` 하면 누구나 접근 | 777이어도 정책이 막으면 차단 |
| 우회 | 소유자/root가 마음대로 변경 | root도 정책을 벗어날 수 없음 |
| 판단 근거 | UID/GID + rwx | **컨텍스트(label)**: user:role:type:level |

> **메모 보강**: "kernel : 하드웨어, 사용자, 운영체제 사이에서 중요한 역할" → 커널은 하드웨어와 응용 프로그램 사이의 **중재자**이고, SELinux는 그 커널 안에서 **LSM(Linux Security Module)** 훅으로 동작합니다. 시스템 콜이 커널에 들어오는 지점마다 검사하므로 **애플리케이션 레벨에서 우회가 불가능**합니다.
>
> **접근 허용 조건**: `DAC 통과` **AND** `MAC(SELinux) 통과` — 둘 다 만족해야 접근됩니다.

### 4-2. 오늘 문제가 생긴 정확한 메커니즘

```
smbd 프로세스 컨텍스트 : system_u:system_r:smbd_t:s0
/sambatest 디렉터리     : system_u:object_r:default_t:s0   ← 문제!
```

SELinux targeted 정책은 **`smbd_t` 도메인이 `samba_share_t` 타입에만 접근**하도록 규정합니다. `chmod 777`로 DAC를 아무리 열어도, 타입이 `default_t`이면 MAC에서 차단됩니다.

**확인 명령**
```bash
ls -Zd /sambatest              # 디렉터리의 SELinux 컨텍스트
ps -eZ | grep smbd             # smbd 프로세스의 도메인
```

### 4-3. 세 가지 모드

Red Hat 9 문서 기준:

| 모드 | 동작 | 용도 |
|---|---|---|
| `enforcing` | *"SELinux security policy is enforced"* — 정책 위반을 **차단하고 AVC 로그 기록** | 운영 환경 (권장) |
| `permissive` | *"SELinux prints warnings instead of enforcing"* — 차단하지 않고 **경고만 기록** | 디버깅·정책 튜닝 |
| `disabled` | 정책을 아예 로드하지 않음 | 비권장 |

### 4-4. 설정 파일과 실습 출력 해석

```bash
vi /etc/selinux/config
```
```
SELINUX=enforcing        # → 실습에서 disabled 로 변경
SELINUXTYPE=targeted     # 지정된 프로세스만 보호 (기본, 대부분 이것)
                         # mls = Multi Level Security (군/정부급 다중등급)
```

> **`/etc/selinux/config` 변경은 재부팅 후에 적용됩니다.**
> 또한 Red Hat 문서는 *"On the next boot, SELinux relabels all the files and directories within the system"* — 모드를 되돌릴 때 전체 재라벨링이 일어나 **부팅이 오래 걸릴 수 있음**을 명시합니다.

실습에서 나온 `sestatus` 출력이 이 원리를 정확히 보여줍니다:

```
SELinux status:                 enabled
Current mode:                   enforcing      ← 지금 메모리에서 동작 중인 모드
Mode from config file:          disabled       ← 설정 파일에 적힌 다음 부팅 모드
Loaded policy name:             targeted
Policy MLS status:              enabled
Max kernel policy version:      33
```

> **두 값이 다르다 = 설정 파일은 바꿨지만 아직 재부팅하지 않았다.** 이 상태에서 "왜 아직도 막히지?"라고 헤매기 쉽습니다. 재부팅 후:
> ```
> [root@localhost ~]# sestatus
> SELinux status:  disabled
> ```

### 4-5. 명령어 모음

```bash
getenforce                 # 현재 모드 한 줄 출력
sestatus                   # 상세 상태
sestatus -v                # 프로세스·파일 컨텍스트까지

setenforce 0               # enforcing → permissive (즉시, 재부팅 시 원복)
setenforce 1               # permissive → enforcing

ls -Z /sambatest           # 파일 컨텍스트
ps -eZ | grep smbd         # 프로세스 컨텍스트
id -Z                      # 내 사용자 컨텍스트

getsebool -a | grep samba  # samba 관련 boolean 전체 목록
semanage fcontext -l | grep samba   # 등록된 컨텍스트 규칙
semanage port -l | grep -i smb      # 허용된 포트 정책
```

### 4-6. **끄지 않고 해결하기** — 실무 정답

수업에서는 이해를 위해 `SELINUX=disabled`로 껐지만, 실무에서는 **정책을 맞춰주는 것**이 정답입니다. SELinux를 끄는 것은 방화벽을 끄는 것과 같습니다.

```bash
# 도구 설치 (semanage는 별도 패키지)
dnf install -y policycoreutils-python-utils setroubleshoot-server
```

#### ① Samba 공유 디렉터리 라벨링

```bash
# 임시 (재라벨링 시 사라짐)
chcon -t samba_share_t /sambatest

# 영구 (규칙 DB에 등록 — 이 방법을 쓸 것)
semanage fcontext -a -t samba_share_t "/sambatest(/.*)?"
restorecon -Rv /sambatest
```
> `semanage fcontext -a`는 **규칙만 등록**합니다. `restorecon`으로 실제 파일에 적용해야 효과가 납니다. 두 명령은 항상 한 쌍입니다.
> 정규식 `"(/.*)?"` = "이 디렉터리 자신과 그 아래 모든 것".

**Samba 관련 SELinux 타입**

| 타입 | 용도 |
|---|---|
| `samba_share_t` | **Samba 전용** 공유 디렉터리 (가장 일반적) |
| `public_content_t` | 여러 서비스(Apache, FTP, rsync, Samba)가 **읽기** 공유 |
| `public_content_rw_t` | 여러 서비스가 **읽기+쓰기** 공유 (`allow_smbd_anon_write` boolean 필요) |
| `samba_etc_t` | `/etc/samba` 설정 파일 |
| `user_home_t` / `user_home_dir_t` | 홈 디렉터리 (`[homes]` 공유 시) |

#### ② Boolean 설정

```bash
setsebool -P samba_enable_home_dirs on   # [homes] 공유 활성화
setsebool -P samba_export_all_ro on      # 임의 경로 읽기 전용 공유 허용
setsebool -P samba_export_all_rw on      # 임의 경로 읽기/쓰기 공유 허용
setsebool -P use_samba_home_dirs on      # 원격 삼바를 홈 디렉터리로 사용
setsebool -P smbd_anon_write on          # 공개 영역 익명 쓰기 허용
setsebool -P samba_share_nfs on          # NFS 마운트 지점을 삼바로 재공유

# NFS 측
setsebool -P nfs_export_all_ro on
setsebool -P nfs_export_all_rw on
```
> **`-P` 플래그가 핵심입니다.** 없으면 재부팅 시 원복됩니다. (`-P` = Persistent)
> `samba_export_all_rw`는 편리하지만 "어떤 경로든 삼바가 쓸 수 있다"는 넓은 허용이므로, 가능하면 **`semanage fcontext`로 해당 디렉터리만 라벨링**하는 쪽이 안전합니다.

#### ③ 차단 원인 진단

```bash
ausearch -m avc -ts recent                    # 최근 AVC(접근 거부) 로그
ausearch -m avc -ts today | audit2allow -w    # 사람이 읽을 수 있는 설명
sealert -a /var/log/audit/audit.log           # 해석 + 해결책 자동 제안
journalctl -t setroubleshoot                  # 요약 알림
```

> ### 증상 감별 요령 (실무에서 가장 유용)
> **"권한은 다 줬는데 안 된다"** → 십중팔구 SELinux입니다.
>
> ```bash
> setenforce 0        # 임시로 permissive
> # → 여기서 되면 SELinux 문제 확정
> setenforce 1        # 반드시 되돌리고
> # → semanage fcontext / setsebool 로 정식 해결
> ```
> `setenforce 0` 상태로 방치하고 "해결했다"고 넘어가는 것이 가장 흔한 실수입니다.

### 4-7. 완전 비활성화 시 주의 (RHEL 9 변경점)

메모에 캡처된 `/etc/selinux/config` 주석 그대로, RHEL 8까지와 RHEL 9는 다릅니다.

| 방법 | 결과 |
|---|---|
| `/etc/selinux/config`에 `SELINUX=disabled` | **정책만 로드하지 않음.** SELinux 인프라는 커널에 남아 있음. 나중에 커널 수정 없이 재활성화 가능 |
| 커널 파라미터 `selinux=0` | **부팅 시점부터 완전 비활성화.** 인프라 자체가 로드되지 않음 |

```bash
# 완전 비활성화
grubby --update-kernel ALL --args selinux=0

# 되돌리기
grubby --update-kernel ALL --remove-args selinux
```

> RHEL 8까지는 `SELINUX=disabled`가 부팅 시 완전 비활성화였지만, **RHEL 9부터는 "정책 없이 SELinux가 동작하는 상태"** 로 의미가 바뀌었습니다. 메모에 캡처된 config 파일의 `NOTE:` 주석이 정확히 이 내용을 설명하고 있습니다.

---

## 5. 호스트네임 변경

```bash
hostnamectl set-hostname server     # 영구 설정 (/etc/hostname에 기록 + 즉시 적용)
hostname                            # 현재 이름 확인
hostnamectl                         # 상세 정보
hostnamectl status                  # 위와 동일
```

### 5-1. 메모에서 확인할 점 — 프롬프트가 안 바뀐 이유

```
[root@localhost sambatest]# hostnamectl set-hostname server
[root@localhost sambatest]# hostname
server
```

호스트네임은 바뀌었는데 프롬프트는 여전히 `localhost`입니다.

> **원인**: 셸 프롬프트 `PS1`의 `\h`(호스트명)는 **셸이 시작될 때 한 번 읽은 값**을 씁니다. 이미 열려 있는 셸 세션에는 반영되지 않습니다.
>
> **해결**
> ```bash
> exec bash          # 현재 셸을 새로 교체
> # 또는 로그아웃 후 재로그인
> ```

### 5-2. `hostname server` vs `hostnamectl set-hostname server`

| 명령 | 효과 | 재부팅 후 |
|---|---|---|
| `hostname server` | 커널의 **transient** 호스트네임만 변경 | **사라짐 (임시)** |
| `hostnamectl set-hostname server` | `/etc/hostname` 기록 + 즉시 적용 | **유지 (영구)** |

> **메모 수정 포인트 ⑥**: 메모 마지막 줄의 `hostname server`는 이미 `hostnamectl`로 설정한 뒤였으므로 **중복**이며, 만약 이것만 단독으로 썼다면 재부팅 시 원래 이름으로 돌아갑니다. 영구 설정은 반드시 `hostnamectl set-hostname`을 쓰세요.

### 5-3. 호스트네임의 세 종류 (systemd)

| 종류 | 설명 | 저장 위치 |
|---|---|---|
| **Static** | 영구 호스트네임 | `/etc/hostname` |
| **Transient** | 커널이 현재 들고 있는 이름. DHCP로 바뀔 수 있음 | 메모리 |
| **Pretty** | "히소카의 실습 서버" 처럼 자유 형식 표시용 (UTF-8, 공백 허용) | `/etc/machine-info` |

```bash
hostnamectl set-hostname server --static
hostnamectl set-hostname "SK 실습 서버" --pretty
hostnamectl set-hostname server --transient
```

### 5-4. `hostnamectl` 출력 읽기

```
 Static hostname: server
       Icon name: computer-vm
         Chassis: vm 🖴
      Machine ID: e9c35e6cd16f4c76a68e8b3dc83245a7
         Boot ID: 46fa7f97ce9241e589c53ac2411e500e
  Virtualization: oracle
Operating System: Rocky Linux 9.7 (Blue Onyx)
     CPE OS Name: cpe:/o:rocky:rocky:9::baseos
          Kernel: Linux 5.14.0-611.5.1.el9_7.x86_64
    Architecture: x86-64
 Hardware Vendor: innotek GmbH
  Hardware Model: VirtualBox
```

| 항목 | 의미 |
|---|---|
| `Virtualization: oracle` | VirtualBox(Oracle) 가상머신임을 **시스템이 스스로 인식** |
| `Machine ID` | `/etc/machine-id`. 설치 시 생성되는 고유 ID. **VM 복제 시 반드시 재생성해야 함** |
| `Boot ID` | 부팅할 때마다 새로 생성 |
| `CPE OS Name` | 표준화된 OS 식별자 (보안 취약점 매칭용) |

> ### ⚠️ VM 복제 시 함정 (오늘 실습과 직결)
> 92번 노드는 81번의 **복제본**입니다. 복제하면 `machine-id`가 같아져서 **DHCP가 같은 IP를 두 대에 배정**하거나 systemd journal이 섞이는 문제가 생깁니다.
> ```bash
> # 복제한 VM에서 실행
> rm -f /etc/machine-id
> systemd-machine-id-setup
> # NetworkManager UUID도 재생성 권장
> ```

### 5-5. `/etc/hosts` 함께 정리

```bash
vi /etc/hosts
```
```
127.0.0.1      localhost localhost.localdomain localhost4
::1            localhost localhost.localdomain localhost6
192.168.16.81  server  server.example.com
192.168.16.92  client  client.example.com
```

이렇게 해두면 IP 대신 이름으로 접속할 수 있습니다:
```bash
mount -t nfs server:/nfsserver /nfsclient
smbclient -L //server -U sambauser
```

> **주의**: `/etc/hostname`을 직접 편집(`vi /etc/hostname`)해도 되지만, 그 경우 **즉시 적용되지 않고 재부팅이 필요**합니다. `hostnamectl set-hostname`은 파일 기록과 커널 적용을 동시에 하므로 이 명령을 쓰는 것이 정석입니다. 메모에서 `vi /etc/hosts`와 `vi /etc/hostname`을 둘 다 편집했는데, `hostnamectl`을 먼저 썼다면 `/etc/hostname` 편집은 불필요합니다.

---

## 6. rsyslog — 로그 중앙 수집 (오후 수업)

### 6-0. 왜 rsyslog인가 — 구조 이해

메모의 한 줄이 이 주제의 전부를 요약합니다.

```
rsyslog server  <->  rsyslog client
DB 저장               event
```

**읽는 법**
- **클라이언트** 쪽에서 발생하는 것은 **event(이벤트 로그)** 입니다. 로그인 실패, 서비스 시작, 커널 경고 같은 모든 사건이 여기 해당합니다.
- **서버** 쪽은 그 이벤트를 받아 **저장(DB화)** 합니다. 파일로 쌓거나 데이터베이스에 넣습니다.
- 화살표가 **양방향(`<->`)** 으로 그려진 이유: 서버도 자기 자신의 로그를 남기는 클라이언트 역할을 동시에 하기 때문입니다. 즉 "서버/클라이언트"는 별개의 프로그램이 아니라 **같은 `rsyslogd`가 설정에 따라 두 역할을 겸하는 것**입니다.

**왜 로그를 한곳에 모으나?**
- 서버가 10대, 100대가 되면 문제가 생겼을 때 각 서버에 SSH로 들어가 `/var/log`를 뒤지는 것이 불가능합니다.
- 침입자가 서버를 장악하면 **가장 먼저 하는 일이 로그 삭제**입니다. 로그를 다른 서버로 즉시 보내두면 증거가 남습니다.
- 여러 서버의 로그를 시간순으로 합쳐 봐야 장애의 전파 경로가 보입니다.

### 6-1. 설치와 dnf 출력 읽기

```bash
dnf install -y rsyslog rsyslog-doc
```

**실습 출력의 의미**

| 출력 | 해석 |
|---|---|
| `꾸러미 rsyslog-8.2506.0-2.el9.x86_64가 이미 설치되어 있습니다` | rsyslog는 **Rocky Linux 기본 설치 패키지**. 이미 깔려 있음 |
| `설치 중: rsyslog-doc  8.2510.0-2.el9  noarch` | `-doc`만 **새로 설치**. 문서 패키지라 아키텍처 무관(`noarch`) |
| `향상 중: rsyslog 8.2510.0-2.el9`, `rsyslog-logrotate` | 저장소에 더 최신 버전이 있어 **업그레이드(upgrade)** 됨. 8.2506.0 → **8.2510.0** |
| `연결 확인 / 연결 시험 / 연결 실행` | 한국어 로케일에서 dnf의 **transaction check / test / run** 이 이렇게 번역됨 |
| `정리 : rsyslog-8.2506.0` | 업그레이드 후 **구버전 제거(cleanup)** |

> **`rsyslog-doc`을 왜 설치했나?** 설치하면 `/usr/share/doc/rsyslog-*/` 아래에 HTML 문서 전체가 들어옵니다. 설정 파일 1행의 주석이 가리키는 그 경로입니다.
> ```
> # For more information see /usr/share/doc/rsyslog-*/rsyslog_conf.html
> ```
> 인터넷이 안 되는 폐쇄망 서버에서 특히 유용합니다.

> **`rsyslog-logrotate`가 같이 올라온 이유**: 로그는 계속 쌓이면 디스크를 가득 채웁니다. logrotate가 `/var/log/messages` 등을 주기적으로 잘라내고 압축·삭제해 줍니다. rsyslog와 짝을 이루는 패키지입니다.

### 6-2. 포트 — 514번

메모: **"514번 포트: rsyslog의 기본 포트"**

- syslog 프로토콜의 **표준 포트가 514**입니다. UDP와 TCP 양쪽 모두 514를 씁니다.
- 설정 파일에서 확인되는 두 줄:
  ```
  $InputUDPServerRun 514
  $InputTCPServerRun 514
  ```
  → 이 서버가 **UDP 514와 TCP 514 양쪽에서 로그를 수신**하도록 열어둔 상태입니다.

**UDP 514 vs TCP 514 — 왜 둘 다 있나**

| 구분 | UDP 514 | TCP 514 |
|---|---|---|
| 특징 | 비연결형, 빠름, 오버헤드 없음 | 연결형, 재전송·순서 보장 |
| 단점 | 네트워크가 밀리면 **로그가 소리 없이 유실** | 상대적으로 느리고 연결 유지 비용 |
| 전통 | syslog의 **원래 방식** | 신뢰성이 필요할 때 |

> 설정 파일의 주석이 이 점을 정확히 짚고 있습니다:
> ```
> # # Remote Logging (we use TCP for reliable delivery)
> ```
> "**신뢰성 있는 전달을 위해 TCP를 쓴다**" — 보안 감사 로그처럼 하나도 잃으면 안 되는 로그는 TCP가 정답입니다.

### 6-3. 모듈 개념 — im / om

메모의 핵심 두 줄:
```
im: input module의 약자   → eventlog들이 server로 input됨
om: output module
```

rsyslog는 **모듈형 구조**입니다. 로그가 흘러가는 경로가 이렇게 나뉩니다.

```
 [입력 im*]  →  [규칙/필터]  →  [출력 om*]
  로그 수집        선별·분류        저장·전달
```

**설정 파일에 실제로 등장한 모듈들**

| 모듈 | 종류 | 설정 파일에서의 역할 |
|---|---|---|
| `imuxsock` | input | 로컬 시스템 로깅 지원 — `logger` 명령 등이 쓰는 **유닉스 소켓**에서 수신 |
| `imjournal` | input | **systemd 저널**에 접근해 로그를 가져옴 |
| `imudp` | input | **UDP** 로 원격 syslog 수신 |
| `imtcp` | input | **TCP** 로 원격 syslog 수신 |
| `imklog` | input | **커널 메시지** 읽기 (주석 처리됨 — journald가 이미 읽으므로 중복) |
| `immark` | input | `--MARK--` 주기적 표시 메시지 (주석 처리됨) |
| `omfile` | output | **파일**에 기록 |
| `omusrmsg` | output | **로그인한 사용자 터미널**에 메시지 전송 |
| `omfwd` | output | **원격 서버로 전달**(forward) |

> **`im`/`om` 접두사 규칙**: 모듈 이름만 봐도 방향을 알 수 있습니다. `im` = **in**put **m**odule, `om` = **o**utput **m**odule. `imudp`는 "UDP로 받는다", `omfwd`는 "forward로 내보낸다"는 뜻입니다.

### 6-4. `/etc/rsyslog.conf` 전체 해부

#### ① GLOBAL DIRECTIVES

```
global(workDirectory="/var/lib/rsyslog")
```
> rsyslog가 작업 파일(큐 스풀, 상태 파일 등)을 놓을 디렉터리입니다. 원격 서버가 죽었을 때 메시지를 임시로 쌓아두는 디스크 큐도 여기 생깁니다.

#### ② MODULES

```
module(load="builtin:omfile" Template="RSYSLOG_TraditionalFileFormat")
```
> 파일 출력의 **기본 형식**을 지정합니다. `RSYSLOG_TraditionalFileFormat` = 전통적인 syslog 형식(`Aug 25 13:20:11 server sshd[1234]: message`). 초 단위까지만 기록하는 옛 형식입니다.

```
module(load="imuxsock"    # provides support for local system logging (e.g. via logger command)
       SysSock.Use="off") # Turn off message reception via local log socket;
                          # local messages are retrieved through imjournal now.
```
> **중요한 구조 변화**: 모듈은 로드하지만 `SysSock.Use="off"`로 **소켓 직접 수신은 껐습니다.** 주석이 이유를 설명합니다 — "로컬 메시지는 이제 **imjournal을 통해** 가져온다".
>
> 즉 현대 RHEL/Rocky의 로그 흐름은 이렇습니다:
> ```
> 애플리케이션 → systemd-journald → (imjournal) → rsyslog → /var/log/*
> ```
> journald가 1차 수집을 하고, rsyslog가 그걸 받아 전통적인 텍스트 파일로 남기는 **2단 구조**입니다.

```
module(load="imjournal"             # provides access to the systemd journal
       UsePid="system"              # PID nummber is retrieved as the ID of the process the journal entry originates from
       FileCreateMode="0644"        # Set the access permissions for the state file
       StateFile="imjournal.state") # File to store the position in the journal
```

| 파라미터 | 의미 |
|---|---|
| `UsePid="system"` | 저널 항목을 만든 **프로세스의 PID**를 기록 |
| `FileCreateMode="0644"` | 상태 파일 권한 |
| `StateFile="imjournal.state"` | **저널의 어디까지 읽었는지 위치를 저장.** rsyslog가 재시작해도 이어서 읽어 중복·누락을 방지 |

```
include(file="/etc/rsyslog.d/*.conf" mode="optional")
```
> `/etc/rsyslog.d/` 아래 `.conf` 파일들을 모두 읽어옵니다. `mode="optional"`이라 파일이 없어도 에러가 나지 않습니다.
> **실무 팁**: `rsyslog.conf` 본문을 직접 고치는 것보다, `/etc/rsyslog.d/50-remote.conf` 같은 별도 파일을 만드는 편이 안전합니다. 패키지 업데이트 시 본 파일이 덮이더라도 설정이 살아남습니다.

#### ③ 원격 수신 활성화 — 두 가지 문법이 공존

설정 파일에는 **같은 기능이 두 문법으로** 들어 있습니다.

**(가) 신형(RainerScript) — 주석 처리된 상태**
```
# Provides UDP syslog reception
# for parameters see http://www.rsyslog.com/doc/imudp.html
#module(load="imudp") # needs to be done just once
#input(type="imudp" port="514")

# Provides TCP syslog reception
# for parameters see http://www.rsyslog.com/doc/imtcp.html
#module(load="imtcp") # needs to be done just once
#input(type="imtcp" port="514")
```

**(나) 구형(legacy) — 실제로 활성화한 부분**
```
$ModLoad imudp
$InputUDPServerRun 514

$ModLoad imtcp
$InputTCPServerRun 514
```

> ### 두 문법의 관계
> | 구분 | 신형 | 구형(legacy) |
> |---|---|---|
> | 표기 | `module(load="imudp")` / `input(type="imudp" port="514")` | `$ModLoad imudp` / `$InputUDPServerRun 514` |
> | 이름 | RainerScript (rsyslog 개발자 Rainer Gerhards의 이름) | `$`로 시작하는 옛 지시어 |
> | 상태 | 현재 **권장** 문법 | **여전히 동작**하지만 옛 방식 |
>
> **기능은 동일합니다.** 이번 실습처럼 legacy 문법을 써도 UDP/TCP 514 수신은 정상 동작합니다. 다만 새로 작성할 때는 신형을 쓰는 편이 좋습니다.
>
> **⚠️ 반드시 주의할 점** — 주석에 적힌 `# needs to be done just once`가 핵심입니다. **모듈 로드는 딱 한 번만 해야 합니다.** 위쪽 신형 블록의 주석을 풀면서 아래 legacy 줄을 지우지 않으면 `imudp`가 두 번 로드되어 rsyslog가 에러를 내고 뜨지 않습니다. 둘 중 **하나만** 남기세요.

#### ④ RULES — 규칙 문법

여기가 rsyslog의 심장입니다. 기본 형식:

```
facility.priority    action
```

**설정 파일의 실제 규칙들**

```
# Log all kernel messages to the console.
#kern.* action(type="omfile" file="/dev/console")
```
> 모든 커널 메시지를 콘솔에 출력. **주석 처리**되어 있습니다. 주석의 이유 설명: *"Logging much else clutters up the screen"* — 화면이 지저분해지기 때문.

```
*.info;mail.none;authpriv.none;cron.none action(type="omfile" file="/var/log/messages")
```
> **가장 중요한 한 줄.** 해석하면:
> - `*.info` = **모든** 시설(facility)의 **info 이상** 등급을 기록
> - `;`로 여러 선택자를 연결
> - `mail.none` = **mail 시설은 제외**
> - `authpriv.none` = **인증 로그 제외**
> - `cron.none` = **cron 로그 제외**
> - → 결과: "웬만한 건 다 `/var/log/messages`에, 단 메일·인증·크론은 각자 전용 파일이 있으니 빼라"
>
> 주석도 같은 말을 합니다: *"Log anything (except mail) of level info or higher. Don't log private authentication messages!"*
>
> **`none`의 정확한 의미** — rsyslog.conf(5) man 원문: *"none stands for no priority of the given facility"*. 즉 "그 시설의 어떤 등급도 기록하지 않음"입니다.

```
authpriv.* action(type="omfile" file="/var/log/secure")
```
> 주석: *"The authpriv file has restricted access."*
> `authpriv`는 **민감한 인증 정보**(su/sudo, 로그인 실패, SSH 인증)를 담습니다. 그래서 `/var/log/secure`는 **root만 읽을 수 있는 권한(600)** 으로 관리됩니다. 위 `*.info` 규칙에서 굳이 `authpriv.none`으로 뺀 이유가 이것입니다 — 아무나 읽는 `messages`에 섞이면 안 되니까요.

```
mail.* action(type="omfile" file="/var/log/maillog" sync="on")
```
> 메일 관련 모든 등급을 `/var/log/maillog`로. `sync="on"`은 **디스크 동기화 쓰기** — 매 기록마다 디스크에 확실히 씁니다. NFS의 `sync` 옵션과 같은 개념으로, 안전하지만 느립니다.

```
cron.* action(type="omfile" file="/var/log/cron")
```
> 예약 작업(cron) 로그 전용 파일.

```
*.emerg action(type="omusrmsg" users="*")
```
> 주석: *"Everybody gets emergency messages"*
> - `*.emerg` = 모든 시설의 **최고 위험 등급**
> - `omusrmsg` = 파일이 아니라 **로그인한 사용자의 터미널로 직접 메시지 전송**
> - `users="*"` = **모든 사용자**에게
> → 시스템이 곧 죽을 상황이면 로그 파일에 조용히 남기는 게 아니라 화면에 대고 알린다는 뜻입니다.

```
uucp,news.crit action(type="omfile" file="/var/log/spooler")
```
> 주석: *"Save news errors of level crit and higher in a special file."*
> `uucp,news` — **콤마로 여러 시설을 한 번에** 지정하는 문법입니다. 둘 다 crit 이상만 `/var/log/spooler`로. (uucp/news는 오늘날 거의 안 쓰는 옛 서비스입니다.)

```
local7.* action(type="omfile" file="/var/log/boot.log")
```
> 주석: *"Save boot messages also to boot.log"*
> `local0`~`local7`은 **용도가 정해지지 않은 예비 시설**입니다. 관례적으로 `local7`을 부팅 메시지에 씁니다. 자체 애플리케이션 로그를 분리하고 싶을 때 `local0`~`local6`을 쓸 수 있습니다.

**Facility(시설) 목록** — rsyslog.conf(5) man 기준

| 시설 | 용도 |
|---|---|
| `auth` / `security` | 시스템 보안·사용자 인증·권한 관리 |
| `authpriv` | 더 민감한 보안 이벤트 (sudo 등) |
| `cron` | 예약 작업 |
| `daemon` | 시스템 데몬 |
| `kern` | **커널**이 생성한 로그 |
| `lpr` | 인쇄 서비스 |
| `mail` | 메일 서비스 |
| `mark` | 주기적 표시 메시지 |
| `news` / `uucp` | 옛 뉴스·UUCP 서비스 |
| `syslog` | syslog 서비스 자신 |
| `user` | 사용자 공간 애플리케이션 |
| `local0` ~ `local7` | **예비(사용자 지정)** |

**Priority(등급) — 낮은 것 → 높은 것 순서**

man 원문: *"in ascending order: debug, info, notice, warning, warn, err, error, crit, alert, emerg, panic"*

| 등급 | 의미 |
|---|---|
| `debug` | 디버깅용 상세 정보 (가장 낮음) |
| `info` | 일반 정보 |
| `notice` | 정상이지만 주목할 만한 상황 |
| `warning` (=`warn`) | 경고 |
| `err` (=`error`) | 오류 |
| `crit` | 심각한 오류 |
| `alert` | 즉시 조치 필요 |
| `emerg` (=`panic`) | 시스템 사용 불가 (가장 높음) |

> ### 반드시 기억할 규칙 — "이상"의 의미
> man 원문: *"all messages of the specified priority and higher are logged"*
>
> `*.info`라고 쓰면 **info만**이 아니라 **info 이상 전부**(info, notice, warning, err, crit, alert, emerg)가 기록됩니다. 이것이 syslog의 기본 동작입니다.
>
> **정확히 그 등급만** 원하면 `=`를 씁니다:
> ```
> *.=info      # info 등급만 (그 위는 제외)
> *.!err       # err 등급 제외
> *.*          # 모든 시설의 모든 등급
> mail.none    # mail 시설은 아무것도 기록 안 함
> ```
> `*`는 위치에 따라 의미가 달라집니다. man 원문: *"stands for all facilities or all priorities, depending on where it is used (before or after the period)"*
> - `*.err` → **모든 시설**의 err 이상
> - `mail.*` → mail 시설의 **모든 등급**

#### ⑤ 원격 전달 규칙 (sample forwarding rule)

파일 맨 끝의 주석 처리된 예시입니다. **클라이언트가 서버로 로그를 보낼 때** 쓰는 부분입니다.

```
# ### sample forwarding rule ###
#action(type="omfwd"
#       # An on-disk queue is created for this action. If the remote host is
#       # down, messages are spooled to disk and sent when it is up again.
#queue.filename="fwdRule1"       # unique name prefix for spool files
#queue.maxdiskspace="1g"         # 1gb space limit (use as much as possible)
#queue.saveonshutdown="on"       # save messages to disk on shutdown
#queue.type="LinkedList"         # run asynchronously
#action.resumeRetryCount="-1"    # infinite retries if host is down
#       # Remote Logging (we use TCP for reliable delivery)
#       # remote_host is: name/ip, e.g. 192.168.0.1, port optional e.g. 10514
#Target="remote_host" Port="XXX" Protocol="tcp")
```

**한 줄씩 해석**

| 항목 | 의미 |
|---|---|
| `type="omfwd"` | 출력 모듈로 **forward(원격 전달)** 사용 |
| `queue.filename="fwdRule1"` | 디스크 큐 스풀 파일의 **고유 이름 접두사** |
| `queue.maxdiskspace="1g"` | 큐가 쓸 수 있는 **디스크 한도 1GB** |
| `queue.saveonshutdown="on"` | 종료 시 **메모리에 남은 메시지를 디스크에 저장** → 재시작 후 이어서 전송 |
| `queue.type="LinkedList"` | **비동기 동작**. 로그 전송이 애플리케이션을 붙잡지 않음 |
| `action.resumeRetryCount="-1"` | **-1 = 무한 재시도.** 상대가 살아날 때까지 포기하지 않음 |
| `Target="remote_host"` | 받을 서버의 **이름 또는 IP** |
| `Port="XXX"` | 포트 (생략 가능, 예시로 10514) |
| `Protocol="tcp"` | **TCP 사용** — 주석의 "reliable delivery" |

> ### 이 블록의 핵심 아이디어 — 디스크 큐
> 주석 원문: *"An on-disk queue is created for this action. If the remote host is down, messages are spooled to disk and sent when it is up again."*
>
> **원격 로그 서버가 죽어 있으면 로그를 버리는 게 아니라 디스크에 쌓아뒀다가, 살아나면 밀린 것까지 전부 보냅니다.** 이것이 rsyslog가 단순 syslog보다 뛰어난 이유입니다. UDP로 그냥 쏘면 서버가 죽은 동안의 로그는 영원히 사라집니다.
>
> 이 큐 파일들이 놓이는 곳이 바로 ①에서 본 `global(workDirectory="/var/lib/rsyslog")` 입니다. 설정의 앞뒤가 이렇게 연결됩니다.

### 6-5. 서버/클라이언트 역할 정리

메모의 `rsyslog server <-> rsyslog client` 구조를 설정 파일 항목에 대응시키면 이렇습니다.

| 역할 | 설정 파일에서 담당하는 부분 | 방향 |
|---|---|---|
| **서버 (수집)** | `$ModLoad imudp` / `$InputUDPServerRun 514`<br>`$ModLoad imtcp` / `$InputTCPServerRun 514` | **받는다** (in) |
| **클라이언트 (전송)** | `action(type="omfwd" Target="..." Port="..." Protocol="tcp")` | **보낸다** (out) |
| **양쪽 공통 (저장)** | `*.info;mail.none;... action(type="omfile" file="/var/log/messages")` 등 RULES 전체 | **쌓는다** |

> 이번 실습에서는 **81번 서버에 수신 측(im)을 열어둔 상태**까지 진행했습니다. `$InputUDPServerRun 514`와 `$InputTCPServerRun 514`가 주석 없이 활성화되어 있다는 것이 곧 "이 서버는 이제 로그 수집 서버다"라는 뜻입니다.

---

---

## 7. rsyslog 서버 구축 — 방화벽 · 기동 · 리스닝 확인

### 7-1. 방화벽에 514 열기

```bash
firewall-cmd --permanent --add-port=514/udp
firewall-cmd --permanent --add-port=514/tcp
firewall-cmd --reload
firewall-cmd --list-all
```

결과:
```
  services: cockpit dhcpv6-client dns samba ssh
  ports: 2049/tcp 514/udp 514/tcp
```

> **읽는 법**: 오전에 연 `2049/tcp`(NFS) 옆에 `514/udp`, `514/tcp`가 추가됐습니다. `services` 줄의 `samba`는 서비스 단위로 열어서 이름으로 표시되고, 포트 단위로 연 것은 `ports` 줄에 숫자로 표시됩니다. **같은 방화벽에 두 방식이 공존**할 수 있습니다.
>
> 실습에서 `--add-port=514/udp`, `--add-port=514/tcp`를 **각각 두 번씩** 실행했지만 모두 `success`가 나왔습니다. firewalld는 **이미 있는 규칙을 다시 추가해도 오류를 내지 않고 멱등(idempotent)하게 처리**하기 때문입니다. 중복 실행해도 안전합니다.

> **`--permanent`의 함정**: `--permanent`로 추가한 규칙은 **설정 파일에만 기록**되고 현재 실행 중인 방화벽에는 즉시 반영되지 않습니다. 그래서 `--reload`가 반드시 필요합니다. 실습에서 `--reload` 후 `--list-all`을 한 순서가 정확합니다.

### 7-2. 서비스 기동

```bash
systemctl start rsyslog
systemctl enable rsyslog
systemctl restart rsyslog     # 설정을 바꾼 뒤에는 restart
```

> `start`/`enable` 차이 복습: `start`는 **지금 실행**, `enable`은 **부팅 시 자동 실행 등록**(심볼릭 링크 생성). 둘 다 해야 재부팅 후에도 살아 있습니다. `systemctl enable --now rsyslog`로 한 번에 처리할 수도 있습니다.
>
> **설정 파일을 고쳤으면 `restart`가 필요합니다.** rsyslog는 시작할 때 설정을 읽으므로, `vi /etc/rsyslog.conf`만 하고 재시작하지 않으면 아무 변화가 없습니다.

### 7-3. 리스닝 확인 도구 설치

```bash
dnf install -y net-tools lsof
```

> **왜 따로 설치하나?** `netstat`은 예전에는 기본 명령이었지만 현재 RHEL/Rocky 9에서는 **`net-tools` 패키지가 기본 설치되지 않습니다.** `lsof`도 마찬가지입니다. 최소 설치 환경에서는 이 두 개를 직접 깔아야 합니다.

### 7-4. 포트가 실제로 열렸는지 확인 — 세 가지 방법

```bash
netstat -natpl | grep 514
lsof -i tcp:514
```

**실습 출력 ①: `netstat -natpl | grep 514`**
```
tcp        0      0 0.0.0.0:514        0.0.0.0:*        LISTEN      2074/rsyslogd
tcp6       0      0 :::514             :::*             LISTEN      2074/rsyslogd
```

`netstat` 옵션 해부

| 옵션 | 의미 |
|---|---|
| `-n` | 이름 대신 **숫자**로 표시 (DNS·서비스명 조회 생략 → 빠름) |
| `-a` | **모든** 소켓 (연결된 것 + 대기 중인 것) |
| `-t` | **TCP**만 |
| `-p` | 소켓을 쓰는 **프로세스(PID/이름)** 표시 (root 권한 필요) |
| `-l` | **LISTEN** 상태만 |
| `-u` | UDP (514/udp 확인 시 필요) |

> **출력 읽는 법**
> - `0.0.0.0:514` = **모든 IPv4 주소**에서 514 포트로 들어오는 연결을 받겠다는 뜻. 특정 IP만 쓰려면 그 IP가 표시됩니다.
> - `:::514` = **IPv6** 전체 주소 (`::`는 IPv6의 `0.0.0.0`에 해당)
> - `0.0.0.0:*` = 상대방(Foreign Address)이 정해지지 않음 → 대기 상태라는 뜻
> - `LISTEN` = 연결을 기다리는 중
> - `2074/rsyslogd` = **PID 2074의 rsyslogd**가 이 포트를 잡고 있음
>
> **UDP도 확인하려면** `-t`를 `-u`로 바꾸거나 함께 씁니다: `netstat -naupl | grep 514`
>
> 메모에 `netstat -natpl grep 514`(파이프 `|` 누락)로 적힌 줄이 있는데, **파이프가 반드시 필요**합니다. 없으면 `grep`과 `514`를 netstat의 인자로 해석해 오류가 납니다.

**실습 출력 ②: `lsof -i tcp:514`**
```
COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
rsyslogd 2074 root    4u  IPv4  34838      0t0  TCP *:shell (LISTEN)
rsyslogd 2074 root    5u  IPv6  34839      0t0  TCP *:shell (LISTEN)
```

| 필드 | 의미 |
|---|---|
| `COMMAND` / `PID` / `USER` | rsyslogd, 2074, root가 소유 |
| `FD` | 파일 디스크립터 번호. `4u`, `5u` — `u`는 **읽기+쓰기(read/write)** 모드 |
| `TYPE` | IPv4 / IPv6 소켓 |
| `NAME` | `*:shell (LISTEN)` |

> ### ⚠️ `*:shell` — 헷갈리기 쉬운 표시
> `lsof`는 `-n` 옵션 없이 실행하면 **포트 번호를 `/etc/services`의 서비스 이름으로 변환**해 보여줍니다. **514/tcp는 역사적으로 `shell`(rsh, remote shell)에 할당된 포트**라서 `shell`이라고 표시된 것입니다.
>
> **rsyslog가 잘못 뜬 게 아닙니다.** 숫자로 보고 싶으면:
> ```bash
> lsof -nP -i tcp:514        # -n: DNS 조회 안 함, -P: 포트를 숫자로
> ```
> 확인: `grep 514 /etc/services` → `shell 514/tcp`, `syslog 514/udp`가 나옵니다. **TCP 514는 shell, UDP 514는 syslog**로 등록되어 있어 이런 차이가 생깁니다.

**`ss` — netstat의 현대적 대체 명령 (기본 설치됨)**
```bash
ss -tulnp | grep 514
```
> `net-tools` 설치 없이 바로 쓸 수 있습니다. 옵션 의미는 netstat과 거의 같습니다(`-t` TCP, `-u` UDP, `-l` LISTEN, `-n` 숫자, `-p` 프로세스).

### 7-5. 로그 파일 실시간 확인 — tail / head

```bash
tail -f /var/log/messages          # 실시간 추적 (핵심)
tail -n 20 /var/log/messages       # 마지막 20줄
head /var/log/messages             # 앞에서 10줄
head -n 20 /var/log/messages       # 앞에서 20줄
```

| 명령 | 동작 |
|---|---|
| `tail` | 파일 **끝**에서 기본 10줄 |
| `tail -f` | **follow** — 파일이 커지면 새 줄을 계속 화면에 출력. 종료는 `Ctrl+C` |
| `tail -n N` | 끝에서 N줄 |
| `head` | 파일 **앞**에서 기본 10줄 |

> ### 메모의 오타 정정
> | 메모 | 문제 | 정답 |
> |---|---|---|
> | `tail -f / var/log/messages` | 슬래시 뒤 **공백** → `/`와 `var/log/messages` 두 개의 인자로 해석됨 | `tail -f /var/log/messages` |
> | `tail -n -f /var/log/messages` | `-n`은 **숫자 인자**를 요구 → `-f`를 숫자로 해석해 오류 | `tail -f` 또는 `tail -n 20` |
> | `tail -f var/log/message` | 앞 `/` 없음(상대경로) + 파일명이 `message`(단수) | `tail -f /var/log/messages` |
>
> `/var/log/messages`는 **복수형 `messages`** 입니다. 6-4절의 RULES에서 본 `*.info;mail.none;...` 규칙이 기록하는 바로 그 파일입니다.

---

## 8. ★ 실습에서 실제로 발생한 에러 — rsyslog 3003

이번 수업에서 가장 값진 부분입니다. `tail -f /var/log/messages`로 확인한 실제 로그:

```
Aug 25 14:34:46 server systemd[1]: Starting System Logging Service...
Aug 25 14:34:46 server systemd[1]: Started System Logging Service.
Aug 25 14:34:46 server rsyslogd[2074]: invalid or yet-unknown config file command 'InputUDPServerRun'
                                       - have you forgotten to load a module?
                                       [v8.2510.0-2.el9 try https://www.rsyslog.com/e/3003 ]
Aug 25 14:34:46 server rsyslogd[2074]: imudp: module loaded, but no listeners defined
                                       - no input will be gathered
                                       [v8.2510.0-2.el9 try https://www.rsyslog.com/e/2212 ]
Aug 25 14:34:46 server rsyslogd[2074]: [origin software="rsyslogd" swVersion="8.2510.0-2.el9" ...] start
Aug 25 14:34:46 server rsyslogd[2074]: imjournal: journal files changed, reloading...
```

### 8-1. 무슨 일이 일어났나

수업 중 `/etc/rsyslog.conf`를 두 번 편집했고, **두 번째 버전에서 `$ModLoad imudp` / `$ModLoad imtcp` 줄이 사라졌습니다.**

| 시점 | 설정 상태 | 결과 |
|---|---|---|
| 1차 (41~45행) | `$ModLoad imudp` + `$InputUDPServerRun 514`<br>`$ModLoad imtcp` + `$InputTCPServerRun 514` | 정상 |
| 2차 | `$ModLoad` 줄이 없어지고 `$Input...ServerRun`만 남거나, 신형 블록은 여전히 주석 | **에러 3003** |

> ### 에러 3003의 공식 설명
> rsyslog 공식 문서 원문:
> - *"An invalid configuration command is part of rsyslog.conf"* (잘못된 명령)
> - *"The command is valid, but resides in a not-yet-loaded plugin"* (**명령은 맞지만 플러그인이 아직 로드되지 않음**)
> - 해결책: *"To use commands provided by plugins, the plugin must be loaded first (via `$ModLoad`). Only after that the command can be used."*
>
> 즉 **`$InputUDPServerRun`은 `imudp` 모듈이 제공하는 명령**입니다. 모듈을 먼저 로드하지 않으면 rsyslog는 그 명령어 자체를 모릅니다. 사람으로 치면 "사전에 없는 단어"인 셈입니다.

### 8-2. 두 번째 에러(2212)가 알려주는 것

```
imudp: module loaded, but no listeners defined - no input will be gathered
```

> **"모듈은 로드됐는데 리스너가 정의되지 않았다 → 아무 입력도 수집되지 않는다"**
>
> 즉 `imudp`는 어떻게든 로드됐지만, "몇 번 포트에서 들을지"를 지정하는 짝(`$InputUDPServerRun 514` 또는 `input(type="imudp" port="514")`)이 유효하게 처리되지 않아 **UDP 수신이 실질적으로 죽은 상태**라는 뜻입니다.
>
> **모듈 로드와 리스너 정의는 항상 한 쌍입니다.** 하나만 있으면 동작하지 않습니다.
> ```
> [모듈 로드]  +  [리스너 정의]  =  수신 동작
> $ModLoad imudp  +  $InputUDPServerRun 514
> module(load="imudp")  +  input(type="imudp" port="514")
> ```

### 8-3. 그런데 왜 TCP 514는 LISTEN 되고 있었나

`netstat` 결과에는 `tcp 0.0.0.0:514 LISTEN 2074/rsyslogd`가 정상적으로 보였습니다. 에러는 **UDP 쪽(`InputUDPServerRun`, `imudp`)에 대한 것**이고, TCP 쪽은 그 시점 설정에서 유효하게 처리되어 리스닝에 성공한 것입니다.

> **여기서 배울 것**: "포트가 열려 있으니 다 잘 되고 있다"고 판단하면 안 됩니다. **`netstat`은 TCP만 봤고(`-t`), UDP는 확인하지 않았습니다.** 로그를 함께 봐야 UDP가 죽어 있다는 사실이 드러납니다.
> ```bash
> netstat -naupl | grep 514     # UDP도 반드시 확인
> ss -ulnp | grep 514
> ```

### 8-4. 올바른 해결 방법

**둘 중 한 문법으로 통일하고, 모듈 로드 + 리스너 정의를 반드시 짝으로 둡니다.**

**(가) 신형 — 권장**
```
module(load="imudp")
input(type="imudp" port="514")

module(load="imtcp")
input(type="imtcp" port="514")
```

**(나) 구형 — 동작은 함**
```
$ModLoad imudp
$InputUDPServerRun 514

$ModLoad imtcp
$InputTCPServerRun 514
```

> **⚠️ 절대 섞지 말 것**: 신형 블록의 주석을 풀면서 구형 줄을 남겨두면 **`imudp` 모듈이 두 번 로드**되어 또 다른 에러가 납니다(`module already in this config`). 6-4절 ③의 주석 `# needs to be done just once`가 바로 이 경고입니다.

### 8-5. 재시작 전에 문법을 검사하는 법 (보강)

Samba에 `testparm`이 있듯, rsyslog에도 설정 검사 명령이 있습니다.

```bash
rsyslogd -N 1
```

> `-N`은 설정만 검사하고 실행하지 않습니다(숫자는 검사 상세 수준). **`systemctl restart` 전에 이것을 돌리면 3003 같은 에러를 로그를 뒤지기 전에 미리 잡을 수 있습니다.** Red Hat 9 문서도 원격 로깅 구성 시 재시작 전 이 명령을 권장합니다.

---

## 9. 클라이언트 → 서버 로그 전송

### 9-1. 클라이언트 설정 — `@` 와 `@@`

클라이언트(92번) `/etc/rsyslog.conf` 맨 아래에 추가한 두 줄:

```
*.* @@192.168.16.81:514
*.* @192.168.16.81:514
```

> ### 이 문법이 오늘의 핵심 암기 포인트
> | 표기 | 프로토콜 | 외우는 법 |
> |---|---|---|
> | `@호스트:포트` | **UDP** | @ **한 개** = 한 번 쏘고 끝 (비연결형) |
> | `@@호스트:포트` | **TCP** | @ **두 개** = 주고받는 연결 (연결형) |
>
> - `*.*` = **모든 시설의 모든 등급** 로그를 전부 보낸다는 뜻 (6-4절 ④ RULES 문법 그대로)
> - `:514` = 목적지 포트. 생략 가능하지만 rsyslog 공식 문서는 *"it is strongly advised to use an explicit port number to make sure that client and server configuration match each other"* — **명시를 강력히 권장**합니다.

> ### ⚠️ 두 줄을 다 쓰면 로그가 두 번 갑니다
> `@@`(TCP)와 `@`(UDP)를 **둘 다** 적으면 같은 메시지가 **TCP로 한 번, UDP로 한 번 총 두 번 전송**됩니다. 서버 DB에 중복 레코드가 쌓입니다.
>
> 실습에서는 두 방식을 모두 시험해 보려는 목적이었지만, **실제 운영에서는 하나만 남깁니다.** 신뢰성이 필요하면 `@@`(TCP)를 택합니다.

**신형 문법 (rsyslog 공식 권장)**
```
*.* action(type="omfwd" target="192.168.16.81" port="514" protocol="tcp")
```
> rsyslog 공식 문서는 레거시 표기에 대해 *"do NOT use this any longer!"* 라고 명시합니다. 신형은 `target`/`port`/`protocol`이 분리되어 읽기 쉽고, 6-4절 ⑤에서 본 **디스크 큐 옵션(`queue.*`, `action.resumeRetryCount`)을 함께 쓸 수 있다는 결정적 장점**이 있습니다. 레거시 `@@` 표기로는 큐를 붙일 수 없습니다.

```bash
# 클라이언트에서
systemctl start rsyslog
systemctl enable rsyslog
```

### 9-2. 전송이 되는지 시험하기 — httpd로 로그 만들기

로그가 오는지 확인하려면 **클라이언트에서 로그가 발생하는 사건**을 일부러 만들어야 합니다. 수업에서 쓴 방법이 `httpd` 서비스 조작입니다.

```bash
# 서버에서 확인 — 아직 설치 안 됨
systemctl status httpd
# Unit httpd.service could not be found.

dnf install -y httpd
```

```bash
# 클라이언트에서 서비스를 켰다 껐다 하며 로그 발생
systemctl start httpd
systemctl stop httpd
systemctl restart httpd
systemctl restart rsyslog
```

```bash
# 서버에서 실시간 확인
tail -f /var/log/messages
```

> **원리**: `systemctl start/stop/restart`를 하면 **systemd가 매번 로그를 남깁니다**(`Starting...`, `Started`, `Stopping...`, `Stopped`). 이 로그는 journald → imjournal → rsyslog를 거쳐 `*.*` 규칙에 걸려 **서버로 전송**됩니다.
>
> 서버 쪽 `/var/log/messages`에서 이미 확인한 형식이 그대로입니다:
> ```
> Aug 25 14:34:46 server systemd[1]: Stopping System Logging Service...
> Aug 25 14:34:46 server systemd[1]: Started System Logging Service.
> ```
> `server` 자리에 **클라이언트의 호스트명**이 찍히면 원격 전송이 성공한 것입니다. 그래서 오전에 `hostnamectl set-hostname`으로 이름을 구분해 둔 것이 여기서 의미를 갖습니다 — **호스트명이 둘 다 `localhost`면 어느 서버 로그인지 구분할 수 없습니다.**

> **`systemctl status`의 `Unit ... could not be found`** = 서비스 유닛 파일 자체가 없다 = **패키지가 설치되지 않았다**는 뜻입니다. `Active: inactive (dead)`(설치는 됐으나 꺼짐)와 구분해야 합니다. 뒤의 MariaDB 절에서 이 차이가 다시 나옵니다.

---

## 10. 로그를 DB에 저장 — MariaDB + ommysql

메모 첫 줄의 `rsyslog server ... DB 저장`이 여기서 실현됩니다.

### 10-1. 왜 DB에 넣나

| 텍스트 파일(`/var/log/messages`) | 데이터베이스 |
|---|---|
| `grep`, `tail`로 순차 검색 | **SQL로 조건 검색** (`WHERE FromHost='client' AND Priority<=3`) |
| 집계하려면 별도 스크립트 | `COUNT`, `GROUP BY`로 즉시 통계 |
| 웹 UI 연동 어려움 | **LogAnalyzer 같은 웹 도구가 바로 붙음** |
| 용량 커지면 느림 | 인덱스로 빠른 조회 |

### 10-2. 패키지 설치와 문서 위치 확인

```bash
ls /usr/share/doc/rsyslog
# AUTHORS  ChangeLog  README.md  html  mysql-createDB.sql  recover_qi.pl

dnf install -y mariadb-server rsyslog-mysql
```

> 6-1절에서 설치한 **`rsyslog-doc`이 여기서 값을 합니다.** `mysql-createDB.sql`이 바로 그 패키지가 넣어준 파일입니다 — DB 스키마를 직접 짤 필요 없이 **rsyslog가 기대하는 정확한 테이블 구조**를 제공합니다.
>
> | 패키지 | 역할 |
> |---|---|
> | `mariadb-server` | 데이터베이스 서버 본체 |
> | `rsyslog-mysql` | **`ommysql` 출력 모듈** 제공. 이게 없으면 `$ModLoad ommysql`이 실패 |

### 10-3. 스키마 파일 읽기

```bash
cat /usr/share/doc/rsyslog/mysql-createDB.sql
```

```sql
CREATE DATABASE Syslog;
USE Syslog;
CREATE TABLE SystemEvents
(
        ID int unsigned not null auto_increment primary key,
        CustomerID bigint,
        ReceivedAt datetime NULL,
        DeviceReportedTime datetime NULL,
        Facility smallint NULL,
        Priority smallint NULL,
        FromHost varchar(63) NULL,
        Message text,
        NTSeverity int NULL,
        ...
        SysLogTag varchar(60),
        EventLogType varchar(60),
        GenericFileName VarChar(60),
        SystemID int NULL
);

CREATE TABLE SystemEventsProperties
(
        ID int unsigned not null auto_increment primary key,
        SystemEventID int NULL ,
        ParamName varchar(255) NULL ,
        ParamValue text NULL
);
```

**핵심 컬럼 해석**

| 컬럼 | 의미 |
|---|---|
| `ID` | `auto_increment primary key` — 자동 증가 기본키 |
| `ReceivedAt` | **서버가 받은 시각** |
| `DeviceReportedTime` | **보낸 장비가 기록한 시각** — 두 시각이 다르면 시간 동기화(NTP) 문제나 전송 지연을 의심 |
| `Facility` | 시설을 **숫자로** 저장 |
| `Priority` | 등급을 **숫자로** 저장 |
| `FromHost` | **어느 호스트에서 온 로그인지** — 중앙 수집의 핵심 컬럼 |
| `Message` | 로그 본문 (`text` 타입) |
| `SysLogTag` | `systemd[1]:` 처럼 **어떤 프로그램이 남겼는지** |
| `NTSeverity`, `EventID`, `EventLogType` 등 | Windows 이벤트 로그 수집용 컬럼. 리눅스만 쓰면 `NULL` |

> **rsyslog 공식 문서 경고**: *"Be sure to leave the table and field names unmodified, because otherwise you need to customize rsyslogd's default sql template."*
> → **테이블·컬럼 이름을 바꾸지 마세요.** rsyslog가 내장 SQL 템플릿으로 INSERT하기 때문에, 이름이 다르면 템플릿까지 직접 고쳐야 합니다.

### 10-4. MariaDB 기동 — 실습에서 만난 에러

```
[root@server ~]# mysql -u root -p < /usr/share/doc/rsyslog/mysql-createDB.sql
Enter password:
ERROR 2002 (HY000): Can't connect to local MySQL server through socket '/var/lib/mysql/mysql.sock' (2)
```

> ### 에러 2002 해석
> **"소켓 파일을 통해 로컬 MySQL 서버에 연결할 수 없다"** — 뒤의 `(2)`는 "No such file or directory"입니다.
>
> `mysql` 클라이언트는 로컬 접속 시 TCP가 아니라 **유닉스 소켓 파일**(`/var/lib/mysql/mysql.sock`)로 붙습니다. 이 파일은 **서버가 실행 중일 때만 생성**됩니다. 즉 **"DB 서버가 꺼져 있다"**는 뜻입니다.

원인 확인:
```
[root@server ~]# systemctl status mariadb
○ mariadb.service - MariaDB 10.5 database server
     Loaded: loaded (/usr/lib/systemd/system/mariadb.service; disabled; preset:>
     Active: inactive (dead)
```

| 출력 | 의미 |
|---|---|
| `○` (흰 동그라미) | 정지 상태 표시 |
| `Loaded: loaded ... ; disabled` | 유닛 파일은 **있지만**(설치됨) **부팅 자동시작은 꺼짐** |
| `Active: inactive (dead)` | **지금 실행 중이 아님** |

> 9-2절의 `Unit httpd.service could not be found`(**설치 안 됨**)와 여기의 `inactive (dead)`(**설치됐으나 꺼짐**)를 구분하는 것이 트러블슈팅의 기본입니다.

해결:
```bash
systemctl start mariadb
systemctl enable mariadb
```
```
Created symlink /etc/systemd/system/mysql.service → /usr/lib/systemd/system/mariadb.service.
Created symlink /etc/systemd/system/mysqld.service → /usr/lib/systemd/system/mariadb.service.
Created symlink /etc/systemd/system/multi-user.target.wants/mariadb.service → ...
```
> **심볼릭 링크가 3개** 생겼습니다. 앞의 두 개(`mysql.service`, `mysqld.service`)는 **MySQL 이름으로 서비스를 호출해도 MariaDB가 뜨도록** 하는 호환 링크입니다. MariaDB가 MySQL의 포크(fork)이기 때문에 제공하는 배려입니다. 세 번째가 실제 **부팅 자동시작 등록**입니다.

### 10-5. 스키마 적용과 확인

```bash
mysql -u root -p < /usr/share/doc/rsyslog/mysql-createDB.sql
```
> `<` 는 **리다이렉션** — 파일 내용을 명령의 표준입력으로 넣습니다. SQL 파일을 한 번에 실행하는 표준 방법입니다.

```sql
MariaDB [(none)]> show databases;
+--------------------+
| Database           |
+--------------------+
| Syslog             |     ← 방금 생성됨
| information_schema |
| mysql              |
| performance_schema |
+--------------------+

MariaDB [(none)]> use Syslog
Database changed

MariaDB [Syslog]> show tables;
+------------------------+
| Tables_in_Syslog       |
+------------------------+
| SystemEvents           |
| SystemEventsProperties |
+------------------------+
```

| 시스템 DB | 역할 |
|---|---|
| `information_schema` | 모든 DB·테이블·컬럼의 **메타데이터** (읽기 전용 가상 DB) |
| `mysql` | **계정·권한 정보**가 실제로 저장되는 곳 |
| `performance_schema` | 성능 측정용 통계 |

> **`show databases` 다음 줄의 `->`**: 실습 출력에 `show databases` 입력 후 `-> ;`가 보입니다. MariaDB 클라이언트는 **세미콜론이 나올 때까지 명령이 안 끝난 것으로 보고** `->` 프롬프트로 계속 입력을 기다립니다. 세미콜론을 빠뜨렸을 때 나오는 정상 동작입니다. 취소하려면 `\c`를 입력합니다.

```sql
MariaDB [Syslog]> desc SystemEvents;
```

`desc`(= `describe`) 출력 필드 읽기

| 필드 | 의미 |
|---|---|
| `Field` / `Type` | 컬럼명 / 자료형 |
| `Null` | `NO`면 필수 입력, `YES`면 비워도 됨 |
| `Key` | `PRI` = **기본키(Primary Key)** |
| `Default` | 기본값 |
| `Extra` | `auto_increment` = 자동 증가 |

> `ID` 컬럼만 `Null=NO`, `Key=PRI`, `Extra=auto_increment`이고 나머지는 전부 `YES/NULL`입니다. → **ID만 필수이고 나머지는 로그마다 있을 수도 없을 수도 있다**는 설계입니다. 실제로 리눅스 로그에서는 Windows 전용 컬럼들이 전부 `NULL`로 채워집니다.

```sql
MariaDB [Syslog]> select * from SystemEvents;
Empty set (0.001 sec)
```
> 아직 rsyslog가 DB로 쓰기 전이라 **비어 있는 것이 정상**입니다.

### 10-6. 권한 부여 — grant / revoke

메모: **권한 부여 `grant` / 권한 회수 `revoke`**

```sql
grant all privileges on Syslog.* to 'rsyslog'@'localhost' identified by 'password';
Query OK, 0 rows affected (0.001 sec)
```

**문법 해부**

| 조각 | 의미 |
|---|---|
| `grant all privileges` | **모든 권한** 부여 (SELECT, INSERT, UPDATE, DELETE, CREATE …) |
| `on Syslog.*` | **Syslog 데이터베이스의 모든 테이블**에 대해 (`DB이름.테이블이름`) |
| `to 'rsyslog'@'localhost'` | **사용자 `rsyslog`**, **localhost에서 접속할 때만** |
| `identified by 'password'` | 그 계정의 **비밀번호를 `password`로 설정** (계정이 없으면 **생성까지** 함) |

> **`Query OK, 0 rows affected`** — 권한 구문은 데이터 행을 바꾸지 않으므로 `0 rows`가 정상입니다. 에러가 아닙니다.

> ### `'rsyslog'@'localhost'` — 왜 `@localhost`가 중요한가
> MariaDB의 계정은 **"사용자명 + 접속 출발지"** 한 쌍이 하나의 계정입니다.
> - `'rsyslog'@'localhost'` → **서버 자기 자신에서만** 접속 가능
> - `'rsyslog'@'%'` → **어디서든** 접속 가능 (`%`는 와일드카드)
>
> 이번 구성은 rsyslog와 MariaDB가 **같은 서버(81번)에 있으므로** `localhost`가 정확하고 안전한 선택입니다.

**권한 회수(revoke)와 확인**
```sql
revoke all privileges on Syslog.* from 'rsyslog'@'localhost';
show grants for 'rsyslog'@'localhost';
```

> **보안 관점 보강**: rsyslog 공식 문서는 *"It is sufficient to grant it INSERT privileges to the systemevents table, only."* — **INSERT 권한만 주면 충분**하다고 명시합니다. `all privileges`는 실습 편의용이며, 최소 권한 원칙에 따르면 다음이 맞습니다.
> ```sql
> grant insert on Syslog.SystemEvents to 'rsyslog'@'localhost';
> ```
> 이렇게 하면 설정 파일이 유출돼도 로그를 **지우거나 조작할 수는 없습니다.**

### 10-7. rsyslog에 ommysql 연결

`/etc/rsyslog.conf`에 추가한 두 줄:

```
$ModLoad ommysql
*.* :ommysql:127.0.0.1,Syslog,rsyslog,password
```

**형식**: `*.* :ommysql:DB서버,DB이름,사용자,비밀번호`

| 위치 | 값 | 의미 |
|---|---|---|
| 1 | `127.0.0.1` | DB 서버 주소 (로컬) |
| 2 | `Syslog` | 데이터베이스 이름 |
| 3 | `rsyslog` | 접속 계정 |
| 4 | `password` | 비밀번호 |

> **8장의 교훈이 그대로 적용됩니다**: `$ModLoad ommysql`(모듈 로드) + `*.* :ommysql:...`(사용) — **로드와 사용은 한 쌍**입니다. `$ModLoad ommysql`을 빼면 또 3003 에러가 납니다. 그리고 `rsyslog-mysql` 패키지를 설치하지 않았다면 모듈 파일 자체가 없어 로드에 실패합니다.

> ### ⚠️ 비밀번호가 평문으로 들어갑니다
> rsyslog 공식 문서: *"Keep `/etc/rsyslog.conf` readable by root only, since database credentials are stored in plain text."*
> ```bash
> chmod 600 /etc/rsyslog.conf
> ls -l /etc/rsyslog.conf
> ```
> 실습 비밀번호가 문자 그대로 `password`인 점도 실습 한정입니다.

```bash
firewall-cmd --permanent --add-port=3306/tcp
systemctl restart rsyslog
```

> **3306은 MySQL/MariaDB의 기본 포트**입니다. 다만 이번 구성은 rsyslog와 DB가 **같은 서버**이고 `127.0.0.1`로 접속하므로 **방화벽을 열 필요가 실제로는 없습니다.** 방화벽은 외부에서 들어오는 트래픽을 통제하는 것이고, 루프백(127.0.0.1) 통신은 대상이 아니기 때문입니다.
> DB를 다른 서버에 두는 구성이라면 그때 3306을 열어야 합니다. 그 경우에도 전체 개방보다 **출발지를 제한**하는 편이 안전합니다.
> ```bash
> firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address=192.168.16.81/32 port port=3306 protocol=tcp accept'
> ```
>
> 참고: `--permanent`만 하고 `--reload`를 하지 않으면 반영되지 않습니다(7-1절).

### 10-8. DB에 로그가 쌓였는지 확인

```sql
MariaDB [Syslog]> select * from SystemEvents;
```

실습 결과 **10건**이 저장됐습니다. 주요 행:

| ID | ReceivedAt | Facility | Priority | FromHost | SysLogTag | Message |
|---|---|---|---|---|---|---|
| 1 | 2026-08-25 16:05:33 | **3** | **6** | server | `systemd[1]:` | Stopping System Logging Service... |
| 2 | 〃 | **5** | **6** | server | `rsyslogd[2749]:` | exiting on signal 15. |
| 7 | 〃 | **5** | **3** | server | `rsyslogd[4606]:` | invalid or yet-unknown config file command 'InputUDPServerRun' … |
| 8 | 〃 | **5** | **3** | server | `rsyslogd[4606]:` | imudp: module loaded, but no listeners defined … |
| 10 | 〃 | **5** | **5** | server | `rsyslogd[4606]:` | imjournal: journal files changed, reloading... |

> ### 숫자로 저장된 Facility / Priority 읽기
> 6-4절 ④에서 이름(`daemon`, `syslog`, `info`)으로 배운 값이 **DB에는 숫자로 저장**됩니다. syslog 프로토콜이 원래 숫자를 쓰기 때문입니다.
>
> **Facility 숫자**
> | 값 | 이름 |
> |---|---|
> | 3 | **daemon** — systemd 등 시스템 데몬 |
> | 5 | **syslog** — syslog 서비스 자신(rsyslogd) |
>
> **Priority(Severity) 숫자 — 작을수록 심각**
> | 값 | 이름 |
> |---|---|
> | 3 | **err** (오류) |
> | 5 | **notice** |
> | 6 | **info** |
>
> 이 표로 위 결과를 다시 읽으면:
> - ID 1 → `Facility 3`(daemon) + `Priority 6`(info) = **systemd가 남긴 일반 정보**
> - ID 7, 8 → `Facility 5`(syslog) + `Priority 3`(**err**) = **rsyslog 자신이 남긴 오류** ← 8장의 그 에러가 DB에도 그대로 기록됐습니다
> - ID 10 → `Priority 5`(notice)
>
> **중요**: 등급 이름은 값이 클수록 심각해 보이지만(`emerg`가 최상위), **숫자는 반대로 작을수록 심각합니다.** `emerg=0 … debug=7`. 헷갈리기 쉬운 지점입니다.
>
> 그래서 SQL로 "오류 이상만 보기"는 다음과 같이 씁니다:
> ```sql
> select ReceivedAt, FromHost, SysLogTag, Message
>   from SystemEvents where Priority <= 3 order by ID desc;
> ```

> **`FromHost`가 전부 `server`인 이유**: 이 시점에 쌓인 10건은 모두 **서버 자신(81번)이 만든 로그**입니다. 클라이언트에서 온 로그가 들어오면 이 컬럼에 클라이언트 호스트명이 찍혀 **어느 장비의 로그인지 SQL로 구분**할 수 있게 됩니다. 중앙 수집의 진짜 가치가 이 컬럼에 있습니다.

> **메모의 `severity - 심각도`** — Priority와 Severity는 같은 것을 가리키는 두 이름입니다. syslog 표준에서는 **Severity(심각도)** 가 정식 용어이고, 설정 파일과 DB 컬럼에서는 **Priority**라는 이름을 씁니다. 6-4절의 8단계(`debug`~`emerg`)가 바로 이 심각도입니다.

---

## 11. LogAnalyzer — 로그를 웹에서 보기

DB에 쌓인 로그를 SQL 없이 **브라우저에서 검색·통계·차트로 보는 웹 도구**입니다. 제작사는 rsyslog와 같은 Adiscon입니다.

### 11-1. 웹 스택 설치

```bash
dnf install -y httpd php php-mysqli
dnf install -y wget
```

| 패키지 | 역할 |
|---|---|
| `httpd` | **Apache 웹 서버** — LogAnalyzer 페이지를 서비스 |
| `php` | LogAnalyzer가 **PHP로 작성**되어 있음 |
| `php-mysqli` | PHP가 **MariaDB에 접속**하기 위한 확장 (MySQL Improved) |
| `wget` | 파일 다운로드 |

> `php-mysqli`가 없으면 LogAnalyzer 설치 마법사에서 "DB에 연결할 수 없다"는 오류가 납니다. **웹(php) ↔ DB(mariadb)를 잇는 다리**가 이 패키지입니다.

### 11-2. 내려받기와 압축 해제

```bash
wget http://download.adiscon.com/loganalyzer/loganalyzer-4.1.13.tar.gz -P /tmp
ls /tmp
```
> `-P /tmp` = **저장할 디렉터리 지정**(prefix). 지정하지 않으면 현재 디렉터리에 받습니다.
>
> `/tmp`에 보이는 `systemd-private-...` 디렉터리들은 systemd가 서비스별로 만들어 주는 **격리된 임시 공간**입니다(`PrivateTmp` 기능). httpd, mariadb, chronyd 등 각 서비스가 자기만의 `/tmp`를 갖게 해 서로 간섭하지 못하게 합니다. 신경 쓰지 않아도 되는 정상 항목입니다.

**메모: `gz` = 압축 파일**

`.tar.gz` 확장자 해부

| 부분 | 의미 |
|---|---|
| `.tar` | 여러 파일을 **하나로 묶기만** 함 (Tape ARchive). 압축은 아님 |
| `.gz` | **gzip 압축** |
| `.tar.gz` (=`.tgz`) | 묶은 뒤 압축 — 리눅스의 표준 배포 형식 |

```bash
tar -xzvf /tmp/loganalyzer-4.1.13.tar.gz          # 현재 디렉터리에 풀림
tar -xzvf /tmp/loganalyzer-4.1.13.tar.gz -C /tmp  # /tmp 에 풀림
```

`tar` 옵션 해부

| 옵션 | 의미 |
|---|---|
| `-x` | e**x**tract, 풀기 |
| `-z` | g**z**ip 처리 |
| `-v` | **v**erbose, 처리 파일 나열 |
| `-f` | **f**ile, 대상 파일 지정 (**항상 마지막에**) |
| `-C 디렉터리` | 지정한 디렉터리로 이동해서 풀기 |
| `-c` | **c**reate, 묶기 (압축할 때) |
| `-t` | **t**est/list, 내용만 보기 |

> ### 실습에서 일어난 일 — 압축이 엉뚱한 곳에 풀림
> 첫 명령을 `/sambatest` 디렉터리에서 실행했기 때문에 결과가 이랬습니다:
> ```
> [root@server sambatest]# ls
> loganalyzer-4.1.13  movie  music  samba.txt  smb.html
> ```
> **`-C` 없이 풀면 "현재 위치"에 풀립니다.** 오전에 만든 삼바 공유 폴더에 압축이 풀려 버린 것입니다. 그래서 `-C /tmp`를 붙여 다시 실행했습니다.
>
> 습관: 압축을 풀기 전에 `pwd`로 현재 위치를 확인하거나, 항상 `-C`로 목적지를 명시하세요. 내용을 미리 보려면 `tar -tzvf 파일.tar.gz | head` 를 씁니다.

**메모: 리눅스 tab키 = 자동완성**
> 긴 파일명(`loganalyzer-4.1.13.tar.gz`)을 칠 때 `logan` 까지만 입력하고 **Tab**을 누르면 나머지가 자동 완성됩니다. **Tab 두 번**은 가능한 후보를 모두 보여줍니다. 오타를 원천적으로 줄여 주는 습관입니다.

### 11-3. 배포 파일 구조

```bash
ls /tmp/loganalyzer-4.1.13
# COPYING  ChangeLog  INSTALL  contrib  doc  src
```

| 항목 | 내용 |
|---|---|
| `src` | **source** — 실제 웹에 올릴 PHP 소스 (메모: `src = source`) |
| `contrib` | 부가 스크립트 (`configure.sh` 등) |
| `doc` | 설치 문서 |
| `INSTALL` | 설치 안내 텍스트 |
| `COPYING` | 라이선스 |
| `ChangeLog` | 변경 이력 |

> LogAnalyzer 공식 문서 원문: *"Upload all files from the loganalyzer/src/ folder to your webserver. The other files are not needed on the webserver."*
> → **`src` 안의 내용만** 웹 루트에 올리면 됩니다. 나머지는 웹서버에 둘 필요가 없습니다(보안상 두지 않는 편이 낫습니다).

### 11-4. 웹 루트에 배치

```bash
mkdir /var/www/html/loganalyzer
cp -r /tmp/loganalyzer-4.1.13/src/* /var/www/html/loganalyzer
cp /tmp/loganalyzer-4.1.13/contrib/configure.sh /var/www/html/loganalyzer
```

> - `/var/www/html` = **Apache의 기본 문서 루트(DocumentRoot)**. 이 아래에 놓인 파일이 `http://서버주소/경로`로 노출됩니다.
> - 따라서 접속 주소는 **`http://192.168.16.81/loganalyzer`** 가 됩니다.
> - `cp -r` = **r**ecursive, 디렉터리를 통째로 복사. `src/*`는 "src 안의 항목들"이라 `src` 폴더 자체는 만들어지지 않습니다.

> ### 메모에 기록된 오류
> ```
> cp /tmp/loganalyzer-4.1.13/contrib/.sh /var/www/html/loganalyzer
> cp: cannot stat '/tmp/loganalyzer-4.1.13/contrib/.sh': 그런 파일이나 디렉터리가 없습니다
> ```
> `.sh`라는 이름의 파일은 없습니다. **`*.sh`**(와일드카드 `*` 포함)로 쓰거나 파일명을 정확히 지정해야 합니다. 다음 줄에서 `configure.sh`로 정확히 지정해 성공했습니다.
> ```bash
> cp /tmp/loganalyzer-4.1.13/contrib/*.sh /var/www/html/loganalyzer   # 모든 .sh 복사
> ```
> **`cannot stat`** = "그 경로의 정보를 읽을 수 없다" = 대개 **파일이 없거나 경로 오타**라는 뜻입니다.

### 11-5. configure.sh 실행

```bash
cd /var/www/html/loganalyzer/
cat configure.sh
```
```sh
#!/bin/sh

touch config.php
chmod 666 config.php
```

> **딱 두 줄짜리 스크립트**입니다.
> - `touch config.php` — **빈 설정 파일 생성**
> - `chmod 666 config.php` — **모든 사용자에게 읽기+쓰기 허용**
>
> 왜 필요한가? LogAnalyzer의 **설치 마법사(`install.php`)가 브라우저에서 입력받은 DB 정보를 `config.php`에 직접 써야 하기 때문**입니다. 웹서버는 `apache` 사용자로 동작하므로, 그 사용자가 파일에 쓸 수 있어야 합니다.
>
> LogAnalyzer 공식 문서 설명: *"this will create a blank config.php, and will also set write access to everyone to it."*

```bash
bash configure.sh
ls
# config.php 가 생성됨
```

> **`#!/bin/sh`** = **셔뱅(shebang)**. 이 스크립트를 어떤 인터프리터로 실행할지 첫 줄에 지정합니다. 실습에서는 `bash configure.sh`로 bash에 직접 넘겨 실행했습니다. 실행 권한을 준 뒤 `./configure.sh`로 실행할 수도 있습니다.
> ```bash
> chmod +x configure.sh && ./configure.sh
> ```

> ### ⚠️ 666 권한은 설치가 끝나면 되돌려야 합니다
> `chmod 666`은 **누구나 설정 파일을 고칠 수 있는 상태**입니다. 이 파일에는 DB 접속 정보가 들어갑니다. 설치 마법사를 끝낸 뒤에는 권한을 조여야 합니다.
> ```bash
> chmod 644 config.php
> ```
> 배포판이 `configure.sh`와 함께 제공하는 `secure.sh`가 이 뒷정리를 담당합니다.

### 11-6. 남은 단계 — 방화벽과 설치 마법사

실습 마지막 `firewall-cmd --list-all` 결과:
```
  services: cockpit dhcpv6-client dns samba ssh
  ports: 2049/tcp 514/udp 514/tcp
```

> **`http`(80/tcp)가 아직 열려 있지 않습니다.** 이 상태로는 다른 PC의 브라우저에서 `http://192.168.16.81/loganalyzer`에 접속할 수 없습니다. 다음 단계에서 열어야 합니다.
> ```bash
> firewall-cmd --permanent --add-service=http
> firewall-cmd --reload
> systemctl enable --now httpd
> ```
> 그 다음 브라우저에서 접속하면 LogAnalyzer가 **설치 마법사(`install.php`)로 안내**합니다. 공식 문서 원문: *"you will see an error, and you will be pointed to the installation script."* 마법사에서 10장에서 만든 DB 정보(`Syslog` / `rsyslog` / `password`)를 입력하면 연결이 완성됩니다.

**전체 데이터 흐름 정리**

```
[클라이언트 92]  systemd/httpd 이벤트
      │  rsyslog (*.* @@192.168.16.81:514)
      ▼
[서버 81]  rsyslog (imudp/imtcp, 514 수신)
      │
      ├─► omfile  →  /var/log/messages   (텍스트 파일)
      └─► ommysql →  MariaDB : Syslog.SystemEvents   (DB)
                              │
                              ▼
                    LogAnalyzer (httpd + php-mysqli)
                              │
                              ▼
                    브라우저에서 검색·통계·차트
```

---
## 12. 전체 실습 명령 시트 (복습용)

### NFS 서버 (81)
```bash
dnf install -y nfs-utils
mkdir /nfsserver && chmod 755 /nfsserver

cat >> /etc/exports <<'EOF'
/nfsserver 192.168.16.92(rw,sync,no_root_squash)
EOF

exportfs -ra && exportfs -v
systemctl enable --now nfs-server rpcbind

firewall-cmd --permanent --add-service={nfs,rpc-bind,mountd}
firewall-cmd --reload

setsebool -P nfs_export_all_rw on
```

### NFS 클라이언트 (92)
```bash
dnf install -y nfs-utils
mkdir /nfsclient
showmount -e 192.168.16.81                        # NFSv3 경로가 열려 있을 때만
mount -t nfs 192.168.16.81:/nfsserver /nfsclient
df -h && mount | grep nfs                          # 협상된 버전 확인

# 영구 마운트
echo '192.168.16.81:/nfsserver /nfsclient nfs defaults,_netdev 0 0' >> /etc/fstab
mount -a                                           # 재부팅 전 검증

# 해제
cd / && umount /nfsclient
```

### Samba 서버 (81)
```bash
dnf install -y samba samba-common samba-client

mkdir /sambatest && chmod 2770 /sambatest
groupadd smbgroup && chgrp smbgroup /sambatest

useradd -s /sbin/nologin -G smbgroup sambauser
smbpasswd -a sambauser

vi /etc/samba/smb.conf        # [sambashare] 섹션 추가
testparm                       # ★ 문법 검증

firewall-cmd --permanent --add-service=samba && firewall-cmd --reload

semanage fcontext -a -t samba_share_t "/sambatest(/.*)?"
restorecon -Rv /sambatest

systemctl enable --now smb nmb
smbstatus
```

### rsyslog 수집 서버 (81)
```bash
dnf install -y rsyslog rsyslog-doc

vi /etc/rsyslog.conf
# 아래 두 쌍 중 한 가지 문법만 사용 (중복 로드 금지)
#   신형: module(load="imudp")  /  input(type="imudp" port="514")
#         module(load="imtcp")  /  input(type="imtcp" port="514")
#   구형: $ModLoad imudp / $InputUDPServerRun 514
#         $ModLoad imtcp / $InputTCPServerRun 514
#   ★ 모듈 로드 + 리스너 정의는 반드시 한 쌍

rsyslogd -N 1                                    # 재시작 전 문법 검사

firewall-cmd --permanent --add-port=514/udp
firewall-cmd --permanent --add-port=514/tcp
firewall-cmd --reload

systemctl enable --now rsyslog

# 리스닝 확인
dnf install -y net-tools lsof
netstat -natpl | grep 514        # TCP
netstat -naupl | grep 514        # UDP (★ 빠뜨리기 쉬움)
lsof -nP -i :514
tail -f /var/log/messages        # 에러 로그 확인
```

### rsyslog 클라이언트 (92)
```bash
vi /etc/rsyslog.conf
#   *.* @@192.168.16.81:514      ← TCP (@ 두 개)
#   *.* @192.168.16.81:514       ← UDP (@ 한 개)
#   신형: *.* action(type="omfwd" target="192.168.16.81" port="514" protocol="tcp")
#   ★ 둘 다 쓰면 로그가 두 번 전송됨

systemctl enable --now rsyslog

# 로그 발생시켜 시험
systemctl restart httpd
```

### 로그를 MariaDB에 저장 (81)
```bash
dnf install -y mariadb-server rsyslog-mysql
systemctl enable --now mariadb

mysql -u root -p < /usr/share/doc/rsyslog/mysql-createDB.sql
mysql -u root -p
```
```sql
show databases;
use Syslog;
show tables;
desc SystemEvents;
grant all privileges on Syslog.* to 'rsyslog'@'localhost' identified by 'password';
-- 최소 권한 버전:  grant insert on Syslog.SystemEvents to 'rsyslog'@'localhost';
-- 회수:            revoke all privileges on Syslog.* from 'rsyslog'@'localhost';
select * from SystemEvents;
select ReceivedAt, FromHost, SysLogTag, Message from SystemEvents where Priority <= 3;
```
```bash
vi /etc/rsyslog.conf
#   $ModLoad ommysql
#   *.* :ommysql:127.0.0.1,Syslog,rsyslog,password
chmod 600 /etc/rsyslog.conf      # 평문 비밀번호 보호
systemctl restart rsyslog
```

### LogAnalyzer 웹 UI (81)
```bash
dnf install -y httpd php php-mysqli wget tar

wget http://download.adiscon.com/loganalyzer/loganalyzer-4.1.13.tar.gz -P /tmp
tar -xzvf /tmp/loganalyzer-4.1.13.tar.gz -C /tmp      # ★ -C 로 목적지 명시

mkdir /var/www/html/loganalyzer
cp -r /tmp/loganalyzer-4.1.13/src/* /var/www/html/loganalyzer
cp /tmp/loganalyzer-4.1.13/contrib/*.sh /var/www/html/loganalyzer

cd /var/www/html/loganalyzer && bash configure.sh     # config.php 생성 + 666

firewall-cmd --permanent --add-service=http && firewall-cmd --reload
systemctl enable --now httpd
# 브라우저 → http://192.168.16.81/loganalyzer  (설치 마법사)
chmod 644 config.php             # 설치 완료 후 권한 회수
```

### 서비스 상태 점검 (문제 생겼을 때 순서대로)
```bash
systemctl status nfs-server smb nmb     # ① 서비스 살아있나
firewall-cmd --list-all                  # ② 방화벽 열렸나
getenforce && ls -Zd /sambatest          # ③ SELinux 컨텍스트 맞나
testparm                                 # ④ 설정 문법 맞나
ss -tulnp | grep -E '2049|445|139|514|3306|:80'  # ⑤ 실제로 포트 리스닝 중인가
journalctl -u smb -n 50                  # ⑥ 로그 확인
ausearch -m avc -ts recent               # ⑦ SELinux 차단 로그
```

---

## 13. 오늘 메모에서 **수정·보강된 항목** 총정리

| # | 메모 원문 | 수정/보강 내용 | 근거 |
|---|---|---|---|
| 1 | `unmonunt /nfsclient` | **`umount`** — n이 하나 빠진 형태 | 표준 명령 |
| 2 | `smbpasswd -x smabauser` 등 | **`sambauser`** (오타 4곳) | 실습 계정명 |
| 3 | "nmbd => tcp 139, udp 137/138" | **TCP 139는 smbd 담당.** nmbd는 UDP 137/138만. 주력은 **TCP 445** | smbd(8)/nmbd(8) man |
| 4 | "rpc/nfslock/rpcbind 세 가지로 nfs 동작" | NFSv3 기준. **NFSv4는 rpcbind 불필요**(2049 단일 포트). 실제 구성요소는 nfsd, rpc.nfsd, rpc.mountd, rpc.statd, nfsdcld, rpcbind | RHEL 9 문서 |
| 5 | "secure — 1024포트 이상 이하" | `secure`=클라이언트 소스 포트 **1024 미만**만 허용(기본), `insecure`=1024 이상 허용. 이유는 특권 포트는 root만 바인딩 가능하기 때문 | exports(5) |
| 6 | `chmod 756 /nfsserver` | 기타 사용자에 `x` 없어 **디렉터리 진입 불가**. root+no_root_squash라 문제가 안 드러난 것. `755`/`1777`/`2775` 권장 | 권한 원리 |
| 7 | `[homes] -> 공유폴더 이름` | 일반 공유가 아닌 **Samba 예약 섹션**. 접속 사용자의 홈을 자동 공유. `%S`=사용자명 치환 | smb.conf(5) |
| 8 | `[sambashare]`에 `writeable`+`read only` 동시 사용 | **완전히 동일한 파라미터의 중복.** 하나만 사용 (testparm이 하나로 정규화) | smb.conf(5) |
| 9 | `create mask = 0777` | 권한 "부여"가 아니라 **상한(마스크)**. 강제 부여는 `force create mode` | smb.conf(5) |
| 10 | `null passwords = yes` | `smbpasswd -n`과 짝. 단 **deprecated 상태**로 경고 로그 발생. 운영 금지 | Samba Bugzilla #10065 |
| 11 | `hostname server` (마지막 줄) | **임시(transient) 설정.** 영구는 `hostnamectl set-hostname` | hostnamectl(1) |
| 12 | SELinux `disabled` 처리 | 실무에서는 끄지 말고 **`semanage fcontext -a -t samba_share_t` + `restorecon`** 또는 `setsebool -P`로 해결 | Fedora SELinux 위키 |
| 13 | (누락) `/etc/exports` 공백 문법 | IP와 `(rw)` 사이 공백 하나로 **전 호스트에 rw 개방** — 심각한 사고 유형 | RHEL 9 문서 |
| 14 | (누락) 영구 마운트 | `mount`는 재부팅 시 소실. `/etc/fstab` + `_netdev` 필요 | RHEL 9 문서 |
| 15 | (누락) `showmount` 한계 | NFSv4-only 서버에서는 동작하지 않음(mountd 질의) | Red Hat KB |
| 16 | (누락) VM 복제 시 machine-id | 92번이 복제본이므로 `machine-id` 재생성 필요 | systemd 원리 |
| 17 | `im: input module` / `om: output module` | 맞음 ✅ + 실제 등장 모듈(imuxsock, imjournal, imudp, imtcp, imklog, immark / omfile, omusrmsg, omfwd) 역할 표로 보강 | rsyslog 문서 |
| 18 | "514번 포트: rsyslog의 기본 포트" | 맞음 ✅ + **UDP 514와 TCP 514 둘 다** 사용하며 신뢰성 차이가 있다는 점 보강 | rsyslog.conf(5) |
| 19 | 설정 파일의 `$ModLoad`와 `module(load=...)` 병존 | **같은 기능의 구형(legacy) / 신형(RainerScript) 문법.** 둘 중 하나만 써야 하며 중복 로드 시 rsyslog 기동 실패 | rsyslog.conf(5) |
| 20 | `*.info;mail.none;...` 규칙 | `*.info`는 info **"이상 전부"**. `none` = 해당 시설 완전 제외. `=`/`!` 연산자 보강 | rsyslog.conf(5) |
| 21 | `rsyslog server <-> rsyslog client` | 별개 프로그램이 아니라 **같은 `rsyslogd`가 설정(im/om)에 따라 두 역할을 겸함** | 구조 설명 |
| 22 | `tail -f / var/log/messages` | 슬래시 뒤 **공백 제거** → `tail -f /var/log/messages` | 경로 문법 |
| 23 | `tail -n -f /var/log/messages` | `-n`은 숫자 인자를 요구 → `tail -f` 또는 `tail -n 20` | tail(1) |
| 24 | `tail -f var/log/message` | 앞 `/` 누락 + 파일명 **`messages`**(복수) | 경로/파일명 |
| 25 | `netstat -natpl grep 514` | **파이프 `\|` 누락** → `netstat -natpl \| grep 514` | 셸 문법 |
| 26 | `lsof -i tcp:514` 결과의 `*:shell` | 오류 아님. **514/tcp가 `/etc/services`에 `shell`(rsh)로 등록**되어 이름이 변환된 것. `lsof -nP`로 숫자 표시 | /etc/services |
| 27 | (실습 에러) `invalid or yet-unknown config file command 'InputUDPServerRun'` | **에러 3003.** `$ModLoad imudp` 누락 → 모듈이 제공하는 명령을 rsyslog가 모름. **모듈 로드 + 리스너 정의는 한 쌍** | rsyslog 공식 3003 |
| 28 | (실습 에러) `imudp: module loaded, but no listeners defined` | 에러 2212. 모듈은 떴지만 리스너 미정의 → **UDP 수신 실질 정지**. TCP만 LISTEN 되어 정상으로 오판하기 쉬움 | rsyslog 진단 |
| 29 | (누락) 재시작 전 문법 검사 | **`rsyslogd -N 1`** — Samba의 `testparm`에 해당. 3003을 미리 잡음 | RHEL 9 문서 |
| 30 | `*.* @@IP:514` / `*.* @IP:514` | **`@@`=TCP, `@`=UDP.** 둘 다 쓰면 **같은 로그가 두 번 전송**됨. 공식 문서는 레거시 표기 대신 `action(type="omfwd" ...)` 권장 | rsyslog 공식 |
| 31 | `cp .../contrib/.sh ...` → `cannot stat` | `.sh`라는 파일은 없음. **`*.sh`** 와일드카드 또는 정확한 파일명 필요 | 셸 문법 |
| 32 | `tar -xzvf ...` (`-C` 없이) | 압축이 **현재 디렉터리(`/sambatest`)에 풀림.** `-C /tmp`로 목적지 명시 필요 | tar(1) |
| 33 | `firewall-cmd --permanent --add-port=3306/tcp` | rsyslog와 DB가 **같은 서버 + `127.0.0.1` 접속**이므로 실제로는 불필요. 또한 `--reload` 없이는 미반영 | firewalld 원리 |
| 34 | `grant all privileges on Syslog.*` | 동작하지만 과도. 공식 문서는 **`INSERT` 권한만으로 충분**하다고 명시 (최소 권한 원칙) | rsyslog DB 문서 |
| 35 | `*.* :ommysql:...,password` | 비밀번호가 **평문 저장**. 공식 문서는 `/etc/rsyslog.conf`를 **root 전용(600)** 으로 두라고 경고 | rsyslog DB 문서 |
| 36 | DB의 `Facility`/`Priority` 숫자 | 이름이 아닌 **숫자로 저장**. 3=daemon, 5=syslog / 3=err, 5=notice, 6=info. **숫자는 작을수록 심각**(emerg=0) | syslog 표준 |
| 37 | `severity - 심각도` | Priority와 Severity는 **같은 것의 두 이름**. 표준 용어는 Severity, 설정/DB 컬럼명은 Priority | syslog 표준 |
| 38 | `chmod 666 config.php` | 설치 마법사가 쓰기 위해 필요하지만, **설치 후 `chmod 644`로 회수**해야 함(배포판의 `secure.sh` 역할) | LogAnalyzer 문서 |
| 39 | (누락) LogAnalyzer 접속용 방화벽 | 실습 종료 시점에 **`http`(80/tcp)가 아직 열려 있지 않음** → 브라우저 접속 불가 | 실습 출력 |

---

## 14. 출처

### NFS
- [Chapter 2. Deploying an NFS server — RHEL 9 Documentation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_and_using_network_file_services/deploying-an-nfs-server_configuring-and-using-network-file-services)
- [Chapter 4. Mounting NFS shares — RHEL 9 Documentation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_file_systems/mounting-nfs-shares_managing-file-systems)
- [How can I disable rpcbind on NFSv4-only servers? — Red Hat Customer Portal](https://access.redhat.com/solutions/902013)
- [Why does the "showmount" command not work…? — Red Hat Customer Portal](https://access.redhat.com/solutions/6968851)
- [Chapter 7. Securing network services — RHEL 9 Documentation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/securing_networks/securing-network-services_securing-networks)

### Samba
- [smbd(8) man page — samba.org](https://www.samba.org/samba/docs/current/man-html/smbd.8.html)
- [nmbd(8) man page — samba.org](https://www.samba.org/samba/docs/current/man-html/nmbd.8.html)
- [smbpasswd(8) man page — samba.org](https://www.samba.org/samba/docs/current/man-html/smbpasswd.8.html)
- [Samba 4.23.0 Release Notes](https://www.samba.org/samba/history/samba-4.23.0.html)
- [Samba 4.23 Features added/changed — SambaWiki](https://wiki.samba.org/index.php/Samba_4.23_Features_added/changed)
- [Bug 10065 — The "null passwords" option is deprecated](https://bugzilla.samba.org/show_bug.cgi?id=10065)
- [Firewalling Samba — samba.org](https://www.samba.org/~tpot/articles/firewall.html)
- [SMB port number: Ports 445, 139, 138, and 137 explained — 4sysops](https://4sysops.com/archives/smb-port-number-ports-445-139-138-and-137-explained/)

### SELinux
- [Chapter 2. Changing SELinux states and modes — RHEL 9 Documentation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/using_selinux/changing-selinux-states-and-modes_using-selinux)
- [SELinux/samba — Fedora Project Wiki](https://fedoraproject.org/wiki/SELinux/samba)
- [samba_selinux(8) man page](https://linux.die.net/man/8/samba_selinux)
- [How do I turn SELinux off in RHEL? — Red Hat Customer Portal](https://access.redhat.com/solutions/3176)

### rsyslog
- [rsyslog.conf(5) — Linux manual page (man7.org)](https://man7.org/linux/man-pages/man5/rsyslog.conf.5.html)
- [Log management — Rocky Linux 9 Admin Guide](https://docs.rockylinux.org/9/books/admin_guide/17-log/)
- [imudp: UDP Syslog Input Module — rsyslog documentation](https://docs.rsyslog.com/doc/configuration/modules/imudp.html)
- [imtcp: TCP Syslog Input Module — rsyslog documentation](https://docs.rsyslog.com/doc/configuration/modules/imtcp.html)
- [rsyslog error 3003 — rsyslog.com](https://www.rsyslog.com/rsyslog-error-3003/)
- [Sending Messages to a Remote Syslog Server — rsyslog.com](https://www.rsyslog.com/sending-messages-to-a-remote-syslog-server/)
- [Chapter 15. Configuring a remote logging solution — RHEL 9 Security hardening](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/security_hardening/assembly_configuring-a-remote-logging-solution_security-hardening)
- [Writing syslog messages to MySQL/PostgreSQL — rsyslog documentation](https://rsyslog-doc-v5.readthedocs.io/en/latest/tutorials/database.html)

### MariaDB / LogAnalyzer
- [GRANT — MariaDB Documentation](https://mariadb.com/docs/server/reference/sql-statements/account-management-sql-statements/grant)
- [Installation — Adiscon LogAnalyzer 공식 문서](https://doc.loganalyzer.adiscon.com/user-guide/chapters/install/)
- [Adiscon LogAnalyzer 다운로드](https://loganalyzer.adiscon.com/downloads)
