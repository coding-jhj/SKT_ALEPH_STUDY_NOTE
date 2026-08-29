# 260818 Cisco Packet Tracer 실습 정리

> 범위: OSPF · EIGRP · Redistribution · ACL · FTP 테스트 · NAT  
> 목적: 수업 중 실제로 입력한 명령과 출력 결과를 기준으로, 중복을 줄이고 **왜 쓰는지 / 어떻게 확인하는지 / 어디서 틀리기 쉬운지**까지 한 문서에 정리

---

# 1. 전체 실습 흐름

```text
기존 EIGRP 제거
    ↓
OSPF 구성
    ↓
Area / Router ID / Neighbor / LSDB 확인
    ↓
Loopback과 Router ID 변경 실습
    ↓
EIGRP 100 + OSPF 1 동시 운용
    ↓
EIGRP ↔ OSPF Redistribution
    ↓
라우팅 테이블에서 O / O E2 확인
    ↓
Standard ACL
    ↓
Named ACL
    ↓
Extended ACL
    ↓
FTP / Web / Ping 정책 테스트
    ↓
NAT Pool + ACL을 이용한 Dynamic NAT 구성 시작
```

---

# 2. 실습 토폴로지 핵심

라우터 간 주요 네트워크:

```text
R1 ---------------- R2 ---------------- R3
      1.1.1.0/24          2.2.2.0/24
        Area 0               Area 0
```

주요 LAN:

```text
R1 쪽
192.168.200.0/28
192.168.200.16/28
192.168.200.32/28

R2 쪽
172.16.100.0/24

R3 쪽
10.10.10.0/24
```

R3는 `2.2.2.0/24 = Area 0`, `10.10.10.0/24 = Area 1`에 참여했던 구성이므로 **ABR(Area Border Router)** 역할을 했습니다.

---

# 3. Cisco CLI 모드 구분

프롬프트를 보고 현재 모드를 구분해야 합니다.

```text
Router>                 User EXEC
Router#                 Privileged EXEC
Router(config)#         Global Configuration
Router(config-if)#      Interface Configuration
Router(config-router)#  Routing Protocol Configuration
```

## `do`를 붙이는 경우

설정 모드 안에서 EXEC 명령을 실행할 때 사용합니다.

```cisco
Router(config)#do show ip route
Router(config-if)#do show access-list
Router(config-router)#do show run
```

반면 이미 `Router#`라면:

```cisco
Router#show ip route
```

처럼 입력해야 합니다.

잘못된 예:

```cisco
Router#do show ip route
```

`Router#`에서는 `do`가 필요 없으므로 오류가 납니다.

---

# 4. OSPF 기본 구성

## OSPF 시작

```cisco
router ospf 1
```

- `1` = OSPF Process ID
- Process ID는 **해당 라우터 내부에서 OSPF 프로세스를 구분하는 번호**
- 이웃 라우터와 Process ID가 반드시 같을 필요는 없음

## Network 등록 예

```cisco
router ospf 1
 network 2.2.2.0 0.0.0.255 area 0
 network 10.10.10.0 0.0.0.255 area 1
```

뜻:

```text
2.2.2.0/24에 해당하는 인터페이스 → Area 0에서 OSPF 동작
10.10.10.0/24에 해당하는 인터페이스 → Area 1에서 OSPF 동작
```

`network` 명령은 IP 주소를 새로 만드는 명령이 아니라, **어떤 인터페이스에서 OSPF를 활성화하고 그 네트워크를 광고할지 결정**합니다.

---

# 5. Area 0 / Multi-Area / ABR

## Area 0

```text
Area 0 = Backbone Area
```

OSPF Multi-Area에서는 다른 Area들이 Backbone Area 0과 정상적으로 연결되는 구조가 기본입니다.

## ABR

```text
ABR = Area Border Router
```

두 개 이상의 Area를 연결하는 라우터입니다.

예:

```text
R3
2.2.2.0/24    → Area 0
10.10.10.0/24 → Area 1
```

따라서 R3는 ABR입니다.

## Virtual Link

Area 0과 정상적인 연속성을 확보하기 어려운 특수한 상황에서는 **Virtual Link**를 이용해 논리적으로 Backbone 연결을 구성할 수 있습니다.

초보 단계에서는 다음 정도로 기억하면 됩니다.

```text
정상 설계 → Area 0 중심으로 구성
예외 상황 → Virtual Link 고려
```

## Single Area 주의

Single-Area OSPF에서 Area 0을 쓰는 것이 일반적이고 권장되지만, **프로토콜상 반드시 Area 번호가 0이어야만 OSPF가 동작하는 것은 아닙니다.**

---

# 6. Router ID

Router ID는 OSPF에서 라우터를 식별하는 값입니다.

선택 우선순위:

```text
1. router-id로 직접 지정
2. Loopback 인터페이스 중 가장 높은 IP
3. 활성 일반 인터페이스 중 가장 높은 IP
```

## 처음 R3

```text
Serial0/3/1        = 2.2.2.2
GigabitEthernet0/0 = 10.10.10.1
```

Loopback과 직접 지정된 Router ID가 없었으므로:

```text
Router ID = 10.10.10.1
```

## Loopback 생성

```cisco
interface loopback 0
 ip address 5.5.5.5 255.255.255.0
```

OSPF 프로세스를 재시작한 뒤 Loopback이 Router ID 후보로 우선됩니다.

```text
Router ID = 5.5.5.5
```

## 직접 지정

```cisco
router ospf 1
 router-id 3.3.3.3
```

현재 실행 중인 OSPF에 적용하려면:

```cisco
clear ip ospf process
```

최종:

```text
Router ID = 3.3.3.3
```

### `clear ip ospf process`와 삭제 차이

```cisco
clear ip ospf process
```

→ 설정 유지, OSPF 프로세스 재시작

```cisco
no router ospf 1
```

→ OSPF 1 설정 자체 삭제

---

# 7. OSPF Neighbor

확인:

```cisco
show ip ospf neighbor
```

예:

```text
Neighbor ID     Pri  State    Address    Interface
172.16.100.1      0  FULL/-   2.2.2.1    Serial0/3/1
```

해석:

```text
Neighbor ID = 상대 라우터의 Router ID
Address     = 실제 연결된 상대 인터페이스 IP
FULL        = 필요한 OSPF 정보 동기화 완료
```

중요:

```text
Neighbor ID 172.16.100.1 ≠ Serial IP 2.2.2.1
```

## Hello와 FULL의 관계

잘못 기억하기 쉬운 표현:

```text
FULL이 되어야 Hello를 주고받는다.  X
```

정확한 흐름:

```text
Hello 패킷 교환
    ↓
Neighbor 발견
    ↓
Adjacency 형성 과정
    ↓
LSDB 동기화
    ↓
FULL
```

즉 **Hello가 먼저**입니다.

대표 상태 흐름:

```text
DOWN → INIT → 2-WAY → EXSTART → EXCHANGE → LOADING → FULL
```

로그 예:

```text
%OSPF-5-ADJCHG: Process 1, Nbr 172.16.100.1 on Serial0/3/1 from LOADING to FULL, Loading Done
```

→ Neighbor 관계가 정상적으로 완성된 상태입니다.

---

# 8. Point-to-Point / Broadcast / DR·BDR

## Serial

```text
Network Type = POINT-TO-POINT
```

두 라우터가 1:1로 연결되는 구조이므로 일반적으로 DR/BDR 선출이 필요 없습니다.

## Ethernet

```text
Network Type = BROADCAST
```

여러 OSPF 라우터가 같은 네트워크에 있을 수 있으므로 DR/BDR 개념이 있습니다.

```text
DR  = Designated Router
BDR = Backup Designated Router
```

Router ID와 DR은 다른 개념입니다.

```text
Router ID = 라우터 자체의 OSPF 식별자
DR        = 특정 Broadcast 네트워크에서의 대표 역할
```

---

# 9. LSDB / LSA

## LSDB

```text
LSDB = Link-State Database
```

OSPF가 알고 있는 링크 상태 정보를 저장하는 데이터베이스입니다.

확인:

```cisco
show ip ospf database
```

## LSA

```text
LSA = Link-State Advertisement
```

라우터들이 서로 전달하는 링크 상태 광고입니다.

`ADV Router`는 **Advertising Router**, 즉 해당 LSA를 광고한 라우터의 Router ID입니다.

---

# 10. OSPF 확인 명령어

```cisco
show ip interface brief
show ip protocols
show ip ospf
show ip ospf neighbor
show ip ospf database
show ip ospf interface
show ip ospf border-routers
show ip route
```

| 명령 | 확인 내용 |
|---|---|
| `show ip interface brief` | IP, 인터페이스 up/down |
| `show ip protocols` | Process, Router ID, network, area |
| `show ip ospf` | OSPF 전체 상태, Area, ABR |
| `show ip ospf neighbor` | Neighbor, FULL |
| `show ip ospf database` | LSDB / LSA |
| `show ip ospf interface` | Area, Cost, Timer, Network Type |
| `show ip route` | 실제 라우팅 테이블 |

---

# 11. 라우팅 테이블 코드

```text
C    = Connected
L    = Local
D    = EIGRP
D EX = EIGRP External
O    = OSPF Intra-Area
O IA = OSPF Inter-Area
O E1 = OSPF External Type 1
O E2 = OSPF External Type 2
```

예:

```text
O 172.16.100.0/24 [110/65] via 2.2.2.1
```

해석:

```text
O          → OSPF로 학습
172.16...  → 목적지 네트워크
110        → Administrative Distance
65         → OSPF Cost
2.2.2.1    → Next Hop
```

OSPF 기본 AD:

```text
110
```

Cost는 낮을수록 선호됩니다.

---

# 12. EIGRP 100으로 전환

OSPF를 제거한 뒤 EIGRP를 구성했던 단계:

```cisco
conf t
no router ospf 1
router eigrp 100
 network 2.2.2.0 0.0.0.255
 network 10.10.10.0 0.0.0.255
 no auto-summary
```

Loopback도 EIGRP에 포함:

```cisco
router eigrp 100
 network 5.5.5.0 0.0.0.255
```

---

# 13. Redistribution이 필요한 이유

서로 다른 Routing Protocol은 기본적으로 각자 배운 경로를 자동으로 공유하지 않습니다.

예:

```text
EIGRP 영역 ── 경계 라우터 ── OSPF 영역
```

이때 경계 라우터에서 **Redistribution(재분배)**을 설정하여 한 프로토콜의 경로를 다른 프로토콜에 전달할 수 있습니다.

---

# 14. OSPF → EIGRP 재분배

```cisco
router eigrp 100
 redistribute ospf 1 metric 1544 2000 255 1 1500
```

EIGRP는 외부에서 받은 경로에 사용할 Seed Metric이 필요합니다.

순서:

```text
1544 = Bandwidth (Kbit/s)
2000 = Delay (10 microsecond 단위) → 20 ms
255  = Reliability (255 = 100%)
1    = Load
1500 = MTU (bytes)
```

즉:

```text
redistribute ospf 1
→ OSPF 1에서 학습한 경로를 EIGRP 100으로 가져온다.
```

주의: 해당 라우터에서 OSPF 1이 실제로 존재하고 경로를 가지고 있어야 의미가 있습니다.

---

# 15. EIGRP → OSPF 재분배

OSPF를 다시 구성:

```cisco
router ospf 1
 redistribute eigrp 100 subnets
 network 2.2.2.0 0.0.0.255 area 0
```

`subnets`:

> EIGRP에서 가져온 서브넷 경로까지 OSPF로 재분배하도록 지정

기본적으로 OSPF로 재분배된 외부 경로는 `O E2`로 보일 수 있습니다.

예:

```text
O E2 5.5.5.0/24     [110/20] via 2.2.2.2
O E2 10.10.10.0/24 [110/20] via 2.2.2.2
```

---

# 16. 경계 네트워크 중복 광고 주의

수업에서 강조한 핵심:

> 경계 라우터에서 같은 네트워크를 여러 Routing Protocol로 불필요하게 중복 광고하면 경로 선택이 복잡해질 수 있다.

그래서 `2.2.2.0/24`를 EIGRP에서 제거:

```cisco
router eigrp 100
 no network 2.2.2.0 0.0.0.255
```

최종 개념:

```text
EIGRP 100
  ├─ 10.10.10.0/24
  └─ 5.5.5.0/24

OSPF 1
  └─ 2.2.2.0/24 Area 0

EIGRP ↔ OSPF는 Redistribution으로 교환
```

`no network`는 인터페이스 IP를 삭제하는 명령이 아닙니다.

```text
EIGRP 참여만 제거
인터페이스 IP는 유지
```

---

# 17. Redistribution 확인 결과

R3에서:

```text
O 1.1.1.0/24 [110/128] via 2.2.2.1
O 172.16.100.0/24 [110/65] via 2.2.2.1
O 192.168.200.0/28 [110/129] via 2.2.2.1
O 192.168.200.16/28 [110/129] via 2.2.2.1
O 192.168.200.32/28 [110/129] via 2.2.2.1
```

→ OSPF 내부 경로로 학습됨.

R2에서:

```text
O E2 5.5.5.0/24 [110/20] via 2.2.2.2
O E2 10.10.10.0/24 [110/20] via 2.2.2.2
```

→ EIGRP에서 OSPF로 재분배된 외부 경로.

Cost 예:

```text
R2 → 192.168.200.0/28 : 65
R3 → 192.168.200.0/28 : 129
```

R3에서 Serial 링크 Cost 64가 추가되어:

```text
65 + 64 = 129
```

으로 볼 수 있습니다.

---

# 18. Redistribution 설계 주의

양방향 재분배:

```text
EIGRP → OSPF
OSPF  → EIGRP
```

를 동시에 사용할 수 있지만, 실제 네트워크에서는 잘못 설계하면 **Route Feedback / Routing Loop / 비정상 경로 선호** 문제가 생길 수 있습니다.

따라서 실무에서는:

```text
경계 네트워크의 소유 프로토콜 명확화
Route-map / Tag / Metric 제어
필요한 경로만 재분배
```

등을 사용합니다.

---

# 19. ACL 기본 개념

```text
ACL = Access Control List
```

패킷을 조건에 따라 허용하거나 차단합니다.

## Standard ACL

주요 판단 기준:

```text
출발지 IP 주소
```

번호 범위:

```text
1~99
```

## Extended ACL

판단할 수 있는 정보:

```text
출발지 IP
목적지 IP
프로토콜
TCP/UDP 포트
ICMP Type 등
```

번호 범위:

```text
100~199
```

---

# 20. ACL 설계 원칙

1. **기본 통신이 되는지 먼저 확인하고 ACL은 마지막에 적용**
2. ACL은 위에서 아래로 검사
3. **첫 번째 Match에서 검사 종료**
4. 구체적인 규칙을 위에 배치
5. 넓은 규칙을 아래에 배치
6. 마지막에는 보이지 않는 `implicit deny any`가 존재

기본 배치 원칙:

```text
Standard ACL → 목적지 가까이
Extended ACL → 출발지 가까이
```

다만 실습 목적에 따라 여러 정책을 한 ACL로 묶어 목적지 쪽 `out`에 적용할 수도 있습니다.

---

# 21. Numbered Standard ACL 실습

처음 입력:

```cisco
access-list 10 deny 172.16.10.3 0.0.0.0
```

주소를 잘못 입력하여 삭제:

```cisco
no access-list 10 deny 172.16.10.3 0.0.0.0
```

올바른 규칙:

```cisco
access-list 10 deny 172.16.100.3 0.0.0.0
access-list 10 permit any
```

`0.0.0.0`은 모든 비트가 정확히 일치해야 하므로 단일 Host를 의미합니다.

다음과 같은 표현도 가능합니다.

```cisco
deny host 172.16.100.3
```

인터페이스 적용 예:

```cisco
interface gi0/0
 ip access-group 10 out
```

확인:

```cisco
show access-list
show ip access-list
```

출력:

```text
10 deny host 172.16.100.3 (36 match(es))
20 permit any (4 match(es))
```

Match Counter는 해당 규칙에 실제로 일치한 패킷 수입니다.

---

# 22. Named Standard ACL

```cisco
ip access-list standard test
 deny host 172.16.100.3
 permit any
```

인터페이스 적용:

```cisco
interface gi0/0
 ip access-group test out
```

Named ACL 삭제:

```cisco
no ip access-list standard test
```

인터페이스 적용 해제:

```cisco
interface gi0/0
 no ip access-group test out
```

**ACL 정의 삭제와 인터페이스 적용 해제는 별개**입니다.

---

# 23. Extended ACL 100 — ICMP 필터링

기존 Standard ACL 10 삭제:

```cisco
conf t
no access-list 10 deny host 172.16.100.3
no access-list 10 permit any
```

`Router#`에서 바로 `no access-list ...`를 입력하면 Global Configuration 명령이므로 오류가 납니다.

## ICMP 규칙

```cisco
access-list 100 deny icmp host 172.16.100.3 host 10.10.10.2 echo
access-list 100 deny icmp host 172.16.100.3 host 10.10.10.2 echo-reply
access-list 100 deny icmp host 172.16.100.4 host 10.10.10.3 echo
access-list 100 deny icmp host 172.16.100.4 host 10.10.10.3 echo-reply
access-list 100 permit ip any any
```

ICMP:

```text
echo       = Ping 요청
 echo-reply = Ping 응답
```

주의: 실제 Ping 왕복에서는 Echo Reply의 출발지/목적지가 요청과 반대 방향이므로, `echo-reply` 규칙을 만들 때는 방향을 확인해야 합니다.

---

# 24. `permit ip any any` 아래의 규칙 문제

출력:

```text
50 permit ip any any
60 deny icmp host 192.168.200.35 host 10.10.10.2 echo
```

이 구조에서는 60번 규칙이 사실상 적용되지 않습니다.

이유:

```text
패킷
 ↓
50 permit ip any any와 먼저 Match
 ↓
허용 후 ACL 검사 종료
 ↓
60번까지 내려가지 않음
```

따라서:

```text
구체적인 deny/permit
        ↓
permit ip any any
```

순서가 되어야 합니다.

---

# 25. Named Extended ACL과 포트 조건

```cisco
ip access-list extended test
 permit tcp host 192.168.200.35 host 10.10.10.2 eq www
 deny tcp 192.168.200.0 0.0.0.255 host 10.10.10.2 eq 80
```

첫 번째 규칙:

```text
192.168.200.35 한 대만 → 10.10.10.2:80 허용
```

두 번째 규칙:

```text
192.168.200.0/24의 나머지 Host → 10.10.10.2:80 차단
```

`192.168.200.35`도 `/24` 범위에 포함되지만 더 구체적인 permit이 위에 있으므로 먼저 허용됩니다.

---

# 26. TCP 포트 연산자

| 명령 | 의미 |
|---|---|
| `eq` | 같은 포트 |
| `gt` | 초과 |
| `lt` | 미만 |
| `neq` | 같지 않음 |
| `range` | 시작~끝 범위, 양 끝 포함 |

주의:

```text
gt = 이상 X → 초과 O
lt = 이하 X → 미만 O
```

대표 서비스:

| 이름 | 포트 | 서비스 |
|---|---:|---|
| `ftp` | 21 | FTP control |
| `telnet` | 23 | Telnet |
| `smtp` | 25 | SMTP |
| `domain` | 53 | DNS |
| `www` | 80 | HTTP |
| `pop3` | 110 | POP3 |

---

# 27. ACL 실전 문제

조건:

```text
1. 10.10.10.0/24 → 192.168.200.34 FTP 접속 불가능
   단 Ping은 가능

2. 10.10.10.3 → 192.168.200.34 FTP 접속 가능

3. 172.16.100.3 → 192.168.200.34 Web 접속 불가능

4. 그 외 모든 트래픽 허용
```

핵심은 `10.10.10.3`이 `10.10.10.0/24` 안에 포함되는 **예외 Host**라는 것입니다.

따라서 예외 permit을 먼저 둡니다.

```cisco
access-list 100 permit tcp host 10.10.10.3 host 192.168.200.34 eq ftp
access-list 100 deny tcp 10.10.10.0 0.0.0.255 host 192.168.200.34 eq ftp
access-list 100 deny tcp host 172.16.100.3 host 192.168.200.34 eq www
access-list 100 permit ip any any
```

### 왜 Ping은 가능한가?

FTP 차단 규칙은:

```text
TCP port 21
```

만 막습니다.

Ping은 ICMP이므로 FTP deny에 걸리지 않고 마지막:

```cisco
permit ip any any
```

에 의해 허용됩니다.

---

# 28. ACL 번호는 라우터마다 독립적

다른 라우터에서 ACL 100을 이미 사용했더라도 **현재 라우터에서 ACL 100을 다시 사용할 수 있습니다.**

```text
R1 ACL 100
R2 ACL 100
R3 ACL 100
```

은 각각 별개의 로컬 설정입니다.

잘못 101로 만들었다면 전체 삭제:

```cisco
conf t
no access-list 101
```

인터페이스에 적용했다면 적용도 따로 제거:

```cisco
interface <인터페이스>
 no ip access-group 101 in
```

또는:

```cisco
no ip access-group 101 out
```

---

# 29. ACL이 맞는데 Web 차단이 안 된 원인

ACL 자체:

```text
10 permit tcp host 10.10.10.3 host 192.168.200.34 eq ftp
20 deny tcp 10.10.10.0 0.0.0.255 host 192.168.200.34 eq ftp
30 deny tcp host 172.16.100.3 host 192.168.200.34 eq www
40 permit ip any any
```

은 올바르게 구성되어 있었습니다.

그런데 Web 접속이 계속 성공했습니다.

`show ip interface` 확인 결과:

```text
Outgoing access list is not set
Inbound access list is not set
```

즉 **ACL은 만들어졌지만 인터페이스에 적용되지 않은 상태**였습니다.

---

# 30. 192.168.200.34가 연결된 인터페이스 찾기

`show ip interface brief`:

```text
GigabitEthernet0/0.10  192.168.200.1
GigabitEthernet0/0.20  192.168.200.17
GigabitEthernet0/0.30  192.168.200.33
Serial0/3/0            1.1.1.1
```

서버:

```text
192.168.200.34
```

`192.168.200.34`는:

```text
192.168.200.32/28
```

에 속합니다.

범위:

```text
Network   192.168.200.32
Gateway   192.168.200.33
Host      192.168.200.33 ~ 192.168.200.46
Broadcast 192.168.200.47
```

따라서 서버 쪽 서브인터페이스는:

```text
GigabitEthernet0/0.30 = 192.168.200.33/28
```

입니다.

---

# 31. ACL 100을 Gi0/0.30 outbound에 적용

```cisco
conf t
interface gi0/0.30
 ip access-group 100 out
end
```

확인:

```cisco
show ip interface gi0/0.30
```

정상:

```text
Outgoing access list is 100
```

### 왜 `out`인가?

```text
172.16.100.3 / 10.10.10.x
          ↓
       라우터들
          ↓
현재 R1
          ↓
Gi0/0.30 OUT
   [ACL 100 검사]
          ↓
192.168.200.34 서버
```

서버 LAN으로 **나가는 패킷**을 검사하기 때문입니다.

---

# 32. ACL 실전 테스트 예상 결과

| 출발지 | 목적지/서비스 | 기대 결과 |
|---|---|---|
| `10.10.10.2` | `192.168.200.34` Ping | 성공 |
| `10.10.10.2` | `192.168.200.34` FTP | 실패 |
| `10.10.10.3` | `192.168.200.34` FTP | 성공 |
| `172.16.100.3` | `192.168.200.34` Web | 실패 |
| 기타 | 기타 정상 트래픽 | 허용 |

테스트 후:

```cisco
show access-list
```

으로 Match Counter가 증가하는지 확인합니다.

---

# 33. Packet Tracer FTP 서버 설정과 테스트

서버 `192.168.200.34`에서:

```text
Server → Services → FTP → On
```

사용자 예:

```text
Username: cisco
Password: 설정한 비밀번호
```

클라이언트에서:

```text
C:\>ftp 192.168.200.34
```

정상 연결 예:

```text
Trying to connect...192.168.200.34
Connected to 192.168.200.34
220- Welcome to PT Ftp server
Username:cisco
331- Username ok, need password
Password:*****
230- Logged in
(passive mode On)
ftp>
```

`230- Logged in`이 나오면 **FTP 로그인 성공**입니다.

파일 목록:

```text
ftp>dir
```

실제 실습에서는 IOS 이미지 파일 목록이 정상적으로 출력되어 FTP 접속 성공을 확인했습니다.

FTP 종료:

```text
ftp>quit
```

주의:

```text
ftp>
```

상태는 이미 FTP 클라이언트 내부입니다.

따라서 여기서 다시:

```text
ftp>ftp 192.168.200.34
```

를 입력하면:

```text
Invalid or non supported command.
```

가 뜹니다.

새 연결을 하려면 먼저 `quit`으로 나온 뒤:

```text
C:\>ftp 192.168.200.34
```

를 실행합니다.

---

# 34. NAT 기본 개념

```text
NAT = Network Address Translation
```

IP 주소를 다른 IP 주소로 변환하는 기술입니다.

이번 실습에서는 **ACL로 변환 대상 내부 주소를 지정하고, NAT Pool에서 변환에 사용할 주소 범위를 정의**하는 Dynamic NAT 형태를 구성하기 시작했습니다.

큰 흐름:

```text
Inside Local 주소
172.16.100.x
      ↓
ACL 10으로 변환 대상 선택
      ↓
NAT Pool dnat
1.1.1.1 ~ 1.1.1.254
      ↓
Inside Global 주소로 변환
```

---

# 35. NAT Pool 생성

도움말 확인:

```cisco
Router(config)#ip nat pool ?
  WORD  Pool name
```

Pool 이름을 `dnat`으로 지정:

```cisco
ip nat pool dnat 1.1.1.1 1.1.1.254 netmask 255.255.255.0
```

구조:

```text
ip nat pool
  dnat             → Pool 이름
  1.1.1.1          → 시작 주소
  1.1.1.254        → 끝 주소
  netmask
  255.255.255.0    → Pool의 네트워크 마스크
```

처음 다음처럼 입력했을 때:

```cisco
ip nat pool dnat 1.1.1.1 1.1.1.254 255.255.255.0
```

오류가 난 이유는 `255.255.255.0` 앞에 **`netmask` 키워드가 필요했기 때문**입니다.

올바른 문법:

```cisco
ip nat pool dnat 1.1.1.1 1.1.1.254 netmask 255.255.255.0
```

---

# 36. NAT 변환 대상 ACL

```cisco
access-list 10 permit 172.16.100.0 0.0.0.255
```

뜻:

> `172.16.100.0/24`를 NAT 변환 대상으로 선택한다.

여기서 ACL은 보안 차단 목적이라기보다 **NAT가 어떤 내부 주소를 변환할지 Match하는 용도**입니다.

```text
permit = NAT 대상에 포함
```

---

# 37. ACL 10과 NAT Pool 연결

```cisco
ip nat inside source list 10 pool dnat
```

구성 요소:

```text
ip nat inside source
→ Inside에서 출발한 Source Address를 변환

list 10
→ ACL 10에 Match되는 주소를 대상으로 함

pool dnat
→ dnat Pool의 주소 중 하나로 변환
```

즉 한 문장으로:

> `172.16.100.0/24` 출발지 주소를 NAT Pool `dnat`의 `1.1.1.1~1.1.1.254` 주소 중 하나로 변환한다.

---

# 38. NAT는 아직 인터페이스 지정이 필요함

현재 입력한 명령만으로는 NAT 설정이 완전히 끝난 것이 아닙니다.

NAT를 사용할 인터페이스에:

```cisco
ip nat inside
```

와:

```cisco
ip nat outside
```

를 지정해야 합니다.

일반 구조:

```text
172.16.100.0/24
      │
      │ Inside
      ▼
[ Router ]
      │
      │ Outside
      ▼
외부 네트워크
```

예시 형태:

```cisco
interface <172.16.100.0/24 쪽 인터페이스>
 ip nat inside

interface <외부망 쪽 인터페이스>
 ip nat outside
```

**정확한 인터페이스는 해당 NAT를 설정하는 라우터의 `show ip interface brief`를 보고 결정해야 합니다.**

---

# 39. Dynamic NAT 동작 예시

가정:

```text
Inside Host = 172.16.100.3
NAT Pool    = 1.1.1.1 ~ 1.1.1.254
```

외부로 통신할 때 예:

```text
172.16.100.3
      ↓ NAT
1.1.1.10
      ↓
외부 네트워크
```

Pool 주소는 필요에 따라 할당됩니다.

이 방식은 여러 내부 Host가 동시에 통신하려면 Pool에 충분한 주소가 있어야 합니다.

---

# 40. NAT 확인 명령

설정을 마친 뒤 확인할 명령:

```cisco
show ip nat translations
show ip nat statistics
show run | include ip nat
show access-list 10
```

Packet Tracer IOS에서 파이프 필터가 제한되면 그냥:

```cisco
show run
```

으로 확인하면 됩니다.

## `show ip nat translations`

실제 변환 테이블 확인.

## `show ip nat statistics`

Inside / Outside 인터페이스와 Pool 등 NAT 상태 확인.

---

# 41. NAT 실습에서 주의할 점

이번 Pool:

```text
1.1.1.1 ~ 1.1.1.254 /24
```

을 사용하기 전에 해당 주소 범위가 실제 토폴로지에서 다른 인터페이스 주소나 실제 장비 주소와 충돌하지 않는지 확인해야 합니다.

실습 토폴로지에서는 이미 `1.1.1.0/24`가 라우터 간 링크로 사용된 적이 있으므로, **Pool 주소와 실제 인터페이스 주소가 중복되지 않는지 확인하는 것이 중요**합니다.

수업에서 지정된 값이라면 강의 토폴로지 의도대로 진행하되, 실제 네트워크에서는 NAT Pool을 설계할 때 주소 충돌을 피해야 합니다.

---

# 42. 문제 발생 시 점검 순서

## Routing 문제

```text
1. show ip interface brief
2. show ip protocols
3. show ip ospf neighbor
4. show ip route
5. ping
```

## ACL 문제

```text
1. 기본 Ping/서비스가 ACL 적용 전 정상인가?
2. show access-list
3. ACL 규칙 순서가 맞는가?
4. permit any가 deny보다 위에 있지 않은가?
5. show ip interface
6. ACL이 실제 인터페이스에 적용되어 있는가?
7. in / out 방향이 맞는가?
8. Match Counter가 증가하는가?
```

## FTP 문제

```text
1. Server Services → FTP = On
2. 사용자 계정 존재
3. Ping 성공 여부
4. C:\> ftp 서버IP
5. ACL에서 TCP 21이 허용/차단되는지 확인
```

## NAT 문제

```text
1. ACL이 올바른 Inside 주소를 Match하는가?
2. NAT Pool 주소 범위가 맞는가?
3. ip nat inside source list ... pool ... 설정이 있는가?
4. Inside 인터페이스에 ip nat inside가 있는가?
5. Outside 인터페이스에 ip nat outside가 있는가?
6. show ip nat translations
7. show ip nat statistics
8. 주소 충돌이 없는가?
```

---

# 43. 핵심 명령어 치트시트

## OSPF

```cisco
router ospf 1
 network <network> <wildcard> area <area>
 router-id <RID>
clear ip ospf process
show ip ospf
show ip ospf neighbor
show ip ospf database
show ip route
```

## EIGRP

```cisco
router eigrp 100
 network <network> <wildcard>
 no auto-summary
show ip protocols
show ip route
```

## Redistribution

```cisco
router eigrp 100
 redistribute ospf 1 metric 1544 2000 255 1 1500

router ospf 1
 redistribute eigrp 100 subnets
```

## Standard ACL

```cisco
access-list 10 deny host <IP>
access-list 10 permit any
interface <interface>
 ip access-group 10 in|out
```

## Extended ACL

```cisco
access-list 100 permit|deny tcp|udp|icmp|ip <source> <destination> [port/type]
access-list 100 permit ip any any
```

## Named ACL

```cisco
ip access-list standard <name>
ip access-list extended <name>
```

## NAT

```cisco
ip nat pool dnat 1.1.1.1 1.1.1.254 netmask 255.255.255.0
access-list 10 permit 172.16.100.0 0.0.0.255
ip nat inside source list 10 pool dnat

interface <inside-interface>
 ip nat inside

interface <outside-interface>
 ip nat outside

show ip nat translations
show ip nat statistics
```

---

# 44. 시험·실습 전에 반드시 구분할 것

```text
Process ID
→ 라우터 내부의 OSPF 프로세스 번호

Router ID
→ OSPF에서 라우터를 식별하는 값

Neighbor ID
→ 상대 라우터의 Router ID

Neighbor Address
→ 실제 상대 인터페이스 IP

Next Hop
→ 목적지로 갈 때 다음으로 전달할 라우터 주소

Area 0
→ OSPF Backbone Area

ABR
→ 서로 다른 OSPF Area를 연결

O
→ OSPF 내부 경로

O E2
→ 다른 프로토콜에서 OSPF로 재분배된 External Type 2 경로

D EX
→ EIGRP로 재분배된 외부 경로

Standard ACL
→ 주로 출발지 기준

Extended ACL
→ 출발지 + 목적지 + 프로토콜 + 포트 등

NAT ACL
→ 차단용이 아니라 변환 대상을 선택하는 용도로도 사용 가능
```

---

# 45. 최종 기억 흐름

```text
[Routing]
인터페이스가 살아 있는가?
        ↓
라우팅 프로토콜 설정이 맞는가?
        ↓
Neighbor가 FULL인가?
        ↓
라우팅 테이블에 경로가 있는가?
        ↓
Ping이 되는가?

[Redistribution]
서로 다른 프로토콜인가?
        ↓
경계 라우터에서 필요한 경로만 재분배
        ↓
O E2 / D EX 등으로 외부 경로 확인

[ACL]
기본 통신 확인
        ↓
구체적인 규칙부터 작성
        ↓
마지막 permit/implicit deny 확인
        ↓
인터페이스 + in/out 적용
        ↓
Match Counter로 검증

[NAT]
변환 대상 ACL
        ↓
NAT Pool 생성
        ↓
ACL과 Pool 연결
        ↓
Inside / Outside 인터페이스 지정
        ↓
실제 트래픽 발생
        ↓
show ip nat translations로 검증
```
---

## NAT 실습 추가 — Inside/Outside 지정, Dynamic NAT 확인, Static NAT

### 1. NAT Inside / Outside 인터페이스 지정

NAT 설정은 Pool과 ACL만 만든다고 끝나는 것이 아닙니다.  
라우터가 어느 쪽을 **Inside(내부망)**, 어느 쪽을 **Outside(외부망)** 로 볼지 인터페이스에 지정해야 합니다.

이번 실습에서는:

```cisco
interface GigabitEthernet0/0
 ip nat inside
!
interface Serial0/3/0
 ip nat outside
```

로 설정했습니다.

의미:

```text
GigabitEthernet0/0
→ NAT 내부망 쪽 인터페이스

Serial0/3/0
→ NAT 외부망 쪽 인터페이스
```

패킷 흐름을 단순화하면:

```text
172.16.100.0/24
      │
      │ Inside
      ▼
GigabitEthernet0/0
      │
    [NAT]
      │
Serial0/3/0
      │ Outside
      ▼
외부 네트워크
```

---

### 2. `show ip nat statistics`

확인 명령:

```cisco
show ip nat statistics
```

실제 출력:

```text
Total translations: 0 (0 static, 0 dynamic, 0 extended)

Outside Interfaces: Serial0/3/0
Inside Interfaces: GigabitEthernet0/0

Hits: 0  Misses: 0
Expired translations: 0

Dynamic mappings:
-- Inside Source
access-list 10 pool dnat refCount 0

 pool dnat: netmask 255.255.255.0
       start 1.1.1.1 end 1.1.1.254
       type generic, total addresses 254 , allocated 0 (0%), misses 0
```

이 출력에서 확인할 수 있는 것:

| 항목 | 의미 |
|---|---|
| `Outside Interfaces: Serial0/3/0` | 외부망 인터페이스 |
| `Inside Interfaces: GigabitEthernet0/0` | 내부망 인터페이스 |
| `access-list 10 pool dnat` | ACL 10과 NAT Pool `dnat`이 연결됨 |
| `start 1.1.1.1 end 1.1.1.254` | 변환에 사용할 Global 주소 범위 |
| `total addresses 254` | Pool에서 사용 가능한 주소 수 |
| `allocated 0` | 아직 실제로 할당된 주소가 없었음 |
| `Hits / Misses` | NAT 변환 성공/미적용 횟수 관련 통계 |

즉 이 시점에는 **설정은 완료됐지만 아직 NAT 트래픽이 발생하지 않은 상태**였습니다.

---

### 3. Dynamic NAT이 실제로 동작한 결과

내부 PC `172.16.100.3`에서 외부 쪽 주소로 Ping을 발생시킨 뒤:

```cisco
show ip nat translations
```

를 확인했습니다.

```text
Pro  Inside global     Inside local       Outside local      Outside global

icmp 1.1.1.1:5         172.16.100.3:5     192.168.200.18:5   192.168.200.18:5
icmp 1.1.1.1:6         172.16.100.3:6     192.168.200.18:6   192.168.200.18:6
icmp 1.1.1.1:7         172.16.100.3:7     192.168.200.18:7   192.168.200.18:7
icmp 1.1.1.1:8         172.16.100.3:8     192.168.200.18:8   192.168.200.18:8
```

핵심 변환:

```text
Inside local  : 172.16.100.3
Inside global : 1.1.1.1
```

즉 내부 PC의 실제 주소 `172.16.100.3`이 외부로 나갈 때 NAT Pool에서 `1.1.1.1`을 할당받았습니다.

```text
172.16.100.3
      │
      │ NAT
      ▼
   1.1.1.1
      │
      ▼
192.168.200.18
```

이것이 **Dynamic NAT**입니다.

Dynamic NAT은 미리 특정 PC와 특정 Global IP를 고정하지 않고,  
Pool에서 사용 가능한 주소를 필요할 때 할당합니다.

---

### 4. NAT 용어 4가지

`show ip nat translations`에서 가장 중요한 네 개의 주소 표현입니다.

#### Inside Local

```text
172.16.100.3
```

내부 네트워크에서 실제로 사용하는 사설/내부 주소입니다.

> 내부 호스트의 원래 주소

#### Inside Global

```text
1.1.1.1
```

Inside Local 주소가 외부 네트워크에 보일 때 사용하는 변환된 주소입니다.

> NAT 이후 외부에서 보이는 내부 호스트 주소

#### Outside Global

예:

```text
192.168.200.18
```

외부 호스트가 실제 외부 네트워크에서 사용하는 주소입니다.

#### Outside Local

이번 실습에서는:

```text
192.168.200.18
```

처럼 Outside Global과 동일했습니다.

Outside Local은 **내부 네트워크에서 바라보는 외부 호스트의 주소**입니다.

일반적인 NAT 실습에서는 Outside Local과 Outside Global이 같은 경우가 많습니다.

---

### 5. Dynamic NAT 전체 설정 구조

이번 실습의 Dynamic NAT 설정을 하나로 보면:

```cisco
ip nat pool dnat 1.1.1.1 1.1.1.254 netmask 255.255.255.0

access-list 10 permit 172.16.100.0 0.0.0.255

ip nat inside source list 10 pool dnat

interface GigabitEthernet0/0
 ip nat inside

interface Serial0/3/0
 ip nat outside
```

각 명령의 역할:

```text
ACL 10
→ 어떤 내부 주소를 NAT할 것인가?

Pool dnat
→ 어떤 Global IP 주소로 바꿀 것인가?

ip nat inside source list 10 pool dnat
→ ACL 10에 해당하는 출발지를 dnat Pool의 주소로 변환

ip nat inside
→ 내부 인터페이스 지정

ip nat outside
→ 외부 인터페이스 지정
```

즉 NAT 설정은 다음 네 요소가 맞아야 합니다.

```text
① NAT 대상 ACL
② NAT Pool
③ ACL과 Pool 연결
④ Inside / Outside 인터페이스 지정
```

---

### 6. Static NAT 설정

다음으로 Static NAT을 설정했습니다.

```cisco
ip nat inside source static 172.16.100.4 1.1.1.10
```

형식:

```cisco
ip nat inside source static <Inside-Local> <Inside-Global>
```

이번 값:

```text
Inside Local  = 172.16.100.4
Inside Global = 1.1.1.10
```

즉:

```text
172.16.100.4  ↔  1.1.1.10
```

의 **고정 1:1 매핑**을 만든 것입니다.

Dynamic NAT과 달리 트래픽이 없더라도 이 매핑 자체는 설정에 존재합니다.

---

### 7. Static NAT 직후 Translation Table

Static NAT을 설정한 직후:

```cisco
do show ip nat translations
```

출력:

```text
Pro  Inside global     Inside local       Outside local      Outside global

---  1.1.1.10          172.16.100.4       ---                ---
```

여기서 `---`는 특정 TCP/UDP/ICMP 세션이 아니라  
**정적으로 설정된 주소 매핑 자체**를 보여주는 것입니다.

즉 아직 실제 통신을 하지 않았더라도:

```text
172.16.100.4 ↔ 1.1.1.10
```

매핑은 이미 존재합니다.

---

### 8. Static NAT 이후 실제 Ping 트래픽

`172.16.100.4`에서 `192.168.200.34`로 Ping을 발생시키자:

```text
icmp 1.1.1.10:1  172.16.100.4:1  192.168.200.34:1  192.168.200.34:1
icmp 1.1.1.10:2  172.16.100.4:2  192.168.200.34:2  192.168.200.34:2
...
icmp 1.1.1.10:8  172.16.100.4:8  192.168.200.34:8  192.168.200.34:8

---  1.1.1.10    172.16.100.4    ---               ---
```

가 나타났습니다.

해석:

```text
Inside Local
172.16.100.4

       NAT

Inside Global
1.1.1.10
```

그리고 목적지는:

```text
Outside Global
192.168.200.34
```

입니다.

즉 외부에서는 `172.16.100.4`가 아니라:

```text
1.1.1.10
```

으로 보이게 됩니다.

---

### 9. Dynamic NAT과 Static NAT 비교

| 구분 | Dynamic NAT | Static NAT |
|---|---|---|
| 매핑 방식 | Pool에서 필요할 때 할당 | 미리 고정 |
| 주소 관계 | 상황에 따라 달라질 수 있음 | 항상 1:1 |
| 예시 | `172.16.100.3 → 1.1.1.1` | `172.16.100.4 ↔ 1.1.1.10` |
| 설정 | `ip nat inside source list ... pool ...` | `ip nat inside source static ...` |
| 주 용도 | 여러 내부 호스트의 동적 변환 | 서버 등 고정 주소가 필요한 장비 |

기억:

```text
Dynamic NAT
→ Pool에서 빌려 쓴다.

Static NAT
→ 특정 내부 IP와 특정 Global IP를 고정으로 묶는다.
```

---

### 10. `show ip nat statistics`와 `show ip nat translations` 차이

```cisco
show ip nat statistics
```

→ NAT의 **전체 설정과 통계**를 확인합니다.

주요 확인 대상:

```text
Inside Interface
Outside Interface
NAT Pool
ACL
할당 주소 수
Hits / Misses
```

반면:

```cisco
show ip nat translations
```

→ 현재 생성된 **실제 주소 변환 테이블**을 확인합니다.

예:

```text
172.16.100.3 → 1.1.1.1
172.16.100.4 → 1.1.1.10
```

따라서 문제를 찾을 때:

```text
설정 자체 확인
→ show ip nat statistics

실제 변환 확인
→ show ip nat translations
```

순서로 보면 좋습니다.

---

### 11. 이번 NAT 실습에서 확인한 전체 흐름

```text
NAT Pool 생성
1.1.1.1 ~ 1.1.1.254
        ↓
ACL 10으로
172.16.100.0/24 선택
        ↓
ACL 10과 dnat Pool 연결
        ↓
Gi0/0 = ip nat inside
        ↓
S0/3/0 = ip nat outside
        ↓
172.16.100.3에서 통신 발생
        ↓
Dynamic NAT 생성
172.16.100.3 → 1.1.1.1
        ↓
Static NAT 추가
172.16.100.4 ↔ 1.1.1.10
        ↓
172.16.100.4에서 Ping
        ↓
Translation Table에서
1.1.1.10으로 변환되는 것 확인
```

---

### 12. NAT 점검 순서

NAT이 동작하지 않을 때는 다음 순서로 확인합니다.

```cisco
show ip interface brief
show run
show access-list
show ip nat statistics
show ip nat translations
show ip route
```

확인 사항:

```text
1. 내부/외부 인터페이스가 up/up인가?
2. ip nat inside / outside 방향이 맞는가?
3. NAT ACL이 실제 내부 주소를 포함하는가?
4. NAT Pool 주소와 Netmask가 맞는가?
5. ACL과 Pool 연결 명령이 존재하는가?
6. 실제 트래픽을 발생시켰는가?
7. Translation Table에 변환이 생기는가?
8. 목적지까지 라우팅 경로가 존재하는가?
```

---

### 13. NAT에서 특히 주의할 점

이번 실습에서는 NAT Pool로:

```text
1.1.1.1 ~ 1.1.1.254
```

를 사용했습니다.

그런데 앞선 라우팅 실습에서도 `1.1.1.0/24`가 실제 Serial 링크 대역으로 사용되었습니다.

실습 지시상 의도된 구성일 수 있지만, 일반적인 네트워크 설계에서는 **NAT Global Pool 주소가 이미 다른 실제 인터페이스/호스트 주소와 충돌하지 않는지 반드시 확인**해야 합니다.

주소가 중복되면:

```text
ARP / Routing / Return Path
```

문제가 생길 수 있습니다.

---

### 14. NAT 한 문장 복습

#### `ip nat inside`

> 현재 인터페이스를 NAT 내부망 방향으로 지정한다.

#### `ip nat outside`

> 현재 인터페이스를 NAT 외부망 방향으로 지정한다.

#### `ip nat inside source list 10 pool dnat`

> ACL 10에 해당하는 내부 출발지 주소를 `dnat` Pool의 Global 주소로 동적으로 변환한다.

#### `ip nat inside source static 172.16.100.4 1.1.1.10`

> 내부 주소 `172.16.100.4`와 Global 주소 `1.1.1.10`을 고정으로 1:1 매핑한다.

#### `show ip nat statistics`

> NAT의 인터페이스, Pool, ACL, Hit/Miss 등 전체 상태를 확인한다.

#### `show ip nat translations`

> 현재 실제로 만들어진 NAT 주소 변환 테이블을 확인한다.
---

## ACL 핵심 원칙 요약

ACL(Access Control List, 접근제어목록)은 패킷을 조건에 따라 허용하거나 차단하는 정책입니다.

### 분류 기준

#### 1. 필터링 기준

```text
Standard ACL
→ 주로 출발지 IP 주소 기준

Extended ACL
→ 출발지 IP + 목적지 IP + 프로토콜 + 포트 등 세부 조건
```

#### 2. 설정 방식

```text
Numbered ACL
→ 번호로 관리

Named ACL
→ 이름으로 관리
```

### ACL 검사 순서

ACL은:

```text
첫 번째 규칙
   ↓
두 번째 규칙
   ↓
세 번째 규칙
   ↓
...
```

순서로 위에서 아래로 검사합니다.

**첫 번째로 일치한 규칙에서 처리가 끝납니다.**

따라서 일반적으로:

```text
구체적이고 범위가 좁은 규칙
        ↓
넓고 포괄적인 규칙
```

순서로 배치하는 것이 좋습니다.

예:

```text
permit host 10.10.10.3 ...
deny 10.10.10.0/24 ...
permit ip any any
```

처럼 예외 Host를 먼저 처리합니다.

### Implicit Deny

ACL 마지막에는 화면에 보이지 않는 기본 규칙이 존재합니다.

Standard ACL:

```text
deny any
```

Extended ACL:

```text
deny ip any any
```

즉 아무 규칙에도 일치하지 않은 패킷은 기본적으로 차단됩니다.

그래서 특정 트래픽만 막고 나머지는 모두 허용하려면 명시적으로:

```cisco
permit any
```

또는:

```cisco
permit ip any any
```

를 마지막에 추가해야 합니다.

---

## NAT Statistics 추가 확인

실습 후 다음 명령을 확인했습니다.

```cisco
show ip nat statistics
```

출력:

```text
Total translations: 1 (1 static, 0 dynamic, 0 extended)

Outside Interfaces: Serial0/3/0
Inside Interfaces: GigabitEthernet0/0

Hits: 4  Misses: 32
Expired translations: 24

Dynamic mappings:
-- Inside Source
access-list 10 pool dnat refCount 0

 pool dnat: netmask 255.255.255.0
       start 1.1.1.1 end 1.1.1.254
       type generic, total addresses 254 , allocated 0 (0%), misses 0
```

### `Total translations: 1`

```text
Total translations: 1
(1 static, 0 dynamic, 0 extended)
```

현재 NAT Translation Table에 총 1개의 변환 항목이 존재한다는 뜻입니다.

구성:

```text
Static NAT  = 1
Dynamic NAT = 0
Extended    = 0
```

앞에서 설정한:

```cisco
ip nat inside source static 172.16.100.4 1.1.1.10
```

이 Static NAT 항목이 계속 유지되고 있기 때문에 `1 static`으로 보입니다.

---

### 왜 Dynamic NAT은 0인가?

앞서 `172.16.100.3`이 Dynamic NAT을 사용했을 때는:

```text
172.16.100.3 → 1.1.1.1
```

같은 변환이 Translation Table에 보였습니다.

하지만 Dynamic NAT 항목은 영구적으로 유지되는 것이 아니라,
사용하지 않는 상태가 일정 시간 지속되면 만료될 수 있습니다.

현재 출력:

```text
0 dynamic
Expired translations: 24
```

를 보면 이전에 생성된 동적 변환 항목들이 이미 만료된 것으로 볼 수 있습니다.

반면 Static NAT은 사용 여부와 관계없이 설정이 존재하는 동안 유지됩니다.

---

### `Hits: 4`

```text
Hits: 4
```

NAT Translation 또는 NAT 규칙을 사용해 정상적으로 처리된 패킷과 관련된 누적 카운터입니다.

쉽게 기억하면:

> NAT가 실제로 사용된 횟수를 확인하는 통계

입니다.

---

### `Misses: 32`

```text
Misses: 32
```

NAT 처리를 위해 Translation Table을 조회했지만 기존 Translation Entry가 없어서,
새 변환을 찾거나 생성해야 했던 경우 등에 관련된 누적 통계입니다.

따라서 단순히:

```text
Miss = NAT 실패
```

라고 외우면 정확하지 않습니다.

Packet Tracer 실습에서는 우선:

> NAT 변환 조회 시 기존 항목을 바로 재사용하지 못한 횟수와 관련된 값

정도로 이해하면 충분합니다.

---

### `Expired translations: 24`

```text
Expired translations: 24
```

일정 시간 사용되지 않아 삭제된 Dynamic Translation Entry의 누적 개수입니다.

예:

```text
Dynamic NAT 생성
      ↓
통신 종료
      ↓
Idle 상태 유지
      ↓
Timeout
      ↓
Translation Entry 삭제
      ↓
Expired translations 증가
```

Static NAT 설정 자체는 이렇게 자동 만료되지 않습니다.

---

### `allocated 0 (0%)`

```text
total addresses 254
allocated 0 (0%)
```

NAT Pool:

```text
1.1.1.1 ~ 1.1.1.254
```

에는 254개의 주소가 있지만,
현재 Dynamic NAT에서 실제 사용 중인 주소가 하나도 없다는 뜻입니다.

즉:

```text
Dynamic NAT Session 없음
→ Pool 주소 할당 0개
```

상태입니다.

앞에서 Dynamic NAT을 테스트했더라도 해당 변환이 만료되면 다시 `allocated 0`으로 돌아갈 수 있습니다.

---

## 현재 NAT 상태 한눈에 보기

```text
Static NAT
172.16.100.4 ↔ 1.1.1.10
→ 설정 유지
→ Total translations에 1 static으로 표시

Dynamic NAT
172.16.100.0/24
→ Pool 1.1.1.1 ~ 1.1.1.254 사용 가능
→ 현재 활성 Dynamic Translation 없음
→ allocated 0

이전에 생성된 Dynamic Translation
→ 일부 만료됨
→ Expired translations 24
```

---

## NAT Statistics 읽는 순서

`show ip nat statistics`를 보면 다음 순서로 읽으면 쉽습니다.

```text
① Total translations
   현재 변환 항목이 몇 개인가?

② Inside / Outside Interfaces
   NAT 방향 지정이 맞는가?

③ Hits / Misses
   NAT가 실제로 처리되고 있는가?

④ Expired translations
   만료된 동적 변환이 있는가?

⑤ Dynamic mappings
   어떤 ACL과 Pool을 사용하고 있는가?

⑥ allocated
   Pool에서 현재 몇 개 주소가 사용 중인가?
```
---

# VPN 기초 정리

## 1. VPN이란?

VPN은:

```text
Virtual Private Network
= 가상 사설망
```

입니다.

인터넷과 같은 공용 네트워크를 사용하면서도,
논리적으로는 사설망처럼 안전한 통신 경로를 만드는 기술입니다.

쉽게 말하면:

```text
공용 인터넷
     │
     │ 암호화된 VPN Tunnel
     ▼
사설 네트워크처럼 통신
```

하는 방식입니다.

VPN에서는 일반적으로 통신 내용을 암호화하고,
VPN 양 끝단 또는 사용자 인증을 통해 허가된 장비/사용자만 연결하도록 구성합니다.

---

## 2. VPN의 대표적인 두 가지 형태

수업에서 우선 구분할 것은:

```text
① Site-to-Site VPN
② Remote Access VPN
```

입니다.

---

## 3. Site-to-Site VPN

Site-to-Site VPN은:

> 서로 떨어져 있는 두 개 이상의 네트워크를 VPN Tunnel로 연결하는 방식

입니다.

예:

```text
서울 본사 LAN
192.168.10.0/24
      │
 [VPN 장비]
      │
====== 인터넷 ======
      │
 [VPN 장비]
      │
부산 지사 LAN
192.168.20.0/24
```

두 지점의 VPN 장비가 Tunnel을 만들기 때문에,
내부 PC들은 VPN을 직접 실행하지 않아도 서로 통신할 수 있습니다.

예를 들어:

```text
서울 PC
192.168.10.10
       ↓
   VPN Tunnel
       ↓
부산 Server
192.168.20.20
```

처럼 LAN-to-LAN 통신이 가능합니다.

pfSense 공식 문서에서도 Site-to-Site IPsec VPN은
두 네트워크를 라우터로 직접 연결한 것과 비슷하게 상호 연결하는 형태로 설명합니다.

### 주로 사용하는 상황

```text
본사 ↔ 지사
회사 ↔ 데이터센터
사무실 A ↔ 사무실 B
```

처럼 **네트워크 전체를 서로 연결**할 때 사용합니다.

---

## 4. Remote Access VPN

Remote Access VPN은:

> 외부의 개별 사용자나 장비가 회사 내부 네트워크에 원격으로 접속하는 방식

입니다.

예:

```text
회사 내부망
192.168.10.0/24
      │
 [VPN Server]
      │
==== 인터넷 ====
      │
      │ VPN Client
      ▼
재택근무 노트북
```

사용자는 노트북이나 스마트폰에서 VPN Client를 실행하고,
인증을 거쳐 회사 내부망에 접속합니다.

pfSense에서는 OpenVPN, IPsec, WireGuard 등의 방식으로 Remote Access VPN 구성이 가능합니다.

---

## 5. Site-to-Site와 Remote Access 비교

| 구분 | Site-to-Site | Remote Access |
|---|---|---|
| 연결 대상 | 네트워크 ↔ 네트워크 | 사용자/장비 ↔ 네트워크 |
| 대표 상황 | 본사 ↔ 지사 | 재택근무자 ↔ 회사 |
| VPN Client | 일반 PC에 보통 불필요 | 사용자 장비에 필요할 수 있음 |
| Tunnel Endpoint | 양쪽 VPN 장비 | VPN 서버 ↔ 사용자 Client |
| 관리 목적 | 여러 LAN 연결 | 개별 원격 사용자 접속 |

기억:

```text
Site-to-Site
→ 장소와 장소를 연결

Remote Access
→ 사람이 밖에서 내부망에 접속
```

---

## 6. VPN Tunnel

VPN에서는 흔히:

```text
Tunnel
```

이라는 표현을 사용합니다.

실제 전용선을 새로 설치하는 것이 아니라,
인터넷 위에 논리적인 통신 경로를 만들어 사용하는 것입니다.

개념적으로:

```text
원래 인터넷 경로
A ----------------------------- B

VPN 사용
A ===== 암호화된 Tunnel ===== B
```

처럼 생각하면 됩니다.

---

## 7. VPN에서 자주 사용하는 기술

대표적인 VPN 기술:

```text
IPsec
OpenVPN
WireGuard
```

### IPsec

IP 계층에서 패킷을 보호하는 VPN 기술입니다.

Site-to-Site VPN에서 매우 흔하게 사용됩니다.

pfSense 공식 문서에서도 서로 다른 VPN 장비 간
Site-to-Site 연결에서는 IPsec이 일반적인 선택이라고 설명합니다.

### OpenVPN

SSL/TLS 기반으로 구성할 수 있는 VPN 솔루션입니다.

다음 모두에 사용할 수 있습니다.

```text
Site-to-Site
Remote Access
```

### WireGuard

비교적 단순한 구조와 현대적인 암호 기술을 사용하는 VPN 방식입니다.

pfSense에서도 Site-to-Site 및 Remote Access 형태로 구성할 수 있습니다.

---

## 8. pfSense

필기의:

```text
pf sense
```

는 정확한 표기로:

```text
pfSense
```

입니다.

pfSense는 방화벽과 라우팅 기능을 제공하는 네트워크 소프트웨어로,
VPN 기능도 제공합니다.

예를 들어 pfSense에서 구성할 수 있는 VPN으로:

```text
IPsec
OpenVPN
WireGuard
```

등이 있습니다.

따라서 실습에서는 pfSense를 사용해서:

```text
Firewall
Routing
NAT
VPN
```

같은 네트워크/보안 기능을 함께 학습할 수 있습니다.

---

## 9. `utn` 필기 확인 — UTM일 가능성이 높음

수업 필기의:

```text
utn
```

은 현재 문맥상:

```text
UTM
```

을 적은 것일 가능성이 높습니다.

UTM:

```text
Unified Threat Management
= 통합 위협 관리
```

입니다.

NIST에서도 UTM을 `Unified Threat Management`로 정의하고 있으며,
일반적으로 하나의 보안 장비/플랫폼에 여러 네트워크 보안 기능을 통합하는 개념입니다.

대표 기능:

```text
Firewall
VPN
IDS / IPS
Anti-malware
Web Filtering
```

등입니다.

즉:

```text
UTM 장비
 ├─ Firewall
 ├─ VPN
 ├─ IDS/IPS
 ├─ Web Filtering
 └─ 기타 보안 기능
```

처럼 하나의 장비에서 여러 보안 기능을 제공하는 형태입니다.

> 주의: 수업에서 실제로 `UTN`이라는 별도 제품/용어를 말한 것이라면 이 해석은 달라질 수 있습니다. 현재 필기와 네트워크 보안 문맥으로는 `UTM` 오타일 가능성이 가장 높습니다.

---

## 10. pfSense와 UTM의 관계를 이해하는 방법

초보 단계에서는 다음처럼 이해하면 편합니다.

```text
전통적인 Router
→ Routing 중심

Firewall
→ 허용/차단 중심

UTM
→ Firewall + VPN + IDS/IPS 등 보안 기능 통합

pfSense
→ Firewall / Routing / NAT / VPN 등의 기능을 제공하는 플랫폼
```

pfSense를 무조건 하나의 특정 상용 UTM 제품과 동일시하기보다는,
여러 네트워크·보안 기능을 통합해 사용할 수 있는 방화벽 플랫폼으로 이해하는 것이 정확합니다.

---

## 11. VPN 전체 그림

```text
                 Internet
                    │
        ┌───────────┴───────────┐
        │                       │
Site-to-Site VPN           Remote Access VPN
        │                       │
본사 LAN ↔ 지사 LAN        사용자 PC → 회사 LAN
        │                       │
네트워크 전체 연결          개별 사용자 접속
```

---

## 12. 한 문장 복습

### VPN

> 공용 네트워크 위에 논리적으로 사설 통신망을 만들어 안전하게 통신하는 기술이다.

### Site-to-Site VPN

> 서로 떨어진 두 네트워크를 VPN Tunnel로 연결한다.

### Remote Access VPN

> 외부 사용자가 VPN Client를 통해 내부 네트워크에 접속한다.

### UTM

> 방화벽, VPN, IDS/IPS 등 여러 보안 기능을 하나의 플랫폼에 통합하는 개념이다.

### pfSense

> 방화벽, 라우팅, NAT, VPN 등의 네트워크 기능을 구성할 수 있는 방화벽 소프트웨어 플랫폼이다.
