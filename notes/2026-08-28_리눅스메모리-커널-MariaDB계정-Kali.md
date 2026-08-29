# 2026-08-28 학습 노트 — 리눅스 메모리·커널 파라미터(`free`/`sysctl`/`/proc`) · MariaDB 계정·권한 관리 · Kali Linux 초기 설정

> **실습 환경**
>
> | 항목 | 값 | 근거 (실습 출력) |
> |---|---|---|
> | 서버 호스트명 | `userver` | `kernel.hostname = userver` |
> | OS | Ubuntu 24.04 LTS | `Ubuntu 13.3.0-6ubuntu2~24.04.1`, `#138-Ubuntu` |
> | 커널 | `6.8.0-138-generic` (x86_64) | `kernel.osrelease`, `/proc/version` |
> | 커널 빌드일 | 2026-07-31 | `#138-Ubuntu SMP PREEMPT_DYNAMIC Fri Jul 31 22:41:49 UTC 2026` |
> | CPU | Intel Core i7-8700 @ 3.20GHz, **VM에 1코어 할당** | `cpu cores : 1`, `flags`에 `hypervisor` |
> | RAM / Swap | 약 1.9 GiB / 약 1.9 GiB | `free -m` = 1968 / 1986 |
> | 루트 파일시스템 | LVM (`/dev/mapper/ubuntu--vg-ubuntu--lv`) **사용률 96%** | `df` |
> | DB | MariaDB **10.11.14** (Ubuntu 24.04 패키지) | `Server version: 10.11.14-MariaDB-0ubuntu0.24.04.1` |
> | 컨테이너 | Docker 실행 중 | `docker0`, `br-bc099e94d7ca`, `veth6ca8f1c` 인터페이스 존재 |
> | 모니터링 | PMM 계정 잔존 | `mysql.user`에 `pmm@localhost` |
> | 공격자 VM | Kali Linux (`kali@kali-Attacker`), 기본 셸 zsh | 프롬프트 `┌──(kali㉿kali-Attacker)-[~]` |
>
> 이 노트의 기술적 사실은 커널 공식 문서(docs.kernel.org), man7.org man 페이지, MariaDB 공식 문서, Debian/Kali 공식 자료로 **재검증한 뒤** 작성했습니다. 검증하지 못한 항목은 11절에 따로 적었습니다.

---

## 0. 오늘의 큰 그림

오늘 수업은 겉보기에 세 덩어리지만, **"시스템 상태를 어디서 읽고, 어디를 고치고, 그 변경이 얼마나 오래 사는가"** 라는 하나의 질문으로 꿰어집니다.

| 블록 | 다룬 것 | 핵심 질문 | 오늘의 답 |
|---|---|---|---|
| ① 메모리·커널 | `free`, `sysctl`, `/proc/meminfo`, `/proc/version`, `/proc/cpuinfo`, `df` | 커널 상태를 **어디서 읽나** | `/proc` 가상 파일시스템. `free`도 결국 `/proc/meminfo`를 읽어 계산한 것 |
| ② 커널 튜닝 | `sysctl -a`, `sysctl -w vm.swappiness=40` | 커널 동작을 **어떻게 바꾸나**, 그 변경은 **살아남나** | `/proc/sys`에 써서 즉시 반영. **재부팅하면 사라짐** → `/etc/sysctl.d/`에 적어야 영구 |
| ③ MariaDB 계정 | `CREATE USER`, `DROP USER`, `GRANT`, `REVOKE`, `SHOW GRANTS` | DB에서 **"누가"는 무엇으로 결정되나** | **`사용자@호스트` 쌍 전체가 하나의 계정**. 이름만 같아도 서로 다른 계정 |
| ④ Kali 초기 설정 | 프롬프트, `ifconfig`/`ip ad`, apt lock, Chrome 설치, 한글 입력, `ping` | 새 시스템을 **쓸 수 있는 상태로 만드는 절차** | 네트워크 확인 → 패키지 갱신 → 필요한 소프트웨어 설치 |

### 오늘 반복해서 나온 공통 패턴 3가지

1. **"읽기 전용 상태 파일"과 "쓰기 가능한 설정 파일"은 다른 곳에 있다.**
   `/proc/meminfo`·`/proc/cpuinfo`는 읽기 전용 상태 스냅샷, `/proc/sys/*`는 쓰면 커널 동작이 바뀌는 설정 손잡이입니다. 같은 `/proc` 아래 있지만 성격이 정반대입니다.

2. **런타임 변경은 휘발성이다.**
   `sysctl -w`도, 메모리 상에 올라간 MariaDB 권한 캐시도 마찬가지입니다. 영속화 위치(`/etc/sysctl.d/`, `mysql.global_priv` 테이블)를 항상 같이 기억해야 합니다.

3. **"이름"만으로 대상을 지정하면 기본값이 몰래 끼어든다.**
   `DROP USER test`가 실제로 지운 것은 `test@'%'` 였습니다. 호스트를 생략하면 `'%'`가 자동으로 붙기 때문입니다. 오늘 실습 출력이 이 사실을 그대로 보여줬습니다.

---

## 1. `free` — 메모리 현황 읽기

### 1-1. 실습 출력

```bash
happy@userver:~$ sudo free -m
               total        used        free      shared  buff/cache   available
Mem:            1968        1045          94          37        1045         922
Swap:           1986         208        1778
```

### 1-2. 열별 정확한 정의 (man 1 free 기준)

| 열 | 정의 | `/proc/meminfo` 대응 |
|---|---|---|
| `total` | 사용 가능한 전체 메모리 | `MemTotal` / `SwapTotal` |
| `used` | **`total - available`** 로 계산된 값 | (계산값) |
| `free` | 아무도 안 쓰는 완전히 빈 메모리 | `MemFree` / `SwapFree` |
| `shared` | 주로 tmpfs가 쓰는 공유 메모리 | `Shmem` |
| `buff/cache` | 버퍼 + 페이지 캐시 + 회수 가능 슬랩의 합 | `Buffers` + `Cached` + `SReclaimable` |
| `available` | **스왑 없이 새 프로그램에 내줄 수 있다고 커널이 추정한 양** | `MemAvailable` |

> ### ⚠️ `free`가 94 MB인데 왜 "메모리 부족"이 아닌가
>
> 이 표에서 가장 많이 오해되는 지점입니다.
>
> - `free`(94 MB)는 **놀고 있는 메모리**입니다. 리눅스는 남는 RAM을 전부 디스크 캐시로 채우는 것이 정상 설계이므로, `free`가 작은 것은 **건강한 상태**입니다.
> - 실제로 봐야 하는 값은 **`available`(922 MB)** 입니다. 캐시(1045 MB) 중 상당량은 필요하면 즉시 회수되므로, 지금 새 프로그램에 약 922 MB를 줄 수 있다는 뜻입니다.
> - `used`가 `total - available`로 계산된다는 점도 중요합니다. 즉 `used`는 "프로세스가 잡아먹은 양"이 아니라 **"내줄 수 없는 양"** 에 가깝습니다.
>
> 정리하면 **`free` 열이 아니라 `available` 열로 판단합니다.**

### 1-3. 실제 숫자 검산

`total(1968) - available(922) = 1046 ≈ used(1045)` — 반올림 오차 범위 안에서 정확히 맞습니다. 이 검산이 맞아떨어지는지 보는 것만으로 열의 의미를 확인할 수 있습니다.

Swap 쪽 `used = 208 MB`는 "지금 메모리가 부족하다"는 뜻이 아닙니다. **과거 어느 시점에 밀려나간 페이지가 아직 스왑에 남아 있는 것**이며, `/proc/meminfo`의 `SwapCached: 13512 kB`가 그중 일부는 이미 RAM으로 돌아왔지만 스왑 사본도 유지 중임을 보여줍니다(다시 밀어낼 때 쓰기를 생략할 수 있어 이득).

### 1-4. `free -g`가 쓸모없었던 이유 (메모 수정 포인트 ①)

```bash
happy@userver:~$ sudo free -g
               total        used        free      shared  buff/cache   available
Mem:               1           1           0           0           1           0
Swap:              1           0           1
```

`available`이 **0**으로 나옵니다. 922 MB는 1 GiB 미만이라 정수 GiB 단위에서 잘려나간 것입니다. 메모리가 2 GiB인 장비에서 `-g`는 정보를 전부 파괴합니다.

| 옵션 | 언제 쓰나 |
|---|---|
| `-m` (MiB) | 수 GB급 서버의 기본 선택 |
| `-h` | 사람이 읽기 좋게 자동 단위 (`Mi`, `Gi`) — **가장 무난** |
| `-g` (GiB) | 수십~수백 GB 장비에서만 의미 있음 |
| `-s N` | N초 간격 반복 출력 (추세 관찰) |
| `-t` | 합계(Mem+Swap) 행 추가 |
| `-w` | buffers와 cache를 분리 표시 |

> **`sudo`는 필요 없습니다.** `free`는 `/proc/meminfo`를 읽을 뿐이고 이 파일은 모든 사용자에게 읽기 권한이 있습니다. 습관적으로 `sudo`를 붙이면, 정말로 권한이 필요한 명령과 구분이 흐려집니다.

---

## 2. `sysctl` — 커널 파라미터 확인과 변경

### 2-1. 인자 없이 실행하면 사용법이 나온다

```bash
happy@userver:~$ sudo sysctl
Usage:
 sysctl [options] [variable[=value] ...]
```

메모에는 `=> 커널에 있는 다양한 값들 확인하는 명령어`라고 적혀 있습니다. **절반만 맞습니다** (메모 수정 포인트 ②).
`sysctl`은 **확인(read) + 변경(write)** 을 모두 하는 명령입니다. `sysctl -w`가 변경이고, 오늘 실습에서도 `vm.swappiness`를 실제로 바꿨습니다.

### 2-2. sysctl의 정체 — `/proc/sys`의 얇은 껍데기

`sysctl`이 다루는 모든 값은 **`/proc/sys/` 아래의 파일**입니다. 변수 이름의 점(`.`)이 디렉터리 구분자(`/`)에 대응합니다.

```
vm.swappiness      ↔  /proc/sys/vm/swappiness
net.ipv4.ip_forward ↔  /proc/sys/net/ipv4/ip_forward
kernel.hostname    ↔  /proc/sys/kernel/hostname
```

따라서 아래 세 줄은 **완전히 같은 일**을 합니다.

```bash
sudo sysctl -w vm.swappiness=40
echo 40 | sudo tee /proc/sys/vm/swappiness
sudo sysctl vm.swappiness=40          # -w 없이 대입만 해도 동작
```

### 2-3. 주요 옵션 (man 8 sysctl 기준)

| 옵션 | 의미 | 비고 |
|---|---|---|
| `-a`, `--all` | 사용 가능한 모든 파라미터 출력 | **deprecated·금지 파라미터는 제외** |
| `--deprecated` | `-a`에 deprecated 항목까지 포함 | |
| `-w`, `--write` | 모든 인자를 쓰기로 강제하고, 파싱 실패 시 에러 | |
| `-p[FILE]`, `--load` | 파일에서 설정 읽어 적용. 파일 생략 시 `/etc/sysctl.conf` | |
| `--system` | **모든 시스템 설정 디렉터리**에서 읽어 적용 | 부팅 시 systemd가 하는 일과 동일 |
| `-n`, `--values` | 키 이름 없이 값만 출력 | 스크립트에서 유용 |
| `-N`, `--names` | 값 없이 키 이름만 출력 | |
| `-r <정규식>` | 확장 정규식과 일치하는 항목만 | `grep` 대신 쓸 수 있음 |
| `-e`, `--ignore` | 모르는 변수 에러 무시 | 배포용 스크립트에 유용 |
| `--dry-run` | 키·값을 출력만 하고 **쓰지 않음** | 적용 전 확인 |
| `-b`, `--binary` | 개행 없이 값 출력 | |

> `-A`, `-X`는 `-a`의 별칭이고, `-d`는 `-h`의 별칭입니다. `-o`, `-x`는 **아무 일도 하지 않습니다**(하위 호환용 더미). 실습 출력의 `does nothing`이 그 뜻입니다.

### 2-4. `sysctl -a` 출력을 분류해서 읽기

출력이 수천 줄이므로 **최상위 네임스페이스(접두어)** 단위로 감을 잡는 것이 요령입니다.

| 접두어 | 영역 | 오늘 출력에서 눈에 띈 값 |
|---|---|---|
| `abi.*` | 바이너리 호환성 | `abi.vsyscall32 = 1` |
| `debug.*` | 디버깅 | `debug.exception-trace = 1` |
| `dev.*` | 장치별 설정 | `dev.cdrom.info`(CD-ROM 능력 목록), `dev.raid.speed_limit_*` |
| `fs.*` | 파일시스템·파일 디스크립터 | `fs.file-max`, `fs.inotify.max_user_watches = 14720` |
| `kernel.*` | 커널 코어 | `kernel.hostname = userver`, `kernel.pid_max = 4194304`, `kernel.threads-max = 15095` |
| `net.*` | 네트워크 스택 | `net.ipv4.ip_forward = 1`, `net.core.somaxconn = 4096` |
| `vm.*` | 가상 메모리 | `vm.swappiness`, `vm.overcommit_memory`, `vm.dirty_ratio` |
| `user.*` / `fs.quota.*` | 네임스페이스 한계, 쿼터 통계 | |

#### `kernel.*` 중 오늘 출력에서 실무상 의미 있는 값

| 키 | 값 | 의미 |
|---|---|---|
| `kernel.hostname` | `userver` | `hostnamectl set-hostname`이 결국 이 값을 바꿉니다 |
| `kernel.osrelease` | `6.8.0-138-generic` | `uname -r`의 원천 |
| `kernel.pid_max` | `4194304` | PID 최댓값. 이 값을 넘으면 1부터 순환 |
| `kernel.threads-max` | `15095` | 시스템 전체 스레드 상한. **RAM이 작아서 낮게 잡힌 값** |
| `kernel.randomize_va_space` | `2` | ASLR 최대 강도(스택·힙·mmap·브k 모두 랜덤화). 보안 기본값 |
| `kernel.dmesg_restrict` | `1` | 비특권 사용자의 `dmesg` 열람 차단 |
| `kernel.kptr_restrict` | `1` | 커널 포인터 주소 노출 제한 |
| `kernel.yama.ptrace_scope` | `1` | 부모-자식 관계가 아닌 프로세스 추적(ptrace) 금지 |
| `kernel.unprivileged_bpf_disabled` | `2` | 비특권 BPF 금지 |
| `kernel.core_pattern` | `\|/usr/share/apport/...` | 코어 덤프를 파일이 아니라 **Ubuntu의 apport 프로그램에 파이프**로 넘김 |
| `kernel.sysrq` | `176` | 매직 SysRq 키 중 일부만 허용(비트마스크) |
| `kernel.panic` | `0` | 패닉 후 **자동 재부팅 안 함**(0=무한 대기). 서버라면 `10`(10초 후 재부팅)을 흔히 씀 |

#### `net.*` 중 오늘 출력에서 의미 있는 값

| 키 | 값 | 의미 |
|---|---|---|
| `net.ipv4.ip_forward` | `1` | **IP 포워딩 켜짐.** Docker가 켠 것입니다(컨테이너 NAT에 필요) |
| `net.ipv4.conf.all.rp_filter` | `2` | 역경로 필터 **느슨한 모드**. 비대칭 라우팅 허용 |
| `net.ipv4.tcp_syncookies` | `1` | SYN 플러딩 방어 |
| `net.ipv4.ip_local_port_range` | `32768 60999` | 클라이언트 소켓이 쓰는 임시 포트 범위(약 28,000개) |
| `net.ipv4.tcp_fin_timeout` | `60` | FIN_WAIT2 대기 시간(초) |
| `net.ipv4.tcp_keepalive_time` | `7200` | 유휴 2시간 후 keepalive 시작 |
| `net.ipv4.tcp_congestion_control` | `cubic` | 혼잡 제어 알고리즘 |
| `net.core.default_qdisc` | `fq_codel` | 기본 큐잉 규율 |
| `net.core.somaxconn` | `4096` | listen 백로그 상한 |
| `net.ipv4.icmp_echo_ignore_all` | `0` | **ping 응답함.** 1로 바꾸면 ping 무응답 |

> 인터페이스 목록이 그대로 드러납니다: `lo`, `enp0s3`(실 NIC), `docker0`(도커 기본 브리지), `br-bc099e94d7ca`(사용자 정의 도커 네트워크), `veth6ca8f1c`(컨테이너 한쪽 끝). **`sysctl -a`만 봐도 이 서버에 Docker가 돌고 컨테이너가 최소 1개 붙어 있다**는 것을 알 수 있습니다.

### 2-5. `vm.*` — 오늘의 주인공

실습에서 나온 `vm.*` 전체 중 시험·실무에서 반복해서 나오는 것만 정리합니다.

| 키 | 이 서버 값 | 커널 문서 기준 의미 |
|---|---|---|
| `vm.swappiness` | 60 → 40 | 스왑과 파일 캐시 회수 중 **어느 쪽에 더 압력을 줄지의 비율**. 범위 **0~200**, 기본 **60** |
| `vm.overcommit_memory` | `0` | 0 = 휴리스틱(명백한 과할당만 거부), 1 = 무조건 허용, 2 = 절대 오버커밋 금지 |
| `vm.overcommit_ratio` | `50` | 모드 2일 때 "swap + RAM의 이 %"까지만 커밋 허용 |
| `vm.dirty_ratio` | `20` | 더티 페이지가 이 %를 넘으면 **쓰는 프로세스가 직접** 플러시(멈춤 발생) |
| `vm.dirty_background_ratio` | `10` | 이 %를 넘으면 커널 플러시 스레드가 **백그라운드로** 기록 시작 |
| `vm.dirty_expire_centisecs` | `3000` | 30초 지난 더티 페이지는 기록 대상 |
| `vm.dirty_writeback_centisecs` | `500` | 5초마다 플러시 스레드 깨어남 |
| `vm.min_free_kbytes` | `45056` | 항상 비워둘 최소 메모리(약 44 MiB). **1024 KB 미만으로 낮추면 시스템이 교착에 빠질 수 있다**고 커널 문서가 경고 |
| `vm.vfs_cache_pressure` | `100` | dentry/inode 캐시 회수 성향. 100이 기준값, 낮추면 캐시 오래 유지 |
| `vm.page-cluster` | `3` | 스왑 인 시 한 번에 읽는 페이지 수의 **로그값** → 2³ = **8페이지**. 0이면 1페이지 |
| `vm.panic_on_oom` | `0` | 0 = OOM 킬러가 프로세스를 죽임, 1 = 커널 패닉, 2 = cgroup OOM에도 강제 패닉 |
| `vm.oom_kill_allocating_task` | `0` | 0 = 휴리스틱으로 희생자 선정, 1 = **할당을 요청한 그 프로세스**를 죽임 |
| `vm.watermark_scale_factor` | `10` | kswapd가 깨고 자는 워터마크 간격. 10 = 가용 메모리의 0.1%, 최대 3000 |
| `vm.max_map_count` | `1048576` | 프로세스당 메모리 맵 최대 개수. Elasticsearch 등이 상향을 요구하는 값 |
| `vm.zone_reclaim_mode` | `0` | NUMA 지역 회수 비활성(단일 노드라 무의미) |

### 2-6. `vm.swappiness` 실습 — 변경과 그 수명

```bash
happy@userver:~$ sudo sysctl -a | grep swap
vm.swappiness = 60
happy@userver:~$ sudo sysctl -w vm.swappiness=40
vm.swappiness = 40
happy@userver:~$ sudo sysctl -a | grep swap
vm.swappiness = 40
```

#### swappiness 값의 실제 의미 (커널 공식 문서)

흔히 "스왑을 얼마나 적극적으로 쓰는지의 백분율"로 설명되지만, 정확한 정의는 다릅니다.

> 커널 문서 원문 요지: swappiness는 **스왑 I/O와 파일시스템 페이징 I/O의 상대적 비용 비율**을 제어합니다. **100**이면 두 경로에 **같은 압력**을 가하고, 낮으면 페이지 캐시를 유지(=익명 페이지 스왑을 덜)하며, 높으면 스왑을 더 씁니다. **0**이면 "해당 존의 free + 파일 기반 페이지가 high watermark 아래로 내려가기 전까지는 스왑을 시작하지 않습니다."

| 값 | 동작 경향 | 쓰는 곳 |
|---|---|---|
| `0` | 거의 스왑 안 함 (완전히 금지는 아님 — OOM 직전에는 씁니다) | 예전 DB 서버 관행 |
| `1` | 최소한만 스왑 | 지연에 민감한 DB/캐시 서버 |
| `10` | 스왑 억제 | 일반적인 DB 튜닝 값 |
| `60` | **커널 기본값** | 데스크톱·범용 서버 |
| `100` | 스왑과 캐시에 동일 압력 | |
| `~200` | 스왑 매우 적극적 | 컨테이너 밀집 등 특수 상황 |

> ⚠️ **"swappiness=0이면 스왑을 안 쓴다"는 흔한 오해입니다.** 0은 "가능한 마지막까지 미룬다"이지 금지가 아닙니다. 진짜로 끄려면 `swapoff -a` + `/etc/fstab`에서 swap 항목 제거이며, 그 경우 메모리 압박 시 **OOM 킬러가 바로 발동**합니다.

#### (메모 보강) 이 변경은 재부팅하면 사라집니다 — 영구 적용법

이 부분이 메모에서 완전히 빠져 있습니다 (메모 보강 포인트 ③). `sysctl -w`는 `/proc/sys`에 쓰는 것이고 `/proc`은 **메모리 위에만 존재하는 가상 파일시스템**이므로 부팅과 함께 초기화됩니다.

```bash
# 1) 설정 파일로 남긴다 (파일명 숫자가 클수록 나중에 적용 = 우선)
echo 'vm.swappiness = 40' | sudo tee /etc/sysctl.d/99-swappiness.conf

# 2) 재부팅 없이 즉시 반영
sudo sysctl --system            # 모든 시스템 디렉터리 재적용
# 또는
sudo sysctl -p /etc/sysctl.d/99-swappiness.conf   # 그 파일만

# 3) 확인
sysctl vm.swappiness
```

`--system`의 **읽는 순서**는 man 페이지에 명시되어 있습니다.

| 순서 | 경로 | 비고 |
|---|---|---|
| 1 | `/etc/sysctl.d/*.conf` | 관리자 설정 |
| 2 | `/run/sysctl.d/*.conf` | 런타임 생성 |
| 3 | `/usr/local/lib/sysctl.d/*.conf` | |
| 4 | `/usr/lib/sysctl.d/*.conf` | 패키지 제공 |
| 5 | `/lib/sysctl.d/*.conf` | |
| 6 | `/etc/sysctl.conf` | **마지막에 적용 → 최종 승자** |

- 각 디렉터리 안에서는 **파일명 사전순**으로 적용되므로 `10-…`보다 `99-…`가 나중에, 즉 더 강하게 적용됩니다.
- **같은 이름의 파일**이 여러 디렉터리에 있으면 **먼저 읽힌 것만** 쓰이고 이후 디렉터리의 동명 파일은 무시됩니다. 이 규칙을 이용해 `/etc/sysctl.d/`에 같은 이름의 빈 파일을 두어 패키지 설정을 **무력화**할 수 있습니다.

#### (메모 수정 포인트 ④) `grep swap`은 스왑 설정 전체가 아니다

```bash
sudo sysctl -a | grep swap      # → vm.swappiness 한 줄만 나옴
```

`vm.page-cluster`(스왑 인 단위), `vm.vfs_cache_pressure`, `/proc/swaps`의 실제 스왑 장치는 이 grep에 걸리지 않습니다. 스왑 상태를 볼 때는 아래를 같이 씁니다.

```bash
swapon --show          # 활성 스왑 장치/파일, 크기, 사용량, 우선순위
cat /proc/swaps        # 같은 정보의 원본
free -h                # 총량/사용량
sysctl -a | grep -iE 'swap|page-cluster'
```

또 실습에서 `sudo sysctl -a | grep swap`을 **연속 두 번** 실행했는데 결과는 당연히 같습니다. 값은 다시 바꾸기 전까지 유지됩니다.

---

## 3. `/proc` — 커널이 노출하는 가상 파일시스템

`/proc`는 디스크에 존재하지 않습니다. **커널이 요청 시점에 즉석에서 생성하는 텍스트**이며, 그래서 `cat`으로 읽을 수 있고 `ls -l` 상 크기가 0으로 보입니다.

| 경로 | 성격 | 오늘 실습 |
|---|---|---|
| `/proc/meminfo` | 읽기 전용 상태 | `cat /proc/meminfo` |
| `/proc/version` | 읽기 전용 상태 | `cat /proc/version` |
| `/proc/cpuinfo` | 읽기 전용 상태 | `cat /proc/cpuinfo` |
| `/proc/sys/**` | **쓰기 가능 설정** | `sysctl -w` |
| `/proc/<PID>/*` | 프로세스별 정보 | (오늘 미실습) |

### 3-1. `/proc/meminfo` 완전 해부

```
MemTotal:        2015300 kB      SwapTotal:       2034684 kB
MemFree:          128176 kB      SwapFree:        1821492 kB
MemAvailable:     922684 kB      SwapCached:        13512 kB
Buffers:           58744 kB      Cached:           869432 kB
```

#### 기본 4형제

| 필드 | man 5 proc 정의 | 이 서버 값의 해석 |
|---|---|---|
| `MemTotal` | 물리 RAM에서 예약 영역과 커널 코드를 뺀 **사용 가능한 총 RAM** | 2015300 kB ≈ 1.92 GiB. `free -m`의 1968과 동일한 값 |
| `MemFree` | 완전히 놀고 있는 메모리 | 128176 kB ≈ 125 MiB |
| `MemAvailable` | **스왑 없이 새 프로그램을 시작할 수 있는 추정치** (Linux 3.14+) | 922684 kB ≈ 878 MiB |
| `Buffers` | 원시 디스크 블록용 임시 저장. "20 MB 정도를 넘게 커지지 않아야 정상" | 58744 kB |
| `Cached` | **파일 페이지 캐시.** SwapCached는 미포함 | 869432 kB — 이 서버 메모리의 최대 소비처 |
| `SwapCached` | 스왑 아웃됐다가 다시 읽혔지만 **스왑 파일에도 사본이 남은** 메모리 | 13512 kB |

#### Active / Inactive — LRU 두 리스트

```
Active:           942460 kB     Inactive:         659040 kB
Active(anon):     532748 kB     Inactive(anon):   187684 kB
Active(file):     409712 kB     Inactive(file):   471356 kB
```

| 필드 | 의미 |
|---|---|
| `Active` | 최근에 쓰였고 **꼭 필요하기 전엔 회수하지 않는** 메모리 |
| `Inactive` | 덜 최근에 쓰인 메모리 — **회수 후보 1순위** |
| `(anon)` | **익명 페이지** = 파일 뒷받침이 없는 메모리(힙, 스택). 회수하려면 **스왑에 써야 함** |
| `(file)` | **파일 기반 페이지** = 페이지 캐시. 깨끗하면 **그냥 버리면 됨**(디스크에 원본 존재) |

> ### swappiness가 조절하는 것이 바로 이 두 축이다
>
> 메모리가 부족해지면 커널은 회수할 페이지를 골라야 합니다.
> - `Inactive(file)` 회수 → 디스크 쓰기 없이 버리면 끝(깨끗한 페이지인 경우). **싸다.**
> - `Inactive(anon)` 회수 → **반드시 스왑에 써야** 함. **비싸다.**
>
> `vm.swappiness`는 이 둘 중 어디에 압력을 얼마나 배분할지의 비율입니다. 이 서버는 `Active(anon)` 532 MB, `Active(file)` 409 MB로 익명 페이지가 더 많아 스왑 사용이 이미 208 MB 발생한 상태입니다.

#### 커널이 쓰는 메모리

| 필드 | 값 | 의미 |
|---|---|---|
| `Slab` | 152712 kB | 커널 내부 자료구조 캐시 총합 |
| `SReclaimable` | 90528 kB | 슬랩 중 **회수 가능한** 부분(dentry·inode 캐시 등) |
| `SUnreclaim` | 62184 kB | 슬랩 중 **회수 불가** 부분 |
| `KReclaimable` | 90528 kB | 압박 시 커널이 회수를 시도할 할당 (4.20+) |
| `KernelStack` | 15196 kB | 커널 스택용 메모리 |
| `PageTables` | 18156 kB | 페이지 테이블 최하위 레벨이 차지하는 메모리 |

`SReclaimable`(90528)이 `buff/cache` 합계에 포함된다는 점이 `free`와의 연결 고리입니다.
`Buffers(58744) + Cached(869432) + SReclaimable(90528) = 1018704 kB ≈ 995 MiB` → `free -m`의 `buff/cache = 1045`와 근사합니다(측정 시점 차이).

#### 오버커밋 — 이 서버에서 가장 눈에 띄는 숫자

```
CommitLimit:     3042332 kB
Committed_AS:    9054516 kB
```

| 필드 | 의미 |
|---|---|
| `CommitLimit` | `overcommit_memory=2`일 때 **허용되는 총 커밋량 상한** |
| `Committed_AS` | 프로세스들이 **약속받은(요청한) 주소 공간의 총합** |

`Committed_AS`(약 8.6 GiB)가 `CommitLimit`(약 2.9 GiB)의 **3배**입니다. 그래도 문제가 없는 이유는 `vm.overcommit_memory = 0`(휴리스틱 모드)이기 때문입니다. 이 모드에서 커널은 "명백히 말이 안 되는 요청"만 거부하고, 프로그램들이 요청만 하고 실제로는 안 쓰는 메모리가 대부분이라는 통계적 사실에 기댑니다.

> ⚠️ 만약 `vm.overcommit_memory=2`로 바꾸면 `CommitLimit = swap + RAM × overcommit_ratio(50%)` 계산이 적용되어, 이 서버에서는 **지금 돌아가는 프로세스 상당수가 메모리 할당에 실패**합니다. 오버커밋 모드를 함부로 바꾸면 안 되는 이유입니다.

#### 나머지 관찰

| 필드 | 값 | 해석 |
|---|---|---|
| `Dirty` | 388 kB | 디스크에 아직 안 쓰인 변경분. 매우 적음 = I/O 부하 없음 |
| `Writeback` | 0 kB | 지금 기록 중인 것 없음 |
| `AnonPages` | 695756 kB | 파일 뒷받침 없이 유저 공간에 매핑된 페이지 |
| `Mapped` | 404904 kB | `mmap()`으로 매핑된 파일(주로 공유 라이브러리) |
| `Shmem` | 38356 kB | tmpfs·System V·POSIX 공유 메모리. `free`의 `shared(37)`와 일치 |
| `Unevictable`/`Mlocked` | 27444 kB | `mlock()`으로 잠긴, 절대 스왑되지 않는 메모리 |
| `HugePages_Total` | 0 | 대형 페이지 미사용. `Hugepagesize: 2048 kB` = 2 MiB |
| `VmallocTotal` | 34359738367 kB | 가상 주소 공간 크기(32 TiB). **물리 메모리와 무관** |
| `DirectMap4k` / `DirectMap2M` | 112576 / 1984512 kB | 커널이 4 KiB/2 MiB 페이지로 선형 매핑한 RAM 양. 합이 MemTotal 근처 |

### 3-2. 필요한 한 줄만 뽑기

```bash
happy@userver:~$ grep MemTotal /proc/meminfo
MemTotal:        2015300 kB
```

`/proc/meminfo`는 50줄이 넘으므로 스크립트에서는 이렇게 씁니다.

```bash
grep -E '^(MemTotal|MemAvailable|SwapTotal|SwapFree):' /proc/meminfo
awk '/^MemAvailable:/ {print $2/1024 " MiB"}' /proc/meminfo
```

### 3-3. `/proc/version` — 커널 신원 확인

```
Linux version 6.8.0-138-generic (buildd@lcy02-amd64-023)
(x86_64-linux-gnu-gcc-13 (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0, GNU ld (GNU Binutils for Ubuntu) 2.42)
#138-Ubuntu SMP PREEMPT_DYNAMIC Fri Jul 31 22:41:49 UTC 2026
```

| 조각 | 의미 |
|---|---|
| `6.8.0` | 커널 메이저.마이너.패치 |
| `-138-generic` | **Ubuntu ABI 번호 138** + `generic` 플레이버(다른 플레이버: `lowlatency`, `kvm`, `aws`) |
| `buildd@lcy02-amd64-023` | Ubuntu 공식 빌드 서버에서 빌드됨 |
| `gcc-13 ... 13.3.0` | 컴파일러 버전 |
| `#138-Ubuntu` | 빌드 횟수 표시 |
| `SMP` | 대칭형 멀티프로세싱 지원 |
| `PREEMPT_DYNAMIC` | 선점 모델을 **부팅 파라미터로 전환 가능**하게 빌드됨 (`preempt=none/voluntary/full`) |
| `Fri Jul 31 ... 2026` | 커널 빌드 시각 |

> `sudo`는 필요 없습니다(메모 수정 포인트 ①). 더 짧게는 `uname -a` 또는 `uname -r`, 배포판 정보는 `lsb_release -a` / `cat /etc/os-release` 입니다.

### 3-4. `/proc/cpuinfo` — CPU 신원과 취약점 목록

```
processor       : 0
model name      : Intel(R) Core(TM) i7-8700 CPU @ 3.20GHz
cpu MHz         : 3192.002
cache size      : 12288 KB
siblings        : 1
cpu cores       : 1
```

| 필드 | 값 | 의미 |
|---|---|---|
| `processor` | `0` | **논리 CPU 번호. 0 하나뿐 = 이 VM에 vCPU 1개만 할당됨** |
| `model name` | i7-8700 | 호스트의 물리 CPU 모델(게스트에 그대로 노출) |
| `cpu family / model / stepping` | 6 / 158 / 10 | Coffee Lake 세대 식별자 |
| `microcode` | `0xde` | 마이크로코드 리비전 — 투기적 실행 취약점 완화의 핵심 |
| `cache size` | 12288 KB | L3 캐시 12 MiB (물리 CPU 값) |
| `siblings` / `cpu cores` | 1 / 1 | 같으면 **하이퍼스레딩 미노출** |
| `bogomips` | 6384.00 | 부팅 시 측정한 대략적 지표. **성능 벤치마크가 아님** |
| `address sizes` | 39 bits physical, 48 bits virtual | 물리 512 GiB, 가상 256 TiB 주소 공간 |

#### `flags`에서 반드시 봐야 할 것

| 플래그 | 의미 |
|---|---|
| **`hypervisor`** | **가상 머신 안에서 돌고 있다는 결정적 증거** |
| `vmx` | Intel VT-x 중첩 가상화 노출 |
| `aes` | AES-NI 하드웨어 암호 가속 (TLS·디스크 암호화 성능) |
| `avx`, `avx2`, `fma` | 벡터 연산 확장 |
| `pti` | Page Table Isolation — **Meltdown 완화가 켜져 있음** |
| `nx` | No-eXecute 비트 (스택 실행 방지) |
| `rdrand`, `rdseed` | 하드웨어 난수 생성기 |
| `constant_tsc`, `nonstop_tsc` | 주파수·절전 상태와 무관하게 일정한 TSC → 신뢰할 수 있는 시간 측정 |

#### `bugs` 줄 — 이 CPU가 가진 알려진 취약점

```
bugs : cpu_meltdown spectre_v1 spectre_v2 spec_store_bypass l1tf mds
       swapgs itlb_multihit srbds mmio_stale_data retbleed gds bhi its
```

Coffee Lake 세대가 투기적 실행 취약점 계열에 광범위하게 노출되어 있음을 보여줍니다. **"취약점이 있다"이지 "무방비"는 아닙니다.** 실제 완화 적용 여부는 아래로 확인합니다.

```bash
grep . /sys/devices/system/cpu/vulnerabilities/*
lscpu | grep -iA20 vulnerab
```

> **더 나은 대안:** `/proc/cpuinfo`는 논리 CPU마다 30줄씩 반복되어 읽기 힘듭니다.
> - `lscpu` — 소켓/코어/스레드 구조, 캐시 계층, 취약점 완화 상태를 한 화면에 요약
> - `nproc` — 논리 CPU 개수만 숫자로
> - `lscpu -e` — CPU별 토폴로지 표

### 3-5. `df` — 디스크 사용량, 그리고 이 서버의 실제 위험

```bash
happy@userver:~$ df
Filesystem                        1K-blocks    Used Available Use% Mounted on
tmpfs                                201532     892    200640   1% /run
/dev/mapper/ubuntu--vg-ubuntu--lv  10218772 9269668    408432  96% /
tmpfs                               1007648       0   1007648   0% /dev/shm
tmpfs                                  5120       0      5120   0% /run/lock
/dev/sda2                           1790136  105416   1575460   7% /boot
tmpfs                                201528      12    201516   1% /run/user/1000
```

| 관찰 | 해석 |
|---|---|
| `/dev/mapper/ubuntu--vg-ubuntu--lv` | **LVM 논리 볼륨**. 이름 규칙은 `VG명-LV명`이고 하이픈이 `--`로 이스케이프되어 있음 → VG=`ubuntu-vg`, LV=`ubuntu-lv` |
| **`/`가 96%, 남은 공간 400 MB** | ⚠️ **오늘 출력에서 가장 위험한 신호.** 로그·DB·Docker 이미지가 조금만 늘어도 즉시 꽉 참 |
| `/boot`이 별도 파티션(`/dev/sda2`) | 커널 업데이트가 여기 쌓임. 7%면 여유 있음 |
| `tmpfs` 4종 | **RAM 기반 파일시스템**이라 재부팅 시 소멸. `/dev/shm`은 RAM의 절반(1 GiB)이 기본 |
| `/run/user/1000` | 로그인한 UID 1000 사용자 전용 런타임 디렉터리 |

> ### `/` 96%일 때의 대응 순서
>
> ```bash
> df -h                                  # 사람이 읽기 좋게
> df -i                                  # inode 고갈도 같은 증상을 냄 — 반드시 함께 확인
> sudo du -xh / --max-depth=1 | sort -h  # -x: 다른 파일시스템으로 안 넘어감
> sudo journalctl --disk-usage
> sudo journalctl --vacuum-size=200M     # systemd 저널 정리
> sudo apt clean                         # /var/cache/apt/archives 비우기
> docker system df                       # 도커가 쓰는 용량 확인
> docker system prune -a                 # ⚠️ 안 쓰는 이미지/컨테이너 전부 삭제 — 확인 후 실행
> sudo lvextend -r -L +5G /dev/ubuntu-vg/ubuntu-lv   # VG에 여유가 있으면 온라인 확장
> ```
>
> **LVM은 확장이 온라인으로 가능**하다는 것이 이 구성의 장점입니다. `-r` 옵션이 파일시스템 크기까지 같이 늘려줍니다.
> Ubuntu 설치 시 LVM을 고르면 기본적으로 VG 전체를 LV에 주지 않으므로, `sudo vgs`로 여유 공간(`VFree`)이 있는지 먼저 봅니다.

`df` 기본 단위는 **1K 블록**입니다. `df -h`(사람 단위), `df -T`(파일시스템 종류 표시), `df -i`(inode)를 함께 기억합니다.

---

## 4. MariaDB 계정 관리 — 사용자는 "이름"이 아니라 "이름@호스트"다

### 4-1. 접속과 서버 버전

```bash
happy@userver:~$ sudo mysql -u root -p
Enter password:
Server version: 10.11.14-MariaDB-0ubuntu0.24.04.1 Ubuntu 24.04
```

| 조각 | 의미 |
|---|---|
| `10.11` | **MariaDB 10.11 LTS**. 2023-02-16 GA, 커뮤니티 지원 **2028-02-16까지** |
| `.14` | 패치 릴리스 |
| `0ubuntu0.24.04.1` | Ubuntu가 패키징한 리비전 |

> **MariaDB 10.4부터 `root@localhost`는 `unix_socket` 인증이 기본**입니다. OS의 root 권한으로 접속하면 비밀번호 없이 들어갈 수 있어서, 실무에서는 `sudo mariadb` 한 줄이면 됩니다. 오늘 `sudo mysql -u root -p`로 비밀번호까지 물은 것은 이 서버에 `mysql_native_password`가 함께 설정되어 있기 때문입니다(`mysql.user`의 root 행에 해시가 있음).
>
> 또 MariaDB 10.5부터 `mysql*` 명령은 전부 `mariadb*`로 개명되었고 `mysql`은 **심볼릭 링크**입니다. 새 스크립트는 `mariadb`, `mariadb-dump`를 쓰는 편이 안전합니다.

### 4-2. 계정 생성 — 같은 이름, 세 개의 다른 계정

```sql
CREATE DATABASE test;
CREATE USER 'test'@'localhost'      IDENTIFIED BY '1234';
CREATE USER 'test'@'%'              IDENTIFIED BY '1234';
CREATE USER 'test'@'192.168.16.100' IDENTIFIED BY '1234';
```

세 문장 모두 `Query OK, 0 rows affected` — **셋은 완전히 별개의 계정**입니다.

| 호스트 표기 | 매칭되는 접속 | 주의 |
|---|---|---|
| `'localhost'` | **유닉스 소켓 접속만** | 리눅스에서 `127.0.0.1`은 여기 매칭되지 **않음** |
| `'127.0.0.1'` | TCP 루프백 | `localhost`와 별개 |
| `'%'` | **모든 호스트** | 원격 어디서든 접속 가능 |
| `'192.168.16.100'` | 해당 IP에서만 | 가장 안전한 형태 |
| `'192.168.16.%'` | 해당 대역 | `%`는 여러 글자, `_`는 한 글자 (LIKE 규칙) |
| `'192.168.16.0/255.255.255.0'` | 넷마스크 표기 | |

> ### 호스트를 생략하면 `'%'`가 붙는다 — 오늘 실습의 핵심
>
> MariaDB 공식 문서: **계정명에서 호스트를 생략하면 `'%'`로 간주**됩니다.
> 즉 `CREATE USER test`는 `CREATE USER 'test'@'%'`이고, `DROP USER test`는 `DROP USER 'test'@'%'` 입니다. 4-5절에서 이 규칙이 실제 출력으로 드러납니다.

#### `IDENTIFIED BY` vs `IDENTIFIED BY PASSWORD`

| 구문 | 인자 | 서버가 하는 일 |
|---|---|---|
| `IDENTIFIED BY '1234'` | **평문 비밀번호** | 서버가 해시로 변환해 저장 |
| `IDENTIFIED BY PASSWORD '*A4B6...'` | **이미 계산된 해시** | 그대로 저장 |

둘 다 `mysql_native_password` / `mysql_old_password` 플러그인에서만 동작합니다.

> ⚠️ **`1234`는 실습에서만.** 평문 비밀번호는 `~/.mysql_history`와 서버의 general log에 남을 수 있습니다. 실무에서는 접속 계정에 `unix_socket`(로컬) 또는 `ed25519`(강한 해시) 플러그인을 씁니다.

### 4-3. `mysql` 데이터베이스 — 권한 정보가 사는 곳

```sql
USE mysql;
SHOW TABLES;   -- 31 rows
```

31개 시스템 테이블을 성격별로 나누면 이렇습니다.

| 그룹 | 테이블 | 역할 |
|---|---|---|
| **계정·권한** | `global_priv`, `user`, `db`, `tables_priv`, `columns_priv`, `procs_priv`, `proxies_priv`, `roles_mapping` | 권한 계층별 저장소 |
| **플러그인·루틴** | `plugin`, `func`, `proc`, `event`, `servers` | |
| **통계(옵티마이저)** | `column_stats`, `index_stats`, `table_stats`, `innodb_index_stats`, `innodb_table_stats` | 실행 계획 수립용 |
| **로그** | `general_log`, `slow_log` | `log_output=TABLE`일 때 사용 |
| **복제** | `gtid_slave_pos` | GTID 기반 복제 위치 |
| **시간대** | `time_zone`, `time_zone_name`, `time_zone_transition`, `time_zone_transition_type`, `time_zone_leap_second` | `mariadb-tzinfo-to-sql`로 채움 |
| **도움말** | `help_topic`, `help_category`, `help_keyword`, `help_relation` | 클라이언트의 `help` 명령용 |
| **시스템 버저닝** | `transaction_registry` | |

#### ★ `mysql.user`는 테이블이 아니라 **뷰**다 (메모 보강 포인트 ⑤)

**MariaDB 10.4부터** 모든 계정·비밀번호·전역 권한은 **`mysql.global_priv`** 테이블에 저장됩니다. `mysql.user`는 옛 애플리케이션과 모니터링 스크립트 호환을 위해 **그 위에 만들어 둔 뷰**입니다.

| 항목 | 10.3 이하 | 10.4 이상 (=오늘 서버) |
|---|---|---|
| 실제 저장소 | `mysql.user` 테이블 | **`mysql.global_priv` 테이블** |
| `mysql.user` | 테이블 | **뷰** |
| 저장 형식 | 컬럼 나열 | **JSON** (`Priv` 컬럼) |
| 뷰 정의자 | root | **`mariadb.sys`** (root 이름을 바꿔도 깨지지 않게) |

```sql
SELECT Host, User, JSON_DETAILED(Priv) FROM mysql.global_priv WHERE User='test'\G
```

이렇게 보면 인증 플러그인, 해시, 리소스 제한이 JSON 하나에 들어 있는 것이 보입니다. 인증 방식이 계정마다 복수로 존재할 수 있어 **관계형 컬럼으로는 표현이 불가능**해진 것이 구조 변경의 이유입니다.

`mysql.user` 목록에 있던 `mariadb.sys@localhost`가 바로 그 뷰의 정의자 계정이며, **비밀번호가 비어 있지만 로그인 불가**로 잠겨 있습니다.

### 4-4. 계정 목록 조회

```sql
SELECT host, user, password FROM user;
+----------------+-------------+-------------------------------------------+
| Host           | User        | Password                                  |
+----------------+-------------+-------------------------------------------+
| localhost      | mariadb.sys |                                           |
| localhost      | root        | *A4B6157319038724E3560894F7F932C8886EBFCF |
| localhost      | mysql       | invalid                                   |
| localhost      | pmm         | *8CBBE670408EA63553597AA7B53E33620C92A14D |
| localhost      | test        | *A4B6157319038724E3560894F7F932C8886EBFCF |
| %              | test        | *A4B6157319038724E3560894F7F932C8886EBFCF |
| 192.168.16.100 | test        | *A4B6157319038724E3560894F7F932C8886EBFCF |
+----------------+-------------+-------------------------------------------+
```

이 한 장의 표에서 읽어야 할 것이 많습니다.

| 관찰 | 해석 |
|---|---|
| `test` 계정이 **3행** | 이름이 같아도 호스트가 다르면 별개 계정 |
| `test` 3개의 해시가 **모두 동일** | 같은 비밀번호(`1234`)를 넣었기 때문. **해시가 같으면 비밀번호가 같다** |
| `root`의 해시가 `test`와 **동일** | ⚠️ **root 비밀번호도 `1234`라는 뜻.** 실습 환경이라도 매우 위험한 상태 |
| `mysql@localhost`의 값이 `invalid` | 진짜 해시가 아닌 **로그인 불가 표식**. `mysql` 계정은 `unix_socket` 전용이며 비밀번호 로그인이 봉인된 상태 |
| `mariadb.sys`가 빈 문자열 | 시스템 내부용 계정, 로그인 불가 |
| `pmm@localhost` | 8/27 실습에서 만든 Percona PMM 모니터링 계정이 그대로 남음 |
| 해시가 `*`로 시작하고 41자 | `mysql_native_password` 형식(SHA1 이중 해시). 16자 형식이면 구식 `mysql_old_password` |

> ⚠️ **`Password` 컬럼은 뷰가 만들어주는 호환용 표시**입니다. 실제 값은 `global_priv`의 JSON 안에 있고, 인증 플러그인이 `ed25519`면 이 컬럼이 비어 보일 수 있습니다. 계정 점검 시에는 아래를 씁니다.
>
> ```sql
> SELECT Host, User, plugin, authentication_string FROM mysql.user;
> ```

### 4-5. ★ `DROP USER test`가 지운 것은 `test@localhost`가 아니었다 (메모 수정 포인트 ⑥)

```sql
DROP USER test;                 -- Query OK
SELECT host, user, password FROM user;
-- → '%' | test 행이 사라짐. localhost·192.168.16.100은 그대로 남음
```

메모만 보면 "`drop user test`로 test를 지웠다"로 읽히지만, 실제로 지워진 것은 **`test@'%'` 한 개뿐**입니다. 이유는 4-2절의 규칙 그대로 — **호스트 생략 시 `'%'`가 기본**이기 때문입니다.

```sql
DROP USER test@localhost;       -- 그다음 localhost 행이 사라짐
-- 남은 것: 192.168.16.100 | test
```

출력이 6행 → 5행으로 줄어드는 것이 그 증거입니다.

> ### 실무 규칙: 계정 조작에는 **항상 호스트를 명시**한다
>
> ```sql
> DROP USER IF EXISTS 'test'@'%';
> DROP USER IF EXISTS 'test'@'localhost';
> DROP USER IF EXISTS 'test'@'192.168.16.100';
> ```
>
> | 문법 | 동작 |
> |---|---|
> | `DROP USER [IF EXISTS] user [, user] ...` | 여러 계정 동시 삭제 |
> | `IF EXISTS` | 없는 계정이면 에러 대신 **note** 반환 |
> | 필요 권한 | 전역 `CREATE USER` 또는 `mysql` DB의 `DELETE` |
> | 접속 중인 계정을 지우면 | 경고와 함께 삭제되지만 **기존 세션은 끊기지 않음**. `FORCE`로 강제 종료 가능(Community 판에는 없음) |
>
> 삭제 후 **기존 세션이 살아 있다**는 점이 중요합니다. 유출 계정을 지웠다면 `SHOW PROCESSLIST` → `KILL <id>`까지 해야 실제로 끊깁니다.

### 4-6. (메모 보강) 접속 시 어떤 계정 행이 선택되는가 — 정렬 규칙

`test@'%'`와 `test@'192.168.16.100'`이 동시에 존재하면, `192.168.16.100`에서 접속했을 때 어느 쪽 권한이 적용될까요? **더 구체적인 쪽**입니다.

서버는 기동 시 계정 목록을 메모리에 올리면서 **구체적인 것이 앞에 오도록 정렬**합니다.

| 우선순위 | Host 형태 |
|---|---|
| 1 (가장 구체적) | 리터럴 IP 주소, 리터럴 호스트명 (`192.168.16.100`, `localhost`) |
| 2 | CIDR 표기 IP |
| 3 | 넷마스크 표기 IP |
| 4 | 와일드카드 패턴 (`%`, `192.168.%`) |
| 5 (가장 느슨) | 빈 문자열 `''` |

User 쪽도 **이름이 있는 계정 → 익명 계정(빈 이름)** 순입니다.

> ⚠️ **익명 계정의 함정**: 빈 User 행이 먼저 매칭되면, 실제로 어떤 이름으로 접속했든 **익명 사용자로 취급**되어 그 세션 내내 권한이 익명 계정 기준으로 적용됩니다. "분명 권한을 줬는데 없다고 나온다"의 대표 원인입니다.
>
> 진단은 한 줄이면 끝납니다.
>
> ```sql
> SELECT USER(), CURRENT_USER();
> ```
>
> | 함수 | 의미 |
> |---|---|
> | `USER()` | 클라이언트가 **주장한** 사용자@접속호스트 |
> | `CURRENT_USER()` | 서버가 **실제로 매칭한** 계정 행 |
>
> 둘이 다르면 의도와 다른 계정 행을 탄 것입니다.

---

## 5. MariaDB 권한 관리 — GRANT / REVOKE / SHOW GRANTS

### 5-1. 권한 부여

```sql
CREATE USER 'hong'@'%' IDENTIFIED BY '1234';
GRANT ALL PRIVILEGES ON test.* TO 'hong'@'%';
```

#### 권한 계층 — `ON` 뒤에 무엇을 쓰느냐가 범위를 정한다

| 표기 | 범위 | 저장 위치 |
|---|---|---|
| `ON *.*` | **전역** — 모든 DB의 모든 객체 + 관리 권한 | `mysql.global_priv` |
| `ON test.*` | **데이터베이스** `test` 전체 | `mysql.db` |
| `ON test.books` | **테이블** 하나 | `mysql.tables_priv` |
| `ON test.books(title)` | **컬럼** | `mysql.columns_priv` |
| `ON PROCEDURE test.p1` | **저장 루틴** | `mysql.procs_priv` |

오늘 쓴 `ON test.*`는 데이터베이스 레벨이므로 `mysql.db`에 기록됩니다. **전역 권한이 아닙니다.**

### 5-2. `SHOW GRANTS` 출력 해부

```sql
SHOW GRANTS;
| GRANT ALL PRIVILEGES ON *.* TO `root`@`localhost` IDENTIFIED BY PASSWORD '*A4B6...' WITH GRANT OPTION |
| GRANT PROXY ON ''@'%' TO 'root'@'localhost' WITH GRANT OPTION                                        |
```

| 줄 | 의미 |
|---|---|
| `GRANT ALL PRIVILEGES ON *.*` | root는 전역 최고 권한 |
| `WITH GRANT OPTION` | **자기가 가진 권한을 남에게 넘겨줄 수 있음.** 이것이 없으면 권한 위임 불가 |
| `IDENTIFIED BY PASSWORD '*A4B6...'` | 출력에 **해시가 그대로 노출됨** — 화면 공유·로그 캡처 시 주의 |
| `GRANT PROXY ON ''@'%' TO root@localhost` | root가 **아무 계정으로나 프록시 인증**할 수 있다는 뜻. root의 만능 권한 중 하나 |

```sql
SHOW GRANTS FOR 'hong'@'%';
| GRANT USAGE ON *.* TO `hong`@`%` IDENTIFIED BY PASSWORD '*A4B6...' |
| GRANT ALL PRIVILEGES ON `test`.* TO `hong`@`%`                     |
```

> ### `GRANT USAGE ON *.*`가 항상 첫 줄에 나오는 이유
>
> **`USAGE`는 "아무 권한도 없음"을 뜻하는 자리표시자**입니다. MariaDB 공식 문서의 표현 그대로 "USAGE 권한은 실질적 권한을 전혀 부여하지 않습니다."
>
> 계정이 존재하면 최소한 **서버에 접속할 자격**은 있어야 하므로, 모든 계정은 전역 레벨에 USAGE 한 줄을 가집니다. 그래서 `SHOW GRANTS` 첫 줄은 사실상 **"이 계정이 존재한다"는 선언**이고, 그 뒤에 붙는 줄들이 진짜 권한입니다.
>
> USAGE 줄은 리소스 제한(`MAX_QUERIES_PER_HOUR` 등)이나 `REQUIRE SSL` 같은 계정 속성을 표시하는 자리이기도 합니다.

| 문법 | 용도 |
|---|---|
| `SHOW GRANTS;` | 내 권한 |
| `SHOW GRANTS FOR CURRENT_USER;` | 위와 동일(명시적) |
| `SHOW GRANTS FOR 'hong'@'%';` | 특정 계정 — **호스트 생략 시 `'%'`** |
| `SHOW GRANTS FOR 역할명;` | 역할(role)의 권한 |

남의 권한을 보려면 `mysql` DB에 대한 `SELECT` 권한이 필요합니다.

### 5-3. `REVOKE` — 권한만 뺀다, 계정은 남는다 (메모 보강 포인트 ⑦)

```sql
REVOKE ALL PRIVILEGES ON test.* FROM 'hong'@'%';

SHOW GRANTS FOR 'hong'@'%';
| GRANT USAGE ON *.* TO `hong`@`%` IDENTIFIED BY PASSWORD '*A4B6...' |
1 row in set
```

두 줄이던 것이 **한 줄로 줄었고, USAGE만 남았습니다.** 이 출력이 REVOKE의 성격을 정확히 보여줍니다.

| 명령 | 결과 |
|---|---|
| `REVOKE ... ON test.* FROM ...` | 해당 범위 권한만 제거. **계정과 비밀번호는 그대로** |
| `REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'hong'@'%';` | 전역·DB·테이블·컬럼·루틴 권한을 **전부** 제거. 그래도 **USAGE는 남아 접속은 됨** |
| `DROP USER 'hong'@'%';` | **계정 자체를 삭제** |

> ⚠️ **"권한을 다 뺐으니 안전하다"는 착각.** REVOKE만 하면 계정은 살아 있어 **로그인은 계속 됩니다.** 접속 자체를 막으려면 `DROP USER`, 또는 잠시 막을 거라면 `ALTER USER 'hong'@'%' ACCOUNT LOCK;` 을 씁니다.
>
> `REVOKE ALL PRIVILEGES, GRANT OPTION FROM user` 구문에는 **`ON *.*`를 쓰면 에러**입니다. 문법이 다릅니다.

### 5-4. 오늘 만든 계정의 보안 문제 정리

| 문제 | 왜 위험한가 | 실무 대안 |
|---|---|---|
| `'test'@'%'`, `'hong'@'%'` | **인터넷 어디서든** 접속 시도 가능. 3306이 열려 있으면 자동화 봇의 표적 | `'app'@'10.0.1.%'`처럼 **대역을 좁힘**. 서버는 `bind-address`로 청취 대상 제한 |
| 비밀번호 `1234` | 사전 공격 즉시 뚫림. root도 같은 해시 | 20자 이상 랜덤. 로컬 관리자는 `unix_socket` |
| `GRANT ALL PRIVILEGES ON test.*` | 애플리케이션 계정에 `DROP`, `ALTER`, `CREATE`까지 부여됨 | 앱 계정은 `SELECT, INSERT, UPDATE, DELETE`만 |
| `mysql_native_password` | SHA1 이중 해시 — 현대 기준으로 약함 | `ed25519` 플러그인 |
| root 비밀번호가 test와 동일 | 실습 계정 하나가 뚫리면 root까지 추측됨 | 계정별로 다른 비밀번호 |

---

## 6. 뷰(VIEW) 실습에서 난 에러 — `ERROR 1146`

```sql
MariaDB [mysql]> create view v_books as select name, ava from books;
ERROR 1146 (42S02): Table 'mysql.books' doesn't exist

MariaDB [mysql]> drop view if exists v_books;
Query OK, 0 rows affected, 1 warning (0.000 sec)
```

### 6-1. 에러 메시지가 이미 원인을 말하고 있다

| 조각 | 의미 |
|---|---|
| `ERROR 1146` | MariaDB 에러 번호 — 테이블 없음 |
| `(42S02)` | SQLSTATE 표준 코드. `42S02` = 기본 테이블/뷰 없음 |
| **`Table 'mysql.books'`** | ★ **`mysql` 데이터베이스에서 `books`를 찾았다**는 뜻 |

원인은 **현재 접속 DB가 `mysql`이었기 때문**입니다. 앞에서 `USE mysql;`을 했고 그대로 뷰를 만들려 했으므로, 스키마를 안 쓴 `books`가 `mysql.books`로 해석된 것입니다.

### 6-2. 세 가지가 동시에 틀렸다 (메모 수정 포인트 ⑧)

`books` 테이블은 **8/27 실습에서 `library` 데이터베이스에 만든 것**이고, 컬럼은 `id, title, author, published_year, available` 이었습니다.

| 틀린 곳 | 메모 | 올바른 값 |
|---|---|---|
| 데이터베이스 | `mysql`에 접속한 상태 | `library` |
| 컬럼 | `name` | `title` |
| 컬럼 | `ava` | `available` |

따라서 의도한 문장은 이것입니다.

```sql
USE library;
CREATE VIEW v_books AS SELECT title, available FROM books;

-- 또는 DB를 바꾸지 않고 스키마를 명시
CREATE VIEW library.v_books AS SELECT title, available FROM library.books;

SELECT * FROM v_books;
SHOW CREATE VIEW v_books\G
```

> 컬럼명 확인은 `DESC books;` 또는 `SHOW COLUMNS FROM books;` 한 줄이면 됩니다. **뷰를 만들기 전에 원본 테이블 구조를 먼저 보는 것**이 순서입니다.

### 6-3. `DROP VIEW IF EXISTS`의 "1 warning"

```
Query OK, 0 rows affected, 1 warning (0.000 sec)
```

`v_books`는 만들어진 적이 없으므로 지울 것이 없습니다. `IF EXISTS`가 있어 **에러 대신 note**가 발생했고, 그것이 `1 warning`으로 집계된 것입니다. 내용은 `SHOW WARNINGS;`로 볼 수 있습니다.

| 항목 | 설명 |
|---|---|
| `DROP VIEW [IF EXISTS] v1 [, v2] ...` | 여러 뷰 동시 삭제 |
| `IF EXISTS` 없을 때 | 없는 뷰를 지정하면 **에러**. 단 목록의 나머지 존재하는 뷰는 삭제됨 |
| `IF EXISTS` 있을 때 | 없는 뷰마다 **NOTE** 발생 |
| 필요 권한 | 각 뷰에 대한 `DROP` 권한 |
| 원자성 | MariaDB 10.6.1+에서 뷰 1개 삭제는 원자적, 여러 개는 크래시 세이프 |

> 뷰를 고칠 때는 지우고 다시 만들 필요 없이 **`CREATE OR REPLACE VIEW`** 를 씁니다. 참조 중인 다른 뷰가 있을 때 원본을 지우면, 남은 뷰는 다음 조회 시 "invalid table(s) or column(s)" 에러를 냅니다.

---

## 7. Kali Linux 초기 설정

### 7-1. 프롬프트 색으로 계정 구분하기 (메모 수정 포인트 ⑨)

메모: `빨간 터미널 -> rootShell`, `파란 터미널 -> PowerShell`

- **빨강 = root 셸**: 맞습니다.
- **파랑 = PowerShell**: **틀렸습니다.** 파란색은 **일반 사용자(kali) 셸**입니다.

Kali는 2020.3 릴리스에서 **비 root 사용자 프롬프트 색을 빨강에서 파랑으로 변경**했고, 2020.4부터 **기본 셸이 zsh**입니다. 오늘 실습 출력의 프롬프트가 그 zsh 프롬프트입니다.

```
┌──(kali㉿kali-Attacker)-[~]
└─$
```

| 조각 | 의미 |
|---|---|
| `kali` | 사용자명 |
| `㉿` | Kali 로고 문자 (`@` 자리) |
| `kali-Attacker` | 호스트명 — 이 VM의 역할이 "공격자"임을 드러냄 |
| `[~]` | 현재 디렉터리 (홈) |
| `$` | **일반 사용자.** root면 `#` |

> **가장 확실한 판별은 색이 아니라 기호와 명령입니다.**
>
> | 방법 | 일반 사용자 | root |
> |---|---|---|
> | 프롬프트 끝 기호 | `$` | `#` |
> | `whoami` | `kali` | `root` |
> | `id -u` | `1000` | `0` |
>
> 색상은 `.zshrc`/`.bashrc`로 얼마든지 바뀌므로 신뢰할 근거가 아닙니다. `kali-tweaks`로도 프롬프트를 변경할 수 있습니다.

메모의 `계정명: kali / 비번 1234` — Kali 공식 이미지의 기본 자격증명은 `kali:kali`이며, `1234`는 이 실습 VM에서 바꾼 값으로 보입니다. **실습 VM 한정 정보**로 기록합니다.

### 7-2. IP 수동 설정 전 중복 확인 (메모 보강 포인트 ⑩)

메모: `ping을 해서 응답이 없는 IP를 할당해야한다.`

방향은 맞지만 **ping 무응답은 "비어 있다"의 충분조건이 아닙니다.**

| 왜 불충분한가 |
|---|
| 방화벽이 ICMP를 차단하면 살아 있어도 무응답 (`net.ipv4.icmp_echo_ignore_all=1`이면 바로 그런 상태) |
| 잠시 꺼져 있는 장비의 IP를 뺏으면, 그 장비가 켜질 때 **IP 충돌** |
| DHCP 풀 범위 안의 주소를 고정으로 쓰면 나중에 충돌 |

더 확실한 확인 방법:

```bash
sudo arping -D -I eth0 -c 3 192.168.16.50   # -D: 중복 주소 탐지(ARP 기반, ICMP 차단과 무관)
sudo nmap -sn 192.168.16.0/24               # 대역 전체 살아있는 호스트 스캔
ip neigh show                                # ARP 캐시에 이미 보이는 이웃
arp -a
```

> 가장 안전한 것은 **네트워크 관리자에게 할당 가능 대역을 확인**하거나, 라우터의 **DHCP 예약(고정 할당)** 을 쓰는 것입니다. ARP는 L2에서 동작해 방화벽 정책의 영향을 거의 받지 않으므로 ping보다 신뢰도가 높습니다.

### 7-3. 네트워크 인터페이스 확인

```bash
ifconfig
ip ad          # = ip addr = ip address show
```

메모: `eth0 > 랜카드 이름`

| 항목 | 설명 |
|---|---|
| `eth0` | Kali의 NIC 이름. **VM 환경에서 흔한 전통적 이름** |
| Ubuntu 서버의 `enp0s3` | systemd의 **예측 가능한 인터페이스 이름**(Predictable Network Interface Names) 규칙: `en`(ethernet) + `p0`(PCI 버스 0) + `s3`(슬롯 3) |
| 두 방식의 차이 | `eth0`은 부팅마다 순서가 바뀔 수 있고, `enp0s3`은 하드웨어 위치 기반이라 고정 |

> ⚠️ **`ifconfig`는 유지보수가 끝난 도구**입니다(net-tools 패키지). 최신 배포판에는 기본 설치조차 안 되어 있는 경우가 많고, 여러 IP·정책 라우팅·VRF 등 현대 기능을 표시하지 못합니다.
>
> | 옛 명령 (net-tools) | 현재 표준 (iproute2) |
> |---|---|
> | `ifconfig` | `ip addr` / `ip a` |
> | `ifconfig eth0 up/down` | `ip link set eth0 up/down` |
> | `route -n` | `ip route` / `ip r` |
> | `arp -a` | `ip neigh` |
> | `netstat -tulpn` | `ss -tulpn` |
> | `netstat -i` | `ip -s link` |

### 7-4. 패키지 갱신 순서 (메모 수정 포인트 ⑪)

메모에는 이 순서로 적혀 있습니다.

```bash
sudo apt install -y fcitx-hangul     # ← 먼저 install
sudo apt update
sudo apt upgrade
```

**순서가 뒤바뀌었습니다.** `apt update`로 패키지 목록을 먼저 받아야 설치가 최신 버전을 찾습니다. 특히 Kali는 **롤링 릴리스**라 목록이 며칠만 지나도 404를 냅니다.

```bash
sudo apt update           # 저장소 목록 갱신 → /var/lib/apt/lists/
sudo apt full-upgrade     # Kali 공식 권장. 의존성 변화까지 처리
sudo apt install -y <패키지>
```

| 명령 | 하는 일 |
|---|---|
| `apt update` | 소스 목록에서 **패키지 색인만** 다시 받음. 설치·업그레이드는 안 함 |
| `apt upgrade` | 이미 설치된 패키지를 최신으로. **패키지 제거·신규 설치는 하지 않음** |
| `apt full-upgrade` (= `dist-upgrade`) | 의존성이 바뀌면 **필요 시 제거·설치까지 수행**. 롤링 배포판에 적합 |
| `apt install ./file.deb` | **로컬 .deb 파일 설치.** 경로에 `./`가 필요 |
| `apt clean` | `/var/cache/apt/archives/`와 `partial/`의 받아둔 .deb 삭제 |
| `apt autoclean` | 더 이상 받을 수 없는 낡은 .deb만 삭제 |
| `apt autoremove` | 자동 설치됐다가 이제 필요 없어진 의존 패키지 제거 |

### 7-5. ★ apt lock 문제 — 원인과 올바른 해결 (메모 수정 포인트 ⑫)

메모: `다운로드 중 lock이 걸리면 캐시 삭제하기 / 백그라운드에서 apt가 돌고있거나 중간에 중단하면 lock이 걸림`

**원인 진단은 정확합니다.** 다만 해결 순서와 명령이 위험합니다.

#### 잠금 파일은 4개이며, 메모에는 핵심 2개가 빠져 있다

| 잠금 파일 | 누가 잡나 |
|---|---|
| `/var/lib/dpkg/lock-frontend` | **dpkg 프런트엔드 — 실무에서 가장 자주 걸리는 것** |
| `/var/lib/dpkg/lock` | dpkg 데이터베이스 |
| `/var/lib/apt/lists/lock` | `apt update` 중 색인 갱신 |
| `/var/cache/apt/archives/lock` | .deb 다운로드 중 |

메모가 지운 것은 뒤의 두 개뿐이라, `lock-frontend`가 걸린 상황(가장 흔한 경우)은 해결되지 않습니다.

#### `sudo kill apt apt-get`은 동작하지 않는다

`kill`은 **PID(숫자)** 를 받습니다. 이름을 주면 `kill: apt: arguments must be process or job IDs` 에러입니다. 프로세스 이름으로 죽이려면 `pkill` 또는 `killall`입니다.

#### 올바른 순서 — 무작정 지우기 전에 "정말 아무도 안 쓰는지" 확인

```bash
# 1) 누가 잡고 있는지 먼저 본다 (가장 중요)
sudo lsof /var/lib/dpkg/lock-frontend
sudo fuser -v /var/lib/dpkg/lock-frontend
ps aux | grep -E 'apt|dpkg|unattended' | grep -v grep

# 2) 자동 업데이트라면 그냥 기다린다 (Kali/Ubuntu의 unattended-upgrades)
#    보통 1~2분 안에 끝남

# 3) 그래도 남아 있고, 확실히 유령 프로세스라면 종료
sudo pkill -f 'apt|apt-get'          # 우선 TERM
sudo pkill -9 -f 'apt|apt-get'       # 그래도 안 죽으면 KILL

# 4) 잠금 파일 제거 (3번 이후에만!)
sudo rm -f /var/lib/dpkg/lock-frontend
sudo rm -f /var/lib/dpkg/lock
sudo rm -f /var/lib/apt/lists/lock
sudo rm -f /var/cache/apt/archives/lock

# 5) 중단된 설치가 있으면 복구 — 이 단계를 빼먹으면 안 됨
sudo dpkg --configure -a
sudo apt --fix-broken install

# 6) 다시 시도
sudo apt update
```

> ### ⚠️ dpkg 동작 **중**에 잠금 파일을 지우면 패키지 DB가 깨진다
>
> 잠금은 버그가 아니라 **동시 실행을 막는 안전장치**입니다. dpkg가 파일을 설치하는 도중에 죽이고 잠금을 지우면 `/var/lib/dpkg/status`가 반쯤 갱신된 상태로 남아, 이후 모든 apt 작업이 실패할 수 있습니다.
>
> 그래서 순서가 **① 확인 → ② 대기 → ③ 종료 → ④ 잠금 삭제 → ⑤ `dpkg --configure -a` 복구** 여야 합니다. 메모처럼 곧바로 ④로 가면 안 됩니다.

메모의 `sudo apt clean`은 **잠금 해제와는 무관**합니다. `apt clean`은 받아둔 .deb 캐시를 지우는 명령이며(디스크 확보에는 유용), 잠금 파일은 건드리지 않습니다. `sudo ls /var/lib/apt/lists`는 색인 파일 목록을 눈으로 확인한 것으로, 진단 단계로는 타당합니다.

### 7-6. Chrome 설치 (메모 수정 포인트 ⑬)

메모:

```bash
sudo wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google.com/linux/direct/google-chrome-stable_current_amd64.deb
```

두 줄 다 손볼 곳이 있습니다.

| 문제 | 설명 | 수정 |
|---|---|---|
| `sudo wget` | 홈 디렉터리에 받는 데 root 권한이 **불필요**. root 소유 파일이 생겨 나중에 지우기 번거로움 | `wget` (sudo 없이) |
| 설치 경로가 URL 조각 | `./google.com/linux/direct/...` 라는 **로컬 디렉터리는 존재하지 않음.** wget은 현재 디렉터리에 파일명만 저장함 | `./google-chrome-stable_current_amd64.deb` |

올바른 절차:

```bash
cd ~/Downloads
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb
```

| 포인트 | 이유 |
|---|---|
| **`./`가 반드시 필요** | 없으면 apt가 이것을 **패키지 이름**으로 해석해 저장소에서 찾다가 실패 |
| `apt install` (not `dpkg -i`) | apt는 **의존성을 자동 해결**. `dpkg -i`는 의존성이 빠지면 설정 실패 상태로 남고 `apt -f install`을 또 해야 함 |
| 저장소 자동 등록 | Chrome 패키지는 설치 시 `/etc/apt/sources.list.d/google-chrome.list`와 서명 키를 등록해, 이후 `apt upgrade`로 자동 갱신됨 |

> ⚠️ **Chrome은 root로 실행되지 않습니다.** Kali에서 root 계정으로 로그인해 chrome을 띄우면 거부됩니다. 일반 사용자(kali)로 실행하거나, 오픈소스 판인 **Chromium**(`sudo apt install chromium`)을 쓰는 것이 Kali에서는 더 무난합니다.
>
> Google 리눅스 패키지는 `EB4C 1BFD 4F04 2F6D DDCC EC91 7721 F63B D38B 4796` 키로 서명되며, 대부분 패키지가 이 키를 자동 등록합니다.

### 7-7. 한글 입력과 폰트 (메모 수정 포인트 ⑭)

메모:

```bash
sudo apt install -y fcitx-hangul
sudo apt install -y fcitx-ui-classic
sudo apt install -y fcitx-libs
sudo apt install -y fonts-nanum*
```

> ### ⚠️ `fcitx`(4버전)는 Debian에서 제거되었습니다
>
> Debian 패키지 추적 기준으로 **`fcitx-hangul`은 2026-07-07에 testing에서 제거**되었고, 현재 개발 저장소에 없습니다. Kali는 Debian testing 기반이므로 **`sudo apt install fcitx-hangul`은 지금 실패할 가능성이 높습니다.**
>
> 후속 프로젝트는 **fcitx5**입니다.

현재 기준 올바른 설치:

```bash
sudo apt update
sudo apt install -y fcitx5 fcitx5-hangul fcitx5-config-qt
sudo apt install -y fonts-nanum fonts-nanum-coding fonts-noto-cjk

# 입력기 프레임워크를 fcitx5로 지정
im-config -n fcitx5
# 로그아웃 후 재로그인 (또는 재부팅) — 환경변수가 다시 읽혀야 적용됨
```

| 항목 | 설명 |
|---|---|
| `fcitx5` | 입력기 프레임워크 본체 |
| `fcitx5-hangul` | 한글 입력 엔진(libhangul 기반) |
| `fcitx5-config-qt` | GUI 설정 도구 — 한/영 전환 키를 여기서 지정 |
| `im-config -n fcitx5` | `XMODIFIERS`, `GTK_IM_MODULE` 등 환경변수를 fcitx5로 설정 |
| `fonts-nanum*` | 셸이 `*`를 **파일 glob으로 먼저 해석**하려 시도하므로, 안전하게는 따옴표(`'fonts-nanum*'`)를 쓰거나 패키지를 명시적으로 나열 |
| `fonts-noto-cjk` | 한중일 통합 폰트. 한글 렌더링 누락이 가장 적음 |

> **한글이 깨져 보이는 것(폰트)과 한글을 못 치는 것(입력기)은 다른 문제**입니다. 폰트만 깔면 표시는 되지만 입력은 안 되고, 입력기만 깔면 입력은 되지만 글자가 □로 보일 수 있습니다. 둘 다 필요합니다.

### 7-8. `ping` — 출력 완전 해석

```
┌──(kali㉿kali-Attacker)-[~]
└─$ ping 8.8.8.8
PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
64 bytes from 8.8.8.8: icmp_seq=1 ttl=108 time=69.7 ms
...
^C
--- 8.8.8.8 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3004ms
rtt min/avg/max/mdev = 68.620/69.005/69.740/0.450 ms
```

| 조각 | 의미 |
|---|---|
| `56(84) bytes` | ICMP 데이터 **56바이트** + ICMP 헤더 8 = 64, + IP 헤더 20 = **84바이트**. `-s`의 기본값이 56 |
| `64 bytes from` | 돌아온 ICMP 페이로드+헤더 크기 |
| `icmp_seq=1` | 순번. **건너뛴 번호가 있으면 그 패킷이 유실된 것** |
| `ttl=108` | **응답 패킷에 남은 TTL.** 아래 설명 참조 |
| `time=69.7 ms` | 왕복 시간(RTT) |
| `time 3004ms` | 첫 패킷부터 마지막까지 걸린 전체 시간. 기본 간격 1초 × 3 = 약 3초 |
| `rtt min/avg/max/mdev` | 최소/평균/최대/**편차**. mdev는 각 RTT가 평균에서 떨어진 정도의 평균 |

> ### `ttl=108`로 홉 수 추정하기
>
> TTL은 라우터를 지날 때마다 1씩 줄어듭니다. 출발지 OS의 초기 TTL은 관례적으로 **Linux/macOS 64, Windows 128, 일부 네트워크 장비 255** 입니다.
>
> `108`은 128에서 20 줄어든 값에 가까우므로 **약 20홉을 거쳐 왔다**고 추정할 수 있습니다. 정확한 경로는 `traceroute 8.8.8.8`(또는 `mtr 8.8.8.8`)로 확인합니다.
>
> ⚠️ 추정일 뿐입니다. 중간 장비가 TTL을 조작하거나 터널을 쓰면 어긋납니다.

#### `-c 4`의 의미와 자주 쓰는 옵션

메모의 두 실행은 결과가 사실상 같지만 **끝나는 방식이 다릅니다.**

| 실행 | 종료 방법 |
|---|---|
| `ping 8.8.8.8` | **무한 반복.** `Ctrl+C`(출력의 `^C`)로 직접 중단 |
| `ping -c 4 8.8.8.8` | 4개 보내고 **자동 종료**. 스크립트·자동화에 필수 |

| 옵션 | 의미 |
|---|---|
| `-c N` | N개 보내고 종료 |
| `-i N` | 전송 간격(초). 기본 1초. **2ms 미만은 root만** |
| `-s N` | 데이터 크기(기본 56). MTU 문제 진단에 사용 |
| `-W N` | 응답 대기 시간(초) |
| `-t N` | 보내는 패킷의 TTL 설정 |
| `-n` | 이름 해석 안 함(DNS 지연 배제) |
| `-D` | 각 줄에 타임스탬프 출력 |

> ### ping이 안 될 때 원인을 좁히는 순서
>
> | 결과 | 의미 |
> |---|---|
> | `8.8.8.8`은 되는데 도메인은 안 됨 | **DNS 문제** — `/etc/resolv.conf` 확인 |
> | 게이트웨이는 되는데 `8.8.8.8`은 안 됨 | 라우팅/NAT/외부 방화벽 |
> | 게이트웨이도 안 됨 | L2 문제 — 케이블/VM 네트워크 어댑터 모드/IP·넷마스크 |
> | 전부 무응답인데 실제로는 통신됨 | 상대가 ICMP 차단(`icmp_echo_ignore_all=1`) — **ping 실패 = 호스트 다운이 아님** |
>
> 진단 순서: `ip a`(내 IP) → `ip r`(기본 게이트웨이) → `ping <게이트웨이>` → `ping 8.8.8.8` → `ping google.com` → `cat /etc/resolv.conf`

---

## 8. 전체 실습 명령 시트

### 8-1. 메모리·커널·시스템 정보

```bash
# 메모리
free -h                    # 권장 (사람 단위)
free -m                    # MiB
free -m -s 2               # 2초 간격 반복
cat /proc/meminfo
grep -E '^(MemTotal|MemAvailable|SwapTotal|SwapFree):' /proc/meminfo
swapon --show              # 스왑 장치 목록

# 커널 파라미터
sysctl -a                          # 전체
sysctl -a | grep -i swap
sysctl vm.swappiness               # 하나만 조회
sudo sysctl -w vm.swappiness=40    # 임시 변경 (재부팅 시 소실)
echo 'vm.swappiness = 40' | sudo tee /etc/sysctl.d/99-swappiness.conf
sudo sysctl --system               # 영구 설정 즉시 반영
sysctl --dry-run -w vm.swappiness=10   # 적용 전 확인

# 시스템 정보
cat /proc/version
uname -a ; uname -r
cat /etc/os-release
cat /proc/cpuinfo
lscpu ; nproc              # 권장
grep . /sys/devices/system/cpu/vulnerabilities/*

# 디스크
df -h ; df -i ; df -T
sudo du -xh / --max-depth=1 | sort -h
sudo vgs ; sudo lvs        # LVM 여유 공간
```

### 8-2. MariaDB 계정·권한

```sql
-- 접속
sudo mariadb                      -- unix_socket (권장)
sudo mysql -u root -p

-- 계정 생성 (호스트를 반드시 명시)
CREATE USER 'test'@'localhost'      IDENTIFIED BY '강한비밀번호';
CREATE USER 'test'@'192.168.16.100' IDENTIFIED BY '강한비밀번호';
CREATE USER IF NOT EXISTS 'app'@'10.0.1.%' IDENTIFIED BY '...';

-- 조회
SELECT Host, User, plugin, authentication_string FROM mysql.user;
SELECT Host, User, JSON_DETAILED(Priv) FROM mysql.global_priv\G
SELECT USER(), CURRENT_USER();

-- 권한
GRANT ALL PRIVILEGES ON test.* TO 'hong'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON app_db.* TO 'app'@'10.0.1.%';  -- 실무형
SHOW GRANTS;
SHOW GRANTS FOR CURRENT_USER;
SHOW GRANTS FOR 'hong'@'%';
REVOKE ALL PRIVILEGES ON test.* FROM 'hong'@'%';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'hong'@'%';   -- ON *.* 쓰면 에러

-- 계정 잠금 / 삭제
ALTER USER 'hong'@'%' ACCOUNT LOCK;
DROP USER IF EXISTS 'test'@'%';
SHOW PROCESSLIST;  KILL <id>;      -- 살아있는 세션 정리

-- 뷰
USE library;
DESC books;
CREATE VIEW v_books AS SELECT title, available FROM books;
CREATE OR REPLACE VIEW v_books AS SELECT title, author FROM books;
SHOW CREATE VIEW v_books\G
DROP VIEW IF EXISTS v_books;
SHOW WARNINGS;
```

### 8-3. Kali 초기 설정

```bash
# 신원·네트워크
whoami ; id -u
ip a ; ip r ; ip neigh
sudo arping -D -I eth0 -c 3 <후보IP>      # IP 중복 확인
ping -c 4 8.8.8.8
traceroute 8.8.8.8

# 패키지
sudo apt update
sudo apt full-upgrade
sudo apt install -y <패키지>
sudo apt install ./local.deb              # ./ 필수
sudo apt clean ; sudo apt autoremove

# lock 해결 (순서 준수)
sudo lsof /var/lib/dpkg/lock-frontend
ps aux | grep -E 'apt|dpkg' | grep -v grep
sudo pkill -9 -f 'apt|apt-get'
sudo rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock \
           /var/lib/apt/lists/lock /var/cache/apt/archives/lock
sudo dpkg --configure -a
sudo apt --fix-broken install
sudo apt update

# 브라우저
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb

# 한글
sudo apt install -y fcitx5 fcitx5-hangul fcitx5-config-qt
sudo apt install -y fonts-nanum fonts-nanum-coding fonts-noto-cjk
im-config -n fcitx5
```

### 8-4. 장애 진단 순서 요약

| 증상 | 확인 순서 |
|---|---|
| "메모리가 부족한 것 같다" | `free -h`의 **available** → `/proc/meminfo`의 `MemAvailable`·`SwapFree` → `ps aux --sort=-%mem \| head` → `dmesg -T \| grep -i oom` |
| "시스템이 느리고 디스크가 계속 돈다" | `free -h`(Swap used 증가) → `vmstat 1`의 `si/so` 열 → `vm.swappiness` 확인 → 메모리 증설 검토 |
| "디스크가 꽉 찼다" | `df -h` → **`df -i`(inode)** → `du -xh / --max-depth=1 \| sort -h` → `journalctl --vacuum-size=`, `apt clean`, `docker system prune` |
| "DB 접속이 거부된다" | `SELECT USER(), CURRENT_USER();` → `SELECT Host,User FROM mysql.user;`에서 **호스트 매칭** 확인 → `SHOW GRANTS FOR ...` → 방화벽 3306 → `bind-address` |
| "분명 권한을 줬는데 없다" | `CURRENT_USER()`가 의도한 계정인지 → 익명 계정/`%` 행이 먼저 매칭됐는지 → `FLUSH PRIVILEGES`(테이블 직접 수정한 경우) |
| "apt가 잠겼다" | `lsof /var/lib/dpkg/lock-frontend` → 자동 업데이트면 대기 → `pkill` → 잠금 삭제 → **`dpkg --configure -a`** |
| "ping이 안 된다" | `ip a` → `ip r` → 게이트웨이 ping → `8.8.8.8` ping → 도메인 ping → `/etc/resolv.conf` |

### 8-5. 오늘 만난 에러 번호

| 번호 | SQLSTATE | 의미 | 오늘의 원인 |
|---|---|---|---|
| `1146` | `42S02` | 테이블/뷰가 없음 | 현재 DB가 `mysql`이라 `mysql.books`를 찾음. 실제 위치는 `library.books` |
| (warning) | — | `DROP ... IF EXISTS`의 note | 존재하지 않는 뷰를 삭제 시도 |

> 참고로 8/27 실습의 에러도 같은 방식으로 읽습니다: `1064`(문법 오류, `near` 직전 토큰을 의심), `1054`(없는 컬럼), `1366`(문자셋 불일치).

---

## 9. 메모 수정·보강 총정리

| # | 메모 원문 | 수정·보강 내용 | 근거 |
|---|---|---|---|
| ① | `sudo free -m`, `sudo cat /proc/version`, `sudo cat /proc/cpuinfo` | **`sudo` 불필요.** `/proc`의 상태 파일은 일반 사용자도 읽을 수 있음. 또 `free -g`는 2 GiB 장비에서 `available`이 0으로 잘려 무의미 → `-h`/`-m` 사용 | man 1 free |
| ② | `=> 커널에 있는 다양한 값들 확인하는 명령어` (sysctl) | 확인**과 변경**을 모두 하는 명령. 실습에서도 `-w`로 실제 변경함 | man 8 sysctl |
| ③ | `sudo sysctl -w vm.swappiness=40` 만 기록 | **재부팅하면 60으로 돌아감.** `/etc/sysctl.d/99-*.conf` + `sysctl --system`으로 영구화해야 함. 적용 순서(디렉터리 6단계, 사전순, 동명 파일 무시 규칙)도 보강 | man 8 sysctl |
| ④ | `sudo sysctl -a \| grep swap` | 이 grep은 `vm.swappiness` 한 줄만 잡음. 스왑 상태는 `swapon --show`, `/proc/swaps`, `grep -i swap`을 함께 봐야 함 | man 8 swapon |
| ⑤ | `select host, user, password from user;` | **10.4부터 `mysql.user`는 뷰**이고 실제 저장소는 `mysql.global_priv`(JSON). `Password` 열은 호환용 표시이며 ed25519 계정은 비어 보임. `mysql@localhost`의 `invalid`는 로그인 불가 표식 | MariaDB 10.4 인증 문서 |
| ⑥ | `drop user test;` → "test 삭제" | 실제로 지워진 것은 **`test@'%'`**. 계정명에서 **호스트 생략 시 `'%'`가 기본**. 이어서 `drop user test@localhost`가 필요했던 이유가 이것 | MariaDB DROP USER / CREATE USER 문서 |
| ⑦ | `revoke all privileges on test.* from 'hong'@'%';` | REVOKE는 **계정을 지우지 않음.** `USAGE`가 남아 **접속은 계속 가능**. 차단하려면 `ACCOUNT LOCK` 또는 `DROP USER` | MariaDB REVOKE 문서 |
| ⑧ | `create view v_books as select name, ava from books;` | **세 곳이 틀림** — ① 현재 DB가 `mysql`(→`library`), ② `name`(→`title`), ③ `ava`(→`available`). 에러 `1146`의 `'mysql.books'`가 원인을 그대로 지목 | 8/27 노트의 `books` 스키마 |
| ⑨ | `파란 터미널 -> PowerShell` | **틀림.** 파랑은 **일반 사용자 셸**. Kali 2020.3에서 비 root 프롬프트 색을 빨강→파랑으로 변경, 2020.4부터 기본 셸이 zsh. 확실한 판별은 `$`/`#`, `whoami`, `id -u` | Kali 2020.4 릴리스 공지 |
| ⑩ | `ping을 해서 응답이 없는 IP를 할당해야한다` | 방향은 맞지만 **불충분**. ICMP 차단·전원 꺼짐·DHCP 풀 충돌 가능. `arping -D`, `nmap -sn`, `ip neigh`를 함께 사용 | man 8 arping / ping |
| ⑪ | `apt install fcitx-hangul` → `apt update` → `apt upgrade` 순서 | **순서 반대.** `update` → `full-upgrade` → `install`. Kali는 롤링이라 목록이 오래되면 404 | apt-get(8) |
| ⑫ | `sudo kill apt apt-get` / `sudo apt clean` / lock 파일 2개 삭제 | ⓐ `kill`은 **PID만** 받음 → `pkill`. ⓑ `apt clean`은 잠금과 무관. ⓒ 잠금 파일은 **4개**이며 `/var/lib/dpkg/lock-frontend`가 가장 흔함. ⓓ 삭제 전 `lsof`/`ps`로 확인, 삭제 후 **`dpkg --configure -a`** 필수 | apt-get(8), dpkg(1) |
| ⑬ | `sudo apt install ./google.com/linux/direct/google-chrome-stable_current_amd64.deb` | **존재하지 않는 경로.** wget은 현재 디렉터리에 파일명만 저장 → `sudo apt install ./google-chrome-stable_current_amd64.deb`. `sudo wget`도 불필요 | apt-get(8) |
| ⑭ | `sudo apt install -y fcitx-hangul` 등 fcitx4 계열 | **`fcitx-hangul`은 Debian testing에서 2026-07-07 제거됨** → `fcitx5` + `fcitx5-hangul` + `im-config -n fcitx5`. `fonts-nanum*`의 `*`는 셸 glob과 충돌하므로 따옴표 처리 | Debian 패키지 추적 |
| ⑮ | (기록 없음) | **`/` 파일시스템 96% 사용, 여유 400 MB** — 오늘 출력에서 가장 시급한 문제. 정리·LVM 확장 절차 보강 | 실습 `df` 출력 |
| ⑯ | (기록 없음) | `root`와 `test`의 비밀번호 해시가 **동일** → root 비밀번호도 `1234`. `'test'@'%'`·`'hong'@'%'`는 원격 무제한 허용. 보안 대안 표 보강 | 실습 `mysql.user` 출력 |
| ⑰ | (기록 없음) | 접속 시 계정 행 **정렬·매칭 규칙**(구체적 호스트 우선, 익명 계정 함정)과 `USER()`/`CURRENT_USER()` 진단법 보강 | MySQL 8.4 접속 검증 문서 |
| ⑱ | `ifconfig`, `ip ad` 병기 | `ifconfig`(net-tools)는 유지보수 종료. iproute2 대체 명령 대응표 보강. `eth0` vs `enp0s3` 명명 규칙 차이 설명 추가 | 실습 출력 + 명명 규칙 |

---

## 10. 출처

### 리눅스 커널 · 메모리 · 시스템

- [Documentation for /proc/sys/vm/ — The Linux Kernel documentation](https://docs.kernel.org/admin-guide/sysctl/vm.html) — `swappiness` 기본 60·범위 0~200, `overcommit_memory` 3가지 모드, `page-cluster` 로그값, `panic_on_oom`, `watermark_scale_factor`, `min_free_kbytes` 경고
- [free(1) — man7.org](https://man7.org/linux/man-pages/man1/free.1.html) — `used = total - available`, `buff/cache` 구성, `-m/-g/-h/-s/-t` 옵션
- [sysctl(8) — man7.org](https://man7.org/linux/man-pages/man8/sysctl.8.html) — 옵션 전체, `--system`의 6단계 읽기 순서와 동명 파일 무시 규칙
- [proc_meminfo(5) — man7.org](https://man7.org/linux/man-pages/man5/proc_meminfo.5.html) — `MemAvailable`(3.14+), `Buffers`/`Cached`/`SwapCached`, `CommitLimit`/`Committed_AS`, `KReclaimable`(4.20+), `DirectMap*`
- [ping(8) — man7.org](https://man7.org/linux/man-pages/man8/ping.8.html) — `-c/-i/-s/-W/-t`, 56(84)바이트 계산, `mdev` 정의

### MariaDB

- [DROP USER — MariaDB Documentation](https://mariadb.com/docs/server/reference/sql-statements/account-management-sql-statements/drop-user) — **호스트 생략 시 `'%'`**, `IF EXISTS`, 필요 권한, 접속 중 계정 삭제 동작
- [CREATE USER — MariaDB Documentation](https://mariadb.com/docs/server/reference/sql-statements/account-management-sql-statements/create-user) — 호스트 표기 형태, `IDENTIFIED BY` vs `IDENTIFIED BY PASSWORD`, **`localhost` ≠ `127.0.0.1` ≠ `%`**
- [GRANT — MariaDB Documentation](https://mariadb.com/docs/server/reference/sql-statements/account-management-sql-statements/grant) — `USAGE`는 실질 권한 없음, 권한 계층별 저장 테이블, `WITH GRANT OPTION`
- [REVOKE — MariaDB Documentation](https://mariadb.com/docs/server/reference/sql-statements/account-management-sql-statements/revoke) — 계정은 남고 **USAGE 유지**, `REVOKE ALL PRIVILEGES, GRANT OPTION FROM`에 `ON *.*` 금지
- [SHOW GRANTS — MariaDB Documentation](https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/show/show-grants.md) — 출력 형식, `FOR CURRENT_USER`, USAGE 줄이 늘 나오는 이유
- [mysql.user Table — MariaDB Documentation](https://mariadb.com/docs/server/reference/system-tables/the-mysql-database-tables/mysql-user-table) — **`mysql.user`는 `global_priv`에 대한 뷰**, 정의자 `mariadb.sys`, Password 해시 형식
- [Authentication from MariaDB 10.4 — MariaDB Documentation](https://mariadb.com/docs/server/security/user-account-management/authentication-from-mariadb-10-4) — 10.4의 `global_priv` 도입, `root@localhost`의 `unix_socket` 기본화
- [DROP VIEW — MariaDB Documentation](https://mariadb.com/docs/server/server-usage/views/drop-view) — `IF EXISTS`가 에러 대신 NOTE, 필요 권한, 10.6.1+ 원자성
- [MySQL 8.4 Reference Manual — Access Control, Stage 1: Connection Verification](https://dev.mysql.com/doc/refman/8.4/en/connection-access.html) — 계정 행 **정렬 규칙**(리터럴 → CIDR → 넷마스크 → 와일드카드 → 빈 문자열)과 익명 계정 함정
- [MariaDB — endoflife.date](https://endoflife.date/mariadb) — **10.11 LTS: 2023-02-16 릴리스, 커뮤니티 지원 2028-02-16까지**

### Debian / Kali / apt

- [apt-get(8) — Debian Manpages](https://manpages.debian.org/testing/apt/apt-get.8.en.html) — `update`/`upgrade`/`dist-upgrade`/`install`/`clean`/`autoclean` 정의, 캐시 `/var/cache/apt/archives/`, 목록 `/var/lib/apt/lists/`
- [fcitx-hangul — Debian Package Tracker](https://tracker.debian.org/pkg/fcitx-hangul) — **2026-07-07 testing에서 제거**, 개발 저장소에 없음
- [fcitx5-hangul — Debian bookworm](https://packages.debian.org/bookworm/fcitx5-hangul) — 후속 패키지
- [fcitx5-hangul — Kali Linux Package Tracker](https://pkg.kali.org/pkg/fcitx5-hangul) — Kali에서의 제공 여부
- [Kali Linux 2020.4 Release — Kali Linux Blog](https://www.kali.org/blog/kali-linux-2020-4-release/) — **기본 셸 zsh**, `┌──(kali㉿kali)-[~]` 프롬프트, 2020.3에서 **비 root 프롬프트 색 빨강→파랑**
- [Google Linux Software Repositories](https://www.google.com/linuxrepositories/) — Chrome 패키지 서명 키(`D38B4796`)와 저장소 자동 등록

### 검증하지 못한 항목 (추측으로 채우지 않음)

| 항목 | 상태 |
|---|---|
| Kali 실습 VM의 `kali/1234` 자격증명 | **강사가 변경한 실습 환경 값**으로 판단. Kali 공식 이미지 기본값은 `kali/kali`. 이 노트에서는 실습 한정 정보로만 기록 |
| 메모의 `[1번 사진]`~`[5번 사진]` | 이미지가 첨부되지 않아 내용 확인 불가. 텍스트 메모에서 유추 가능한 범위(프롬프트 색, `ifconfig`/`ip ad`, apt lock 화면, `/var/lib/apt/lists` 목록, Chrome 설치 과정)까지만 서술 |
| `파란 터미널 -> PowerShell` | Kali에 PowerShell 패키지가 존재하기는 하나(`powershell`), 기본 설치는 아님. 실습 화면의 파란 프롬프트는 zsh 형식(`┌──(kali㉿…)-[~]`)이므로 **일반 사용자 zsh로 판단**. 화면을 직접 보지 못했으므로 단정은 피함 |
| `sudo sysctl -a \| grep swap`을 두 번 실행한 이유 | 메모에 설명 없음. 값 유지 확인 목적으로 추정되나 확인 불가 |
| `/` 96% 사용의 실제 원인 | `du` 출력이 메모에 없어 어느 디렉터리가 차지하는지 확인 불가. 8/27 실습에서 Docker·PMM을 설치했으므로 컨테이너 이미지가 유력하나 **미확인** |
